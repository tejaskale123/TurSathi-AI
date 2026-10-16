import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError

from app.ml.tur_image_validator import TurImageValidator

logger = logging.getLogger("tursathi.ml.gate")

# ==============================================================================
# Centralized Image Quality Thresholds
# ==============================================================================
# Minimum resolution floor: both dimensions must meet this threshold.
# Set conservatively to 224 to match the EfficientNet-B0 native input resolution.
MIN_IMAGE_DIMENSION: int = 224

# Blur detection configuration via Laplacian variance.
# Conservative threshold of 35.0: severely defocused/blurred images (<10.0) are rejected,
# while legitimate soft/low-light field images (>130.0) are safely preserved.
ENABLE_BLUR_CHECK: bool = True
BLUR_THRESHOLD: float = 35.0

# Illumination and contrast quality thresholds.
# Severe underexposure (<35.0) or extreme glare/overexposure (>235.0) prevent the
# neural network from observing leaf venation, lesion margins, and pest webbing.
ENABLE_LIGHTING_CHECK: bool = True
MIN_BRIGHTNESS: float = 35.0
MAX_BRIGHTNESS: float = 235.0
MIN_CONTRAST: float = 12.0


@dataclass
class ValidationResult:
    is_valid_tur: bool
    label: str
    confidence: float
    reason: str
    message: Optional[str] = None
    message_mr: Optional[str] = None


class TurImageGate:
    """
    A practical, conservative image validation gate.

    Enforces:
    1. Image sanity and integrity (PIL decode verification).
    2. Minimum resolution floor (MIN_IMAGE_DIMENSION = 224px).
    3. Illumination / lighting quality (MIN_BRIGHTNESS <= mean <= MAX_BRIGHTNESS, std >= MIN_CONTRAST).
    4. Sharpness / blur heuristic (Laplacian variance >= BLUR_THRESHOLD).
    5. Binary crop validation (Tur vs Not_Tur).

    NOTE: Passing image quality checks ensures that the image is clear, adequately
    illuminated, and sufficiently resolved, but does NOT guarantee that the image depicts an
    individual leaf. Organ-level classification (leaf vs pod/stem/whole-plant)
    remains an open limitation requiring future multi-class organ modeling.
    """

    def __init__(
        self,
        min_dimension: int = MIN_IMAGE_DIMENSION,
        blur_threshold: float = BLUR_THRESHOLD,
        enable_blur_check: bool = ENABLE_BLUR_CHECK,
        min_brightness: float = MIN_BRIGHTNESS,
        max_brightness: float = MAX_BRIGHTNESS,
        enable_lighting_check: bool = ENABLE_LIGHTING_CHECK,
        min_contrast: float = MIN_CONTRAST,
    ) -> None:
        self.min_dimension = min_dimension
        self.blur_threshold = blur_threshold
        self.enable_blur_check = enable_blur_check
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self.enable_lighting_check = enable_lighting_check
        self.min_contrast = min_contrast
        try:
            self.validator = TurImageValidator()
        except Exception as exc:
            logger.error("Failed to load TurImageValidator: %s", exc)
            self.validator = None

    def validate_bytes(
        self,
        image_bytes: bytes,
        source_name: str = "frame",
    ) -> ValidationResult:
        """
        Validates raw image bytes in-memory without reading or writing from disk.
        Executes PIL integrity verification, resolution checks, lighting/contrast checks,
        Laplacian blur check, and TurImageValidator inference.
        """
        if not image_bytes:
            return ValidationResult(
                is_valid_tur=False,
                label="Error",
                confidence=1.0,
                reason="empty_file",
                message="No image data provided.",
                message_mr="कोणतीही फोटो फाईल दिली नाही. कृपया फोटो पुन्हा घ्या.",
            )

        # 1. Basic Image Sanity & Resolution Checks
        try:
            with Image.open(io.BytesIO(image_bytes)) as img_verify:
                img_verify.verify()

            with Image.open(io.BytesIO(image_bytes)) as image:
                width, height = image.size
                if width < self.min_dimension or height < self.min_dimension:
                    return ValidationResult(
                        is_valid_tur=False,
                        label="Error",
                        confidence=1.0,
                        reason="image_too_small",
                        message=(
                            f"Image resolution is too low ({width}x{height}). "
                            f"Please upload a clear Tur/Pigeonpea leaf image. "
                            f"Minimum required resolution is {self.min_dimension}x{self.min_dimension} pixels."
                        ),
                        message_mr="फोटोचा आकार खूप लहान आहे. कृपया जवळून तूर पानाचा स्पष्ट फोटो पुन्हा घ्या.",
                    )

                gray_image = image.convert("L")
                gray_np = np.array(gray_image)

                # 2. Sharpness / Blur Heuristic Check
                if self.enable_blur_check:
                    try:
                        blur_score = float(cv2.Laplacian(gray_np, cv2.CV_64F).var())

                        if blur_score < self.blur_threshold:
                            logger.warning(
                                "Image rejected due to excessive blur (Laplacian variance: %.2f < %.2f): %s",
                                blur_score, self.blur_threshold, source_name,
                            )
                            return ValidationResult(
                                is_valid_tur=False,
                                label="Error",
                                confidence=1.0,
                                reason="image_too_blurry",
                                message="Image appears too blurry or out of focus. Please upload a clear Tur/Pigeonpea leaf image.",
                                message_mr="फोटो अस्पष्ट (blurry) दिसत आहे. कृपया फोन स्थिर धरून चांगल्या प्रकाशात तूर पानाचा फोटो पुन्हा घ्या.",
                            )
                    except Exception as blur_exc:
                        logger.warning("Blur evaluation failed (non-fatal, continuing): %s", blur_exc)

                # 3. Illumination / Lighting & Contrast Check
                if self.enable_lighting_check:
                    try:
                        mean_brightness = float(np.mean(gray_np))
                        if mean_brightness < self.min_brightness:
                            logger.warning(
                                "Image rejected due to low lighting / underexposure (mean brightness: %.2f < %.2f): %s",
                                mean_brightness, self.min_brightness, source_name,
                            )
                            return ValidationResult(
                                is_valid_tur=False,
                                label="Error",
                                confidence=1.0,
                                reason="image_too_dark",
                                message="Image is too dark or poorly lit. Please upload a clear Tur/Pigeonpea leaf image in good daylight.",
                                message_mr="फोटोमध्ये प्रकाश खूप कमी (अंधुक) आहे. कृपया चांगल्या सूर्यप्रकाशात किंवा उजेडात तूर पानाचा फोटो पुन्हा घ्या.",
                            )
                        elif mean_brightness > self.max_brightness:
                            logger.warning(
                                "Image rejected due to excessive brightness / glare (mean brightness: %.2f > %.2f): %s",
                                mean_brightness, self.max_brightness, source_name,
                            )
                            return ValidationResult(
                                is_valid_tur=False,
                                label="Error",
                                confidence=1.0,
                                reason="image_too_bright",
                                message="Image is overexposed or too bright. Please upload a clear Tur/Pigeonpea leaf image in balanced lighting.",
                                message_mr="फोटोमध्ये प्रकाश खूप जास्त (ओव्हरएक्सपोज्ड) आहे. कृपया योग्य प्रकाशात तूर पानाचा फोटो पुन्हा घ्या.",
                            )

                        std_brightness = float(np.std(gray_np))
                        if std_brightness < self.min_contrast:
                            logger.warning(
                                "Image rejected due to low contrast / lack of features (std: %.2f < %.2f): %s",
                                std_brightness, self.min_contrast, source_name,
                            )
                            return ValidationResult(
                                is_valid_tur=False,
                                label="Error",
                                confidence=1.0,
                                reason="image_low_contrast",
                                message="Image lacks contrast or details. Please upload a clear Tur/Pigeonpea leaf image.",
                                message_mr="फोटोमध्ये पानाचे तपशील स्पष्ट दिसत नाहीत. कृपया तूर पानाचा स्पष्ट फोटो पुन्हा घ्या.",
                            )
                    except Exception as light_exc:
                        logger.warning("Lighting evaluation failed (non-fatal, continuing): %s", light_exc)


        except UnidentifiedImageError:
            return ValidationResult(
                is_valid_tur=False,
                label="Error",
                confidence=1.0,
                reason="corrupted_image",
                message="Please upload a clear Tur/Pigeonpea leaf image.",
                message_mr="फोटो फाईल वाचता आली नाही. कृपया तूर पानाचा स्पष्ट फोटो पुन्हा घ्या.",
            )
        except Exception as exc:
            logger.error("Image sanity check failed: %s", exc)
            return ValidationResult(
                is_valid_tur=False,
                label="Error",
                confidence=1.0,
                reason="read_error",
                message="Please upload a clear Tur/Pigeonpea leaf image.",
                message_mr="फोटो फाईल वाचताना त्रुटी आली. कृपया तूर पानाचा स्पष्ट फोटो पुन्हा घ्या.",
            )

        # 4. Existing Tur Validator Check
        if self.validator:
            try:
                pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                val_result = self.validator.predict(pil_image)

                is_tur = val_result["is_tur"]
                label = val_result["label"]
                confidence = val_result["confidence"]

                if is_tur:
                    return ValidationResult(
                        is_valid_tur=True,
                        label=label,
                        confidence=confidence,
                        reason="validator_confident_tur",
                    )
                else:
                    return ValidationResult(
                        is_valid_tur=False,
                        label=label,
                        confidence=confidence,
                        reason="validator_confident_not_tur",
                        message="Please upload a clear Tur/Pigeonpea leaf image.",
                        message_mr="हा फोटो तुरीच्या पानाचा वाटत नाही. कृपया तूर पिकाच्या पानाचा स्पष्ट फोटो पुन्हा घ्या.",
                    )

            except Exception as exc:
                logger.error("TurImageValidator failed during predict: %s", exc)
                return ValidationResult(
                    is_valid_tur=False,
                    label="Error",
                    confidence=0.0,
                    reason="validator_prediction_error_fallback_reject",
                    message="Internal validation error. Please try uploading the image again.",
                    message_mr="अंतर्गत पडताळणी त्रुटी आली. कृपया फोटो पुन्हा अपलोड करा.",
                )

        # Default fallback if validator fails to load
        return ValidationResult(
            is_valid_tur=False,
            label="Fallback",
            confidence=0.0,
            reason="all_gates_failed_fallback_reject",
            message="Image validation service is currently unavailable. Cannot process image.",
            message_mr="फोटो पडताळणी सेवा सध्या उपलब्ध नाही. कृपया थोड्या वेळाने प्रयत्न करा.",
        )

    def validate(self, image_path: Path) -> ValidationResult:
        """
        Validates the image file safely using PIL sanity checks, resolution floor,
        Laplacian blur assessment, and the existing TurImageValidator.
        """
        if not image_path.exists():
            return ValidationResult(
                is_valid_tur=False,
                label="Error",
                confidence=1.0,
                reason="file_not_found",
                message="Image file could not be found.",
            )

        try:
            image_bytes = image_path.read_bytes()
        except Exception as exc:
            logger.error("Image read failed: %s", exc)
            return ValidationResult(
                is_valid_tur=False,
                label="Error",
                confidence=1.0,
                reason="read_error",
                message="Please upload a clear Tur/Pigeonpea leaf image.",
            )

        return self.validate_bytes(image_bytes, source_name=image_path.name)



# Singleton instance
_gate_instance: Optional[TurImageGate] = None

def get_tur_image_gate() -> TurImageGate:
    global _gate_instance
    if _gate_instance is None:
        _gate_instance = TurImageGate()
    return _gate_instance
