from fastapi import APIRouter, Security
from app.api.v1.auth import router as auth_router
from app.api.v1.scans import router as scans_router
from app.api.v1.predictions import router as predictions_router
from app.api.v1.recommendations import router as recommendations_router
from app.api.v1.test_voice import router as test_voice_router
from app.core.security import verify_api_key

api_router = APIRouter(dependencies=[Security(verify_api_key)])
api_router.include_router(auth_router)
api_router.include_router(scans_router)
api_router.include_router(predictions_router)
api_router.include_router(recommendations_router)
api_router.include_router(test_voice_router)
