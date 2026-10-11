# ADR 0006 — Imagem principal otimizada por oferta

- Status: aceito
- Data: 2026-10-11

## Contexto

O MVP publica texto via Evolution API v2.3.7. Cada oferta deverá poder enviar **uma imagem principal + legenda**, sem perder aprovações manuais, bloqueio SEND_ENABLED e reserva idempotente antes da chamada remota.

## Decisão

1. `image_url` HTTPS é opcional no contrato de criação, por compatibilidade com ofertas antigas. Somente imagens de hosts explicitamente aprovados (`MEDIA_ALLOWED_HOSTS`; default `http2.mlstatic.com`) podem ser obtidas pelo servidor; URLs arbitrárias, redes locais e redirects são rejeitados. A etapa de imagem é explicitamente iniciada via `POST /offers/{id}/prepare-media`, apenas para DRAFT. O resultado é vinculado à oferta, evitando download durante publicação.
2. `app/media.py` baixa no máximo 5 MiB, com timeout, converte com Pillow para JPEG com lado maior <= 1200 px, corrige orientação EXIF e usa qualidade adaptativa procurando arquivo <= 1 MiB sem ampliá-lo. Conteúdo é validado como imagem por decodificação, não apenas pelo header HTTP. Evitar SSRF: hostname exato de allowlist e rejeitar IPs privados/loopback, além de redirects. **A allowlist é de confiança do operador**; proteção contra DNS rebinding pode exigir controle de egress na infraestrutura para produção.
3. Cache endereçado por SHA-256 da versão otimizada em `data/media` persistida no volume local. Migração SQLite 2 -> 3 adiciona `offers.image_url`, `offers.image_sha256` e tabela `media_assets`. Não alterar estado DRAFT/APPROVED nem envios existentes.
4. Oferta com `image_url` **não pode ser publicada sem imagem preparada**; ofertas legadas sem imagem continuam com fluxo de texto. O preview retorna legenda + metadados da imagem; não chama rede.
5. Evolution API v2.3.7 usa `POST /message/sendMedia/{instance}`, mediatype=image, mimetype=image/jpeg, media=base64 JPEG, caption=texto; nome de arquivo para imagem será `filename` minúsculo conforme comportamento reportado na [issue #2459](https://github.com/evolution-foundation/evolution-api/issues/2459) desta versão. Testes de contrato com stub HTTP não garantem entrega real.
6. Testes Python e Docker no GitHub Actions usam dados sintéticos e stub da Evolution sem segredos ou WhatsApp conectado. A primeira entrega real será feita manualmente em grupo próprio, autorizada pelo operador.
7. O coletor CSV continua funcionando e passa a aceitar coluna opcional `image_url`; geração DRAFT sem mídia permanece possível, mas a publicação com imagem exigirá preparação.
