ALTER TABLE offers ADD COLUMN image_url TEXT;
ALTER TABLE offers ADD COLUMN image_sha256 TEXT;
CREATE TABLE IF NOT EXISTS media_assets (
  sha256 TEXT PRIMARY KEY,
  relative_path TEXT NOT NULL,
  size_bytes INTEGER NOT NULL CHECK (size_bytes > 0),
  width INTEGER NOT NULL CHECK (width > 0),
  height INTEGER NOT NULL CHECK (height > 0),
  mime_type TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_offers_media ON offers(image_sha256);
