from pathlib import Path

import torch
import torch.nn as nn
from PIL import Image
from torchvision import models, transforms
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "best_ppld_efficientnet_b0.pth"
)

TEST_DIR = (
    PROJECT_ROOT
    / "PPLD_processed"
    / "test"
)

RESULTS_PATH = (
    PROJECT_ROOT
    / "models"
    / "ppld_saved_model_evaluation.txt"
)


# ============================================================
# DEVICE
# ============================================================

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

print("=" * 70)
print("TurSathi AI - Saved PPLD Model Full Evaluation")
print("=" * 70)

print(f"Device : {DEVICE}")

if torch.cuda.is_available():
    print(f"GPU    : {torch.cuda.get_device_name(0)}")

print("=" * 70)


# ============================================================
# CHECK PATHS
# ============================================================

if not MODEL_PATH.exists():
    raise FileNotFoundError(
        f"Model not found: {MODEL_PATH}"
    )

if not TEST_DIR.exists():
    raise FileNotFoundError(
        f"Test directory not found: {TEST_DIR}"
    )


# ============================================================
# LOAD CHECKPOINT
# ============================================================

checkpoint = torch.load(
    MODEL_PATH,
    map_location=DEVICE,
    weights_only=False,
)

classes = checkpoint["classes"]
num_classes = len(classes)

print("\nModel:")
print(f"  Name             : {checkpoint['model_name']}")
print(f"  Classes          : {classes}")
print(f"  Best Val Accuracy: "
      f"{checkpoint['best_val_accuracy'] * 100:.2f}%")
print(f"  Best Epoch       : {checkpoint['best_epoch']}")


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
# IMAGE TRANSFORM
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
# COLLECT TEST IMAGES
# ============================================================

image_extensions = {
    ".jpg",
    ".jpeg",
    ".png",
}

test_images = []

for class_name in classes:

    class_dir = TEST_DIR / class_name

    if not class_dir.exists():
        raise FileNotFoundError(
            f"Class directory not found: {class_dir}"
        )

    for image_path in sorted(class_dir.iterdir()):

        if image_path.suffix.lower() in image_extensions:

            test_images.append(
                (image_path, class_name)
            )


print("\nTest images found:")
print(f"  Total: {len(test_images)}")

for class_name in classes:

    count = sum(
        1
        for _, actual in test_images
        if actual == class_name
    )

    print(
        f"  {class_name}: {count}"
    )


# ============================================================
# FULL INFERENCE
# ============================================================

all_actual = []
all_predicted = []

correct = 0

print("\n" + "=" * 70)
print("RUNNING INFERENCE")
print("=" * 70)


with torch.no_grad():

    for index, (image_path, actual_class) in enumerate(
        test_images,
        start=1,
    ):

        image = Image.open(
            image_path
        ).convert("RGB")

        tensor = transform(
            image
        ).unsqueeze(0).to(DEVICE)

        output = model(tensor)

        probabilities = torch.softmax(
            output,
            dim=1,
        )[0]

        predicted_index = probabilities.argmax().item()

        predicted_class = classes[
            predicted_index
        ]

        all_actual.append(
            actual_class
        )

        all_predicted.append(
            predicted_class
        )

        if predicted_class == actual_class:
            correct += 1


        # Progress
        if index % 25 == 0 or index == len(test_images):

            print(
                f"Processed: {index}/{len(test_images)}"
            )


# ============================================================
# ACCURACY
# ============================================================

accuracy = accuracy_score(
    all_actual,
    all_predicted,
)

print("\n" + "=" * 70)
print("FINAL SAVED MODEL EVALUATION")
print("=" * 70)

print(
    f"\nCorrect predictions : {correct}/{len(test_images)}"
)

print(
    f"Incorrect predictions: "
    f"{len(test_images) - correct}/{len(test_images)}"
)

print(
    f"Test Accuracy       : "
    f"{accuracy * 100:.2f}%"
)


# ============================================================
# CLASSIFICATION REPORT
# ============================================================

report = classification_report(
    all_actual,
    all_predicted,
    labels=classes,
    target_names=classes,
    digits=4,
    zero_division=0,
)

print("\nClassification Report:")
print(report)


# ============================================================
# CONFUSION MATRIX
# ============================================================

matrix = confusion_matrix(
    all_actual,
    all_predicted,
    labels=classes,
)

print("Confusion Matrix:")

print(
    "                "
    + " ".join(
        f"{name[:10]:>12}"
        for name in classes
    )
)

for class_name, row in zip(
    classes,
    matrix,
):

    print(
        f"{class_name[:15]:<15}"
        + " ".join(
            f"{value:>12}"
            for value in row
        )
    )


# ============================================================
# SAVE EVALUATION REPORT
# ============================================================

with open(
    RESULTS_PATH,
    "w",
    encoding="utf-8",
) as file:

    file.write(
        "TurSathi AI - Saved PPLD Model Evaluation\n"
    )

    file.write(
        "=" * 60 + "\n\n"
    )

    file.write(
        f"Model: {checkpoint['model_name']}\n"
    )

    file.write(
        f"Best Validation Accuracy: "
        f"{checkpoint['best_val_accuracy'] * 100:.2f}%\n"
    )

    file.write(
        f"Best Epoch: "
        f"{checkpoint['best_epoch']}\n\n"
    )

    file.write(
        f"Total Test Images: "
        f"{len(test_images)}\n"
    )

    file.write(
        f"Correct Predictions: "
        f"{correct}\n"
    )

    file.write(
        f"Incorrect Predictions: "
        f"{len(test_images) - correct}\n"
    )

    file.write(
        f"Test Accuracy: "
        f"{accuracy * 100:.2f}%\n\n"
    )

    file.write(
        "Classification Report:\n"
    )

    file.write(
        report
    )

    file.write(
        "\nConfusion Matrix:\n"
    )

    file.write(
        "Classes: "
        + ", ".join(classes)
        + "\n"
    )

    for row in matrix:

        file.write(
            " ".join(
                map(str, row)
            )
            + "\n"
        )


# ============================================================
# FINAL
# ============================================================

print("\nEvaluation report saved:")
print(RESULTS_PATH)

print("\n" + "=" * 70)
print("EVALUATION COMPLETE")
print("=" * 70)