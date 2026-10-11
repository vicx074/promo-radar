# Acesso privado ao Promo Radar em uma VPS

Arquitetura para **uma pessoa**, sem SaaS: navegador no seu computador ou celular -> **Tailscale Serve HTTPS** -> Nginx em localhost:5173 -> FastAPI e SQLite em localhost:8000 / rede Docker -> Evolution API. A VPS não precisa de porta web pública.

## 1. Preparar a VPS
Instale Docker/Compose e Tailscale conforme documentação oficial, mantenha acesso SSH de recuperação, configure backups e confirme que as portas 5173, 8000 e 8085 não estão publicadas no firewall. A rede Tailscale deve ter ACL/grants que restrinjam acesso à sua conta/dispositivos. **Não habilite Tailscale Funnel**, pois Funnel publica na internet.

Confirme no `compose.yaml` que as portas expostas do `web`, `bot` e `evolution` estão ligadas a `127.0.0.1`, e que PostgreSQL/Redis não expõem portas no host.

## 2. Configurar a única senha

Crie seu `.env` na VPS a partir de `.env.example` (se não tiver um existente). Gere senhas exclusivas para `EVOLUTION_API_KEY` e `POSTGRES_PASSWORD`, mantenha `SEND_ENABLED=false`.

Gere o hash Argon2id **interativamente**, sem imprimir a senha no terminal/issue:
```bash
docker compose run --rm --no-deps bot python -m app.auth hash-password
```
Se o container `bot` ainda não foi compilado, execute `docker compose build bot` antes. O comando imprime somente o hash `$argon2id$...`.

No arquivo `.env` (nunca no Git), acrescente/ajuste:
```dotenv
# Use o hash REAL que o comando gerou, entre aspas simples
OWNER_PASSWORD_HASH='$argon2id$v=19$m=...'
SINGLE_OWNER_MODE=true
ALLOW_ADMIN_API_KEY=false
SESSION_COOKIE_SECURE=true
SEND_ENABLED=false
```
As aspas simples são importantes: evitam que o Compose interprete os caracteres `$` do hash como substituição de variáveis. O hash de exemplo acima **não funciona**; use o seu. Mantenha o hash fora de logs, prints e Git.

Execute:
```bash
docker compose up -d --build
docker compose ps
curl -fsS http://127.0.0.1:8000/health
```
Na VPS, o backend **recusa iniciar** se faltar `OWNER_PASSWORD_HASH`, se houver `SESSION_COOKIE_SECURE=false` ou se `ALLOW_ADMIN_API_KEY=true`.

## 3. Publicar somente dentro da sua tailnet

Depois de conectar a VPS à sua tailnet e habilitar HTTPS para o domínio `.ts.net`, use:
```bash
sudo tailscale serve --bg http://127.0.0.1:5173
tailscale serve status
```
Abra **a URL HTTPS `.ts.net` retornada**, estando logado no Tailscale no celular ou computador. O Tailscale Serve restringe o acesso à tailnet; **não use `tailscale funnel`**.

Documentação oficial: https://tailscale.com/docs/features/tailscale-serve e https://tailscale.com/docs/reference/tailscale-cli/serve.

## 4. Entrar, sair e recuperar acesso
Entre com a senha escolhida; o navegador nunca vê `ADMIN_API_KEY` ou o hash. Somente um login fica ativo por vez. O cookie Secure+HttpOnly+SameSite=Strict usa sessão de 12 horas no máximo ou 30 minutos sem atividade, o que acontecer primeiro. **Sair** revoga a sessão no SQLite. Alterar a senha/hash no `.env` requer reiniciar o `bot` e, para revogar sessões existentes, limpar a tabela `owner_sessions` com manutenção de banco ou fazer novo login.

Se perder acesso à senha, entre na VPS **por um canal administrativo seguro**, gere novo hash pelo comando e substitua `OWNER_PASSWORD_HASH` no `.env`; não existe recuperação por e-mail.

Em desenvolvimento local **sem HTTPS** (jamais na VPS), opcionalmente configure `SINGLE_OWNER_MODE=false` e `SESSION_COOKIE_SECURE=false`, apenas em localhost. O proxy Vite `/api` e as rotas de autenticação são as mesmas.

## 5. Segurança operacional

Mantenha `SEND_ENABLED=false` até validar um destino próprio e permitido; `SENT` é aceite HTTP, não entrega. Faça backups frequentes do SQLite com o utilitário existente e dos dados Evolution, tenha restore testado; proteja o disco e limite permissões do `.env` (ex.: `chmod 600 .env`). Não cole cookies da Central Mercado Livre em nenhum lugar do sistema.

O login protege o **Promo Radar**, não conecta a conta de afiliado. Geração oficial automática de links, busca live e agendamento ainda não estão implementados.
