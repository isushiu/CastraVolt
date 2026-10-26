"""Individual accounts, hashed sessions/tokens and shared rate limits."""
from alembic import op
import sqlalchemy as sa

revision = '0002_accounts'
down_revision = '0001_foundation'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('users',sa.Column('id',sa.Uuid(),primary_key=True),
        sa.Column('email',sa.String(254),nullable=False),sa.Column('name',sa.String(100),nullable=False),
        sa.Column('password_hash',sa.String(512),nullable=False),sa.Column('verified_at',sa.DateTime(timezone=True)),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_users_email','users',['email'],unique=True)
    op.create_table('sessions',sa.Column('id',sa.Uuid(),primary_key=True),
        sa.Column('user_id',sa.Uuid(),sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),
        sa.Column('token_hash',sa.String(64),unique=True,nullable=False),sa.Column('csrf_hash',sa.String(64),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('expires_at',sa.DateTime(timezone=True),nullable=False),sa.Column('revoked_at',sa.DateTime(timezone=True)))
    op.create_index('ix_sessions_user_id','sessions',['user_id'])
    op.create_index('ix_sessions_expires_at','sessions',['expires_at'])
    op.create_table('account_tokens',sa.Column('id',sa.Uuid(),primary_key=True),
        sa.Column('user_id',sa.Uuid(),sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),
        sa.Column('token_hash',sa.String(64),unique=True,nullable=False),sa.Column('purpose',sa.String(20),nullable=False),
        sa.Column('expires_at',sa.DateTime(timezone=True),nullable=False),sa.Column('used_at',sa.DateTime(timezone=True)))
    op.create_index('ix_account_tokens_user_id','account_tokens',['user_id'])
    op.create_index('ix_account_tokens_expires_at','account_tokens',['expires_at'])
    op.create_table('auth_rate_limits',sa.Column('key',sa.String(64),primary_key=True),
        sa.Column('count',sa.Integer(),nullable=False),sa.Column('expires_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_auth_rate_limits_expires_at','auth_rate_limits',['expires_at'])


def downgrade():
    for table in ['auth_rate_limits','account_tokens','sessions','users']: op.drop_table(table)
