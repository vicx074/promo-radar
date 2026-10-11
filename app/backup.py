import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.config import Settings


def backup_database(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"Banco não encontrado: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"Backup já existe: {destination}")
    with sqlite3.connect(str(source)) as src, sqlite3.connect(str(destination)) as dst:
        src.backup(dst)
        result = dst.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise RuntimeError(f"Integridade do backup falhou: {result}")


if __name__ == "__main__":
    filename = datetime.now(timezone.utc).strftime("offers-%Y%m%dT%H%M%SZ.db")
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/backups") / filename
    backup_database(Settings.from_env().sqlite_path, dest)
    print(f"Backup criado: {dest}")
