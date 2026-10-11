# Promo Radar

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
