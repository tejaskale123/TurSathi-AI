import sys
from pathlib import Path
from unittest.mock import patch

# Ensure backend directory is in sys.path
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
from app.database.models.user import User
from app.database.models.login_history import LoginHistory
from app.database.session import get_db
from app.core.security import get_password_hash, create_access_token
from app.services.auth_service import authenticate_google_user


@pytest.fixture(scope="function")
def isolated_client():
    """
    Isolated in-memory SQLite fixture.
    Guarantees zero connections or writes to PostgreSQL or remote servers.
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
        with TestClient(app) as client:
            yield client, TestingSessionLocal
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_login_success_records_history(isolated_client):
    """
    Valid local password login must:
    1. Return HTTP 200 with JWT access token.
    2. Persist a LoginHistory record with status='success', correct user_id, method='local_password'.
    3. Safely record sanitized IP and User-Agent.
    """
    client, SessionMaker = isolated_client

    # Seed active user
    db = SessionMaker()
    raw_password = "FarmerSecretPassword99!"
    user = User(
        full_name="Santosh Patil",
        mobile_number="9876543210",
        email="santosh.patil@example.com",
        password_hash=get_password_hash(raw_password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    user_id = user.id
    db.close()

    # Perform login
    headers = {
        "User-Agent": "TurSathi-Mobile-App/1.0.0 (Android)",
    }
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": "9876543210", "password": raw_password},
        headers=headers,
    )
    assert response.status_code == 200, f"Expected 200, got: {response.text}"
    token_data = response.json()
    assert "access_token" in token_data

    # Verify audit record
    db_check = SessionMaker()
    records = db_check.query(LoginHistory).all()
    assert len(records) == 1
    record = records[0]
    assert record.user_id == user_id
    assert record.login_method == "local_password"
    assert record.status == "success"
    assert record.failure_reason is None
    assert record.user_agent == "TurSathi-Mobile-App/1.0.0 (Android)"
    assert record.login_at is not None
    db_check.close()


def test_login_wrong_password_records_history(isolated_client):
    """
    Incorrect password attempt must:
    1. Return HTTP 401 with generic error.
    2. Persist LoginHistory with status='failed', failure_reason='invalid_credentials'.
    3. User_id is recorded since the user account was identified.
    4. Password must NEVER be persisted in the audit record.
    """
    client, SessionMaker = isolated_client

    db = SessionMaker()
    user = User(
        full_name="Kavita Shinde",
        mobile_number="9876500001",
        email="kavita@example.com",
        password_hash=get_password_hash("CorrectPassword1!"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    user_id = user.id
    db.close()

    # Attempt login with incorrect password
    bad_password = "WrongAttackerPassword!"
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": "kavita@example.com", "password": bad_password},
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0)"},
    )
    assert response.status_code == 401
    assert "access_token" not in response.json()

    # Verify audit record
    db_check = SessionMaker()
    records = db_check.query(LoginHistory).all()
    assert len(records) == 1
    record = records[0]
    assert record.user_id == user_id
    assert record.login_method == "local_password"
    assert record.status == "failed"
    assert record.failure_reason == "invalid_credentials"
    assert bad_password not in (record.failure_reason or "")
    db_check.close()


def test_login_unknown_user_records_history_with_null_user_id(isolated_client):
    """
    Non-existent account attempt must:
    1. Return HTTP 401.
    2. Persist LoginHistory with status='failed', failure_reason='invalid_credentials'.
    3. user_id must be NULL (no account matches).
    4. The submitted identifier must NEVER be stored.
    """
    client, SessionMaker = isolated_client

    unknown_identifier = "nonexistent_9999999999@example.com"
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": unknown_identifier, "password": "AnyPassword123!"},
    )
    assert response.status_code == 401

    db_check = SessionMaker()
    records = db_check.query(LoginHistory).all()
    assert len(records) == 1
    record = records[0]
    assert record.user_id is None  # Nullable for unidentifiable accounts
    assert record.login_method == "local_password"
    assert record.status == "failed"
    assert record.failure_reason == "invalid_credentials"
    # Verify submitted identifier is not saved in failure_reason or anywhere
    assert unknown_identifier not in (record.failure_reason or "")
    db_check.close()


def test_login_inactive_user_records_history(isolated_client):
    """
    Inactive account attempt must:
    1. Return HTTP 400.
    2. Persist LoginHistory with status='failed', failure_reason='account_inactive'.
    3. user_id is linked to the inactive account.
    """
    client, SessionMaker = isolated_client

    db = SessionMaker()
    user = User(
        full_name="Deactivated Farmer",
        mobile_number="9876500002",
        email="inactive@example.com",
        password_hash=get_password_hash("Password123!"),
        is_active=False,
    )
    db.add(user)
    db.commit()
    user_id = user.id
    db.close()

    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": "9876500002", "password": "Password123!"},
    )
    assert response.status_code == 400
    assert "inactive" in response.json().get("detail", "").lower()

    db_check = SessionMaker()
    records = db_check.query(LoginHistory).all()
    assert len(records) == 1
    record = records[0]
    assert record.user_id == user_id
    assert record.login_method == "local_password"
    assert record.status == "failed"
    assert record.failure_reason == "account_inactive"
    db_check.close()


def test_google_oauth_success_and_failure_records_history(isolated_client):
    """
    Google OAuth tracking paths:
    1. authenticate_google_user with new user records success.
    2. authenticate_google_user with inactive user records failure.
    3. google_exchange with invalid exchange code records failure with null user_id.
    """
    client, SessionMaker = isolated_client
    db = SessionMaker()

    # 1. Successful Google user authentication
    google_user = authenticate_google_user(
        db=db,
        google_id="google_sub_101",
        email="farmer.google@example.com",
        name="Google Farmer",
        ip_address="192.168.1.100",
        user_agent="TurSathi-OAuth-Client",
    )
    assert google_user.id is not None

    records = db.query(LoginHistory).filter(LoginHistory.user_id == google_user.id).all()
    assert len(records) == 1
    assert records[0].login_method == "google_oauth"
    assert records[0].status == "success"
    assert records[0].failure_reason is None
    assert records[0].ip_address == "192.168.1.100"

    # 2. Inactive Google user authentication failure
    google_user.is_active = False
    db.commit()

    with pytest.raises(Exception):
        authenticate_google_user(
            db=db,
            google_id="google_sub_101",
            email="farmer.google@example.com",
            name="Google Farmer",
        )

    records_inactive = db.query(LoginHistory).filter(
        LoginHistory.user_id == google_user.id,
        LoginHistory.status == "failed"
    ).all()
    assert len(records_inactive) == 1
    assert records_inactive[0].failure_reason == "account_inactive"

    # 3. Google exchange with forged/expired code
    response = client.post(
        "/api/v1/auth/google/exchange",
        json={"exchange_code": "forged_non_jwt_code"},
    )
    assert response.status_code == 401

    records_exchange = db.query(LoginHistory).filter(
        LoginHistory.failure_reason == "invalid_exchange_code"
    ).all()
    assert len(records_exchange) == 1
    assert records_exchange[0].user_id is None
    assert records_exchange[0].status == "failed"
    db.close()


def test_audit_logging_failure_does_not_break_login(isolated_client):
    """
    Guarantees fault-tolerance:
    If the database fails while inserting a LoginHistory record (e.g., table locked, disk full),
    the user's login MUST STILL SUCCEED and return an access token.
    The authentication workflow must not be disrupted by audit logging failures.
    """
    client, SessionMaker = isolated_client

    db = SessionMaker()
    user = User(
        full_name="Resilience Test Farmer",
        mobile_number="9876500003",
        email="resilience@example.com",
        password_hash=get_password_hash("ValidPass123!"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.close()

    # Simulate an error inside record_login_attempt by patching LoginHistory creation
    with patch("app.services.auth_service.LoginHistory", side_effect=RuntimeError("Simulated DB Write Error")):
        response = client.post(
            "/api/v1/auth/login",
            json={"identifier": "9876500003", "password": "ValidPass123!"},
        )
        # Authentication MUST still succeed with HTTP 200 and return a valid token
        assert response.status_code == 200, f"Login failed when audit logging errored: {response.text}"
        assert "access_token" in response.json()


def test_audit_logging_never_persists_secrets_or_raw_identifiers(isolated_client):
    """
    Privacy & Zero-Leakage Audit:
    Verify that across multiple attempts, no password, password hash, OTP, or raw identifier
    is stored anywhere in the login_history table.
    """
    client, SessionMaker = isolated_client

    secret_password = "SuperSecretPasswordDoNotLeak999!"
    sensitive_identifier = "secret_farmer_account@example.com"

    db = SessionMaker()
    user = User(
        full_name="Audit Farmer",
        mobile_number="9876500004",
        email=sensitive_identifier,
        password_hash=get_password_hash(secret_password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.close()

    # 1. Login success
    client.post("/api/v1/auth/login", json={"identifier": sensitive_identifier, "password": secret_password})

    # 2. Login failure with wrong password
    client.post("/api/v1/auth/login", json={"identifier": sensitive_identifier, "password": "TypoInPassword!"})

    # 3. Login failure with unknown user
    client.post("/api/v1/auth/login", json={"identifier": "unknown_intruder@example.com", "password": "IntruderPassword!"})

    # Verify all records
    db_check = SessionMaker()
    all_records = db_check.query(LoginHistory).all()
    assert len(all_records) == 3

    forbidden_strings = [
        secret_password,
        "TypoInPassword!",
        "IntruderPassword!",
        sensitive_identifier,
        "unknown_intruder@example.com",
    ]

    for rec in all_records:
        for forbidden in forbidden_strings:
            assert forbidden not in (rec.login_method or ""), f"Leaked {forbidden} in login_method"
            assert forbidden not in (rec.status or ""), f"Leaked {forbidden} in status"
            assert forbidden not in (rec.failure_reason or ""), f"Leaked {forbidden} in failure_reason"
            assert forbidden not in (rec.ip_address or ""), f"Leaked {forbidden} in ip_address"
            assert forbidden not in (rec.user_agent or ""), f"Leaked {forbidden} in user_agent"

    db_check.close()
