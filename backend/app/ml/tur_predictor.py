"""
ML Predictor interface for Tur leaf disease classification.

Architecture:
    API route → PredictionService → TurDiseasePredictor → Real ML model (future)

The predictor is intentionally decoupled from the API layer so that:
1. The real ML model can be plugged in here without touching the API or database.
2. The prediction service can call any model backend (local inference, remote API, etc.).
3. The absence of the ML model is cleanly signalled via ModelNotConfiguredError.

DO NOT:
- Invent disease names.
- Invent confidence values.
- Return fake predictions.
- Put ML inference code in the API route.

When the real model is ready:
    1. Load the model inside `TurDiseasePredictor.__init__`.
    2. Implement `predict()` to return real results.
    3. Set MODEL_AVAILABLE = True.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger("tursathi.ml")

# ── Feature flag ─────────────────────────────────────────────────────────────
# Set to True only when the real ML model files are present and loaded.
MODEL_AVAILABLE: bool = False


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class PredictionResult:
    """
    Structured result from the Tur disease ML model.
    All fields are populated only when prediction_status == "completed".
    """
    disease_name: str
    confidence: float          # 0.0 – 1.0
    severity: str              # "mild" | "moderate" | "severe"
    prediction_status: str = "completed"


# ── Custom exception ──────────────────────────────────────────────────────────

class ModelNotConfiguredError(Exception):
    """
    Raised when the Tur disease ML model is not yet configured.
    The API layer catches this and returns HTTP 503.
    """
    pass


# ── Predictor ─────────────────────────────────────────────────────────────────

class TurDiseasePredictor:
    """
    Clean abstraction layer for Tur leaf disease prediction.

    Future integration steps:
    1. Install the ML framework (e.g. torch, tensorflow, onnxruntime).
    2. Load your model weights in __init__ (e.g. from a .onnx or .pt file).
    3. Implement the prediction logic in predict().
    4. Set MODEL_AVAILABLE = True.
    5. No changes needed in the API layer or database layer.
    """

    def __init__(self) -> None:
        self._model = None
        if MODEL_AVAILABLE:
            self._load_model()

    def _load_model(self) -> None:
        """
        Load the Tur disease ML model weights.
        Implement this when the model is available.
        """
        logger.info("[TurDiseasePredictor] Loading Tur disease ML model...")
        # Example (future implementation):
        # import onnxruntime as ort
        # model_path = Path(__file__).parent / "weights" / "tur_disease_v1.onnx"
        # self._model = ort.InferenceSession(str(model_path))
        # logger.info("[TurDiseasePredictor] Model loaded successfully.")
        raise NotImplementedError("ML model loading not yet implemented.")

    def is_available(self) -> bool:
        """Returns True if the predictor is ready to make inferences."""
        return MODEL_AVAILABLE and self._model is not None

    def predict(self, image_path: Path) -> PredictionResult:
        """
        Run Tur leaf disease prediction on the provided image.

        Parameters
        ----------
        image_path : Absolute path to the stored scan image on the server filesystem.

        Returns
        -------
        PredictionResult with disease_name, confidence, severity.

        Raises
        ------
        ModelNotConfiguredError : If the ML model is not yet configured.
        FileNotFoundError       : If the image file does not exist.
        ValueError              : If the image cannot be processed.
        """
        if not self.is_available():
            raise ModelNotConfiguredError(
                "Tur disease ML model is not configured yet."
            )

        if not image_path.exists():
            raise FileNotFoundError(
                f"Scan image not found at expected path. Cannot run prediction."
            )

        # ── Implement real inference here when model is ready ─────────────────
        # Example skeleton:
        #
        # import PIL.Image
        # import numpy as np
        #
        # img = PIL.Image.open(image_path).convert("RGB")
        # img_resized = img.resize((224, 224))
        # input_array = np.array(img_resized, dtype=np.float32) / 255.0
        # input_tensor = input_array[np.newaxis, ...]
        #
        # outputs = self._model.run(None, {"input": input_tensor})
        # class_id = np.argmax(outputs[0])
        # confidence = float(np.max(outputs[0]))
        #
        # return PredictionResult(
        #     disease_name=CLASS_NAMES[class_id],
        #     confidence=confidence,
        #     severity=map_severity(confidence),
        # )
        # ─────────────────────────────────────────────────────────────────────

        raise ModelNotConfiguredError(
            "Tur disease ML model is not configured yet."
        )


# ── Module-level singleton (instantiated lazily) ───────────────────────────────

_predictor_instance: Optional[TurDiseasePredictor] = None


def get_predictor() -> TurDiseasePredictor:
    """Returns the module-level predictor singleton."""
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = TurDiseasePredictor()
    return _predictor_instance
