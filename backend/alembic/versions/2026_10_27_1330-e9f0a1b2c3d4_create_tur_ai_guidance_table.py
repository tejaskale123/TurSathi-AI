"""create_tur_ai_guidance_table

Revision ID: e9f0a1b2c3d4
Revises: 615b1d654a3c
Create Date: 2026-10-27 13:30:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e9f0a1b2c3d4'
down_revision: Union[str, None] = '615b1d654a3c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'tur_ai_guidance',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('scan_id', sa.Integer(), nullable=False),
        sa.Column('language', sa.String(length=10), nullable=False),
        sa.Column('disease_name', sa.String(length=255), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='success'),
        sa.Column('disease_explanation', sa.Text(), nullable=False),
        sa.Column('farmer_actions', sa.JSON(), nullable=False),
        sa.Column('warnings', sa.JSON(), nullable=False),
        sa.Column('spray_guidance_available', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('ai_guidance_available', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('important_alert', sa.String(length=1024), nullable=True),
        sa.Column('cache_fingerprint', sa.String(length=64), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['scan_id'], ['tur_scans.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('scan_id', 'language', name='uq_tur_ai_guidance_scan_language'),
    )
    op.create_index(op.f('ix_tur_ai_guidance_scan_id'), 'tur_ai_guidance', ['scan_id'], unique=False)
    op.create_index(op.f('ix_tur_ai_guidance_cache_fingerprint'), 'tur_ai_guidance', ['cache_fingerprint'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_tur_ai_guidance_cache_fingerprint'), table_name='tur_ai_guidance')
    op.drop_index(op.f('ix_tur_ai_guidance_scan_id'), table_name='tur_ai_guidance')
    op.drop_table('tur_ai_guidance')
