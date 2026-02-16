from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # MLflow
    mlflow_tracking_uri: str = "http://localhost:5000"

    # Environment
    env: str = "development"


settings = Settings()