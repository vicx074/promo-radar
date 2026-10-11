-- Schema v5: preserva a coluna legada offers.affiliate_url (NOT NULL), que
-- historicamente continha product_url em ofertas Mercado Livre. Nunca inferir
-- atribuição de comissão a partir desse valor.
ALTER TABLE offers ADD COLUMN product_url TEXT;
ALTER TABLE offers ADD COLUMN affiliate_link_url TEXT;
ALTER TABLE offers ADD COLUMN affiliate_link_provenance TEXT;
ALTER TABLE offers ADD COLUMN affiliate_registered_at TEXT;

-- Migração conservadora: URL antiga vira somente URL de produto.
-- affiliate_link_url fica NULL mesmo para registros APPROVED preexistentes.
UPDATE offers
SET product_url = affiliate_url
WHERE source = 'mercado_livre';

CREATE TABLE IF NOT EXISTS affiliate_integrations (
  provider TEXT PRIMARY KEY,
  status TEXT NOT NULL CHECK(status IN ('DISCONNECTED', 'CONNECTED')),
  external_account_id TEXT,
  account_label TEXT,
  authorized_permissions TEXT NOT NULL DEFAULT '[]',
  verified_at TEXT,
  updated_at TEXT NOT NULL
);

INSERT OR IGNORE INTO affiliate_integrations
  (provider, status, authorized_permissions, updated_at)
VALUES ('mercado_livre', 'DISCONNECTED', '[]', strftime('%Y-%m-%dT%H:%M:%fZ','now'));
