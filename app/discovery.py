"""Descoberta por catálogo CSV de procedência autorizada, sem scraping de sites."""

import csv
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from app.storage import SQLiteStore, utc_now

_SOURCE = "mercado_livre"
_ITEM_RE = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
_FIELDS = {"source_item_id", "title", "price_cents", "product_url"}
_MAX_ROWS = 500


@dataclass(frozen=True)
class CatalogItem:
    item_id: str
    title: str
    price_cents: int
    product_url: str


@dataclass(frozen=True)
class IngestionSummary:
    received: int
    observed: int
    skipped_hour: int
    drafts_created: int


def _valid_product_url(raw: str) -> bool:
    try:
        url = urlsplit(raw)
        host = (url.hostname or "").lower()
        valid_host = host == "mercadolivre.com.br" or host.endswith(
            ".mercadolivre.com.br"
        )
        return (
            url.scheme == "https"
            and valid_host
            and bool(url.path.strip("/"))
            and not url.username
            and not url.password
            and url.port is None
            and not url.fragment
        )
    except ValueError:
        return False


def read_catalog(path: Path) -> list[CatalogItem]:
    """Rejeita entradas inválidas antes de alterar o banco."""
    records = []
    seen = set()
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        if not reader.fieldnames or not _FIELDS.issubset(set(reader.fieldnames)):
            raise ValueError("CSV deve ter source_item_id,title,price_cents,product_url")
        for line, record in enumerate(reader, start=2):
            if line > _MAX_ROWS + 1:
                raise ValueError(f"CSV excede limite de {_MAX_ROWS} produtos")
            if None in record or any(record.get(key) is None for key in _FIELDS):
                raise ValueError(f"Linha {line}: colunas inválidas")
            item_id = record["source_item_id"].strip()
            title = record["title"].strip()
            price = record["price_cents"].strip()
            url = record["product_url"].strip()
            if not _ITEM_RE.fullmatch(item_id) or item_id in seen:
                raise ValueError(f"Linha {line}: ID vazio, inválido ou duplicado")
            if not 3 <= len(title) <= 200:
                raise ValueError(f"Linha {line}: título inválido")
            if not price.isascii() or not price.isdecimal():
                raise ValueError(f"Linha {line}: preço deve ser inteiro em centavos")
            cents = int(price)
            if not 0 < cents <= 1_000_000_000:
                raise ValueError(f"Linha {line}: preço fora do intervalo")
            if not _valid_product_url(url):
                raise ValueError(f"Linha {line}: URL HTTPS de produto inválida")
            seen.add(item_id)
            records.append(CatalogItem(item_id, title, cents, url))
    return records


def ingest_catalog(
    path: Path,
    store: SQLiteStore,
    *,
    min_drop_percent: int = 15,
    now: datetime | None = None,
) -> IngestionSummary:
    if not 1 <= min_drop_percent <= 95:
        raise ValueError("min_drop_percent deve estar entre 1 e 95")
    observed_time = now or datetime.now(UTC)
    if observed_time.tzinfo is None or observed_time.utcoffset() is None:
        raise ValueError("A data da observação precisa ter timezone")
    observed_hour = observed_time.astimezone(UTC).replace(
        minute=0, second=0, microsecond=0
    ).isoformat()
    items = read_catalog(path)
    store.initialize()
    inserted = skipped = drafts = 0
    with store.connect() as conn:
        for item in items:
            # O mesmo produto não gera observações artificiais ao reexecutar
            # várias vezes dentro da mesma hora.
            exists = conn.execute(
                """SELECT 1 FROM price_observations
                   WHERE source = ? AND source_item_id = ? AND observed_hour = ?""",
                (_SOURCE, item.item_id, observed_hour),
            ).fetchone()
            if exists:
                skipped += 1
                continue
            stats = conn.execute(
                """SELECT COUNT(*) AS n, MIN(price_cents) AS min_price
                   FROM price_observations WHERE source = ? AND source_item_id = ?""",
                (_SOURCE, item.item_id),
            ).fetchone()
            conn.execute(
                """INSERT INTO price_observations
                   (source, source_item_id, price_cents, observed_hour)
                   VALUES (?, ?, ?, ?)""",
                (_SOURCE, item.item_id, item.price_cents, observed_hour),
            )
            inserted += 1
            previous_low = stats["min_price"]
            # Nunca atribuir "desconto" a uma única observação isolada,
            # nem confundir preço anunciado com menor preço já observado.
            if (
                stats["n"] < 2
                or previous_low is None
                or item.price_cents >= previous_low
                or (previous_low - item.price_cents) * 100
                < min_drop_percent * previous_low
            ):
                continue
            # Uma oferta por combinação (produto, menor preço novo).
            # Uma queda adicional de preço pode gerar uma nova DRAFT para revisão.
            offer_item_id = f"{item.item_id}-p{item.price_cents}"
            result = conn.execute(
                """INSERT OR IGNORE INTO offers
                   (id, source, source_item_id, title, price_cents,
                    reference_price_cents, affiliate_url, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'DRAFT', ?)""",
                (
                    str(uuid4()), _SOURCE, offer_item_id, item.title,
                    item.price_cents, previous_low, item.product_url, utc_now(),
                ),
            )
            drafts += result.rowcount
    return IngestionSummary(len(items), inserted, skipped, drafts)
