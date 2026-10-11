# ADR 0011 — Operador único em VPS privada

Status: aceito para implementação · 2026-10-11.

## Escopo
Promo Radar não é SaaS. Uma pessoa opera um único painel e uma instância Evolution; não há cadastro de clientes, multi-tenant, planos, organizações ou RBAC. O login do painel **não** autentica no Mercado Livre.

## Acesso e confiança
- Implantação recomendada: **Tailscale Serve**, HTTPS TLS encerrado no Tailscale, HTTPS exclusivo para membros autorizados da tailnet; **não utilizar Funnel** nem abrir porta 5173 no firewall público. Compose mantém frontend (5173), FastAPI (8000) e Evolution (8085) vinculados apenas a 127.0.0.1 do host.
- Para a VPS, `SINGLE_OWNER_MODE=true`, `OWNER_PASSWORD_HASH` Argon2id, `SESSION_COOKIE_SECURE=true` e `ALLOW_ADMIN_API_KEY=false`. Backend **falha na inicialização** se essas condições não forem cumpridas.
- Senha nunca persistida em claro, chave administrativa não presente no frontend, endpoint de login requer Origin HTTPS e Host equivalentes. A senha se verifica com Argon2id (`argon2-cffi`).
- Sessão autenticada: token criptograficamente aleatório (48 bytes) no cookie `__Host-promo_session`, com `HttpOnly`, `Secure`, `SameSite=Strict`, `Path=/`. SQLite armazena apenas SHA-256 do token. Prazo absoluto de 12h, inatividade de 30min, logout revoga e novo login invalida sessões anteriores. A cada GET `/api/v1/auth/session`, o frontend restaura somente um token CSRF aleatório — nunca a senha.
- Requisições mutáveis com cookie exigem **Origin exata** da origem HTTPS e `x-csrf-token` igual ao da sessão. Todas as rotas admin reutilizam a autorização via cookie; nunca liberar criação/aprovação/publicação pública. Na VPS a chave legada por header não autentica. No ambiente local/CI, modo legado é configurável explicitamente para compatibilidade dos testes e CLI.
- Limitador de login **global e persistente** em SQLite: após 5 falhas em janela de 15 minutos, bloquear login por 15 minutos; o operador pode se bloquear, mas é melhor que tentativas ilimitadas.
- Não implementa 2FA nem auditoria multiusuário. Segurança perimetral por Tailscale ACL e isolamento no host **é obrigatória** antes de expor o aplicativo.

## Consequências
O SPA React mantém sessão pelo cookie do browser e CSRF apenas em memória, recuperável após atualização. Logout invalida no servidor. O modo privado é opt-in na configuração; o backend legado permanece utilizável pelos testes, sem credenciais reais. Não mudar invariantes de envio (DRAFT, APPROVED, SEND_ENABLED, idempotência, UNKNOWN). Senha Argon2id é configuração sensível, deve ficar apenas na VPS e em backup seguro (não versionar).
