"""
Predictions API — POST /api/v1/predictions/tur-leaf/{scan_id}

Endpoint:
    POST /api/v1/predictions/tur-leaf/{scan_id}

    Uses the scan's already-stored image (no re-upload required).
    Calls the TurDiseasePredictor via PredictionService.

    When ML model is not configured:
        HTTP 503
        {"status": "model_not_configured", "message": "..."}

    When ML model is available and succeeds:
        HTTP 200
        {"scan_id": 123, "crop": "tur", "disease_name": "...", "confidence": 0.92, ...}

Security:
    - Requires Bearer JWT.
    - Ownership enforced at the service layer.
    - No internal paths in response.
"""

import logging

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.database.models.user import User
from app.database.session import get_db
from app.schemas.prediction import PredictionResponse
from app.schemas.claude_guidance import ClaudeGuidanceResponse
from app.services.prediction_service import run_prediction
from app.services.scan_service import get_scan_for_user
from app.services.claude_guidance_service import generate_claude_guidance

logger = logging.getLogger("tursathi.api.predictions")

router = APIRouter(prefix="/predictions", tags=["Predictions"])


@router.post(
    "/tur-leaf/{scan_id}",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Run Tur leaf disease prediction on a stored scan",
)
def predict_tur_leaf(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PredictionResponse:
    """
    Runs the Tur leaf disease ML prediction on the scan image that was already
    uploaded and stored during the initial scan upload (POST /api/v1/scans).

    The mobile app should NOT re-upload the image — this endpoint uses the
    server-side stored copy identified by scan_id.

    Behaviour when ML model is not yet configured:
        Returns HTTP 503 with:
        {"status": "model_not_configured", "message": "..."}
        The scan record and image are NOT deleted.

    Behaviour when ML model is available:
        Returns HTTP 200 with disease_name, confidence, severity.
        Results are persisted to TurScan.disease_name / .confidence / .severity.
    """
    logger.info(
        "[API/PREDICTIONS] Prediction requested: scan_id=%d user_id=%d",
        scan_id, current_user.id,
    )

    # run_prediction raises HTTPException for model_not_configured (503) or errors
    scan = run_prediction(db=db, scan_id=scan_id, user_id=current_user.id)

    return PredictionResponse(
        scan_id=scan.id,
        crop=scan.crop,
        status=scan.prediction_status,
        disease_name=scan.disease_name,
        confidence=scan.confidence,
        severity=scan.severity,
    )


@router.post(
    "/tur-leaf/{scan_id}/ai-guidance",
    response_model=ClaudeGuidanceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get secondary AI guidance and explanation layer powered by Claude Sonnet 4.5",
)
def get_ai_guidance_for_tur_scan(
    scan_id: int,
    language: str = Query("en", description="Target language code: en | mr | hi"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClaudeGuidanceResponse:
    """
    Retrieves secondary AI guidance for a Tur scan using Claude Sonnet 4.5.

    - Authenticates the user and validates scan ownership.
    - Uses existing ML prediction (or runs inference if pending).
    - Enforces confidence threshold (>= 60%).
    - Enforces Healthy safety (no pesticide recommendations for healthy leaves).
    - Uses verified recommendation database as the single source of truth.
    - Returns structured AI explanation or database fallback.
    """
    logger.info(
        "[API/PREDICTIONS] AI Guidance requested: scan_id=%d user_id=%d language=%s",
        scan_id, current_user.id, language,
    )

    # 1. Verify scan ownership
    scan = get_scan_for_user(db=db, scan_id=scan_id, user_id=current_user.id)

    # 2. Ensure prediction is run
    if scan.prediction_status != "completed" or not scan.disease_name:
        logger.info("[API/PREDICTIONS] Scan #%d prediction not yet completed. Running prediction now...", scan_id)
        scan = run_prediction(db=db, scan_id=scan_id, user_id=current_user.id)

    # 3. Generate Claude guidance
    return generate_claude_guidance(db=db, scan=scan, language=language)
