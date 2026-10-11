"""URLs de divulgação: validação estrutural, sem fingir atribuição de comissão."""

from urllib.parse import urlsplit


class AffiliateLinkError(ValueError):
    pass


def validate_official_link(raw: str) -> str:
    """Aceita padrões conhecidos de links gerados oficialmente.

    O formato e o domínio NÃO comprovam titularidade, elegibilidade, rastreamento,
    atribuição ou autorização do Mercado Livre.
    """
    try:
        url = urlsplit(raw)
        host = (url.hostname or "").lower()
        if (
            url.scheme != "https"
            or url.username
            or url.password
            or url.port is not None
            or url.fragment
            or "\\" in raw
            or any(char.isspace() for char in raw)
        ):
            raise AffiliateLinkError("Use link HTTPS oficial do Gerador de Links")
        path = url.path.strip("/")
        if host == "meli.la" and path and "/" not in path:
            return raw
        if host in {"mercadolivre.com.br", "www.mercadolivre.com.br"}:
            if path.startswith("sec/") and path.count("/") == 1:
                return raw
        raise AffiliateLinkError("Link de divulgação não tem um formato permitido")
    except ValueError as exc:
        if isinstance(exc, AffiliateLinkError):
            raise
        raise AffiliateLinkError("Link de divulgação inválido") from exc
