"""Autenticação de um operador; sessão opaca revogável em SQLite.

Nunca registrar senha, cookie nem CSRF. Somente hash SHA-256 do token no banco.
"""
import getpass
import hashlib
import hmac
import secrets
import sqlite3
import sys
import time
from dataclasses import dataclass
from urllib.parse import urlsplit

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError, VerificationError

COOKIE_SECURE_NAME = "__Host-promo_session"
COOKIE_LOCAL_NAME = "promo_session"
SESSION_ABSOLUTE_SECONDS = 12 * 60 * 60
SESSION_IDLE_SECONDS = 30 * 60
LOGIN_WINDOW_SECONDS = 15 * 60
LOGIN_LOCK_SECONDS = 15 * 60
MAX_LOGIN_FAILURES = 5
_HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)


def cookie_name(secure: bool) -> str:
    return COOKIE_SECURE_NAME if secure else COOKIE_LOCAL_NAME


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_origin(origin: str | None, host: str | None, *, secure: bool) -> bool:
    """Strict Origin + Host check; headers passed through trusted same-origin proxy."""
    if not origin or not host:
        return False
    try:
        parsed = urlsplit(origin)
        return (
            parsed.scheme == ("https" if secure else "http")
            and parsed.netloc.lower() == host.lower()
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
            and parsed.path in ("", "/")
            and not parsed.query
            and not parsed.fragment
        )
    except ValueError:
        return False


def verify_password(password: str, encoded: str) -> bool:
    try:
        return bool(_HASHER.verify(encoded, password))
    except (InvalidHashError, VerifyMismatchError, VerificationError, ValueError):
        return False


@dataclass(frozen=True)
class OwnerSession:
    csrf_token: str
    created_at: int
    expires_at: int


class OwnerAuth:
    def __init__(self, store):
        self.store = store

    def throttle_remaining(self, now: int | None = None) -> int:
        now = int(time.time()) if now is None else now
        with self.store.connect() as conn:
            row = conn.execute(
                "SELECT locked_until FROM owner_login_throttle WHERE id=1"
            ).fetchone()
        return max(0, row["locked_until"] - now)

    def failed_login(self, now: int | None = None) -> None:
        now = int(time.time()) if now is None else now
        with self.store.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT attempts,window_started_at,locked_until "
                "FROM owner_login_throttle WHERE id=1"
            ).fetchone()
            if row["locked_until"] > now:
                return
            attempts = row["attempts"] + 1 if now - row["window_started_at"] < LOGIN_WINDOW_SECONDS else 1
            locked = now + LOGIN_LOCK_SECONDS if attempts >= MAX_LOGIN_FAILURES else 0
            conn.execute(
                "UPDATE owner_login_throttle SET attempts=?,window_started_at=?,locked_until=? "
                "WHERE id=1",
                (attempts, row["window_started_at"] if attempts > 1 else now, locked),
            )

    def issue_session(self, now: int | None = None) -> tuple[str, OwnerSession]:
        now = int(time.time()) if now is None else now
        raw_token = secrets.token_urlsafe(48)
        csrf = secrets.token_urlsafe(32)
        with self.store.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "UPDATE owner_login_throttle SET attempts=0,window_started_at=0,locked_until=0 "
                "WHERE id=1"
            )
            conn.execute("DELETE FROM owner_sessions WHERE expires_at <= ?", (now,))
            # Cada login revoga todas as sessões anteriores: apenas uma sessão ativa.
            conn.execute("DELETE FROM owner_sessions")
            conn.execute(
                "INSERT INTO owner_sessions(token_hash,csrf_token,created_at,last_seen_at,expires_at) "
                "VALUES(?,?,?,?,?)",
                (token_hash(raw_token), csrf, now, now, now + SESSION_ABSOLUTE_SECONDS),
            )
        return raw_token, OwnerSession(csrf, now, now + SESSION_ABSOLUTE_SECONDS)

    def read_session(self, raw_token: str | None, now: int | None = None) -> OwnerSession | None:
        if not raw_token or len(raw_token) > 256:
            return None
        now = int(time.time()) if now is None else now
        with self.store.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT csrf_token,created_at,last_seen_at,expires_at "
                "FROM owner_sessions WHERE token_hash=?",
                (token_hash(raw_token),),
            ).fetchone()
            if row is None:
                return None
            if row["expires_at"] <= now or now - row["last_seen_at"] >= SESSION_IDLE_SECONDS:
                conn.execute("DELETE FROM owner_sessions WHERE token_hash=?", (token_hash(raw_token),))
                return None
            conn.execute(
                "UPDATE owner_sessions SET last_seen_at=? WHERE token_hash=?",
                (now, token_hash(raw_token)),
            )
            return OwnerSession(row["csrf_token"], row["created_at"], row["expires_at"])

    def revoke(self, raw_token: str | None) -> None:
        if not raw_token:
            return
        with self.store.connect() as conn:
            conn.execute("DELETE FROM owner_sessions WHERE token_hash=?", (token_hash(raw_token),))


def main() -> None:
    if sys.argv[1:] != ["hash-password"]:
        raise SystemExit("Uso: python -m app.auth hash-password")
    password = getpass.getpass("Nova senha privada (mínimo 14 caracteres): ")
    confirmation = getpass.getpass("Confirme a senha: ")
    if len(password) < 14 or password != confirmation or len(password) > 1024:
        raise SystemExit("Senha inválida, muito curta ou confirmação diferente.")
    print(_HASHER.hash(password))


if __name__ == "__main__":
    main()
