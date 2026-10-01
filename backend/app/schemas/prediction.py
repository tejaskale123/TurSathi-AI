from typing import Optional
from pydantic import BaseModel, ConfigDict


class PredictionResponse(BaseModel):
    """
    Response schema for the prediction endpoint.

    When the ML model is not yet configured the HTTP status is 503
    and status field is "model_not_configured".

    When the real model is available:
        status = "completed"
        disease_name, confidence, severity are populated.
    """
    scan_id: int
    crop: str
    status: str  # model_not_configured | pending | processing | completed | failed
    message: Optional[str] = None

    # Populated only when prediction_status == "completed"
    disease_name: Optional[str] = None
    confidence: Optional[float] = None
    severity: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
