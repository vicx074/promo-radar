# Pesquisa real no Mercado Livre — modo live via Apify

A rota **`POST /api/v1/discovery/search`** agora usa um scraper terceirizado que devolve anúncios obtidos da busca do Mercado Livre quando o backend está configurado com `DISCOVERY_PROVIDER=apify`. **Não é API oficial do Mercado Livre, nem gera links de afiliado.** Os resultados estão sujeitos a preços desatualizados, indisponibilidade, bloqueios, custo por consulta e mudanças no Actor.

## Ativar na VPS

1. Acesse https://apify.com/gio21/mercado-livre-scraper , veja o preço atual, a documentação do Actor e faça uma busca de teste na própria Apify. É necessário uma conta na Apify, e podem existir cobranças.
2. Gere um **API token Apify** no painel da sua conta. Adicione somente ao **`.env` privado da VPS**; nunca em GitHub, frontend ou em URLs.
3. Configure:
   ```dotenv
   DISCOVERY_PROVIDER=apify
   APIFY_TOKEN=seu_token_apify_privado
   SEND_ENABLED=false
   ```
4. Reinicie o backend com `docker compose up -d --build bot web`.
5. Entre na tela **Descobrir** do Promo Radar pela URL HTTPS do Tailscale e pesquise, por exemplo, **mouse gamer**.
6. Escolha apenas produtos que realmente correspondem ao anúncio, conferindo preço/estoque/entrega na página do produto. A seleção cria **DRAFT**, não aprova nem envia. O link de afiliado ainda deve ser gerado manualmente na Central e cadastrado na revisão.

**Sem APIFY_TOKEN**, a rota retorna 503 e indica como configurar. Não troca silenciosamente por CSV. Para usar o modo offline intencionalmente, defina `DISCOVERY_PROVIDER=csv` e forneça `data/import/catalogo.csv`.

## Limites implementados

- Pesquisa apenas quando uma pessoa clica em buscar; **nenhum scheduler**, nenhuma pesquisa periódica ou envio.
- `maxPages=1`, até 50 produtos (20 na interface atual) e teto informado à Apify de **US$0,20 por consulta**, conforme suporte da API; verifique o faturamento real na sua conta.
- O token vai em **Authorization: Bearer** apenas entre FastAPI e `api.apify.com`, nunca em query, cookie, log ou cliente React.
- Cada item deve ter título, preço numérico e link direto HTTPS de produto do Mercado Livre. URLs patrocinadas de tracking, sites externos e preços incoerentes são descartados. Imagens só do CDN do Mercado Livre.
- O resultado informa `provider: apify_live`, `live: true`, `promotion_verified:false` e `price_history_available:false`. **Não garantimos desconto, estoque, frete nem comissão** apenas por resultados de busca.
- Snapshot SQLite de 45 minutos e seleção de até 20 produtos preservam os valores vistos na pesquisa. Uma busca posterior não altera produtos já aprovados; publicação exige link afiliado cadastrado, revisão e SEND_ENABLED.
- O provedor é **terceirizado e opera scraping**; verifique termos de uso e a autorização para utilização comercial dos dados. Não há código de bypass, proxy rotativo, CAPTCHA ou autenticação ML neste repositório.

## Verificação real pendente

Os testes Python/CI utilizam `httpx.MockTransport` e preços **fictícios**, e só demonstram integração e filtros do nosso código. Para afirmar que a busca externa **funciona na sua VPS**, é necessário um token válido, conta ativa/saldo e confirmar pelo menos uma consulta real com título, imagem, preço e URL existentes. Não temos acesso à sua conta Apify e nenhum teste CI consome sua quota sem pedido explícito.
