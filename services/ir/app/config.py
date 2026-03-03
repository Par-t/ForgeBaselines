"""IR service configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    mlflow_tracking_uri: str = "http://mlflow:5000"
    env: str = "development"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
