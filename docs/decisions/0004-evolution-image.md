# ADR 0004 — Imagem Docker da Evolution API

- Status: aceito
- Data: 2026-10-11

## Contexto

A imagem original atendai/evolution-api:v2.1.1 falhou com pull access denied no Docker Desktop do projeto. A Evolution API passou a distribuir imagens no namespace evoapicloud/evolution-api. A tag v2.3.7 está publicada no Docker Hub (linux/amd64 e linux/arm64) e é usada pela configuração oficial do projeto.

## Decisão

Fixar evoapicloud/evolution-api:v2.3.7 no Compose, sem utilizar latest. Manter o mapeamento de portas 127.0.0.1:8085:8080 no host e http://evolution:8080 na rede Docker. Adicionar ao CI verificação da tag declarada e de seu manifesto remoto.

## Alternativas rejeitadas

- Namespace atendai com v2.1.1: download falhou no ambiente.
- latest: tag mutável, menos reprodutível.
- 2.4.0-rc2 / homolog: versões de pré-lançamento desnecessárias para o MVP.
- Build local da Evolution API clonada: maior custo de manutenção e tempo de build.

## Consequências

A imagem é publicamente encontrada, mas validação de manifesto não garante que o container rode ou que QR e envio funcionem. Esses passos continuam dependentes de teste real. Nunca usar down -v para atualização de rotina: a Evolution mantém dados em volumes nomeados.

## Referências

- https://hub.docker.com/r/evoapicloud/evolution-api/tags
- https://github.com/evolution-foundation/evolution-api/blob/main/Docker/swarm/evolution_api_v2.yaml
- https://github.com/EvolutionAPI/docs-evolution/pull/19/files
