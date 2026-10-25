"""Centralized application settings using pydantic-settings."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global system configuration."""

    ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000

    # Local filesystem paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    PROFILE_DATA_PATH: Path = BASE_DIR / "data" / "profile.json"
    PROFILE_EXAMPLE_PATH: Path = BASE_DIR / "data" / "profile.example.json"
    STORAGE_DIR: Path = BASE_DIR / "storage"
    DB_PATH: Path = STORAGE_DIR / "app.db"
    DB_URL: str = f"sqlite+aiosqlite:///{DB_PATH.as_posix()}"
    LOGS_DIR: Path = BASE_DIR / "logs"
    APPLICATIONS_OUTPUT_DIR: Path = BASE_DIR / "output" / "applications"
    TEMPLATES_DIR: Path = BASE_DIR / "templates"

    # LaTeX configuration
    LATEX_CMD: str = "pdflatex"
    LATEX_TEMPLATE_PATH: Path = TEMPLATES_DIR / "cv_template.tex"

    # AI API keys (optional)
    GEMINI_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

# Ensure critical runtime directories exist locally
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
settings.APPLICATIONS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
