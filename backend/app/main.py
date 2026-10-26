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
# In development, permits local development loopbacks and RFC 1918 private LAN IP addresses for mobile devices.
# In production, regex is disabled (None) and strict explicit origin matching is enforced.
dev_origin_regex = (
    r"^https?://(localhost|127\.0\.0\.1|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})(:\d+)?$"
    if settings.ENVIRONMENT == "development"
    else None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.FRONTEND_CORS_ORIGINS.split(",") if origin.strip()],
    allow_origin_regex=dev_origin_regex,
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


@app.get("/test-voice", include_in_schema=False)
def test_voice_shortcut():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"{settings.API_V1_STR}/test/ui")
