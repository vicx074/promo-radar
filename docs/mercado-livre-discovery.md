# Ingestão inicial de catálogo do Mercado Livre

A rotina **não faz scraping do Mercado Livre**: lê um CSV que você obteve com autorização, de API/fornecedor habilitado ou que preencheu manualmente. Não exige Chromium, não envia WhatsApp e não aprova ofertas.

## Arquivo de entrada

CSV UTF-8 com cabeçalho obrigatório:

```csv
source_item_id,title,price_cents,product_url
MLB1234567890,Mouse de teste,19990,https://www.mercadolivre.com.br/p/MLB1234567890
```

Exemplo **fictício**: IDs/URL são demonstrativos, não uma oferta comprovada. Não publique dados de teste em grupos reais. Use um ID de anúncio estável. O parser aceita até 500 linhas por arquivo, proíbe duplicatas, exige HTTPS do domínio mercadolivre.com.br e não aceita preços em reais: `19990` significa R$ 199,90.

No PowerShell na pasta `C:\Projestos pessoais\promo-radar`:

```powershell
New-Item -ItemType Directory -Force data\import | Out-Null
notepad data\import\catalogo.csv
docker compose up -d --build bot
docker compose exec -T bot python -m app.discovery_cli /app/data/import/catalogo.csv
```

**Atenção:** o SQLite existente é atualizado automaticamente de schema 1 para 2. Faça o [backup consistente](operations.md) antes de executar a nova versão pela primeira vez.

A primeira execução registra referência sem criar oferta. Uma segunda observação em **outra hora** consolida histórico. Uma terceira observação, em hora posterior, somente gera DRAFT se o preço cair pelo menos 15% comparado ao menor preço já visto. Repetir a mesma hora não gera novos dados. Exemplo:

- 11h: R$ 200,00
- 12h: R$ 200,00
- 13h: R$ 160,00 → DRAFT com referência histórica R$ 200,00

Para modificar o limiar:

```powershell
docker compose exec -T bot python -m app.discovery_cli /app/data/import/catalogo.csv --min-drop-percent 20
```

Revise as ofertas em `http://localhost:8000/docs` com `GET /api/v1/offers` (header `x-admin-key`). Ofertas importadas **não estão aprovadas nem publicadas**. O campo `affiliate_url` do contrato existente armazena a URL fornecida; ela é inicialmente um link de produto comum, não necessariamente afiliado.

## Limites conhecidos

- Sem descoberta automática: depende de CSV atualizado por fonte autorizada.
- Não verifica frete, disponibilidade, reputação ou condições PIX e parcelamento.
- Não valida se um preço é realmente uma promoção; detecta somente queda contra nosso próprio histórico.
- Não há job em background; a execução é manual por ora.
- Sem mecanismos para contornar bloqueios, sessões, CAPTCHA ou restrições de coleta da plataforma.

Próxima etapa: ligar um provedor de feed licenciado ou uma API oficial aprovada ao mesmo formato do pipeline, mantendo baixo consumo de memória.
