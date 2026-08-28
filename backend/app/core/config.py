from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, loaded from environment variables / .env.

    See .env.example for the full list of recognized variables and their purpose.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"

    postgres_user: str = "structure_to_safety"
    postgres_password: str = "changeme_local_dev_only"
    postgres_db: str = "structure_to_safety"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str | None = None

    openfda_api_key: str | None = None

    random_seed: int = 42

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
