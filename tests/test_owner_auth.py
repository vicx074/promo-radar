"""Integração segura em ambiente de testes. Não utiliza serviços reais nem senha de produção."""
import sqlite3

import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient

from app.auth import OwnerAuth, verify_origin
from app.config import Settings
from app.main import create_app
from app.storage import SQLiteStore

PASSWORD = "uma-senha-de-teste-com-mais-de-14"


def config(tmp_path, **kwargs):
    data = {
        "sqlite_path": tmp_path / "offers.db",
        "admin_api_key": "deprecated-cli-key",
        "evolution_base_url": "http://localhost:8080",
        "evolution_api_key": "fake",
        "evolution_instance": "promocoes",
        "whatsapp_group_id": "",
        "send_enabled": False,
        "owner_password_hash": PasswordHasher(time_cost=1, memory_cost=1024).hash(PASSWORD),
        "allow_admin_api_key": False,
        "session_cookie_secure": False,
    }
    data.update(kwargs)
    return Settings(**data)


ORIGIN = {"Origin": "http://testserver"}


def login(client, password=PASSWORD, headers=None):
    return client.post(
        "/api/v1/auth/login",
        json={"password": password},
        headers=ORIGIN if headers is None else headers,
    )


def test_owner_session_login_protects_all_routes(tmp_path):
    with TestClient(create_app(config(tmp_path))) as client:
        assert client.get("/api/v1/offers").status_code == 401
        assert client.get(
            "/api/v1/offers", headers={"x-admin-key": "deprecated-cli-key"}
        ).status_code == 401
        assert login(client, "senha-errada").status_code == 401
        response = login(client)
        assert response.status_code == 200, response.text
        assert response.json()["authenticated"] is True
        assert "csrf_token" in response.json()
        header = response.headers["set-cookie"].lower()
        assert "httponly" in header
        assert "samesite=strict" in header
        assert "path=/" in header
        assert client.get("/api/v1/offers").status_code == 200
        csrf = client.get("/api/v1/auth/session").json()["csrf_token"]
        assert csrf == response.json()["csrf_token"]
        assert client.post(
            "/api/v1/discovery/search", json={"query": "mouse"}
        ).status_code == 403
        assert client.post(
            "/api/v1/discovery/search",
            headers={"Origin": "http://evil.test", "x-csrf-token": csrf},
            json={"query": "mouse"},
        ).status_code == 403
        assert client.post(
            "/api/v1/discovery/search",
            headers={**ORIGIN, "x-csrf-token": "wrong"},
            json={"query": "mouse"},
        ).status_code == 403
        valid = client.post(
            "/api/v1/discovery/search",
            headers={**ORIGIN, "x-csrf-token": csrf},
            json={"query": "mouse"},
        )
        assert valid.status_code == 503  # passou autenticação; CSV ainda não existe
        assert client.post("/api/v1/auth/logout", headers=ORIGIN).status_code == 403
        assert client.post(
            "/api/v1/auth/logout", headers={**ORIGIN, "x-csrf-token": csrf}
        ).status_code == 200
        assert client.get("/api/v1/offers").status_code == 401


def test_one_active_session_and_restart_recovery(tmp_path):
    cfg = config(tmp_path)
    with TestClient(create_app(cfg)) as first:
        assert login(first).status_code == 200
        first_cookie = first.cookies.get("promo_session")
    with TestClient(create_app(cfg)) as second:
        assert second.get("/api/v1/auth/session", cookies={"promo_session": first_cookie}
                          ).status_code == 200
        assert login(second).status_code == 200
        assert second.get("/api/v1/auth/session").status_code == 200
        assert second.get("/api/v1/auth/session", cookies={"promo_session": first_cookie}
                          ).status_code == 401
    with sqlite3.connect(cfg.sqlite_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM owner_sessions").fetchone()[0] == 1
        assert conn.execute("SELECT token_hash FROM owner_sessions").fetchone()[0][0] != first_cookie


def test_expired_or_idle_session_is_rejected(tmp_path):
    cfg = config(tmp_path)
    with TestClient(create_app(cfg)) as client:
        assert login(client).status_code == 200
        with sqlite3.connect(cfg.sqlite_path) as conn:
            conn.execute("UPDATE owner_sessions SET last_seen_at = last_seen_at - 1900")
        assert client.get("/api/v1/offers").status_code == 401
        assert login(client).status_code == 200
        with sqlite3.connect(cfg.sqlite_path) as conn:
            conn.execute("UPDATE owner_sessions SET expires_at=0")
        assert client.get("/api/v1/auth/session").status_code == 401


def test_rate_limit_persists_between_app_restarts(tmp_path):
    cfg = config(tmp_path)
    with TestClient(create_app(cfg)) as client:
        for _ in range(5):
            assert login(client, "invalida").status_code == 401
        response = login(client)
        assert response.status_code == 429
        assert int(response.headers["retry-after"]) > 0
    with TestClient(create_app(cfg)) as client:
        assert login(client).status_code == 429


def test_secure_cookie_and_https_origin_on_vps(tmp_path):
    cfg = config(tmp_path, session_cookie_secure=True, single_owner_mode=True)
    with TestClient(create_app(cfg), base_url="https://testserver") as client:
        assert login(client, headers={"Origin": "http://testserver"}).status_code == 403
        response = login(client, headers={"Origin": "https://testserver"})
        assert response.status_code == 200
        assert "secure" in response.headers["set-cookie"].lower()
        assert "__Host-promo_session" in response.headers["set-cookie"]
        assert client.get("/api/v1/offers").status_code == 200


@pytest.mark.parametrize("override", [
    {"owner_password_hash": ""},
    {"session_cookie_secure": False},
    {"allow_admin_api_key": True},
])
def test_vps_fail_closed_on_unsafe_configuration(tmp_path, override):
    cfg = config(tmp_path, single_owner_mode=True, **override)
    with pytest.raises(RuntimeError):
        with TestClient(create_app(cfg)):
            pass


def test_token_digest_only_and_expiry_semantics(tmp_path):
    store = SQLiteStore(tmp_path / "state.db")
    store.initialize()
    auth = OwnerAuth(store)
    raw, _ = auth.issue_session(now=100000)
    with store.connect() as conn:
        row = conn.execute("SELECT token_hash, csrf_token FROM owner_sessions").fetchone()
    assert raw not in row["token_hash"]
    assert len(row["token_hash"]) == 64
    assert auth.read_session(raw, now=100001) is not None
    assert auth.read_session(raw, now=101801) is None


def test_strict_origin_verification():
    assert verify_origin("https://node.tailnet.ts.net", "node.tailnet.ts.net", secure=True)
    assert not verify_origin("http://node.tailnet.ts.net", "node.tailnet.ts.net", secure=True)
    assert not verify_origin("https://node.tailnet.ts.net.evil.tld",
                             "node.tailnet.ts.net", secure=True)
    assert not verify_origin(None, "node.tailnet.ts.net", secure=True)
