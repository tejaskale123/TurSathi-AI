import pytest
from pathlib import Path
from PIL import Image
from unittest.mock import patch, MagicMock

# Create dummy images for testing
TEST_DIR = Path("test_gate_images")
TEST_DIR.mkdir(exist_ok=True)

TUR_IMAGE = TEST_DIR / "tur.jpg"
Image.new("RGB", (224, 224), color="green").save(TUR_IMAGE)

NOT_TUR_IMAGE = TEST_DIR / "not_tur.jpg"
Image.new("RGB", (224, 224), color="blue").save(NOT_TUR_IMAGE)

CORRUPT_IMAGE = TEST_DIR / "corrupt.jpg"
with open(CORRUPT_IMAGE, "wb") as f:
    f.write(b"NOT AN IMAGE")
    
MISSING_IMAGE = TEST_DIR / "missing.jpg"

SMALL_IMAGE = TEST_DIR / "small.jpg"
Image.new("RGB", (10, 10), color="red").save(SMALL_IMAGE)

def test_gate_valid_tur():
    from app.ml.tur_image_gate import get_tur_image_gate
    gate = get_tur_image_gate()
    
    # Mock the validator predict
    with patch.object(gate.validator, "predict", return_value={"is_tur": True, "label": "Tur", "confidence": 0.99}):
        result = gate.validate(TUR_IMAGE)
        assert result.is_valid_tur is True
        assert result.reason == "validator_confident_tur"

def test_gate_invalid_not_tur():
    from app.ml.tur_image_gate import get_tur_image_gate
    gate = get_tur_image_gate()
    
    with patch.object(gate.validator, "predict", return_value={"is_tur": False, "label": "Not_Tur", "confidence": 0.99}):
        result = gate.validate(NOT_TUR_IMAGE)
        assert result.is_valid_tur is False
        assert result.reason == "validator_confident_not_tur"

def test_gate_corrupt_image():
    from app.ml.tur_image_gate import get_tur_image_gate
    gate = get_tur_image_gate()
    
    result = gate.validate(CORRUPT_IMAGE)
    assert result.is_valid_tur is False
    assert result.reason in ["corrupted_image", "read_error"]

def test_gate_missing_image():
    from app.ml.tur_image_gate import get_tur_image_gate
    gate = get_tur_image_gate()
    
    result = gate.validate(MISSING_IMAGE)
    assert result.is_valid_tur is False
    assert result.reason == "file_not_found"

def test_gate_small_image():
    from app.ml.tur_image_gate import get_tur_image_gate
    gate = get_tur_image_gate()
    
    result = gate.validate(SMALL_IMAGE)
    assert result.is_valid_tur is False
    assert result.reason == "image_too_small"

def test_gate_validator_failure_fails_closed():
    from app.ml.tur_image_gate import get_tur_image_gate
    gate = get_tur_image_gate()
    
    with patch.object(gate.validator, "predict", side_effect=Exception("Model crashed")):
        result = gate.validate(TUR_IMAGE)
        assert result.is_valid_tur is False
        assert result.reason == "validator_prediction_error_fallback_reject"
