from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_prefix='CASTRAVOLT_', extra='ignore')
    database_url: str | None = None
    cors_origins: list[str] = Field(default_factory=lambda: ['http://localhost:5173'])
    database_pool_size: int = Field(default=5, ge=1, le=20)
    database_max_overflow: int = Field(default=5, ge=0, le=20)

    @field_validator('database_url')
    @classmethod
    def postgres_only(cls, value: str | None) -> str | None:
        if value and not value.startswith('postgresql+psycopg://'):
            raise ValueError('Use a postgresql+psycopg:// database URL')
        return value

    @field_validator('cors_origins')
    @classmethod
    def explicit_origins(cls, value: list[str]) -> list[str]:
        if '*' in value:
            raise ValueError('Credentialed requests require explicit origins')
        return value
