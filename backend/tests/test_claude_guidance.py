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


# ── Phase B: Multimodal Image + Transcript Focused Tests ─────────────────────

def test_claude_multimodal_image_and_transcript_same_request(tmp_path):
    """Verify that original plant image block and farmer voice transcript appear together in the same Claude user message."""
    import json
    from app.database.models.tur_voice_report import TurVoiceReport
    import app.services.storage_service as storage_service

    # Create dummy image in a temporary test upload dir
    test_image_dir = tmp_path / "scans"
    test_image_dir.mkdir(parents=True, exist_ok=True)
    dummy_img = test_image_dir / "test_leaf.jpg"
    dummy_img.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"fake_jpeg_leaf_data")

    db = MagicMock()
    scan = mock_scan(scan_id=99, disease_name="Leaf_Spot", confidence=0.85)
    scan.image_path = "scans/test_leaf.jpg"
    scan.image_content_type = "image/jpeg"
    rec = mock_rec(disease_name="Leaf_Spot")

    mock_voice = MagicMock(spec=TurVoiceReport)
    mock_voice.transcription = "पानांवर पिवळे डाग पडले आहेत आणि पाने गळत आहेत"

    db.scalar.side_effect = [rec, mock_voice]

    mock_anthropic = MagicMock()
    mock_response = MagicMock()
    mock_block = MagicMock()
    mock_block.text = json.dumps({
        "disease_explanation": "पानांवरील ठिपके आणि शेतकऱ्याच्या वर्णनानुसार पिवळे डाग स्पष्ट दिसत आहेत.",
        "farmer_action": [
            "Mancozeb 75 WP फवारणी करा.",
            "एकापेक्षा जास्त औषधे एकत्र मिसळण्यापूर्वी उत्पादनाच्या label वरील सूचना किंवा अधिकृत कृषी शिफारस तपासा."
        ]
    })
    mock_response.content = [mock_block]
    mock_anthropic.messages.create.return_value = mock_response

    with patch.object(storage_service, "UPLOAD_DIR", tmp_path), \
         patch.object(settings, "ANTHROPIC_API_KEY", "test_key"), \
         patch("anthropic.Anthropic", return_value=mock_anthropic):
        
        res = generate_claude_guidance(db, scan, language="mr")
        
        assert res.status == "success"
        assert res.spray_guidance_available is True
        assert res.ai_guidance_available is True

        # 1. Exactly one Claude request must occur
        assert mock_anthropic.messages.create.call_count == 1

        # 2. Extract call arguments
        call_kwargs = mock_anthropic.messages.create.call_args[1]
        user_content = call_kwargs["messages"][0]["content"]

        # 3. Must be a multimodal list with both image and text blocks
        assert isinstance(user_content, list)
        assert len(user_content) == 2

        image_block = user_content[0]
        text_block = user_content[1]

        assert image_block["type"] == "image"
        assert image_block["source"]["type"] == "base64"
        assert image_block["source"]["media_type"] == "image/jpeg"
        assert len(image_block["source"]["data"]) > 0

        assert text_block["type"] == "text"
        assert "farmer_spoken_observation" in text_block["text"]
        assert "पानांवर पिवळे डाग पडले आहेत" in text_block["text"]
        assert "Leaf_Spot" in text_block["text"]


def test_claude_image_only_workflow_without_transcript(tmp_path):
    """Verify that when farmer skips voice recording, the image block is still sent with disease data."""
    import json
    import app.services.storage_service as storage_service

    test_image_dir = tmp_path / "scans"
    test_image_dir.mkdir(parents=True, exist_ok=True)
    dummy_img = test_image_dir / "skipped_voice_leaf.png"
    dummy_img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"fake_png_data")

    db = MagicMock()
    scan = mock_scan(scan_id=101, disease_name="Leaf_Spot", confidence=0.88)
    scan.image_path = "scans/skipped_voice_leaf.png"
    scan.image_content_type = "image/png"
    rec = mock_rec(disease_name="Leaf_Spot")

    # Second db.scalar returns None (no voice report for this scan)
    db.scalar.side_effect = [rec, None]

    mock_anthropic = MagicMock()
    mock_response = MagicMock()
    mock_block = MagicMock()
    mock_block.text = json.dumps({
        "disease_explanation": "Detected Leaf Spot on the leaf photo.",
        "farmer_action": [
            "Apply Mancozeb 75 WP.",
            "Before mixing more than one product, check the product label or verified agricultural recommendation."
        ]
    })
    mock_response.content = [mock_block]
    mock_anthropic.messages.create.return_value = mock_response

    with patch.object(storage_service, "UPLOAD_DIR", tmp_path), \
         patch.object(settings, "ANTHROPIC_API_KEY", "test_key"), \
         patch("anthropic.Anthropic", return_value=mock_anthropic):
        
        res = generate_claude_guidance(db, scan, language="en")
        assert res.status == "success"

        call_kwargs = mock_anthropic.messages.create.call_args[1]
        user_content = call_kwargs["messages"][0]["content"]

        assert isinstance(user_content, list)
        assert len(user_content) == 2
        assert user_content[0]["type"] == "image"
        assert user_content[0]["source"]["media_type"] == "image/png"
        assert "farmer_spoken_observation" not in user_content[1]["text"]


def test_claude_missing_image_file_fails_safely():
    """Verify that if the image file is missing on disk, guidance falls back safely without crashing."""
    import json
    db = MagicMock()
    scan = mock_scan(scan_id=102, disease_name="Leaf_Spot", confidence=0.78)
    scan.image_path = "scans/deleted_or_missing.jpg"
    rec = mock_rec(disease_name="Leaf_Spot")
    db.scalar.side_effect = [rec, None]

    mock_anthropic = MagicMock()
    mock_response = MagicMock()
    mock_block = MagicMock()
    mock_block.text = json.dumps({
        "disease_explanation": "Text only analysis of Leaf Spot.",
        "farmer_action": [
            "Action 1",
            "Before mixing more than one product, check the product label or verified agricultural recommendation."
        ]
    })
    mock_response.content = [mock_block]
    mock_anthropic.messages.create.return_value = mock_response

    with patch.object(settings, "ANTHROPIC_API_KEY", "test_key"), \
         patch("anthropic.Anthropic", return_value=mock_anthropic):
        
        res = generate_claude_guidance(db, scan, language="en")
        assert res.status == "success"
        # Warning should be noted in response
        assert any("Scan image file was not found on server disk" in w for w in res.warnings)

        # Call content falls back to text string
        call_kwargs = mock_anthropic.messages.create.call_args[1]
        user_content = call_kwargs["messages"][0]["content"]
        assert isinstance(user_content, str)


def test_claude_unsupported_image_format_rejected(tmp_path):
    """Verify that unsupported image formats (e.g. BMP/TIFF) are rejected and fall back safely."""
    import json
    import app.services.storage_service as storage_service

    test_image_dir = tmp_path / "scans"
    test_image_dir.mkdir(parents=True, exist_ok=True)
    dummy_img = test_image_dir / "unsupported_leaf.bmp"
    dummy_img.write_bytes(b"BM" + b"fake_bmp_data")

    db = MagicMock()
    scan = mock_scan(scan_id=103, disease_name="Leaf_Spot", confidence=0.79)
    scan.image_path = "scans/unsupported_leaf.bmp"
    scan.image_content_type = "image/bmp"
    rec = mock_rec(disease_name="Leaf_Spot")
    db.scalar.side_effect = [rec, None]

    mock_anthropic = MagicMock()
    mock_response = MagicMock()
    mock_block = MagicMock()
    mock_block.text = json.dumps({
        "disease_explanation": "Leaf Spot analysis without unsupported image format.",
        "farmer_action": [
            "Action 1",
            "Before mixing more than one product, check the product label or verified agricultural recommendation."
        ]
    })
    mock_response.content = [mock_block]
    mock_anthropic.messages.create.return_value = mock_response

    with patch.object(storage_service, "UPLOAD_DIR", tmp_path), \
         patch.object(settings, "ANTHROPIC_API_KEY", "test_key"), \
         patch("anthropic.Anthropic", return_value=mock_anthropic):
        
        res = generate_claude_guidance(db, scan, language="en")
        assert res.status == "success"
        assert any("is not supported for cloud multimodal analysis" in w for w in res.warnings)

        call_kwargs = mock_anthropic.messages.create.call_args[1]
        user_content = call_kwargs["messages"][0]["content"]
        assert isinstance(user_content, str)


def test_claude_path_traversal_image_path_rejected():
    """Verify that attempted path traversal in image_path is safely rejected."""
    import json
    db = MagicMock()
    scan = mock_scan(scan_id=104, disease_name="Leaf_Spot", confidence=0.80)
    scan.image_path = "../../../etc/shadow"
    rec = mock_rec(disease_name="Leaf_Spot")
    db.scalar.side_effect = [rec, None]

    mock_anthropic = MagicMock()
    mock_response = MagicMock()
    mock_block = MagicMock()
    mock_block.text = json.dumps({
        "disease_explanation": "Safe analysis.",
        "farmer_action": [
            "Action 1",
            "Before mixing more than one product, check the product label or verified agricultural recommendation."
        ]
    })
    mock_response.content = [mock_block]
    mock_anthropic.messages.create.return_value = mock_response

    with patch.object(settings, "ANTHROPIC_API_KEY", "test_key"), \
         patch("anthropic.Anthropic", return_value=mock_anthropic):
        
        res = generate_claude_guidance(db, scan, language="en")
        assert res.status == "success"
        assert any("rejected by security guard" in w for w in res.warnings)


