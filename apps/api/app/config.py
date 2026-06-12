from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "xianda-wan-90d4-auto-paper-wri"
    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 8080
    database_url: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_bucket: str | None = None
    s3_prefix: str | None = None
    s3_endpoint: str | None = None
    s3_region: str = "auto"
    s3_force_path_style: bool = True
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
