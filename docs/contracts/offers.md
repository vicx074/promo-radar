# Contrato de oferta v1

POST /api/v1/offers requer x-admin-key. Campos: source (2..40), source_item_id (1..100), title (3..200), price_cents (inteiro > 0), reference_price_cents (inteiro > 0 opcional), affiliate_url (HTTPS). Ofertas duplicadas por (source, source_item_id) retornam 409. Criar -> DRAFT; aprovar -> APPROVED. Valores monetários sempre em centavos. Preview não tem efeitos colaterais. Fonte e link vêm do operador nesta fase; o sistema não atesta histórico de preços nem gera links automaticamente.


## Versão aditiva v2 — imagem opcional

`POST /api/v1/offers` pode incluir `image_url` HTTPS. O download é somente de hosts permitidos, iniciado explicitamente via `POST /api/v1/offers/{id}/prepare-media`, autenticado e permitido enquanto DRAFT. `GET /api/v1/offers/{id}/preview` acrescenta `image_url`, `image_ready` e `image` com `mime_type`, `size_bytes`, `width`, `height`. O conteúdo do preview permanece sem efeitos colaterais. O campo `affiliate_url` não é gerado automaticamente.


## Versão aditiva v3 — links de afiliado separados

Para `source=mercado_livre`, `POST /api/v1/offers` passa a exigir `product_url` HTTPS e aceitar `affiliate_url` somente pelo endpoint explícito de cadastro posterior. `POST /api/v1/offers/{id}/affiliate-link` exige `x-admin-key` e `{affiliate_url:HTTPS, product_match_confirmed:true}`, enquanto DRAFT e sem publicações. Aceita padrão meli.la/<ID> ou mercadolivre.com.br/sec/<ID>. Na resposta para ofertas ML `affiliate_url` é null até essa ação; `affiliate_status=OPERATOR_SUBMITTED` após ela (não significa verificado pelo ML). `GET /api/v1/affiliates/mercado-livre/status` retorna `DISCONNECTED`, sem OAuth e sem credenciais. Outras fontes preservam o contrato legado.

## Versão aditiva v4 — fila de geração local de links (SQLite v7)

Quando `AFFILIATE_BRIDGE_TOKEN` (chave exclusiva do Promo Radar) e `AFFILIATE_AUTO_QUEUE=true` estiverem configurados, `POST /api/v1/discovery/select` cria tarefas PENDING para rascunhos Mercado Livre selecionados, atomicamente com a seleção. O operador pode chamar `POST /api/v1/offers/{id}/affiliate-link/queue` para criar ou reencaminhar uma tarefa que falhou; não altera links de ofertas APPROVED nem publica. `GET /api/v1/offers/{id}` inclui `affiliate_job_status`. `GET /api/v1/affiliate-bridge/status` apresenta heartbeat/contadores sem revelar credenciais e não equivale à conexão OAuth com o ML. O worker Chrome local acessa apenas `POST /api/v1/affiliate-agent/{heartbeat,claim,complete}` mediante Authorization Bearer do conector, sem autenticação administrativa, aprovação ou publicação. Vincular depende de URL de origem compatível e formato do link retornado, **não atesta comissão ou titularidade da conta**. Cadastro manual continua disponível e cancela tarefa pendente.

## Versão aditiva v5 — somente anúncios com promoção (SQLite v8)

No modo `DISCOVERY_PROVIDER=apify`, `POST /api/v1/discovery/search` filtra produtos que não possuem `originalPrice` numérico válido e superior a `price` em pelo menos 1% (valores do próprio anúncio). O retorno `items` tem `reference_price_cents` e `discount_percent` calculado a partir dos centavos inteiros; `promotion_verified=false` permanece, pois o preço riscado não representa histórico independente. Pesquisa sem descontos retorna `items=[]`, não uma promoção fictícia. O catálogo CSV legado preserva seu comportamento explícito de fonte local, com `reference_price_cents=null`. `discovery_search_items` ganha coluna opcional `reference_price_cents` na migração SQLite v8; a seleção salva esse preço em `offers.reference_price_cents` sem reescrever ofertas existentes nem criar publicação. O frontend pode apresentar De / Por / OFF e a prévia usa os valores capturados na busca.
