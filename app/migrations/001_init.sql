CREATE TABLE IF NOT EXISTS offers (
  id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  source_item_id TEXT NOT NULL,
  title TEXT NOT NULL,
  price_cents INTEGER NOT NULL CHECK(price_cents > 0),
  reference_price_cents INTEGER CHECK(reference_price_cents > 0),
  affiliate_url TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('DRAFT', 'APPROVED')),
  created_at TEXT NOT NULL,
  approved_at TEXT,
  UNIQUE(source, source_item_id)
);
CREATE TABLE IF NOT EXISTS publications (
  id TEXT PRIMARY KEY,
  offer_id TEXT NOT NULL REFERENCES offers(id) ON DELETE RESTRICT,
  group_jid TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('SENDING', 'SENT', 'UNKNOWN')),
  provider_message_id TEXT,
  error_summary TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(offer_id, group_jid)
);
CREATE INDEX IF NOT EXISTS idx_offers_status_created ON offers(status, created_at);
CREATE INDEX IF NOT EXISTS idx_publications_offer_id ON publications(offer_id);
