from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class TurAIGuidance(Base):
    """
    Persisted Claude AI guidance for a TurScan case, separated by language.
    Acts as a durable cache to prevent redundant Claude API calls across app sessions.
    Invalidated whenever model prediction, confidence, or verified recommendation changes.
    """

    __tablename__ = "tur_ai_guidance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    scan_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tur_scans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    language: Mapped[str] = mapped_column(String(10), nullable=False)

    disease_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="success")

    disease_explanation: Mapped[str] = mapped_column(Text, nullable=False)

    # Stored as JSON array of action strings
    farmer_actions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # Stored as JSON array of warning strings
    warnings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    spray_guidance_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    ai_guidance_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    important_alert: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    # SHA-256 fingerprint of inputs (scan_id, lang, disease, conf, rec_id, rec fields, transcript)
    cache_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

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

    # Relationships
    scan: Mapped["TurScan"] = relationship("TurScan", back_populates="ai_guidance_records")

    __table_args__ = (
        UniqueConstraint("scan_id", "language", name="uq_tur_ai_guidance_scan_language"),
    )

    def __repr__(self) -> str:
        return f"<TurAIGuidance id={self.id} scan_id={self.scan_id} lang={self.language} status={self.status}>"
