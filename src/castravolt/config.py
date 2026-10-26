from typing import Literal
from urllib.parse import urlsplit
from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_prefix='CASTRAVOLT_', extra='ignore')
    database_url: str | None = None
    cors_origins: list[str] = Field(default_factory=lambda: ['http://localhost:5173'])
    database_pool_size: int = Field(default=5, ge=1, le=20)
    database_max_overflow: int = Field(default=5, ge=0, le=20)
    frontend_url: str = 'http://127.0.0.1:5173'
    secure_cookies: bool = False
    environment: Literal['development','production'] = 'development'
    session_hours: int = Field(default=24,ge=1,le=168)
    auth_rate_limit: int = Field(default=30,ge=1,le=1000)
    mail_mode: Literal['file','smtp'] = 'file'
    mail_directory: str = 'tmp/mailbox'
    mail_from: str = 'CastraVolt <noreply@castravolt.local>'
    smtp_host: str = 'localhost'
    smtp_port: int = Field(default=587,ge=1,le=65535)
    smtp_starttls: bool = True
    smtp_username: str = ''
    smtp_password: SecretStr = SecretStr('')

    @field_validator('frontend_url')
    @classmethod
    def valid_frontend(cls,value):
        url=urlsplit(value)
        if url.scheme not in {'http','https'} or not url.netloc or url.username or url.password or url.path not in {'','/'} or url.query or url.fragment:
            raise ValueError('frontend_url must be an HTTP(S) origin')
        return value.rstrip('/')

    @model_validator(mode='after')
    def safe_production(self):
        if self.environment=='production' and (not self.secure_cookies or self.mail_mode!='smtp' or not self.smtp_starttls or not self.frontend_url.startswith('https://')):
            raise ValueError('Production requires HTTPS, secure cookies and TLS SMTP delivery')
        return self

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
