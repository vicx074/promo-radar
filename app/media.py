"""Download restrito, transcodificação JPEG e cache persistente de imagens."""

import hashlib
import io
import ipaddress
import socket
import warnings
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_DOWNLOAD_BYTES = 5 * 1024 * 1024
MAX_OUTPUT_BYTES = 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


class MediaError(ValueError):
    """Imagem ou origem não permitida/inválida."""


@dataclass(frozen=True)
class OptimizedImage:
    content: bytes
    sha256: str
    width: int
    height: int

    @property
    def size_bytes(self) -> int:
        return len(self.content)


def validated_image_host(url: str, allowed_hosts: tuple[str, ...]) -> str:
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        if (
            parts.scheme != "https"
            or not host
            or host not in allowed_hosts
            or not parts.path.strip("/")
            or parts.username
            or parts.password
            or parts.port is not None
            or parts.fragment
        ):
            raise MediaError("Imagem deve usar HTTPS de host explicitamente permitido")
        return host
    except ValueError as exc:
        raise MediaError("URL de imagem inválida") from exc


def public_dns_addresses(host: str) -> None:
    """Defesa adicional; egress privado também deve ser bloqueado no deploy."""
    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        if not addresses:
            raise MediaError("Host de imagem sem resolução DNS")
        for result in addresses:
            address = ipaddress.ip_address(result[4][0])
            if not address.is_global:
                raise MediaError("Endereço privado/reservado bloqueado para imagem")
    except OSError as exc:
        raise MediaError("Não foi possível resolver o host de imagem") from exc


def optimize_jpeg(raw: bytes) -> OptimizedImage:
    if not raw or len(raw) > MAX_DOWNLOAD_BYTES:
        raise MediaError("Imagem excede limite de entrada (5 MiB)")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as original:
                original.load()
                if original.width * original.height > MAX_IMAGE_PIXELS:
                    raise MediaError("Imagem contém pixels demais")
                image = ImageOps.exif_transpose(original)
                if image.mode in ("RGBA", "LA") or (
                    image.mode == "P" and "transparency" in image.info
                ):
                    canvas = Image.new("RGB", image.size, (255, 255, 255))
                    canvas.paste(image.convert("RGBA"), mask=image.convert("RGBA").getchannel("A"))
                    image = canvas
                else:
                    image = image.convert("RGB")
                image.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
                # Primeiro preservar qualidade, depois reduzir peso progressivamente.
                for side in (1200, 1000, 800, 640):
                    if max(image.size) > side:
                        image.thumbnail((side, side), Image.Resampling.LANCZOS)
                    for quality in (88, 82, 76, 68):
                        buffer = io.BytesIO()
                        image.save(buffer, "JPEG", quality=quality, optimize=True)
                        content = buffer.getvalue()
                        if len(content) <= MAX_OUTPUT_BYTES:
                            return OptimizedImage(
                                content, hashlib.sha256(content).hexdigest(),
                                image.width, image.height,
                            )
                raise MediaError("Não foi possível reduzir imagem para 1 MiB")
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as exc:
        raise MediaError("Formato de imagem inválido ou perigoso") from exc


def download_image(
    url: str,
    allowed_hosts: tuple[str, ...],
    *,
    client: httpx.Client | None = None,
    resolve_host=public_dns_addresses,
) -> OptimizedImage:
    host = validated_image_host(url, allowed_hosts)
    resolve_host(host)
    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=10, follow_redirects=False, trust_env=False)
    try:
        with client.stream("GET", url, headers={"Accept": "image/jpeg,image/png,image/webp"}) as r:
            if 300 <= r.status_code < 400:
                raise MediaError("Redirecionamento de imagem não permitido")
            r.raise_for_status()
            mime = r.headers.get("content-type", "").lower().split(";")[0]
            if mime not in {"image/jpeg", "image/png", "image/webp"}:
                raise MediaError("Content-Type de imagem não permitido")
            header_length = r.headers.get("content-length")
            if header_length and int(header_length) > MAX_DOWNLOAD_BYTES:
                raise MediaError("Imagem excede limite de download")
            raw = bytearray()
            for chunk in r.iter_bytes():
                raw.extend(chunk)
                if len(raw) > MAX_DOWNLOAD_BYTES:
                    raise MediaError("Imagem excede limite de download")
        return optimize_jpeg(bytes(raw))
    except (httpx.HTTPError, ValueError) as exc:
        if isinstance(exc, MediaError):
            raise
        raise MediaError("Falha no download da imagem") from exc
    finally:
        if own_client:
            client.close()


def cache_image(image: OptimizedImage, media_dir: Path) -> str:
    media_dir.mkdir(parents=True, exist_ok=True)
    name = f"{image.sha256}.jpg"
    target = media_dir / name
    if not target.exists():
        temporary = media_dir / f".{name}.tmp"
        temporary.write_bytes(image.content)
        temporary.replace(target)
    return name


def load_image(content_dir: Path, digest: str) -> bytes:
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise MediaError("Hash de mídia inválido")
    content = (content_dir / f"{digest}.jpg").read_bytes()
    if hashlib.sha256(content).hexdigest() != digest:
        raise MediaError("Arquivo de mídia não corresponde ao hash")
    if not content or len(content) > MAX_OUTPUT_BYTES:
        raise MediaError("Arquivo de mídia fora dos limites")
    return content
