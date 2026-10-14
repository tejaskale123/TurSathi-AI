import sys
from pathlib import Path

# Ensure backend directory is in sys.path for direct execution
backend_path = Path(__file__).resolve().parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

import random
import string
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database.base import Base
from app.database.session import get_db


@pytest.fixture(scope="function")
def client():
    """
    Provides an in-process FastAPI TestClient backed by an isolated
    in-memory SQLite database. Does not connect to or modify PostgreSQL.
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
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_auth_regression(client):
    """
    Regression test verifying email/mobile normalization and auth security
    in an isolated in-memory test environment.
    """
    suffix = "".join(random.choices(string.ascii_lowercase, k=6))
    mobile_suffix = "".join(random.choices(string.digits, k=4))

    # 1. Register with mixed case email, login with lowercase
    email_reg = f"Tejas_{suffix}@Gmail.com"
    email_login = f"tejas_{suffix}@gmail.com"
    password = "SecurePassword123!"

    reg_resp = client.post("/api/v1/auth/register", json={
        "full_name": "Tejas Test",
        "email": email_reg,
        "mobile_number": f"987650{mobile_suffix}",
        "password": password,
        "confirm_password": password
    })
    assert reg_resp.status_code == 201, f"Registration failed: {reg_resp.text}"
    reg_data = reg_resp.json()
    assert "access_token" in reg_data

    log_resp = client.post("/api/v1/auth/login", json={
        "identifier": email_login,
        "password": password
    })
    assert log_resp.status_code == 200, f"Login failed: {log_resp.text}"
    log_data = log_resp.json()
    assert "access_token" in log_data

    # 2. Register with mobile formatting, login with normalized mobile
    mobile_reg = f"+91 987654{mobile_suffix}"
    mobile_login = f"987654{mobile_suffix}"

    reg_resp2 = client.post("/api/v1/auth/register", json={
        "full_name": "Mobile Test",
        "email": f"mobile_{suffix}@test.com",
        "mobile_number": mobile_reg,
        "password": password,
        "confirm_password": password
    })
    assert reg_resp2.status_code == 201, f"Registration failed: {reg_resp2.text}"

    log_resp2 = client.post("/api/v1/auth/login", json={
        "identifier": mobile_login,
        "password": password
    })
    assert log_resp2.status_code == 200, f"Login failed: {log_resp2.text}"

    # 3. Wrong password
    log_resp3 = client.post("/api/v1/auth/login", json={
        "identifier": email_login,
        "password": "WrongPassword!"
    })
    assert log_resp3.status_code == 401, f"Expected 401, got {log_resp3.status_code}"

    # 4. Non-existing user
    log_resp4 = client.post("/api/v1/auth/login", json={
        "identifier": "nonexistent_user@example.com",
        "password": password
    })
    assert log_resp4.status_code == 401, f"Expected 401, got {log_resp4.status_code}"

    # 5. Duplicate Email Rejection
    dup_email_resp = client.post("/api/v1/auth/register", json={
        "full_name": "Duplicate Email User",
        "email": email_login,
        "mobile_number": "9999888877",
        "password": password,
        "confirm_password": password
    })
    assert dup_email_resp.status_code == 400, f"Expected 400 for duplicate email, got {dup_email_resp.status_code}"
    assert "already registered" in dup_email_resp.text.lower()

    # 6. Duplicate Mobile Rejection
    dup_mobile_resp = client.post("/api/v1/auth/register", json={
        "full_name": "Duplicate Mobile User",
        "email": f"unique_{suffix}@example.com",
        "mobile_number": mobile_login,
        "password": password,
        "confirm_password": password
    })
    assert dup_mobile_resp.status_code == 400, f"Expected 400 for duplicate mobile, got {dup_mobile_resp.status_code}"
    assert "already registered" in dup_mobile_resp.text.lower()

    # 7. Missing Required Field / Validation Error (422)
    inv_reg_resp = client.post("/api/v1/auth/register", json={
        "full_name": "No Password User",
        "email": f"nopass_{suffix}@example.com",
        "mobile_number": "9123456789"
    })
    assert inv_reg_resp.status_code == 422, f"Expected 422 for missing fields, got {inv_reg_resp.status_code}"

    # 8. Password Mismatch (422)
    mismatch_resp = client.post("/api/v1/auth/register", json={
        "full_name": "Mismatch User",
        "email": f"mismatch_{suffix}@example.com",
        "mobile_number": "9123456780",
        "password": "Password123!",
        "confirm_password": "DifferentPassword!"
    })
    assert mismatch_resp.status_code == 422, f"Expected 422 for mismatch, got {mismatch_resp.status_code}"

    # 9. Protected Endpoint (/api/v1/auth/me) with Valid Token
    token = log_data["access_token"]
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200, f"Expected 200 for /me, got {me_resp.status_code}"
    me_data = me_resp.json()
    assert me_data["email"] == email_login.lower()
    assert "password" not in me_data
    assert "hashed_password" not in me_data

    # 10. Protected Endpoint without Token or with Invalid Token (401)
    no_auth_resp = client.get("/api/v1/auth/me")
    assert no_auth_resp.status_code == 401, f"Expected 401 without auth, got {no_auth_resp.status_code}"

    bad_auth_resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.fake.token"})
    assert bad_auth_resp.status_code == 401, f"Expected 401 with fake token, got {bad_auth_resp.status_code}"

    # 11. Sensitive Field Exposure Check
    for resp_data in [reg_data, log_data]:
        user_info = resp_data.get("user", {})
        assert "password" not in user_info
        assert "hashed_password" not in user_info
        assert "password_hash" not in user_info


if __name__ == "__main__":
    # Support direct execution without pytest runner
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
    try:
        with TestClient(app) as direct_client:
            test_auth_regression(direct_client)
            print("All auth regression tests passed successfully in isolated test environment.")
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
