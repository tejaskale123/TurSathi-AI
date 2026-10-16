"""
Real EfficientNet-B0 predictor for Tur leaf disease classification.

Flow:
    API route
        ↓
    PredictionService
        ↓
    TurDiseasePredictor
        ↓
    EfficientNet-B0
        ↓
    Disease + confidence

Supported classes:
    Healthy
    Leaf_Spot
    Leaf_webber
    Sterilic_mosaic
    Wilt
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import torch
import torch.nn as nn
from PIL import Image
from torchvision import models, transforms


logger = logging.getLogger("tursathi.ml")


# ============================================================
# PATHS
# ============================================================

# backend/app/ml/tur_predictor.py
# parents[0] = ml
# parents[1] = app
# parents[2] = backend
# parents[3] = TurSathi AI project root

PROJECT_ROOT = Path(__file__).resolve().parents[3]

MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "best_pigeonpea_disease_final_efficientnet_b0.pth"
)


# ============================================================
# DEVICE
# ============================================================

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)


# ============================================================
# MODEL FEATURE FLAG
# ============================================================

MODEL_AVAILABLE: bool = MODEL_PATH.exists()


# ============================================================
# RESULT
# ============================================================

@dataclass
class PredictionResult:
    """
    Structured result from the Tur disease ML model.
    """

    disease_name: str
    confidence: float
    severity: str
    prediction_status: str = "completed"


# ============================================================
# EXCEPTION
# ============================================================

class ModelNotConfiguredError(Exception):
    """
    Raised when the Tur disease ML model is not configured.
    """

    pass


# ============================================================
# PREDICTOR
# ============================================================

class TurDiseasePredictor:
    """
    EfficientNet-B0 based Tur leaf disease predictor.
    """

    def __init__(self) -> None:

        self._model = None

        self._classes: list[str] = []

        self._transform = transforms.Compose([
            transforms.Resize((224, 224)),

            transforms.ToTensor(),

            transforms.Normalize(
                mean=[
                    0.485,
                    0.456,
                    0.406,
                ],
                std=[
                    0.229,
                    0.224,
                    0.225,
                ],
            ),
        ])

        if not MODEL_AVAILABLE:

            logger.warning(
                "[TurDiseasePredictor] "
                f"Model file not found: {MODEL_PATH}"
            )

            return

        self._load_model()


    # ========================================================
    # LOAD MODEL
    # ========================================================

    def _load_model(self) -> None:
        """
        Load the trained EfficientNet-B0 checkpoint.
        """

        logger.info(
            "[TurDiseasePredictor] "
            f"Loading model from: {MODEL_PATH}"
        )

        if not MODEL_PATH.exists():

            raise ModelNotConfiguredError(
                "Tur disease ML model file was not found."
            )

        try:

            checkpoint = torch.load(
                MODEL_PATH,
                map_location=DEVICE,
                weights_only=False,
            )

            classes = checkpoint.get("classes")

            if not classes:

                raise ModelNotConfiguredError(
                    "Model checkpoint does not contain class information."
                )

            self._classes = list(classes)

            num_classes = len(
                self._classes
            )

            # -----------------------------------------------
            # Create EfficientNet-B0 architecture
            # -----------------------------------------------

            model = models.efficientnet_b0(
                weights=None
            )

            in_features = (
                model.classifier[1].in_features
            )

            model.classifier[1] = nn.Linear(
                in_features,
                num_classes,
            )

            # -----------------------------------------------
            # Load trained weights
            # -----------------------------------------------

            model.load_state_dict(
                checkpoint["model_state_dict"]
            )

            model = model.to(
                DEVICE
            )

            model.eval()

            self._model = model

            logger.info(
                "[TurDiseasePredictor] "
                "Model loaded successfully."
            )

            logger.info(
                "[TurDiseasePredictor] "
                f"Device: {DEVICE}"
            )

            logger.info(
                "[TurDiseasePredictor] "
                f"Classes: {self._classes}"
            )

            if torch.cuda.is_available():

                logger.info(
                    "[TurDiseasePredictor] "
                    f"GPU: "
                    f"{torch.cuda.get_device_name(0)}"
                )

        except ModelNotConfiguredError:

            raise

        except Exception as exc:

            logger.exception(
                "[TurDiseasePredictor] "
                "Failed to load model."
            )

            raise ModelNotConfiguredError(
                "Tur disease ML model could not be loaded."
            ) from exc


    # ========================================================
    # AVAILABILITY
    # ========================================================

    def is_available(self) -> bool:
        """
        Returns True when the model is loaded and ready.
        """

        return (
            MODEL_AVAILABLE
            and self._model is not None
        )


    # ========================================================
    # CONFIDENCE LEVEL
    # ========================================================

    @staticmethod
    def _map_confidence_level(
        confidence: float,
    ) -> str:
        """
        The trained classifier predicts disease class and
        confidence, not biological disease severity.

        This returns a confidence level category.
        """

        if confidence >= 0.90:
            return "high_confidence"

        if confidence >= 0.70:
            return "moderate_confidence"

        return "low_confidence"


    # ========================================================
    # PREDICT
    # ========================================================

    def predict(
        self,
        image_path: Path,
    ) -> PredictionResult:
        """
        Run EfficientNet-B0 inference on a stored scan image.
        """

        if not self.is_available():

            raise ModelNotConfiguredError(
                "Tur disease ML model is not configured yet."
            )

        if not image_path.exists():

            raise FileNotFoundError(
                "Scan image not found at expected path. "
                "Cannot run prediction."
            )

        try:

            # -----------------------------------------------
            # Load image
            # -----------------------------------------------

            image = Image.open(
                image_path
            ).convert("RGB")

            # -----------------------------------------------
            # Transform image
            # -----------------------------------------------

            input_tensor = self._transform(
                image
            ).unsqueeze(0)

            input_tensor = input_tensor.to(
                DEVICE
            )

            # -----------------------------------------------
            # Inference
            # -----------------------------------------------

            with torch.no_grad():

                output = self._model(
                    input_tensor
                )

                probabilities = torch.softmax(
                    output,
                    dim=1,
                )[0]

                predicted_index = (
                    probabilities.argmax().item()
                )

                confidence = (
                    probabilities[
                        predicted_index
                    ].item()
                )

            disease_name = self._classes[
                predicted_index
            ]

            confidence_level = self._map_confidence_level(
                confidence
            )

            logger.info(
                "[TurDiseasePredictor] "
                f"Prediction: {disease_name} "
                f"confidence={confidence:.4f}"
            )
            logger.info(
                "[PREDICTOR_DIAGNOSTIC] raw_index=%d mapped_class=%s raw_softmax_conf=%.6f status=completed device=%s",
                predicted_index, disease_name, confidence, str(DEVICE)
            )

            return PredictionResult(
                disease_name=disease_name,
                confidence=confidence,
                severity=confidence_level,  # API compatibility
                prediction_status="completed",
            )

        except FileNotFoundError:

            raise

        except Exception as exc:

            logger.exception(
                "[TurDiseasePredictor] "
                "Prediction failed."
            )

            raise ValueError(
                "The scan image could not be processed "
                "for disease prediction."
            ) from exc


# ============================================================
# MODULE-LEVEL SINGLETON
# ============================================================

_predictor_instance: Optional[
    TurDiseasePredictor
] = None


def get_predictor() -> TurDiseasePredictor:
    """
    Returns the module-level predictor singleton.
    """

    global _predictor_instance

    if _predictor_instance is None:

        _predictor_instance = (
            TurDiseasePredictor()
        )

    return _predictor_instance
