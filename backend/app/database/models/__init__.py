from app.database.base import Base
from app.database.models.user import User
from app.database.models.tur_scan import TurScan
from app.database.models.tur_voice_report import TurVoiceReport
from app.database.models.tur_disease_recommendation import TurDiseaseRecommendation
from app.database.models.tur_ai_guidance import TurAIGuidance

__all__ = ["Base", "User", "TurScan", "TurVoiceReport", "TurDiseaseRecommendation", "TurAIGuidance"]
