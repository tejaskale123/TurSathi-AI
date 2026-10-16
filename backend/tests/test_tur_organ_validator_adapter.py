"""
Focused unit tests for Phase 5D Step 1: Organ Validator Adapter.

Tests the isolated translation contract between:
- OrganValidationResult (backend/app/ml/tur_organ_validator.py)
- ValidationResult (backend/app/ml/tur_image_gate.py)

STRICT RULES OBSERVED:
- Does NOT modify production application code.
- Does NOT connect TurOrganValidator to live TurImageGate or PredictionService.
- Does NOT load real weights, execute real ML inference, or require field data.
- Verifies exact field mapping and ensures raw_probabilities is never leaked to API contract.
"""

import json
import unittest
from dataclasses import asdict
from typing import Optional
from unittest.mock import MagicMock

from app.ml.tur_image_gate import ValidationResult
from app.ml.tur_organ_validator import (
    ORGAN_CLASSES,
    ORGAN_GUIDANCE_MESSAGES,
    OrganModelNotConfiguredError,
    OrganValidationResult,
    TurOrganValidator,
)


def adapt_organ_result_to_validation_result(
    organ_result: OrganValidationResult,
) -> ValidationResult:
    """
    Isolated adapter function mapping OrganValidationResult to the existing
    ValidationResult consumed by TurImageGate and PredictionService.

    Mapping specification:
        organ_result.is_valid_leaf -> ValidationResult.is_valid_tur
        organ_result.organ_class   -> ValidationResult.label
        organ_result.confidence    -> ValidationResult.confidence
        organ_result.reason        -> ValidationResult.reason
        organ_result.user_message  -> ValidationResult.message

    Note:
        organ_result.raw_probabilities is intentionally omitted to preserve
        the existing ValidationResult and API error-response schemas.
    """
    return ValidationResult(
        is_valid_tur=organ_result.is_valid_leaf,
        label=organ_result.organ_class,
        confidence=organ_result.confidence,
        reason=organ_result.reason,
        message=organ_result.user_message,
    )


class TestOrganValidatorAdapter(unittest.TestCase):

    def test_01_adapt_valid_tur_leaf_mapping(self):
        """Valid Tur_Leaf maps to is_valid_tur=True with message=None."""
        organ_res = OrganValidationResult(
            organ_class="Tur_Leaf",
            confidence=0.9450,
            is_valid_leaf=True,
            reason="organ_verified_leaf",
            user_message=None,
            raw_probabilities={
                "Tur_Leaf": 0.9450,
                "Tur_Pod": 0.0250,
                "Tur_WholePlant_or_Canopy": 0.0200,
                "Not_Tur_or_Unsupported": 0.0100,
            },
        )

        gate_res = adapt_organ_result_to_validation_result(organ_res)

        self.assertIsInstance(gate_res, ValidationResult)
        self.assertTrue(gate_res.is_valid_tur)
        self.assertEqual(gate_res.label, "Tur_Leaf")
        self.assertEqual(gate_res.confidence, 0.9450)
        self.assertEqual(gate_res.reason, "organ_verified_leaf")
        self.assertIsNone(gate_res.message)

    def test_02_adapt_tur_pod_mapping(self):
        """Tur_Pod rejection maps to is_valid_tur=False with pod guidance message."""
        pod_msg = ORGAN_GUIDANCE_MESSAGES["Tur_Pod"]
        organ_res = OrganValidationResult(
            organ_class="Tur_Pod",
            confidence=0.9120,
            is_valid_leaf=False,
            reason="organ_rejected_pod",
            user_message=pod_msg,
            raw_probabilities={"Tur_Pod": 0.9120, "Tur_Leaf": 0.0500},
        )

        gate_res = adapt_organ_result_to_validation_result(organ_res)

        self.assertIsInstance(gate_res, ValidationResult)
        self.assertFalse(gate_res.is_valid_tur)
        self.assertEqual(gate_res.label, "Tur_Pod")
        self.assertEqual(gate_res.confidence, 0.9120)
        self.assertEqual(gate_res.reason, "organ_rejected_pod")
        self.assertEqual(gate_res.message, pod_msg)

    def test_03_adapt_tur_whole_plant_canopy_mapping(self):
        """Tur_WholePlant_or_Canopy maps to is_valid_tur=False with canopy guidance message."""
        canopy_msg = ORGAN_GUIDANCE_MESSAGES["Tur_WholePlant_or_Canopy"]
        organ_res = OrganValidationResult(
            organ_class="Tur_WholePlant_or_Canopy",
            confidence=0.8875,
            is_valid_leaf=False,
            reason="organ_rejected_canopy",
            user_message=canopy_msg,
            raw_probabilities={"Tur_WholePlant_or_Canopy": 0.8875},
        )

        gate_res = adapt_organ_result_to_validation_result(organ_res)

        self.assertIsInstance(gate_res, ValidationResult)
        self.assertFalse(gate_res.is_valid_tur)
        self.assertEqual(gate_res.label, "Tur_WholePlant_or_Canopy")
        self.assertEqual(gate_res.confidence, 0.8875)
        self.assertEqual(gate_res.reason, "organ_rejected_canopy")
        self.assertEqual(gate_res.message, canopy_msg)

    def test_04_adapt_not_tur_or_unsupported_mapping(self):
        """Not_Tur_or_Unsupported maps to is_valid_tur=False with unsupported guidance."""
        unsupported_msg = ORGAN_GUIDANCE_MESSAGES["Not_Tur_or_Unsupported"]
        organ_res = OrganValidationResult(
            organ_class="Not_Tur_or_Unsupported",
            confidence=0.9630,
            is_valid_leaf=False,
            reason="organ_rejected_unsupported",
            user_message=unsupported_msg,
            raw_probabilities={"Not_Tur_or_Unsupported": 0.9630},
        )

        gate_res = adapt_organ_result_to_validation_result(organ_res)

        self.assertIsInstance(gate_res, ValidationResult)
        self.assertFalse(gate_res.is_valid_tur)
        self.assertEqual(gate_res.label, "Not_Tur_or_Unsupported")
        self.assertEqual(gate_res.confidence, 0.9630)
        self.assertEqual(gate_res.reason, "organ_rejected_unsupported")
        self.assertEqual(gate_res.message, unsupported_msg)

    def test_05_raw_probabilities_excluded_from_validation_result(self):
        """Ensure raw_probabilities is strictly filtered out and never present on ValidationResult."""
        organ_res = OrganValidationResult(
            organ_class="Tur_Pod",
            confidence=0.85,
            is_valid_leaf=False,
            reason="organ_rejected_pod",
            user_message="Pods detected",
            raw_probabilities={"Tur_Pod": 0.85, "Tur_Leaf": 0.15},
        )

        gate_res = adapt_organ_result_to_validation_result(organ_res)
        gate_dict = asdict(gate_res)

        # Confirm strictly standard keys only
        expected_keys = {"is_valid_tur", "label", "confidence", "reason", "message", "message_mr"}
        self.assertEqual(set(gate_dict.keys()), expected_keys)
        self.assertNotIn("raw_probabilities", gate_dict)
        self.assertFalse(hasattr(gate_res, "raw_probabilities"))

    def test_06_api_error_detail_serialization(self):
        """Ensure adapted gate_res produces valid JSON matching PredictionService HTTP 422 detail."""
        organ_res = OrganValidationResult(
            organ_class="Tur_Pod",
            confidence=0.92,
            is_valid_leaf=False,
            reason="organ_rejected_pod",
            user_message=ORGAN_GUIDANCE_MESSAGES["Tur_Pod"],
        )
        gate_res = adapt_organ_result_to_validation_result(organ_res)

        # Simulation of PredictionService error detail payload
        error_detail = {
            "status": "validation_failed",
            "message": gate_res.message or "This image does not appear to be a valid Tur leaf.",
        }

        # Must cleanly serialize to JSON
        json_str = json.dumps(error_detail)
        deserialized = json.loads(json_str)
        self.assertEqual(deserialized["status"], "validation_failed")
        self.assertIn("Pigeonpea pods detected", deserialized["message"])

    def test_07_mocked_unconfigured_error_boundary(self):
        """Verify that an unconfigured validator raises OrganModelNotConfiguredError and is safely catchable."""
        mock_validator = TurOrganValidator()
        self.assertFalse(mock_validator.is_available())

        # An adapter consumer must be able to catch OrganModelNotConfiguredError safely
        caught = False
        try:
            mock_validator.predict(MagicMock())
        except OrganModelNotConfiguredError as exc:
            caught = True
            self.assertIn("unconfigured", str(exc).lower())

        self.assertTrue(caught, "OrganModelNotConfiguredError must be raised when unconfigured.")


if __name__ == "__main__":
    unittest.main()
