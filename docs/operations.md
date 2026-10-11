# Operação

Use docker compose up -d --build após configurar .env a partir de .env.example com segredos fortes distintos. Serviços HTTP ligados a 127.0.0.1, sem acesso público. SQLite no host ./data/offers.db por bind mount; não é apagado por rebuild/down. O comando down -v remove volumes nomeados da Evolution (PostgreSQL, Redis e instâncias), não o bind mount. Não utilize down -v em produção.

Backup consistente: docker compose exec -T bot python -m app.backup /app/data/backups/offers-YYYYMMDD.db. Copie para outro host/disco seguro e teste restauração, com bot parado. Faça backups separados dos volumes e PostgreSQL da Evolution. Não copie apenas arquivo .db ativo em WAL. Primeiro envio: grupo próprio de teste e SEND_ENABLED=false até pareamento e validação do endpoint.
