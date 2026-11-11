"""Runtime settings. Every value can be overridden with a KITTYSON_* env var or a .env file.

Import the one instance and read from it: `from kittyson.config import settings`.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KITTYSON_", env_file=".env", extra="ignore")

    tz: str = "Asia/Seoul"

    # Weather location (default: Seoul city hall)
    lat: float = 37.5665
    lon: float = 126.9780
    weather_ttl_seconds: int = 30 * 60

    cat_size: int = 1024

    # The model that writes the day's fortune. A claude CLI alias or a full model id.
    fortune_model: str = "haiku"

    data_dir: Path = Path("data")

    host: str = "0.0.0.0"
    port: int = 8000

    @property
    def cats_inbox(self) -> Path:
        return self.data_dir / "cats" / "inbox"

    @property
    def cats_daily(self) -> Path:
        return self.data_dir / "cats" / "daily"

    @property
    def fortunes(self) -> Path:
        return self.data_dir / "fortunes"


settings = Settings()
