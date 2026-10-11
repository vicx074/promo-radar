import httpx


class EvolutionPublisher:
    def __init__(self, base_url: str, api_key: str, instance: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.instance = instance

    def send_text(self, group_jid: str, text: str) -> str | None:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                f"{self.base_url}/message/sendText/{self.instance}",
                headers={"apikey": self.api_key},
                json={"number": group_jid, "text": text},
            )
            response.raise_for_status()
            payload = response.json()
            key = payload.get("key") if isinstance(payload, dict) else None
            message_id = key.get("id") if isinstance(key, dict) else None
            return message_id if isinstance(message_id, str) else None
