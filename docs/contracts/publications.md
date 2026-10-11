# Contrato de publicação v1

POST /api/v1/offers/{id}/publish exige x-admin-key, SEND_ENABLED=true, APPROVED e GROUP_ID com @g.us. Reserva UNIQUE(offer_id,group_jid) em SENDING antes do POST Evolution /message/sendText/{instance} com {number,text} e header apikey. HTTP 2xx -> SENT (aceite, não entrega); timeout/erro -> UNKNOWN e 502. GET /api/v1/publications/{id} consulta o resultado. Nunca retry automático depois de SENDING, SENT ou UNKNOWN. Publicidade identificada no texto.
