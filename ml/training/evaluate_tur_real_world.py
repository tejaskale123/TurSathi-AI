from pathlib import Path
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[2]

MODEL_PATH = ROOT / "models" / "tur_image_validator_efficientnet_b0_v2.pth"
TEST_DIR = ROOT / "datasets" / "tur_image_validator" / "real_world_test"


# ============================================================
# DEVICE
# ============================================================

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print("=" * 70)
print("TUR IMAGE VALIDATOR - REAL WORLD TEST")
print("=" * 70)
print(f"Device : {device}")
print(f"Model  : {MODEL_PATH}")
print(f"Test   : {TEST_DIR}")
print()


# ============================================================
# LOAD CHECKPOINT
# ============================================================

checkpoint = torch.load(
    MODEL_PATH,
    map_location=device,
    weights_only=False
)

classes = checkpoint["classes"]

print(f"Classes : {classes}")
print()


# ============================================================
# MODEL
# ============================================================

model = models.efficientnet_b0(weights=None)

in_features = model.classifier[1].in_features

model.classifier[1] = nn.Linear(
    in_features,
    len(classes)
)

model.load_state_dict(checkpoint["model_state_dict"])

model = model.to(device)
model.eval()


# ============================================================
# IMAGE TRANSFORM
# ============================================================

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])


# ============================================================
# REAL-WORLD IMAGES
# ============================================================

image_files = []

for extension in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
    image_files.extend(TEST_DIR.rglob(extension))

image_files = sorted(image_files)

print(f"Total real-world images : {len(image_files)}")
print()


# ============================================================
# PREDICTION
# ============================================================

correct = 0
total = 0

results = []

for image_path in image_files:

    # Folder name is the expected label
    actual_label = image_path.parent.name

    try:
        image = Image.open(image_path).convert("RGB")

        tensor = transform(image).unsqueeze(0).to(device)

        with torch.no_grad():
            output = model(tensor)

            probabilities = torch.softmax(output, dim=1)

            confidence, predicted_index = torch.max(
                probabilities,
                dim=1
            )

        predicted_label = classes[predicted_index.item()]
        confidence_value = confidence.item()

        is_correct = predicted_label == actual_label

        if is_correct:
            correct += 1

        total += 1

        results.append({
            "file": image_path.name,
            "actual": actual_label,
            "predicted": predicted_label,
            "confidence": confidence_value,
            "correct": is_correct
        })

    except Exception as e:

        print(f"ERROR: {image_path.name}")
        print(f"       {e}")


# ============================================================
# RESULTS
# ============================================================

print("=" * 70)
print("REAL-WORLD RESULTS")
print("=" * 70)

for result in results:

    status = "PASS" if result["correct"] else "FAIL"

    print(
        f"{status:5} | "
        f"{result['file']:<30} | "
        f"Actual: {result['actual']:<8} | "
        f"Predicted: {result['predicted']:<8} | "
        f"Confidence: {result['confidence']:.4f}"
    )


# ============================================================
# ACCURACY
# ============================================================

if total > 0:

    accuracy = correct / total

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print(f"Total images      : {total}")
    print(f"Correct           : {correct}")
    print(f"Incorrect         : {total - correct}")
    print(f"Real-world accuracy: {accuracy * 100:.2f}%")

else:

    print("No images were successfully evaluated.")