# Links de afiliado no Promo Radar

Esta etapa habilita **registro manual de links oficiais**, sem login e sem geração automática na Central de Afiliados. URLs de produtos não são tratadas como afiliadas.

## Fluxo

1. Buscar por nicho em `POST /api/v1/discovery/search` (CSV autorizado, não dados ao vivo) e selecionar ofertas. Uma oferta Mercado Livre surge como `DRAFT` com `product_url`, `affiliate_url=null`.
2. Abrir o produto na Central de Afiliados do Mercado Livre e, quando for elegível, gerar um link oficial para o produto.
3. Anexar o link com `POST /api/v1/offers/{id}/affiliate-link`:
```json
{"affiliate_url":"https://meli.la/LINK_EXEMPLO","product_match_confirmed":true}
```
O exemplo é fictício. A declaração é de responsabilidade do operador; o servidor confere o formato, mas não verifica a atribuição nem o produto de destino.
4. Preparar a imagem com `/prepare-media` enquanto DRAFT, caso exista `image_url`. Aprovar e revisar no preview.
5. A publicação continua dependente de `SEND_ENABLED=true`, ação explícita e destino autorizado. A legenda passa a usar **o link de afiliado cadastrado**, e não o link comum.

`GET /api/v1/affiliates/mercado-livre/status` retorna `DISCONNECTED` e capacidade de geração automática desabilitada até que exista um método autorizado.

## Compatibilidade

A coluna física legada `offers.affiliate_url` continua `NOT NULL` para preservar o SQLite v1 e FKs. A aplicação não a usa como link remunerado nas ofertas Mercado Livre: a API retorna `affiliate_url` a partir de `affiliate_link_url`. A migração v5 considera **todos os links ML anteriores como URLs comuns**, independentemente de aprovação. Registros de publicação anteriores não são apagados. Exige backup antes de migrar.
