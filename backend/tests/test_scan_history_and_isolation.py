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
from app.database.models.tur_disease_recommendation import TurDiseaseRecommendation


@pytest.fixture(scope="function")
def isolated_env(monkeypatch):
    """
    Sets up an isolated in-memory SQLite database and temporary storage directory.
    Guarantees zero writes or modifications to production PostgreSQL or upload files.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    # Seed isolated test recommendations
    db = TestingSessionLocal()
    try:
        active_rec = TurDiseaseRecommendation(
            crop="tur",
            disease_name="Fusarium Wilt",
            application_method="01 Drench soil with Carbendazim 1g/L\n02 Avoid water stagnation",
            after_spray_advisory="Inspect root collar after 7 days",
            safety_precautions="Wear protective rubber gloves and mask",
            is_active=True,
        )
        inactive_rec = TurDiseaseRecommendation(
            crop="tur",
            disease_name="Leaf Webber",
            application_method="Historical application",
            after_spray_advisory="Do not spray",
            safety_precautions="Toxic",
            is_active=False,
        )
        db.add_all([active_rec, inactive_rec])
        db.commit()
    finally:
        db.close()

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

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


def register_user(client: TestClient, full_name: str, mobile: str, email: str = None) -> str:
    """Helper to register a user and return their JWT access token."""
    resp = client.post("/api/v1/auth/register", json={
        "full_name": full_name,
        "mobile_number": mobile,
        "email": email,
        "password": "Password123!",
        "confirm_password": "Password123!"
    })
    assert resp.status_code == 201, f"Registration failed: {resp.text}"
    return resp.json()["access_token"]


def create_dummy_scan(client: TestClient, token: str, filename: str = "tur_leaf.jpg") -> int:
    """Helper to upload a valid tiny JPEG image and return scan_id."""
    # Minimal 1x1 valid JPEG byte payload
    jpeg_bytes = bytes([
        0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
        0x01, 0x01, 0x00, 0x48, 0x00, 0x48, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
        0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
        0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
        0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
        0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
        0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
        0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
        0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x1F, 0x00, 0x00,
        0x01, 0x05, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
        0x09, 0x0A, 0x0B, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F,
        0x00, 0xBF, 0x80, 0xFF, 0xD9
    ])

    files = {"image": (filename, jpeg_bytes, "image/jpeg")}
    data = {"crop": "tur"}
    resp = client.post(
        "/api/v1/scans",
        headers={"Authorization": f"Bearer {token}"},
        files=files,
        data=data,
    )
    assert resp.status_code == 201, f"Scan creation failed: {resp.text}"
    return resp.json()["scan_id"]


# ==============================================================================
# Priority 1: Persistent Scan History & Isolation Tests
# ==============================================================================

def test_scan_history_unauthorized(isolated_env):
    """GET /api/v1/scans without authorization must return HTTP 401."""
    client = isolated_env
    resp = client.get("/api/v1/scans")
    assert resp.status_code == 401


def test_scan_history_empty_for_new_user(isolated_env):
    """New user has empty persistent history."""
    client = isolated_env
    token = register_user(client, "Ramesh Patil", "9876500001")

    resp = client.get("/api/v1/scans", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []
    assert data["page"] == 1


def test_scan_history_pagination_and_ordering(isolated_env):
    """
    User creates multiple scans. GET /api/v1/scans respects skip/limit,
    computes total pages, and orders newest-first.
    """
    client = isolated_env
    token = register_user(client, "Suresh Deshmukh", "9876500002")

    # Create 5 scans
    scan_ids = []
    for i in range(5):
        s_id = create_dummy_scan(client, token, filename=f"leaf_{i}.jpg")
        scan_ids.append(s_id)

    # Page 1: limit 2
    resp1 = client.get("/api/v1/scans?page=1&limit=2", headers={"Authorization": f"Bearer {token}"})
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["total"] == 5
    assert data1["page"] == 1
    assert data1["limit"] == 2
    assert data1["total_pages"] == 3
    assert len(data1["items"]) == 2
    # Newest scan should be first
    assert data1["items"][0]["scan_id"] == scan_ids[4]
    assert data1["items"][1]["scan_id"] == scan_ids[3]

    # Page 2: limit 2
    resp2 = client.get("/api/v1/scans?page=2&limit=2", headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert len(data2["items"]) == 2
    assert data2["items"][0]["scan_id"] == scan_ids[2]
    assert data2["items"][1]["scan_id"] == scan_ids[1]

    # Page 3: limit 2
    resp3 = client.get("/api/v1/scans?page=3&limit=2", headers={"Authorization": f"Bearer {token}"})
    assert resp3.status_code == 200
    data3 = resp3.json()
    assert len(data3["items"]) == 1
    assert data3["items"][0]["scan_id"] == scan_ids[0]


def test_cross_user_scan_isolation(isolated_env):
    """
    User A's scans must never be visible to User B, neither in list nor by direct ID.
    """
    client = isolated_env
    token_a = register_user(client, "Farmer A", "9876500011")
    token_b = register_user(client, "Farmer B", "9876500012")

    # User A creates a scan
    scan_a_id = create_dummy_scan(client, token_a, "crop_a.jpg")

    # User B requests scan list -> User A's scan is NOT in User B's list
    resp_b_list = client.get("/api/v1/scans", headers={"Authorization": f"Bearer {token_b}"})
    assert resp_b_list.status_code == 200
    assert resp_b_list.json()["total"] == 0
    assert resp_b_list.json()["items"] == []

    # User B attempts to access User A's scan directly -> HTTP 403 Forbidden
    resp_b_detail = client.get(f"/api/v1/scans/{scan_a_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert resp_b_detail.status_code == 403
    assert "access denied" in resp_b_detail.text.lower()

    # User A can access their own scan
    resp_a_detail = client.get(f"/api/v1/scans/{scan_a_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert resp_a_detail.status_code == 200
    assert resp_a_detail.json()["scan_id"] == scan_a_id


def test_missing_scan_detail_returns_404(isolated_env):
    """Requesting nonexistent scan returns HTTP 404."""
    client = isolated_env
    token = register_user(client, "Farmer C", "9876500013")
    resp = client.get("/api/v1/scans/999999", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


def test_recommendation_safety_and_inactive_behavior(isolated_env):
    """
    Active disease (Fusarium Wilt) returns HTTP 200 with structured spray guidance.
    Inactive / unsupported condition (Leaf Webber) returns HTTP 404 without pesticide prescription.
    """
    client = isolated_env
    token = register_user(client, "Farmer D", "9876500014")

    # 1. Active disease
    resp_active = client.get(
        "/api/v1/recommendations/tur/Fusarium%20Wilt/spray-guidance",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_active.status_code == 200
    data_active = resp_active.json()
    assert data_active["disease_name"] == "Fusarium Wilt"
    assert len(data_active["spray_guidance"]) > 0

    # 2. Inactive Leaf Webber safety behavior: strictly forbidden to recommend pesticides
    resp_inactive = client.get(
        "/api/v1/recommendations/tur/Leaf%20Webber/spray-guidance",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_inactive.status_code == 404
