from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/tgtexnika",
        description="Async PostgreSQL DSN",
    )

    # Telegram Bot
    BOT_TOKEN: str = Field(default="", description="Telegram Bot API token")

    # JWT / Auth
    SECRET_KEY: str = Field(default="change-me", description="JWT signing key")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=480)

    # Google Sheets (optional)
    GOOGLE_SHEETS_CREDENTIALS_FILE: str = Field(default="credentials.json")
    GOOGLE_SHEETS_SPREADSHEET_ID: str = Field(default="")

    # Email for Error reports
    SMTP_SERVER: str = Field(default="smtp.gmail.com", description="SMTP server address")
    SMTP_PORT: int = Field(default=465, description="SMTP server port (465 for SSL)")
    SMTP_USERNAME: str = Field(default="", description="Email address for SMTP login")
    SMTP_PASSWORD: str = Field(default="", description="Email password or App Password for SMTP")
    DEVELOPER_EMAIL: str = Field(default="nembnem4@gmail.com", description="Developer email to receive reports")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
