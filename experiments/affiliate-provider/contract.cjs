/* Avaliação offline do pacote @afilimax/mercado-livre-provider.
 * Todos os fetch() são simulados, sem credenciais, cookies reais ou chamadas ao ML.
 */
"use strict";

const assert = require("node:assert/strict");
const path = require("node:path");

const { MercadoLivreProvider } = require(
  path.resolve(__dirname, "../../../upstream-provider/dist/index.js")
);

const COOKIE_VALUE = "FAKE-COOKIE-DO-NOT-USE";
const CSRF_VALUE = "FAKE-CSRF";
const PRODUCT = "https://produto.mercadolivre.com.br/MLB-12345678-teste-_JM";
const INTERNAL = "https://www.mercadolivre.com.br/affiliate-program/api/v2/stripe/user/links";
const provider = new MercadoLivreProvider({
  tag: "tag-ficticia",
  cookies: [
    { name: "_csrf", value: CSRF_VALUE },
    { name: "session", value: COOKIE_VALUE },
  ],
});

async function main() {
  const calls = [];
  global.fetch = async (url, options = {}) => {
    calls.push({ url: String(url), ...options });
    if (String(url) === INTERNAL) {
      return {
        ok: true,
        json: async () => ({ short_url: "https://meli.la/LINK_FICTICIO" }),
      };
    }
    return {
      ok: false,
      status: 404,
      text: async () => "not found",
    };
  };

  const link = await provider.createAffiliateUrl(PRODUCT);
  assert.equal(link, "https://meli.la/LINK_FICTICIO");
  assert.equal(calls.length, 2);
  const post = calls.find((call) => call.url === INTERNAL);
  assert.ok(post, "Faltou chamar o gerador interno simulado");
  assert.equal(post.method, "POST");
  assert.deepEqual(JSON.parse(post.body), {
    url: PRODUCT, tag: "tag-ficticia",
  });
  assert.match(post.headers.cookie, /session=FAKE-COOKIE-DO-NOT-USE/);
  console.log("PASS: gerou short_url fictício e enviou URL/tag no POST simulado.");

  calls.length = 0;
  const EVIL_URL = "https://example.invalid/produto";
  await provider.createAffiliateUrl(EVIL_URL);
  const unsafeFetch = calls.find((call) => call.url === EVIL_URL);
  assert.ok(unsafeFetch, "Não foi possível avaliar a primeira requisição do provedor");
  const leaked = String(unsafeFetch.headers?.cookie ?? "").includes(COOKIE_VALUE);
  console.log("SECURITY_CHECK: cookie_in_external_request=" + leaked);
  // Uma falha neste teste significa que a versão upstream mudou;
  // revisar manualmente as consequências antes de confiar nela.
  assert.equal(leaked, true, "O comportamento da versão fixada foi alterado");
  console.log(
    "BLOCKER: versão upstream encaminha cookies a uma URL arbitrária; " +
    "não integrar esse código diretamente."
  );
  console.log("LIVE_AFFILIATE_GENERATION: NOT_TESTED (no authenticated session)");
}

main().catch((error) => {
  console.error("Falha na avaliação offline:", error.message);
  process.exitCode = 1;
});
