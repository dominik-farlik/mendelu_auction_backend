from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

COMPROMISED_SECRET_KEYS = {
    "9763f12ff2028efa1443a41da9fbad602b0c1033805048e5034247d94aeaa446",
}


class Settings(BaseSettings):
    SECRET_KEY: str
    PASSWORD_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    UPLOAD_DIR: Path

    ADMIN_EMAIL: str
    ADMIN_PASSWORD: str

    DATABASE_URL: str
    FRONTEND_URL: str
    BACKEND_URL: str

    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int
    MAIL_SERVER: str
    MAIL_STARTTLS: bool
    MAIL_SSL_TLS: bool

    TRANSPARENT_ACCOUNT: str = "Zatím nezadáno"

    model_config = SettingsConfigDict(env_file=".env")

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        if value in COMPROMISED_SECRET_KEYS:
            raise ValueError("SECRET_KEY je kompromitovaný (je v git historii), vygenerujte nový.")
        if len(value) < 32:
            raise ValueError("SECRET_KEY musí mít alespoň 32 znaků.")
        return value

    @field_validator("PASSWORD_ALGORITHM")
    @classmethod
    def validate_algorithm(cls, value: str) -> str:
        if value not in {"HS256", "HS384", "HS512"}:
            raise ValueError("PASSWORD_ALGORITHM musí být HS256, HS384 nebo HS512.")
        return value


@lru_cache
def get_settings():
    return Settings()
