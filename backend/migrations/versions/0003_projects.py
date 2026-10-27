"""Owned projects, sites and immutable prediction snapshots."""
from alembic import op

revision = '0003_projects'
down_revision = '0002_accounts'
branch_labels = None
depends_on = None


def upgrade():
    # Freeze the table definitions here so later ORM edits cannot change this migration.
    import sqlalchemy as sa
    from sqlalchemy.dialects.postgresql import JSONB
    op.create_table('projects',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('owner_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False), sa.Column('description', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_projects_owner_id', 'projects', ['owner_id'])
    op.create_table('sites',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('project_id', sa.Uuid(), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False), sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False), sa.Column('state', sa.String(40)),
        sa.Column('category', sa.String(60), nullable=False), sa.Column('address', sa.String(500), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('latitude BETWEEN -90 AND 90'), sa.CheckConstraint('longitude BETWEEN -180 AND 180'))
    op.create_index('ix_sites_project_id', 'sites', ['project_id'])
    op.create_table('predictions',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('site_id', sa.Uuid(), sa.ForeignKey('sites.id', ondelete='CASCADE'), nullable=False),
        sa.Column('requester_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('input_snapshot', JSONB(), nullable=False), sa.Column('raw_estimate', sa.Float(), nullable=False),
        sa.Column('displayed_total', sa.Integer(), nullable=False),
        sa.Column('model_version', sa.String(100), nullable=False),
        sa.Column('extraction_rule_version', sa.String(100), nullable=False),
        sa.Column('poi_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('adoption_reference_year', sa.Integer(), nullable=False),
        sa.Column('adoption_value', sa.Integer(), nullable=False),
        sa.Column('rounding_policy', sa.String(100), nullable=False),
        sa.Column('idempotency_key', sa.String(128)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('displayed_total >= 1'))
    op.create_index('ix_predictions_site_id', 'predictions', ['site_id'])


def downgrade():
    for table in ['predictions', 'sites', 'projects']:
        op.drop_table(table)
