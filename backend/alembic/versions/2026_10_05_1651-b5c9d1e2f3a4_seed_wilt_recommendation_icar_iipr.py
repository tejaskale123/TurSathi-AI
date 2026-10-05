"""seed_wilt_recommendation_icar_iipr

Adds verified Wilt (Fusarium udum) disease recommendation for pigeonpea.

Source: ICAR-IIPR (Indian Institute of Pulses Research), Kanpur.
        Official technology module for pigeonpea wilt management.

Treatment: Trichoderma viride biological seed treatment @ 10 g/kg seed.
           This is a seed treatment / soil biological agent — NOT a foliar spray.
           Water quantity and pump quantity are NOT applicable for seed treatment.

Leaf_webber: No sufficiently verified recommendation with specific dosage
             found from an authoritative official source. Kept unavailable.

Revision ID: b5c9d1e2f3a4
Revises: a3f8b2c1d4e5
Create Date: 2026-10-05 16:51:00.000000+00:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone

# revision identifiers, used by Alembic.
revision: str = 'b5c9d1e2f3a4'
down_revision: Union[str, None] = 'a3f8b2c1d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Insert verified Wilt recommendation (ICAR-IIPR)
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
                'Wilt',
                'Fusarium wilt (Fusarium udum) is a serious soil-borne fungal disease of pigeonpea. Infected plants show yellowing, wilting, and death, often from one side of the plant. The disease persists in soil for many years.',
                'Trichoderma viride seed treatment — a biological agent that colonizes the root zone and provides protection against Fusarium udum.',
                'Trichoderma viride (biological fungicide / biocontrol agent)',
                '10 g per kg of seed',
                NULL,
                NULL,
                'Apply as seed treatment before sowing. If also applying Rhizobium culture, apply Trichoderma first, allow seeds to shade-dry for ~2 hours, then apply Rhizobium.',
                'Seed treatment (biological). This is NOT a foliar spray. Mix the required quantity of Trichoderma viride uniformly with seeds. Shade-dry for ~2 hours before sowing. Optionally combine with soil application: mix 2.5 kg Trichoderma viride/ha with 50 kg well-decomposed FYM and apply to soil before sowing.',
                'Avoid exposure to direct sunlight after treating seeds as it reduces bioagent viability. Do not mix with chemical fungicides unless compatibility is confirmed. Wash hands after handling. Store treated seeds in shade.',
                'Uproot and remove wilted plants from the field to reduce inoculum. Practice crop rotation — avoid growing pigeonpea in the same field for at least 3 years in wilt-affected areas. Monitor the crop and consult your local Krishi Vigyan Kendra (KVK) for region-specific follow-up. Source: ICAR-IIPR, Kanpur.',
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
            WHERE crop = 'tur' AND disease_name = 'Wilt'
        """)
    )
