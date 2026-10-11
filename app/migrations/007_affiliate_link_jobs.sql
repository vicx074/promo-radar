-- Conector local por token separado; nunca armazenar cookies/senhas do Mercado Livre.
CREATE TABLE affiliate_link_jobs (
  id TEXT PRIMARY KEY,
  offer_id TEXT NOT NULL UNIQUE REFERENCES offers(id) ON DELETE CASCADE,
  status TEXT NOT NULL CHECK (status IN ('PENDING','PROCESSING','LINKED','FAILED','CANCELLED')),
  claim_hash TEXT,
  lease_expires_at INTEGER,
  error_code TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX idx_affiliate_link_jobs_next ON affiliate_link_jobs(status, created_at);
CREATE TABLE affiliate_agent_heartbeat (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  last_seen_at INTEGER NOT NULL DEFAULT 0
);
INSERT INTO affiliate_agent_heartbeat (id, last_seen_at) VALUES (1, 0);
