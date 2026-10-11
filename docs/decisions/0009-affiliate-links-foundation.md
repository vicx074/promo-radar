# ADR 0009 — Separação segura dos links de afiliado

Status: aceito para o MVP · 2026-10-11.

## Problema

Até SQLite v4, a coluna `offers.affiliate_url NOT NULL` representa ora uma URL comum, ora uma possível URL de afiliado, gerando falso senso de comissão. A busca Mercado Livre usa CSV e alimenta esta coluna com `product_url`. Ofertas antigas inclusive aprovadas podem conter URL de produto comum. Uma migração que marcar todas como afiliadas é incorreta.

## Decisão de compatibilidade e segurança

1. Migração v5 aditiva acrescenta `product_url`, `affiliate_link_url`, `affiliate_link_provenance`, `affiliate_registered_at`. Para `source=mercado_livre`, copia-se a coluna v1 legada para `product_url` e mantém-se `affiliate_link_url=NULL`. **O SQLite mantém o nome legada `affiliate_url NOT NULL` para não reconstruir tabelas com FK/publications; a API expõe `affiliate_url` como projeção de `affiliate_link_url` para ML**, nunca como seu valor legado. A coluna física legada é preenchida com a URL de produto em novas ofertas ML, somente por compatibilidade. Não apagar/mudar informações históricas em publicações já registradas.
2. API autenticada `POST /api/v1/offers/{offer_id}/affiliate-link` exige `{affiliate_url, product_match_confirmed:true}` e só permite anexar enquanto DRAFT, sem publicações e com produto ML cadastrado. Valida HTTPS e formato da URL (meli.la/ID ou mercadolivre.com.br/sec/ID), **sem afirmar que o link pertence à conta ou ao mesmo produto**, tampouco comissão. Confirmação é declaração do operador, não verificação remota. Nenhum cookie nem chave ou tag são usados.
3. Novas ofertas de fonte `mercado_livre` são DRAFT e não são aprovadas nem publicadas até anexar a URL oficial manualmente. Outras fontes preservam o contrato v1 por compatibilidade; não afirmar links legados como afiliados verificados.
4. Preview com affiliate_url quando disponível; sem afiliado, exibe URL do produto e um aviso explícito de que não há rastreamento. Publicação exige link antes de reservar SENDING, sem afetar a barreira `SEND_ENABLED`, autenticação, imagem e idempotência.
5. `affiliate_integrations` registra estado e possíveis permissões futuras. Hoje GET `/api/v1/affiliates/mercado-livre/status` informa **DISCONNECTED**, `auto_generation_available=false`; nenhum endpoint altera essa situação até que tenhamos integração autorizada. Nunca armazenar cookies ou fingir OAuth.
6. Todos os testes automáticos usam URLs fictícias e publisher simulado, inclusive na CI Docker. Nenhuma rede ML/WhatsApp envolvida.

## Limitações

Validar um formato de link não confirma destino, atribuição ou elegibilidade. Mesmo o link gerado oficialmente pode não gerar comissão para um produto/canal específico. Precisamos de conexão autorizada e teste com conta própria para validar esse aspecto. Ver pesquisa [ADR 0008](0008-affiliate-provider-evaluation.md) na PR de pesquisa separada.
