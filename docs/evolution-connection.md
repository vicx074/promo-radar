# Conectar Evolution API v2 em ambiente local

Este runbook cobre somente grupo próprio autorizado e número de testes. Baileys não é oficial e pode desconectar ou causar restrições de conta. Nunca exponha QR, token ou JID publicamente.

## 1. Preparar e subir

```bash
cp .env.example .env
# Configure ADMIN_API_KEY, EVOLUTION_API_KEY e POSTGRES_PASSWORD fortes e distintos.
# Deixe SEND_ENABLED=false e WHATSAPP_GROUP_ID vazio.
docker compose up -d --build
docker compose ps
docker compose logs --tail=50 evolution
curl --fail http://127.0.0.1:8000/health
```

Se estiver numa VPS, use túnel SSH em vez de abrir a porta 8000/8080: `ssh -L 8000:127.0.0.1:8000 -L 8080:127.0.0.1:8080 usuario@ip-da-vps`.

## 2. Criar e conectar a instância

```bash
docker compose exec -T bot python -m app.evolution_admin create
```

Se já existir, a Evolution pode retornar erro. Não apague sessões sem verificar estado. Abra [Evolution Manager](http://127.0.0.1:8080/manager), indique URL `http://127.0.0.1:8080` e a chave `EVOLUTION_API_KEY`, selecione a instância `promocoes`, conecte e escaneie o QR em WhatsApp > Dispositivos conectados > Conectar dispositivo. A rota da interface varia por release; se necessário consulte a documentação da imagem fixada. Não salve QR em logs.

```bash
docker compose exec -T bot python -m app.evolution_admin status
```

Depois de parear, espere `Estado da instância: open`.

## 3. Descobrir grupo próprio

```bash
docker compose exec -T bot python -m app.evolution_admin groups
```

Escolha somente um grupo de testes sob seu controle. Copie o JID `...@g.us` para `WHATSAPP_GROUP_ID` no arquivo .env, sem publicá-lo em issues.

## 4. Validar sem enviar

Abra [Swagger](http://127.0.0.1:8000/docs) localmente. Informe `x-admin-key` para usar endpoints administrativos. Cadastre oferta com link HTTPS, aprove e consulte a prévia. Com `SEND_ENABLED=false`, `publish` retorna HTTP 409 sem enviar.

## 5. Primeiro envio deliberado

Com conexão `open`, grupo próprio e prévia revisada: altere `SEND_ENABLED=true` e rode `docker compose up -d --force-recreate bot`. Publique **uma única vez** pelo endpoint `POST /api/v1/offers/{id}/publish` e confira diretamente no WhatsApp. Estado `SENT` só prova aceite da Evolution, não entrega; `UNKNOWN` ou `SENDING` exigem reconciliação manual, não retry cego. Volte para `SEND_ENABLED=false` após o teste.

## Diagnóstico

- `docker compose logs --tail=100 evolution` (retire segredos antes de compartilhar).
- `docker compose logs --tail=100 postgres redis` para problemas de banco/cache.
- Não use `docker compose down -v` em dados reais: remove volumes nomeados da Evolution.
- Smoke de Docker ou adaptador fake não comprova pareamento nem envio real.

Referências: [criação de instância](https://docs.evoapicloud.com/api-reference/instance-controller/instance-create), [estado](https://docs.evoapicloud.com/api-reference/instance-controller/connection-state) e [grupos](https://docs.evoapicloud.com/api-reference/group-controller/fetch-all-groups).
