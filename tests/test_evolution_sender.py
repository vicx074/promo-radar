import json

import httpx
import pytest

from app.evolution import EvolutionPublisher


def test_send_text_contract_and_message_id(monkeypatch):
    def handler(request):
        assert request.method == "POST"
        assert request.url.path == "/message/sendText/promocoes"
        assert request.headers["apikey"] == "private-secret"
        assert json.loads(request.content) == {
            "number": "123@g.us", "text": "*Publicidade:* oferta de teste"
        }
        return httpx.Response(201, json={"key": {"id": "message-123"}})

    original = httpx.Client
    monkeypatch.setattr(
        "app.evolution.httpx.Client",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )
    sender = EvolutionPublisher("http://evolution:8080", "private-secret", "promocoes")
    assert sender.send_text("123@g.us", "*Publicidade:* oferta de teste") == "message-123"


def test_send_text_raises_on_auth_error(monkeypatch):
    original = httpx.Client
    monkeypatch.setattr(
        "app.evolution.httpx.Client",
        lambda **kwargs: original(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(401, json={"error": "Unauthorized"})
            ),
            **kwargs,
        ),
    )
    sender = EvolutionPublisher("http://evolution:8080", "private-secret", "promocoes")
    with pytest.raises(httpx.HTTPStatusError):
        sender.send_text("123@g.us", "teste")
