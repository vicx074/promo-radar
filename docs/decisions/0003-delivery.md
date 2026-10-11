# ADR 0003 — Reserva de publicação e aprovação

Status: aceito. Data: 2026-10-11.

## Contexto
Timeout pode ocorrer após aceitação da mensagem e preços exigem curadoria.
## Decisão
Ofertas criadas como DRAFT; exigir APPROVED, autenticação, SEND_ENABLED=true e grupo configurado. Persistir publicação SENDING antes da chamada Evolution. Sucesso HTTP marca SENT; falhas UNKNOWN; bloquear republicação da mesma oferta ao mesmo grupo.
## Alternativas rejeitadas
Postar ao cadastrar, retries cegos após timeout, ou guardar envio somente após resposta.
## Consequências
Menos spam e duplicações, mas reconciliação de resultado incerto é manual.
