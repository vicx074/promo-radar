# Arquitetura do Promo Radar

Monólito modular Python/FastAPI. Admin HTTP -> SQLite (ofertas e publicações); somente ação de publicação explícita -> Evolution API v2 (Baileys) -> grupo autorizado.

Domínio em app/domain.py; adaptadores app/storage.py (SQLite WAL) e app/evolution.py (HTTP); borda HTTP app/main.py. Banco em /app/data/offers.db persistido por bind mount ./data do host; serviços da Evolution usam PostgreSQL e Redis com volumes separados. Sem scraping, scheduler, webhook ou UI nesta fase.

Estado: oferta DRAFT -> APPROVED; publicação ausente -> SENDING -> SENT | UNKNOWN. SENDING é registrado antes do HTTP. SENT é aceitação da Evolution, não comprovação de entrega. UNKNOWN e SENDING após crash exigem reconciliação manual e não permitem retry cego.


## Ferramenta de diagnóstico

`app/evolution_admin.py` implementa somente criação de instância, consulta de conexão e listagem de grupos da Evolution API. Não oferece envio fora do caso de uso de publicação, que permanece protegido pelo controle de aprovação. Pareamento de QR via Manager é manual. Confira o runbook `docs/evolution-connection.md`.
