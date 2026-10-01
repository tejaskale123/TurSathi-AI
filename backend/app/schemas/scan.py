from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


# ── Request ────────────────────────────────────────────────────────────────────

class ScanCreateRequest(BaseModel):
    """
    Internal schema used by the scan service after multipart upload is parsed.
    The crop field defaults to "tur".
    """
    crop: str = Field(default="tur", description="Crop type (always 'tur' currently)")


# ── Responses ─────────────────────────────────────────────────────────────────

class ScanCreateResponse(BaseModel):
    """
    Returned immediately after image upload and scan record creation.
    The mobile app stores scan_id and passes it to subsequent screens.
    """
    scan_id: int
    crop: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class ScanDetailResponse(BaseModel):
    """
    Full scan detail including prediction fields (nullable until model runs).
    """
    scan_id: int
    user_id: int
    crop: str
    status: str
    image_filename: Optional[str] = None
    image_content_type: Optional[str] = None
    image_size: Optional[int] = None
    disease_name: Optional[str] = None
    confidence: Optional[float] = None
    severity: Optional[str] = None
    prediction_status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Voice report ───────────────────────────────────────────────────────────────

class VoiceReportCreateResponse(BaseModel):
    """
    Returned after farmer voice recording is received and linked to a scan.
    """
    voice_report_id: int
    scan_id: int
    language: Optional[str] = None
    status: str = "received"

    model_config = ConfigDict(from_attributes=True)
