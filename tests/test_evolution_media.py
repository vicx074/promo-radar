"""Validação do contrato JSON de envio da Evolution, sem WhatsApp real."""

import base64
import json

import httpx
import pytest

from app.evolution import EvolutionPublisher


def test_media_uses_sendmedia_with_caption_as_one_message(monkeypatch):
    calls = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert request.method == "POST"
        assert request.url.path == "/message/sendMedia/promocoes"
        assert request.headers["apikey"] == "example-secret"
        data = json.loads(request.content)
        assert data["number"] == "123456@g.us"
        assert data["mediatype"] == "image"
        assert data["mimetype"] == "image/jpeg"
        assert data["filename"] == "oferta.jpg"
        assert "fileName" not in data
        assert data["caption"] == "*Oferta* R$ 10,00"
        assert base64.b64decode(data["media"], validate=True) == b"\xff\xd8img"
        return httpx.Response(201, json={"key": {"id": "3EB0test-id"}})

    original = httpx.Client
    monkeypatch.setattr(
        "app.evolution.httpx.Client",
        lambda **kwargs: original(transport=httpx.MockTransport(handle)),
    )
    publisher = EvolutionPublisher("http://evolution:8080", "example-secret", "promocoes")
    result = publisher.send_image("123456@g.us", b"\xff\xd8img", "*Oferta* R$ 10,00")
    assert result == "3EB0test-id"
    assert len(calls) == 1


def test_media_raises_on_provider_error(monkeypatch):
    original = httpx.Client
    monkeypatch.setattr(
        "app.evolution.httpx.Client",
        lambda **kwargs: original(
            transport=httpx.MockTransport(lambda _: httpx.Response(500))
        ),
    )
    publisher = EvolutionPublisher("http://evolution:8080", "example-secret", "promocoes")
    with pytest.raises(httpx.HTTPStatusError):
        publisher.send_image("123456@g.us", b"jpeg", "caption")
