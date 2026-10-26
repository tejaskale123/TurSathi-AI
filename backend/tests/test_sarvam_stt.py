from unittest.mock import MagicMock, patch
import httpx
import pytest

from app.core.config import settings
from app.services.sarvam_stt_service import (
    map_language_code,
    transcribe_audio_bytes,
)


def test_map_language_code():
    assert map_language_code("mr") == "mr-IN"
    assert map_language_code("MR") == "mr-IN"
    assert map_language_code("hi") == "hi-IN"
    assert map_language_code("en") == "en-IN"
    assert map_language_code(None) == "unknown"
    assert map_language_code("") == "unknown"
    assert map_language_code("te") == "unknown"


def test_transcribe_audio_bytes_missing_api_key(monkeypatch):
    monkeypatch.setattr(settings, "SARVAM_API_KEY", None)
    result = transcribe_audio_bytes(b"dummy audio bytes", language="mr")
    assert result is None


def test_transcribe_audio_bytes_empty_payload(monkeypatch):
    monkeypatch.setattr(settings, "SARVAM_API_KEY", "test_key")
    result = transcribe_audio_bytes(b"", language="mr")
    assert result is None


def test_transcribe_audio_bytes_success(monkeypatch):
    monkeypatch.setattr(settings, "SARVAM_API_KEY", "test_key")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "transcript": "पानावर पिवळे चट्टे दिसत आहेत आणि पाने गुंडाळली आहेत"
    }

    with patch("httpx.Client.post", return_value=mock_response) as mock_post:
        result = transcribe_audio_bytes(
            file_bytes=b"fake_m4a_audio_bytes",
            original_filename="audio.m4a",
            content_type="audio/mp4",
            language="mr",
        )

        assert result == "पानावर पिवळे चट्टे दिसत आहेत आणि पाने गुंडाळली आहेत"
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["headers"]["api-subscription-key"] == "test_key"
        assert call_kwargs["data"]["language_code"] == "mr-IN"
        assert call_kwargs["data"]["model"] == settings.SARVAM_STT_MODEL


def test_transcribe_audio_bytes_alt_key_name(monkeypatch):
    monkeypatch.setattr(settings, "SARVAM_API_KEY", "test_key")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "transcription": "पत्तियों पर धब्बे हैं"
    }

    with patch("httpx.Client.post", return_value=mock_response):
        result = transcribe_audio_bytes(
            file_bytes=b"fake_audio",
            language="hi",
        )
        assert result == "पत्तियों पर धब्बे हैं"


def test_transcribe_audio_bytes_api_error_status(monkeypatch):
    monkeypatch.setattr(settings, "SARVAM_API_KEY", "test_key")

    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized: Invalid Subscription Key"

    with patch("httpx.Client.post", return_value=mock_response):
        result = transcribe_audio_bytes(b"audio", language="en")
        # Must return None gracefully, not raise an exception
        assert result is None


def test_transcribe_audio_bytes_timeout(monkeypatch):
    monkeypatch.setattr(settings, "SARVAM_API_KEY", "test_key")

    with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Read timed out")):
        result = transcribe_audio_bytes(b"audio", language="mr")
        assert result is None


def test_transcribe_audio_bytes_generic_exception(monkeypatch):
    monkeypatch.setattr(settings, "SARVAM_API_KEY", "test_key")

    with patch("httpx.Client.post", side_effect=RuntimeError("Socket error")):
        result = transcribe_audio_bytes(b"audio", language="mr")
        assert result is None
