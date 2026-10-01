from app.database.base import Base
from app.database.models.user import User
from app.database.models.tur_scan import TurScan
from app.database.models.tur_voice_report import TurVoiceReport
from app.database.models.tur_disease_recommendation import TurDiseaseRecommendation

__all__ = ["Base", "User", "TurScan", "TurVoiceReport", "TurDiseaseRecommendation"]
