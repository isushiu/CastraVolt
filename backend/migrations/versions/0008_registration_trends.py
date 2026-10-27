"""Versioned monthly registration data and reusable narrative summaries."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision='0008_registration_trends'
down_revision='0007_optional_adoption'
branch_labels=None
depends_on=None


def upgrade():
    op.create_table('registration_source_versions',sa.Column('id',sa.String(64),primary_key=True),sa.Column('manifest',postgresql.JSONB(),nullable=False),sa.Column('active',sa.Boolean(),nullable=False),sa.Column('imported_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('uq_registration_active','registration_source_versions',['active'],unique=True,postgresql_where=sa.text('active'))
    op.create_table('registration_months',sa.Column('version_id',sa.String(64),sa.ForeignKey('registration_source_versions.id',ondelete='CASCADE'),primary_key=True),sa.Column('state',sa.String(40),primary_key=True),sa.Column('month',sa.String(7),primary_key=True),sa.Column('count',sa.Integer(),nullable=False),sa.CheckConstraint('count >= 0'))
    op.create_table('trend_summary_cache',sa.Column('key',sa.String(64),primary_key=True),sa.Column('version_id',sa.String(64),sa.ForeignKey('registration_source_versions.id',ondelete='CASCADE'),nullable=False),sa.Column('model',sa.String(120),nullable=False),sa.Column('prompt_version',sa.String(40),nullable=False),sa.Column('filters',postgresql.JSONB(),nullable=False),sa.Column('status',sa.String(16),nullable=False),sa.Column('content',sa.Text()),sa.Column('lease_token',sa.String(36)),sa.Column('lease_until',sa.DateTime(timezone=True),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_trend_summary_cache_version_id','trend_summary_cache',['version_id'])
    from castravolt.trends_data import packaged_snapshot
    from castravolt.trends import publish_snapshot
    from sqlalchemy.orm import Session
    with Session(bind=op.get_bind()) as session:
        publish_snapshot(session,packaged_snapshot())
        session.commit()


def downgrade():
    op.drop_table('trend_summary_cache');op.drop_table('registration_months');op.drop_table('registration_source_versions')
