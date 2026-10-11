# ADR 0010 — Painel administrativo em React + Vite

Status: aceito para o MVP · 2026-10-11.

## Contexto
O Promo Radar precisa de um frontend simples, componentizado e responsivo para pesquisar no catálogo local autorizado, criar rascunhos, vincular links de afiliado, preparar imagens, aprovar ofertas, pré-visualizar e realizar publicação manual. O backend FastAPI já disponibiliza endpoints protegidos por `x-admin-key` (SQLite schema v5), mas não possui API pública de geração de links de afiliados, agendador, consulta de grupos pelo painel nem autenticação OAuth de afiliados.

## Decisão
1. Usar **React 19 + TypeScript + Vite 6**, sem Next.js ou SSR, com CSS modularizado por áreas no MVP. Interface em português, tema azul-claro e responsividade de mobile a desktop.
2. Aplicar o padrão de composição e microinteração **Letter Swap** adaptado do projeto Fancy Components (Daniel Petho, MIT, https://github.com/danielpetho/fancy) com `motion/react`, respeitando `prefers-reduced-motion`. Os demais componentes são locais reutilizáveis. Evitar excesso de efeitos.
3. O browser acessa `/api/v1/...` **na mesma origem**: Vite faz proxy no desenvolvimento e Nginx reencaminha requests de produção para `bot:8000` no Compose. Não habilitar CORS aberto e não colocar ADMIN_API_KEY no bundle ou Docker build args.
4. Autenticar no painel validando a chave administrativa contra uma rota existente. A chave fica apenas em **estado React**, não persiste em localStorage/sessionStorage nem cookies. Isso é autenticação administrativa MVP, **não é login na conta Mercado Livre**. O operador deve proteger o host e não publicar a porta na internet.
5. Ler produtos da rota de busca sob demanda, com informação explícita de que os dados são de CSV local e não de API ao vivo. Selecionar rascunhos, listar, cadastrar link informado pelo operador, preparar JPEG, aprovar e publicar manualmente, mediante confirmação e destinatário permitido. Exibir `SENT` apenas como aceite HTTP.
6. Telas Grupos/Programações sinalizam **não implementado**; Histórico consulta publicação conhecida por UUID em vez de inventar uma API de listagem. Configurações consultam `DISCONNECTED` em vez de desenhar botão funcional de OAuth.
7. Fotos renderizadas somente se a URL HTTPS pertence ao CDN `http2.mlstatic.com`. Resposta 401/409/422 é apresentada na UI. CI executa testes de utilitários, TypeScript + build e smoke Nginx em Docker.

## Restrições e futuras evoluções
- Ao implantar com backend existente, a aplicação precisa da PR #6 com rotas de afiliados e schema v5.
- Não disponibilizar para usuários na internet com ADMIN_API_KEY compartilhada; antes disso, implantar autenticação de usuários, autorização e anti-CSRF conforme arquitetura de sessões.
- Campanhas, destinos, histórico paginado, fonte de catálogo live autorizada e integração oficial para geração de links permanecem etapas futuras.
- A interface, por si só, não comprova comissão, entrega WhatsApp ou validade comercial do produto.

## Atualização ADR 0011

A autenticação por `x-admin-key` **não é mais usada pelo navegador**; foi substituída por sessão cookie segura e token CSRF (ver [ADR 0011](0011-private-single-owner-auth.md)). A chave permanece somente como interface legada para testes/CLI local, desligada na VPS. Interface organizada para um único operador, não SaaS.
