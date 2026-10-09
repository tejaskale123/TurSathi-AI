import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database.session import get_db
from app.database.base import Base
from app.database.models.user import User
from app.database.models.tur_scan import TurScan
from app.api.v1.auth import get_current_user

# Setup isolated test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_staging.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

def override_get_current_user():
    db = TestingSessionLocal()
    user = db.query(User).filter(User.id == 1).first()
    db.close()
    return user

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # Create test user
    db.add(User(id=1, email="test@test.com", full_name="Test User"))
    
    # Create mock scan for Tur
    tur_scan = TurScan(id=1, user_id=1, image_path="fake_tur.jpg", crop="tur", status="received")
    
    # Create mock scan for Not_Tur
    nottur_scan = TurScan(id=2, user_id=1, image_path="fake_nottur.jpg", crop="tur", status="received")
    
    db.add(tur_scan)
    db.add(nottur_scan)
    db.commit()
    yield
    db.close()

@patch("app.services.prediction_service.get_tur_image_gate")
@patch("app.services.prediction_service.get_predictor")
@patch("app.services.prediction_service.UPLOAD_DIR", Path("."))
def test_staging_tur_image(mock_get_predictor, mock_get_gate):
    # Mock Gate: Valid Tur
    mock_gate = MagicMock()
    mock_gate_result = MagicMock()
    mock_gate_result.is_valid_tur = True
    mock_gate_result.label = "Tur"
    mock_gate.validate.return_value = mock_gate_result
    mock_get_gate.return_value = mock_gate
    
    # Mock Predictor: Disease
    mock_predictor = MagicMock()
    mock_pred_result = MagicMock()
    mock_pred_result.disease_name = "Wilt"
    mock_pred_result.confidence = 0.95
    mock_pred_result.severity = "high"
    mock_predictor.predict.return_value = mock_pred_result
    mock_get_predictor.return_value = mock_predictor
    
    # Run API
    response = client.post("/api/v1/predictions/tur-leaf/1")
    
    assert response.status_code == 200
    data = response.json()
    assert data["disease_name"] == "Wilt"
    assert data["status"] == "completed"
    
    # Verify disease predictor WAS called
    mock_predictor.predict.assert_called_once()

@patch("app.services.prediction_service.get_tur_image_gate")
@patch("app.services.prediction_service.get_predictor")
@patch("app.services.prediction_service.UPLOAD_DIR", Path("."))
def test_staging_not_tur_image(mock_get_predictor, mock_get_gate):
    # Mock Gate: Not_Tur
    mock_gate = MagicMock()
    mock_gate_result = MagicMock()
    mock_gate_result.is_valid_tur = False
    mock_gate_result.label = "Not_Tur"
    mock_gate_result.reason = "validator_confident_not_tur"
    mock_gate_result.message = "This image does not appear to be a valid Tur (Pigeonpea) leaf."
    mock_gate.validate.return_value = mock_gate_result
    mock_get_gate.return_value = mock_gate
    
    # Mock Predictor: Disease (Should NOT be called)
    mock_predictor = MagicMock()
    mock_get_predictor.return_value = mock_predictor
    
    # Run API
    response = client.post("/api/v1/predictions/tur-leaf/2")
    
    assert response.status_code == 422
    data = response.json()
    assert data["detail"]["status"] == "validation_failed"
    
    # Verify disease predictor WAS NOT called
    mock_predictor.predict.assert_not_called()
    
    # Verify DB state updated to rejected
    db = TestingSessionLocal()
    scan = db.query(TurScan).filter(TurScan.id == 2).first()
    assert scan.prediction_status == "rejected"
    assert scan.status == "rejected"
    db.close()
