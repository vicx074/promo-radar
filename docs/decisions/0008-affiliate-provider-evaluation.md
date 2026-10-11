# ADR 0008 — Pesquisa de geração automática de links de afiliados

Status: **avaliação, bloqueado para produção** · 2026-10-11.

## Objetivo

O Promo Radar pretende transformar URLs de produtos autorizados do Mercado Livre em links de afiliados reconhecidos pela conta do operador. O mecanismo deve ser independente da busca por nicho, preservar valores em centavos e nunca transformar uma URL comum em "afiliada" inventando parâmetros.

## Evidências do código público

- `Afilimax/mercado-livre-provider`, commit `f2594f9c1c52344d97679a10a096d90d31ad4a4a` (2026-09-01): TypeScript MIT; `createAffiliateUrl(url)` obtém token CSRF da página, envia `POST /affiliate-program/api/v2/stripe/user/links` com `{url,tag}`, cookies e cabeçalhos do navegador, retorna `short_url`.
- As dependências incluem `@xcrap/got-scraping-client`. Os testes básicos usam `global.fetch` falso. Os testes práticos do upstream dependem do arquivo `cookies.json` e, sem ele, retornam sem executar o teste real. **Um status verde não comprova geração funcional ou atribuição de comissão.**
- **Falha de segurança:** `fetchCsrfToken(url)` solicita a URL de entrada e envia no header `cookie` os cookies autenticados, sem validá-la como pertencente ao ML. Uma URL controlada por terceiros poderia receber a sessão. **Não instalar nem executar o provedor com cookies reais sem corrigir e auditar.**
- `sophismartai-sudo/ml-afiliados`, commit `1a3ab5054cef7ef7797fb932f04a099bd7bd9122` (2026-07-31): guia/skill que descreve chamadas `fetch` no Chrome autenticado e endpoints internos de tags, geração e busca. Não é SDK/API pública com SLA. O arquivo também documenta integração n8n de terceiros; não executar webhooks externos.
- `Afilimax/afilimax-cli`: depende de tag + cookies locais e/ou Chromium, não resolve sozinho permissão de uso da interface interna.

## Decisão

1. **Não integrar os endpoints internos automaticamente ao backend de produção agora.**
2. Criar workflow GitHub Actions separado: checkout do código upstream por **SHA fixo**, `npm ci --ignore-scripts`, `vitest` com teste unitário mockado, `npm run build` e harness próprio em `experiments/affiliate-provider/contract.cjs`. Nenhum segredo/cookie real ou rede Mercado Livre.
3. O harness verifica a estrutura `{url,tag}`, retorno `short_url` fictício e documenta de forma reproduzível o vazamento de cookie para URL arbitrária. **Esse teste verifica somente código, não a integração live.**
4. Para prosseguir em produção, exigir autorização aplicável do ML, autenticação que não exponha sessão, URLs estritamente allowlisted, redirecionamentos e DNS protegidos, tratamento de expiração e `429`, separação entre URL do produto e link de afiliado gerado, elegibilidade/atribuição de comissões confirmadas na Central.
5. Antes de qualquer disparo ao WhatsApp, confirmar o canal permitido e aprovação da campanha; não adicionar coleta ou envio periódico nesta pesquisa.

## Referências

- https://github.com/Afilimax/mercado-livre-provider/blob/f2594f9c1c52344d97679a10a096d90d31ad4a4a/src/index.ts
- https://github.com/Afilimax/mercado-livre-provider/blob/f2594f9c1c52344d97679a10a096d90d31ad4a4a/__tests__/index.spec.ts
- https://github.com/Afilimax/mercado-livre-provider/blob/f2594f9c1c52344d97679a10a096d90d31ad4a4a/__tests__/practical.spec.ts
- https://github.com/sophismartai-sudo/ml-afiliados/blob/1a3ab5054cef7ef7797fb932f04a099bd7bd9122/SKILL.md
