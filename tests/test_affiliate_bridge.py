"""Contrato do vínculo por conector local: sem Chrome/ML/Apify/WhatsApp reais."""
import sqlite3

from fastapi.testclient import TestClient

from app.affiliate_bridge import matching_product
from app.config import Settings
from app.main import create_app
from app.storage import SQLiteStore

TOKEN = "t" * 64
OWNER = {"x-admin-key": "test-admin-key"}
AGENT = {"Authorization": "Bearer " + TOKEN}
PRODUCT = "https://www.mercadolivre.com.br/notebook/p/MLB123456"
OTHER = "https://www.mercadolivre.com.br/cadeira/p/MLB999999"


def settings(tmp_path, *, auto=True):
    return Settings(
        sqlite_path=tmp_path / "offers.db", admin_api_key="test-admin-key",
        evolution_base_url="http://localhost:8080", evolution_api_key="test-key",
        evolution_instance="promocoes", whatsapp_group_id="", send_enabled=False,
        affiliate_bridge_token=TOKEN, affiliate_auto_queue=auto,
    )


def catalog(tmp_path):
    folder = tmp_path / "import"
    folder.mkdir(exist_ok=True)
    (folder / "catalogo.csv").write_text(
        "source_item_id,title,price_cents,product_url,image_url\n"
        f"MLB123456,Notebook para teste,259990,{PRODUCT},\n",
        encoding="utf-8",
    )


def add_offer(client):
    result = client.post("/api/v1/discovery/search",
                         headers=OWNER, json={"query": "notebook", "limit": 10})
    assert result.status_code == 200, result.text
    data = result.json()
    response = client.post("/api/v1/discovery/select", headers=OWNER, json={
        "search_id": data["search_id"],
        "source_item_ids": ["MLB123456"],
    })
    assert response.status_code == 200, response.text
    return response.json()["selected"][0]["offer_id"]


def test_automatic_link_generation_queue_and_match(tmp_path):
    catalog(tmp_path)
    with TestClient(create_app(settings(tmp_path))) as client:
        offer_id = add_offer(client)
        offer = client.get(f"/api/v1/offers/{offer_id}", headers=OWNER).json()
        assert offer["affiliate_job_status"] == "PENDING"
        assert offer["affiliate_url"] is None
        assert offer["status"] == "DRAFT"
        assert client.get("/health").json()["schema_version"] == 8

        assert client.post("/api/v1/affiliate-agent/claim").status_code == 401
        assert client.post("/api/v1/affiliate-agent/claim",
                           headers={"Authorization": "Bearer wrong"}).status_code == 401
        assert client.get("/api/v1/affiliate-bridge/status").status_code == 401

        claimed = client.post("/api/v1/affiliate-agent/claim", headers=AGENT)
        assert claimed.status_code == 200
        job = claimed.json()["job"]
        assert job["offer_id"] == offer_id
        assert job["product_url"] == PRODUCT
        assert len(job["claim_token"]) > 20
        assert client.post("/api/v1/affiliate-agent/claim",
                           headers=AGENT).json()["job"] is None

        bad_claim = client.post("/api/v1/affiliate-agent/complete", headers=AGENT,
                                json={"job_id": job["job_id"], "claim_token": "x"*40,
                                      "affiliate_url": "https://meli.la/LINKTEST",
                                      "origin_url": PRODUCT})
        assert bad_claim.status_code == 409
        ok = client.post("/api/v1/affiliate-agent/complete", headers=AGENT,
                         json={"job_id": job["job_id"], "claim_token": job["claim_token"],
                               "affiliate_url": "https://meli.la/LINKTEST",
                               "origin_url": PRODUCT})
        assert ok.status_code == 200, ok.text
        assert ok.json()["status"] == "LINKED"
        updated = client.get(f"/api/v1/offers/{offer_id}", headers=OWNER).json()
        assert updated["affiliate_url"] == "https://meli.la/LINKTEST"
        assert updated["affiliate_status"] == "LOCAL_BROWSER_BRIDGE"
        assert updated["affiliate_job_status"] == "LINKED"
        # Gerar link não concede aprovação nem aciona WhatsApp.
        assert updated["status"] == "DRAFT"
        assert client.get("/api/v1/offers", headers=OWNER).json()[0]["status"] == "DRAFT"
        assert client.post("/api/v1/affiliate-agent/complete", headers=AGENT, json={
            "job_id": job["job_id"], "claim_token": job["claim_token"],
            "affiliate_url": "https://meli.la/LINKTEST", "origin_url": PRODUCT
        }).status_code == 409


def test_mismatch_fails_safely_and_manual_retry(tmp_path):
    catalog(tmp_path)
    with TestClient(create_app(settings(tmp_path))) as client:
        oid = add_offer(client)
        job = client.post("/api/v1/affiliate-agent/claim", headers=AGENT).json()["job"]
        response = client.post("/api/v1/affiliate-agent/complete", headers=AGENT,
                               json={"job_id": job["job_id"], "claim_token": job["claim_token"],
                                     "affiliate_url": "https://meli.la/EXEMPLO",
                                     "origin_url": OTHER})
        assert response.json()["error_code"] == "PRODUCT_MISMATCH"
        assert client.get(f"/api/v1/offers/{oid}", headers=OWNER).json()["affiliate_url"] is None
        retry = client.post(f"/api/v1/offers/{oid}/affiliate-link/queue", headers=OWNER)
        assert retry.status_code == 200
        assert retry.json()["status"] == "PENDING"
        assert client.post("/api/v1/affiliate-agent/claim", headers=AGENT).json()["job"]


def test_manual_link_cancels_pending_agent_and_agent_cannot_publish(tmp_path):
    catalog(tmp_path)
    with TestClient(create_app(settings(tmp_path))) as client:
        oid = add_offer(client)
        job = client.post("/api/v1/affiliate-agent/claim", headers=AGENT).json()["job"]
        manual = client.post(f"/api/v1/offers/{oid}/affiliate-link", headers=OWNER,
                             json={"affiliate_url": "https://meli.la/MANUAL",
                                   "product_match_confirmed": True})
        assert manual.status_code == 200, manual.text
        assert manual.json()["affiliate_job_status"] == "CANCELLED"
        assert client.post("/api/v1/affiliate-agent/complete", headers=AGENT,
                           json={"job_id": job["job_id"], "claim_token": job["claim_token"],
                                 "affiliate_url": "https://meli.la/OTHER",
                                 "origin_url": PRODUCT}).status_code == 409
        assert client.post(f"/api/v1/offers/{oid}/publish", headers=AGENT).status_code == 401


def test_inactive_agent_and_offline_workstation(tmp_path):
    catalog(tmp_path)
    with TestClient(create_app(settings(tmp_path))) as client:
        oid = add_offer(client)
        status = client.get("/api/v1/affiliate-bridge/status", headers=OWNER).json()
        assert status["configured"] is True
        assert status["worker_online"] is False
        assert status["jobs"]["PENDING"] == 1
        assert client.post("/api/v1/affiliate-agent/heartbeat", headers=AGENT).status_code == 200
        assert client.get("/api/v1/affiliate-bridge/status",
                          headers=OWNER).json()["worker_online"] is True
        assert client.get(f"/api/v1/offers/{oid}", headers=OWNER).json()["status"] == "DRAFT"


def test_claim_timeout_never_retries_external_action_without_operator(tmp_path):
    catalog(tmp_path)
    cfg = settings(tmp_path)
    with TestClient(create_app(cfg)) as client:
        oid = add_offer(client)
        first = client.post("/api/v1/affiliate-agent/claim", headers=AGENT).json()["job"]
        with sqlite3.connect(cfg.sqlite_path) as db:
            db.execute("UPDATE affiliate_link_jobs SET lease_expires_at=0 WHERE id=?",
                       (first["job_id"],))
        assert client.post("/api/v1/affiliate-agent/claim", headers=AGENT).json()["job"] is None
        assert client.get(f"/api/v1/offers/{oid}",
                          headers=OWNER).json()["affiliate_job_status"] == "FAILED"
        assert client.post("/api/v1/affiliate-agent/complete", headers=AGENT, json={
            "job_id": first["job_id"], "claim_token": first["claim_token"],
            "affiliate_url": "https://meli.la/OLD", "origin_url": PRODUCT
        }).status_code == 409


def test_can_disable_auto_queue_then_request_individually(tmp_path):
    catalog(tmp_path)
    with TestClient(create_app(settings(tmp_path, auto=False))) as client:
        oid = add_offer(client)
        assert client.get(f"/api/v1/offers/{oid}",
                          headers=OWNER).json()["affiliate_job_status"] is None
        assert client.post(f"/api/v1/offers/{oid}/affiliate-link/queue",
                           headers=OWNER).status_code == 200


def test_browser_bridge_destination_validation(tmp_path):
    assert matching_product(PRODUCT, PRODUCT + "?tracking=abc")
    assert matching_product(
        "https://www.mercadolivre.com.br/outra/p/MLB123456",
        "https://mercadolivre.com.br/versao/up/MLB123456",
    )
    assert not matching_product(PRODUCT, OTHER)
    assert not matching_product(PRODUCT, "https://mercadolivre.com.br.evil.org/foo")
    assert not matching_product(PRODUCT, "https://evil.org/foo")


def test_bridge_migration_from_schema_v6_keeps_offers(tmp_path):
    from pathlib import Path
    db = tmp_path / "offers.db"
    migration_dir = Path(__file__).resolve().parents[1] / "app" / "migrations"
    with sqlite3.connect(db) as conn:
        for idx, name in enumerate([
            "001_init.sql", "002_price_observations.sql",
            "003_offer_media.sql", "004_search_snapshots.sql",
            "005_affiliate_links.sql", "006_owner_sessions.sql",
        ], start=1):
            conn.executescript((migration_dir / name).read_text())
            conn.execute(f"PRAGMA user_version={idx}")
        conn.execute(
            """INSERT INTO offers(id, source, source_item_id, title, price_cents,
               affiliate_url, status, created_at) VALUES
               ('old','mercado_livre','MLB_OLD','Produto anterior',15990,
                'https://www.mercadolivre.com.br/p/MLB_OLD','DRAFT','2026-10-10')"""
        )
    store = SQLiteStore(db)
    store.initialize()
    assert store.get_offer("old")["affiliate_link_url"] is None
    with sqlite3.connect(db) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 8
