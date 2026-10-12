# ADR 0015 — Descoberta apenas de anúncios com preço promocional

Status: implementação validada com dados simulados, requer verificação após atualização local.

## Problema

A busca Apify retornava anúncios normais misturados a ofertas, mostrando apenas `price`. O ator `gio21/mercado-livre-scraper` fornece também `originalPrice` (preço riscado informado no anúncio) e `discount` (texto opcional); o backend descartava ambos. Operador quer compartilhar somente promoções e visualizar "De / Por / % OFF" nos cards e na prévia.

## Decisão

1. **Somente Apify live** passa a filtrar anúncios para os quais `price` e `originalPrice` são valores positivos válidos em reais, com `originalPrice > price` e desconto calculado de ao menos 1%. Linhas sem referência, iguais, negativas, com moeda divergente ou fonte inválida não entram na lista. A string de `discount` não é prova suficiente para calcular valores nem sobrepõe a matemática a partir dos preços. Resultados vazios sem promoção são normais, não erro. O CSV legado continua explicitamente um catálogo local, sem classificar promoções sem preço de referência.
2. Preços continuam em **centavos inteiros** (`Decimal` para converter reais recebidos). `CatalogItem` carrega `reference_price_cents` opcional; `POST /discovery/search` devolve `reference_price_cents` e `discount_percent` calculado com truncamento inteiro para não inflar percentuais. `promotion_verified=false` permanece, pois preço riscado informado pelo anúncio **não equivale a histórico de preço confirmado**.
3. SQLite **schema v8 aditivo** acrescenta `discovery_search_items.reference_price_cents` opcional. Salvar snapshot com os dois preços e transferir o valor original para `offers.reference_price_cents` na seleção; não alterar preço/histórico de ofertas já criadas, especialmente aprovadas/publicadas. Deduplicação prévia por produto/preço continua intacta. Valores antigos têm referência `NULL`.
4. Como a maioria dos anúncios pesquisados pode não ter desconto, cada busca Apify consulta até `min(50, max(10, limit*3))` anúncios em **uma única execução**, com `maxPages=1` e `maxTotalChargeUsd=0.20` já existente; retorna até `limit` promoções. Isto **não garante** que existam promoções em toda busca e pode aumentar o consumo do serviço. Nunca criar consultas automáticas em background ou passar tokens ao navegador.
5. UI React + Tailwind mostra "De: (preço riscado)", "Por: (preço destacado)", e "% OFF" derivado dos números. Mensagem de lista vazia explica quando o provedor não identificou promoções. Detalhe da oferta e prévia do WhatsApp também mostram os dois preços, quando presentes. Nenhum envio ou aprovação automático.
6. Testes CI simulam contrato da Apify, seleção durável, desconto computado e responsividade; validar resultados reais/estoque por meio do painel do operador antes de divulgar. A verificação da busca Apify com token do operador antes desta mudança confirmou produtos reais, mas **não comprova este novo filtro com execução ao vivo**.

## Riscos

O anunciante/provedor pode exibir "preço original" artificialmente alto; cálculo correto do percentual não significa economia real nem menor preço histórico. A interface deve informar isso. Apify é coletor de terceiros e não API oficial do Mercado Livre. Alterações do ator podem exigir ajustes. Os preços podem mudar entre pesquisa e publicação, que permanece revisão humana obrigatória.
