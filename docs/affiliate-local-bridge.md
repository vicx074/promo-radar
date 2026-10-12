# Vinculação automática de links com a conta de afiliado do titular

**Atenção:** o worker utiliza endpoints **internos/não oficiais** da Central de Afiliados do Mercado Livre, inspirados no open source `sophismartai-sudo/ml-afiliados`. Ainda **não foi testado em uma conta real**. A disponibilidade do endpoint e a atribuição de comissão **não são garantidas**. Não executar sem consentimento do titular e observância dos termos da plataforma.

## Fluxo

O pai (único operador) entra no Promo Radar pelo computador ou celular, pesquisa um nicho, seleciona produtos e aguarda a geração de links. Cada item selecionado vai para DRAFT com um job PENDING, sem aprovação/publicação. Um worker rodando no computador do titular, com Chrome em **perfil dedicado**, usa a sessão que ele próprio abriu na Central de Afiliados para solicitar o link. O backend compara o produto retornado e o link, vincula quando coincidem, e mostra LINKED; senão FAILED. A página Ofertas permite acompanhar o status ou pedir nova tentativa.

**Para gerar pelo celular, o computador deve permanecer ligado e o worker aberto.** A VPS NÃO recebe cookies, senha, perfil do navegador ou QR do Mercado Livre. O token do worker autoriza **apenas** claim/complete/heartbeat, nunca publicar mensagens.

## Preparação da chave (uma única vez)

No terminal privado do computador, gere um segredo para o **Promo Radar**:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Coloque o mesmo segredo, com pelo menos 40 caracteres, **em dois locais privados**: `AFFILIATE_BRIDGE_TOKEN` no `.env` usado pelo backend e na variável de ambiente do processo do worker no computador. **Esse token não é do Mercado Livre.** Não envie nenhum dos tokens pelo chat, nem grave em GitHub.

No `.env` do backend:
```dotenv
AFFILIATE_BRIDGE_TOKEN=SEU_SEGREDO_ALEATORIO_COM_NO_MINIMO_40_CARACTERES
AFFILIATE_AUTO_QUEUE=true
SEND_ENABLED=false
```

Não sobrescreva o `.env` atual; apenas acrescente as variáveis. Não faça `docker compose down -v`, pois pode apagar volumes persistentes da Evolution API.

Atualize somente os serviços web e bot:
```powershell
docker compose up -d --build bot web
```

Para começar **somente no computador local**, a aplicação pode estar em `http://127.0.0.1:8000` e o conector rodar na mesma máquina. A aplicação com `SINGLE_OWNER_MODE=true` exige HTTPS e não pode ser usada em HTTP sem reconfigurar corretamente o ambiente de desenvolvimento. **Para a VPS** mantenha `SINGLE_OWNER_MODE=true` e acesso apenas por Tailscale Serve HTTPS.

## Worker no computador Windows

Abra um terminal PowerShell separado na pasta do repositório:

```powershell
python -m pip install -r agent/requirements.txt
$env:PROMO_BASE_URL = "http://127.0.0.1:8000"
$env:AFFILIATE_BRIDGE_TOKEN = "MESMO_SEGREDO_ALEATORIO_DO_BACKEND"
python agent/affiliate_worker.py
```

Se o Promo Radar estiver na VPS, use a URL HTTPS da tailnet em `PROMO_BASE_URL` e instale/ative Tailscale no computador do seu pai. **Nunca use HTTP público**.

O worker abre o Chrome em um perfil local independente (`agent/.chrome-profile`, ignorado pelo Git). O titular faz login na Central de Afiliados na janela que abriu e pressiona ENTER no terminal. Não é necessário informar senha ao aplicativo. Deixe a janela e o terminal abertos. Se o site solicitar autenticação novamente, faça o login na mesma janela e clique `Tentar novamente` no produto que falhou. **Nunca exporte cookies ou ative depuração remota para esse fluxo**.

A aba do site precisa continuar autenticada. Endpoints internos identificados pelo repositório open source:

- `GET /affiliate-program/api/v2/stripe/user/tags`: consulta tag ativa.
- `POST /affiliate-program/api/v2/stripe/user/links`: recebe URL e tag ativa e tenta gerar `short_url` e `origin_url`.

O worker só transmite à VPS o URL de produto, o link curto devolvido e o URL de origem para conferência. Não transmite a tag, cookies ou credenciais do site; confere a tag localmente.

## Verificação de busca real via Apify

A Apify é um **serviço de scraping terceirizado**, separado do Chrome. A API já está conectada no projeto, mas testes CI usam mocks; para comprovar a busca real, configure `APIFY_TOKEN` somente no backend e solicite conscientemente **uma consulta que pode ser cobrada**:

```powershell
python -m app.apify_probe "mouse gamer" --run-paid-probe
```

Execute onde `APIFY_TOKEN` esteja presente como variável de ambiente (Python não carrega `.env` automaticamente), preferencialmente dentro do container backend que recebeu a variável:
```powershell
docker compose exec -T bot python -m app.apify_probe "mouse gamer" --run-paid-probe
```

O teste busca até 10 produtos com limite de custo na API Apify. Anote somente número de resultados, alguns títulos e as URLs públicas; confira no site se existem. **Não compartilhe credenciais**. A página **Configurações** informa se APIFY_TOKEN foi configurado (não significa que a coleta externa foi validada).

## Diagnóstico

- Conector OFFLINE: computador desligado, worker não iniciado, token diferente, Tailscale sem conexão.
- PENDING: aguardando o Chrome local consumir o pedido. No computador desligado, pedidos aguardam.
- PROCESSING: o navegador iniciou a geração. Se passar 120s sem confirmação vira FAILED, **sem retry automático**.
- LINKED: link estruturalmente válido e URL de origem coincidente, **sem atestar comissão**.
- FAILED: conta deslogada, endpoint interno falhou, produto não coincide ou houve timeout. Reabra a Central de Afiliados, faça login se preciso e pressione `Tentar novamente`.
- Cadastro manual permanece disponível, e sempre cancela a tarefa automática daquele rascunho.
- O link gerado **não aprova nem envia** a oferta. Continuam obrigatórios: preparo da imagem, aprovação explícita, `SEND_ENABLED=true` e grupo autorizado.

## WhatsApp já pareado no computador

O número conectado na **Evolution local** é um avanço, mas **não equivale a uma instância conectada na VPS**. Se o bot for movido para a VPS com o `EVOLUTION_BASE_URL` interno do Compose, será outra instalação, e o pareamento existente não migra automaticamente. Preserve os volumes; teste primeiro localmente e planeje separadamente mover ou conectar a Evolution da VPS, sem alterar o número pareado sem autorização.
