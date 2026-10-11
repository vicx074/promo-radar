import sqlite3

from app.backup import backup_database
from app.storage import SQLiteStore


def test_online_backup_has_valid_database(tmp_path):
    source = tmp_path / "data" / "offers.db"
    store = SQLiteStore(source)
    store.initialize()
    created = store.create_offer({
        "source": "store", "source_item_id": "abc", "title": "Teclado",
        "price_cents": 15990, "reference_price_cents": None,
        "affiliate_url": "https://example.org/ref",
    })
    backup_path = tmp_path / "backups" / "backup.db"
    backup_database(source, backup_path)
    with sqlite3.connect(backup_path) as conn:
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert conn.execute("SELECT id FROM offers").fetchone()[0] == created["id"]
