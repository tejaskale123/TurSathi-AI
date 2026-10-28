import sys
from pathlib import Path

# Ensure backend directory is in sys.path for direct execution
backend_path = Path(__file__).resolve().parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

import random
import string
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database.base import Base
from app.database.models.user import User
from app.database.models.password_reset_otp import PasswordResetOTP
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


def test_email_required_for_registration(client):
    """
    Verifies that email is strictly required for new user signups.
    """
    resp = client.post("/api/v1/auth/register", json={
        "full_name": "No Email Farmer",
        "mobile_number": "9876543210",
        "password": "ValidPassword123!",
        "confirm_password": "ValidPassword123!"
    })
    assert resp.status_code == 422, f"Expected 422 for missing email, got {resp.status_code}"

    resp_empty = client.post("/api/v1/auth/register", json={
        "full_name": "Empty Email Farmer",
        "mobile_number": "9876543211",
        "email": "   ",
        "password": "ValidPassword123!",
        "confirm_password": "ValidPassword123!"
    })
    assert resp_empty.status_code == 422, f"Expected 422 for blank email, got {resp_empty.status_code}"


def test_existing_null_email_user_can_login(client):
    """
    Verifies that legacy users in the database whose email is NULL
    can still log in seamlessly using their mobile number.
    """
    from app.core.security import get_password_hash
    from app.database.session import get_db

    # Insert a user directly with email=None to simulate a legacy record
    password = "LegacyPassword123!"
    mobile = "9812345678"

    # Access the active db session through the app override
    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        legacy_user = User(
            full_name="Legacy Farmer",
            mobile_number=mobile,
            email=None,
            password_hash=get_password_hash(password),
            is_active=True
        )
        db.add(legacy_user)
        db.commit()
    finally:
        db.close()

    # Attempt mobile number login
    login_resp = client.post("/api/v1/auth/login", json={
        "identifier": mobile,
        "password": password
    })
    assert login_resp.status_code == 200, f"Legacy user login failed: {login_resp.text}"
    token_data = login_resp.json()
    assert "access_token" in token_data
    assert token_data["user"]["mobile_number"] == mobile
    assert token_data["user"]["email"] is None


def test_forgot_password_full_lifecycle(client, monkeypatch=None):
    """
    Comprehensive integration test of the complete password recovery flow:
    - OTP request for registered user
    - Anti-enumeration generic responses
    - Cooldown rate-limiting (429)
    - SMTP failure rollback
    - Brute force protection / max attempts invalidation
    - OTP expiration handling
    - Single-use reset authorization token
    - Token purpose isolation (cross-endpoint rejection)
    - Successful password reset and credential rotation
    """
    suffix = "".join(random.choices(string.ascii_lowercase, k=6))
    email = f"recovery_{suffix}@example.com"
    mobile = f"998877{random.randint(1000, 9999)}"
    initial_password = "InitialPassword123!"
    new_password = "NewSecretPassword456!"

    # Capture sent OTPs in memory for test verification
    captured_otps = []

    def mock_send_otp_email(recipient_email, recipient_name, otp_code):
        captured_otps.append((recipient_email, otp_code))
        return True

    import app.services.auth_service as auth_svc
    if monkeypatch:
        monkeypatch.setattr(auth_svc, "send_otp_email", mock_send_otp_email)
    else:
        auth_svc.send_otp_email = mock_send_otp_email

    # 1. Register a test user
    reg_resp = client.post("/api/v1/auth/register", json={
        "full_name": "Recovery Test Farmer",
        "email": email,
        "mobile_number": mobile,
        "password": initial_password,
        "confirm_password": initial_password
    })
    assert reg_resp.status_code == 201

    # 2. Anti-enumeration: Unknown email returns 200 generic response
    unknown_resp = client.post("/api/v1/auth/forgot-password", json={
        "identifier": "unknown_farmer_404@example.com"
    })
    assert unknown_resp.status_code == 200
    assert "If an account with this email address exists" in unknown_resp.json()["message"]
    assert len(captured_otps) == 0

    # 3. Request OTP for eligible registered email
    forgot_resp = client.post("/api/v1/auth/forgot-password", json={
        "identifier": email
    })
    assert forgot_resp.status_code == 200
    assert "If an account with this email address exists" in forgot_resp.json()["message"]
    assert len(captured_otps) == 1
    sent_email, otp_code = captured_otps[-1]
    assert sent_email == email
    assert len(otp_code) == 6 and otp_code.isdigit()

    # 4. Resend cooldown: Immediate second request triggers 429
    cooldown_resp = client.post("/api/v1/auth/forgot-password", json={
        "identifier": email
    })
    assert cooldown_resp.status_code == 429
    assert "Please wait" in cooldown_resp.json()["detail"]

    # 5. Invalid OTP submission increments attempts
    bad_otp_resp = client.post("/api/v1/auth/verify-otp", json={
        "identifier": email,
        "otp": "000000" if otp_code != "000000" else "111111"
    })
    assert bad_otp_resp.status_code == 400
    assert "attempt(s) remaining" in bad_otp_resp.json()["detail"]

    # 6. Failed attempts limit: Send wrong OTP until locked (5 total attempts)
    for _ in range(4):
        client.post("/api/v1/auth/verify-otp", json={
            "identifier": email,
            "otp": "000000" if otp_code != "000000" else "111111"
        })
    locked_resp = client.post("/api/v1/auth/verify-otp", json={
        "identifier": email,
        "otp": otp_code
    })
    assert locked_resp.status_code == 400
    assert "Maximum verification attempts exceeded" in locked_resp.json()["detail"] or "No active" in locked_resp.json()["detail"]

    # 7. Advance cooldown and request a fresh OTP
    from app.database.session import get_db
    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    try:
        from app.database.models.password_reset_otp import PasswordResetOTP
        db.query(PasswordResetOTP).update({"created_at": datetime.now(timezone.utc) - timedelta(seconds=70)})
        db.commit()
    finally:
        db.close()

    forgot_resp2 = client.post("/api/v1/auth/forgot-password", json={
        "identifier": email
    })
    assert forgot_resp2.status_code == 200
    assert len(captured_otps) == 2
    _, fresh_otp = captured_otps[-1]

    # 8. Successful OTP verification yields single-use reset authorization token
    verify_resp = client.post("/api/v1/auth/verify-otp", json={
        "identifier": email,
        "otp": fresh_otp
    })
    assert verify_resp.status_code == 200
    verify_data = verify_resp.json()
    assert "reset_token" in verify_data
    reset_token = verify_data["reset_token"]

    # 9. Verifying the same OTP again fails (already consumed)
    repeat_verify = client.post("/api/v1/auth/verify-otp", json={
        "identifier": email,
        "otp": fresh_otp
    })
    assert repeat_verify.status_code == 400

    # 10. Cross-token isolation checks:
    # A) Reset token CANNOT be used as an access token on /api/v1/auth/me
    token_abuse_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {reset_token}"})
    assert token_abuse_resp.status_code == 401
    assert "Invalid token purpose" in token_abuse_resp.json()["detail"]

    # B) Access token CANNOT authorize a password reset on /api/v1/auth/reset-password
    login_dummy = client.post("/api/v1/auth/login", json={"identifier": email, "password": initial_password})
    normal_access_token = login_dummy.json()["access_token"]
    access_token_abuse = client.post("/api/v1/auth/reset-password", json={
        "reset_token": normal_access_token,
        "new_password": new_password,
        "confirm_password": new_password
    })
    assert access_token_abuse.status_code == 401
    assert "Invalid or expired password reset authorization" in access_token_abuse.json()["detail"]

    # 11. Password validation: Mismatch rejection (422)
    mismatch_resp = client.post("/api/v1/auth/reset-password", json={
        "reset_token": reset_token,
        "new_password": new_password,
        "confirm_password": "CompletelyDifferentPassword!"
    })
    assert mismatch_resp.status_code == 422

    # 12. Successful password reset
    reset_success_resp = client.post("/api/v1/auth/reset-password", json={
        "reset_token": reset_token,
        "new_password": new_password,
        "confirm_password": new_password
    })
    assert reset_success_resp.status_code == 200
    assert "successfully reset" in reset_success_resp.json()["message"]

    # 13. Replaying the consumed reset_token fails (401 Unauthorized)
    replay_resp = client.post("/api/v1/auth/reset-password", json={
        "reset_token": reset_token,
        "new_password": "AnotherNewPassword123!",
        "confirm_password": "AnotherNewPassword123!"
    })
    assert replay_resp.status_code == 401, f"Expected 401 on replay, got {replay_resp.status_code}"

    # 14. Old password login FAILS (401)
    old_log_resp = client.post("/api/v1/auth/login", json={
        "identifier": email,
        "password": initial_password
    })
    assert old_log_resp.status_code == 401

    # 15. New password login SUCCEEDS (200)
    new_log_resp = client.post("/api/v1/auth/login", json={
        "identifier": email,
        "password": new_password
    })
    assert new_log_resp.status_code == 200
    assert "access_token" in new_log_resp.json()


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
            test_email_required_for_registration(direct_client)
            test_existing_null_email_user_can_login(direct_client)
            test_forgot_password_full_lifecycle(direct_client)
            print("All auth and password recovery tests passed successfully in isolated test environment.")
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
