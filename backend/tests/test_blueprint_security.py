"""
Unit and Integration Tests for Universal Blueprint Security Checklist.

Validates:
1. Binary Magic-Byte Signature Validation (JPEG, PNG, WebP vs fake/disguised payloads).
2. Decompression Bomb Protection (Image.MAX_IMAGE_PIXELS = 25 MP).
3. Image Sanitization & Total Metadata Erasure (Conversion to raw NumPy RGB [H, W, 3]).
4. Constant-Time API Key Verification (secrets.compare_digest raw port defense).
5. Production Exception Masking (prevents VPS traceback/path leakage).
"""

import io
import pytest
import numpy as np
from PIL import Image
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.security import verify_api_key
from app.utils.image import (
    validate_magic_bytes,
    load_and_sanitize_image,
    MAX_PIXELS,
)
from app.services.storage_service import validate_image_upload


# Helper to build a valid minimal test JPEG
def make_test_jpeg(width: int = 20, height: int = 20) -> bytes:
    img = Image.new("RGB", (width, height), color=(34, 139, 34))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


# Helper to build a valid minimal test PNG
def make_test_png(width: int = 20, height: int = 20) -> bytes:
    img = Image.new("RGB", (width, height), color=(10, 20, 30))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# Helper to build a valid minimal test WebP
def make_test_webp(width: int = 20, height: int = 20) -> bytes:
    img = Image.new("RGB", (width, height), color=(50, 100, 150))
    buf = io.BytesIO()
    img.save(buf, format="WEBP")
    return buf.getvalue()


# ── 1. Magic-Byte Binary Signature Tests ─────────────────────────────────────

def test_validate_magic_bytes_valid_signatures():
    jpeg_bytes = make_test_jpeg()
    assert validate_magic_bytes(jpeg_bytes[:16]) == "JPEG"

    png_bytes = make_test_png()
    assert validate_magic_bytes(png_bytes[:16]) == "PNG"

    webp_bytes = make_test_webp()
    assert validate_magic_bytes(webp_bytes[:16]) == "WEBP"


def test_validate_magic_bytes_rejects_disguised_text_payload():
    fake_payload = b"malicious data disguised as image"
    with pytest.raises(ValueError) as exc:
        validate_magic_bytes(fake_payload[:16])
    assert "signatures" in str(exc.value).lower()


def test_validate_magic_bytes_rejects_undersized_header():
    with pytest.raises(ValueError) as exc:
        validate_magic_bytes(b"\xff\xd8")
    assert "too small" in str(exc.value).lower()


# ── 2. Decompression Bomb & Sanitization Tests ───────────────────────────────

def test_max_image_pixels_capped_at_25_mp():
    assert Image.MAX_IMAGE_PIXELS == 25_000_000
    assert MAX_PIXELS == 25_000_000


def test_load_and_sanitize_image_produces_raw_numpy_rgb():
    jpeg_bytes = make_test_jpeg(width=40, height=30)
    img_rgb, w, h = load_and_sanitize_image(jpeg_bytes)

    assert isinstance(img_rgb, np.ndarray)
    assert img_rgb.dtype == np.uint8
    assert img_rgb.shape == (30, 40, 3)
    assert w == 40
    assert h == 30


def test_load_and_sanitize_image_rejects_fake_image():
    with pytest.raises(ValueError) as exc:
        load_and_sanitize_image(b"not an image file")
    assert "signatures" in str(exc.value).lower() or "too small" in str(exc.value).lower()


# ── 3. Storage Service validate_image_upload Integration ─────────────────────

def test_blueprint_security_rejects_fake_image_magic_bytes():
    """Blueprint Test 4: Fake image payload must fail magic byte inspection before inference."""
    fake_data = b"malicious script contents pretending to be a jpeg"
    with pytest.raises(ValueError) as exc:
        validate_magic_bytes(fake_data[:16])
    assert "signatures" in str(exc.value).lower()


def test_storage_validate_image_upload_accepts_valid_image():
    valid_bytes = make_test_jpeg(25, 25)
    # Should complete with zero errors
    validate_image_upload(file_bytes=valid_bytes, content_type="image/jpeg")


# ── 4. Constant-Time API Key Authentication Tests ────────────────────────────

def test_verify_api_key_allows_access_when_no_key_configured(monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", None)
    assert verify_api_key(api_key=None) is True
    assert verify_api_key(api_key="any_key") is True


def test_verify_api_key_rejects_missing_key_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "prod_secret_vault_key_123")
    with pytest.raises(HTTPException) as exc:
        verify_api_key(api_key=None)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "X-API-Key" in exc.value.detail


def test_verify_api_key_rejects_invalid_key_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "prod_secret_vault_key_123")
    with pytest.raises(HTTPException) as exc:
        verify_api_key(api_key="wrong_hacker_key")
    assert exc.value.status_code == status.HTTP_403_FORBIDDEN
    assert "Invalid API key" in exc.value.detail


def test_verify_api_key_accepts_correct_key_in_constant_time(monkeypatch):
    secret = "prod_secret_vault_key_123"
    monkeypatch.setattr(settings, "API_KEY", secret)
    assert verify_api_key(api_key=secret) is True


# ── 5. Production Exception Masking Tests ────────────────────────────────────

@pytest.mark.asyncio
async def test_generic_exception_handler_masks_internal_error_in_production(monkeypatch):
    from app.main import generic_exception_handler

    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "DEBUG", False)

    mock_request = None
    sensitive_internal_error = Exception("Connection to postgresql://admin:secret@10.0.0.5:5432 failed on /var/www/internal.py:84")

    response = await generic_exception_handler(mock_request, sensitive_internal_error)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 500
    
    # Verify no internal passwords, file paths, or IP addresses leaked in response
    response_body = response.body.decode("utf-8")
    assert "internal server error occurred" in response_body.lower()
    assert "secret" not in response_body
    assert "postgresql" not in response_body
    assert "/var/www" not in response_body


@pytest.mark.asyncio
async def test_generic_exception_handler_passes_through_http_exceptions():
    from app.main import generic_exception_handler

    mock_request = None
    client_error = HTTPException(status_code=403, detail="Custom Forbidden Detail")

    response = await generic_exception_handler(mock_request, client_error)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 403
    assert "Custom Forbidden Detail" in response.body.decode("utf-8")
