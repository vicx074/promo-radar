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
    media_allowed_hosts: tuple[str, ...] = ("http2.mlstatic.com",)
    owner_password_hash: str = ""
    session_cookie_secure: bool = True
    allow_admin_api_key: bool = True
    single_owner_mode: bool = False
    discovery_provider: str = "csv"
    apify_token: str = ""

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
            owner_password_hash=os.getenv("OWNER_PASSWORD_HASH", ""),
            session_cookie_secure=os.getenv("SESSION_COOKIE_SECURE", "true").lower() == "true",
            allow_admin_api_key=os.getenv("ALLOW_ADMIN_API_KEY", "true").lower() == "true",
            single_owner_mode=os.getenv("SINGLE_OWNER_MODE", "false").lower() == "true",
            discovery_provider=os.getenv("DISCOVERY_PROVIDER", "apify").lower(),
            apify_token=os.getenv("APIFY_TOKEN", ""),
            media_allowed_hosts=tuple(
                item.strip().lower()
                for item in os.getenv("MEDIA_ALLOWED_HOSTS", "http2.mlstatic.com").split(",")
                if item.strip()
            ),
        )
