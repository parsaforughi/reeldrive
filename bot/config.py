from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Old Railway env values — never show these in /connect
_LEGACY_BRIDGE_HANDLES = frozenset(
    {"reeldrive_bridge", "reeldrive-bridge", "bridge", "regram_bridge"}
)


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
    # LOGIN = email or username for Instagram API (often ≠ public @handle)
    instagram_bridge_login: str = ""
    instagram_bridge_username: str = ""
    instagram_bridge_password: str = ""
    instagram_bridge_session_path: str = "sessions/bridge.json"
    instagram_bridge_display: str = "reeldrivebot"
    # Optional: sessionid from browser (avoids password login on Railway)
    instagram_session_id: str = ""
    instagram_bridge_session_id: str = ""
    # Optional: http://user:pass@host:port if IG blocks datacenter IP
    instagram_proxy: str = ""
    # Set false to never try bridge login (Bio /verify + Telegram links still work)
    instagram_bridge_enabled: bool = True
    # Try password login on server only if true (usually blocked on Railway)
    instagram_bridge_force_login: bool = False

    database_url: str = "sqlite+aiosqlite:///./data/reeldrive.db"
    bot_name: str = "Reeldrive"
    bot_mention: str = "reeldrivebot"

    verification_code_ttl_minutes: int = 15
    bridge_poll_interval_seconds: int = 20
    max_zip_posts: int = 100

    # Admin dashboard
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
        """@ shown in /connect — always reeldrivebot unless a valid custom display is set."""
        for raw in (self.instagram_bridge_display, self.instagram_bridge_username):
            name = (raw or "").strip().lstrip("@")
            if name and self._normalize_ig_handle(name) not in _LEGACY_BRIDGE_HANDLES:
                return name
        return self.bot_mention.lstrip("@")

    @property
    def bridge_ig_handle(self) -> str:
        return f"@{self._public_bridge_handle()}"


settings = Settings()
