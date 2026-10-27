"""Versioned successful POI extraction cache."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision='0005_poi_cache'
down_revision='0004_geocode_cache'
branch_labels=None
depends_on=None


def upgrade():
    op.create_table('poi_cache',sa.Column('key',sa.String(64),primary_key=True),
        sa.Column('counts',JSONB(),nullable=False),sa.Column('provenance',JSONB(),nullable=False),
        sa.Column('extracted_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('expires_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_poi_cache_expires_at','poi_cache',['expires_at'])


def downgrade(): op.drop_table('poi_cache')
