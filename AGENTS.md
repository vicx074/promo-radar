# Contrato obrigatório para IA

Antes de alterar qualquer arquivo, leia README.md, ARCHITECTURE.md, docs/decisions/* e docs/contracts/*.md. Contratos, ADRs e testes são a fonte de verdade; mudanças de arquitetura requerem ADR antes ou junto do código.

Invariantes: criar oferta não publica; aprovação explícita e SEND_ENABLED=true são obrigatórios; salvar reserva de publicação ANTES do HTTP; nunca reenviar automaticamente SENDING, SENT ou UNKNOWN; dinheiro apenas em centavos inteiros; banco fora do container; não versionar .env, sessão, credenciais, backups ou SQLite. Grupos devem ser próprios ou consentidos. Baileys não é oficial. Não adicionar filas, microserviços ou front-end sem justificativa. Executar testes e declarar o que foi ou não validado em integração real.
