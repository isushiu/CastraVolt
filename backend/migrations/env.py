from alembic import context
from castravolt.config import Settings
from castravolt.database import Base, make_engine
import castravolt.account_models  # Register account metadata for autogeneration.
import castravolt.project_models
import castravolt.location_models
import castravolt.feature_models

config = context.config
settings = Settings()
if not settings.database_url:
    raise RuntimeError('Set CASTRAVOLT_DATABASE_URL before running migrations')
target_metadata = Base.metadata

if context.is_offline_mode():
    context.configure(url=settings.database_url, target_metadata=target_metadata,
                      literal_binds=True, dialect_opts={'paramstyle': 'named'})
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = make_engine(settings)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()
