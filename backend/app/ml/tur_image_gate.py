import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PIL import Image, UnidentifiedImageError

from app.ml.tur_image_validator import TurImageValidator

logger = logging.getLogger("tursathi.ml.gate")


@dataclass
class ValidationResult:
    is_valid_tur: bool
    label: str
    confidence: float
    reason: str
    message: Optional[str] = None


class TurImageGate:
    """
    A practical, conservative image validation gate.
    """

    def __init__(self) -> None:
        try:
            self.validator = TurImageValidator()
        except Exception as exc:
            logger.error("Failed to load TurImageValidator: %s", exc)
            self.validator = None

    def validate(self, image_path: Path) -> ValidationResult:
        """
        Validates the image file safely using PIL sanity checks
        and the existing TurImageValidator.
        """
        if not image_path.exists():
            return ValidationResult(
                is_valid_tur=False,
                label="Error",
                confidence=1.0,
                reason="file_not_found",
                message="Image file could not be found.",
            )

        # 1. Basic Image Sanity Checks
        try:
            image = Image.open(image_path)
            image.verify()  # Verify it's a valid image file structure
            
            # Reopen for actual dimension checking since verify() doesn't allow subsequent operations on some formats
            image = Image.open(image_path)
            width, height = image.size
            if width < 32 or height < 32:
                return ValidationResult(
                    is_valid_tur=False,
                    label="Error",
                    confidence=1.0,
                    reason="image_too_small",
                    message="Please upload a clear Tur/Pigeonpea leaf image.",
                )

        except UnidentifiedImageError:
            return ValidationResult(
                is_valid_tur=False,
                label="Error",
                confidence=1.0,
                reason="corrupted_image",
                message="Please upload a clear Tur/Pigeonpea leaf image.",
            )
        except Exception as exc:
            logger.error("Image sanity check failed: %s", exc)
            return ValidationResult(
                is_valid_tur=False,
                label="Error",
                confidence=1.0,
                reason="read_error",
                message="Please upload a clear Tur/Pigeonpea leaf image.",
            )

        # 2. Existing Tur Validator Check
        if self.validator:
            try:
                # Must open again fresh to pass into validator
                pil_image = Image.open(image_path).convert("RGB")
                val_result = self.validator.predict(pil_image)
                
                is_tur = val_result["is_tur"]
                label = val_result["label"]
                confidence = val_result["confidence"]

                # Conservative logic: we only pass through what the validator gives us.
                # If the validator explicitly says Not_Tur, we reject.
                # If it says Tur, we accept.
                if is_tur:
                    return ValidationResult(
                        is_valid_tur=True,
                        label=label,
                        confidence=confidence,
                        reason="validator_confident_tur"
                    )
                else:
                    return ValidationResult(
                        is_valid_tur=False,
                        label=label,
                        confidence=confidence,
                        reason="validator_confident_not_tur",
                        message="Please upload a clear Tur/Pigeonpea leaf image."
                    )

            except Exception as exc:
                logger.error("TurImageValidator failed during predict: %s", exc)
                return ValidationResult(
                    is_valid_tur=False,
                    label="Error",
                    confidence=0.0,
                    reason="validator_prediction_error_fallback_reject",
                    message="Internal validation error. Please try uploading the image again."
                )

        # Default fallback if validator fails to load
        return ValidationResult(
            is_valid_tur=False,
            label="Fallback",
            confidence=0.0,
            reason="all_gates_failed_fallback_reject",
            message="Image validation service is currently unavailable. Cannot process image."
        )


# Singleton instance
_gate_instance: Optional[TurImageGate] = None

def get_tur_image_gate() -> TurImageGate:
    global _gate_instance
    if _gate_instance is None:
        _gate_instance = TurImageGate()
    return _gate_instance
