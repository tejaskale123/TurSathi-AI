"""create_login_history_table

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-10-30 03:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, None] = 'a2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'login_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('login_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('login_method', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('failure_reason', sa.String(length=100), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_login_history_user_id'), 'login_history', ['user_id'], unique=False)
    op.create_index(op.f('ix_login_history_login_at'), 'login_history', ['login_at'], unique=False)
    op.create_index('ix_login_history_status_login_at', 'login_history', ['status', 'login_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_login_history_status_login_at', table_name='login_history')
    op.drop_index(op.f('ix_login_history_login_at'), table_name='login_history')
    op.drop_index(op.f('ix_login_history_user_id'), table_name='login_history')
    op.drop_table('login_history')
