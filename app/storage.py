import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from app.domain import OfferStatus, PublicationStatus


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class DuplicateOffer(Exception):
    pass


class AffiliateLinkRequired(Exception):
    pass


class AffiliateOfferNotEditable(Exception):
    pass


class AlreadyPublishedOrInProgress(Exception):
    pass


class SearchSnapshotNotFound(Exception):
    pass


class SearchSnapshotExpired(Exception):
    pass


class SearchSelectionInvalid(Exception):
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
                version = 3
            if version == 3:
                migration = Path(__file__).parent.joinpath(
                    "migrations/004_search_snapshots.sql"
                ).read_text()
                conn.executescript(migration)
                conn.execute("PRAGMA user_version = 4")
                version = 4
            if version == 4:
                migration = Path(__file__).parent.joinpath(
                    "migrations/005_affiliate_links.sql"
                ).read_text()
                conn.executescript(migration)
                conn.execute("PRAGMA user_version = 5")
                version = 5
            if version == 5:
                migration = Path(__file__).parent.joinpath(
                    "migrations/006_owner_sessions.sql"
                ).read_text()
                conn.executescript(migration)
                conn.execute("PRAGMA user_version = 6")
                version = 6
            if version == 6:
                migration = Path(__file__).parent.joinpath(
                    "migrations/007_affiliate_link_jobs.sql"
                ).read_text()
                conn.executescript(migration)
                conn.execute("PRAGMA user_version = 7")
                version = 7
            if version != 7:
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
                     affiliate_url, product_url, image_url, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (offer_id, data["source"], data["source_item_id"], data["title"],
                     data["price_cents"], data.get("reference_price_cents"),
                     data["affiliate_url"], data.get("product_url"),
                     data.get("image_url"), OfferStatus.DRAFT, utc_now()),
                )
        except sqlite3.IntegrityError as exc:
            raise DuplicateOffer from exc
        return self.get_offer(offer_id)

    @staticmethod
    def present_offer(row: sqlite3.Row) -> dict:
        offer = dict(row)
        if offer["source"] == "mercado_livre":
            # Coluna v1 'affiliate_url' continha URL comum e nunca foi atestada.
            offer["affiliate_url"] = offer["affiliate_link_url"]
            offer["affiliate_status"] = (
                (offer["affiliate_link_provenance"] or "OPERATOR_SUBMITTED")
                if offer["affiliate_link_url"] else "MISSING"
            )
        else:
            offer["product_url"] = offer["product_url"] or offer["affiliate_url"]
            offer["affiliate_status"] = "LEGACY_UNVERIFIED"
        return offer

    def get_offer(self, offer_id: str) -> dict | None:
        with self.connect() as conn:
            row = conn.execute(
                """SELECT o.*,(SELECT status FROM affiliate_link_jobs j WHERE j.offer_id=o.id)
                   AS affiliate_job_status FROM offers o WHERE o.id=?""", (offer_id,),
            ).fetchone()
            return self.present_offer(row) if row else None

    def list_offers(self, limit: int = 50) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT o.*,(SELECT status FROM affiliate_link_jobs j WHERE j.offer_id=o.id)
                   AS affiliate_job_status FROM offers o
                   ORDER BY o.created_at DESC,o.id DESC LIMIT ?""", (limit,)
            ).fetchall()
            return [self.present_offer(row) for row in rows]

    def approve(self, offer_id: str) -> dict | None:
        with self.connect() as conn:
            current = conn.execute(
                "SELECT source, status, affiliate_link_url FROM offers WHERE id = ?",
                (offer_id,),
            ).fetchone()
            if current is None:
                return None
            if (current["status"] == OfferStatus.DRAFT
                    and current["source"] == "mercado_livre"
                    and not current["affiliate_link_url"]):
                raise AffiliateLinkRequired
            conn.execute(
                """UPDATE offers SET status = ?, approved_at = ?
                WHERE id = ? AND status = ?""",
                (OfferStatus.APPROVED, utc_now(), offer_id, OfferStatus.DRAFT),
            )
        return self.get_offer(offer_id)

    def register_affiliate_link(self, offer_id: str, url: str) -> dict | None:
        with self.connect() as conn:
            current = conn.execute(
                "SELECT id, source, status, product_url FROM offers WHERE id = ?",
                (offer_id,),
            ).fetchone()
            if current is None:
                return None
            if (current["status"] != OfferStatus.DRAFT
                    or current["source"] != "mercado_livre"
                    or not current["product_url"]):
                raise AffiliateOfferNotEditable
            if conn.execute(
                "SELECT 1 FROM publications WHERE offer_id = ? LIMIT 1", (offer_id,)
            ).fetchone():
                raise AffiliateOfferNotEditable
            conn.execute(
                """UPDATE offers SET affiliate_link_url = ?,
                   affiliate_link_provenance = 'OPERATOR_SUBMITTED',
                   affiliate_registered_at = ?
                   WHERE id = ? AND status = ?""",
                (url, utc_now(), offer_id, OfferStatus.DRAFT),
            )
        return self.get_offer(offer_id)

    def affiliate_connection_status(self) -> dict:
        with self.connect() as conn:
            record = conn.execute(
                """SELECT provider, status, external_account_id, account_label,
                   authorized_permissions, verified_at FROM affiliate_integrations
                   WHERE provider = 'mercado_livre'"""
            ).fetchone()
        return {
            "provider": record["provider"],
            "status": record["status"],
            "connected": False,
            "auto_generation_available": False,
            "permissions": [],
            "connection_method": "NOT_CONFIGURED",
        }

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


    def save_search(self, query: str, source: str, items: list) -> dict:
        search_id = str(uuid4())
        now = datetime.now(UTC)
        expires_at = (now + timedelta(minutes=45)).isoformat()
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO discovery_searches(id, source, query, created_at, expires_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (search_id, source, query, now.isoformat(), expires_at),
            )
            for item in items:
                conn.execute(
                    """INSERT INTO discovery_search_items
                    (search_id, source_item_id, title, price_cents, product_url, image_url)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (search_id, item.item_id, item.title, item.price_cents,
                     item.product_url, item.image_url),
                )
        return {
            "search_id": search_id,
            "source": source,
            "query": query,
            "expires_at": expires_at,
            "items": [
                {
                    "source_item_id": item.item_id,
                    "title": item.title,
                    "price_cents": item.price_cents,
                    "product_url": item.product_url,
                    "image_url": item.image_url,
                    "price_history_available": False,
                    "promotion_verified": False,
                }
                for item in items
            ],
        }

    def select_search_items(self, search_id: str, item_ids: list[str]) -> list[dict]:
        """Seleção atômica; valores vêm apenas do snapshot no banco."""
        with self.connect() as conn:
            search = conn.execute(
                "SELECT * FROM discovery_searches WHERE id = ?", (search_id,)
            ).fetchone()
            if search is None:
                raise SearchSnapshotNotFound
            if datetime.fromisoformat(search["expires_at"]) <= datetime.now(UTC):
                raise SearchSnapshotExpired
            marks = ",".join("?" for _ in item_ids)
            rows = conn.execute(
                f"""SELECT * FROM discovery_search_items
                   WHERE search_id = ? AND source_item_id IN ({marks})""",
                (search_id, *item_ids),
            ).fetchall()
            by_id = {row["source_item_id"]: row for row in rows}
            if len(by_id) != len(item_ids):
                raise SearchSelectionInvalid
            results = []
            for item_id in item_ids:
                row = by_id[item_id]
                # Uma mesma oferta pode ser selecionada em buscas futuras sem duplicação;
                # preço diferente gera candidato diferente, sem alterar um APPROVED.
                offer_source_id = f"{item_id}-p{row['price_cents']}"
                offer_id = str(uuid4())
                created = conn.execute(
                    """INSERT OR IGNORE INTO offers
                    (id, source, source_item_id, title, price_cents,
                     reference_price_cents, affiliate_url, product_url,
                     image_url, status, created_at)
                    VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?)""",
                    (offer_id, search["source"], offer_source_id, row["title"],
                     row["price_cents"], row["product_url"],
                     row["product_url"], row["image_url"], OfferStatus.DRAFT, utc_now()),
                ).rowcount == 1
                offer = conn.execute(
                    """SELECT id, status FROM offers
                       WHERE source = ? AND source_item_id = ?""",
                    (search["source"], offer_source_id),
                ).fetchone()
                results.append({
                    "source_item_id": item_id,
                    "offer_id": offer["id"],
                    "status": offer["status"],
                    "created": created,
                })
            return results
