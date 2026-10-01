from typing import List
from pydantic import BaseModel, Field


class SprayGuidanceResponse(BaseModel):
    crop: str = Field(default="tur", description="Crop identifier, restricted to 'tur'")
    disease_name: str = Field(..., description="ML detected or queried disease name")
    leaf_condition: str = Field(..., description="Dynamic condition status (e.g. Needs Treatment, Monitor, Attention Required)")
    important_alert: str = Field(..., description="Important safety alert message")
    spray_guidance: List[str] = Field(..., description="Numbered step-by-step practical spray actions")
    after_spraying: List[str] = Field(..., description="Practical actions to take after spraying")
    safety_precautions: List[str] = Field(..., description="Safety and protective equipment guidelines")
    farmer_action: str = Field(..., description="Final next-step instruction for the farmer")

    class Config:
        from_attributes = True
