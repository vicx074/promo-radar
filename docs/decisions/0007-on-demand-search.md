# ADR 0007 — Busca sob demanda e seleção revisada

- Status: aceito
- Data: 2026-10-11

## Contexto

O usuário deve escrever um nicho/palavra-chave, ver produtos com preços e imagens e escolher quais ofertas entram na fila de aprovação, **sem varredura periódica**. Ainda não há contrato/API autorizada de busca comercial em tempo real do Mercado Livre.

## Decisão

1. Introduzir interface de consulta `CatalogProvider` e implementação `CsvCatalogProvider` lendo um arquivo fornecido pelo operador em `data/import/catalogo.csv`. **Não faz HTTP nem scraping e não oferece catálogo live**. O provider pode ser substituído futuramente por API/feed licenciado.
2. `POST /api/v1/discovery/search` exige autenticação administrativa, busca apenas quando solicitado, utiliza normalização casefold/acentos e compara termos ao título. Limites: termo 2–100 caracteres; até 50 resultados retornados. **Busca por título**, não classificação comprovada de categorias.
3. Persistir snapshot de busca e resultados no SQLite schema v4, com expiração de 45 minutos. A seleção deve referenciar `search_id` e os `source_item_id` recebidos do servidor, nunca confiar em preços ou links enviados pelo cliente; uma mudança posterior do CSV não pode trocar o preço selecionado silenciosamente.
4. `POST /api/v1/discovery/select` somente cria DRAFT das linhas selecionadas. Preço em centavos; imagem original opcional. Link é o endereço do produto informado no CSV, **não é rastreamento de afiliado**. Referência histórica permanece nula; sem inventar desconto. A deduplicação considera produto e preço, retorna `created=false` para oferta já existente (inclusive aprovada).
5. Sem preparação de imagem, aprovação, agendamento ou WhatsApp automático. O próximo operador usa `prepare-media` e `approve` existentes. Grupos e campanhas ficam em etapa posterior.
6. Em erro de origem indisponível, retornar 503; catálogo inválido, 422; snapshot expirado, 410. Busca vazia é válida.
7. Exercitar as APIs na CI (Pytest e Docker), sem Mercado Livre/WhatsApp reais.

## Consequências

A busca por nicho funciona apenas sobre o conteúdo já obtido com autorização e presente no catálogo; **não significa busca automática no Mercado Livre**. Precisaremos negociar/feed autorizado para a etapa de aquisição real. O snapshot usa SQLite e não exige Redis/fila.
