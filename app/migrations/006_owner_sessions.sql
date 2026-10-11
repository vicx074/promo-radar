-- Usuário único: nunca persistir senha, token de sessão em claro ou IP real.
CREATE TABLE IF NOT EXISTS owner_sessions (
    token_hash TEXT PRIMARY KEY,
    csrf_token TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    last_seen_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_owner_sessions_expiry ON owner_sessions(expires_at);
CREATE TABLE IF NOT EXISTS owner_login_throttle (
    id INTEGER PRIMARY KEY CHECK (id=1),
    attempts INTEGER NOT NULL DEFAULT 0,
    window_started_at INTEGER NOT NULL DEFAULT 0,
    locked_until INTEGER NOT NULL DEFAULT 0
);
INSERT OR IGNORE INTO owner_login_throttle
    (id, attempts, window_started_at, locked_until) VALUES (1,0,0,0);
