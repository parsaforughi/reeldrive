from pathlib import Path
import os

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Old Railway env values — never show these in /connect
_LEGACY_BRIDGE_HANDLES = frozenset(
    {"reeldrive_bridge", "reeldrive-bridge", "bridge", "regram_bridge"}
)

_DEFAULT_SQLITE = "sqlite+aiosqlite:///./data/reeldrive.db"


def _railway_data_dir() -> Path:
    mount = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "").strip()
    if mount:
        return Path(mount)
    if os.environ.get("RAILWAY_ENVIRONMENT"):
        return Path("/app/data")
    return Path("data")


def _sqlite_file_url(directory: Path, filename: str = "reeldrive.db") -> str:
    path = (directory / filename).as_posix()
    if not path.startswith("/"):
        return f"sqlite+aiosqlite:///./{path}"
    return f"sqlite+aiosqlite:///{path}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    telegram_bot_token: str

    # Apify — direct download (links); no IG login needed
    apify_token: str = ""
    apify_actor: str = "apify~instagram-scraper"
    apify_timeout_seconds: int = 120

    # Service account — optional: profile/stories/highlights (instagrapi)
    instagram_username: str = ""
    instagram_password: str = ""
    instagram_session_path: str = "sessions/service.json"

    # Bridge account — reads DMs to @reeldrivebot, forwards to Telegram
    instagram_bridge_login: str = ""
    instagram_bridge_username: str = ""
    instagram_bridge_password: str = ""
    instagram_bridge_session_path: str = "sessions/bridge.json"
    instagram_bridge_display: str = "reeldrivebot"
    instagram_session_id: str = ""
    instagram_bridge_session_id: str = ""
    instagram_proxy: str = ""
    instagram_bridge_enabled: bool = True
    instagram_bridge_force_login: bool = False

    database_url: str = _DEFAULT_SQLITE
    bot_name: str = "Reeldrive"
    bot_mention: str = "reeldrivebot"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        # Railway Postgres plugin sets DATABASE_URL / DATABASE_PRIVATE_URL
        url = (value or os.environ.get("DATABASE_PRIVATE_URL") or "").strip()
        if not url:
            url = _DEFAULT_SQLITE
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif (
            url.startswith("postgresql://")
            and "+asyncpg" not in url
            and "+psycopg" not in url
        ):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if os.environ.get("RAILWAY_ENVIRONMENT") and "sqlite" in url:
            data_dir = _railway_data_dir()
            expected = _sqlite_file_url(data_dir)
            if url in (_DEFAULT_SQLITE, "sqlite+aiosqlite:///./data/reeldrive.db"):
                url = expected
            elif str(data_dir) not in url:
                url = expected
        return url

    @model_validator(mode="after")
    def railway_persistent_paths(self) -> "Settings":
        if not os.environ.get("RAILWAY_ENVIRONMENT"):
            return self
        base = _railway_data_dir()
        if self.instagram_bridge_session_path.replace("\\", "/").startswith("sessions/"):
            self.instagram_bridge_session_path = str(base / "sessions" / "bridge.json")
        if self.instagram_session_path.replace("\\", "/").startswith("sessions/"):
            self.instagram_session_path = str(base / "sessions" / "service.json")
        return self

    @property
    def database_is_postgres(self) -> bool:
        return "postgresql" in self.database_url

    @property
    def persistent_data_dir(self) -> Path:
        if self.database_is_postgres:
            return _railway_data_dir() if os.environ.get("RAILWAY_ENVIRONMENT") else Path("data")
        if "sqlite" in self.database_url:
            raw = self.database_url.split("sqlite+aiosqlite:///")[-1]
            return Path(raw).parent
        return Path("data")

    verification_code_ttl_minutes: int = 15
    bridge_poll_interval_seconds: float = 2.0
    bridge_poll_idle_seconds: float = 10.0
    max_zip_posts: int = 100

    dashboard_password: str = "admin"
    dashboard_secret: str = "change-me-dashboard-secret"
    dashboard_port: int = 8080

    @property
    def service_session_file(self) -> Path:
        return Path(self.instagram_session_path)

    @property
    def bridge_session_file(self) -> Path:
        return Path(self.instagram_bridge_session_path)

    def _normalize_ig_handle(self, value: str) -> str:
        return value.strip().lstrip("@").lower()

    def _public_bridge_handle(self) -> str:
        for raw in (self.instagram_bridge_display, self.instagram_bridge_username):
            name = (raw or "").strip().lstrip("@")
            if name and self._normalize_ig_handle(name) not in _LEGACY_BRIDGE_HANDLES:
                return name
        return self.bot_mention.lstrip("@")

    @property
    def bridge_ig_handle(self) -> str:
        return f"@{self._public_bridge_handle()}"


settings = Settings()
