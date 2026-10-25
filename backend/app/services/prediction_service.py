"""
Prediction Service — orchestrates ML inference on stored scan images.

Architecture:
    API route → PredictionService.run_prediction(scan_id, user_id)
             → validates scan ownership
             → retrieves stored image path
             → calls TurDiseasePredictor.predict()
             → persists result back to TurScan record

When the ML model is not configured:
    - TurScan.prediction_status is set to "model_not_configured".
    - The scan record is NOT deleted — the image remains safely stored.
    - The caller (API route) raises HTTP 503.

DO NOT generate fake predictions in this service.
"""

import logging
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.database.models.tur_scan import TurScan
from app.ml.tur_predictor import ModelNotConfiguredError, get_predictor
from app.ml.tur_image_gate import get_tur_image_gate
from app.services.scan_service import get_scan_for_user
from app.services.storage_service import UPLOAD_DIR

logger = logging.getLogger("tursathi.prediction_service")


def run_prediction(
    db: Session,
    scan_id: int,
    user_id: int,
) -> TurScan:
    """
    Runs ML prediction for the given scan.

    Steps:
    1. Retrieves and verifies scan ownership.
    2. Resolves the stored image path.
    3. Validates the image using TurImageGate.
    4. Calls the ML predictor.
    5. Persists result to TurScan record.
    6. Returns updated TurScan.

    Raises:
        HTTP 404 — scan not found.
        HTTP 403 — scan belongs to another user.
        HTTP 422 — validation failed (not a Tur image).
        HTTP 503 — ML model not yet configured (model_not_configured).
        HTTP 500 — unexpected prediction failure.
    """
    # 1. Get scan (enforces ownership)
    scan = get_scan_for_user(db=db, scan_id=scan_id, user_id=user_id)

    # 2. Ensure image exists in storage
    if not scan.image_path:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Scan does not have an associated image.",
        )

    image_abs_path = (UPLOAD_DIR / scan.image_path).resolve()

    # 3. Gate Validation
    gate = get_tur_image_gate()
    gate_result = gate.validate(image_abs_path)
    
    if not gate_result.is_valid_tur:
        scan.status = "rejected"
        scan.prediction_status = "rejected"
        db.commit()
        logger.warning(
            "[PREDICTION_SERVICE] Scan #%d rejected by gate: %s (reason: %s)",
            scan_id, gate_result.label, gate_result.reason
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "status": "validation_failed",
                "reason": gate_result.reason,
                "message": gate_result.message or "This image does not appear to be a valid Tur (Pigeonpea) leaf.",
                "message_mr": getattr(gate_result, "message_mr", None) or "तूर पानाचा फोटो पुरेसा स्पष्ट नाही. कृपया चांगल्या प्रकाशात फोटो पुन्हा घ्या.",
            }
        )

    # 4. Mark as processing
    scan.status = "processing"
    scan.prediction_status = "processing"
    db.commit()
    db.refresh(scan)

    # 5. Run predictor
    predictor = get_predictor()
    try:
        result = predictor.predict(image_abs_path)

        if not result.is_supported_class or result.confidence < 0.65:
            scan.status = "rejected"
            scan.prediction_status = "rejected"
            db.commit()
            rejection_reason = result.rejection_reason or "low_confidence_unsupported"
            logger.warning(
                "[PREDICTION_SERVICE] Scan #%d rejected: reason=%s, conf=%.3f, cos_dist=%s. Class outside current database.",
                scan_id, rejection_reason, result.confidence, str(result.cosine_distance)
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "status": "unsupported_disease",
                    "reason": rejection_reason,
                    "message": "This specific class does not exist in the current database. The system strictly supports only verified pigeon pea classes: Healthy, Leaf Spot, Leaf Webber, Sterility Mosaic, and Wilt.",
                    "message_mr": "हा विशिष्ट रोग सध्याच्या डेटाबेसमध्ये उपलब्ध नाही. तूर साथी केवळ अधिकृत ५ रोगांचे (निरोगी, पानांवरील ठिपके, पाने गुंडाळणारी अळी, वांझ रोग, आणि मर रोग) अचूक निदान करते.",
                }
            )

        # 6a. Persist completed result
        scan.disease_name = result.disease_name
        scan.confidence = result.confidence
        scan.severity = result.severity
        scan.prediction_status = "completed"
        scan.status = "completed"
        db.commit()
        db.refresh(scan)

        logger.info(
            "[PREDICTION_SERVICE] Scan #%d prediction completed: disease=%s confidence=%.3f",
            scan_id, result.disease_name, result.confidence,
        )
        logger.info(
            "[PREDICTION_SERVICE_DIAGNOSTIC] scan_id=%d mapped_class=%s confidence=%.6f prediction_status=%s status=%s",
            scan.id, result.disease_name, result.confidence, scan.prediction_status, scan.status,
        )
        return scan

    except ModelNotConfiguredError:
        # 5b. Model not configured — mark the scan but preserve image and record
        scan.prediction_status = "model_not_configured"
        scan.status = "received"  # Revert to received — image is safe, scan is valid
        db.commit()
        db.refresh(scan)

        logger.warning(
            "[PREDICTION_SERVICE] Scan #%d: ML model not configured. "
            "Image and scan record are safely preserved.",
            scan_id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "model_not_configured",
                "message": "Tur disease ML model is not configured yet.",
            },
        )

    except FileNotFoundError:
        scan.prediction_status = "failed"
        scan.status = "failed"
        db.commit()
        logger.error("[PREDICTION_SERVICE] Scan #%d: image file not found on disk.", scan_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Scan image could not be found on the server.",
        )

    except HTTPException:
        # Pass through intentional HTTP exceptions (like 422 for low confidence)
        raise

    except Exception as exc:
        # Unexpected error — mark failed but preserve the record
        scan.prediction_status = "failed"
        scan.status = "failed"
        db.commit()
        logger.error(
            "[PREDICTION_SERVICE] Scan #%d: unexpected prediction error: %s",
            scan_id, exc,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during prediction.",
        )
