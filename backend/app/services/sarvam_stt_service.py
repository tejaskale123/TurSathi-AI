import logging
from typing import Optional
import httpx

from app.core.config import settings

logger = logging.getLogger("tursathi.services.sarvam_stt")

# Map app language codes (en, mr, hi) to Sarvam BCP-47 codes
SARVAM_LANGUAGE_MAP = {
    "mr": "mr-IN",
    "hi": "hi-IN",
    "en": "en-IN",
}


def map_language_code(language: Optional[str]) -> str:
    """
    Translates application language codes to Sarvam AI supported BCP-47 codes.
    Defaults to 'unknown' to allow Sarvam's automatic language identification.
    """
    if not language:
        return "unknown"
    cleaned = language.strip().lower()
    return SARVAM_LANGUAGE_MAP.get(cleaned, "unknown")


def transcribe_audio_bytes(
    file_bytes: bytes,
    original_filename: str = "recording.m4a",
    content_type: str = "audio/mp4",
    language: Optional[str] = None,
    timeout_seconds: float = 12.0,
) -> Optional[str]:
    """
    Transcribes audio bytes using Sarvam AI Speech-to-Text API.
    
    Safe & resilient:
    - If SARVAM_API_KEY is not configured or blank, returns None gracefully.
    - If network call times out or fails with an API error, logs and returns None.
    - NEVER raises unhandled exceptions to caller so audio upload never fails.
    """
    api_key = settings.SARVAM_API_KEY
    if not api_key or not api_key.strip():
        logger.info("[SARVAM_STT] SARVAM_API_KEY is not configured. Skipping transcription.")
        return None

    if not file_bytes:
        logger.warning("[SARVAM_STT] Audio file bytes are empty. Skipping transcription.")
        return None

    lang_code = map_language_code(language)
    endpoint = f"{settings.SARVAM_API_BASE_URL.rstrip('/')}/speech-to-text"
    headers = {
        "api-subscription-key": api_key.strip(),
    }
    data = {
        "model": settings.SARVAM_STT_MODEL,
        "mode": "transcribe",
        "language_code": lang_code,
    }
    files = {
        "file": (original_filename, file_bytes, content_type or "audio/mp4"),
    }

    try:
        logger.info(
            "[SARVAM_STT] Sending STT request to Sarvam: model=%s lang=%s size=%d bytes",
            settings.SARVAM_STT_MODEL, lang_code, len(file_bytes),
        )
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.post(
                endpoint,
                headers=headers,
                data=data,
                files=files,
            )

        if response.status_code == 200:
            result = response.json()
            transcript = (
                result.get("transcript")
                or result.get("transcription")
                or result.get("text")
                or ""
            ).strip()
            if transcript:
                logger.info("[SARVAM_STT] Transcription succeeded (%d chars): %s", len(transcript), transcript[:60])
                return transcript
            logger.info("[SARVAM_STT] Transcription response contained empty text.")
            return None
        else:
            logger.warning(
                "[SARVAM_STT] Sarvam API returned HTTP %d: %s",
                response.status_code,
                response.text[:200],
            )
            return None

    except httpx.TimeoutException:
        logger.warning("[SARVAM_STT] Sarvam STT request timed out after %.1fs", timeout_seconds)
        return None
    except Exception as exc:
        logger.error("[SARVAM_STT] Unexpected error during Sarvam STT call: %s", exc)
        return None
