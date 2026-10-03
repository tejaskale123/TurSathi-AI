from pathlib import Path

import torch
import torch.nn as nn
from PIL import Image
from torchvision import models, transforms


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL_PATH = PROJECT_ROOT / "models" / "best_ppld_efficientnet_b0.pth"

IMAGE_PATH = (
    PROJECT_ROOT
    / "PPLD_processed"
    / "test"
    / "Healthy"
    / "Healthy_0000.jpg"
)


# ============================================================
# DEVICE
# ============================================================

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print("=" * 70)
print("TurSathi AI - PPLD Saved Model Inference Test")
print("=" * 70)

print(f"Device : {DEVICE}")

if torch.cuda.is_available():
    print(f"GPU    : {torch.cuda.get_device_name(0)}")

print("=" * 70)


# ============================================================
# LOAD CHECKPOINT
# ============================================================

if not MODEL_PATH.exists():
    raise FileNotFoundError(
        f"Model not found: {MODEL_PATH}"
    )

if not IMAGE_PATH.exists():
    raise FileNotFoundError(
        f"Image not found: {IMAGE_PATH}"
    )


checkpoint = torch.load(
    MODEL_PATH,
    map_location=DEVICE,
    weights_only=False,
)

classes = checkpoint["classes"]

num_classes = len(classes)

print("\nModel information:")
print(f"Model              : {checkpoint.get('model_name', 'Unknown')}")
print(f"Classes            : {classes}")
print(f"Number of classes  : {num_classes}")
print(
    f"Best validation accuracy: "
    f"{checkpoint.get('best_val_accuracy', 0) * 100:.2f}%"
)
print(
    f"Best epoch         : "
    f"{checkpoint.get('best_epoch', 'Unknown')}"
)


# ============================================================
# CREATE MODEL
# ============================================================

model = models.efficientnet_b0(
    weights=None
)

in_features = model.classifier[1].in_features

model.classifier[1] = nn.Linear(
    in_features,
    num_classes,
)

model.load_state_dict(
    checkpoint["model_state_dict"]
)

model = model.to(DEVICE)

model.eval()


# ============================================================
# IMAGE TRANSFORMATION
# ============================================================

transform = transforms.Compose([
    transforms.Resize((224, 224)),

    transforms.ToTensor(),

    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    ),
])


# ============================================================
# LOAD IMAGE
# ============================================================

image = Image.open(
    IMAGE_PATH
).convert("RGB")

input_tensor = transform(
    image
).unsqueeze(0)

input_tensor = input_tensor.to(
    DEVICE
)


# ============================================================
# INFERENCE
# ============================================================

with torch.no_grad():

    output = model(
        input_tensor
    )

    probabilities = torch.softmax(
        output,
        dim=1,
    )[0]

    predicted_index = probabilities.argmax().item()

    predicted_class = classes[
        predicted_index
    ]

    confidence = probabilities[
        predicted_index
    ].item()


# ============================================================
# RESULTS
# ============================================================

actual_class = IMAGE_PATH.parent.name

print("\n" + "=" * 70)
print("INFERENCE RESULT")
print("=" * 70)

print(f"Image     : {IMAGE_PATH.name}")
print(f"Actual    : {actual_class}")
print(f"Predicted : {predicted_class}")
print(f"Confidence: {confidence * 100:.2f}%")

print("\nAll class probabilities:")

for index, class_name in enumerate(classes):

    probability = probabilities[
        index
    ].item() * 100

    print(
        f"  {class_name:<20} "
        f"{probability:.2f}%"
    )


# ============================================================
# RESULT CHECK
# ============================================================

print("\n" + "=" * 70)

if predicted_class == actual_class:

    print("RESULT: CORRECT PREDICTION")

else:

    print("RESULT: INCORRECT PREDICTION")

print("=" * 70)