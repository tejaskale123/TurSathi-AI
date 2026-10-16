"""
Tur Organ Validator — Interface Stub (Phase 5D).

This module defines the architectural contract and interface for organ-level
validation (distinguishing Tur_Leaf from Tur_Pod, Tur_WholePlant_or_Canopy,
and Not_Tur_or_Unsupported).

CRITICAL ARCHITECTURAL CONSTRAINTS:
1. This is strictly an interface stub. It does NOT contain trained weights or
   perform real inference.
2. It must NEVER invent predictions, fake confidence scores, or mock field validation.
3. When unconfigured (i.e. model_path is None or does not exist), calling predict()
   must explicitly raise OrganModelNotConfiguredError.
4. Model training and operational activation depend on real field data collection
   and independent agronomist verification (Phase 5D-B).
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Literal, Optional, Union
from PIL import Image

logger = logging.getLogger("tursathi.ml.organ_validator")

# ==============================================================================
# Canonical Organ Taxonomy (Phase 5D-A Design)
# ==============================================================================

OrganClass = Literal[
    "Tur_Leaf",
    "Tur_Pod",
    "Tur_WholePlant_or_Canopy",
    "Not_Tur_or_Unsupported",
]

ORGAN_CLASSES: List[str] = [
    "Tur_Leaf",
    "Tur_Pod",
    "Tur_WholePlant_or_Canopy",
    "Not_Tur_or_Unsupported",
]


# ==============================================================================
# Exceptions
# ==============================================================================

class OrganModelNotConfiguredError(Exception):
    """
    Raised when organ validation is requested but no trained organ model
    checkpoint is configured or available on disk.
    """
    pass


# ==============================================================================
# Result Contract
# ==============================================================================

@dataclass
class OrganValidationResult:
    """
    Structured outcome of an organ validation evaluation.

    Attributes:
        organ_class: The predicted organ category.
        confidence: Prediction confidence probability in range [0.0, 1.0].
        is_valid_leaf: True ONLY if organ_class == 'Tur_Leaf' and meets threshold.
        reason: Machine-readable outcome token (e.g. 'organ_verified_leaf').
        user_message: Human-readable guidance message for the farmer if rejected.
        raw_probabilities: Optional full probability distribution across all classes.
    """
    organ_class: str
    confidence: float
    is_valid_leaf: bool
    reason: str
    user_message: Optional[str] = None
    raw_probabilities: Optional[Dict[str, float]] = None


# ==============================================================================
# Standard Guidance Messages
# ==============================================================================

ORGAN_GUIDANCE_MESSAGES: Dict[str, str] = {
    "Tur_Pod": (
        "Pigeonpea pods detected. Pod borer/blight diagnosis will be available in Phase 6. "
        "Please upload a close-up photo of an individual leaf for disease diagnosis."
    ),
    "Tur_WholePlant_or_Canopy": (
        "Distant whole-plant or canopy view detected. Please hold your camera 20-30 cm "
        "away from an individual leaf so leaf symptoms can be clearly examined."
    ),
    "Not_Tur_or_Unsupported": (
        "Image does not appear to be a pigeonpea leaf. Please upload a clear "
        "Tur (Pigeonpea) leaf image."
    ),
}


# ==============================================================================
# TurOrganValidator Interface
# ==============================================================================

class TurOrganValidator:
    """
    Architectural interface for pigeonpea organ-level classification.

    When fully trained and configured with weights in a future phase, this
    component will evaluate whether an image depicts an individual leaf lamina
    suitable for the 5-class foliar disease classifier, or an unsupported organ.

    In this Phase 5D interface-only state, the model is unconfigured by default.
    """

    def __init__(
        self,
        model_path: Optional[Union[str, Path]] = None,
        leaf_confidence_threshold: float = 0.70,
    ) -> None:
        self.model_path: Optional[Path] = Path(model_path) if model_path else None
        self.leaf_confidence_threshold: float = leaf_confidence_threshold
        self._classes: List[str] = list(ORGAN_CLASSES)
        self._model = None  # Unloaded by default; requires verified weights file

        if self.model_path is not None and self.model_path.exists():
            self._load_model()
        else:
            logger.info(
                "[TurOrganValidator] Interface initialized without active weights. "
                "(Status: UNCONFIGURED - Awaiting Phase 5D field dataset & training)"
            )

    @property
    def classes(self) -> List[str]:
        """Returns the canonical organ classes."""
        return list(self._classes)

    def is_available(self) -> bool:
        """
        Returns True only when a trained model is loaded and ready for inference.
        In this interface-only phase, this always returns False unless a valid
        checkpoint is explicitly provided and successfully loaded.
        """
        return self._model is not None

    def _load_model(self) -> None:
        """
        Loads the trained model weights.
        In this stub, if model_path is specified but loader is not yet implemented,
        raises OrganModelNotConfiguredError.
        """
        # When future training produces a verified checkpoint, model loading logic
        # will be implemented here. For now, weights do not exist.
        raise OrganModelNotConfiguredError(
            f"Organ validator model loader is not yet implemented for: {self.model_path}"
        )

    def predict(
        self,
        image: Union[Image.Image, Path, str],
    ) -> OrganValidationResult:
        """
        Evaluates organ classification on an input image.

        Raises:
            OrganModelNotConfiguredError: In this interface-only state, predictions
                cannot be made because no model weights exist.
        """
        if not self.is_available():
            raise OrganModelNotConfiguredError(
                "TurOrganValidator is unconfigured. Real predictions cannot be generated "
                "until Phase 5D field collection and model training are complete."
            )

        # Unreachable in interface-only stub
        raise NotImplementedError("Organ classification inference is not implemented.")


# ==============================================================================
# Singleton Accessor
# ==============================================================================

_organ_validator_instance: Optional[TurOrganValidator] = None


def get_tur_organ_validator() -> TurOrganValidator:
    """
    Returns the singleton instance of TurOrganValidator.
    """
    global _organ_validator_instance
    if _organ_validator_instance is None:
        _organ_validator_instance = TurOrganValidator()
    return _organ_validator_instance
