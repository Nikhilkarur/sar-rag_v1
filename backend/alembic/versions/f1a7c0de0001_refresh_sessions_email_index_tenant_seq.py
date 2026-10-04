"""per-session refresh tokens, lower(email) index, tenant public-id sequence

Revision ID: f1a7c0de0001
Revises: c3ce3e9551d4
Create Date: 2026-10-04 00:00:00.000000

- refresh_sessions: one row per login, so a second login no longer invalidates the
  first session's refresh token, and a replayed (already-rotated) token can revoke
  its session. Replaces users.refresh_token_hash (left in place, unused).
- ix_users_email_lower: logins/signups now match emails case-insensitively via
  lower(email). Non-unique on purpose: databases may already hold accounts that
  differ only by case, and new rows are always written lowercase, so the existing
  unique constraint on users.email already rejects new duplicates.
- tenant_public_id_seq: atomic TEN-XXXX allocation for concurrent approvals. Starts
  after the highest id already issued.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a7c0de0001'
down_revision: Union[str, None] = 'c3ce3e9551d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('refresh_sessions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('token_hash', sa.String(length=255), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revoked_reason', sa.String(length=30), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_refresh_sessions_user_id'), 'refresh_sessions', ['user_id'], unique=False)

    op.create_index('ix_users_email_lower', 'users', [sa.text('lower(email)')], unique=False)

    op.execute("CREATE SEQUENCE tenant_public_id_seq")
    op.execute(
        "SELECT setval('tenant_public_id_seq', COALESCE((SELECT max(substring(tenant_id_public "
        "FROM '^TEN-([0-9]+)$')::bigint) FROM tenants), 0) + 1, false)"
    )


def downgrade() -> None:
    op.execute("DROP SEQUENCE IF EXISTS tenant_public_id_seq")
    op.drop_index('ix_users_email_lower', table_name='users')
    op.drop_index(op.f('ix_refresh_sessions_user_id'), table_name='refresh_sessions')
    op.drop_table('refresh_sessions')
