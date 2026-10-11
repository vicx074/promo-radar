# ADR 0014 — Geração automática de links pela sessão local do operador

Status: implementação inicial, **ainda sem validação em uma conta real**.

## Problema
O operador quer selecionar produtos pelo celular ou PC e ter um link de afiliado correto vinculado automaticamente. Uma URL comum não contém necessariamente rastreamento. A API oficial do programa de afiliados não disponibiliza contrato público confirmado para essa operação. O open source `ml-afiliados` demonstra GET /affiliate-program/api/v2/stripe/user/tags e POST /affiliate-program/api/v2/stripe/user/links por sessão autenticada no navegador do usuário, mas ambos são **endpoints internos, instáveis e sujeitos a regras da plataforma**.

## Decisão
- Criar fila SQLite v7 `affiliate_link_jobs` de trabalhos com DRAFT, nunca aprovação/publicação. Quando `AFFILIATE_BRIDGE_TOKEN` e `AFFILIATE_AUTO_QUEUE=true` estiverem configurados, `POST /discovery/select` cria cada rascunho e insere um trabalho PENDING na mesma transação.
- Executar um **worker opt-in no próprio computador do titular**, que abre Chrome em perfil dedicado e solicita login pessoal na Central de Afiliados. O worker requisita `tags` e `links` dentro da página Mercado Livre via `fetch` de mesma origem; nenhum cookie, senha, QR ou perfil vai para a VPS. Não ativar remote debugging, proxy rotativo, contorno de CAPTCHA, exportação de cookies, nem acesso à conta do Mercado Livre no backend FastAPI.
- Comunicar o worker com o Promo Radar sobre HTTPS privado na tailnet (HTTP só em localhost), autenticando com segredo aleatório de no mínimo 40 caracteres por `Authorization: Bearer`. Essa credencial tem apenas autorização `heartbeat/claim/complete`, **não permite aprovar nem publicar**. Guardar somente em env local e env da VPS, jamais em Git/URL ou JS do frontend. Se comprometida, rotacionar.
- A resposta de geração inclui `short_url`, `origin_url`, tag retornada e tag ativa. O worker compara tags; o backend checa formato de URL de afiliado, destino original canônico ou mesmo ID de produto. Divergências nunca são vinculadas. O status `LINKED` significa associação estrutural, **não confirmação de comissão**.
- Persistir job PROCESSING antes de executar a chamada ao site; após 120s sem confirmação, FAILED/LEASE_EXPIRED, **sem retry automático**. Conflitos e erros deixam link vazio. Novo pedido manual do operador pode reencaminhar. Se o PC estiver desligado, trabalhos ficam PENDING; a UI mostra o estado. Nenhum envio WhatsApp é disparado automaticamente.
- Informar na UI se o worker foi visto nos últimos 90s, sem fingir conexão OAuth ou autenticação Mercado Livre verificada. Manter cadastro manual como alternativa.
- O worker é implementado em Python+Playwright e **requer o Chrome do próprio computador aberto**. Se o usuário desejar geração a partir do celular, o PC deve continuar ligado e com worker rodando; sem servidor remoto contendo cookies. O operador assume a necessidade de observar os termos do serviço e a disponibilidade desses endpoints internos.
- Usar `DISCOVERY_PROVIDER=apify` separadamente para pesquisa de anúncios sem credenciais ML, com `APIFY_TOKEN` privado. Uma execução real com token é requisito para afirmar coleta funcionando.

## Validado versus pendente
Testes automatizados podem validar fila, token, integridade, vínculo, isolamento, captura de respostas simuladas e migração v6→v7. Não comprovam disponibilidade dos endpoints privados no ML, conta de afiliado, comissões, busca real Apify, ou disponibilidade da VPS/PC. O primeiro teste externo requer login feito pessoalmente pelo titular e revisão dos resultados. Não armazenar nenhuma credencial real no repositório.
