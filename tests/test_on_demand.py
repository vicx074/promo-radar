import sqlite3
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


class NeverSend:
    def __init__(self):
        self.calls = []

    def send_text(self, *args):
        self.calls.append(("text", args))
        raise AssertionError("A seleção jamais deve enviar texto")

    def send_image(self, *args):
        self.calls.append(("image", args))
        raise AssertionError("A seleção jamais deve enviar imagem")


def settings(tmp_path):
    return Settings(
        sqlite_path=tmp_path / "offers.db", admin_api_key="test-admin-key",
        evolution_base_url="http://evolution:8080", evolution_api_key="test-evolution-key",
        evolution_instance="promocoes", whatsapp_group_id="test-group@g.us",
        send_enabled=True,
    )


def catalog(tmp_path):
    folder = tmp_path / "import"
    folder.mkdir(exist_ok=True)
    csv_file = folder / "catalogo.csv"
    csv_file.write_text(
        "source_item_id,title,price_cents,product_url,image_url\n"
        "MLBmouse,Mouse Gamer Eletrônico,19990,"
        "https://www.mercadolivre.com.br/p/MLB111,"
        "https://http2.mlstatic.com/test.jpg\n"
        "MLBkeyboard,Teclado Mecânico,27990,"
        "https://www.mercadolivre.com.br/p/MLB222,\n",
        encoding="utf-8",
    )
    return csv_file


def search(client, query):
    return client.post(
        "/api/v1/discovery/search", headers={"x-admin-key": "test-admin-key"},
        json={"query": query, "limit": 10},
    )


def select(client, search_id, ids):
    return client.post(
        "/api/v1/discovery/select", headers={"x-admin-key": "test-admin-key"},
        json={"search_id": search_id, "source_item_ids": ids},
    )


def test_search_on_demand_and_select_without_whatsapp(tmp_path):
    catalog(tmp_path)
    fake = NeverSend()
    with TestClient(create_app(settings(tmp_path), publisher=fake)) as client:
        response = search(client, "mouse ELETRONICO")
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["source"] == "mercado_livre"
        assert result["query"] == "mouse ELETRONICO"
        assert len(result["items"]) == 1
        item = result["items"][0]
        assert item["source_item_id"] == "MLBmouse"
        assert item["price_cents"] == 19990
        assert item["image_url"] == "https://http2.mlstatic.com/test.jpg"
        assert item["promotion_verified"] is False
        assert item["price_history_available"] is False
        assert client.get("/health").json()["schema_version"] == 8
        assert client.get("/api/v1/offers", headers={"x-admin-key": "test-admin-key"}
                          ).json() == []
        created = select(client, result["search_id"], ["MLBmouse"])
        assert created.status_code == 200, created.text
        assert created.json()["selected"][0]["created"] is True
        offer_id = created.json()["selected"][0]["offer_id"]
        offer = client.get(
            f"/api/v1/offers/{offer_id}", headers={"x-admin-key": "test-admin-key"}
        ).json()
        assert offer["status"] == "DRAFT"
        assert offer["reference_price_cents"] is None
        assert offer["price_cents"] == item["price_cents"]
        assert offer["image_url"] == item["image_url"]
        assert offer["affiliate_url"] is None
        assert offer["product_url"] == item["product_url"]
        assert offer["image_sha256"] is None
        again = select(client, result["search_id"], ["MLBmouse"]).json()
        assert again["selected"][0]["created"] is False
        assert again["selected"][0]["offer_id"] == offer_id
        assert not fake.calls


def test_snapshot_prevents_silent_price_change(tmp_path):
    file = catalog(tmp_path)
    with TestClient(create_app(settings(tmp_path), publisher=NeverSend())) as client:
        result = search(client, "mouse").json()
        file.write_text(
            file.read_text().replace("19990", "99990"), encoding="utf-8"
        )
        response = select(client, result["search_id"], ["MLBmouse"])
        assert response.status_code == 200
        offer_id = response.json()["selected"][0]["offer_id"]
        detail = client.get(
            f"/api/v1/offers/{offer_id}", headers={"x-admin-key": "test-admin-key"}
        ).json()
        assert detail["price_cents"] == 19990


def test_search_without_matching_items_is_empty(tmp_path):
    catalog(tmp_path)
    with TestClient(create_app(settings(tmp_path), publisher=NeverSend())) as client:
        result = search(client, "monitor ultrawide")
        assert result.status_code == 200
        assert result.json()["items"] == []


def test_search_missing_catalog_and_auth(tmp_path):
    with TestClient(create_app(settings(tmp_path), publisher=NeverSend())) as client:
        assert client.post("/api/v1/discovery/search",
                           json={"query": "mouse"}).status_code == 401
        response = search(client, "mouse")
        assert response.status_code == 503
        assert "Catálogo local" in response.json()["detail"]


def test_invalid_selection_never_creates_partial_offer(tmp_path):
    catalog(tmp_path)
    with TestClient(create_app(settings(tmp_path), publisher=NeverSend())) as client:
        result = search(client, "mouse").json()
        unknown = select(client, result["search_id"], ["MLBmouse", "MLBnotInResults"])
        assert unknown.status_code == 422
        duplicate = select(client, result["search_id"], ["MLBmouse", "MLBmouse"])
        assert duplicate.status_code == 422
        bad_uuid = select(client, "not-a-uuid", ["MLBmouse"])
        assert bad_uuid.status_code == 422
        missing = select(client, "bcf87b44-646f-4901-8b0e-e20dab835acb", ["MLBmouse"])
        assert missing.status_code == 404
        assert client.get("/api/v1/offers", headers={"x-admin-key": "test-admin-key"}
                          ).json() == []


def test_expired_search_requires_fresh_request(tmp_path):
    catalog(tmp_path)
    config = settings(tmp_path)
    with TestClient(create_app(config, publisher=NeverSend())) as client:
        result = search(client, "mouse").json()
        with sqlite3.connect(config.sqlite_path) as conn:
            conn.execute(
                "UPDATE discovery_searches SET expires_at = ? WHERE id = ?",
                ((datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
                 result["search_id"]),
            )
        expired = select(client, result["search_id"], ["MLBmouse"])
        assert expired.status_code == 410
        assert not client.get("/api/v1/offers",
                              headers={"x-admin-key": "test-admin-key"}).json()


def test_existing_approved_offer_is_not_modified_or_republished(tmp_path):
    catalog(tmp_path)
    fake = NeverSend()
    with TestClient(create_app(settings(tmp_path), publisher=fake)) as client:
        first = search(client, "mouse").json()
        created = select(client, first["search_id"], ["MLBmouse"]).json()
        offer_id = created["selected"][0]["offer_id"]
        registered = client.post(
            f"/api/v1/offers/{offer_id}/affiliate-link",
            headers={"x-admin-key": "test-admin-key"},
            json={
                "affiliate_url": "https://meli.la/EXEMPLO",
                "product_match_confirmed": True,
            },
        )
        assert registered.status_code == 200
        approved = client.post(
            f"/api/v1/offers/{offer_id}/approve",
            headers={"x-admin-key": "test-admin-key"},
        )
        assert approved.status_code == 200
        next_search = search(client, "mouse").json()
        again = select(client, next_search["search_id"], ["MLBmouse"]).json()
        assert again["selected"][0] == {
            "source_item_id": "MLBmouse", "offer_id": offer_id,
            "status": "APPROVED", "created": False,
        }
        assert fake.calls == []


def test_preserves_existing_v3_data_after_upgrade(tmp_path):
    from pathlib import Path

    config = settings(tmp_path)
    store = config.sqlite_path
    with sqlite3.connect(store) as conn:
        migration_folder = Path(__file__).parent.parent / "app" / "migrations"
        for number, name in enumerate((
            "001_init.sql", "002_price_observations.sql", "003_offer_media.sql",
        ), start=1):
            conn.executescript((migration_folder / name).read_text())
            conn.execute(f"PRAGMA user_version = {number}")
        conn.execute(
            """INSERT INTO offers(id, source, source_item_id, title, price_cents,
            affiliate_url, status, created_at)
            VALUES('old', 'manual', 'old-sku', 'Oferta anterior', 15990,
                   'https://example.org/old', 'APPROVED', '2026-10-10T00:00:00+00:00')"""
        )
    with TestClient(create_app(config, publisher=NeverSend())) as client:
        assert client.get("/health").json()["schema_version"] == 8
        assert client.get("/api/v1/offers/old",
                          headers={"x-admin-key": "test-admin-key"}
                          ).json()["status"] == "APPROVED"
