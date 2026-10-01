import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.database.models.user import User
from app.database.session import get_db
from app.schemas.recommendation import SprayGuidanceResponse
from app.services.recommendation_service import get_tur_spray_guidance_service

logger = logging.getLogger("tursathi.api.recommendations")

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get(
    "/tur/{disease_name}/spray-guidance",
    response_model=SprayGuidanceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get verified smart spray guidance for detected Tur disease",
)
def get_tur_spray_guidance(
    disease_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SprayGuidanceResponse:
    """
    Fetches verified agricultural spray guidance for a specified Tur disease.

    - Restricts crop to "tur".
    - Queries verified active recommendations from tur_disease_recommendations.
    - Returns HTTP 404 when verified guidance is not available yet.
    - Never fabricates or invents unverified pesticide data.
    """
    clean_name = disease_name.strip()
    if not clean_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Disease name parameter is required.",
        )

    logger.info(
        "[API/RECOMMENDATIONS] Spray guidance requested: disease_name=%s user_id=%d",
        clean_name, current_user.id,
    )

    result = get_tur_spray_guidance_service(db=db, disease_name=clean_name)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verified spray guidance is not available for this condition yet.",
        )

    return result
