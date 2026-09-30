import time
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import api_router
from app.core.config import settings

# Configure logging to output request details directly to the terminal
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tursathi.api")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

@app.middleware("http")
async def log_incoming_requests(request: Request, call_next):
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    method = request.method
    path = request.url.path
    origin = request.headers.get("origin", "no-origin")
    
    print(f"\n==================================================")
    print(f"[INCOMING API REQUEST] {method} {path}")
    print(f" -> Client IP: {client_ip}")
    print(f" -> Origin: {origin}")
    print(f"==================================================")
    
    response = await call_next(request)
    
    duration = (time.time() - start_time) * 1000
    print(f"[API RESPONSE] {method} {path} -> Status: {response.status_code} ({duration:.2f}ms)\n")
    return response

# CORS Configuration for Mobile / Web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8081",
        "http://127.0.0.1:8081",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 Router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Health"])
def root():
    return {
        "success": True,
        "name": settings.PROJECT_NAME,
        "status": "online",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "database": "connected"
    }
