from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class SprayGuidanceDetails(BaseModel):
    """
    Verified spray guidance details passed to/from Claude.
    """
    treatment: Optional[str] = Field(None, description="Commercial product name")
    active_ingredient: Optional[str] = Field(None, description="Chemical active ingredient")
    recommended_quantity: Optional[str] = Field(None, description="Official dosage per liter or unit")
    water_quantity: Optional[str] = Field(None, description="Water volume if specified, otherwise None")
    per_pump_quantity: Optional[str] = Field(None, description="Per-pump dose if specified, otherwise None")
    spray_timing: Optional[str] = Field(None, description="When to apply spray")
    application_method: Optional[str] = Field(None, description="Method of application")
    safety_precautions: Optional[str] = Field(None, description="PPE and safety guidance")
    after_spray_advisory: Optional[str] = Field(None, description="Post-application monitoring")

    model_config = ConfigDict(from_attributes=True)


class ClaudeGuidanceResponse(BaseModel):
    """
    Structured schema for AI guidance endpoint response.
    """
    status: str = Field(..., description="Status: 'success', 'low_confidence', or 'fallback'")
    crop: str = Field(default="tur", description="Crop identifier")
    disease_name: Optional[str] = Field(None, description="Detected disease name")
    confidence: Optional[float] = Field(None, description="Model confidence (0.0 - 1.0)")
    confidence_percent: Optional[int] = Field(None, description="Model confidence percentage (0 - 100)")
    disease_explanation: Optional[str] = Field(None, description="AI explanation of condition")
    farmer_action: List[str] = Field(default_factory=list, description="Step-by-step actions for farmer")
    spray_guidance_available: bool = Field(default=False, description="Whether spray guidance is active/available")
    ai_guidance_available: bool = Field(default=True, description="Whether Claude AI generated the guidance")
    spray_guidance: Optional[SprayGuidanceDetails] = Field(None, description="Verified spray guidance object")
    warnings: List[str] = Field(default_factory=list, description="Safety warnings or low-confidence notes")
    language: str = Field(default="en", description="Language of human-readable guidance (en, mr, hi)")
    important_alert: Optional[str] = Field(None, description="Override alert message for special cases (e.g., seed treatment instead of foliar spray)")

    model_config = ConfigDict(from_attributes=True)
