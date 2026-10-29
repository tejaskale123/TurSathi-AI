from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Integer, String, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class LoginHistory(Base):
    """
    Records authentication events for security auditing and tracking.
    
    Security & Privacy Rules:
    - user_id is nullable (null for failed attempts where no user account is identified).
    - NEVER store passwords, password hashes, OTPs, tokens, or raw request bodies.
    - NEVER store user-submitted raw identifiers (e.g., mistyped passwords in username fields).
    - failure_reason stores only generic category codes (e.g., 'invalid_credentials', 'account_inactive').
    """

    __tablename__ = "login_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Nullable foreign key to users.id. If user is deleted, set to NULL to preserve audit trail.
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # UTC timestamp when the login event took place
    login_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Method used: 'local_password', 'google_oauth'
    login_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # Outcome: 'success' or 'failed'
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    # Safe generic failure category (null on success). Never contains credentials or user input.
    failure_reason: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    # Client IP address (IPv4 or IPv6 up to 45 chars). Nullable and sanitized.
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
    )

    # Client User-Agent string. Truncated to 255 chars, sanitized, and nullable.
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # Record creation timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationship to user
    user = relationship("User")

    __table_args__ = (
        Index("ix_login_history_status_login_at", "status", "login_at"),
    )

    def __repr__(self) -> str:
        return f"<LoginHistory id={self.id} user_id={self.user_id} method={self.login_method} status={self.status}>"
