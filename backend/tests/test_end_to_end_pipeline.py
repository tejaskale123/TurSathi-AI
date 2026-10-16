"""
Isolated End-to-End Pipeline Verification Suite for Stage F27.

Covers:
- API endpoints: /api/v1/scans, /api/v1/predictions/tur-leaf/{scan_id}, /api/v1/recommendations
- Schema compliance across all five supported classes (Healthy, Leaf_Spot, Leaf_webber, Sterilic_mosaic, Wilt)
- Valid supported pigeonpea end-to-end flow through TurImageGate and TurDiseasePredictor
- Image-gate rejection of non-tur leaves (HTTP 422 validation_failed)
- Handling of corrupted images (intake + gate rejection on predict)
- Handling of empty and disallowed MIME uploads
- Ownership security and multi-tenant isolation
- Error sanitization ensuring no secrets, internal paths, or stack traces leak to users
- Database isolation via in-memory SQLite (zero writes to PostgreSQL)
- Temporary isolated filesystem storage (zero writes to production upload directory)
"""

import sys
import tempfile
from pathlib import Path

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database.base import Base
from app.database.session import get_db
import app.services.storage_service as storage_module
import app.services.prediction_service as prediction_module
from app.schemas.prediction import PredictionResponse
from app.schemas.scan import ScanDetailResponse
from app.ml.tur_predictor import TurDiseasePredictor


SUPPORTED_FIVE_CLASSES = [
    "Healthy",
    "Leaf_Spot",
    "Leaf_webber",
    "Sterilic_mosaic",
    "Wilt",
]


@pytest.fixture(scope="function")
def isolated_env(monkeypatch):
    """
    Sets up an in-memory SQLite database and a temporary directory for file uploads.
    Guarantees no records are written to PostgreSQL and no files to production uploads.
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

        with TestClient(app) as test_client:
            yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def register_and_get_token(client: TestClient, email: str = "farmer@test.com", mobile: str = "9876543210") -> str:
    """Helper to register a user and return a bearer JWT."""
    resp = client.post("/api/v1/auth/register", json={
        "full_name": "Farmer Ramesh",
        "email": email,
        "mobile_number": mobile,
        "password": "ValidPassword123!",
        "confirm_password": "ValidPassword123!"
    })
    assert resp.status_code == 201, f"Registration failed: {resp.text}"
    return resp.json()["access_token"]


# ==============================================================================
# 1. Schema & Five-Class Mapping Tests
# ==============================================================================

def test_five_classes_schema_integrity():
    """Verify that all five supported classes exist and match predictor classes."""
    predictor = TurDiseasePredictor()
    assert predictor.is_available(), "Predictor model must be available"
    loaded_classes = predictor._classes

    # Verify exact match with 5 supported classes
    assert sorted(loaded_classes) == sorted(SUPPORTED_FIVE_CLASSES), (
        f"Loaded classes {loaded_classes} do not match supported 5 classes {SUPPORTED_FIVE_CLASSES}"
    )

    # Verify each class can be serialized in PredictionResponse schema
    for cls_name in SUPPORTED_FIVE_CLASSES:
        resp = PredictionResponse(
            scan_id=1,
            crop="tur",
            status="completed",
            disease_name=cls_name,
            confidence=0.95,
            severity="high_confidence"
        )
        assert resp.disease_name == cls_name
        assert resp.status == "completed"


# ==============================================================================
# 2. End-to-End Flow for Valid Supported Pigeonpea Image
# ==============================================================================

def test_valid_pigeonpea_end_to_end_flow(isolated_env):
    """
    Upload real clean pigeonpea test image -> runs image gate -> runs disease classifier
    -> returns HTTP 200 with completed status and valid disease prediction.
    """
    client = isolated_env
    token = register_and_get_token(client, "valid_farmer@test.com", "9876543201")
    headers = {"Authorization": f"Bearer {token}"}

    # Use a real healthy pigeonpea test image
    real_img_path = Path("datasets/pigeonpea_disease_final/test/Healthy/healthy_test_0000.jpg")
    assert real_img_path.exists(), f"Test fixture not found: {real_img_path}"

    with open(real_img_path, "rb") as f:
        img_bytes = f.read()

    # Step 1: Upload Scan (POST /api/v1/scans)
    upload_resp = client.post(
        "/api/v1/scans",
        headers=headers,
        files={"image": ("healthy_test_0000.jpg", img_bytes, "image/jpeg")},
        data={"crop": "tur"}
    )
    assert upload_resp.status_code == 201, f"Upload failed: {upload_resp.text}"
    upload_data = upload_resp.json()
    scan_id = upload_data["scan_id"]
    assert upload_data["crop"] == "tur"
    assert upload_data["status"] == "received"

    # Step 2: Run Prediction (POST /api/v1/predictions/tur-leaf/{scan_id})
    pred_resp = client.post(
        f"/api/v1/predictions/tur-leaf/{scan_id}",
        headers=headers
    )
    assert pred_resp.status_code == 200, f"Prediction failed: {pred_resp.text}"
    pred_data = pred_resp.json()
    assert pred_data["scan_id"] == scan_id
    assert pred_data["crop"] == "tur"
    assert pred_data["status"] == "completed"
    assert pred_data["disease_name"] in SUPPORTED_FIVE_CLASSES
    assert 0.0 <= pred_data["confidence"] <= 1.0
    assert pred_data["severity"] in ["high_confidence", "moderate_confidence", "low_confidence"]

    # Step 3: Verify Persistence in Scan Detail (GET /api/v1/scans/{scan_id})
    detail_resp = client.get(
        f"/api/v1/scans/{scan_id}",
        headers=headers
    )
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert detail_data["scan_id"] == scan_id
    assert detail_data["status"] == "completed"
    assert detail_data["prediction_status"] == "completed"
    assert detail_data["disease_name"] == pred_data["disease_name"]
    assert detail_data["confidence"] == pred_data["confidence"]


# ==============================================================================
# 3. Image-Gate Rejection for Non-Tur Agricultural Leaf
# ==============================================================================

def test_image_gate_rejection_non_tur(isolated_env):
    """
    Upload a non-tur crop leaf (e.g. chilli/tomato leaf curl) -> image gate detects
    Not_Tur -> returns HTTP 422 with user-friendly rejection guidance.
    """
    client = isolated_env
    token = register_and_get_token(client, "nottur_farmer@test.com", "9876543202")
    headers = {"Authorization": f"Bearer {token}"}

    nottur_path = Path("datasets/tur_image_validator_v3/test/Not_Tur/curl106.jpg")
    assert nottur_path.exists(), f"Test fixture not found: {nottur_path}"

    with open(nottur_path, "rb") as f:
        img_bytes = f.read()

    # Step 1: Upload succeeds at intake level
    upload_resp = client.post(
        "/api/v1/scans",
        headers=headers,
        files={"image": ("curl106.jpg", img_bytes, "image/jpeg")},
        data={"crop": "tur"}
    )
    assert upload_resp.status_code == 201
    scan_id = upload_resp.json()["scan_id"]

    # Step 2: Prediction is safely rejected by TurImageGate
    pred_resp = client.post(
        f"/api/v1/predictions/tur-leaf/{scan_id}",
        headers=headers
    )
    assert pred_resp.status_code == 422, f"Expected 422 rejection, got: {pred_resp.status_code}"
    error_data = pred_resp.json()
    assert "detail" in error_data
    assert error_data["detail"]["status"] == "validation_failed"
    assert "Please upload a clear Tur/Pigeonpea leaf image." in error_data["detail"]["message"]

    # Step 3: Scan state in database is updated to rejected
    detail_resp = client.get(f"/api/v1/scans/{scan_id}", headers=headers)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["status"] == "rejected"
    assert detail_resp.json()["prediction_status"] == "rejected"


# ==============================================================================
# 4. Corrupted, Empty, and Disallowed Image Handling
# ==============================================================================

def test_empty_image_upload_rejected(isolated_env):
    """Empty 0-byte file must be rejected with HTTP 422."""
    client = isolated_env
    token = register_and_get_token(client, "empty_file_user@test.com", "9876543203")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(
        "/api/v1/scans",
        headers=headers,
        files={"image": ("empty.jpg", b"", "image/jpeg")},
        data={"crop": "tur"}
    )
    assert resp.status_code in [400, 422]
    assert "empty" in resp.text.lower() or "no image" in resp.text.lower()


def test_corrupted_image_caught_safely(isolated_env):
    """
    Corrupted bytes disguised with image/jpeg header:
    - Intake saves the upload as received (HTTP 201).
    - Prediction service invokes TurImageGate which decodes with PIL, detects corruption,
      updates scan status to rejected, and raises HTTP 422 with user guidance.
    """
    client = isolated_env
    token = register_and_get_token(client, "corrupt_user@test.com", "9876543204")
    headers = {"Authorization": f"Bearer {token}"}

    fake_bytes = b"NOT_A_REAL_JPEG_HEADER_RANDOM_TEXT_DATA_CORRUPTION"
    upload_resp = client.post(
        "/api/v1/scans",
        headers=headers,
        files={"image": ("corrupt.jpg", fake_bytes, "image/jpeg")},
        data={"crop": "tur"}
    )
    assert upload_resp.status_code == 201
    scan_id = upload_resp.json()["scan_id"]

    pred_resp = client.post(
        f"/api/v1/predictions/tur-leaf/{scan_id}",
        headers=headers
    )
    assert pred_resp.status_code == 422
    err = pred_resp.json()
    assert err["detail"]["status"] == "validation_failed"
    assert "Please upload a clear Tur/Pigeonpea leaf image." in err["detail"]["message"]

    # Scan record is marked rejected
    detail = client.get(f"/api/v1/scans/{scan_id}", headers=headers).json()
    assert detail["status"] == "rejected"
    assert detail["prediction_status"] == "rejected"


def test_disallowed_mime_type_rejected(isolated_env):
    """PDF file uploaded as image must be rejected with HTTP 422 at intake."""
    client = isolated_env
    token = register_and_get_token(client, "pdf_user@test.com", "9876543205")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(
        "/api/v1/scans",
        headers=headers,
        files={"image": ("document.pdf", b"%PDF-1.4 dummy content", "application/pdf")},
        data={"crop": "tur"}
    )
    assert resp.status_code == 422
    assert "unsupported image type" in resp.text.lower()


# ==============================================================================
# 5. Security: Authentication & Tenant Ownership Enforcement
# ==============================================================================

def test_unauthenticated_requests_blocked(isolated_env):
    """
    Unauthenticated calls to protected routes are rejected:
    - Missing Authorization header returns HTTP 422 (required header missing).
    - Invalid/expired Bearer token returns HTTP 401 (unauthorized).
    """
    client = isolated_env
    # Missing header -> 401 or 422
    assert client.get("/api/v1/scans/1").status_code in [401, 422]
    assert client.post("/api/v1/predictions/tur-leaf/1").status_code in [401, 422]

    # Invalid Bearer token -> 401
    bad_headers = {"Authorization": "Bearer invalid.jwt.token"}
    assert client.get("/api/v1/scans/1", headers=bad_headers).status_code == 401
    assert client.post("/api/v1/predictions/tur-leaf/1", headers=bad_headers).status_code == 401
    assert client.post("/api/v1/scans", headers=bad_headers).status_code in [401, 422]


def test_cross_tenant_scan_isolation(isolated_env):
    """User B cannot access or trigger prediction on User A's scan."""
    client = isolated_env
    token_a = register_and_get_token(client, "user_a@test.com", "9876543211")
    token_b = register_and_get_token(client, "user_b@test.com", "9876543212")

    # User A uploads a scan
    real_img_path = Path("datasets/pigeonpea_disease_final/test/Healthy/healthy_test_0000.jpg")
    with open(real_img_path, "rb") as f:
        img_bytes = f.read()

    upload_resp = client.post(
        "/api/v1/scans",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"image": ("healthy.jpg", img_bytes, "image/jpeg")},
        data={"crop": "tur"}
    )
    assert upload_resp.status_code == 201
    scan_id_a = upload_resp.json()["scan_id"]

    # User B attempts to access User A's scan
    get_resp = client.get(
        f"/api/v1/scans/{scan_id_a}",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert get_resp.status_code in [403, 404]

    # User B attempts to run prediction on User A's scan
    pred_resp = client.post(
        f"/api/v1/predictions/tur-leaf/{scan_id_a}",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert pred_resp.status_code in [403, 404]


# ==============================================================================
# 6. Error Sanitization & Route Integrity Checks
# ==============================================================================

def test_nonexistent_route_clean_404(isolated_env):
    """Requests to non-existent route /api/v1/predict/ return clean 404 without stack traces."""
    client = isolated_env
    token = register_and_get_token(client, "route_tester@test.com", "9876543213")
    resp = client.post("/api/v1/predict/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404
    assert "c:" not in resp.text.lower()
    assert "users" not in resp.text.lower()


def test_recommendation_endpoint_handled_safely(isolated_env):
    """
    GET /api/v1/recommendations/tur/{disease_name}/spray-guidance returns clean 404
    with user-facing message when unseeded, without crashing or exposing internals.
    """
    client = isolated_env
    token = register_and_get_token(client, "recom_tester@test.com", "9876543214")
    headers = {"Authorization": f"Bearer {token}"}

    for disease in ["Healthy", "Leaf_Spot", "Wilt"]:
        resp = client.get(f"/api/v1/recommendations/tur/{disease}/spray-guidance", headers=headers)
        assert resp.status_code in [200, 404]
        if resp.status_code == 404:
            err = resp.json()
            assert "Verified spray guidance is not available" in err["detail"]
