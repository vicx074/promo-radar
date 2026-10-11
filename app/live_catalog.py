"""Busca real sob demanda via provedor de dados públicos do Mercado Livre.

O Actor Apify é serviço TERCEIRO (scraping), não API oficial do ML.
Não faz login, não coleta cookies e não contorna bloqueios no nosso servidor.
"""
import hashlib
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit, urlunsplit

import httpx

from app.catalog import CatalogUnavailable, InvalidCatalog
from app.discovery import CatalogItem, _valid_product_url

_ACTOR_ENDPOINT = (
    "https://api.apify.com/v2/acts/"
    "gio21~mercado-livre-scraper/run-sync-get-dataset-items"
)
_ID = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
_MAX_JSON_BYTES = 2_000_000
_BAD_STOCK = {"out_of_stock", "unavailable", "inactive", "closed", "paused"}


def _price_in_cents(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        raw = str(value).strip()
        if not raw:
            return None
        if "," in raw and "." in raw:
            raw = raw.replace(".", "").replace(",", ".")
        elif "," in raw:
            raw = raw.replace(",", ".")
        amount = Decimal(raw)
        if not amount.is_finite() or amount <= 0:
            return None
        cents = amount * 100
        if cents != cents.to_integral_value() or cents > 1_000_000_000:
            return None
        return int(cents)
    except (InvalidOperation, ValueError, TypeError):
        return None


def _product_link(value: object) -> str | None:
    if not isinstance(value, str) or len(value) > 2048:
        return None
    if not _valid_product_url(value):
        return None
    parsed = urlsplit(value)
    if (
        parsed.hostname not in {"mercadolivre.com.br", "www.mercadolivre.com.br"}
        or "\\" in value
        or any(c.isspace() for c in value)
    ):
        return None
    # Retira parâmetros de rastreamento; nunca segue URL externa / redirecionamento.
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def _image(value: object) -> str | None:
    if not isinstance(value, str) or len(value) > 2048:
        return None
    try:
        u = urlsplit(value)
        if (
            u.scheme == "https"
            and u.hostname == "http2.mlstatic.com"
            and not u.username
            and not u.password
            and u.port is None
            and not any(c.isspace() for c in value)
        ):
            return urlunsplit((u.scheme, u.netloc, u.path, "", ""))
    except ValueError:
        pass
    return None


def parse_apify_items(data: object, *, limit: int) -> list[CatalogItem]:
    """Valida cada entrada de terceiros, sem aceitar links tracking/fora do ML."""
    if not isinstance(data, list):
        raise InvalidCatalog("Provedor retornou formato incompatível (não é uma lista)")
    if len(data) > 1000:
        raise InvalidCatalog("Provedor retornou produtos acima do limite de segurança")
    results: list[CatalogItem] = []
    seen: set[str] = set()
    for row in data:
        if not isinstance(row, dict):
            continue
        if row.get("available") is False:
            continue
        if str(row.get("status", "")).lower() in _BAD_STOCK:
            continue
        title = row.get("title")
        if not isinstance(title, str):
            continue
        title = " ".join(title.split())
        if not 3 <= len(title) <= 200:
            continue
        price = _price_in_cents(row.get("price"))
        url = _product_link(row.get("url") or row.get("product_url"))
        if price is None or url is None:
            continue
        item_id = row.get("productId") or row.get("item_id")
        if not isinstance(item_id, str) or not _ID.fullmatch(item_id):
            item_id = "WEB" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
        if item_id in seen:
            continue
        seen.add(item_id)
        image = _image(row.get("image") or row.get("image_url"))
        results.append(CatalogItem(item_id, title, price, url, image))
        if len(results) >= limit:
            break
    if data and not results:
        raise InvalidCatalog(
            "O provedor não retornou anúncios válidos: confira URLs, preços e formato"
        )
    return results


@dataclass
class ApifyCatalogProvider:
    """Executa scraper terceirizado em consulta única, com limite de custo.

    Requer APIFY_TOKEN no backend; é proibido fornecer cookie/senha Mercado Livre.
    A conta Apify pode cobrar por resultado mesmo quando houver falha de rede.
    """

    token: str
    client: httpx.Client | None = None
    source: str = "mercado_livre"
    name: str = "apify_live"

    def search(self, query: str, limit: int) -> list[CatalogItem]:
        if not self.token:
            raise CatalogUnavailable(
                "Busca ao vivo não configurada: defina APIFY_TOKEN na VPS. "
                "O CSV não é utilizado como resultado falso."
            )
        if not 2 <= len(query.strip()) <= 100 or not 1 <= limit <= 50:
            raise InvalidCatalog("Nicho ou limite de resultados inválido")
        # Um Actor específico e auditável; não é URL recebida do usuário (sem SSRF).
        # A configuração reduz a carga e limita o custo máximo por execução.
        payload = {
            "keyword": query.strip(),
            "maxItems": max(10, limit),
            "maxPages": 1,
            "sort": "relevance",
        }
        client = self.client or httpx.Client(timeout=110.0, follow_redirects=False)
        own_client = self.client is None
        try:
            response = client.post(
                _ACTOR_ENDPOINT,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                params={"maxItems": str(max(10, limit)), "maxTotalChargeUsd": "0.20"},
                json=payload,
            )
            if response.status_code in (401, 403):
                raise CatalogUnavailable("Credencial ou acesso Apify recusado (HTTP 401/403)")
            if response.status_code == 402:
                raise CatalogUnavailable("Saldo Apify insuficiente para a busca ao vivo")
            if response.status_code == 429:
                raise CatalogUnavailable("Limite de solicitações Apify atingido")
            if response.status_code >= 400:
                raise CatalogUnavailable(
                    f"Provedor de busca ao vivo indisponível (HTTP {response.status_code})"
                )
            if len(response.content) > _MAX_JSON_BYTES:
                raise InvalidCatalog("Resposta do provedor maior que o permitido")
            try:
                data = response.json()
            except ValueError as exc:
                raise InvalidCatalog("Provedor não retornou JSON válido") from exc
            return parse_apify_items(data, limit=limit)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise CatalogUnavailable("Timeout ou conexão indisponível no provedor de busca") from exc
        finally:
            if own_client:
                client.close()
