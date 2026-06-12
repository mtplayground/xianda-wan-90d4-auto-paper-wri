import json
from dataclasses import dataclass
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


def _require(value: str | None, env_name: str) -> str:
    if not value:
        raise RuntimeError(f"{env_name} environment variable is required")
    return value


@dataclass(frozen=True)
class MctaiAuthConfig:
    url: str
    app_token: str
    jwks_url: str


@dataclass(frozen=True)
class ClaudeConfig:
    api_key: str
    base_url: str
    model: str


class Settings(BaseSettings):
    app_name: str = "xianda-wan-90d4-auto-paper-wri"
    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 8080
    self_url: str | None = None
    database_url: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_bucket: str | None = None
    s3_prefix: str | None = None
    s3_endpoint: str | None = None
    s3_region: str = "auto"
    s3_force_path_style: bool = True
    mctai_auth_url: str | None = None
    mctai_auth_app_token: str | None = None
    mctai_auth_jwks_url: str | None = None
    anthropic_api_key: str | None = None
    anthropic_base_url: str = "https://api.anthropic.com"
    claude_model: str | None = None
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_prefix="",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        stripped = self.cors_origins.strip()
        if not stripped:
            return []
        if stripped.startswith("["):
            return json.loads(stripped)
        return [origin.strip() for origin in stripped.split(",") if origin.strip()]

    def require_database_url(self) -> str:
        return _require(self.database_url, "DATABASE_URL")

    def require_mctai_auth(self) -> MctaiAuthConfig:
        return MctaiAuthConfig(
            url=_require(self.mctai_auth_url, "MCTAI_AUTH_URL"),
            app_token=_require(self.mctai_auth_app_token, "MCTAI_AUTH_APP_TOKEN"),
            jwks_url=_require(self.mctai_auth_jwks_url, "MCTAI_AUTH_JWKS_URL"),
        )

    def require_claude(self) -> ClaudeConfig:
        return ClaudeConfig(
            api_key=_require(self.anthropic_api_key, "ANTHROPIC_API_KEY"),
            base_url=self.anthropic_base_url,
            model=_require(self.claude_model, "CLAUDE_MODEL"),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
