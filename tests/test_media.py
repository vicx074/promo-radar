import io
from hashlib import sha256

import httpx
import pytest
from PIL import Image

from app.media import (
    MediaError,
    cache_image,
    download_image,
    load_image,
    optimize_jpeg,
    validated_image_host,
)

ALLOWED = ("http2.mlstatic.com",)
URL = "https://http2.mlstatic.com/D_NQ_NP_123.jpg"


def image_bytes(size=(2400, 1800), color=(20, 80, 160), kind="PNG"):
    image = Image.new("RGB", size, color)
    output = io.BytesIO()
    image.save(output, kind)
    return output.getvalue()


def test_optimize_image_resize_jpeg_and_cache(tmp_path):
    original = image_bytes()
    optimized = optimize_jpeg(original)
    assert optimized.width == 1200
    assert optimized.height == 900
    assert optimized.size_bytes < len(original)
    assert optimized.size_bytes <= 1024 * 1024
    assert optimized.sha256 == sha256(optimized.content).hexdigest()
    with Image.open(io.BytesIO(optimized.content)) as result:
        assert result.format == "JPEG"
        assert result.size == (1200, 900)
    name = cache_image(optimized, tmp_path)
    assert name == f"{optimized.sha256}.jpg"
    assert load_image(tmp_path, optimized.sha256) == optimized.content


def test_download_only_allowed_domain_no_redirect_and_jpeg_optimized():
    data = image_bytes((1400, 700))

    def handler(request):
        assert request.url.host == "http2.mlstatic.com"
        return httpx.Response(200, content=data, headers={"content-type": "image/png"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = download_image(URL, ALLOWED, client=client, resolve_host=lambda _: None)
    assert (result.width, result.height) == (1200, 600)

    def redirect(_):
        return httpx.Response(302, headers={"location": "https://evil.test/image"})

    with httpx.Client(transport=httpx.MockTransport(redirect)) as client:
        with pytest.raises(MediaError, match="Redirecionamento"):
            download_image(URL, ALLOWED, client=client, resolve_host=lambda _: None)


@pytest.mark.parametrize("url", [
    "http://http2.mlstatic.com/img.jpg",
    "https://localhost/image.jpg",
    "https://http2.mlstatic.com.evil.test/img.jpg",
    "https://user:pass@http2.mlstatic.com/img.jpg",
    "https://http2.mlstatic.com:8000/img.jpg",
    "https://127.0.0.1/img.jpg",
    "file:///etc/passwd",
])
def test_rejects_untrusted_urls(url):
    with pytest.raises(MediaError):
        validated_image_host(url, ALLOWED)


def test_rejects_bad_content_and_bombs():
    with pytest.raises(MediaError):
        optimize_jpeg(b"not an image")
    with pytest.raises(MediaError, match="5 MiB"):
        optimize_jpeg(b"0" * (5 * 1024 * 1024 + 1))


def test_rejects_stream_overflow_and_wrong_mime():
    def wrong_mime(_):
        return httpx.Response(200, content=b"junk", headers={"content-type": "text/html"})

    with httpx.Client(transport=httpx.MockTransport(wrong_mime)) as client:
        with pytest.raises(MediaError, match="Content-Type"):
            download_image(URL, ALLOWED, client=client, resolve_host=lambda _: None)

    def large(_):
        return httpx.Response(200, content=b"x" * (5 * 1024 * 1024 + 1),
                              headers={"content-type": "image/jpeg"})

    with httpx.Client(transport=httpx.MockTransport(large)) as client:
        with pytest.raises(MediaError, match="limite de download"):
            download_image(URL, ALLOWED, client=client, resolve_host=lambda _: None)


def test_detects_tampered_image(tmp_path):
    result = optimize_jpeg(image_bytes((200, 200)))
    name = cache_image(result, tmp_path)
    (tmp_path / name).write_bytes(b"tampered")
    with pytest.raises(MediaError, match="hash"):
        load_image(tmp_path, result.sha256)
