# Arquitetura do Promo Radar

Monólito modular Python/FastAPI. Admin HTTP -> SQLite (ofertas e publicações); somente ação de publicação explícita -> Evolution API v2 (Baileys) -> grupo autorizado.

Domínio em app/domain.py; adaptadores app/storage.py (SQLite WAL) e app/evolution.py (HTTP); borda HTTP app/main.py. Banco em /app/data/offers.db persistido por bind mount ./data do host; serviços da Evolution usam PostgreSQL e Redis com volumes separados. Sem scraping não autorizado, scheduler, webhook ou UI nesta fase. A descoberta por CSV local autorizado registra histórico de preços no SQLite e cria candidatos DRAFT quando encontra uma queda contra o menor preço já observado, sem chamar Evolution.

Estado: oferta DRAFT -> APPROVED; publicação ausente -> SENDING -> SENT | UNKNOWN. SENDING é registrado antes do HTTP. SENT é aceitação da Evolution, não comprovação de entrega. UNKNOWN e SENDING após crash exigem reconciliação manual e não permitem retry cego.


## Ferramenta de diagnóstico

`app/evolution_admin.py` implementa somente criação de instância, consulta de conexão e listagem de grupos da Evolution API. Não oferece envio fora do caso de uso de publicação, que permanece protegido pelo controle de aprovação. Pareamento de QR via Manager é manual. Confira o runbook `docs/evolution-connection.md`.

## Descoberta Mercado Livre (fase inicial)

`app/discovery.py` valida feed CSV de origem autorizada, guarda preços por hora em `price_observations` (schema SQLite v2), e cria somente DRAFT se houver duas observações anteriores e queda mínima frente ao menor preço histórico. `app/discovery_cli.py` executa a importação manual. Nunca publica, aprova ou chama o Mercado Livre. Veja [ADR 0005](docs/decisions/0005-mercado-livre-feed.md) e [guia](docs/mercado-livre-discovery.md).

## Mídia (PR #3)

`app/media.py` prepara JPEG antes da aprovação em `POST /offers/{id}/prepare-media`, armazenando bytes no volume e metadados em SQLite schema v3. `app/evolution.py` envia uma imagem mais caption usando `sendMedia` quando preparada; texto legado usa `sendText`. O preview lê apenas o banco. Vide [ADR 0006](docs/decisions/0006-media-offers.md).

## Busca pontual e revisão antes de qualquer campanha

`app/catalog.py` define provider substituível `CatalogProvider` com implementação inicial `CsvCatalogProvider`. `POST /api/v1/discovery/search` só consulta quando solicitado, salva resultados completos no SQLite schema v4 e expira em 45 minutos. `POST /api/v1/discovery/select` aceita apenas IDs presentes nesse snapshot e cria ofertas DRAFT idempotentes, preservando preço/link/imagem do momento da busca. Não há coleta periódica, scheduler nem disparos nesta fase. Veja [ADR 0007](docs/decisions/0007-on-demand-search.md).
