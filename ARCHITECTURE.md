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

## Separação de links e estado da integração (PR #6)

O schema v5 preserva o `affiliate_url` físico legado para compatibilidade SQLite e acrescenta `product_url` + `affiliate_link_url`, que é a fonte da `affiliate_url` exposta pela API para ML. A migração nunca assume que a URL legada de produto gera comissão. O cadastro de link oficial exige confirmação do operador em uma oferta DRAFT; sem ele não há aprovação nem publicação. `affiliate_integrations` mantém Mercado Livre `DISCONNECTED` enquanto não houver autorização formal; não persiste cookies e não fornece login simulado. Veja [ADR 0009](docs/decisions/0009-affiliate-links-foundation.md).

## Frontend React + Vite

SPA React 19/TypeScript em `web/`, com componentes reutilizáveis, microinteração Fancy Components (MIT), renderização de imagens limitada ao CDN conhecido. Em desenvolvimento, Vite faz proxy de `/api` ao FastAPI; em produção local, Nginx no Compose em 127.0.0.1:5173 reencaminha `/api` para `bot:8000`. O backend continua único dono das regras de negócio, autenticação administrativa, SQLite e chamadas Evolution. `x-admin-key` só fica no estado React, sem cookies nem armazenamento permanente; uso local de administrador, não segurança multiusuário. O estado de geração automática e o agendador permanecem ausentes. Veja [ADR 0010](docs/decisions/0010-vite-dashboard.md).

## Autenticação de operador único na VPS (schema SQLite v6)

Não é SaaS. `app/auth.py` mantém uma única sessão ativa, revogável no SQLite (hash SHA-256 do token; cookie opaco `__Host-promo_session`; CSRF em header; Argon2id para senha). `POST /api/v1/auth/login`, `GET /api/v1/auth/session` e `POST /api/v1/auth/logout` controlam a sessão. Todas as rotas `/api/v1/*` operacionais exigem cookie de sessão com Origin/CSRF em escrita; a chave legada só continua como opção de CLI/CI local, e **não pode ser ativada** em modo VPS `SINGLE_OWNER_MODE=true`. Limite de tentativas e revogação são persistentes. Acesso remoto exclusivamente pela tailnet via TLS do Tailscale Serve, com Nginx e bot presos a localhost. [ADR 0011](docs/decisions/0011-private-single-owner-auth.md).

## Busca live de produtos por nicho — provedor Apify (ADR 0012)

Em produção `DISCOVERY_PROVIDER=apify` lê anúncios reais a cada solicitação do operador por meio do scraper terceirizado `gio21/mercado-livre-scraper` na Apify, exigindo `APIFY_TOKEN` privado. O adapter `app/live_catalog.py` valida títulos, preço BRL em centavos, link e imagem; não identifica desconto comprovado nem garante estoque ou atribuição de comissão. Sem credenciais responde 503; o backend **não** usa o CSV silenciosamente. O modo CSV fica disponível explicitamente para testes/offline via `DISCOVERY_PROVIDER=csv`. A seleção mantém os snapshots SQLite, DRAFT e bloqueios de publicação existentes. Este Actor é terceirizado e o serviço é pago conforme uso; a API oficial ML não é usada para pesquisa geral.

## Layout mobile-first Tailwind CSS 4

Vite usa plugin `@tailwindcss/vite`; o frontend compõe classes de layout Tailwind em JSX, mantendo classes cosméticas em `styles.css` na camada `components`. Em dispositivos de até 767px, a navegação ocorre por tabs fixas inferiores, com safe-area iOS; a partir de 768px, sidebar fixa. O grid de ofertas simplifica para coluna única no tablet/celular e painel duplo no desktop largo. Tarefas de negócio, sessão HttpOnly e API FastAPI são inalteradas. E2E Chromium via Playwright simula API e confere ausência de overflow horizontal. Ver [ADR 0013](docs/decisions/0013-tailwind-mobile-first.md).
