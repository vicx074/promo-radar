# Contrato de publicação v1

POST /api/v1/offers/{id}/publish exige x-admin-key, SEND_ENABLED=true, APPROVED e GROUP_ID com @g.us. Reserva UNIQUE(offer_id,group_jid) em SENDING antes do POST Evolution /message/sendText/{instance} com {number,text} e header apikey. HTTP 2xx -> SENT (aceite, não entrega); timeout/erro -> UNKNOWN e 502. GET /api/v1/publications/{id} consulta o resultado. Nunca retry automático depois de SENDING, SENT ou UNKNOWN. Publicidade identificada no texto.


## Versão aditiva v2 — imagem + caption

Com `image_url`, a oferta aprovada requer mídia previamente preparada; caso contrário, `409` sem reservar publicação. `sendMedia` transmite JPEG otimizado em base64 puro com legenda em `caption`, uma única requisição. A reserva SENDING precede o HTTP. Falha/timeout é UNKNOWN e não permite retry automático; SENT só confirma aceite HTTP. Ofertas legadas sem mídia continuam com `sendText`.


## Versão aditiva v3 — bloqueio de links não cadastrados

Ofertas Mercado Livre sem link oficial cadastrado pelo operador retornam 409 já na aprovação e, por defesa em profundidade, novamente na publicação antes da reserva SENDING. Registros migrados do CSV não são afiliados automaticamente, mesmo que APPROVED em versão anterior. O texto do envio usa a URL cadastrada em `affiliate_link_url` projetada como `affiliate_url`. Links de outras fontes continuam no contrato legado não verificado.
