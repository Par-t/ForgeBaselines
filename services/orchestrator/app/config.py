from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Storage
    storage_backend: str = "local"
    s3_bucket: str = "forgebaselines-artifacts"

    # MLflow
    mlflow_tracking_uri: str = "http://localhost:5000"

    # Services
    classification_service_url: str = "http://localhost:8001"

    # AWS
    aws_default_region: str = "us-east-2"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    # Environment
    env: str = "development"


settings = Settings()
