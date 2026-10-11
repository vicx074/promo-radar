# ADR 0012 — Busca real por nicho via provedor terceirizado de scraping

Status: implementado em branch, pendente prova autenticada real na VPS.

## Necessidade
A consulta CSV do MVP não atende ao requisito de pesquisar anúncios reais por termo. A API pública `/sites/MLB/search` tem relatos repetidos de 403, e requisições à página pública também podem ser bloqueadas. Não chamaremos um CSV de busca ao vivo.

## Decisão
1. Introduzir `ApifyCatalogProvider` chamando **um Actor específico** `gio21/mercado-livre-scraper` no serviço Apify. Este é **um scraper operado por terceiro** e **não é API oficial ou aprovada do Mercado Livre**. O usuário precisa definir `APIFY_TOKEN` **somente no backend** e revisar os termos de uso da plataforma e do provedor. Nunca enviar cookie ou senha ML, não implementar navegador furtivo, proxy rotativo, CAPTCHA bypass nem scraping direto da infraestrutura do Promo Radar.
2. Modo de produção: `DISCOVERY_PROVIDER=apify` (padrão ao ler env). Em `Settings` instanciado manualmente, o modo CSV continua o padrão para fixtures dos testes antigos; `DISCOVERY_PROVIDER=csv` permite a operação offline explícita. **Sem token → HTTP 503** e mensagem útil; nada de fallback silencioso de resultados do CSV.
3. Um único POST on-demand ao endpoint Apify oficial `/v2/acts/gio21~mercado-livre-scraper/run-sync-get-dataset-items` com Bearer header, `keyword`, `maxItems` pequeno, `maxPages=1`, `maxTotalChargeUsd=0.20`. Timeout 110s; não seguir redirects; nenhum token exposto em URL/browser/logs. Não executar automaticamente pesquisas ou serviços que gerem cobranças.
4. Parse de JSON externo rigoroso: preço em centavos `Decimal`, nome não vazio, link direto HTTPS do Mercado Livre (não aceitar URLs patrocinadas/de tracking, nem hosts falsos); imagem HTTPS do CDN `http2.mlstatic.com`; filtrar marcas explícitas de indisponibilidade. Produto sem ID recebe identificador estável SHA-256 truncado da URL. Nunca considerar desconto/estoque atual como verificado apenas pelo cartão de pesquisa.
5. Reusar o snapshot SQLite com expiração em 45 minutos e seleção humana que cria somente DRAFT. `source=mercado_livre`, `affiliate_url=null` até o operador cadastrar um link próprio; aprovação e envio continuam bloqueados pelas regras anteriores.
6. Frontend apresenta origem `Apify (terceiros)` e aviso de que preço/estoque precisam ser verificados. Não inventar produtos nem métricas promocionais.
7. Testes de integração HTTP em CI **mockados** não comprovam scraper ao vivo. Validação final requer `APIFY_TOKEN` real configurado pelo operador, com consulta autorizada ao Actor e confirmação manual dos dados.

## Riscos
Actor terceirizado pode mudar schema, ter falhas/403 e cobrar por uso. Mercado Livre pode restringir acesso conforme termos e regras. O operador é responsável por conferir permissão e dados antes da publicação. Monitorar custo, demanda e atualização; implementar no futuro cache e revalidação do preço antes de disparos agendados.
