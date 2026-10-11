import base64

import httpx


class EvolutionPublisher:
    def __init__(self, base_url: str, api_key: str, instance: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.instance = instance

    @staticmethod
    def _message_id(response: httpx.Response) -> str | None:
        response.raise_for_status()
        payload = response.json()
        key = payload.get("key") if isinstance(payload, dict) else None
        message_id = key.get("id") if isinstance(key, dict) else None
        return message_id if isinstance(message_id, str) else None

    def send_text(self, group_jid: str, text: str) -> str | None:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                f"{self.base_url}/message/sendText/{self.instance}",
                headers={"apikey": self.api_key},
                json={"number": group_jid, "text": text},
            )
            return self._message_id(response)

    def send_image(self, group_jid: str, image_bytes: bytes, caption: str) -> str | None:
        # Em Evolution v2.3.7, o nome em imagens é 'filename' em minúsculas.
        # O base64 vai puro e sem prefixo data:image.
        payload = {
            "number": group_jid,
            "mediatype": "image",
            "mimetype": "image/jpeg",
            "media": base64.b64encode(image_bytes).decode("ascii"),
            "filename": "oferta.jpg",
            "caption": caption,
        }
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{self.base_url}/message/sendMedia/{self.instance}",
                headers={"apikey": self.api_key},
                json=payload,
            )
            return self._message_id(response)
