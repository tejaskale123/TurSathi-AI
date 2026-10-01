from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base


class TurDiseaseRecommendation(Base):
    """
    Represents verified agricultural recommendations for detected Tur crop diseases.

    Used by the Treatment Recommendation and Smart Spray Guidance pages
    to map ML-detected disease names to verified treatment guidance.
    """

    __tablename__ = "tur_disease_recommendations"

    __table_args__ = (
        UniqueConstraint(
            "crop",
            "disease_name",
            name="uq_tur_disease_recommendations_crop_disease",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Crop identifier (default "tur")
    crop: Mapped[str] = mapped_column(String(50), nullable=False, default="tur", index=True)

    # ML disease class/name (e.g. "Phytophthora Blight", "Tur Leaf Spot")
    disease_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Short farmer-friendly explanation of the disease
    disease_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Verified treatment recommendation text
    treatment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Active ingredient / chemical or organic formulation details
    active_ingredient: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Recommended quantity (e.g., "500 ml/acre")
    recommended_quantity: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Water quantity (e.g., "200 L/acre")
    water_quantity: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Per pump quantity (e.g., "30 ml per 15L pump")
    per_pump_quantity: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Recommended spray timing (e.g., "Early morning 7-10 AM")
    spray_timing: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Application instructions and nozzle guidance
    application_method: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Safety precautions and protective gear guidance
    safety_precautions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Post-spray monitoring and follow-up advisory
    after_spray_advisory: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status flag allowing recommendations to be toggled without deleting history
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    # Timestamps
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

    def __repr__(self) -> str:
        return (
            f"<TurDiseaseRecommendation id={self.id} crop={self.crop} "
            f"disease_name={self.disease_name} is_active={self.is_active}>"
        )
