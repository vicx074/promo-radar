import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    sqlite_path: Path
    admin_api_key: str
    evolution_base_url: str
    evolution_api_key: str
    evolution_instance: str
    whatsapp_group_id: str
    send_enabled: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            sqlite_path=Path(os.getenv("SQLITE_PATH", "data/offers.db")),
            admin_api_key=os.getenv("ADMIN_API_KEY", ""),
            evolution_base_url=os.getenv("EVOLUTION_BASE_URL", "http://localhost:8080"),
            evolution_api_key=os.getenv("EVOLUTION_API_KEY", ""),
            evolution_instance=os.getenv("EVOLUTION_INSTANCE", "promocoes"),
            whatsapp_group_id=os.getenv("WHATSAPP_GROUP_ID", ""),
            send_enabled=os.getenv("SEND_ENABLED", "false").strip().lower() == "true",
        )
