"""
Scans API — POST /api/v1/scans and POST /api/v1/scans/{scan_id}/voice

Endpoints:
    POST /api/v1/scans
        Receives multipart/form-data with:
            - image  (file upload)
            - crop   (form field, default "tur")
        Returns ScanCreateResponse with scan_id.

    GET /api/v1/scans/{scan_id}
        Returns full scan detail for the authenticated user.

    POST /api/v1/scans/{scan_id}/voice
        Receives multipart/form-data with:
            - audio    (file upload)
            - language (form field, optional BCP-47 code)
            - duration (form field, optional float seconds)
        Returns VoiceReportCreateResponse.

Security:
    - Requires Bearer JWT on every endpoint.
    - Ownership enforced at the service layer.
    - Image and audio validated before write.
    - Server-side UUID filenames prevent path traversal.
    - No internal paths exposed in responses.

Rate-limiting is expected to be handled at the infra level (nginx / API gateway).
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_user
from app.database.models.user import User
from app.database.session import get_db
from app.schemas.scan import ScanCreateResponse, ScanDetailResponse, VoiceReportCreateResponse
from app.services.scan_service import create_scan_with_image, create_voice_report, get_scan_for_user

logger = logging.getLogger("tursathi.api.scans")

router = APIRouter(prefix="/scans", tags=["Scans"])

# ── Maximum read size guard (secondary, before storage_service validates) ──────
_MAX_IMAGE_READ_BYTES = 20 * 1024 * 1024 + 1  # 20 MB + 1 byte
_MAX_AUDIO_READ_BYTES = 50 * 1024 * 1024 + 1  # 50 MB + 1 byte


@router.post(
    "",
    response_model=ScanCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Tur leaf image and create a scan record",
)
async def upload_scan(
    image: UploadFile = File(..., description="Tur leaf image (JPEG, PNG, WebP, HEIC)"),
    crop: str = Form(default="tur", description="Crop type (always 'tur' currently)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScanCreateResponse:
    """
    Accepts a Tur leaf image upload from the mobile app.

    - Validates file type and size.
    - Stores image on server filesystem with a safe UUID filename.
    - Creates a TurScan record in PostgreSQL linked to the authenticated user.
    - Returns scan_id immediately for the mobile app to carry forward.

    The mobile app must pass scan_id to all subsequent screens so that
    voice recordings and future ML results are linked to the correct scan.
    """
    if not image.filename and not image.size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image file was provided.",
        )

    # Read file bytes with size guard
    try:
        file_bytes = await image.read(_MAX_IMAGE_READ_BYTES)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read the uploaded image. Please try again.",
        )

    content_type = image.content_type or "application/octet-stream"
    original_filename = image.filename or "tur_leaf.jpg"

    logger.info(
        "[API/SCANS] Upload received: user_id=%d filename=%s content_type=%s size=%d crop=%s",
        current_user.id, original_filename, content_type, len(file_bytes), crop,
    )

    scan = create_scan_with_image(
        db=db,
        user_id=current_user.id,
        file_bytes=file_bytes,
        content_type=content_type,
        original_filename=original_filename,
        crop=crop,
    )

    return ScanCreateResponse(
        scan_id=scan.id,
        crop=scan.crop,
        status=scan.status,
    )


@router.get(
    "/{scan_id}",
    response_model=ScanDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get full scan detail for the authenticated user",
)
def get_scan(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScanDetailResponse:
    """
    Returns the full TurScan record for the given scan_id.
    Enforces ownership — only the owner can retrieve their scan.
    """
    scan = get_scan_for_user(db=db, scan_id=scan_id, user_id=current_user.id)

    return ScanDetailResponse(
        scan_id=scan.id,
        user_id=scan.user_id,
        crop=scan.crop,
        status=scan.status,
        image_filename=scan.image_filename,
        image_content_type=scan.image_content_type,
        image_size=scan.image_size,
        disease_name=scan.disease_name,
        confidence=scan.confidence,
        severity=scan.severity,
        prediction_status=scan.prediction_status,
        created_at=scan.created_at,
        updated_at=scan.updated_at,
    )


@router.post(
    "/{scan_id}/voice",
    response_model=VoiceReportCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload farmer voice recording linked to a scan",
)
async def upload_voice_report(
    scan_id: int,
    audio: UploadFile = File(..., description="Farmer voice recording (MP3, M4A, WAV, etc.)"),
    language: Optional[str] = Form(default=None, description="BCP-47 language code: en | mr | hi"),
    duration: Optional[float] = Form(default=None, description="Recording duration in seconds"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VoiceReportCreateResponse:
    """
    Receives and stores a farmer's voice recording linked to the given scan.

    - Verifies scan ownership before accepting the upload.
    - Validates audio file type and size.
    - Stores audio on server filesystem with a safe UUID filename.
    - Creates a TurVoiceReport record linked to the scan and user.
    - transcription is null — reserved for future speech-to-text integration.
    """
    if not audio.filename and not audio.size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No audio file was provided.",
        )

    try:
        file_bytes = await audio.read(_MAX_AUDIO_READ_BYTES)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read the uploaded audio. Please try again.",
        )

    content_type = audio.content_type or "audio/mp4"
    original_filename = audio.filename or "voice_report.m4a"

    # Normalize language code
    norm_language: Optional[str] = None
    if language:
        lang = language.strip().lower()
        if lang in ("en", "mr", "hi"):
            norm_language = lang

    logger.info(
        "[API/SCANS] Voice upload received: scan_id=%d user_id=%d language=%s size=%d",
        scan_id, current_user.id, norm_language, len(file_bytes),
    )

    voice_report = create_voice_report(
        db=db,
        scan_id=scan_id,
        user_id=current_user.id,
        file_bytes=file_bytes,
        content_type=content_type,
        original_filename=original_filename,
        language=norm_language,
        duration=duration,
    )

    return VoiceReportCreateResponse(
        voice_report_id=voice_report.id,
        scan_id=voice_report.scan_id,
        language=voice_report.language,
        status="received",
    )
