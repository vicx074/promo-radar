# Promo Radar

Backend para curadoria de promoções de tecnologia e publicação manualmente aprovada em **grupo próprio do WhatsApp**, usando Python, FastAPI, SQLite e Evolution API v2.

**Estado atual: fundação / MVP 0.1.** API administrativa, banco SQLite, backup consistente, adapter Evolution, aprovação de ofertas, preview, registro durável de envio e testes. **Ainda não existem** coleta automática de marketplaces, geração de links de afiliados, painel, scheduler ou integração real validada com WhatsApp.

## Documentação e regras de IA

- [Arquitetura](ARCHITECTURE.md)
- [ADRs](docs/decisions/)
- [Contrato de ofertas](docs/contracts/offers.md)
- [Contrato de publicação](docs/contracts/publications.md)
- [Operação/backup](docs/operations.md)
- [Conexão Evolution API: QR, grupos e primeiro envio](docs/evolution-connection.md)
- [Instruções de IA](AGENTS.md)

Nenhum agente deve modificar invariantes sem revisar contratos, testes e ADRs. SEND_ENABLED é **false** por padrão. Baileys é integração não oficial, sujeita a desconexões e políticas do WhatsApp.

## Executar localmente

Pré-requisito: Docker e Docker Compose. A implantação padrão expõe somente 127.0.0.1:8000 (FastAPI) e 127.0.0.1:8080 (Evolution) no host; PostgreSQL e Redis não têm portas públicas.

```bash
cp .env.example .env
# Configure ADMIN_API_KEY, EVOLUTION_API_KEY e POSTGRES_PASSWORD com segredos fortes distintos.
docker compose up -d --build
docker compose ps
curl http://127.0.0.1:8000/health
```

Swagger local: http://127.0.0.1:8000/docs — endpoints administrativos exigem `x-admin-key`.

## Fluxo do MVP

1. Criar oferta por POST /api/v1/offers com source, source_item_id, title, price_cents, reference_price_cents (opcional) e affiliate_url HTTPS.
2. Aprovar por POST /api/v1/offers/{id}/approve.
3. Revisar por GET /api/v1/offers/{id}/preview.
4. Após parear instância Evolution e validar um grupo próprio de testes, configurar WHATSAPP_GROUP_ID e SEND_ENABLED=true, recriar o container bot e publicar por POST /api/v1/offers/{id}/publish.
5. Verificar publicação por GET /api/v1/publications/{id}. Não reenviar UNKNOWN/SENDING automaticamente.

A Evolution aceita texto pelo endpoint POST /message/sendText/{instance} com header `apikey` e corpo `{number,text}`. O contrato real e o QR devem ser verificados na versão implantada; HTTP 2xx **não significa entregue**.

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
