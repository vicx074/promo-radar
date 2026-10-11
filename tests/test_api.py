import sqlite3

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


class FakePublisher:
    def __init__(self, failure=False):
        self.failure = failure
        self.calls = []

    def send_text(self, group_jid, text):
        self.calls.append((group_jid, text))
        if self.failure:
            raise TimeoutError("Unknown delivery outcome")
        return "message-123"


def settings(tmp_path, send_enabled=False):
    return Settings(tmp_path / "offers.db", "admin-test-secret", "http://example.test:8080",
                    "evolution-secret", "promocoes", "123456@g.us", send_enabled)


def payload():
    return {"source": "test-store", "source_item_id": "sku-123", "title": "Teclado mecanico",
            "price_cents": 15990, "reference_price_cents": 24990,
            "affiliate_url": "https://example.org/affiliate"}


def create(client):
    response = client.post("/api/v1/offers", json=payload(),
                           headers={"x-admin-key": "admin-test-secret"})
    assert response.status_code == 201, response.text
    return response.json()


def approve(client, offer_id):
    return client.post(f"/api/v1/offers/{offer_id}/approve",
                       headers={"x-admin-key": "admin-test-secret"})


def publish(client, offer_id):
    return client.post(f"/api/v1/offers/{offer_id}/publish",
                       headers={"x-admin-key": "admin-test-secret"})


def test_auth_validation_and_no_implicit_send(tmp_path):
    fake = FakePublisher()
    with TestClient(create_app(settings(tmp_path, True), fake)) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/api/v1/offers").status_code == 401
        assert client.post("/api/v1/offers", json=payload()).status_code == 401
        assert create(client)["status"] == "DRAFT"
        assert not fake.calls


def test_duplicate_and_approval_gate(tmp_path):
    fake = FakePublisher()
    with TestClient(create_app(settings(tmp_path, True), fake)) as client:
        offer = create(client)
        assert client.post("/api/v1/offers", json=payload(),
                           headers={"x-admin-key": "admin-test-secret"}).status_code == 409
        assert publish(client, offer["id"]).status_code == 409
        assert not fake.calls


def test_send_once_after_approval(tmp_path):
    fake = FakePublisher()
    with TestClient(create_app(settings(tmp_path, True), fake)) as client:
        offer = create(client)
        assert approve(client, offer["id"]).status_code == 200
        sent = publish(client, offer["id"])
        assert sent.status_code == 200
        assert sent.json()["status"] == "SENT"
        assert sent.json()["provider_message_id"] == "message-123"
        assert publish(client, offer["id"]).status_code == 409
        assert len(fake.calls) == 1


def test_unknown_delivery_is_not_retried(tmp_path):
    fake = FakePublisher(failure=True)
    with TestClient(create_app(settings(tmp_path, True), fake)) as client:
        offer = create(client)
        approve(client, offer["id"])
        assert publish(client, offer["id"]).status_code == 502
        assert publish(client, offer["id"]).status_code == 409
        assert len(fake.calls) == 1


def test_send_disabled_by_default(tmp_path):
    fake = FakePublisher()
    with TestClient(create_app(settings(tmp_path), fake)) as client:
        offer = create(client)
        approve(client, offer["id"])
        assert publish(client, offer["id"]).status_code == 409
        assert not fake.calls


def test_data_survives_app_restart(tmp_path):
    config = settings(tmp_path)
    with TestClient(create_app(config, FakePublisher())) as client:
        offer = create(client)
    with TestClient(create_app(config, FakePublisher())) as client:
        response = client.get(f"/api/v1/offers/{offer['id']}",
                              headers={"x-admin-key": "admin-test-secret"})
        assert response.status_code == 200
    with sqlite3.connect(config.sqlite_path) as conn:
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
