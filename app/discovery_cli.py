"""CLI de ingestão de preços de um CSV local autorizado."""

import argparse
import sqlite3
import sys
from pathlib import Path

from app.config import Settings
from app.discovery import ingest_catalog
from app.storage import SQLiteStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Importar CSV autorizado do Mercado Livre (sem scraping ou envios)"
    )
    parser.add_argument("path", type=Path, help="CSV local montado no container")
    parser.add_argument("--min-drop-percent", type=int, default=15)
    args = parser.parse_args(argv)
    try:
        result = ingest_catalog(
            args.path,
            SQLiteStore(Settings.from_env().sqlite_path),
            min_drop_percent=args.min_drop_percent,
        )
    except (OSError, ValueError, sqlite3.DatabaseError) as exc:
        print(f"Falha na ingestão: {exc}", file=sys.stderr)
        return 1
    print(
        f"Recebidos: {result.received} | Observações novas: {result.observed} | "
        f"Repetidos na mesma hora: {result.skipped_hour} | "
        f"Ofertas DRAFT criadas: {result.drafts_created}"
    )
    print("Não houve envio ao WhatsApp.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
