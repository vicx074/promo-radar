# ADR 0002 — SQLite durável

Status: aceito. Data: 2026-10-11.

## Contexto
Rebuild Docker não pode apagar o estado.
## Decisão
SQLite WAL no bind mount ./data:/app/data, backups consistentes com SQLite online backup API copiados para outro host.
## Alternativas rejeitadas
Arquivo interno ao container, guardar dados no Git ou PostgreSQL extra apenas para o bot.
## Consequências
Build e recriação preservam dados; perda da VPS, deleção do diretório ou ausência de backups externos continuam sendo riscos. A Evolution mantém seus próprios dados em volumes independentes.
