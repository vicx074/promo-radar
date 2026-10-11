import httpx
import pytest

from app.evolution_admin import EvolutionAdmin


def mock_api(handler):
    return EvolutionAdmin(
        "http://evolution:8080", "private-secret", "promocoes",
        transport=httpx.MockTransport(handler),
    )


def test_create_instance_uses_contract_without_exposing_qr():
    def handler(request):
        assert request.url.path == "/instance/create"
        assert request.method == "POST"
        assert request.headers["apikey"] == "private-secret"
        assert b'"integration":"WHATSAPP-BAILEYS"' in request.content
        return httpx.Response(201, json={
            "instance": {"instanceName": "promocoes"},
            "qrcode": {"base64": "private-qr"},
        })
    assert mock_api(handler).create_instance() == "promocoes"


def test_connection_state():
    def handler(request):
        assert request.url.path == "/instance/connectionState/promocoes"
        return httpx.Response(200, json={"instance": {"state": "open"}})
    assert mock_api(handler).connection_state() == "open"


def test_list_groups_filters_non_groups():
    def handler(request):
        assert request.url.path == "/group/fetchAllGroups/promocoes"
        assert request.url.params["getParticipants"] == "false"
        assert request.extensions["timeout"]["read"] == 90.0
        assert request.extensions["timeout"]["connect"] == 5.0
        return httpx.Response(200, json=[
            {"id": "123@g.us", "subject": "Teste"},
            {"id": "456@g.us"},
            {"id": "555@s.whatsapp.net", "subject": "Contato"},
        ])
    assert mock_api(handler).list_groups() == [
        ("123@g.us", "Teste"), ("456@g.us", "Sem nome"),
    ]


def test_http_error_does_not_leak_response_body():
    def handler(request):
        return httpx.Response(401, text="private-secret private-qr")
    with pytest.raises(RuntimeError, match="HTTP 401") as caught:
        mock_api(handler).connection_state()
    assert "private-secret" not in str(caught.value)
    assert "private-qr" not in str(caught.value)


def test_rejects_instance_path_traversal():
    with pytest.raises(ValueError):
        EvolutionAdmin("http://evolution:8080", "private-secret", "../../other")


def test_group_read_timeout_reports_type_without_leaking_sensitive_details():
    def handler(request):
        raise httpx.ReadTimeout("private-secret private-qr", request=request)

    with pytest.raises(RuntimeError, match="ReadTimeout") as caught:
        mock_api(handler).list_groups()
    assert "private-secret" not in str(caught.value)
    assert "private-qr" not in str(caught.value)


def test_groups_connection_error_reports_type_without_url():
    def handler(request):
        raise httpx.ConnectError("private-secret private-qr", request=request)

    with pytest.raises(RuntimeError, match="ConnectError") as caught:
        mock_api(handler).list_groups()
    assert "private-secret" not in str(caught.value)
    assert "private-qr" not in str(caught.value)
