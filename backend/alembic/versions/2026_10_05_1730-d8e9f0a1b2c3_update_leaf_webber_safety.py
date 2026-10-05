"""update_leaf_webber_safety

Revision ID: d8e9f0a1b2c3
Revises: c7d8e9f0a1b2
Create Date: 2026-10-05 17:30:00.000000+00:00

Updates Leaf_webber historical recommendation to remove actionable dosage
and spray timing to ensure farmers do not use the banned substance.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd8e9f0a1b2c3'
down_revision: Union[str, None] = 'c7d8e9f0a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text("""
            UPDATE tur_disease_recommendations
            SET treatment = 'Current approved treatment information is unavailable.',
                active_ingredient = 'Dichlorvos (DDVP) — BANNED IN INDIA',
                recommended_quantity = 'Not applicable — do not use.',
                water_quantity = NULL,
                per_pump_quantity = NULL,
                spray_timing = 'Not applicable — do not use.',
                application_method = 'Not applicable — do not use.',
                safety_precautions = 'CRITICAL: Dichlorvos (DDVP) is banned in India. Do NOT use this pesticide. Consult a qualified agricultural expert or your local KVK for currently approved alternatives.',
                after_spray_advisory = 'Follow the latest official agricultural recommendations and currently registered pesticide labels.',
                updated_at = NOW()
            WHERE crop = 'tur' AND disease_name = 'Leaf_webber'
        """)
    )


def downgrade() -> None:
    # We don't restore the dangerous actionable pesticide dosage in a downgrade.
    pass
