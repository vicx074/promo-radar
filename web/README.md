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
1. Informe a chave `ADMIN_API_KEY` definida no backend: é a **chave administrativa do Promo Radar**, não a senha do Mercado Livre. Fica só na memória do componente React.
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
