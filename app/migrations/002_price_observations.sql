-- Extensão aditiva: observações de preços independentes da fila de publicação.
CREATE TABLE IF NOT EXISTS price_observations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL,
  source_item_id TEXT NOT NULL,
  price_cents INTEGER NOT NULL CHECK (price_cents > 0),
  observed_hour TEXT NOT NULL,
  UNIQUE(source, source_item_id, observed_hour)
);
CREATE INDEX IF NOT EXISTS idx_price_observations_item
  ON price_observations(source, source_item_id, observed_hour);
