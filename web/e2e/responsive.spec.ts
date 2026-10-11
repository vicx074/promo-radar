import {expect, test, type Page} from "@playwright/test";

const product = {
  source: "mercado_livre",
  source_item_id: "MLB_NOTEBOOK",
  id: "00000000-0000-4000-8000-000000000001",
  title: "Notebook Lenovo 16GB de memória para testes",
  price_cents: 259990,
  reference_price_cents: null,
  status: "DRAFT",
  product_url: "https://www.mercadolivre.com.br/p/MLB12345",
  affiliate_url: null,
  affiliate_status: "MISSING",
  image_url: null,
  created_at: "2026-10-11T12:00:00Z",
};

async function mockPrivateApi(page: Page) {
  await page.route("**/api/v1/**", async (route) => {
    const pathname = new URL(route.request().url()).pathname;
    if (pathname === "/api/v1/auth/session") {
      await route.fulfill({json: {authenticated: true, csrf_token: "test-csrf", expires_at: 1800000000}});
    } else if (pathname === "/api/v1/discovery/search") {
      await route.fulfill({json: {
        search_id: "00000000-0000-4000-8000-000000000002",
        query: "notebook",
        source: "mercado_livre",
        live: true,
        provider: "apify_live",
        expires_at: "2026-10-11T13:00:00Z",
        items: Array.from({length: 6}, (_, i) => ({
          source_item_id: "MLB_NOTEBOOK_" + i,
          title: "Notebook Lenovo configuração " + i + " memória e SSD",
          price_cents: 259990 + i * 1000,
          product_url: product.product_url,
          image_url: null,
          promotion_verified: false,
          price_history_available: false,
        })),
      }});
    } else if (pathname === "/api/v1/offers") {
      await route.fulfill({json: [product]});
    } else if (pathname === "/api/v1/offers/" + product.id) {
      await route.fulfill({json: product});
    } else if (pathname === "/api/v1/offers/" + product.id + "/preview") {
      await route.fulfill({json: {message: "Promoção: Notebook Lenovo", image_url: null, image_ready: false, image: null}});
    } else if (pathname === "/api/v1/affiliates/mercado-livre/status") {
      await route.fulfill({json: {
        provider: "mercado_livre", status: "DISCONNECTED",
        connected: false, auto_generation_available: false,
        permissions: [], connection_method: "none",
      }});
    } else {
      await route.fulfill({status: 404, json: {detail: "Rota não simulada"}});
    }
  });
}

async function expectNoHorizontalOverflow(page: Page) {
  const widths = await page.evaluate(() => ({
    scroll: document.documentElement.scrollWidth,
    viewport: window.innerWidth,
  }));
  expect(widths.scroll, "A tela não pode criar rolagem horizontal").toBeLessThanOrEqual(widths.viewport + 1);
}

for (const width of [320, 375, 390, 768, 1024, 1440]) {
  test(`layout responsivo e navegação a ${width}px`, async ({page}) => {
    await page.setViewportSize({width, height: 850});
    await mockPrivateApi(page);
    await page.goto("/");
    await expect(page.getByRole("heading", {name: "Descubra novas oportunidades"})).toBeVisible();
    await expectNoHorizontalOverflow(page);

    const bottomNav = page.getByRole("navigation", {name: "Navegação inferior"});
    if (width < 768) {
      await expect(bottomNav).toBeVisible();
      await expect(page.getByRole("button", {name: "Sair do painel"})).toBeVisible();
      for (const name of ["Descobrir", "Ofertas", "Histórico", "Ajustes"]) {
        await expect(bottomNav.getByRole("button", {name})).toBeVisible();
      }
    } else {
      await expect(bottomNav).toBeHidden();
      await expect(page.getByRole("navigation", {name: "Navegação principal"})).toBeVisible();
    }

    await page.getByRole("textbox", {name: "Buscar produtos"}).fill("notebook");
    await page.getByRole("button", {name: "Buscar ofertas"}).click();
    await expect(page.locator(".catalog-card")).toHaveCount(6);
    await expectNoHorizontalOverflow(page);

    await page.getByRole("button", {name: "Ofertas", exact: true}).click();
    await expect(page.getByRole("heading", {name: "Suas ofertas, sob controle"})).toBeVisible();
    await expect(page.locator(".offer-row")).toHaveCount(1);
    await page.locator(".offer-row").click();
    await expect(page.getByRole("heading", {name: "Revisão & publicação"})).toBeVisible();
    await expectNoHorizontalOverflow(page);

    await page.getByRole("button", {name: width < 768 ? "Ajustes" : "Ajustes", exact: true}).click();
    await expect(page.getByRole("heading", {name: "Configurações"})).toBeVisible();
    await expectNoHorizontalOverflow(page);
  });
}

test("login privado continua utilizável em celular estreito", async ({page}) => {
  await page.setViewportSize({width: 320, height: 660});
  await page.route("**/api/v1/auth/session", route =>
    route.fulfill({status: 401, json: {detail: "Sessão expirada"}}));
  await page.goto("/");
  await expect(page.getByRole("heading", {name: "Acesse seu painel"})).toBeVisible();
  await expectNoHorizontalOverflow(page);
  const input = page.getByLabel("Senha do painel");
  await expect(input).toBeVisible();
  expect(await input.evaluate(element => getComputedStyle(element).fontSize)).toBe("16px");
});
