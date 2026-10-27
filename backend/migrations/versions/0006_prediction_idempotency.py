"""Prevent duplicate saved predictions for the same site and request key."""
from alembic import op
revision='0006_prediction_idempotency'
down_revision='0005_poi_cache'
branch_labels=None
depends_on=None


def upgrade():op.create_unique_constraint('uq_prediction_site_key','predictions',['site_id','idempotency_key'])


def downgrade():op.drop_constraint('uq_prediction_site_key','predictions',type_='unique')
