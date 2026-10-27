"""Preserve legacy adoption history while allowing the ten-feature model to omit it."""
from alembic import op
import sqlalchemy as sa
revision='0007_optional_adoption'
down_revision='0006_prediction_idempotency'
branch_labels=None
depends_on=None


def upgrade():
    op.alter_column('predictions','adoption_reference_year',existing_type=sa.Integer(),nullable=True)
    op.alter_column('predictions','adoption_value',existing_type=sa.Integer(),nullable=True)


def downgrade():
    count=op.get_bind().execute(sa.text('SELECT COUNT(*) FROM predictions WHERE adoption_reference_year IS NULL OR adoption_value IS NULL')).scalar()
    if count:raise RuntimeError('Newer predictions have no adoption context. Preserve them before downgrading.')
    op.alter_column('predictions','adoption_reference_year',existing_type=sa.Integer(),nullable=False)
    op.alter_column('predictions','adoption_value',existing_type=sa.Integer(),nullable=False)
