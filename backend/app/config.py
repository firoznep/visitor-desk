from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "production"] = "production"
    database_url: str                      # postgresql+asyncpg://visitor_app:...@db:5432/visitors
    timezone: str = "Asia/Qatar"           # defines what "today" means for receptionists
    allowed_origins: str = ""              # comma separated, e.g. https://visitors.example.com

    cookie_name: str = ""  # if unset, computed below: __Host- prefix only applies when Secure
    cookie_secure: bool = True
    session_idle_minutes: int = 30
    session_absolute_hours: int = 12

    lockout_threshold: int = 5
    lockout_minutes: int = 15

    # Encryption of ID numbers / dates of birth at rest (see README, "Keys and backups")
    id_encryption_keys: SecretStr          # "k1:<urlsafe-b64 32 bytes>,k0:<old key>"
    id_active_key_id: str = "k1"
    id_index_key: SecretStr                # HMAC key for the searchable ID hash. Never change without `reindex`.
    scan_token_secret: SecretStr
    scan_token_ttl_seconds: int = 600

    @property
    def resolved_cookie_name(self) -> str:
        # The __Host- prefix is a browser-enforced guarantee (no Domain attribute, Path=/,
        # Secure only) and every modern client, including curl, refuses to store such a
        # cookie without the Secure flag. So it's only valid when serving over HTTPS.
        if self.cookie_name:
            return self.cookie_name
        return "__Host-vd_session" if self.cookie_secure else "vd_session"

    @property
    def origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def is_prod(self) -> bool:
        return self.app_env == "production"

    @model_validator(mode="after")
    def _prod_guards(self):
        if self.is_prod and not self.cookie_secure:
            raise ValueError("COOKIE_SECURE must be true in production")
        if self.is_prod and not self.origins:
            raise ValueError("ALLOWED_ORIGINS must be set in production")
        return self


settings = Settings()  # type: ignore[call-arg]
