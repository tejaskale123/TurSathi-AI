from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class TurVoiceReport(Base):
    """
    Represents a farmer's voice description linked to a specific TurScan case.

    The audio binary is stored on the filesystem (storage service).
    Only the storage reference (audio_path) and metadata are persisted here.
    Transcription is nullable — reserved for future speech-to-text integration.
    """

    __tablename__ = "tur_voice_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Link to parent scan — one scan can have one or more voice reports
    scan_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tur_scans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Denormalized for query convenience (avoids join to tur_scans for ownership checks)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Storage reference (relative path from UPLOAD_DIR root)
    audio_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Original client-provided filename (sanitized server-side)
    audio_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # MIME type (e.g. "audio/mpeg", "audio/mp4", "audio/wav")
    audio_content_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # File size in bytes
    audio_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # BCP-47 language tag derived from farmer's active language selection
    # Supported: "en" | "mr" | "hi"
    language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Recording duration in seconds (client-reported, not authoritative)
    duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Transcription text — null until speech-to-text pipeline is implemented
    transcription: Mapped[Optional[str]] = mapped_column(String(8192), nullable=True)

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

    # ── Relationship ─────────────────────────────────────────────────────────────

    scan: Mapped["TurScan"] = relationship(  # noqa: F821
        "TurScan",
        back_populates="voice_reports",
    )

    def __repr__(self) -> str:
        return (
            f"<TurVoiceReport id={self.id} scan_id={self.scan_id} "
            f"user_id={self.user_id} language={self.language}>"
        )
