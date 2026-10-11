# Imagens nas ofertas

O backend mantém texto para ofertas antigas e acrescenta uma imagem principal por oferta nova. O envio de imagem foi projetado para Evolution API v2.3.7 (sendMedia), mas deve ser confirmado com grupo próprio antes de uso real.

## Fluxo

1. Cadastrar oferta DRAFT via `POST /api/v1/offers`, com `image_url` HTTPS **opcional**.
2. `POST /api/v1/offers/{id}/prepare-media` baixa a imagem de host permitido, valida, redimensiona, compacta e armazena JPEG em `data/media`. Este endpoint exige x-admin-key, só aceita ofertas DRAFT e não envia WhatsApp.
3. `GET /api/v1/offers/{id}/preview` devolve `message`, `image_url`, `image_ready` e metadados do arquivo otimizado. Não faz download nem envia.
4. Aprovar a oferta e publicar deliberadamente, mantendo `SEND_ENABLED`. Oferta com `image_url` exige `image_ready=true`. O envio utiliza base64 JPEG + caption em uma só mensagem. Sem `image_url`, continua com sendText.

## Configuração

`MEDIA_ALLOWED_HOSTS` aceita hosts EXATOS separados por vírgula (ex.: `http2.mlstatic.com`), definidos e verificados pelo operador. Default é `http2.mlstatic.com`. Domínios genéricos, URLs HTTP e redirects não funcionam. A proteção de infraestrutura deve bloquear egress a redes privadas em produção.

A transformação: JPEG, EXIF transposto, sem metadados, lado maior <= 1200 px, qualidade inicial 88, tamanho-alvo <= 1 MiB. Não aumenta imagens pequenas. Arquivos no volume `./data:/app/data`.

Nunca publique uma imagem que não tenha autorização para uso promocional. Referência de preços não significa desconto comprovado.

## Testes

- GitHub Actions testa Python (Pillow, URLs, limites, migrações, API) e também constrói/executa uma imagem Docker de testes.
- `sendMedia` é exercitado por um mock de HTTP na CI, sem credenciais.
- A CI NÃO demonstra conexão ao WhatsApp, nem confirma que uma foto foi entregue a um grupo. Validar essa etapa manualmente.
