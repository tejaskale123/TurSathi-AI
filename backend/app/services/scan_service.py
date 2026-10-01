"""
Scan Service — handles scan record creation, image storage, and voice report linking.

Responsibilities:
- Validate uploaded files before writing to disk.
- Persist images via storage_service (safe filenames, no path traversal).
- Create TurScan records owned by the authenticated user.
- Create TurVoiceReport records linked to the correct scan.
- Enforce user ownership on all scan queries.
"""

import logging
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.database.models.tur_scan import TurScan
from app.database.models.tur_voice_report import TurVoiceReport
from app.services.storage_service import (
    save_scan_image,
    save_voice_report,
    validate_audio_upload,
    validate_image_upload,
)

logger = logging.getLogger("tursathi.scan_service")


# ── Scan creation ─────────────────────────────────────────────────────────────

def create_scan_with_image(
    db: Session,
    user_id: int,
    file_bytes: bytes,
    content_type: Optional[str],
    original_filename: Optional[str],
    crop: str = "tur",
) -> TurScan:
    """
    Validates, stores the image, and creates a TurScan record in PostgreSQL.

    Raises HTTPException for all validation and storage errors.
    The scan record is created with status="received" and prediction_status="pending".
    """
    # 1. Validate file (raises ValueError on failure)
    try:
        validate_image_upload(file_bytes, content_type)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    # 2. Persist to filesystem (raises IOError on failure)
    try:
        storage_key, stored_filename = save_scan_image(
            file_bytes=file_bytes,
            content_type=content_type,
            original_filename=original_filename,
        )
    except Exception as exc:
        logger.error("[SCAN_SERVICE] Failed to store scan image: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Image could not be stored. Please try again.",
        )

    # 3. Create database record
    scan = TurScan(
        user_id=user_id,
        crop=crop,
        image_path=storage_key,
        image_filename=original_filename,
        image_content_type=content_type,
        image_size=len(file_bytes),
        status="received",
        prediction_status="pending",
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    logger.info(
        "[SCAN_SERVICE] TurScan #%d created for user_id=%d crop=%s size=%d",
        scan.id, user_id, crop, len(file_bytes),
    )
    return scan


# ── Scan retrieval ────────────────────────────────────────────────────────────

def get_scan_for_user(
    db: Session,
    scan_id: int,
    user_id: int,
) -> TurScan:
    """
    Retrieves a TurScan record, enforcing ownership.
    Raises HTTP 404 if scan is not found.
    Raises HTTP 403 if the scan belongs to a different user.
    """
    scan = db.query(TurScan).filter(TurScan.id == scan_id).first()
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan #{scan_id} not found.",
        )
    if scan.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. This scan belongs to another user.",
        )
    return scan


# ── Voice report creation ─────────────────────────────────────────────────────

def create_voice_report(
    db: Session,
    scan_id: int,
    user_id: int,
    file_bytes: bytes,
    content_type: Optional[str],
    original_filename: Optional[str],
    language: Optional[str] = None,
    duration: Optional[float] = None,
) -> TurVoiceReport:
    """
    Validates, stores the voice recording, and creates a TurVoiceReport record.

    Verifies scan ownership before linking the voice report.
    Raises HTTPException for validation and storage errors.
    """
    # 1. Verify scan exists and belongs to this user
    scan = get_scan_for_user(db=db, scan_id=scan_id, user_id=user_id)

    # 2. Validate audio file
    try:
        validate_audio_upload(file_bytes, content_type)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    # 3. Persist to filesystem
    try:
        storage_key, stored_filename = save_voice_report(
            file_bytes=file_bytes,
            content_type=content_type,
            original_filename=original_filename,
        )
    except Exception as exc:
        logger.error("[SCAN_SERVICE] Failed to store voice report: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Voice recording could not be stored. Please try again.",
        )

    # 4. Create database record
    voice_report = TurVoiceReport(
        scan_id=scan.id,
        user_id=user_id,
        audio_path=storage_key,
        audio_filename=original_filename,
        audio_content_type=content_type,
        audio_size=len(file_bytes),
        language=language,
        duration=duration,
        transcription=None,  # Reserved for future speech-to-text integration
    )
    db.add(voice_report)
    db.commit()
    db.refresh(voice_report)

    logger.info(
        "[SCAN_SERVICE] TurVoiceReport #%d created for scan_id=%d user_id=%d language=%s",
        voice_report.id, scan_id, user_id, language,
    )
    return voice_report
