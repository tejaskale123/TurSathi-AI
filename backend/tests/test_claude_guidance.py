import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.database.models.tur_scan import TurScan
from app.database.models.tur_disease_recommendation import TurDiseaseRecommendation
from app.schemas.claude_guidance import ClaudeGuidanceResponse
from app.services.claude_guidance_service import generate_claude_guidance


# ── Mock Fixtures ─────────────────────────────────────────────────────────────

def mock_scan(scan_id=1, user_id=1, disease_name="Leaf_Spot", confidence=0.75, status="completed"):
    scan = MagicMock(spec=TurScan)
    scan.id = scan_id
    scan.user_id = user_id
    scan.crop = "tur"
    scan.disease_name = disease_name
    scan.confidence = confidence
    scan.severity = "moderate"
    scan.prediction_status = status
    return scan


def mock_rec(disease_name="Leaf_Spot"):
    rec = MagicMock(spec=TurDiseaseRecommendation)
    rec.crop = "tur"
    rec.disease_name = disease_name
    rec.disease_description = "Leaf spot disease affecting Tur leaves."
    rec.treatment = "Mancozeb 75 WP"
    rec.active_ingredient = "Mancozeb 75% WP"
    rec.recommended_quantity = "2.5 g/L of water"
    rec.water_quantity = None
    rec.per_pump_quantity = None
    rec.spray_timing = "At onset of disease"
    rec.application_method = "Foliar spray"
    rec.safety_precautions = "Wear protective gear"
    rec.after_spray_advisory = "Monitor crop"
    rec.is_active = True
    return rec


# ── 1. Missing Anthropic API Key Test ─────────────────────────────────────────

def test_missing_anthropic_api_key():
    db = MagicMock()
    scan = mock_scan(confidence=0.70)
    rec = mock_rec()
    db.scalar.return_value = rec

    with patch.object(settings, "ANTHROPIC_API_KEY", None):
        res = generate_claude_guidance(db, scan, language="en")
        assert res.status == "fallback"
        assert res.spray_guidance_available is True
        assert res.ai_guidance_available is False
        assert res.spray_guidance is not None
        assert res.spray_guidance.treatment == "Mancozeb 75 WP"
        assert res.spray_guidance.water_quantity is None


# ── 2. Claude Service Initialization Test ─────────────────────────────────────

def test_claude_service_initialization():
    db = MagicMock()
    scan = mock_scan(confidence=0.75)
    rec = mock_rec()
    db.scalar.return_value = rec

    mock_claude_response = MagicMock()
    mock_block = MagicMock()
    mock_block.text = '{"disease_explanation": "Test explanation", "farmer_action": ["Step 1", "Step 2"]}'
    mock_claude_response.content = [mock_block]

    with patch.object(settings, "ANTHROPIC_API_KEY", "test-key-123"):
        with patch("anthropic.Anthropic") as MockAnthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_claude_response
            MockAnthropic.return_value = mock_client

            res = generate_claude_guidance(db, scan, language="en")
            MockAnthropic.assert_called_once_with(api_key="test-key-123")
            assert res.status == "success"
            assert res.disease_explanation == "Test explanation"


# ── 3. Leaf_Spot Confidence >= 60% Test ───────────────────────────────────────

def test_leaf_spot_confidence_gte_60():
    db = MagicMock()
    scan = mock_scan(disease_name="Leaf_Spot", confidence=0.65)
    rec = mock_rec()
    db.scalar.return_value = rec

    with patch.object(settings, "ANTHROPIC_API_KEY", None):
        res = generate_claude_guidance(db, scan, language="en")
        assert res.confidence == 0.65
        assert res.confidence_percent == 65
        assert res.spray_guidance_available is True
        assert res.spray_guidance.treatment == "Mancozeb 75 WP"


# ── 4. Leaf_Spot Confidence < 60% Test ────────────────────────────────────────

def test_leaf_spot_confidence_lt_60():
    db = MagicMock()
    scan = mock_scan(disease_name="Leaf_Spot", confidence=0.349)

    res = generate_claude_guidance(db, scan, language="en")
    assert res.status == "low_confidence"
    assert res.confidence == 0.349
    assert res.confidence_percent == 35
    assert res.spray_guidance_available is False
    assert res.spray_guidance is None
    assert "below 60%" in res.disease_explanation


# ── 5. Healthy Prediction Test ────────────────────────────────────────────────

def test_healthy_prediction():
    db = MagicMock()
    scan = mock_scan(disease_name="Healthy", confidence=0.95)

    res = generate_claude_guidance(db, scan, language="en")
    assert res.status == "success"
    assert res.disease_name == "Healthy"
    assert res.spray_guidance_available is False
    assert res.spray_guidance is None
    assert "healthy" in res.disease_explanation.lower()


# ── 6. Missing Recommendation Test ────────────────────────────────────────────

def test_missing_recommendation():
    db = MagicMock()
    scan = mock_scan(disease_name="Unknown_Disease", confidence=0.80)
    db.scalar.return_value = None

    res = generate_claude_guidance(db, scan, language="en")
    assert res.status == "fallback"
    assert res.spray_guidance_available is False
    assert res.spray_guidance is None


# ── 7. Claude API Failure Test ────────────────────────────────────────────────

def test_claude_api_failure():
    db = MagicMock()
    scan = mock_scan(confidence=0.75)
    rec = mock_rec()
    db.scalar.return_value = rec

    with patch.object(settings, "ANTHROPIC_API_KEY", "test-key"):
        with patch("anthropic.Anthropic") as MockAnthropic:
            mock_client = MagicMock()
            mock_client.messages.create.side_effect = Exception("API connection error")
            MockAnthropic.return_value = mock_client

            res = generate_claude_guidance(db, scan, language="en")
            assert res.status == "fallback"
            assert res.spray_guidance_available is True
            assert res.spray_guidance.treatment == "Mancozeb 75 WP"


# ── 8. Invalid Claude Response Test ───────────────────────────────────────────

def test_invalid_claude_response():
    db = MagicMock()
    scan = mock_scan(confidence=0.75)
    rec = mock_rec()
    db.scalar.return_value = rec

    mock_claude_response = MagicMock()
    mock_block = MagicMock()
    mock_block.text = "NOT_JSON_RESPONSE"
    mock_claude_response.content = [mock_block]

    with patch.object(settings, "ANTHROPIC_API_KEY", "test-key"):
        with patch("anthropic.Anthropic") as MockAnthropic:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_claude_response
            MockAnthropic.return_value = mock_client

            res = generate_claude_guidance(db, scan, language="en")
            assert res.status == "fallback"
            assert res.spray_guidance_available is True


# ── 9 & 10 & 11 API Endpoint Tests ────────────────────────────────────────────

def test_unauthorized_request():
    client = TestClient(app)
    res = client.post("/api/v1/predictions/tur-leaf/1/ai-guidance", headers={"Authorization": "Bearer invalid_token"})
    assert res.status_code == 401


def test_authenticated_ai_guidance_request():
    client = TestClient(app)
    mock_user = MagicMock()
    mock_user.id = 1
    mock_scan_obj = mock_scan(scan_id=1, user_id=1, confidence=0.70)
    mock_scan_obj.prediction_status = "completed"

    from app.api.v1.auth import get_current_user
    from app.database.session import get_db

    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        with patch("app.api.v1.predictions.get_scan_for_user", return_value=mock_scan_obj):
            with patch.object(settings, "ANTHROPIC_API_KEY", None):
                res = client.post(
                    "/api/v1/predictions/tur-leaf/1/ai-guidance",
                    headers={"Authorization": "Bearer fake_token"}
                )
                assert res.status_code == 200
                data = res.json()
                assert data["crop"] == "tur"
                assert "status" in data
    finally:
        app.dependency_overrides.clear()


# ── 12, 13, 14. Multilingual Language Tests ───────────────────────────────────

def test_english_language():
    db = MagicMock()
    scan = mock_scan(confidence=0.30)
    res = generate_claude_guidance(db, scan, language="en")
    assert res.language == "en"
    assert "confidence is below 60%" in res.disease_explanation


def test_marathi_language():
    db = MagicMock()
    scan = mock_scan(confidence=0.30)
    res = generate_claude_guidance(db, scan, language="mr")
    assert res.language == "mr"
    assert "६०%" in res.disease_explanation


def test_hindi_language():
    db = MagicMock()
    scan = mock_scan(confidence=0.30)
    res = generate_claude_guidance(db, scan, language="hi")
    assert res.language == "hi"
    assert "60%" in res.disease_explanation


# ── 15 & 16 Existing Endpoints Integrity Tests ────────────────────────────────

def test_existing_prediction_endpoint_integrity():
    client = TestClient(app)
    mock_user = MagicMock()
    mock_user.id = 1
    mock_scan_obj = mock_scan(scan_id=1, user_id=1, confidence=0.90)

    from app.api.v1.auth import get_current_user
    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        with patch("app.api.v1.predictions.run_prediction", return_value=mock_scan_obj):
            res = client.post(
                "/api/v1/predictions/tur-leaf/1",
                headers={"Authorization": "Bearer fake_token"}
            )
            assert res.status_code == 200
            data = res.json()
            assert data["scan_id"] == 1
            assert data["crop"] == "tur"
    finally:
        app.dependency_overrides.clear()


def test_existing_recommendation_endpoint_integrity():
    client = TestClient(app)
    mock_user = MagicMock()
    mock_user.id = 1

    from app.api.v1.auth import get_current_user
    from app.database.session import get_db

    mock_db = MagicMock()
    mock_rec_obj = mock_rec(disease_name="Leaf_Spot")
    mock_db.scalar.return_value = mock_rec_obj

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db
    try:
        res = client.get(
            "/api/v1/recommendations/tur/Leaf_Spot/spray-guidance",
            headers={"Authorization": "Bearer fake_token"}
        )
        assert res.status_code in (200, 404)
    finally:

        app.dependency_overrides.clear()


def test_leaf_webber_safety_disabled_spray_guidance():
    """Leaf Webber must not output chemical spray recommendations or dosages."""
    db = MagicMock()
    scan = mock_scan(disease_name="Leaf_webber", confidence=0.88)
    res_en = generate_claude_guidance(db, scan, language="en")
    assert res_en.status == "unverified"
    assert res_en.spray_guidance_available is False
    assert res_en.spray_guidance is None
    assert "Grapholita critica" in res_en.disease_explanation

    res_mr = generate_claude_guidance(db, scan, language="mr")
    assert res_mr.status == "unverified"
    assert res_mr.spray_guidance_available is False
    assert res_mr.spray_guidance is None
    assert "पाने गुंडाळणारी आळी" in res_mr.disease_explanation


def test_leaf_webber_recommendation_endpoint_returns_404():
    """GET /api/v1/recommendations/tur/Leaf_webber/spray-guidance must return 404 to avoid leaking banned chemicals."""
    client = TestClient(app)
    mock_user = MagicMock()
    mock_user.id = 1

    from app.api.v1.auth import get_current_user
    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        res = client.get(
            "/api/v1/recommendations/tur/Leaf_webber/spray-guidance",
            headers={"Authorization": "Bearer fake_token"}
        )
        assert res.status_code == 404
        assert "Verified spray guidance is not available" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_claude_guidance_with_farmer_voice_transcription():
    """Verify that farmer voice transcription is retrieved from TurVoiceReport and passed into Claude prompt."""
    import json
    from app.database.models.tur_voice_report import TurVoiceReport

    db = MagicMock()
    scan = mock_scan(scan_id=42, disease_name="Leaf_Spot", confidence=0.82)
    rec = mock_rec(disease_name="Leaf_Spot")

    mock_voice = MagicMock(spec=TurVoiceReport)
    mock_voice.transcription = "पानांवर काळे डाग पडले आहेत आणि झाड सुकत चालले आहे"

    # db.scalar returns rec on first call, mock_voice on second call
    db.scalar.side_effect = [rec, mock_voice]

    mock_anthropic = MagicMock()
    mock_response = MagicMock()
    mock_block = MagicMock()
    mock_block.text = json.dumps({
        "disease_explanation": "तुरीच्या पानांवर ठिपके रोग आढळला असून शेतकऱ्याने सांगितल्याप्रमाणे काळे डाग दिसत आहेत.",
        "farmer_action": [
            "Mancozeb 75 WP ची फवारणी करा.",
            "एकापेक्षा जास्त औषधे एकत्र मिसळण्यापूर्वी उत्पादनाच्या label वरील सूचना किंवा अधिकृत कृषी शिफारस तपासा."
        ]
    })
    mock_response.content = [mock_block]
    mock_anthropic.messages.create.return_value = mock_response

    with patch.object(settings, "ANTHROPIC_API_KEY", "test_key"), \
         patch("anthropic.Anthropic", return_value=mock_anthropic):
        res = generate_claude_guidance(db, scan, language="mr")
        assert res.status == "success"
        assert "काळे डाग" in res.disease_explanation

        # Verify Claude messages.create received farmer observation
        call_kwargs = mock_anthropic.messages.create.call_args[1]
        user_message_content = call_kwargs["messages"][0]["content"]
        assert "farmer_spoken_observation" in user_message_content
        assert "पानांवर काळे डाग पडले आहेत" in user_message_content

