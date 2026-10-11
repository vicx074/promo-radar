CREATE TABLE IF NOT EXISTS discovery_searches (
  id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  query TEXT NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS discovery_search_items (
  search_id TEXT NOT NULL REFERENCES discovery_searches(id) ON DELETE CASCADE,
  source_item_id TEXT NOT NULL,
  title TEXT NOT NULL,
  price_cents INTEGER NOT NULL CHECK (price_cents > 0),
  product_url TEXT NOT NULL,
  image_url TEXT,
  PRIMARY KEY(search_id, source_item_id)
);
CREATE INDEX IF NOT EXISTS idx_discovery_search_expiry
  ON discovery_searches(expires_at);
