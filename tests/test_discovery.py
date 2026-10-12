import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from app.discovery import ingest_catalog, read_catalog
from app.storage import SQLiteStore

URL = "https://www.mercadolivre.com.br/p/MLB1234567890"
START = datetime(2026, 10, 11, 10, tzinfo=UTC)


def write_catalog(tmp_path, price, *, url=URL, item_id="MLB1234567890", title="Mouse teste"):
    file = tmp_path / "catalogo.csv"
    file.write_text(
        "source_item_id,title,price_cents,product_url\n"
        f"{item_id},{title},{price},{url}\n",
        encoding="utf-8",
    )
    return file


def test_creates_draft_only_after_two_baselines_and_real_drop(tmp_path):
    store = SQLiteStore(tmp_path / "data" / "offers.db")
    a = ingest_catalog(write_catalog(tmp_path, 20000), store, now=START)
    b = ingest_catalog(
        write_catalog(tmp_path, 20000), store, now=START + timedelta(hours=1)
    )
    c = ingest_catalog(
        write_catalog(tmp_path, 16000), store, now=START + timedelta(hours=2)
    )
    assert a.drafts_created == b.drafts_created == 0
    assert c.drafts_created == 1
    offer = store.list_offers()[0]
    assert offer["status"] == "DRAFT"
    assert offer["source"] == "mercado_livre"
    assert offer["price_cents"] == 16000
    assert offer["reference_price_cents"] == 20000
    assert offer["affiliate_url"] is None
    assert offer["product_url"] == URL
    assert offer["approved_at"] is None
    with store.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM price_observations").fetchone()[0] == 3
        assert conn.execute("SELECT COUNT(*) FROM publications").fetchone()[0] == 0


def test_same_hour_and_same_price_deduplicated(tmp_path):
    store = SQLiteStore(tmp_path / "offers.db")
    catalog = write_catalog(tmp_path, 20000)
    assert ingest_catalog(catalog, store, now=START).observed == 1
    same = ingest_catalog(catalog, store, now=START + timedelta(minutes=30))
    assert same.observed == 0
    assert same.skipped_hour == 1
    assert store.list_offers() == []


def test_previous_minimum_not_advertised_reference_and_same_drop_no_repeat(tmp_path):
    store = SQLiteStore(tmp_path / "offers.db")
    for i, price in enumerate((20000, 19500, 16500, 16500, 13500)):
        result = ingest_catalog(
            write_catalog(tmp_path, price),
            store,
            now=START + timedelta(hours=i),
        )
    assert result.drafts_created == 1
    offers = store.list_offers()
    assert len(offers) == 2
    assert offers[0]["reference_price_cents"] == 16500
    assert offers[0]["price_cents"] == 13500
    assert offers[1]["reference_price_cents"] == 19500
    assert offers[1]["price_cents"] == 16500


def test_ignores_small_price_drop(tmp_path):
    store = SQLiteStore(tmp_path / "offers.db")
    for i, price in enumerate((10000, 10000, 9400)):
        result = ingest_catalog(
            write_catalog(tmp_path, price),
            store, now=START + timedelta(hours=i),
        )
    assert result.drafts_created == 0
    assert store.list_offers() == []


@pytest.mark.parametrize("url", [
    "http://www.mercadolivre.com.br/p/MLB123",
    "https://mercadolivre.com.br.evil.test/product",
    "https://evil.test/p/MLB123",
    "https://user:pass@mercadolivre.com.br/p/MLB123",
    "https://mercadolivre.com.br:8000/p/MLB123",
    "https://mercadolivre.com.br/",
])
def test_rejects_bad_urls(tmp_path, url):
    file = write_catalog(tmp_path, 10000, url=url)
    with pytest.raises(ValueError, match="URL HTTPS"):
        read_catalog(file)


def test_malformed_catalog_rejected_before_database_mutation(tmp_path):
    store = SQLiteStore(tmp_path / "offers.db")
    file = write_catalog(tmp_path, 10000, title="AB")
    with pytest.raises(ValueError, match="título"):
        ingest_catalog(file, store, now=START)
    assert not store.path.exists()


def test_requires_distinct_id_and_numeric_integer_cents(tmp_path):
    file = write_catalog(tmp_path, "199.90")
    with pytest.raises(ValueError, match="centavos"):
        read_catalog(file)
    file.write_text(
        "source_item_id,title,price_cents,product_url\n"
        f"MLB1234567890,Mouse teste,10000,{URL}\n"
        f"MLB1234567890,Mouse teste,10000,{URL}\n", encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicado"):
        read_catalog(file)


def test_upgrades_existing_v1_database_without_deleting_offers(tmp_path):
    store = SQLiteStore(tmp_path / "offers.db")
    store.path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(store.path) as conn:
        migration = (
            __import__("pathlib").Path(__file__).parent.parent
            / "app" / "migrations" / "001_init.sql"
        ).read_text()
        conn.executescript(migration)
        conn.execute("PRAGMA user_version=1")
        conn.execute(
            """INSERT INTO offers
            (id, source, source_item_id, title, price_cents, affiliate_url, status,
            created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("old-offer", "manual", "old-id", "Item anterior", 10000,
             "https://example.org", "APPROVED", "2026-10-10T00:00:00+00:00"),
        )
    store.initialize()
    assert store.get_offer("old-offer")["status"] == "APPROVED"
    with store.connect() as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 7
        assert conn.execute("SELECT COUNT(*) FROM price_observations").fetchone()[0] == 0
