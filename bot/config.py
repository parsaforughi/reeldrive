from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    telegram_bot_token: str
    instagram_username: str = ""
    instagram_password: str = ""
    instagram_session_path: str = "sessions/instagram.json"
    bot_name: str = "Regram Pro"

    @property
    def session_file(self) -> Path:
        return Path(self.instagram_session_path)


settings = Settings()
