from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.scans import router as scans_router
from app.api.v1.predictions import router as predictions_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(scans_router)
api_router.include_router(predictions_router)
