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

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import numpy as np
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

OOD_PROFILE_PATH = (
    PROJECT_ROOT
    / "models"
    / "ood_feature_profile.json"
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
# ARCHITECTURE DEFINITION
# ============================================================

class TurEfficientNetB0(nn.Module):
    """
    EfficientNet-B0 with dedicated penultimate feature extraction tapping.
    Used for 1280-D dense latent vector extraction and strict OOD boundary checks.
    """
    def __init__(self, num_classes: int = 5):
        super().__init__()
        base_model = models.efficientnet_b0(weights=None)
        self.features = base_model.features
        self.avgpool = base_model.avgpool
        in_features = base_model.classifier[1].in_features
        self.dropout = nn.Dropout(p=0.2, inplace=True)
        self.classifier = nn.Linear(in_features, num_classes)

    def extract_features(self, x: torch.Tensor) -> torch.Tensor:
        feat = self.features(x)
        feat = self.avgpool(feat)
        feat = torch.flatten(feat, 1)
        return feat

    def forward(self, x: torch.Tensor):
        feat = self.extract_features(x)
        out = self.dropout(feat)
        logits = self.classifier(out)
        return logits, feat


# ============================================================
# RESULT
# ============================================================

@dataclass
class PredictionResult:
    """
    Structured result from the Tur disease ML model with strict OOD enforcement.
    """

    disease_name: str
    confidence: float
    severity: str
    prediction_status: str = "completed"
    is_supported_class: bool = True
    rejection_reason: Optional[str] = None
    cosine_distance: Optional[float] = None


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
    EfficientNet-B0 based Tur leaf disease predictor with strict closed-set
    1280-D latent manifold validation.
    """

    def __init__(self) -> None:

        self._model = None

        self._classes: list[str] = []
        self._norm_centroids: Dict[str, np.ndarray] = {}
        self._class_thresholds: Dict[str, float] = {
            "Healthy": 0.46,
            "Leaf_Spot": 0.54,
            "Leaf_webber": 0.48,
            "Sterilic_mosaic": 0.58,
            "Wilt": 0.40,
        }

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
            model = TurEfficientNetB0(num_classes=num_classes)

            # Load trained weights (support both classifier.weight and classifier.1.weight)
            sd = checkpoint["model_state_dict"]
            new_sd = {}
            for k, v in sd.items():
                if k == "classifier.1.weight":
                    new_sd["classifier.weight"] = v
                elif k == "classifier.1.bias":
                    new_sd["classifier.bias"] = v
                else:
                    new_sd[k] = v

            model.load_state_dict(new_sd)
            model = model.to(DEVICE)
            model.eval()
            self._model = model

            # -----------------------------------------------
            # Load OOD Latent Feature Profile
            # -----------------------------------------------
            if OOD_PROFILE_PATH.exists():
                try:
                    with open(OOD_PROFILE_PATH, "r") as f:
                        profile_data = json.load(f)
                    cents = profile_data.get("centroids", {})
                    self._norm_centroids = {}
                    for c_name, c_vec in cents.items():
                        arr = np.array(c_vec, dtype=np.float32)
                        self._norm_centroids[c_name] = arr / (np.linalg.norm(arr) + 1e-8)
                    logger.info(
                        "[TurDiseasePredictor] Loaded OOD feature centroids for %d classes",
                        len(self._norm_centroids)
                    )
                except Exception as ood_err:
                    logger.warning("[TurDiseasePredictor] Could not parse OOD profile: %s", ood_err)

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
        Run EfficientNet-B0 inference on a stored scan image with strict
        multi-layer closed-set OOD validation.
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
            # Inference & Feature Extraction
            # -----------------------------------------------

            with torch.no_grad():

                logits, feat = self._model(
                    input_tensor
                )

                probabilities = torch.softmax(
                    logits,
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

            # -----------------------------------------------
            # Strict Closed-Set OOD Manifold Validation
            # -----------------------------------------------
            feat_vec = feat[0].cpu().numpy()
            norm_feat = feat_vec / (np.linalg.norm(feat_vec) + 1e-8)
            target_cent = self._norm_centroids.get(disease_name)

            if target_cent is not None:
                cos_dist = float(1.0 - np.dot(norm_feat, target_cent))
            else:
                cos_dist = 0.0

            sorted_probs = torch.sort(probabilities, descending=True).values
            prob_margin = float(sorted_probs[0] - sorted_probs[1]) if len(sorted_probs) > 1 else 1.0

            # Per-class calibrated boundary to prevent Wilt Sinkhole
            class_threshold = self._class_thresholds.get(disease_name, 0.45)
            is_rejected = (cos_dist > class_threshold) or (confidence < 0.70) or (prob_margin < 0.20)

            if is_rejected:
                logger.warning(
                    "[TurDiseasePredictor] STRICT OOD REJECTION: predicted=%s, "
                    "cos_dist=%.4f (threshold=%.4f), confidence=%.4f, margin=%.4f",
                    disease_name,
                    cos_dist,
                    class_threshold,
                    confidence,
                    prob_margin,
                )
                return PredictionResult(
                    disease_name="Unsupported_Disease",
                    confidence=confidence,
                    severity="low_confidence",
                    prediction_status="rejected",
                    is_supported_class=False,
                    rejection_reason="class_not_in_database",
                    cosine_distance=cos_dist,
                )

            logger.info(
                "[TurDiseasePredictor] Validated In-Distribution: %s "
                "(conf=%.4f, cos_dist=%.4f, margin=%.4f)",
                disease_name,
                confidence,
                cos_dist,
                prob_margin,
            )

            return PredictionResult(
                disease_name=disease_name,
                confidence=confidence,
                severity=confidence_level,
                prediction_status="completed",
                is_supported_class=True,
                cosine_distance=cos_dist,
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
