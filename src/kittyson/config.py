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

    # A pixabay.com API key (free, pixabay.com/api/docs). The cats come from Pixabay: without a key no new cat is made.
    pixabay_key: str = ""
    # The model that looks at a Pixabay photo to see whether it is a cat. A full model id or a claude CLI alias.
    cat_model: str = "claude-opus-5-5"

    # The model that picks the day's quote.
    quote_model: str = "claude-opus-5-5"

    # Where to say that a day's cat or quote could not be made: a Telegram bot's token and the chat it writes to.
    # Without them a failure is only logged.
    telegram_token: str = ""
    telegram_chat: str = ""

    data_dir: Path = Path("data")

    # Log file cap: one file is at most log_max_mb, and log_backups older files are kept.
    # Total on disk: log_max_mb x (log_backups + 1).
    log_max_mb: int = 5
    log_backups: int = 3

    @property
    def cats_daily(self) -> Path:
        return self.data_dir / "cats" / "daily"

    @property
    def quotes(self) -> Path:
        return self.data_dir / "quotes"

    @property
    def logs(self) -> Path:
        return self.data_dir / "logs"


settings = Settings()
