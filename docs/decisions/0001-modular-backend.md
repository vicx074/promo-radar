# ADR 0001 — Monólito modular Python

Status: aceito. Data: 2026-10-11.

## Contexto
Um operador, baixo volume e orçamento mínimo.
## Decisão
FastAPI com domínio, persistência SQLite e adaptador Evolution independentes.
## Alternativas rejeitadas
Microserviços, RabbitMQ, Celery e frontend imediato aumentariam custo sem evidência de necessidade. Flask seria viável, mas FastAPI fornece validação e OpenAPI.
## Consequências
Um único processo do bot; escalar somente após medir demanda.
