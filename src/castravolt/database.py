from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase

from castravolt.config import Settings


class Base(DeclarativeBase):
    pass


def make_engine(settings: Settings):
    if not settings.database_url:
        return None
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=5,
        connect_args={'connect_timeout': 3, 'options': '-c statement_timeout=3000'},
    )
