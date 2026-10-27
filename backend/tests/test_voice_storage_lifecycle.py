import io
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database.base import Base
from app.database.session import get_db
from app.database.models.user import User
from app.database.models.tur_scan import TurScan
from app.database.models.tur_voice_report import TurVoiceReport
from app.services.scan_service import create_voice_report
import app.services.storage_service as storage_module
from fastapi import HTTPException


# ── Isolated Test Environment Fixture ────────────────────────────────────────

@pytest.fixture(scope="function")
def isolated_db(monkeypatch):
    """
    Sets up an in-memory SQLite database and isolated temporary storage directory.
    Guarantees zero writes or file leaks into backend/uploads/.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        monkeypatch.setattr(storage_module, "UPLOAD_DIR", temp_path)
        monkeypatch.setattr(storage_module, "SCAN_IMAGES_DIR", temp_path / "scans")
        monkeypatch.setattr(storage_module, "VOICE_REPORTS_DIR", temp_path / "voice_reports")

        session = TestingSessionLocal()
        try:
            # Seed test user and scan
            user = User(
                id=1,
                full_name="Farmer Ramesh",
                mobile_number="9876543210",
                password_hash="hashed_pw",
                is_active=True,
            )
            session.add(user)
            session.commit()

            scan = TurScan(
                id=10,
                user_id=1,
                crop="tur",
                image_path="scans/dummy_leaf.jpg",
                status="received",
                prediction_status="pending",
            )
            session.add(scan)
            session.commit()

            yield session, temp_path
        finally:
            session.close()

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# ── Tests ────────────────────────────────────────────────────────────────────

def test_voice_report_transcription_success_writes_zero_disk_files(isolated_db):
    """
    Verify that upon successful Sarvam transcription:
    1. The transcript text is saved to TurVoiceReport.transcription.
    2. audio_path is strictly None (Zero-Retention).
    3. Metadata (audio_filename, audio_size, audio_content_type) is preserved.
    4. ZERO audio files are created on disk in voice_reports/.
    """
    session, temp_upload_dir = isolated_db
    sample_audio_bytes = b"\x00\x00\x00\x1cftypM4A \x00\x00\x00\x00isomiso2" + b"dummy_audio_bytes"

    with patch("app.services.scan_service.transcribe_audio_bytes") as mock_stt:
        mock_stt.return_value = "पानांवर पिवळे डाग पडले आहेत आणि झाड वाळत आहे"

        report = create_voice_report(
            db=session,
            scan_id=10,
            user_id=1,
            file_bytes=sample_audio_bytes,
            content_type="audio/mp4",
            original_filename="farmer_voice.m4a",
            language="mr",
            duration=3.5,
        )

        # 1. Transcribe service was called with in-memory bytes
        mock_stt.assert_called_once_with(
            file_bytes=sample_audio_bytes,
            original_filename="farmer_voice.m4a",
            content_type="audio/mp4",
            language="mr",
        )

        # 2. Database model attributes
        assert report.id is not None
        assert report.scan_id == 10
        assert report.user_id == 1
        assert report.transcription == "पानांवर पिवळे डाग पडले आहेत आणि झाड वाळत आहे"
        assert report.audio_path is None  # Zero-Retention verified
        assert report.audio_filename == "farmer_voice.m4a"
        assert report.audio_size == len(sample_audio_bytes)
        assert report.audio_content_type == "audio/mp4"
        assert report.language == "mr"
        assert report.duration == 3.5

        # 3. Check disk: voice_reports directory must either not exist or have 0 files
        voice_dir = temp_upload_dir / "voice_reports"
        if voice_dir.exists():
            disk_files = list(voice_dir.iterdir())
            assert len(disk_files) == 0, f"Found unexpected raw audio files on disk: {disk_files}"


def test_voice_report_transcription_failure_safe_zero_disk(isolated_db):
    """
    Verify that when Sarvam STT returns None (silent/unclear speech or API error):
    1. The voice report record is created safely with transcription=None.
    2. audio_path is strictly None (Zero-Retention: failed audio is never retained).
    3. ZERO audio files are created on disk.
    """
    session, temp_upload_dir = isolated_db
    sample_audio_bytes = b"ID3\x03\x00\x00\x00\x00\x00\x00" + b"dummy_mp3_bytes"

    with patch("app.services.scan_service.transcribe_audio_bytes", return_value=None):
        report = create_voice_report(
            db=session,
            scan_id=10,
            user_id=1,
            file_bytes=sample_audio_bytes,
            content_type="audio/mpeg",
            original_filename="silent_audio.mp3",
            language="hi",
            duration=1.2,
        )

        assert report.id is not None
        assert report.transcription is None
        assert report.audio_path is None
        assert report.language == "hi"

        voice_dir = temp_upload_dir / "voice_reports"
        if voice_dir.exists():
            assert len(list(voice_dir.iterdir())) == 0


def test_voice_report_transcription_timeout_or_network_error(isolated_db):
    """
    Verify that if the STT service encounters a timeout or connection issue:
    1. Error handling returns None gracefully without crashing the upload.
    2. Zero audio files are saved to disk.
    """
    session, temp_upload_dir = isolated_db
    sample_audio_bytes = b"RIFF\x24\x00\x00\x00WAVE" + b"dummy_wav_bytes"

    # transcribe_audio_bytes already catches TimeoutException internally and returns None
    with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Read timed out")):
        report = create_voice_report(
            db=session,
            scan_id=10,
            user_id=1,
            file_bytes=sample_audio_bytes,
            content_type="audio/wav",
            original_filename="timeout_audio.wav",
            language="en",
        )

        assert report.transcription is None
        assert report.audio_path is None

        voice_dir = temp_upload_dir / "voice_reports"
        if voice_dir.exists():
            assert len(list(voice_dir.iterdir())) == 0


def test_voice_report_database_commit_failure_rollback(isolated_db):
    """
    Verify that if database commit fails:
    1. The session is rolled back safely.
    2. HTTPException(500) is raised.
    3. ZERO orphaned audio files are left on disk.
    """
    session, temp_upload_dir = isolated_db
    sample_audio_bytes = b"\x00\x00\x00\x1cftypM4A " + b"dummy_audio_bytes"

    with patch("app.services.scan_service.transcribe_audio_bytes", return_value="Test transcript"), \
         patch.object(session, "commit", side_effect=OperationalError("commit failed", None, None)):
        
        with pytest.raises(HTTPException) as exc_info:
            create_voice_report(
                db=session,
                scan_id=10,
                user_id=1,
                file_bytes=sample_audio_bytes,
                content_type="audio/mp4",
                original_filename="db_fail.m4a",
                language="mr",
            )

        assert exc_info.value.status_code == 500
        assert "Voice report record could not be saved" in exc_info.value.detail

        voice_dir = temp_upload_dir / "voice_reports"
        if voice_dir.exists():
            assert len(list(voice_dir.iterdir())) == 0


def test_voice_report_ownership_and_validation_guards(isolated_db):
    """
    Verify that existing scan ownership and audio validation guards remain intact.
    """
    session, _ = isolated_db

    # 1. Non-existent scan -> 404
    with pytest.raises(HTTPException) as exc_404:
        create_voice_report(
            db=session,
            scan_id=9999,
            user_id=1,
            file_bytes=b"dummy",
            content_type="audio/mp4",
            original_filename="test.m4a",
        )
    assert exc_404.value.status_code == 404

    # 2. Wrong user ownership -> 403
    with pytest.raises(HTTPException) as exc_403:
        create_voice_report(
            db=session,
            scan_id=10,
            user_id=99,  # Different user
            file_bytes=b"dummy",
            content_type="audio/mp4",
            original_filename="test.m4a",
        )
    assert exc_403.value.status_code == 403

    # 3. Disallowed MIME type -> 422
    with pytest.raises(HTTPException) as exc_422:
        create_voice_report(
            db=session,
            scan_id=10,
            user_id=1,
            file_bytes=b"dummy",
            content_type="application/pdf",
            original_filename="doc.pdf",
        )
    assert exc_422.value.status_code == 422


def test_voice_upload_api_endpoint_schema_contract(isolated_db):
    """
    Verify the API endpoint POST /api/v1/scans/{scan_id}/voice maintains the exact
    VoiceReportCreateResponse schema contract with zero disk retention.
    """
    session, temp_upload_dir = isolated_db
    user = session.query(User).filter(User.id == 1).first()

    from app.api.v1.auth import get_current_user
    app.dependency_overrides[get_current_user] = lambda: user

    try:
        with TestClient(app) as client, \
             patch("app.services.scan_service.transcribe_audio_bytes", return_value="शेतात पाने पिवळी पडली आहेत"):
            
            audio_payload = io.BytesIO(b"\x00\x00\x00\x1cftypM4A " + b"endpoint_audio_bytes")
            files = {"audio": ("farmer_recording.m4a", audio_payload, "audio/mp4")}
            data = {"language": "mr", "duration": "4.2"}

            res = client.post(
                "/api/v1/scans/10/voice",
                headers={"Authorization": "Bearer fake_token"},
                files=files,
                data=data,
            )

            assert res.status_code == 201
            body = res.json()
            assert body["scan_id"] == 10
            assert body["language"] == "mr"
            assert body["status"] == "received"
            assert body["transcription"] == "शेतात पाने पिवळी पडली आहेत"
            assert "voice_report_id" in body
            assert "audio_path" not in body  # API contract preserved

            # Verify no audio was written to disk
            voice_dir = temp_upload_dir / "voice_reports"
            if voice_dir.exists():
                assert len(list(voice_dir.iterdir())) == 0
    finally:
        app.dependency_overrides.pop(get_current_user, None)
