from pathlib import Path
import os

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_LEGACY_BRIDGE_HANDLES = frozenset(
    {"reeldrive_bridge", "reeldrive-bridge", "bridge", "regram_bridge"}
)

_DEFAULT_SQLITE = "sqlite+aiosqlite:///./data/reeldrive.db"

_PG_ENV_KEYS = (
    "DATABASE_PRIVATE_URL",
    "DATABASE_URL",
    "DATABASE_PUBLIC_URL",
)


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


def _is_postgres_url(url: str) -> bool:
    u = (url or "").lower()
    return u.startswith("postgres://") or u.startswith("postgresql://")


def _postgres_url_from_env() -> tuple[str, str]:
    """Find Postgres URL in any Railway-injected variable."""
    for key in _PG_ENV_KEYS:
        raw = os.environ.get(key, "").strip()
        if _is_postgres_url(raw):
            return raw, key
    for key, raw in os.environ.items():
        if not raw or key in _PG_ENV_KEYS:
            continue
        val = raw.strip()
        if _is_postgres_url(val) and "POSTGRES" in key.upper():
            return val, key

    host = (
        os.environ.get("PGHOST", "").strip()
        or os.environ.get("POSTGRES_HOST", "").strip()
    )
    if host:
        port = os.environ.get("PGPORT") or os.environ.get("POSTGRES_PORT") or "5432"
        user = (
            os.environ.get("PGUSER")
            or os.environ.get("POSTGRES_USER")
            or "postgres"
        )
        password = os.environ.get("PGPASSWORD") or os.environ.get("POSTGRES_PASSWORD") or ""
        db = (
            os.environ.get("PGDATABASE")
            or os.environ.get("POSTGRES_DB")
            or "railway"
        )
        return f"postgresql://{user}:{password}@{host}:{port}/{db}", "PGHOST"

    return "", ""


def _to_asyncpg_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if (
        url.startswith("postgresql://")
        and "+asyncpg" not in url
        and "+psycopg" not in url
    ):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    telegram_bot_token: str

    apify_token: str = ""
    apify_actor: str = "apify~instagram-scraper"
    apify_following_actor: str = "scraping_solutions~instagram-scraper-followers-following-no-cookies"
    apify_timeout_seconds: int = 120

    instagram_username: str = ""
    instagram_password: str = ""
    instagram_session_path: str = "sessions/service.json"

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
    database_url_source: str = "default"
    bot_name: str = "Reeldrive"
    bot_mention: str = "reeldrivebot"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        explicit = (value or "").strip()
        pg_url, pg_key = _postgres_url_from_env()

        # Postgres env always wins (Railway injects via service link / references)
        if pg_url:
            return _to_asyncpg_url(pg_url)

        if explicit:
            url = explicit
        else:
            url = _DEFAULT_SQLITE

        url = _to_asyncpg_url(url) if _is_postgres_url(url) else url

        if os.environ.get("RAILWAY_ENVIRONMENT") and "sqlite" in url:
            data_dir = _railway_data_dir()
            if url in (_DEFAULT_SQLITE, "sqlite+aiosqlite:///./data/reeldrive.db"):
                url = _sqlite_file_url(data_dir)
            elif str(data_dir) not in url:
                url = _sqlite_file_url(data_dir)
        return url

    @model_validator(mode="after")
    def set_database_source(self) -> "Settings":
        pg_url, pg_key = _postgres_url_from_env()
        if pg_url:
            self.database_url_source = pg_key
        elif self.database_is_postgres:
            self.database_url_source = "DATABASE_URL"
        elif "sqlite" in self.database_url:
            self.database_url_source = "sqlite"
        return self

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

    @property
    def legacy_sqlite_path(self) -> Path:
        """Old sqlite file on Railway volume (before Postgres link)."""
        return _railway_data_dir() / "reeldrive.db"

    verification_code_ttl_minutes: int = 15
    bridge_poll_interval_seconds: float = 2.0
    bridge_poll_idle_seconds: float = 10.0
    max_zip_posts: int = 100
    max_following_list: int = 10000  # Instagram itself caps following at ~7500

    stars_payment_enabled: bool = True
    free_direct_downloads: int = 3
    download_requires_subscription: bool = True
    payment_support_username: str = "reeldrive"
    webapp_base_url: str = ""  # optional override; default = same host as dashboard
    pro_stars_price: int = 20
    pro_toman_monthly: int = 98000
    pro_subscription_days: int = 30

    # Following-list: must join these channels; every account looked up
    # costs a token bought via manual card-to-card (no free pages).
    following_required_channels: str = "@abolfazl_nouriii,@reeldirve"
    # On top of the base channels above, each user is also required to
    # join exactly one of these — alternated per user (by telegram_id) so
    # the join load is split evenly across them.
    following_alternate_channels: str = "@license_club,@breaking_text"
    following_page_price_toman: int = 15000
    following_free_pages: int = 0
    # Only the first card is active for now — add more comma-separated
    # whenever rotation should resume.
    following_support_cards: str = "6104331002522101"
    following_card_holder_name: str = "احمد عابدزاده"
    following_cards_rotate_every: int = 15
    admin_telegram_ids: str = "99686187,8989258776"
    # Who actually gets pushed the receipt/purchase-request messages — a
    # subset of admin_telegram_ids. Everyone in admin_telegram_ids can still
    # approve manually (e.g. via /addtokens), they just aren't pinged.
    following_notify_ids: str = "8989258776"

    @property
    def shop_webapp_url(self) -> str:
        """Mini App lives on the dashboard at /shop — same public URL."""
        base = (self.webapp_base_url or "").strip()
        if not base:
            base = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "").strip()
        if not base and os.environ.get("RAILWAY_ENVIRONMENT"):
            base = "reeldrive.up.railway.app"
        if not base:
            base = f"localhost:{self.dashboard_port}"
        if not base.startswith("http"):
            scheme = "http" if base.startswith("localhost") else "https"
            base = f"{scheme}://{base}"
        return f"{base.rstrip('/')}/shop"

    openai_api_key: str = ""
    ai_api_base: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-4o"
    ai_vision_enabled: bool = True
    ai_video_frames_enabled: bool = True
    ai_video_frame_count: int = 8
    ai_video_max_mb: int = 25
    ai_video_max_duration: int = 90
    ai_analysis_requires_pro: bool = True
    ai_free_monthly_limit: int = 0
    ai_pro_monthly_limit: int = 80
    ai_unlimited_usernames: str = "parsaforughi"
    ai_unlimited_telegram_ids: str = "99686187"
    ai_page_benchmark_enabled: bool = True
    ai_page_posts_for_avg: int = 12
    ai_max_tokens: int = 1500
    ai_timeout_seconds: int = 120

    dashboard_password: str = "admin"
    dashboard_secret: str = "change-me-dashboard-secret"
    dashboard_port: int = 8080

    @field_validator("ai_api_base", mode="before")
    @classmethod
    def normalize_ai_api_base(cls, value: str) -> str:
        url = (value or "").strip()
        if "gapgpt" in url.lower():
            return "https://api.openai.com/v1"
        return url or "https://api.openai.com/v1"

    @model_validator(mode="after")
    def normalize_ai_model_for_openai(self) -> "Settings":
        base = self.ai_api_base.lower()
        legacy_models = {"gpt-5.2", "gpt-5", "gpt5.2"}
        if "api.openai.com" in base and self.ai_model.strip().lower() in legacy_models:
            self.ai_model = "gpt-4o"
        return self

    @property
    def ai_chat_completions_url(self) -> str:
        return f"{self.ai_api_base.rstrip('/')}/chat/completions"

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
