# Promo Radar

> **Modo de operação recomendado: painel privado para um único operador em VPS via Tailscale Serve HTTPS.** Acesso com senha Argon2id, sessão HttpOnly e CSRF, sem cadastro de usuários ou SaaS. Consulte [guia de implantação privada](docs/private-vps.md) e [ADR 0011](docs/decisions/0011-private-single-owner-auth.md). A senha entra somente no login do Promo Radar, nunca no Mercado Livre.

Backend para curadoria de promoções de tecnologia e publicação manualmente aprovada em **grupo próprio do WhatsApp**, usando Python, FastAPI, SQLite e Evolution API v2.

**Estado atual: fundação / MVP 0.1.** API administrativa, banco SQLite, backup consistente, adapter Evolution, aprovação de ofertas, preview, registro durável de envio e testes. **A descoberta automática de marketplaces e a geração de links de afiliados ainda não existem**; foi adicionada uma importação manual de catálogo autorizado com histórico de preços e geração de candidatos DRAFT. Não há painel nem scheduler. A integração real de WhatsApp deve ser validada por cada operador.

## Documentação e regras de IA

- [Arquitetura](ARCHITECTURE.md)
- [ADRs](docs/decisions/)
- [Imagem Docker da Evolution](docs/decisions/0004-evolution-image.md)
- [Descoberta Mercado Livre via catálogo autorizado](docs/mercado-livre-discovery.md)
- [ADR do coletor sem scraping não autorizado](docs/decisions/0005-mercado-livre-feed.md)
- [Contrato de ofertas](docs/contracts/offers.md)
- [Contrato de publicação](docs/contracts/publications.md)
- [Operação/backup](docs/operations.md)
- [Conexão Evolution API: QR, grupos e primeiro envio](docs/evolution-connection.md)
- [Instruções de IA](AGENTS.md)

Nenhum agente deve modificar invariantes sem revisar contratos, testes e ADRs. SEND_ENABLED é **false** por padrão. Baileys é integração não oficial, sujeita a desconexões e políticas do WhatsApp.

## Executar localmente

Pré-requisito: Docker e Docker Compose. A implantação padrão expõe somente 127.0.0.1:8000 (FastAPI) e 127.0.0.1:8085 (Evolution) no host; PostgreSQL e Redis não têm portas públicas.

```bash
cp .env.example .env
# Configure ADMIN_API_KEY, EVOLUTION_API_KEY e POSTGRES_PASSWORD com segredos fortes distintos.
docker compose up -d --build
docker compose ps
curl http://127.0.0.1:8000/health
```

Evolution Manager local: http://127.0.0.1:8085/manager. O mapeamento e o acesso são distintos: **host 8085 → container Evolution 8080**; o bot usa **http://evolution:8080** pela rede interna. Alterar `EVOLUTION_BASE_URL` no `.env` não altera o mapeamento de portas do Compose.

Swagger local: http://127.0.0.1:8000/docs — endpoints administrativos exigem `x-admin-key`.

## Imagem da Evolution API e primeiro deploy

A imagem fixada no Compose é `evoapicloud/evolution-api:v2.3.7` (ADR 0004). A tag antiga `atendai/evolution-api:v2.1.1` falhou com `pull access denied` no Docker Desktop do projeto. Mantemos **host 8085 -> container 8080**; o bot acessa internamente `http://evolution:8080`.

No Windows, use a pasta **`C:\Projestos pessoais\promo-radar`**: há outra cópia do projeto aninhada em `evolution-api`, que não deve ser utilizada neste deploy. Confira as credenciais **neste** `.env` sem compartilhá-las e não copie `.env.example` sobre as configurações existentes.

```powershell
cd 'C:\Projestos pessoais\promo-radar'
git pull origin feat/backend-foundation
docker compose pull evolution
docker compose up -d --build
docker compose ps
```

Se houver erro de inicialização, rode `docker compose logs --tail=100 evolution` e não utilize `down -v`: volumes nomeados da Evolution são persistentes. A disponibilidade da tag no Docker Hub não equivale a validação real de pareamento com WhatsApp.

## Fluxo do MVP

1. Criar oferta por POST /api/v1/offers com source, source_item_id, title, price_cents, reference_price_cents (opcional) e affiliate_url HTTPS.
2. Aprovar por POST /api/v1/offers/{id}/approve.
3. Revisar por GET /api/v1/offers/{id}/preview.
4. Após parear instância Evolution e validar um grupo próprio de testes, configurar WHATSAPP_GROUP_ID e SEND_ENABLED=true, recriar o container bot e publicar por POST /api/v1/offers/{id}/publish.
5. Verificar publicação por GET /api/v1/publications/{id}. Não reenviar UNKNOWN/SENDING automaticamente.

A Evolution aceita texto pelo endpoint POST /message/sendText/{instance} com header `apikey` e corpo `{number,text}`. O contrato real e o QR devem ser verificados na versão implantada; HTTP 2xx **não significa entregue**.

## Descoberta de preços sem Chromium

O comando `python -m app.discovery_cli` ingere um arquivo CSV de catálogo obtido de fonte **autorizada** (ou preenchido manualmente), registra um preço por produto por hora e cria DRAFT apenas após duas observações de referência e queda de pelo menos 15%. Não aprova ou publica. Não executa scraping não autorizado das páginas do Mercado Livre: seus termos e robots impõem restrições. Consulte [guia de importação](docs/mercado-livre-discovery.md).

```powershell
New-Item -ItemType Directory -Force data\import | Out-Null
notepad data\import\catalogo.csv
docker compose up -d --build bot
docker compose exec -T bot python -m app.discovery_cli /app/data/import/catalogo.csv
```

**Faça backup antes da atualização:** `app/storage.py` migra automaticamente bancos existentes de schema 1 para 2 sem descartar ofertas/publicações.

## Desenvolvimento sem Docker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
export ADMIN_API_KEY='uma-chave-forte'
python -m pytest -q
ruff check app tests
uvicorn app.main:app --reload
```

No Windows, ative com `.venv\\Scripts\\activate`. Configure as variáveis no ambiente: o Python não carrega .env automaticamente.

## Persistência

`./data:/app/data` mantém SQLite no disco host, fora da imagem. `docker compose up --build` e `docker compose down` preservam o arquivo. `docker compose down -v` remove volumes nomeados do PostgreSQL, Redis e instâncias Evolution, mas não o bind mount do bot. Perder a VPS/disco apaga os dados se não houver backup externo.

Backup online consistente, inclusive em WAL:

```bash
docker compose exec -T bot python -m app.backup /app/data/backups/offers-YYYYMMDD.db
```

Armazene cópia segura fora da VPS e teste restauração. Não copie somente o arquivo .db ativo. Consulte [runbook](docs/operations.md).

## Testes

`python -m pytest -q` exercita estado de ofertas, idempotência, aceite e falha incerta usando publisher fake; não equivale a teste real de envio via WhatsApp.

## Diagnóstico da Evolution API (sem enviar)

Com Compose executando e `SEND_ENABLED=false`:

```bash
docker compose exec -T bot python -m app.evolution_admin create
docker compose exec -T bot python -m app.evolution_admin status
docker compose exec -T bot python -m app.evolution_admin groups
```

Esses comandos criam/consultam a instância e listam os JIDs dos grupos; não enviam mensagens. Conexão QR no Evolution Manager e primeiro envio deliberado estão em [docs/evolution-connection.md](docs/evolution-connection.md). Não compartilhe JIDs, QR ou API keys em issues.

O CI agora também compila a imagem do bot e inicia somente o FastAPI para testar `/health`, sem autenticar WhatsApp. Isso não valida o container da Evolution nem o QR.

## Imagem principal nas promoções

A oferta agora pode receber `image_url` HTTPS. Após criar o DRAFT, execute `POST /api/v1/offers/{id}/prepare-media` **antes de aprovar**, para baixar imagem de host autorizado, otimizar JPEG com Pillow e salvar em `./data/media`. O preview mostra metadados e `image_ready`; a publicação usa uma mensagem única de imagem e legenda via `sendMedia`. Ofertas antigas sem imagem continuam enviando texto. Migração automática do schema 2 para 3. Leia [docs/media-offers.md](docs/media-offers.md) e [ADR 0006](docs/decisions/0006-media-offers.md).

A CI executa a suíte Python dentro e fora do container Docker e simula a requisição HTTP da Evolution. Isso **não** equivale à entrega real de imagem a um grupo: o teste end-to-end WhatsApp deve ser manual e autorizado.

## Busca por nicho sob demanda (PR #4)

O painel pode buscar **quando o operador solicitar**, sem coleta periódica. No modo legado `DISCOVERY_PROVIDER=csv`, o catálogo de entrada é o arquivo `./data/import/catalogo.csv`, fornecido de fonte autorizada ou preenchido manualmente — **o modo CSV não pesquisa anúncios ao vivo no Mercado Livre**. Para busca real via provedor terceirizado, configure `DISCOVERY_PROVIDER=apify` e `APIFY_TOKEN` (ADR 0012). `POST /api/v1/discovery/search` procura termos no título e devolve `search_id` + cards de produtos (preço em centavos, link e `image_url`, quando disponível). `POST /api/v1/discovery/select` seleciona IDs desse snapshot e cria apenas DRAFT, sem aprovação, otimização de imagem ou envio. A busca expira em 45 minutos, IDs repetidos são rejeitados e a seleção não altera ofertas existentes. A partir do DRAFT, o fluxo de imagem da PR #3 continua inalterado.

Consulte [guia de busca sob demanda](docs/on-demand-discovery.md) e [ADR 0007](docs/decisions/0007-on-demand-search.md). A CI testa busca e seleção em Python e Docker, com catálogo sintético e sem WhatsApp real.

## Links de afiliado reais (cadastro manual, schema v6)

A URL comum de produto foi separada da URL de divulgação do afiliado. `GET /api/v1/offers/{id}` apresenta `product_url` e `affiliate_url`, que fica `null` para Mercado Livre até o operador cadastrar explicitamente em `POST /api/v1/offers/{id}/affiliate-link`. Ofertas Mercado Livre não podem ser aprovadas nem publicadas sem cadastro. Não adicionamos login nem geração automática: o status da integração Mercado Livre permanece `DISCONNECTED`. **A validação do formato do link não comprova comissão nem que pertence à conta.** Veja [guia](docs/affiliate-links.md) e [ADR 0009](docs/decisions/0009-affiliate-links-foundation.md).

## Painel web React + Vite (PR #7)

O frontend está em `./web`, com **React 19, Vite 6, TypeScript, Motion/Fancy Components e ícones Lucide**. O Docker Compose adiciona `web` (Nginx) na porta **http://127.0.0.1:5173**, com proxy `/api` para o FastAPI, sem habilitar CORS aberto. Para desenvolver sem Docker, rode `npm install` e `npm run dev` na pasta `web`, mantendo FastAPI na porta 8000. Veja [guia do frontend](web/README.md) e [ADR 0010](docs/decisions/0010-vite-dashboard.md).

**Implementado no painel:** entrada por chave administrativa somente na memória, pesquisa no CSV local, seleção DRAFT, lista e revisão de ofertas, cadastro manual de link de afiliado, preparação de JPEG, prévia, aprovação, publicação manual mediante confirmação, estado da integração Mercado Livre e consulta de publicação conhecida por UUID.

**Não implementado neste frontend originalmente:** busca ao vivo no Mercado Livre (adicionada posteriormente via Apify, com token), conexão OAuth da conta de afiliado, geração automática de links, agendador, gerenciamento visual de grupos e lista completa de histórico. Essas telas mostram explicitamente as limitações, sem simular integração.

**Atenção:** antes de abrir o frontend, use uma versão do backend com migração SQLite v5 (PR #6). O painel não deve ser publicado diretamente na Internet com chave administrativa compartilhada. `SEND_ENABLED=false` continua o padrão. A existência da UI não equivale à validação real de comissão ou entrega ao WhatsApp.

## Autenticação para operador único (PR #8)

O painel **não pede ADMIN_API_KEY**: digite a senha privada configurada na VPS; o backend verifica hash Argon2id, cria sessão com token opaco e cookie `__Host-promo_session` (`Secure`, `HttpOnly`, `SameSite=Strict`). A sessão expira após até 12h ou 30 minutos sem atividade; um novo login revoga o anterior. Operações mutáveis exigem Origin e CSRF. Após 5 senhas erradas, o login fica bloqueado 15 minutos. A VPS deve usar `SINGLE_OWNER_MODE=true`, `ALLOW_ADMIN_API_KEY=false`, `SESSION_COOKIE_SECURE=true` e HTTPS Tailscale Serve. `SEND_ENABLED=false` segue como padrão.

As instruções históricas deste README relativas a digitar `ADMIN_API_KEY` referem-se apenas à API/CLI legada em ambientes de desenvolvimento; **não devem ser usadas para autenticar o navegador nem ativadas em VPS privada**. Os dados permanecem locais no SQLite e os segredos apenas na VPS. Veja [passo a passo da VPS](docs/private-vps.md).

## Busca real no Mercado Livre (provedor terceirizado)

O backend agora suporta `DISCOVERY_PROVIDER=apify`, usando um Actor de scraping terceirizado na Apify quando `APIFY_TOKEN` estiver configurado **apenas na VPS**. O modo CSV continua disponível explicitamente (`DISCOVERY_PROVIDER=csv`). Sem token, a busca retorna HTTP 503 e não inventa produtos. A interface identifica os resultados como coleta terceirizada; preços, disponibilidade e descontos devem ser verificados no anúncio. A busca continua manual, snapshots duram 45 minutos e a seleção só cria DRAFT — geração de link afiliado e envio automático continuam pendentes. Veja o [guia de configuração e validação](docs/live-mercado-livre-search.md) e [ADR 0012](docs/decisions/0012-live-ml-search.md).

## Interface responsiva Tailwind CSS 4 (PR #10)

O frontend permanece React + Vite, com **Tailwind CSS 4** para layout responsivo e Motion/Fancy Components para a microinteração do logo. Celular: quatro abas de navegação inferior, ações acessíveis por toque, busca e cards responsivos, seleção de produtos acima da barra inferior e revisão de oferta em coluna única; computador: sidebar e painel duplo. Veja [web/README.md](web/README.md) e [ADR 0013](docs/decisions/0013-tailwind-mobile-first.md). Testes E2E simulados em Chromium cobrem 320–1440px e não implicam integração real da conta Mercado Livre.

## Geração de links com conector local (fila SQLite v7)

Quando configurado `AFFILIATE_BRIDGE_TOKEN` (um segredo exclusivo **do Promo Radar**) e `AFFILIATE_AUTO_QUEUE=true`, selecionar produtos em Descobrir cria tarefas PENDING para cada DRAFT Mercado Livre. O computador do titular roda um **worker local Chrome/Playwright** com login pessoal na Central de Afiliados; o worker tenta usar endpoints **internos e não oficiais**, devolve `short_url` e `origin_url`, e o backend confere o vínculo antes de guardar. Acesse pelo celular ou computador, mas **o PC do titular deve estar ligado com o worker funcionando** para gerar links. Sem token/worker, cadastro manual continua disponível. Nenhum cookie/senha Mercado Livre sai do PC; geração nunca implica comissão confirmada, aprovação ou envio WhatsApp. Veja [guia passo a passo](docs/affiliate-local-bridge.md) e [ADR 0014](docs/decisions/0014-local-affiliate-bridge.md).

Para comprovar a busca real Apify (não apenas mocks), execute conscientemente o probe que **pode gerar cobrança**: `docker compose exec -T bot python -m app.apify_probe "mouse gamer" --run-paid-probe`, com `APIFY_TOKEN` configurado no backend. A CI não realiza chamadas faturáveis.

## Somente promoções reais identificadas pelo anúncio (ADR 0015)

No modo Apify, a busca retorna **somente anúncios que fornecem preço original riscado (`originalPrice`) superior ao preço atual (`price`) em pelo menos 1%**. No card aparecem o preço original, o preço atual e o percentual conservador calculado pelos valores da fonte. O snapshot SQLite v8 persiste a referência e a seleção leva os dois preços ao DRAFT e à prévia para WhatsApp. Sem preço original a linha não é considerada promoção; uma busca pode não encontrar nenhuma. O scraper consulta até 50 anúncios por busca para encontrar candidatos e pode consumir mais créditos, mantendo **um único pedido** e limite de custo configurado. Isso NÃO valida economia histórica: preços riscado/atual, estoque e elegibilidade de comissão devem ser revisados diretamente na plataforma antes de publicar. Veja [ADR 0015](docs/decisions/0015-promotion-only-discovery.md).
