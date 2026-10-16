"""
Focused unit tests for Phase 5D: Tur Organ Validator Interface Stub.

Verifies:
1. Canonical organ classes taxonomy.
2. OrganValidationResult dataclass contract.
3. TurOrganValidator initialization, defaults, and unconfigured state.
4. Predict method raises OrganModelNotConfiguredError (no fake predictions).
5. get_tur_organ_validator singleton accessor.
6. ENABLE_ORGAN_VALIDATOR configuration flag defaults to False.
7. Guidance messages for rejected organ types.
"""

import unittest
from pathlib import Path
# pyrefly: ignore [missing-import]
from PIL import Image

from app.core.config import settings
from app.ml.tur_organ_validator import (
    ORGAN_CLASSES,
    ORGAN_GUIDANCE_MESSAGES,
    OrganModelNotConfiguredError,
    OrganValidationResult,
    TurOrganValidator,
    get_tur_organ_validator,
)


class TestTurOrganValidatorInterface(unittest.TestCase):

    def test_01_canonical_organ_classes(self):
        """Verify the exact 4 canonical organ classes defined in Phase 5D design."""
        expected_classes = [
            "Tur_Leaf",
            "Tur_Pod",
            "Tur_WholePlant_or_Canopy",
            "Not_Tur_or_Unsupported",
        ]
        self.assertEqual(ORGAN_CLASSES, expected_classes)
        self.assertEqual(len(ORGAN_CLASSES), 4)

    def test_02_validation_result_contract(self):
        """Verify the OrganValidationResult dataclass fields and types."""
        res = OrganValidationResult(
            organ_class="Tur_Leaf",
            confidence=0.95,
            is_valid_leaf=True,
            reason="organ_verified_leaf",
            user_message=None,
            raw_probabilities={
                "Tur_Leaf": 0.95,
                "Tur_Pod": 0.02,
                "Tur_WholePlant_or_Canopy": 0.02,
                "Not_Tur_or_Unsupported": 0.01,
            },
        )
        self.assertEqual(res.organ_class, "Tur_Leaf")
        self.assertEqual(res.confidence, 0.95)
        self.assertTrue(res.is_valid_leaf)
        self.assertEqual(res.reason, "organ_verified_leaf")
        self.assertIsNone(res.user_message)
        self.assertIsNotNone(res.raw_probabilities)
        self.assertEqual(res.raw_probabilities["Tur_Leaf"], 0.95)

    def test_03_default_unconfigured_state(self):
        """TurOrganValidator must initialize in an unconfigured state when no model exists."""
        validator = TurOrganValidator()
        self.assertFalse(validator.is_available())
        self.assertIsNone(validator.model_path)
        self.assertEqual(validator.classes, ORGAN_CLASSES)

    def test_04_predict_raises_when_unconfigured(self):
        """Calling predict() must raise OrganModelNotConfiguredError; no fake predictions."""
        validator = TurOrganValidator()
        self.assertFalse(validator.is_available())

        dummy_img = Image.new("RGB", (224, 224), color=(0, 128, 0))
        with self.assertRaises(OrganModelNotConfiguredError) as ctx:
            validator.predict(dummy_img)

        self.assertIn("unconfigured", str(ctx.exception).lower())

    def test_05_nonexistent_model_path_handled_safely(self):
        """Specifying a nonexistent checkpoint path leaves validator unavailable and safe."""
        fake_path = Path("models/nonexistent_organ_checkpoint.pth")
        validator = TurOrganValidator(model_path=fake_path)

        self.assertFalse(validator.is_available())
        dummy_img = Image.new("RGB", (224, 224), color=(0, 128, 0))
        with self.assertRaises(OrganModelNotConfiguredError):
            validator.predict(dummy_img)

    def test_06_singleton_accessor(self):
        """get_tur_organ_validator() returns a valid, consistent TurOrganValidator instance."""
        inst1 = get_tur_organ_validator()
        inst2 = get_tur_organ_validator()
        self.assertIs(inst1, inst2)
        self.assertIsInstance(inst1, TurOrganValidator)
        self.assertFalse(inst1.is_available())

    def test_07_feature_flag_defaults_to_false(self):
        """ENABLE_ORGAN_VALIDATOR setting must default to False in application configuration."""
        self.assertFalse(settings.ENABLE_ORGAN_VALIDATOR)

    def test_08_guidance_messages_defined(self):
        """Farmer guidance messages exist for all non-leaf organ categories."""
        for organ_class in ["Tur_Pod", "Tur_WholePlant_or_Canopy", "Not_Tur_or_Unsupported"]:
            self.assertIn(organ_class, ORGAN_GUIDANCE_MESSAGES)
            msg = ORGAN_GUIDANCE_MESSAGES[organ_class]
            self.assertIsInstance(msg, str)
            self.assertGreater(len(msg), 20)


if __name__ == "__main__":
    unittest.main()
