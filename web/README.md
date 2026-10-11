> **Atualização de interface:** React + Vite usa Tailwind CSS 4 para responsividade mobile-first, mantendo Motion/Fancy Components. No celular há navegação inferior fixa; no computador, sidebar lateral. Os testes de viewport usam Playwright/Chromium (320 a 1440px). Veja [ADR 0013](../docs/decisions/0013-tailwind-mobile-first.md).

# Promo Radar Web — React + Vite

Painel administrativo componentizado em React 19 + TypeScript, Vite 6, Motion (microinteração inspirada no Fancy Components) e ícones Lucide.

## Local (Windows PowerShell)
Na pasta `web`:
```powershell
npm install
npm run dev
```
Acesse http://localhost:5173. O Vite faz proxy de `/api` para o backend em http://127.0.0.1:8000. Para mudar a URL do proxy, defina `PROMO_API_PROXY` **somente no servidor de desenvolvimento**.

Se preferir Docker, na raiz do projeto:
```powershell
docker compose up -d --build
```
Acesse http://127.0.0.1:5173. O Nginx serve a interface compilada e envia `/api` para o container FastAPI.

## Uso
1. Informe a **senha privada do Promo Radar**, configurada como hash Argon2id no backend. O navegador mantém apenas a sessão HttpOnly e o token CSRF em memória. Não use a chave ADMIN_API_KEY no browser.
2. Em **Descobrir ofertas**, pesquise título/nicho no CSV autorizado `./data/import/catalogo.csv`. Se o arquivo estiver ausente, a API retorna erro 503; não há busca ao vivo do Mercado Livre.
3. Selecione produtos e vá a **Minhas ofertas**. O backend cria DRAFT sem envio.
4. Abra a oferta; adicione link oficial do afiliado gerado na Central do Mercado Livre, confirmando que ele corresponde ao produto. Validação de formato não comprova comissão.
5. Se houver imagem, clique em **Preparar** enquanto rascunho. Revise a prévia, aprove e, se a configuração de envio estiver habilitada e o destino for permitido, utilize **Publicar agora** com confirmação adicional.
6. O menu **Configurações** exibe integração Mercado Livre desconectada. **Grupos** e **Programações** são placeholders explícitos. **Histórico** permite consultar apenas publicação pelo UUID retornado no envio.

## Componentes
- `src/App.tsx`: entrada administrativa e navegação.
- `src/components/layout/Sidebar.tsx`: barra lateral.
- `src/pages/DiscoveryPage.tsx`: busca, cards e seleção.
- `src/pages/OffersPage.tsx`: lista, filtros e painel de revisão.
- `src/components/offers/OfferDetails.tsx`: afiliação, imagem, aprovação, preview e publicação manual.
- `src/pages/SettingsPage.tsx`: estado real da integração.
- `src/pages/HistoryPage.tsx`: consulta pelo UUID.
- `src/components/ui/LetterSwap.tsx`: adaptação do Fancy Components (MIT; fonte identificada no componente).
- `src/lib/api.ts`: chamadas tipadas e tratamento de erros.

## Testes
```powershell
npm test
npm run build
```
GitHub Actions: `.github/workflows/web.yml` também constrói imagem Nginx e testa a entrega de assets por HTTP.

### Segurança
Não insira cookies do Mercado Livre, token de sessão, JID de grupo ou chave administrativa em issues, logs ou commits. O painel é para acesso local de administrador; não exponha diretamente a porta 5173 à Internet. As rotas protegidas continuam exigindo `x-admin-key` mesmo com frontend.

## Operação remota para uma pessoa

O painel é uma ferramenta privada, não um SaaS. Não oferece cadastro de usuários, equipes ou planos. O acesso de VPS requer `SINGLE_OWNER_MODE=true` com senha Argon2id, cookie HTTPS e `ALLOW_ADMIN_API_KEY=false`, via Tailscale Serve. Veja [docs/private-vps.md](../docs/private-vps.md). É possível atualizar a página sem digitar novamente a senha até a sessão expirar; clicar em Sair revoga a sessão no SQLite. A interface não armazena credenciais em localStorage, sessionStorage ou cookies acessíveis por JavaScript.

## Mobile e testes de responsividade

O projeto utiliza `tailwindcss` + `@tailwindcss/vite` (v4). Use classes `sm:`, `md:`, `xl:` etc. nos componentes, em vez de novos breakpoints no CSS legado. As cores/sombras originais estão preservadas em `src/styles.css`, na camada `components`. Navegação inferior do celular considera `env(safe-area-inset-bottom)` e botões têm no mínimo 44px de altura; formulários usam fontes de 16px no celular para evitar zoom automático no Safari iOS.

Para validar o layout em Chromium:

```bash
cd web
npm install
npx playwright install chromium
npm run test:e2e
```

O CI testa larguras 320, 375, 390, 768, 1024 e 1440px com API **simulada**. Não substitui uma conferência manual no celular do operador conectado ao Tailscale.
