import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.domain import OfferStatus, PublicationStatus


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class DuplicateOffer(Exception):
    pass


class AlreadyPublishedOrInProgress(Exception):
    pass


class SQLiteStore:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(str(self.path), timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 10000")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if version == 0:
                script = Path(__file__).parent.joinpath("migrations/001_init.sql").read_text()
                conn.executescript(script)
                conn.execute("PRAGMA user_version = 1")
                version = 1
            if version == 1:
                migration = Path(__file__).parent.joinpath(
                    "migrations/002_price_observations.sql"
                ).read_text()
                conn.executescript(migration)
                conn.execute("PRAGMA user_version = 2")
                version = 2
            if version == 2:
                migration = Path(__file__).parent.joinpath(
                    "migrations/003_offer_media.sql"
                ).read_text()
                conn.executescript(migration)
                conn.execute("PRAGMA user_version = 3")
            elif version != 3:
                raise RuntimeError(f"Versão do SQLite incompatível: {version}")

    def health(self) -> bool:
        with self.connect() as conn:
            return conn.execute("SELECT 1").fetchone()[0] == 1

    def create_offer(self, data: dict) -> dict:
        offer_id = str(uuid4())
        try:
            with self.connect() as conn:
                conn.execute(
                    """INSERT INTO offers
                    (id, source, source_item_id, title, price_cents, reference_price_cents,
                     affiliate_url, image_url, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (offer_id, data["source"], data["source_item_id"], data["title"],
                     data["price_cents"], data.get("reference_price_cents"),
                     data["affiliate_url"], data.get("image_url"),
                     OfferStatus.DRAFT, utc_now()),
                )
        except sqlite3.IntegrityError as exc:
            raise DuplicateOffer from exc
        return self.get_offer(offer_id)

    def get_offer(self, offer_id: str) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM offers WHERE id = ?", (offer_id,)).fetchone()
            return dict(row) if row else None

    def list_offers(self, limit: int = 50) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM offers ORDER BY created_at DESC, id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(row) for row in rows]

    def approve(self, offer_id: str) -> dict | None:
        with self.connect() as conn:
            conn.execute(
                """UPDATE offers SET status = ?, approved_at = ?
                WHERE id = ? AND status = ?""",
                (OfferStatus.APPROVED, utc_now(), offer_id, OfferStatus.DRAFT),
            )
        return self.get_offer(offer_id)

    def claim_publication(self, offer_id: str, group_jid: str) -> dict:
        publication_id = str(uuid4())
        now = utc_now()
        try:
            with self.connect() as conn:
                conn.execute(
                    """INSERT INTO publications
                    (id, offer_id, group_jid, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (publication_id, offer_id, group_jid, PublicationStatus.SENDING, now, now),
                )
        except sqlite3.IntegrityError as exc:
            raise AlreadyPublishedOrInProgress from exc
        return self.get_publication(publication_id)

    def finish_publication(
        self, publication_id: str, status: PublicationStatus,
        provider_message_id: str | None = None, error_summary: str | None = None,
    ) -> dict:
        assert status in {PublicationStatus.SENT, PublicationStatus.UNKNOWN}
        with self.connect() as conn:
            conn.execute(
                """UPDATE publications SET status = ?, provider_message_id = ?,
                error_summary = ?, updated_at = ? WHERE id = ? AND status = ?""",
                (status, provider_message_id, error_summary, utc_now(),
                 publication_id, PublicationStatus.SENDING),
            )
        return self.get_publication(publication_id)

    def get_publication(self, publication_id: str) -> dict | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM publications WHERE id = ?", (publication_id,)
            ).fetchone()
            return dict(row) if row else None

    def attach_media(self, offer_id: str, image: dict) -> dict | None:
        """Guarda o JPEG otimizado; não altera oferta já aprovada."""
        with self.connect() as conn:
            current = conn.execute(
                "SELECT status FROM offers WHERE id = ?", (offer_id,)
            ).fetchone()
            if not current or current["status"] != OfferStatus.DRAFT:
                return None
            conn.execute(
                """INSERT OR IGNORE INTO media_assets
                (sha256, relative_path, size_bytes, width, height, mime_type, created_at)
                VALUES (?, ?, ?, ?, ?, 'image/jpeg', ?)""",
                (image["sha256"], image["relative_path"], image["size_bytes"],
                 image["width"], image["height"], utc_now()),
            )
            conn.execute(
                "UPDATE offers SET image_sha256 = ? WHERE id = ? AND status = ?",
                (image["sha256"], offer_id, OfferStatus.DRAFT),
            )
        return self.get_offer(offer_id)

    def media_for_offer(self, offer_id: str) -> dict | None:
        with self.connect() as conn:
            row = conn.execute(
                """SELECT m.* FROM media_assets m JOIN offers o
                ON o.image_sha256 = m.sha256 WHERE o.id = ?""",
                (offer_id,),
            ).fetchone()
            return dict(row) if row else None
