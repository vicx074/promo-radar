import io
import sqlite3

from PIL import Image

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.media import optimize_jpeg


class FakePublisher:
    def __init__(self, failure=False):
        self.failure = failure
        self.calls = []

    def send_text(self, group_jid, text):
        self.calls.append(("text", group_jid, text))
        if self.failure:
            raise TimeoutError("Unknown delivery outcome")
        return "message-123"

    def send_image(self, group_jid, image_bytes, caption):
        self.calls.append(("image", group_jid, image_bytes, caption))
        if self.failure:
            raise TimeoutError("Unknown delivery outcome")
        return "message-image-123"


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


def test_image_requires_explicit_preparation_before_approval_and_sends_once(tmp_path):
    image = Image.new("RGB", (1500, 800), (20, 130, 200))
    stream = io.BytesIO()
    image.save(stream, "PNG")
    optimized = optimize_jpeg(stream.getvalue())
    fake = FakePublisher()
    image_payload = {
        **payload(), "source_item_id": "img-1",
        "image_url": "https://http2.mlstatic.com/test.jpg",
    }
    loader_calls = []

    def fake_loader(url):
        loader_calls.append(url)
        return optimized

    with TestClient(create_app(settings(tmp_path, True), fake, fake_loader)) as client:
        headers = {"x-admin-key": "admin-test-secret"}
        offer = client.post("/api/v1/offers", headers=headers, json=image_payload)
        assert offer.status_code == 201, offer.text
        offer_id = offer.json()["id"]
        assert offer.json()["status"] == "DRAFT"
        assert not fake.calls
        assert not loader_calls
        # Não aprovar antes de preparar, para manter imutabilidade da mídia.
        before = client.get(f"/api/v1/offers/{offer_id}/preview", headers=headers).json()
        assert before["image_ready"] is False
        assert before["image_url"] == image_payload["image_url"]
        assert client.post(f"/api/v1/offers/{offer_id}/publish", headers=headers).status_code == 409
        prepared = client.post(f"/api/v1/offers/{offer_id}/prepare-media", headers=headers)
        assert prepared.status_code == 200, prepared.text
        assert prepared.json()["size_bytes"] == optimized.size_bytes
        assert loader_calls == [image_payload["image_url"]]
        preview = client.get(f"/api/v1/offers/{offer_id}/preview", headers=headers).json()
        assert preview["image_ready"] is True
        assert preview["image"]["mime_type"] == "image/jpeg"
        assert client.post(f"/api/v1/offers/{offer_id}/approve", headers=headers).status_code == 200
        assert client.post(f"/api/v1/offers/{offer_id}/prepare-media",
                           headers=headers).status_code == 409
        sent = client.post(f"/api/v1/offers/{offer_id}/publish", headers=headers)
        assert sent.status_code == 200, sent.text
        assert sent.json()["status"] == "SENT"
        assert sent.json()["provider_message_id"] == "message-image-123"
        assert client.post(f"/api/v1/offers/{offer_id}/publish", headers=headers).status_code == 409
    assert len(fake.calls) == 1
    kind, recipient, content, caption = fake.calls[0]
    assert kind == "image"
    assert recipient == "123456@g.us"
    assert content == optimized.content
    assert "Teclado mecanico" in caption


def test_missing_prepared_image_blocks_after_approval_without_claim(tmp_path):
    fake = FakePublisher()
    image_payload = {**payload(), "image_url": "https://http2.mlstatic.com/test.jpg"}
    with TestClient(create_app(settings(tmp_path, True), fake)) as client:
        headers = {"x-admin-key": "admin-test-secret"}
        response = client.post("/api/v1/offers", json=image_payload, headers=headers)
        offer_id = response.json()["id"]
        assert approve(client, offer_id).status_code == 200
        cannot_publish = publish(client, offer_id)
        assert cannot_publish.status_code == 409
        assert "Imagem precisa" in cannot_publish.json()["detail"]
        assert not fake.calls
        assert client.get(f"/api/v1/offers/{offer_id}/preview",
                          headers=headers).json()["image_ready"] is False


def test_image_delivery_unknown_blocks_retry(tmp_path):
    optimized = optimize_jpeg(
        make_png_for_tests()
    )
    fake = FakePublisher(failure=True)
    image_payload = {**payload(), "image_url": "https://http2.mlstatic.com/test.jpg"}
    with TestClient(create_app(settings(tmp_path, True), fake, lambda _: optimized)) as client:
        headers = {"x-admin-key": "admin-test-secret"}
        offer_id = client.post("/api/v1/offers", json=image_payload, headers=headers).json()["id"]
        client.post(f"/api/v1/offers/{offer_id}/prepare-media", headers=headers)
        approve(client, offer_id)
        assert publish(client, offer_id).status_code == 502
        assert publish(client, offer_id).status_code == 409
        assert len(fake.calls) == 1


def make_png_for_tests():
    stream = io.BytesIO()
    Image.new("RGB", (220, 160), (0, 70, 120)).save(stream, "PNG")
    return stream.getvalue()
