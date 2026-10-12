-- Preserva o preço riscado exibido no anúncio no momento da busca.
-- Não representa histórico de preços nem validação independente de desconto.
ALTER TABLE discovery_search_items
    ADD COLUMN reference_price_cents INTEGER
    CHECK (reference_price_cents IS NULL OR reference_price_cents > price_cents);
