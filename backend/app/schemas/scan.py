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


class ScanListResponse(BaseModel):
    """
    Paginated list of scan records for the authenticated user.
    """
    total: int = Field(description="Total count of scans owned by this user")
    page: int = Field(description="Current 1-based page number")
    limit: int = Field(description="Page size limit")
    total_pages: int = Field(description="Total number of pages")
    items: list[ScanDetailResponse] = Field(default_factory=list, description="List of scan records")

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
    transcription: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ── Frame validation (stateless camera probe) ──────────────────────────────────

class FrameValidationResponse(BaseModel):
    """
    Returned by POST /api/v1/scans/validate-frame for in-memory camera snapshot evaluation.
    No database records or stored files are created.
    """
    is_valid_tur: bool = Field(description="True if the snapshot meets resolution, clarity, and Tur confidence")
    label: str = Field(description="'Tur' or rejection category")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    reason: str = Field(description="Machine-readable outcome or rejection reason")
    message: Optional[str] = Field(default=None, description="Localized/user-facing explanation message")
    message_mr: Optional[str] = Field(default=None, description="Clear Marathi user-facing explanation message")

