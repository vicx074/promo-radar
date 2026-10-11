# Contrato de oferta v1

POST /api/v1/offers requer x-admin-key. Campos: source (2..40), source_item_id (1..100), title (3..200), price_cents (inteiro > 0), reference_price_cents (inteiro > 0 opcional), affiliate_url (HTTPS). Ofertas duplicadas por (source, source_item_id) retornam 409. Criar -> DRAFT; aprovar -> APPROVED. Valores monetários sempre em centavos. Preview não tem efeitos colaterais. Fonte e link vêm do operador nesta fase; o sistema não atesta histórico de preços nem gera links automaticamente.
