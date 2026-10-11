# Contrato de oferta v1

POST /api/v1/offers requer x-admin-key. Campos: source (2..40), source_item_id (1..100), title (3..200), price_cents (inteiro > 0), reference_price_cents (inteiro > 0 opcional), affiliate_url (HTTPS). Ofertas duplicadas por (source, source_item_id) retornam 409. Criar -> DRAFT; aprovar -> APPROVED. Valores monetários sempre em centavos. Preview não tem efeitos colaterais. Fonte e link vêm do operador nesta fase; o sistema não atesta histórico de preços nem gera links automaticamente.


## Versão aditiva v2 — imagem opcional

`POST /api/v1/offers` pode incluir `image_url` HTTPS. O download é somente de hosts permitidos, iniciado explicitamente via `POST /api/v1/offers/{id}/prepare-media`, autenticado e permitido enquanto DRAFT. `GET /api/v1/offers/{id}/preview` acrescenta `image_url`, `image_ready` e `image` com `mime_type`, `size_bytes`, `width`, `height`. O conteúdo do preview permanece sem efeitos colaterais. O campo `affiliate_url` não é gerado automaticamente.
