"""Integração do scraper terceirizado; dados fictícios, sem chamar o ML ou Apify real."""

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.catalog import CatalogUnavailable, InvalidCatalog
from app.config import Settings
from app.live_catalog import ApifyCatalogProvider, parse_apify_items
from app.main import create_app

ADMIN = {"x-admin-key": "test-admin-key"}
PRODUCT_URL = "https://www.mercadolivre.com.br/notebook-lenovo/up/MLBU1234567890"
IMAGE = "https://http2.mlstatic.com/D_TEST.webp"


def fake_item(**kwargs):
    return {
        "productId": None, "title": "Notebook Lenovo com 16GB",
        "price": 2599.90, "url": PRODUCT_URL,
        "image": IMAGE, "currency": "BRL", **kwargs,
    }


def client_with_response(status=201, body=None):
    requests = []

    def handle(request: httpx.Request):
        requests.append(request)
        return httpx.Response(status, json=body if body is not None else [fake_item()])

    return httpx.Client(transport=httpx.MockTransport(handle)), requests


def config(tmp_path):
    return Settings(
        sqlite_path=tmp_path / "offers.db",
        admin_api_key="test-admin-key",
        evolution_base_url="http://evolution:8080",
        evolution_api_key="fake", evolution_instance="promocoes",
        whatsapp_group_id="", discovery_provider="apify",
    )


def test_live_search_and_selection_only_draft(tmp_path):
    mock, reqs = client_with_response()
    provider = ApifyCatalogProvider("only-test-token", client=mock)
    with TestClient(create_app(config(tmp_path), catalog_provider=provider)) as client:
        response = client.post(
            "/api/v1/discovery/search", headers=ADMIN,
            json={"query": "notebook", "limit": 10},
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["live"] is True
        assert data["provider"] == "apify_live"
        assert data["source"] == "mercado_livre"
        assert len(data["items"]) == 1
        item = data["items"][0]
        assert item["price_cents"] == 259990
        assert item["product_url"] == PRODUCT_URL
        assert item["image_url"] == IMAGE
        assert item["promotion_verified"] is False
        assert item["price_history_available"] is False
        assert item["source_item_id"].startswith("WEB")
        assert client.get("/api/v1/offers", headers=ADMIN).json() == []

        chosen = client.post(
            "/api/v1/discovery/select", headers=ADMIN,
            json={"search_id": data["search_id"], "source_item_ids": [item["source_item_id"]]},
        )
        assert chosen.status_code == 200
        offer_id = chosen.json()["selected"][0]["offer_id"]
        offer = client.get("/api/v1/offers/" + offer_id, headers=ADMIN).json()
        assert offer["status"] == "DRAFT"
        assert offer["product_url"] == PRODUCT_URL
        assert offer["affiliate_url"] is None
        assert client.post("/api/v1/offers/" + offer_id + "/approve",
                           headers=ADMIN).status_code == 409

    assert len(reqs) == 1
    request = reqs[0]
    assert request.url.host == "api.apify.com"
    assert request.url.path.endswith("gio21~mercado-livre-scraper/run-sync-get-dataset-items")
    assert request.headers["Authorization"] == "Bearer only-test-token"
    assert "only-test-token" not in str(request.url)
    payload = json.loads(request.content)
    assert payload["keyword"] == "notebook"
    assert payload["maxPages"] == 1
    assert payload["maxItems"] == 10
    assert request.url.params["maxTotalChargeUsd"] == "0.20"


def test_no_secret_means_503_never_falls_back_to_csv(tmp_path):
    with TestClient(create_app(config(tmp_path))) as client:
        res = client.post("/api/v1/discovery/search", headers=ADMIN,
                          json={"query": "notebook", "limit": 10})
        assert res.status_code == 503
        assert "APIFY_TOKEN" in res.json()["detail"]
        assert client.get("/api/v1/offers", headers=ADMIN).json() == []


@pytest.mark.parametrize("price, expected", [
    (1299.9, 129990), ("1.299,90", 129990),
    ("1299.90", 129990), (True, None),
    ("NaN", None), (-1, None), ("123.456", None),
    (0, None), (None, None),
])
def test_price_parsing_exact(price, expected):
    from app.live_catalog import _price_in_cents

    assert _price_in_cents(price) == expected


def test_rejects_redirects_lookalike_hosts_wrong_images_and_deduplicates():
    rows = [
        fake_item(url="https://click1.mercadolivre.com.br/mclics/clicks"),
        fake_item(url="https://www.mercadolivre.com.br.evil.org/foo"),
        fake_item(url="https://evil.org/anything"),
        fake_item(url="https://www.mercadolivre.com.br@evil.org/foo"),
        fake_item(url=PRODUCT_URL, image="https://evil.org/img.jpg"),
        fake_item(url=PRODUCT_URL),
        fake_item(url="https://www.mercadolivre.com.br/invalid",
                  status="out_of_stock"),
    ]
    parsed = parse_apify_items(rows, limit=20)
    assert len(parsed) == 1
    assert parsed[0].image_url is None
    assert parsed[0].product_url == PRODUCT_URL


@pytest.mark.parametrize("http_code, expect", [
    (401, "Credencial"), (402, "Saldo"), (403, "Credencial"),
    (429, "Limite"), (500, "indisponível"),
])
def test_remote_errors_are_clear_and_not_leaked(http_code, expect):
    mock, _ = client_with_response(status=http_code)
    provider = ApifyCatalogProvider("private-token", client=mock)
    with pytest.raises(CatalogUnavailable, match=expect) as err:
        provider.search("mouse", 5)
    assert "private-token" not in str(err.value)


def test_rejects_schema_changes_and_missing_products():
    with pytest.raises(InvalidCatalog):
        parse_apify_items({"items": []}, limit=10)
    with pytest.raises(InvalidCatalog):
        parse_apify_items([{"error": "blocked"}], limit=10)
    assert parse_apify_items([], limit=10) == []


def test_offline_mode_remains_explicit_for_existing_csv_tests(tmp_path):
    cfg = config(tmp_path)
    assert cfg.discovery_provider == "apify"
    assert Settings.from_env().discovery_provider in {"csv", "apify"}
