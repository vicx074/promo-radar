# Busca sob demanda por nicho (PR #4)

**Esta etapa não consulta o Mercado Livre pela rede.** Busca somente no CSV de catálogo autorizado, carregado pelo operador, e não cria tarefas recorrentes. O frontend poderá trocar a fonte por uma API oficial/licenciada sem alterar o contrato de busca e seleção.

## Preparar dados

Em `C:\Projestos pessoais\promo-radar`:

```powershell
New-Item -ItemType Directory -Force data\import | Out-Null
@'
source_item_id,title,price_cents,product_url,image_url
MLB_TESTE_01,Mouse Gamer Ficticio,19990,https://www.mercadolivre.com.br/p/MLB1234567890,
MLB_TESTE_02,Teclado Mecanico Ficticio,27990,https://www.mercadolivre.com.br/p/MLB9999999999,
'@ | Set-Content .\data\import\catalogo.csv -Encoding utf8

docker compose up -d --build bot
```

Esses produtos/links são fictícios e **não devem ser publicados como ofertas reais**. Em operação real, substituir por catálogo válido e autorizado com URLs de imagem `https://http2.mlstatic.com/...` quando disponíveis. O arquivo pode ter coluna opcional `image_url`, sendo esse o campo da imagem principal.

## Busca e seleção no PowerShell

```powershell
$apiKey = ((Get-Content .env | Where-Object { $_ -match '^ADMIN_API_KEY=' } | Select-Object -First 1) -replace '^ADMIN_API_KEY=', '').Trim()
$headers = @{ 'x-admin-key' = $apiKey }
$body = @{ query = 'mouse'; limit = 10 } | ConvertTo-Json
$search = Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/discovery/search' -Method Post -Headers $headers -ContentType 'application/json; charset=utf-8' -Body $body
$search | ConvertTo-Json -Depth 6

# Selecionar apenas o primeiro resultado; cria DRAFT, não aprova, não envia:
if ($search.items.Count -gt 0) {
  $chosen = @{ search_id = $search.search_id; source_item_ids = @($search.items[0].source_item_id) } | ConvertTo-Json
  Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/discovery/select' -Method Post -Headers $headers -ContentType 'application/json; charset=utf-8' -Body $chosen | ConvertTo-Json -Depth 5
}
```

`search_id` dura 45 minutos. A seleção usa o snapshot que o servidor salvou, portanto o CSV pode mudar sem trocar silenciosamente os detalhes da oferta selecionada. Uma nova busca é necessária depois do vencimento.

## Limites

- `POST /api/v1/discovery/search`: `{ "query": "notebook", "limit": 20 }`; resultados `search_id`, `expires_at`, `items`. A busca é textual nos títulos, sem comprovação de categoria/preço promocional.
- `POST /api/v1/discovery/select`: `{ "search_id": "uuid", "source_item_ids": ["MLB..."] }`; seleciona 1–20 IDs, cria ofertas DRAFT ou retorna já existentes sem modificá-las.
- `image_url` será incluída na oferta escolhida. A imagem otimizada precisa ser preparada separadamente, antes da aprovação.
- Sem agendamento ou WhatsApp automático. Deixar `SEND_ENABLED=false` durante os testes.
- O `affiliate_url` herdado do schema v1 recebe a URL comum do produto. **Não tratar como link de afiliado real.**
