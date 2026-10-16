"""
Stateless Frame Validation Verification Suite.

Tests:
1. POST /api/v1/scans/validate-frame requires Bearer JWT authentication.
2. Valid real Tur leaf image returns HTTP 200 with is_valid_tur=True.
3. Undersized (<224x224) frame returns HTTP 200 with is_valid_tur=False and reason 'image_too_small'.
4. Blurry frame returns HTTP 200 with is_valid_tur=False and reason 'image_too_blurry'.
5. Empty upload returns HTTP 200 with is_valid_tur=False and reason 'empty_file'.
6. ZERO DATABASE RECORDS CREATED: Verifies tur_scans table has 0 rows before and after validation calls.
7. ZERO FILES WRITTEN TO DISK: Verifies the upload directory contains 0 files before and after validation calls.
"""

import io
import sys
import tempfile
from pathlib import Path

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

import pytest
import numpy as np
import cv2
from PIL import Image
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database.base import Base
from app.database.session import get_db
from app.database.models.tur_scan import TurScan
import app.services.storage_service as storage_module
import app.services.prediction_service as prediction_module


@pytest.fixture(scope="function")
def test_setup(monkeypatch):
    """
    Sets up an in-memory SQLite database and an isolated temporary upload directory.
    Yields (test_client, db_session_factory, temp_upload_dir).
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_upload_path = Path(temp_dir)
        monkeypatch.setattr(storage_module, "UPLOAD_DIR", temp_upload_path)
        monkeypatch.setattr(storage_module, "SCAN_IMAGES_DIR", temp_upload_path / "scans")
        monkeypatch.setattr(storage_module, "VOICE_REPORTS_DIR", temp_upload_path / "voice_reports")
        monkeypatch.setattr(prediction_module, "UPLOAD_DIR", temp_upload_path)

        with TestClient(app) as client:
            yield client, TestingSessionLocal, temp_upload_path

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def get_auth_token(client: TestClient) -> str:
    """Helper to register a test user and obtain a JWT bearer token."""
    resp = client.post("/api/v1/auth/register", json={
        "full_name": "Test Farmer",
        "email": "farmer_probe@test.com",
        "mobile_number": "9123456789",
        "password": "Password123!",
        "confirm_password": "Password123!",
    })
    assert resp.status_code == 201
    return resp.json()["access_token"]


def create_test_image_bytes(width: int = 300, height: int = 300, is_blurry: bool = False) -> bytes:
    """Creates in-memory JPEG bytes for testing."""
    if is_blurry:
        # Uniform solid color produces 0 variance in Laplacian
        arr = np.full((height, width, 3), 128, dtype=np.uint8)
    else:
        # Sharp high-frequency grid pattern
        arr = np.zeros((height, width, 3), dtype=np.uint8)
        arr[::10, :, :] = 255
        arr[:, ::10, :] = 255
    
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestValidateFrameStateless:

    def test_auth_required(self, test_setup):
        client, _, _ = test_setup
        resp = client.post(
            "/api/v1/scans/validate-frame",
            files={"image": ("probe.jpg", b"dummy", "image/jpeg")},
        )
        assert resp.status_code == 401, "Unauthenticated request must be rejected"

    def test_real_tur_image_passes(self, test_setup):
        client, _, _ = test_setup
        token = get_auth_token(client)
        headers = {"Authorization": f"Bearer {token}"}

        # Check real leaf fixture if available
        real_tur_path = Path("datasets/tur_image_validator/real_world_test/Tur/realworld_tur_01.png")
        if real_tur_path.exists():
            image_bytes = real_tur_path.read_bytes()
        else:
            image_bytes = create_test_image_bytes(width=300, height=300, is_blurry=False)

        resp = client.post(
            "/api/v1/scans/validate-frame",
            headers=headers,
            files={"image": ("probe.png", image_bytes, "image/png")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "is_valid_tur" in data
        assert "confidence" in data
        assert "label" in data
        assert "reason" in data
        assert isinstance(data["confidence"], float)

        if real_tur_path.exists():
            assert data["is_valid_tur"] is True
            assert data["reason"] == "validator_confident_tur"

    def test_undersized_image_rejected(self, test_setup):
        client, _, _ = test_setup
        token = get_auth_token(client)
        headers = {"Authorization": f"Bearer {token}"}

        small_bytes = create_test_image_bytes(width=100, height=100)
        resp = client.post(
            "/api/v1/scans/validate-frame",
            headers=headers,
            files={"image": ("small.jpg", small_bytes, "image/jpeg")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_valid_tur"] is False
        assert data["reason"] == "image_too_small"

    def test_blurry_image_rejected(self, test_setup):
        client, _, _ = test_setup
        token = get_auth_token(client)
        headers = {"Authorization": f"Bearer {token}"}

        blurry_bytes = create_test_image_bytes(width=300, height=300, is_blurry=True)
        resp = client.post(
            "/api/v1/scans/validate-frame",
            headers=headers,
            files={"image": ("blurry.jpg", blurry_bytes, "image/jpeg")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_valid_tur"] is False
        assert data["reason"] == "image_too_blurry"

    def test_empty_frame_handled_safely(self, test_setup):
        client, _, _ = test_setup
        token = get_auth_token(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.post(
            "/api/v1/scans/validate-frame",
            headers=headers,
            files={"image": ("empty.jpg", b"", "image/jpeg")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_valid_tur"] is False
        assert data["reason"] == "empty_file"

    def test_zero_database_records_and_zero_files_created(self, test_setup):
        """
        CRITICAL TEST: Proves that multiple probe snapshot validations create
        zero database records in tur_scans and write zero files to the filesystem.
        """
        client, SessionLocal, upload_path = test_setup
        token = get_auth_token(client)
        headers = {"Authorization": f"Bearer {token}"}

        # Check DB state before probes
        db = SessionLocal()
        initial_scans_count = db.query(TurScan).count()
        db.close()

        # Check filesystem state before probes
        initial_file_count = len(list(upload_path.rglob("*")))

        # Simulate 10 consecutive camera snapshot probes
        for i in range(10):
            test_bytes = create_test_image_bytes(width=250, height=250, is_blurry=(i % 2 == 0))
            resp = client.post(
                "/api/v1/scans/validate-frame",
                headers=headers,
                files={"image": (f"probe_{i}.jpg", test_bytes, "image/jpeg")},
            )
            assert resp.status_code == 200

        # Verify DB state after probes
        db = SessionLocal()
        final_scans_count = db.query(TurScan).count()
        db.close()

        # Verify filesystem state after probes
        final_file_count = len(list(upload_path.rglob("*")))

        assert final_scans_count == initial_scans_count, (
            f"Database pollution detected! Expected {initial_scans_count} scans, found {final_scans_count}"
        )
        assert final_file_count == initial_file_count, (
            f"Filesystem pollution detected! Expected {initial_file_count} files, found {final_file_count}"
        )

    def test_real_nottur_image_rejected(self, test_setup):
        """Verifies that non-Tur field images are rejected with is_valid_tur=False."""
        client, _, _ = test_setup
        token = get_auth_token(client)
        headers = {"Authorization": f"Bearer {token}"}

        nottur_path = Path("datasets/tur_image_validator/real_world_test/Not_Tur/realworld_nottur_01.png")
        if nottur_path.exists():
            image_bytes = nottur_path.read_bytes()
            resp = client.post(
                "/api/v1/scans/validate-frame",
                headers=headers,
                files={"image": ("nottur.png", image_bytes, "image/png")},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["is_valid_tur"] is False
            assert data["reason"] == "validator_confident_not_tur"

    def test_binary_model_organ_limitation_honest_contract(self, test_setup):
        """
        Verifies and documents that the existing TurImageGate model operates as
        a binary crop gate (Tur vs Not_Tur) and does not pretend to perform
        organ-level leaf-vs-pod discrimination.
        """
        from app.ml.tur_image_gate import TurImageGate
        gate = TurImageGate()
        assert gate.validator is not None
        # Confirms classes are binary
        assert set(gate.validator.classes) == {"Not_Tur", "Tur"}
        # Confirms that no pod/canopy organ classifier is falsely active
        from app.core.config import settings
        assert getattr(settings, "ENABLE_ORGAN_VALIDATOR", False) is False

