from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class TurScan(Base):
    """
    Represents a single Tur leaf scan/case submitted by a farmer.

    Lifecycle:
        received     → Image uploaded, scan record created.
        processing   → Prediction service is actively running inference.
        completed    → Prediction result saved.
        failed       → Prediction failed after all retries.

    The actual image binary is stored on the filesystem (storage service).
    Only the storage reference (image_path) is persisted in the database.
    """

    __tablename__ = "tur_scans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Ownership — every scan belongs to a registered authenticated farmer
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Crop identifier (always "tur" for this model, reserved for future crops)
    crop: Mapped[str] = mapped_column(String(50), nullable=False, default="tur")

    # Image storage reference (relative path from UPLOAD_DIR root, never absolute)
    image_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Original client-provided filename (sanitized server-side before storage)
    image_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # MIME type as reported during upload (validated server-side)
    image_content_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # File size in bytes
    image_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Overall scan pipeline status
    # Allowed values: received | processing | completed | failed
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="received", index=True
    )

    # ── ML Prediction results (populated when model is available) ──────────────

    # Human-readable disease name (e.g. "Phytophthora Blight")
    disease_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Model confidence score 0.0 – 1.0
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Severity level string (e.g. "mild", "moderate", "severe")
    severity: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # ML prediction pipeline status
    # Allowed values: pending | processing | completed | failed | model_not_configured
    prediction_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending"
    )

    # ── Timestamps ──────────────────────────────────────────────────────────────

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ── Relationships ────────────────────────────────────────────────────────────

    # Back-reference to voice reports linked to this scan
    voice_reports: Mapped[list["TurVoiceReport"]] = relationship(  # noqa: F821
        "TurVoiceReport",
        back_populates="scan",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<TurScan id={self.id} user_id={self.user_id} "
            f"crop={self.crop} status={self.status} "
            f"prediction_status={self.prediction_status}>"
        )
