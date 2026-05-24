from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Bridge account — receives verification codes & user DMs
    instagram_bridge_username: str = ""
    instagram_bridge_password: str = ""
    instagram_bridge_session_path: str = "sessions/bridge.json"
    instagram_bridge_display: str = "reeldrivebot"

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

    @property
    def bridge_ig_handle(self) -> str:
        name = (
            self.instagram_bridge_display
            or self.instagram_bridge_username
            or self.bot_mention
        )
        return f"@{name.lstrip('@')}"


settings = Settings()
