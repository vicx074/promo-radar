# ADR 0013 — Tailwind CSS 4 e UX mobile-first do operador único

Status: implementado para revisão · 2026-10-11.

## Contexto

O Promo Radar é um painel privado usado por uma pessoa em computador e celular, via HTTPS/Tailscale Serve. A interface criada inicialmente com CSS manual precisava de responsividade mais sistemática e componentes fáceis de manter. A pesquisa por produto, a seleção e a revisão devem funcionar com toque e larguras de celular comuns.

## Decisão

1. Manter **React 19 + TypeScript + Vite 6 + Motion/Fancy Components** e acrescentar **Tailwind CSS 4** com `@tailwindcss/vite`, sem Next.js, shadcn, SSR ou JavaScript de breakpoint para apresentação.
2. Migrar regras de **breakpoint/layout** para classes Tailwind diretamente nos componentes. Preservar as classes cosméticas existentes (paleta, sombras, animações) numa camada CSS `components`, permitindo às utilities Tailwind sobrepor layout. Eliminar `@media(max-width)` legadas; apenas a preferência de movimento reduzido permanece em CSS.
3. **Mobile-first:** até 767px, mostrar barra fixa inferior com quatro ações (Descobrir, Ofertas, Histórico, Ajustes) e saída explícita no cabeçalho; a partir de `md`, sidebar lateral. Inclui padding da `safe-area` de iOS, área de clique de 44px ou mais, campos 16px para evitar zoom do Safari iOS, layout fluido e nenhuma rolagem horizontal.
4. A lista de ofertas se torna coluna única antes do breakpoint `xl`; ao tocar numa oferta, deslocar o foco visual para o painel de revisão (mantido na própria página); fornecer retorno à lista. Em desktop, mostrar lista e revisão lado a lado.
5. Grid de produtos vai de 1 coluna em telas muito estreitas para 2, 3 e 4 conforme espaço. Faixa de seleção respeita a altura da navegação inferior, sem ocultar o botão de salvar rascunhos. Nenhuma alteração de estado de negócio ou criação/publicação automática.
6. O login segue com cookie HttpOnly, CSRF e senha privada do único operador. Não armazenar tokens em JS persistente.
7. Validar via Vitest/TypeScript, Docker Nginx e testes de viewport Chromium/Playwright (320, 375, 390, 768, 1024 e 1440px) com APIs simuladas, incluindo ausência de rolagem horizontal. Esses testes não atestam entrega real via Evolution nem links Mercado Livre.

## Consequências

Tailwind passa a ser padrão para novas regras de responsividade. CSS legado de estilo ainda existe e pode ser migrado gradualmente para componentes reutilizáveis; não duplicar regras de breakpoint em CSS tradicional. A operação remota continua privada via Tailscale; não publicar portas do Compose.
