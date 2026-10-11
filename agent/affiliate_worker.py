"""Worker LOCAL (Windows/macOS/Linux) do titular da conta Mercado Livre.

Usa Chrome em perfil dedicado, aberto e autenticado pessoalmente pelo dono.
Nao extrai cookies, nao utiliza acesso remoto de depuracao, nem transmite sessao ML.
A API acessada pelo navegador e INTERNA/NAO OFICIAL e pode parar de funcionar.
"""
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from playwright.sync_api import Error as BrowserError
from playwright.sync_api import sync_playwright

ML_BASE = "https://www.mercadolivre.com.br"
PROFILE_DIR = Path(__file__).resolve().parent / ".chrome-profile"
MIN_POLL_SECONDS = 15

# Executado exclusivamente dentro de uma pagina autenticada do dominio do Mercado Livre.
# Usa a sessao existente de primeira parte; NUNCA consulta document.cookie.
GENERATE_JS = """
async (productUrl) => {
  if (location.hostname !== "www.mercadolivre.com.br" &&
      location.hostname !== "mercadolivre.com.br") {
    return {error: "LOGIN_REQUIRED"};
  }
  const tagsResponse = await fetch("/affiliate-program/api/v2/stripe/user/tags", {
    credentials: "same-origin",
    headers: {Accept: "application/json"}
  });
  if (tagsResponse.status === 401 || tagsResponse.status === 403) {
    return {error: "LOGIN_REQUIRED"};
  }
  if (!tagsResponse.ok) return {error: "PROVIDER_UNAVAILABLE"};
  const tags = await tagsResponse.json();
  const activeTag = Array.isArray(tags.tags)
    ? tags.tags.find(t => t.in_use === true)?.tag : undefined;
  if (!activeTag) return {error: "LOGIN_REQUIRED"};

  const response = await fetch("/affiliate-program/api/v2/stripe/user/links", {
    method: "POST",
    credentials: "same-origin",
    headers: {"Content-Type": "application/json", Accept: "application/json"},
    body: JSON.stringify({url: productUrl, tag: activeTag})
  });
  if (response.status === 401 || response.status === 403) {
    return {error: "LOGIN_REQUIRED"};
  }
  if (!response.ok) return {error: "PROVIDER_UNAVAILABLE"};
  const data = await response.json();
  if (data.tag !== activeTag || typeof data.short_url !== "string" ||
      typeof data.origin_url !== "string") {
    return {error: "INVALID_LINK"};
  }
  return {affiliate_url: data.short_url, origin_url: data.origin_url};
}
"""


def config() -> tuple[str, str]:
    base = os.getenv("PROMO_BASE_URL", "").strip().rstrip("/")
    token = os.getenv("AFFILIATE_BRIDGE_TOKEN", "")
    parsed = urlsplit(base)
    local = parsed.hostname in {"localhost", "127.0.0.1"}
    if (
        not token or len(token) < 40
        or parsed.scheme not in ({"http", "https"} if local else {"https"})
        or not parsed.hostname or parsed.username or parsed.password
        or parsed.query or parsed.fragment or parsed.path not in ("", "/")
    ):
        raise SystemExit(
            "Configure PROMO_BASE_URL HTTPS da tailnet (ou HTTP localhost) "
            "e AFFILIATE_BRIDGE_TOKEN com pelo menos 40 caracteres."
        )
    return base, token


def main() -> None:
    base, token = config()
    headers = {"Authorization": "Bearer " + token}
    with httpx.Client(base_url=base, headers=headers,
                      timeout=20, follow_redirects=False) as api:
        with sync_playwright() as playwright:
            # Chrome do proprio computador, em perfil separado. Nenhuma senha salva na VPS.
            browser = playwright.chromium.launch_persistent_context(
                str(PROFILE_DIR), channel="chrome", headless=False,
                viewport={"width": 1280, "height": 800},
            )
            try:
                page = browser.pages[0] if browser.pages else browser.new_page()
                page.goto(ML_BASE + "/afiliados", wait_until="domcontentloaded",
                          timeout=45000)
                print("Entre na conta de afiliado do titular nesta janela do Chrome.")
                input("Quando a Central de Afiliados estiver aberta, pressione ENTER: ")
                print("Conector ativo. O computador e esta janela precisam permanecer abertos.")
                while True:
                    try:
                        api.post("/api/v1/affiliate-agent/heartbeat").raise_for_status()
                        r = api.post("/api/v1/affiliate-agent/claim")
                        r.raise_for_status()
                        job = r.json()["job"]
                    except (httpx.HTTPError, ValueError, KeyError):
                        print("Nao foi possivel conectar ao Promo Radar; tentando novamente.")
                        time.sleep(30)
                        continue
                    if not job:
                        time.sleep(MIN_POLL_SECONDS)
                        continue

                    print("Gerando link para oferta " + job["offer_id"][:8] + "...")
                    output: dict = {}
                    try:
                        page.goto(ML_BASE + "/afiliados", wait_until="domcontentloaded",
                                  timeout=45000)
                        if urlsplit(page.url).hostname not in {
                            "www.mercadolivre.com.br", "mercadolivre.com.br"
                        }:
                            output = {"error_code": "LOGIN_REQUIRED"}
                        else:
                            value = page.evaluate(GENERATE_JS, job["product_url"])
                            if not isinstance(value, dict):
                                output = {"error_code": "UNKNOWN"}
                            elif value.get("error"):
                                output = {"error_code": str(value["error"])}
                            else:
                                output = {
                                    "affiliate_url": value.get("affiliate_url"),
                                    "origin_url": value.get("origin_url"),
                                }
                    except BrowserError:
                        output = {"error_code": "PROVIDER_UNAVAILABLE"}
                    except Exception:
                        output = {"error_code": "UNKNOWN"}

                    try:
                        done = api.post(
                            "/api/v1/affiliate-agent/complete",
                            json={
                                "job_id": job["job_id"],
                                "claim_token": job["claim_token"],
                                **output,
                            },
                        )
                        done.raise_for_status()
                        status = done.json().get("status", "UNKNOWN")
                        print("Vinculo " + str(status) + ".")
                    except (httpx.HTTPError, ValueError):
                        print("Resposta nao registrada (incerta). Nao repetir automaticamente.")
                    time.sleep(1)
            finally:
                browser.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Conector encerrado.")
        sys.exit(0)
