# Contrato de oferta v1

POST /api/v1/offers requer x-admin-key. Campos: source (2..40), source_item_id (1..100), title (3..200), price_cents (inteiro > 0), reference_price_cents (inteiro > 0 opcional), affiliate_url (HTTPS). Ofertas duplicadas por (source, source_item_id) retornam 409. Criar -> DRAFT; aprovar -> APPROVED. Valores monetários sempre em centavos. Preview não tem efeitos colaterais. Fonte e link vêm do operador nesta fase; o sistema não atesta histórico de preços nem gera links automaticamente.


## Versão aditiva v2 — imagem opcional

`POST /api/v1/offers` pode incluir `image_url` HTTPS. O download é somente de hosts permitidos, iniciado explicitamente via `POST /api/v1/offers/{id}/prepare-media`, autenticado e permitido enquanto DRAFT. `GET /api/v1/offers/{id}/preview` acrescenta `image_url`, `image_ready` e `image` com `mime_type`, `size_bytes`, `width`, `height`. O conteúdo do preview permanece sem efeitos colaterais. O campo `affiliate_url` não é gerado automaticamente.


## Versão aditiva v3 — links de afiliado separados

Para `source=mercado_livre`, `POST /api/v1/offers` passa a exigir `product_url` HTTPS e aceitar `affiliate_url` somente pelo endpoint explícito de cadastro posterior. `POST /api/v1/offers/{id}/affiliate-link` exige `x-admin-key` e `{affiliate_url:HTTPS, product_match_confirmed:true}`, enquanto DRAFT e sem publicações. Aceita padrão meli.la/<ID> ou mercadolivre.com.br/sec/<ID>. Na resposta para ofertas ML `affiliate_url` é null até essa ação; `affiliate_status=OPERATOR_SUBMITTED` após ela (não significa verificado pelo ML). `GET /api/v1/affiliates/mercado-livre/status` retorna `DISCONNECTED`, sem OAuth e sem credenciais. Outras fontes preservam o contrato legado.
