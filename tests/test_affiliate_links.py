"""Proteções para afiliação sem assumir rastreamento/comissão reais."""

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.affiliate import AffiliateLinkError, validate_official_link
from app.config import Settings
from app.main import create_app

ADMIN = {"x-admin-key": "secret-test"}
PRODUCT = "https://www.mercadolivre.com.br/p/MLB4567890"
AFFILIATE = "https://meli.la/EXEMPLO-NAO-REAL"


class FakePublisher:
    def __init__(self):
        self.calls = []

    def send_text(self, group_jid, text):
        self.calls.append(("text", group_jid, text))
        return "stub-message-id"

    def send_image(self, group_jid, content, caption):
        self.calls.append(("image", group_jid, caption))
        return "stub-image-id"


def settings(tmp_path, send_enabled=True):
    return Settings(
        sqlite_path=tmp_path / "offers.db", admin_api_key="secret-test",
        evolution_base_url="http://evolution:8080", evolution_api_key="dummy",
        evolution_instance="promocoes", whatsapp_group_id="test-group@g.us",
        send_enabled=send_enabled,
    )


def make_offer(client, **kwargs):
    payload = {
        "source": "mercado_livre",
        "source_item_id": "MLB4567890-p12000",
        "title": "Produto teste Mercado Livre",
        "price_cents": 12000,
        "product_url": PRODUCT,
    }
    payload.update(kwargs)
    return client.post("/api/v1/offers", headers=ADMIN, json=payload)


def attach_link(client, offer_id, link=AFFILIATE, confirmed=True):
    return client.post(
        f"/api/v1/offers/{offer_id}/affiliate-link",
        headers=ADMIN,
        json={"affiliate_url": link, "product_match_confirmed": confirmed},
    )


def test_no_affiliate_link_never_approved_or_published(tmp_path):
    fake = FakePublisher()
    with TestClient(create_app(settings(tmp_path), fake)) as client:
        item = make_offer(client)
        assert item.status_code == 201, item.text
        offer = item.json()
        assert offer["status"] == "DRAFT"
        assert offer["product_url"] == PRODUCT
        assert offer["affiliate_url"] is None
        assert offer["affiliate_status"] == "MISSING"
        preview = client.get(f"/api/v1/offers/{offer['id']}/preview", headers=ADMIN)
        assert preview.status_code == 200
        assert PRODUCT in preview.json()["message"]
        assert "sem rastreamento de afiliado" in preview.json()["message"]
        approved = client.post(f"/api/v1/offers/{offer['id']}/approve", headers=ADMIN)
        assert approved.status_code == 409
        assert client.post(f"/api/v1/offers/{offer['id']}/publish",
                           headers=ADMIN).status_code == 409
        assert fake.calls == []
        with sqlite3.connect(settings(tmp_path).sqlite_path) as conn:
            assert conn.execute("SELECT count(*) FROM publications").fetchone()[0] == 0


def test_registration_then_explicit_approval_and_publication(tmp_path):
    fake = FakePublisher()
    with TestClient(create_app(settings(tmp_path), fake)) as client:
        offer = make_offer(client).json()
        result = attach_link(client, offer["id"])
        assert result.status_code == 200, result.text
        assert result.json()["affiliate_url"] == AFFILIATE
        assert result.json()["product_url"] == PRODUCT
        assert result.json()["affiliate_status"] == "OPERATOR_SUBMITTED"
        assert client.post(f"/api/v1/offers/{offer['id']}/approve",
                           headers=ADMIN).status_code == 200
        sent = client.post(f"/api/v1/offers/{offer['id']}/publish", headers=ADMIN)
        assert sent.status_code == 200, sent.text
        assert sent.json()["status"] == "SENT"
        assert sent.json()["provider_message_id"] == "stub-message-id"
        assert len(fake.calls) == 1
        assert AFFILIATE in fake.calls[0][2]
        assert PRODUCT not in fake.calls[0][2]
        assert client.post(f"/api/v1/offers/{offer['id']}/publish",
                           headers=ADMIN).status_code == 409
        assert attach_link(client, offer["id"]).status_code == 409
        assert len(fake.calls) == 1


def test_registration_is_admin_only_and_requires_explicit_confirmation(tmp_path):
    with TestClient(create_app(settings(tmp_path), FakePublisher())) as client:
        offer = make_offer(client).json()
        assert client.post(
            f"/api/v1/offers/{offer['id']}/affiliate-link",
            json={"affiliate_url": AFFILIATE, "product_match_confirmed": True},
        ).status_code == 401
        assert attach_link(client, offer["id"], confirmed=False).status_code == 422
        assert client.get(f"/api/v1/offers/{offer['id']}", headers=ADMIN
                          ).json()["affiliate_url"] is None


@pytest.mark.parametrize("link", [
    "http://meli.la/example",
    "https://meli.la.evil.test/test",
    "https://evil.example/affiliate",
    "https://www.mercadolivre.com.br/p/MLB4567890",
    "https://www.mercadolivre.com.br.evil.test/sec/123",
    "https://user:password@meli.la/short",
    "https://meli.la:8080/short",
    "https://127.0.0.1/short",
    "https://meli.la/",
    "https://meli.la/one/two",
    "https://meli.la/short#fragment",
])
def test_fake_or_untrusted_affiliate_links_rejected(tmp_path, link):
    with pytest.raises(AffiliateLinkError):
        validate_official_link(link)
    with TestClient(create_app(settings(tmp_path), FakePublisher())) as client:
        offer = make_offer(client).json()
        assert attach_link(client, offer["id"], link).status_code == 422


def test_accepted_shapes_are_only_format_checks():
    assert validate_official_link(AFFILIATE) == AFFILIATE
    official_shape = "https://www.mercadolivre.com.br/sec/FICTICIO"
    assert validate_official_link(official_shape) == official_shape


def test_connection_is_disconnected_no_oauth_claim(tmp_path):
    with TestClient(create_app(settings(tmp_path), FakePublisher())) as client:
        assert client.get("/api/v1/affiliates/mercado-livre/status").status_code == 401
        r = client.get("/api/v1/affiliates/mercado-livre/status", headers=ADMIN)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "DISCONNECTED"
        assert data["connected"] is False
        assert data["auto_generation_available"] is False
        assert data["permissions"] == []


def test_migrates_approved_ml_with_publication_without_claiming_commission(tmp_path):
    db = settings(tmp_path).sqlite_path
    migrations = Path(__file__).parent.parent / "app" / "migrations"
    with sqlite3.connect(db) as conn:
        for n, path in enumerate((
            "001_init.sql", "002_price_observations.sql",
            "003_offer_media.sql", "004_search_snapshots.sql",
        ), start=1):
            conn.executescript((migrations / path).read_text())
            conn.execute(f"PRAGMA user_version = {n}")
        conn.execute(
            """INSERT INTO offers
            (id,source,source_item_id,title,price_cents,affiliate_url,status,created_at)
            VALUES('old','mercado_livre','x','Old offer',10000,?,'APPROVED',?)""",
            (PRODUCT, "2026-10-10T00:00:00+00:00"),
        )
        conn.execute(
            """INSERT INTO publications
            (id,offer_id,group_jid,status,created_at,updated_at)
            VALUES('publication-old','old','group@g.us','SENT',?,?)""",
            ("2026-10-10T00:00:00+00:00", "2026-10-10T00:00:00+00:00"),
        )
    fake = FakePublisher()
    with TestClient(create_app(settings(tmp_path), fake)) as client:
        offer = client.get("/api/v1/offers/old", headers=ADMIN).json()
        assert offer["product_url"] == PRODUCT
        assert offer["affiliate_url"] is None
        assert offer["status"] == "APPROVED"
        assert client.post("/api/v1/offers/old/publish", headers=ADMIN).status_code == 409
        assert attach_link(client, "old").status_code == 409
        assert client.get("/api/v1/publications/publication-old",
                          headers=ADMIN).json()["status"] == "SENT"
        assert fake.calls == []
    with sqlite3.connect(db) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 5
        assert conn.execute("SELECT COUNT(*) FROM publications").fetchone()[0] == 1
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_non_ml_legacy_behavior_kept(tmp_path):
    with TestClient(create_app(settings(tmp_path), FakePublisher())) as client:
        response = client.post(
            "/api/v1/offers",
            headers=ADMIN,
            json={"source": "test-store", "source_item_id": "other-1",
                  "title": "Produto externo", "price_cents": 14990,
                  "affiliate_url": "https://example.org/product"},
        )
        assert response.status_code == 201, response.text
        assert response.json()["affiliate_url"] == "https://example.org/product"
        assert response.json()["affiliate_status"] == "LEGACY_UNVERIFIED"
