import logging
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.database.models.tur_disease_recommendation import TurDiseaseRecommendation
from app.schemas.recommendation import SprayGuidanceResponse

logger = logging.getLogger("tursathi.services.recommendation")


def _parse_text_to_list(text_val: Optional[str], default_list: List[str]) -> List[str]:
    if not text_val or not text_val.strip():
        return default_list
    lines = [line.strip("- *").strip() for line in text_val.split("\n") if line.strip()]
    return lines if lines else default_list


def get_tur_spray_guidance_service(db: Session, disease_name: str) -> Optional[SprayGuidanceResponse]:
    clean_disease_name = disease_name.strip()
    if not clean_disease_name:
        return None

    # Leaf Webber safety: no verified chemical spray exists; historical Dichlorvos is banned
    if "webber" in clean_disease_name.lower():
        logger.info("[RECOMMENDATION SERVICE] Spray guidance requested for Leaf Webber. Returning None (pesticide recommendations disabled for safety).")
        return None

    query = select(TurDiseaseRecommendation).where(
        TurDiseaseRecommendation.crop == "tur",
        func.lower(TurDiseaseRecommendation.disease_name) == clean_disease_name.lower(),
        TurDiseaseRecommendation.is_active == True,
    )
    rec = db.scalar(query)

    if not rec:
        logger.info("[RECOMMENDATION SERVICE] No active verified recommendation found for crop=tur, disease=%s", clean_disease_name)
        return None

    default_spray_guidance = [
        "01 Prepare the sprayer",
        "02 Follow the recommended treatment",
        "03 Spray the affected Tur plants evenly",
        "04 Avoid unnecessary overspray",
        "05 Keep people and animals away from the spray area",
    ]
    default_after_spraying = [
        "Clean the sprayer properly",
        "Wash hands and exposed areas",
        "Observe the crop regularly",
        "Do not repeat spraying unnecessarily",
    ]
    default_safety_precautions = [
        "Wear gloves and protective clothing",
        "Avoid direct contact with the spray",
        "Keep children and animals away",
        "Follow product-label instructions",
    ]

    spray_guidance_list = _parse_text_to_list(rec.application_method, default_spray_guidance)
    after_spraying_list = _parse_text_to_list(rec.after_spray_advisory, default_after_spraying)
    safety_precautions_list = _parse_text_to_list(rec.safety_precautions, default_safety_precautions)

    leaf_condition = "Needs Treatment"
    if "healthy" in clean_disease_name.lower():
        leaf_condition = "Monitor"

    return SprayGuidanceResponse(
        crop="tur",
        disease_name=rec.disease_name,
        leaf_condition=leaf_condition,
        important_alert="Follow the verified treatment recommendation and product-label instructions while spraying.",
        spray_guidance=spray_guidance_list,
        after_spraying=after_spraying_list,
        safety_precautions=safety_precautions_list,
        farmer_action="Monitor your Tur crop regularly. If symptoms continue, increase, or change, scan a fresh leaf again.",
    )
