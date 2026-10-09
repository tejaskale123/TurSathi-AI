from pathlib import Path

import torch
import torch.nn as nn
from PIL import Image
from torchvision import models, transforms


class TurImageValidator:
    """
    Validates whether an uploaded image is a Tur/Pigeonpea image
    before sending it to the disease classifier.
    """

    def __init__(self, model_path: str | Path | None = None):
        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        if model_path is None:
            project_root = Path(__file__).resolve().parents[3]
            model_path = (
                project_root
                / "models"
                / "tur_image_validator_efficientnet_b0_v3.pth"
            )

        self.model_path = Path(model_path)

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Tur validator model not found: {self.model_path}"
            )

        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ])

        checkpoint = torch.load(
            self.model_path,
            map_location=self.device,
            weights_only=False,
        )

        # Support both V1 dict format and V3 pure state_dict format
        if isinstance(checkpoint, dict) and "classes" in checkpoint:
            self.classes = checkpoint["classes"]
            self.class_to_idx = checkpoint["class_to_idx"]
            state_dict = checkpoint["model_state_dict"]
        else:
            self.classes = ["Not_Tur", "Tur"]
            self.class_to_idx = {"Not_Tur": 0, "Tur": 1}
            state_dict = checkpoint

        self.model = models.efficientnet_b0(weights=None)

        in_features = self.model.classifier[1].in_features

        self.model.classifier[1] = nn.Linear(
            in_features,
            len(self.classes),
        )

        self.model.load_state_dict(state_dict)

        self.model = self.model.to(self.device)
        self.model.eval()

    @torch.no_grad()
    def predict(self, image: Image.Image) -> dict:
        """
        Predict whether the image is Tur or Not_Tur.
        """

        if image.mode != "RGB":
            image = image.convert("RGB")

        tensor = self.transform(image)
        tensor = tensor.unsqueeze(0).to(self.device)

        outputs = self.model(tensor)

        probabilities = torch.softmax(
            outputs,
            dim=1,
        )

        confidence, predicted_index = torch.max(
            probabilities,
            dim=1,
        )

        predicted_index = predicted_index.item()
        confidence = confidence.item()

        label = self.classes[predicted_index]

        return {
            "is_tur": label == "Tur",
            "label": label,
            "confidence": round(confidence, 4),
        }