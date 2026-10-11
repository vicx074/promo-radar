"""Fila de geração de links via navegador LOCAL do titular (nunca na VPS).

A API interna de afiliados do site pode mudar. O link só é vinculado
após checagem do origin_url e da tag na sessão do próprio navegador.
Não autentica no Mercado Livre nem comprova comissões.
"""
import hashlib
import hmac
import re
import secrets
import time
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

from app.affiliate import AffiliateLinkError, validate_official_link
from app.discovery import _valid_product_url
from app.storage import SQLiteStore, utc_now

_ERROR_CODES = frozenset({
    "LOGIN_REQUIRED", "PROVIDER_UNAVAILABLE", "PRODUCT_MISMATCH",
    "INVALID_LINK", "LEASE_EXPIRED", "ALREADY_LINKED", "UNKNOWN",
})
_PRODUCT_ID = re.compile(r"MLB[A-Z0-9]+", re.I)
_LEASE_SECONDS = 120


class JobInvalid(Exception):
    pass


class JobConflict(Exception):
    pass


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_product_url(raw: str) -> str | None:
    if not isinstance(raw, str) or not _valid_product_url(raw):
        return None
    try:
        u = urlsplit(raw)
        if u.hostname not in {"www.mercadolivre.com.br", "mercadolivre.com.br"}:
            return None
        if any(char.isspace() for char in raw) or "\\" in raw:
            return None
        return urlunsplit(("https", "www.mercadolivre.com.br", u.path.rstrip("/"), "", ""))
    except ValueError:
        return None


def matching_product(original: str, from_central: str) -> bool:
    """Recusa destino divergente; IDs comprovadamente iguais toleram URLs diferentes."""
    a = canonical_product_url(original)
    b = canonical_product_url(from_central)
    if a is None or b is None:
        return False
    if a == b:
        return True
    ids_a = _PRODUCT_ID.findall(urlsplit(a).path)
    ids_b = _PRODUCT_ID.findall(urlsplit(b).path)
    return bool(ids_a and ids_b and ids_a[-1].upper() == ids_b[-1].upper())


@dataclass
class AffiliateBridge:
    store: SQLiteStore

    def queue_offer(self, offer_id: str) -> dict:
        with self.store.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            offer = conn.execute(
                "SELECT source,status,product_url,affiliate_link_url FROM offers WHERE id=?",
                (offer_id,),
            ).fetchone()
            if offer is None:
                raise JobInvalid("Oferta não encontrada")
            if (
                offer["source"] != "mercado_livre"
                or offer["status"] != "DRAFT"
                or not canonical_product_url(offer["product_url"])
                or offer["affiliate_link_url"]
            ):
                raise JobConflict("Link automático permitido apenas para rascunho sem link")
            existing = conn.execute(
                "SELECT * FROM affiliate_link_jobs WHERE offer_id=?", (offer_id,)
            ).fetchone()
            if existing:
                if existing["status"] in ("FAILED", "CANCELLED"):
                    conn.execute(
                        """UPDATE affiliate_link_jobs SET status='PENDING',error_code=NULL,
                           claim_hash=NULL,lease_expires_at=NULL,updated_at=? WHERE offer_id=?""",
                        (utc_now(), offer_id),
                    )
                # Nunca duplicar trabalhos ativos nem repetir geração já concluída.
            else:
                conn.execute(
                    """INSERT INTO affiliate_link_jobs
                       (id,offer_id,status,created_at,updated_at)
                       VALUES (?,?,'PENDING',?,?)""",
                    (str(uuid4()), offer_id, utc_now(), utc_now()),
                )
            job = conn.execute(
                "SELECT id,offer_id,status,error_code FROM affiliate_link_jobs WHERE offer_id=?",
                (offer_id,),
            ).fetchone()
        return dict(job)

    def claim(self) -> dict | None:
        with self.store.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            now = int(time.time())
            # Não repetir automaticamente uma ação feita remotamente cujo resultado é incerto.
            conn.execute(
                """UPDATE affiliate_link_jobs SET status='FAILED',
                   error_code='LEASE_EXPIRED',claim_hash=NULL,lease_expires_at=NULL,
                   updated_at=? WHERE status='PROCESSING' AND lease_expires_at<=?""",
                (utc_now(), now),
            )
            row = conn.execute(
                """SELECT j.id,j.offer_id,o.product_url
                   FROM affiliate_link_jobs j JOIN offers o ON o.id=j.offer_id
                   WHERE j.status='PENDING' AND o.status='DRAFT'
                     AND o.affiliate_link_url IS NULL
                   ORDER BY j.created_at,j.id LIMIT 1"""
            ).fetchone()
            if row is None:
                return None
            raw_claim = secrets.token_urlsafe(32)
            conn.execute(
                """UPDATE affiliate_link_jobs SET status='PROCESSING',
                   claim_hash=?,lease_expires_at=?,updated_at=? WHERE id=?""",
                (digest(raw_claim), now + _LEASE_SECONDS, utc_now(), row["id"]),
            )
            return {
                "job_id": row["id"], "offer_id": row["offer_id"],
                "product_url": row["product_url"], "claim_token": raw_claim,
                "lease_seconds": _LEASE_SECONDS,
            }

    def finish(
        self, job_id: str, claim_token: str, *,
        affiliate_url: str | None = None, origin_url: str | None = None,
        error_code: str | None = None,
    ) -> dict:
        with self.store.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """SELECT j.*,o.product_url,o.status AS offer_status,o.affiliate_link_url
                   FROM affiliate_link_jobs j JOIN offers o ON o.id=j.offer_id
                   WHERE j.id=?""",
                (job_id,),
            ).fetchone()
            if (
                not row or row["status"] != "PROCESSING" or not row["claim_hash"]
                or not hmac.compare_digest(row["claim_hash"], digest(claim_token))
                or row["lease_expires_at"] <= int(time.time())
            ):
                raise JobConflict("Trabalho expirado ou concluído; não vinculado")
            if row["offer_status"] != "DRAFT" or row["affiliate_link_url"]:
                raise JobConflict("Oferta alterada desde a solicitação")
            if error_code:
                if error_code not in _ERROR_CODES:
                    error_code = "UNKNOWN"
                status = "FAILED"
            else:
                try:
                    if not affiliate_url or not origin_url:
                        raise AffiliateLinkError("Faltam informações de origem")
                    validate_official_link(affiliate_url)
                    if not matching_product(row["product_url"], origin_url):
                        error_code = "PRODUCT_MISMATCH"
                    else:
                        conn.execute(
                            """UPDATE offers SET affiliate_link_url=?,
                               affiliate_link_provenance='LOCAL_BROWSER_BRIDGE',
                               affiliate_registered_at=?
                               WHERE id=? AND status='DRAFT' AND affiliate_link_url IS NULL""",
                            (affiliate_url, utc_now(), row["offer_id"]),
                        )
                except AffiliateLinkError:
                    error_code = "INVALID_LINK"
                status = "FAILED" if error_code else "LINKED"
            conn.execute(
                """UPDATE affiliate_link_jobs SET status=?,error_code=?,
                   claim_hash=NULL,lease_expires_at=NULL,updated_at=? WHERE id=?""",
                (status, error_code, utc_now(), job_id),
            )
            return {"job_id": job_id, "offer_id": row["offer_id"],
                    "status": status, "error_code": error_code}

    def heartbeat(self) -> None:
        with self.store.connect() as conn:
            conn.execute(
                "UPDATE affiliate_agent_heartbeat SET last_seen_at=? WHERE id=1",
                (int(time.time()),),
            )

    def status(self, *, configured: bool) -> dict:
        with self.store.connect() as conn:
            row = conn.execute(
                "SELECT last_seen_at FROM affiliate_agent_heartbeat WHERE id=1"
            ).fetchone()
            queue = conn.execute(
                """SELECT status, COUNT(*) AS n FROM affiliate_link_jobs GROUP BY status"""
            ).fetchall()
        seen = row["last_seen_at"] if row else 0
        return {
            "configured": configured,
            "worker_online": bool(configured and seen and time.time() - seen < 90),
            "last_seen_at": seen or None,
            "jobs": {r["status"]: r["n"] for r in queue},
            "connection_method": "LOCAL_BROWSER_UNOFFICIAL",
            "marketplace_session_verified": False,
        }
