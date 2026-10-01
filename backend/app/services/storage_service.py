"""
Storage Service — safe local filesystem storage for uploaded images and audio.

Key security properties:
- Server-side UUID-based filenames prevent path traversal.
- Client-provided filenames are never used directly on disk.
- Only the relative storage key is persisted in the database.
- Absolute paths are never exposed to the mobile client.
"""

import logging
import os
import uuid
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger("tursathi.storage")

# ── Storage root configuration ──────────────────────────────────────────────
# Relative to the backend project root; resolved at import time.
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = _BACKEND_ROOT / "uploads"

# Sub-directories per asset type
SCAN_IMAGES_DIR = UPLOAD_DIR / "scans"
VOICE_REPORTS_DIR = UPLOAD_DIR / "voice_reports"

# ── Allowed MIME types ───────────────────────────────────────────────────────
ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}

ALLOWED_AUDIO_TYPES = {
    "audio/mpeg",
    "audio/mp4",
    "audio/mp4a-latm",
    "audio/x-m4a",
    "audio/wav",
    "audio/x-wav",
    "audio/webm",
    "audio/ogg",
    "audio/aac",
    "audio/3gpp",
    "audio/3gpp2",
}

# Maximum upload sizes
MAX_IMAGE_SIZE_BYTES = 20 * 1024 * 1024   # 20 MB
MAX_AUDIO_SIZE_BYTES = 50 * 1024 * 1024   # 50 MB

# Extension fallback map (content_type → extension)
_MIME_TO_EXT: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "image/heif": ".heif",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "audio/mp4a-latm": ".m4a",
    "audio/x-m4a": ".m4a",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/aac": ".aac",
    "audio/3gpp": ".3gp",
    "audio/3gpp2": ".3g2",
}


def _ensure_dir(path: Path) -> None:
    """Creates directory and all parents if they do not already exist."""
    path.mkdir(parents=True, exist_ok=True)


def _safe_extension(content_type: Optional[str], fallback: str = ".bin") -> str:
    """Returns a file extension for a given MIME type."""
    if not content_type:
        return fallback
    ct = content_type.strip().lower()
    # Strip parameters (e.g. "image/jpeg; charset=utf-8" → "image/jpeg")
    base_ct = ct.split(";")[0].strip()
    return _MIME_TO_EXT.get(base_ct, fallback)


def save_scan_image(
    file_bytes: bytes,
    content_type: Optional[str],
    original_filename: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Persists an uploaded scan image to the secure uploads directory.

    Parameters
    ----------
    file_bytes      : Raw bytes of the uploaded image.
    content_type    : MIME type reported by the client (validated before calling).
    original_filename : Original filename from the upload (sanitized; not used for disk path).

    Returns
    -------
    (storage_key, filename_on_disk)
        storage_key    — Relative path from UPLOAD_DIR root (stored in DB).
        filename_on_disk — UUID-based filename (not exposed to client).
    """
    _ensure_dir(SCAN_IMAGES_DIR)

    ext = _safe_extension(content_type, fallback=".jpg")
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = SCAN_IMAGES_DIR / filename

    file_path.write_bytes(file_bytes)
    logger.info("[STORAGE] Scan image saved: %s (%d bytes)", filename, len(file_bytes))

    # storage_key is relative so it is portable and safe to store in the DB
    storage_key = f"scans/{filename}"
    return storage_key, filename


def save_voice_report(
    file_bytes: bytes,
    content_type: Optional[str],
    original_filename: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Persists an uploaded voice recording to the secure uploads directory.

    Returns
    -------
    (storage_key, filename_on_disk)
    """
    _ensure_dir(VOICE_REPORTS_DIR)

    ext = _safe_extension(content_type, fallback=".m4a")
    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = VOICE_REPORTS_DIR / filename

    file_path.write_bytes(file_bytes)
    logger.info("[STORAGE] Voice report saved: %s (%d bytes)", filename, len(file_bytes))

    storage_key = f"voice_reports/{filename}"
    return storage_key, filename


def get_absolute_image_path(storage_key: str) -> Path:
    """
    Resolves a storage_key back to an absolute Path on the server filesystem.
    Used internally by the ML prediction service — never exposed to clients.
    """
    path = (UPLOAD_DIR / storage_key).resolve()
    # Guard against path traversal
    if not str(path).startswith(str(UPLOAD_DIR.resolve())):
        raise ValueError("Path traversal detected in storage_key.")
    return path


def validate_image_upload(
    file_bytes: bytes,
    content_type: Optional[str],
) -> None:
    """
    Raises ValueError with a human-readable message if the image upload is invalid.
    Call before persisting.
    """
    if not file_bytes:
        raise ValueError("Uploaded image is empty.")

    ct = (content_type or "").strip().lower().split(";")[0].strip()
    if ct not in ALLOWED_IMAGE_TYPES:
        raise ValueError(
            f"Unsupported image type '{content_type}'. "
            f"Allowed types: JPEG, PNG, WebP, HEIC."
        )

    if len(file_bytes) > MAX_IMAGE_SIZE_BYTES:
        mb = len(file_bytes) / (1024 * 1024)
        raise ValueError(
            f"Image size {mb:.1f} MB exceeds the maximum allowed 20 MB."
        )


def validate_audio_upload(
    file_bytes: bytes,
    content_type: Optional[str],
) -> None:
    """
    Raises ValueError if the audio upload is invalid.
    """
    if not file_bytes:
        raise ValueError("Uploaded audio is empty.")

    ct = (content_type or "").strip().lower().split(";")[0].strip()
    if ct not in ALLOWED_AUDIO_TYPES:
        raise ValueError(
            f"Unsupported audio type '{content_type}'. "
            f"Allowed: MP3, M4A, WAV, WebM, OGG, AAC."
        )

    if len(file_bytes) > MAX_AUDIO_SIZE_BYTES:
        mb = len(file_bytes) / (1024 * 1024)
        raise ValueError(
            f"Audio size {mb:.1f} MB exceeds the maximum allowed 50 MB."
        )
