from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms
from sklearn.metrics import classification_report, confusion_matrix


# ============================================================
# CONFIG
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

DATASET_DIR = ROOT / "datasets" / "tur_image_validator"
MODEL_PATH = ROOT / "models" / "tur_image_validator_efficientnet_b0.pth"

IMAGE_SIZE = 224
BATCH_SIZE = 32

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print("=" * 70)
print("TurSathi AI - Tur Image Validator Evaluation")
print("=" * 70)

print(f"Device : {DEVICE}")
print(f"Model  : {MODEL_PATH}")
print(f"Test   : {DATASET_DIR / 'test'}")


# ============================================================
# TRANSFORM
# ============================================================

test_transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    ),
])


# ============================================================
# TEST DATASET
# ============================================================

test_dataset = datasets.ImageFolder(
    DATASET_DIR / "test",
    transform=test_transform,
)

test_loader = DataLoader(
    test_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    num_workers=0,
)


print("\nClasses:")
print(test_dataset.class_to_idx)

print(f"\nTest images: {len(test_dataset)}")


# ============================================================
# MODEL
# ============================================================

model = models.efficientnet_b0(weights=None)

in_features = model.classifier[1].in_features

model.classifier[1] = nn.Linear(
    in_features,
    2,
)

checkpoint = torch.load(
    MODEL_PATH,
    map_location=DEVICE,
    weights_only=False,
)

model.load_state_dict(
    checkpoint["model_state_dict"]
)

model = model.to(DEVICE)
model.eval()


# ============================================================
# PREDICTIONS
# ============================================================

all_labels = []
all_predictions = []

with torch.no_grad():

    for images, labels in test_loader:

        images = images.to(DEVICE)

        outputs = model(images)

        predictions = outputs.argmax(dim=1)

        all_labels.extend(
            labels.cpu().tolist()
        )

        all_predictions.extend(
            predictions.cpu().tolist()
        )


# ============================================================
# CONFUSION MATRIX
# ============================================================

cm = confusion_matrix(
    all_labels,
    all_predictions,
)

print("\n" + "=" * 70)
print("CONFUSION MATRIX")
print("=" * 70)

print("             Predicted")
print("             Not_Tur   Tur")

print(
    f"Actual Not_Tur   {cm[0][0]:5d}   {cm[0][1]:5d}"
)

print(
    f"Actual Tur       {cm[1][0]:5d}   {cm[1][1]:5d}"
)


# ============================================================
# CLASSIFICATION REPORT
# ============================================================

print("\n" + "=" * 70)
print("CLASSIFICATION REPORT")
print("=" * 70)

print(
    classification_report(
        all_labels,
        all_predictions,
        target_names=["Not_Tur", "Tur"],
        digits=4,
    )
)


# ============================================================
# ACCURACY
# ============================================================

correct = sum(
    p == y
    for p, y in zip(
        all_predictions,
        all_labels,
    )
)

total = len(all_labels)

accuracy = correct / total

print("=" * 70)
print("FINAL EVALUATION")
print("=" * 70)

print(f"Correct predictions : {correct}/{total}")
print(f"Test Accuracy       : {accuracy * 100:.2f}%")

print("=" * 70)