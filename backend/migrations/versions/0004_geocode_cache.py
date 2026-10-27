"""Successful address-search result cache."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision='0004_geocode_cache'
down_revision='0003_projects'
branch_labels=None
depends_on=None


def upgrade():
    op.create_table('geocode_cache',sa.Column('key',sa.String(64),primary_key=True),
        sa.Column('results',JSONB(),nullable=False),sa.Column('expires_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_geocode_cache_expires_at','geocode_cache',['expires_at'])


def downgrade():
    op.drop_table('geocode_cache')
