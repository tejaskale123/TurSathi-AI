"""add_google_auth_fields

Revision ID: 615b1d654a3c
Revises: d8e9f0a1b2c3
Create Date: 2026-10-07 12:06:44.581895+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '615b1d654a3c'
down_revision: Union[str, None] = 'd8e9f0a1b2c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns
    op.add_column('users', sa.Column('google_id', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('auth_provider', sa.String(length=50), nullable=False, server_default='local'))
    
    # Create index for google_id
    op.create_index(op.f('ix_users_google_id'), 'users', ['google_id'], unique=True)
    
    # Alter existing columns to be nullable
    op.alter_column('users', 'mobile_number', existing_type=sa.String(length=20), nullable=True)
    op.alter_column('users', 'password_hash', existing_type=sa.String(length=255), nullable=True)


def downgrade() -> None:
    # Revert columns to not nullable
    op.alter_column('users', 'password_hash', existing_type=sa.String(length=255), nullable=False)
    op.alter_column('users', 'mobile_number', existing_type=sa.String(length=20), nullable=False)
    
    # Drop index and columns
    op.drop_index(op.f('ix_users_google_id'), table_name='users')
    op.drop_column('users', 'auth_provider')
    op.drop_column('users', 'google_id')
