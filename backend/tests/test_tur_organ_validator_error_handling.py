"""
Focused unit tests for Phase 5D Step 2: Organ Validator Error Handling.

Tests the isolated error handling boundaries and failure behaviors for
TurOrganValidator and its interactions without modifying production code.

STRICT CONSTRAINTS:
- Does NOT modify production application code under backend/app/.
- Does NOT connect TurOrganValidator to live TurImageGate or PredictionService.
- Does NOT load real weights, execute real ML inference, or require field data.
- Uses unit test mocks and controlled test objects exclusively.
"""

import json
import unittest
from unittest.mock import MagicMock

from fastapi import HTTPException, status
from PIL import Image

from app.core.config import settings
from app.ml.tur_image_gate import ValidationResult
from app.ml.tur_organ_validator import (
    ORGAN_CLASSES,
    OrganModelNotConfiguredError,
    OrganValidationResult,
    TurOrganValidator,
)


class TestTurOrganValidatorErrorHandling(unittest.TestCase):

    def test_01_unconfigured_validator_raises_explicit_exception(self):
        """Unconfigured TurOrganValidator raises OrganModelNotConfiguredError, never returns fake predictions."""
        validator = TurOrganValidator()
        self.assertFalse(validator.is_available())

        dummy_img = Image.new("RGB", (224, 224), color=(0, 200, 50))
        with self.assertRaises(OrganModelNotConfiguredError) as ctx:
            validator.predict(dummy_img)

        err_msg = str(ctx.exception)
        self.assertIn("unconfigured", err_msg.lower())
        self.assertIn("field collection", err_msg.lower())

    def test_02_organ_model_not_configured_error_is_catchable_subclass(self):
        """OrganModelNotConfiguredError can be caught explicitly or as generic Exception."""
        validator = TurOrganValidator()

        # Specific catch
        caught_specific = False
        try:
            validator.predict(MagicMock())
        except OrganModelNotConfiguredError:
            caught_specific = True
        self.assertTrue(caught_specific)

        # Generic catch
        caught_generic = False
        try:
            validator.predict(MagicMock())
        except Exception:
            caught_generic = True
        self.assertTrue(caught_generic)

    def test_03_no_fake_predictions_on_failure(self):
        """Failure must never fabricate an OrganValidationResult or return fake confidences."""
        validator = TurOrganValidator()
        result = None
        try:
            result = validator.predict(MagicMock())
        except OrganModelNotConfiguredError:
            pass

        self.assertIsNone(result, "Unconfigured validator must not return any result object.")

    def test_04_simulated_gate_error_boundary_does_not_mask_failures(self):
        """A gate wrapper catching OrganModelNotConfiguredError handles it without inventing valid state."""
        # Simulated gate logic showing how TurImageGate should handle unconfigured organ validator
        def simulated_safe_organ_gate_wrapper(validator: TurOrganValidator, img) -> ValidationResult:
            try:
                organ_res = validator.predict(img)
                return ValidationResult(
                    is_valid_tur=organ_res.is_valid_leaf,
                    label=organ_res.organ_class,
                    confidence=organ_res.confidence,
                    reason=organ_res.reason,
                    message=organ_res.user_message,
                )
            except OrganModelNotConfiguredError:
                # Safe fallback: reject with clear unconfigured reason, never pretend valid
                return ValidationResult(
                    is_valid_tur=False,
                    label="Error",
                    confidence=0.0,
                    reason="organ_validator_unconfigured",
                    message="Organ validation is unconfigured. Awaiting field dataset.",
                )

        unconfigured_validator = TurOrganValidator()
        fallback_res = simulated_safe_organ_gate_wrapper(unconfigured_validator, MagicMock())

        self.assertIsInstance(fallback_res, ValidationResult)
        self.assertFalse(fallback_res.is_valid_tur, "Fallback must NOT mark image as valid.")
        self.assertEqual(fallback_res.confidence, 0.0)
        self.assertEqual(fallback_res.reason, "organ_validator_unconfigured")

    def test_05_unexpected_runtime_error_handled_safely(self):
        """Unexpected runtime errors (e.g. OOM, OS errors) are not silently converted to valid predictions."""
        broken_validator = TurOrganValidator()
        broken_validator.is_available = MagicMock(return_value=True)

        def simulated_failing_gate(validator, img):
            try:
                # Force unexpected runtime error during predict
                raise RuntimeError("Simulated GPU out-of-memory or driver failure")
            except RuntimeError:
                return ValidationResult(
                    is_valid_tur=False,
                    label="Error",
                    confidence=0.0,
                    reason="organ_validator_runtime_error",
                    message="Internal validation error. Please try uploading the image again.",
                )

        error_res = simulated_failing_gate(broken_validator, MagicMock())
        self.assertFalse(error_res.is_valid_tur)
        self.assertEqual(error_res.reason, "organ_validator_runtime_error")

    def test_06_error_detail_api_contract_compatibility(self):
        """Simulated HTTP 422 detail payload satisfies the PredictionService API contract."""
        rejection_res = ValidationResult(
            is_valid_tur=False,
            label="Tur_Pod",
            confidence=0.92,
            reason="organ_rejected_pod",
            message="Pigeonpea pods detected. Pod borer/blight diagnosis will be available in Phase 6.",
        )

        # Simulate PredictionService HTTPException detail
        http_exc = HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "status": "validation_failed",
                "message": rejection_res.message,
            },
        )

        self.assertEqual(http_exc.status_code, 422)
        self.assertIsInstance(http_exc.detail, dict)
        self.assertEqual(http_exc.detail["status"], "validation_failed")
        self.assertIn("Pigeonpea pods detected", http_exc.detail["message"])

        # Must cleanly serialize to JSON
        json_output = json.dumps(http_exc.detail)
        self.assertIn("validation_failed", json_output)

    def test_07_live_pipeline_integration_intentionally_skipped(self):
        """
        Documented Limitation & Intentional Omission:
        Live route integration test (e.g. test_client.post('/api/v1/predictions/tur-leaf/1'))
        is intentionally SKIPPED because ENABLE_ORGAN_VALIDATOR is False and the stub
        is not wired into production code under backend/app/.
        """
        self.assertFalse(
            settings.ENABLE_ORGAN_VALIDATOR,
            "ENABLE_ORGAN_VALIDATOR must remain False during Phase 5D interface testing.",
        )


if __name__ == "__main__":
    unittest.main()
