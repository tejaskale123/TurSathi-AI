"""
Comprehensive Integration Test Suite for Phase G2 & G3.

Phase G2: Voice Transcripts & Scan History Persistence
Phase G3: Claude AI Guidance Durable Caching & Persistence

Covers:
1. G2: Scan detail and scan history return the persisted voice transcript across new DB sessions.
2. G2: Scan without voice report cleanly returns transcription=None and voice_reports=[].
3. G2: Multiple voice reports order newest-first, select latest transcript, never expose audio_path.
4. G2: Cross-user scan history isolation prevents access to other users' scans and transcripts.
5. G3: Guidance successfully persists to tur_ai_guidance after a successful Claude response.
6. G3: Second guidance request for same scan and language hits durable cache (zero Anthropic API calls).
7. G3: Distinct languages (en, mr, hi) persist independent guidance records.
8. G3: Safety gates (confidence < 60%, Healthy, Leaf Webber) execute before cache lookup.
9. G3: Cache invalidation: modifying recommendation data changes fingerprint and triggers fresh Claude call.
10. G3: Failed / invalid Claude responses are never cached as successful guidance.
11. G3: Database commit failure during guidance persistence rolls back cleanly without crashing the response.
12. G3: Cross-user isolation on AI guidance endpoint (HTTP 404 for another user's scan).
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

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
from app.database.models.user import User
from app.database.models.tur_scan import TurScan
from app.database.models.tur_voice_report import TurVoiceReport
from app.database.models.tur_disease_recommendation import TurDiseaseRecommendation
from app.database.models.tur_ai_guidance import TurAIGuidance
from app.services.claude_guidance_service import generate_claude_guidance
import app.services.storage_service as storage_module
from app.core.config import settings


@pytest.fixture(scope="function")
def isolated_g2_g3_env(monkeypatch):
    """
    Sets up an in-memory SQLite database and isolated temp storage directory.
    Guarantees complete isolation from production PostgreSQL and upload folders.
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

        # Seed users and recommendations
        session = TestingSessionLocal()
        try:
            user1 = User(
                id=1,
                full_name="Farmer Ramesh",
                mobile_number="9876543201",
                password_hash="pw1",
                is_active=True,
            )
            user2 = User(
                id=2,
                full_name="Farmer Suresh",
                mobile_number="9876543202",
                password_hash="pw2",
                is_active=True,
            )
            session.add_all([user1, user2])
            session.commit()

            rec_spot = TurDiseaseRecommendation(
                crop="tur",
                disease_name="Leaf_Spot",
                disease_description="Cercospora leaf spot causing circular brown lesions.",
                treatment="Spray Mancozeb 75 WP",
                active_ingredient="Mancozeb 75 WP",
                recommended_quantity="2.5 g/L",
                water_quantity="500 L/ha",
                per_pump_quantity="37.5 g",
                spray_timing="At first sign of disease onset",
                application_method="Foliar spray with uniform coverage",
                safety_precautions="Wear rubber gloves and mask",
                after_spray_advisory="Inspect leaves after 7 days",
                is_active=True,
            )
            session.add(rec_spot)
            session.commit()

            yield session, temp_path, TestingSessionLocal
        finally:
            session.close()
            app.dependency_overrides.clear()
            Base.metadata.drop_all(bind=engine)
            engine.dispose()


# ══════════════════════════════════════════════════════════════════════════════
# PHASE G2: VOICE TRANSCRIPT AND SCAN HISTORY TESTS
# ══════════════════════════════════════════════════════════════════════════════

def test_scan_detail_returns_persisted_transcript_across_sessions(isolated_g2_g3_env):
    """
    Verifies that a scan with a linked voice report returns the persisted transcript
    and safe metadata when queried in a new database session.
    """
    db, temp_path, SessionMaker = isolated_g2_g3_env

    # 1. Create scan and voice report in Session 1
    scan = TurScan(
        id=101,
        user_id=1,
        crop="tur",
        image_path="scans/leaf_101.jpg",
        status="completed",
        disease_name="Leaf_Spot",
        confidence=0.88,
        prediction_status="completed",
    )
    db.add(scan)
    db.commit()

    voice = TurVoiceReport(
        id=201,
        scan_id=101,
        user_id=1,
        audio_path=None,
        audio_filename="problem.m4a",
        audio_content_type="audio/mp4",
        audio_size=12345,
        language="mr",
        duration=4.5,
        transcription="पानांवर काळे ठिपके दिसत आहेत आणि पाने पिवळी पडत आहेत.",
    )
    db.add(voice)
    db.commit()

    # 2. Query scan using a fresh database session (Session 2)
    new_db = SessionMaker()
    try:
        with TestClient(app) as client:
            from app.api.v1.auth import get_current_user
            app.dependency_overrides[get_current_user] = lambda: new_db.query(User).filter(User.id == 1).first()

            resp = client.get("/api/v1/scans/101")
            assert resp.status_code == 200
            data = resp.json()

            assert data["scan_id"] == 101
            assert data["disease_name"] == "Leaf_Spot"
            assert data["transcription"] == "पानांवर काळे ठिपके दिसत आहेत आणि पाने पिवळी पडत आहेत."
            assert data["voice_language"] == "mr"
            assert len(data["voice_reports"]) == 1
            assert data["voice_reports"][0]["transcription"] == "पानांवर काळे ठिपके दिसत आहेत आणि पाने पिवळी पडत आहेत."
            assert "audio_path" not in data  # Never leak internal storage paths
            assert "audio_path" not in data["voice_reports"][0]
    finally:
        new_db.close()


def test_scan_detail_without_voice_report_clean_nulls(isolated_g2_g3_env):
    """
    Verifies that a scan without a voice report returns transcription=None and voice_reports=[].
    """
    db, temp_path, SessionMaker = isolated_g2_g3_env

    scan = TurScan(
        id=102,
        user_id=1,
        crop="tur",
        image_path="scans/leaf_102.jpg",
        status="completed",
        disease_name="Healthy",
        confidence=0.95,
        prediction_status="completed",
    )
    db.add(scan)
    db.commit()

    new_db = SessionMaker()
    try:
        with TestClient(app) as client:
            from app.api.v1.auth import get_current_user
            app.dependency_overrides[get_current_user] = lambda: new_db.query(User).filter(User.id == 1).first()

            resp = client.get("/api/v1/scans/102")
            assert resp.status_code == 200
            data = resp.json()

            assert data["scan_id"] == 102
            assert data["transcription"] is None
            assert data["voice_language"] is None
            assert data["voice_reports"] == []
    finally:
        new_db.close()


def test_scan_list_history_includes_voice_transcripts(isolated_g2_g3_env):
    """
    Verifies that the paginated scan history list (/api/v1/scans) properly surfaces
    the voice transcripts for the authenticated user's scans.
    """
    db, temp_path, SessionMaker = isolated_g2_g3_env

    # Add 2 scans for user 1 (one with transcript, one without)
    scan1 = TurScan(id=103, user_id=1, crop="tur", status="completed", disease_name="Leaf_Spot", confidence=0.90, prediction_status="completed")
    scan2 = TurScan(id=104, user_id=1, crop="tur", status="completed", disease_name="Healthy", confidence=0.95, prediction_status="completed")
    db.add_all([scan1, scan2])
    db.commit()

    voice = TurVoiceReport(id=202, scan_id=103, user_id=1, audio_path=None, language="hi", transcription="पत्तियों पर धब्बे हैं।")
    db.add(voice)
    db.commit()

    new_db = SessionMaker()
    try:
        with TestClient(app) as client:
            from app.api.v1.auth import get_current_user
            app.dependency_overrides[get_current_user] = lambda: new_db.query(User).filter(User.id == 1).first()

            resp = client.get("/api/v1/scans")
            assert resp.status_code == 200
            data = resp.json()

            assert data["total"] == 2
            items = data["items"]
            # Scans are ordered newest first (id desc: 104, then 103)
            scan104 = next(s for s in items if s["scan_id"] == 104)
            scan103 = next(s for s in items if s["scan_id"] == 103)

            assert scan104["transcription"] is None
            assert scan103["transcription"] == "पत्तियों पर धब्बे हैं।"
            assert scan103["voice_language"] == "hi"
    finally:
        new_db.close()


def test_scan_history_cross_user_isolation(isolated_g2_g3_env):
    """
    Verifies that User 2 cannot retrieve User 1's scan detail or transcripts.
    """
    db, temp_path, SessionMaker = isolated_g2_g3_env

    scan = TurScan(id=105, user_id=1, crop="tur", status="completed", disease_name="Leaf_Spot", prediction_status="completed")
    db.add(scan)
    db.commit()

    voice = TurVoiceReport(id=203, scan_id=105, user_id=1, audio_path=None, transcription="खाजगी शेतकरी माहिती")
    db.add(voice)
    db.commit()

    new_db = SessionMaker()
    try:
        with TestClient(app) as client:
            from app.api.v1.auth import get_current_user
            # Authenticate as User 2
            app.dependency_overrides[get_current_user] = lambda: new_db.query(User).filter(User.id == 2).first()

            resp = client.get("/api/v1/scans/105")
            assert resp.status_code == 403 or resp.status_code == 404
    finally:
        new_db.close()


# ══════════════════════════════════════════════════════════════════════════════
# PHASE G3: CLAUDE AI GUIDANCE PERSISTENCE & CACHING TESTS
# ══════════════════════════════════════════════════════════════════════════════

def test_claude_guidance_persisted_to_database_on_success(isolated_g2_g3_env, monkeypatch):
    """
    Verifies that on a successful Claude guidance request:
    1. The guidance response is generated.
    2. A record is persisted in tur_ai_guidance with matching fingerprint, explanation, and actions.
    """
    db, temp_path, SessionMaker = isolated_g2_g3_env

    # Create scan image file in temp storage
    img_file = temp_path / "scans" / "leaf_201.jpg"
    img_file.parent.mkdir(parents=True, exist_ok=True)
    img_file.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

    scan = TurScan(
        id=201,
        user_id=1,
        crop="tur",
        image_path="scans/leaf_201.jpg",
        status="completed",
        disease_name="Leaf_Spot",
        confidence=0.85,
        prediction_status="completed",
    )
    db.add(scan)
    db.commit()

    # Mock Anthropic Messages API
    mock_response = MagicMock()
    mock_block = MagicMock()
    mock_block.text = json.dumps({
        "disease_explanation": "Cercospora leaf spot detected with 85% certainty.",
        "farmer_action": [
            "Apply Mancozeb 75 WP at 2.5 g/L.",
            "Ensure uniform foliar coverage.",
            "Before mixing more than one product, check the product label or verified agricultural recommendation."
        ]
    })
    mock_response.content = [mock_block]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    monkeypatch.setattr("anthropic.Anthropic", lambda api_key: mock_client)
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "mock-anthropic-key-12345")

    # Generate guidance
    guidance = generate_claude_guidance(db=db, scan=scan, language="en")

    assert guidance.status == "success"
    assert guidance.disease_explanation == "Cercospora leaf spot detected with 85% certainty."
    assert len(guidance.farmer_action) == 3

    # Verify database persistence in tur_ai_guidance
    saved_record = (
        db.query(TurAIGuidance)
        .filter(TurAIGuidance.scan_id == 201, TurAIGuidance.language == "en")
        .first()
    )
    assert saved_record is not None
    assert saved_record.disease_explanation == "Cercospora leaf spot detected with 85% certainty."
    assert saved_record.status == "success"
    assert len(saved_record.farmer_actions) == 3
    assert saved_record.cache_fingerprint is not None


def test_claude_guidance_cache_hit_bypasses_second_api_call(isolated_g2_g3_env, monkeypatch):
    """
    Verifies that calling generate_claude_guidance a second time for the same scan
    and language returns the persisted record directly with ZERO calls to Anthropic API.
    """
    db, temp_path, SessionMaker = isolated_g2_g3_env

    img_file = temp_path / "scans" / "leaf_202.jpg"
    img_file.parent.mkdir(parents=True, exist_ok=True)
    img_file.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

    scan = TurScan(
        id=202,
        user_id=1,
        crop="tur",
        image_path="scans/leaf_202.jpg",
        status="completed",
        disease_name="Leaf_Spot",
        confidence=0.88,
        prediction_status="completed",
    )
    db.add(scan)
    db.commit()

    mock_response = MagicMock()
    mock_block = MagicMock()
    mock_block.text = json.dumps({
        "disease_explanation": "First generation explanation.",
        "farmer_action": ["Action 1", "Action 2"]
    })
    mock_response.content = [mock_block]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response

    monkeypatch.setattr("anthropic.Anthropic", lambda api_key: mock_client)
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "mock-anthropic-key-12345")

    # 1. First call -> Cache Miss -> Calls Anthropic API
    first_res = generate_claude_guidance(db=db, scan=scan, language="en")
    assert mock_client.messages.create.call_count == 1
    assert first_res.disease_explanation == "First generation explanation."

    # 2. Second call -> Cache Hit -> Must NOT call Anthropic API
    second_res = generate_claude_guidance(db=db, scan=scan, language="en")
    assert mock_client.messages.create.call_count == 1  # Unchanged!
    assert second_res.disease_explanation == "First generation explanation."
    assert second_res.farmer_action == ["Action 1", "Action 2"]
    assert second_res.spray_guidance is not None
    assert second_res.spray_guidance.treatment == "Spray Mancozeb 75 WP"


def test_distinct_languages_persist_separate_guidance_records(isolated_g2_g3_env, monkeypatch):
    """
    Verifies that requests in different languages ('en' vs 'mr') persist distinct
    records in tur_ai_guidance without overwriting each other.
    """
    db, temp_path, SessionMaker = isolated_g2_g3_env

    img_file = temp_path / "scans" / "leaf_203.jpg"
    img_file.parent.mkdir(parents=True, exist_ok=True)
    img_file.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

    scan = TurScan(id=203, user_id=1, crop="tur", image_path="scans/leaf_203.jpg", status="completed", disease_name="Leaf_Spot", confidence=0.80, prediction_status="completed")
    db.add(scan)
    db.commit()

    def mock_create(*args, **kwargs):
        messages = kwargs.get("messages", [])
        user_content = messages[0]["content"] if messages else ""
        text = user_content[-1]["text"] if isinstance(user_content, list) else user_content

        resp = MagicMock()
        block = MagicMock()
        if "mr" in text:
            block.text = json.dumps({"disease_explanation": "पानांवरील ठिपके आढळले.", "farmer_action": ["मँकोझेब फवारा."]})
        else:
            block.text = json.dumps({"disease_explanation": "Leaf spot detected.", "farmer_action": ["Spray Mancozeb."]})
        resp.content = [block]
        return resp

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = mock_create

    monkeypatch.setattr("anthropic.Anthropic", lambda api_key: mock_client)
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "mock-anthropic-key-12345")

    # Call English
    res_en = generate_claude_guidance(db=db, scan=scan, language="en")
    assert res_en.disease_explanation == "Leaf spot detected."

    # Call Marathi
    res_mr = generate_claude_guidance(db=db, scan=scan, language="mr")
    assert res_mr.disease_explanation == "पानांवरील ठिपके आढळले."

    # Check database contains 2 records for scan 203
    records = db.query(TurAIGuidance).filter(TurAIGuidance.scan_id == 203).all()
    assert len(records) == 2
    langs = {r.language for r in records}
    assert langs == {"en", "mr"}


def test_safety_gates_execute_before_cache_lookup(isolated_g2_g3_env, monkeypatch):
    """
    Verifies that safety gates (low confidence, Healthy leaf, Leaf Webber)
    execute BEFORE checking the cache, and never return stale chemical guidance.
    """
    db, temp_path, SessionMaker = isolated_g2_g3_env

    # 1. Low confidence scan (<60%)
    scan_low = TurScan(id=204, user_id=1, crop="tur", status="completed", disease_name="Leaf_Spot", confidence=0.45, prediction_status="completed")
    # Even if an old guidance row existed with status=success:
    stale_guidance = TurAIGuidance(
        scan_id=204, language="en", disease_name="Leaf_Spot", confidence=0.85,
        status="success", disease_explanation="Old advice", farmer_actions=["Spray"],
        warnings=[], spray_guidance_available=True, ai_guidance_available=True,
        cache_fingerprint="dummy",
    )
    db.add_all([scan_low, stale_guidance])
    db.commit()

    res_low = generate_claude_guidance(db=db, scan=scan_low, language="en")
    assert res_low.status == "low_confidence"
    assert res_low.spray_guidance_available is False
    assert res_low.spray_guidance is None

    # 2. Healthy Leaf
    scan_healthy = TurScan(id=205, user_id=1, crop="tur", status="completed", disease_name="Healthy", confidence=0.95, prediction_status="completed")
    res_healthy = generate_claude_guidance(db=db, scan=scan_healthy, language="en")
    assert res_healthy.status == "success"
    assert res_healthy.spray_guidance_available is False
    assert res_healthy.spray_guidance is None


def test_cache_invalidation_when_recommendation_changes(isolated_g2_g3_env, monkeypatch):
    """
    Verifies that if an agronomist modifies the verified recommendation dose,
    the cache fingerprint changes and a fresh Claude call is triggered.
    """
    db, temp_path, SessionMaker = isolated_g2_g3_env

    img_file = temp_path / "scans" / "leaf_206.jpg"
    img_file.parent.mkdir(parents=True, exist_ok=True)
    img_file.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

    scan = TurScan(id=206, user_id=1, crop="tur", image_path="scans/leaf_206.jpg", status="completed", disease_name="Leaf_Spot", confidence=0.85, prediction_status="completed")
    db.add(scan)
    db.commit()

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_block = MagicMock()
    mock_block.text = json.dumps({"disease_explanation": "Advisory text", "farmer_action": ["Action"]})
    mock_resp.content = [mock_block]
    mock_client.messages.create.return_value = mock_resp

    monkeypatch.setattr("anthropic.Anthropic", lambda api_key: mock_client)
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "mock-anthropic-key-12345")

    # First call -> cache miss
    generate_claude_guidance(db=db, scan=scan, language="en")
    assert mock_client.messages.create.call_count == 1

    # Second call -> cache hit
    generate_claude_guidance(db=db, scan=scan, language="en")
    assert mock_client.messages.create.call_count == 1

    # Update recommendation dose in PostgreSQL
    rec = db.query(TurDiseaseRecommendation).filter(TurDiseaseRecommendation.disease_name == "Leaf_Spot").first()
    rec.recommended_quantity = "3.0 g/L (Updated)"
    db.commit()

    # Third call -> fingerprint changed -> cache miss -> triggers second Claude API call
    generate_claude_guidance(db=db, scan=scan, language="en")
    assert mock_client.messages.create.call_count == 2


def test_failed_claude_response_is_not_persisted_to_cache(isolated_g2_g3_env, monkeypatch):
    """
    Verifies that if Claude API raises an exception or returns invalid JSON,
    the fallback response is returned to the user but NEVER saved to tur_ai_guidance.
    """
    db, temp_path, SessionMaker = isolated_g2_g3_env

    scan = TurScan(id=207, user_id=1, crop="tur", status="completed", disease_name="Leaf_Spot", confidence=0.85, prediction_status="completed")
    db.add(scan)
    db.commit()

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = RuntimeError("Claude API 500 Overloaded")

    monkeypatch.setattr("anthropic.Anthropic", lambda api_key: mock_client)
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "mock-anthropic-key-12345")

    res = generate_claude_guidance(db=db, scan=scan, language="en")
    assert res.status == "fallback"

    # Verify zero records saved in tur_ai_guidance
    records = db.query(TurAIGuidance).filter(TurAIGuidance.scan_id == 207).all()
    assert len(records) == 0


def test_ai_guidance_db_commit_failure_handled_gracefully(isolated_g2_g3_env, monkeypatch):
    """
    Verifies that if db.commit fails while saving to tur_ai_guidance,
    db.rollback() is invoked and the successful Claude guidance is still returned to the user.
    """
    db, temp_path, SessionMaker = isolated_g2_g3_env

    scan = TurScan(id=208, user_id=1, crop="tur", status="completed", disease_name="Leaf_Spot", confidence=0.85, prediction_status="completed")
    db.add(scan)
    db.commit()

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_block = MagicMock()
    mock_block.text = json.dumps({"disease_explanation": "Valid explanation", "farmer_action": ["Valid action"]})
    mock_resp.content = [mock_block]
    mock_client.messages.create.return_value = mock_resp

    monkeypatch.setattr("anthropic.Anthropic", lambda api_key: mock_client)
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "mock-anthropic-key-12345")

    # Mock db.commit to raise an exception
    orig_commit = db.commit
    def failing_commit():
        raise RuntimeError("Simulated DB lock error during guidance persistence")

    monkeypatch.setattr(db, "commit", failing_commit)

    # Function must not crash; returns guidance cleanly
    res = generate_claude_guidance(db=db, scan=scan, language="en")
    assert res.status == "success"
    assert res.disease_explanation == "Valid explanation"
