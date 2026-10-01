"""create_tur_disease_recommendations_table

Revision ID: a3f8b2c1d4e5
Revises: 277ef63be889
Create Date: 2026-10-01 19:26:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f8b2c1d4e5'
down_revision: Union[str, None] = '277ef63be889'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'tur_disease_recommendations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('crop', sa.String(length=50), nullable=False),
        sa.Column('disease_name', sa.String(length=255), nullable=False),
        sa.Column('disease_description', sa.Text(), nullable=True),
        sa.Column('treatment', sa.Text(), nullable=True),
        sa.Column('active_ingredient', sa.String(length=255), nullable=True),
        sa.Column('recommended_quantity', sa.String(length=255), nullable=True),
        sa.Column('water_quantity', sa.String(length=255), nullable=True),
        sa.Column('per_pump_quantity', sa.String(length=255), nullable=True),
        sa.Column('spray_timing', sa.Text(), nullable=True),
        sa.Column('application_method', sa.Text(), nullable=True),
        sa.Column('safety_precautions', sa.Text(), nullable=True),
        sa.Column('after_spray_advisory', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
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
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'crop',
            'disease_name',
            name='uq_tur_disease_recommendations_crop_disease',
        ),
    )
    op.create_index(
        op.f('ix_tur_disease_recommendations_crop'),
        'tur_disease_recommendations',
        ['crop'],
        unique=False,
    )
    op.create_index(
        op.f('ix_tur_disease_recommendations_disease_name'),
        'tur_disease_recommendations',
        ['disease_name'],
        unique=False,
    )
    op.create_index(
        op.f('ix_tur_disease_recommendations_is_active'),
        'tur_disease_recommendations',
        ['is_active'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_tur_disease_recommendations_is_active'),
        table_name='tur_disease_recommendations',
    )
    op.drop_index(
        op.f('ix_tur_disease_recommendations_disease_name'),
        table_name='tur_disease_recommendations',
    )
    op.drop_index(
        op.f('ix_tur_disease_recommendations_crop'),
        table_name='tur_disease_recommendations',
    )
    op.drop_table('tur_disease_recommendations')
