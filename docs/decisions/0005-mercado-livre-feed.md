# ADR 0005 — Descoberta Mercado Livre por fonte autorizada

- Status: aceito
- Data: 2026-10-11

## Contexto

Precisamos descobrir oportunidades sem Chromium persistente. A busca geral da API de Mercado Livre (`/sites/MLB/search`) foi reportada como HTTP 403 por integradores, inclusive com OAuth. Os [Termos do Programa de Desenvolvedores](https://developers.mercadolivre.com.br/pt_br/termos-e-condicoes), cláusula 7.6, restringem scraping não autorizado; o [robots.txt](https://www.mercadolivre.com.br/robots.txt) também restringe rotas de ofertas. Não vamos contornar CAPTCHA, bloqueios ou limites com proxies, fingerprints e navegador.

## Decisão

- Criar um pipeline de **ingestão de catálogo CSV autorizado**, preparado para a substituição por integração oficial ou feed licenciado. Um CSV manual funciona também como fixture de desenvolvimento; não representa coleta automática.
- Cada linha contém ID estável do anúncio, título, preço em **centavos inteiros** e URL HTTPS do domínio do Mercado Livre.
- Guardar 1 observação por produto por hora em SQLite, com migração aditiva de schema v1 para v2 e preservação de todos os registros anteriores.
- Exigir **duas observações anteriores em horas distintas** antes de declarar queda. Comparar o preço atual ao **menor preço anteriormente observado pelo nosso coletor**, e criar um DRAFT somente se cair pelo menos 15% (configurável). Não confundir essa comparação com histórico oficial nem com oferta garantida.
- Deduplicar por (item ID, preço da queda) para evitar múltiplas ofertas iguais e nunca modificar itens aprovados/publicados.
- Zero disparos para WhatsApp, aprovações automáticas, requisições HTTP ao marketplace ou scheduler nesta etapa.

## Consequências

O MVP permite persistência, avaliação e aprovação de dados de terceiros **com acesso autorizado** e sem browser; ainda não é descoberta automática independente. Necessita fornecedor licenciado/contrato ou aprovação de integração oficial. Não gerar URLs de afiliados automaticamente nem chamar links diretos de afiliados. A promoção deve ser verificada antes de publicar.
