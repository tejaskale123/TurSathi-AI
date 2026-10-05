"""add_leaf_webber_historical_recommendation

Revision ID: c7d8e9f0a1b2
Revises: b5c9d1e2f3a4
Create Date: 2026-10-05 17:18:00.000000+00:00

Adds historical recommendation for Leaf_webber from ICAR-IIPR (Dichlorvos 76 EC).
Notes that the pesticide is now banned in India.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone

# revision identifiers, used by Alembic.
revision: str = 'c7d8e9f0a1b2'
down_revision: Union[str, None] = 'b5c9d1e2f3a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text("""
            INSERT INTO tur_disease_recommendations (
                crop,
                disease_name,
                disease_description,
                treatment,
                active_ingredient,
                recommended_quantity,
                water_quantity,
                per_pump_quantity,
                spray_timing,
                application_method,
                safety_precautions,
                after_spray_advisory,
                is_active,
                created_at,
                updated_at
            )
            VALUES (
                'tur',
                'Leaf_webber',
                'Leaf webber (Grapholita critica Meyr.) is a pest of pigeonpea. The larvae web the terminal leaves together and feed from inside.',
                'Historical ICAR recommendation: Dichlorvos 76 EC (NOTE: BANNED IN INDIA)',
                'Dichlorvos 76 EC (BANNED)',
                '1.0 ml per litre of water (HISTORICAL ONLY)',
                NULL,
                NULL,
                'Historical recommendation was at fortnightly intervals. DO NOT USE BANNED CHEMICALS.',
                'Historical foliar spray.',
                'CRITICAL: Dichlorvos (DDVP) is BANNED for use in India as per Ministry of Agriculture notification S.O. 1196(E) dated March 20, 2020. Do not use this pesticide. Please consult a qualified agricultural expert or your local Krishi Vigyan Kendra (KVK) for currently approved alternatives.',
                'Follow current official agricultural advice and latest registered labels.',
                TRUE,
                NOW(),
                NOW()
            )
            ON CONFLICT ON CONSTRAINT uq_tur_disease_recommendations_crop_disease DO NOTHING
        """)
    )


def downgrade() -> None:
    op.execute(
        sa.text("""
            DELETE FROM tur_disease_recommendations
            WHERE crop = 'tur' AND disease_name = 'Leaf_webber'
        """)
    )
