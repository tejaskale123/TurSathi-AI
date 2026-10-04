from pathlib import Path
import copy
import json

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms
from torchvision.models import EfficientNet_B0_Weights

from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score,
)


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATASET_DIR = PROJECT_ROOT / "datasets" / "pigeonpea_disease_clean"

MODEL_DIR = PROJECT_ROOT / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

BEST_MODEL_PATH = MODEL_DIR / "best_pigeonpea_disease_efficientnet_b0.pth"
RESULTS_PATH = MODEL_DIR / "pigeonpea_disease_training_results.json"
CONFUSION_MATRIX_PATH = MODEL_DIR / "pigeonpea_disease_confusion_matrix.txt"

IMAGE_SIZE = 224
BATCH_SIZE = 16
NUM_WORKERS = 0

EPOCHS = 30
LEARNING_RATE = 1e-4
WEIGHT_DECAY = 1e-4

EARLY_STOPPING_PATIENCE = 7

SEED = 42


# ============================================================
# REPRODUCIBILITY
# ============================================================

torch.manual_seed(SEED)

if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)


# ============================================================
# DEVICE
# ============================================================

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print("=" * 70)
print("TurSathi AI - PPLD EfficientNet-B0 Training")
print("=" * 70)

print(f"Project root : {PROJECT_ROOT}")
print(f"Dataset      : {DATASET_DIR}")
print(f"Device       : {DEVICE}")

if torch.cuda.is_available():
    print(f"GPU          : {torch.cuda.get_device_name(0)}")
    print(f"CUDA         : {torch.version.cuda}")
    print(f"VRAM         : {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")

print("=" * 70)


# ============================================================
# DATA TRANSFORMS
# ============================================================

train_transforms = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),

    transforms.RandomHorizontalFlip(p=0.5),
    transforms.RandomVerticalFlip(p=0.2),
    transforms.RandomRotation(15),

    transforms.ColorJitter(
        brightness=0.15,
        contrast=0.15,
        saturation=0.15,
        hue=0.03,
    ),

    transforms.ToTensor(),

    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    ),
])


eval_transforms = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),

    transforms.ToTensor(),

    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225],
    ),
])


# ============================================================
# DATASETS
# ============================================================

train_dir = DATASET_DIR / "train"
val_dir = DATASET_DIR / "val"
test_dir = DATASET_DIR / "test"

if not train_dir.exists():
    raise FileNotFoundError(f"Training directory not found: {train_dir}")

if not val_dir.exists():
    raise FileNotFoundError(f"Validation directory not found: {val_dir}")

if not test_dir.exists():
    raise FileNotFoundError(f"Test directory not found: {test_dir}")


train_dataset = datasets.ImageFolder(
    train_dir,
    transform=train_transforms,
)

val_dataset = datasets.ImageFolder(
    val_dir,
    transform=eval_transforms,
)

test_dataset = datasets.ImageFolder(
    test_dir,
    transform=eval_transforms,
)


# ============================================================
# CLASS CHECK
# ============================================================

class_names = train_dataset.classes
num_classes = len(class_names)

print("\nClasses:")
for index, class_name in enumerate(class_names):
    print(f"  {index}: {class_name}")

print(f"\nNumber of classes: {num_classes}")

if class_names != val_dataset.classes:
    raise ValueError("Train and validation class order does not match.")

if class_names != test_dataset.classes:
    raise ValueError("Train and test class order does not match.")


# ============================================================
# DATALOADERS
# ============================================================

train_loader = DataLoader(
    train_dataset,
    batch_size=BATCH_SIZE,
    shuffle=True,
    num_workers=NUM_WORKERS,
    pin_memory=torch.cuda.is_available(),
)

val_loader = DataLoader(
    val_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    num_workers=NUM_WORKERS,
    pin_memory=torch.cuda.is_available(),
)

test_loader = DataLoader(
    test_dataset,
    batch_size=BATCH_SIZE,
    shuffle=False,
    num_workers=NUM_WORKERS,
    pin_memory=torch.cuda.is_available(),
)


print("\nDataset sizes:")
print(f"  Train: {len(train_dataset)}")
print(f"  Val  : {len(val_dataset)}")
print(f"  Test : {len(test_dataset)}")


# ============================================================
# MODEL
# ============================================================

print("\nLoading EfficientNet-B0 pretrained weights...")

weights = EfficientNet_B0_Weights.DEFAULT

model = models.efficientnet_b0(weights=weights)

# Replace final classifier
in_features = model.classifier[1].in_features

model.classifier[1] = nn.Linear(
    in_features,
    num_classes,
)

model = model.to(DEVICE)


# ============================================================
# LOSS / OPTIMIZER
# ============================================================

criterion = nn.CrossEntropyLoss()

optimizer = optim.AdamW(
    model.parameters(),
    lr=LEARNING_RATE,
    weight_decay=WEIGHT_DECAY,
)

scheduler = optim.lr_scheduler.ReduceLROnPlateau(
    optimizer,
    mode="max",
    factor=0.5,
    patience=2,
)


# ============================================================
# TRAINING FUNCTION
# ============================================================

def train_one_epoch(model, loader, criterion, optimizer):
    model.train()

    running_loss = 0.0
    correct = 0
    total = 0

    for images, labels in loader:

        images = images.to(DEVICE, non_blocking=True)
        labels = labels.to(DEVICE, non_blocking=True)

        optimizer.zero_grad(set_to_none=True)

        outputs = model(images)

        loss = criterion(outputs, labels)

        loss.backward()

        optimizer.step()

        running_loss += loss.item() * images.size(0)

        predictions = outputs.argmax(dim=1)

        correct += (predictions == labels).sum().item()
        total += labels.size(0)

    epoch_loss = running_loss / total
    epoch_accuracy = correct / total

    return epoch_loss, epoch_accuracy


# ============================================================
# VALIDATION FUNCTION
# ============================================================

def evaluate(model, loader, criterion):
    model.eval()

    running_loss = 0.0
    correct = 0
    total = 0

    all_labels = []
    all_predictions = []

    with torch.no_grad():

        for images, labels in loader:

            images = images.to(DEVICE, non_blocking=True)
            labels = labels.to(DEVICE, non_blocking=True)

            outputs = model(images)

            loss = criterion(outputs, labels)

            running_loss += loss.item() * images.size(0)

            predictions = outputs.argmax(dim=1)

            correct += (predictions == labels).sum().item()
            total += labels.size(0)

            all_labels.extend(labels.cpu().numpy())
            all_predictions.extend(predictions.cpu().numpy())

    epoch_loss = running_loss / total
    epoch_accuracy = correct / total

    return (
        epoch_loss,
        epoch_accuracy,
        all_labels,
        all_predictions,
    )


# ============================================================
# TRAINING LOOP
# ============================================================

best_val_accuracy = 0.0
best_epoch = 0
patience_counter = 0

best_model_state = None

history = {
    "train_loss": [],
    "train_accuracy": [],
    "val_loss": [],
    "val_accuracy": [],
}


print("\n" + "=" * 70)
print("STARTING TRAINING")
print("=" * 70)


for epoch in range(1, EPOCHS + 1):

    train_loss, train_accuracy = train_one_epoch(
        model,
        train_loader,
        criterion,
        optimizer,
    )

    (
        val_loss,
        val_accuracy,
        _,
        _,
    ) = evaluate(
        model,
        val_loader,
        criterion,
    )

    scheduler.step(val_accuracy)

    history["train_loss"].append(train_loss)
    history["train_accuracy"].append(train_accuracy)

    history["val_loss"].append(val_loss)
    history["val_accuracy"].append(val_accuracy)

    current_lr = optimizer.param_groups[0]["lr"]

    print(
        f"Epoch [{epoch:02d}/{EPOCHS}] | "
        f"Train Loss: {train_loss:.4f} | "
        f"Train Acc: {train_accuracy * 100:.2f}% | "
        f"Val Loss: {val_loss:.4f} | "
        f"Val Acc: {val_accuracy * 100:.2f}% | "
        f"LR: {current_lr:.2e}"
    )

    # --------------------------------------------------------
    # SAVE BEST MODEL
    # --------------------------------------------------------

    if val_accuracy > best_val_accuracy:

        best_val_accuracy = val_accuracy
        best_epoch = epoch
        patience_counter = 0

        best_model_state = copy.deepcopy(model.state_dict())

        checkpoint = {
            "model_name": "efficientnet_b0",
            "classes": class_names,
            "num_classes": num_classes,
            "image_size": IMAGE_SIZE,
            "best_val_accuracy": best_val_accuracy,
            "best_epoch": best_epoch,
            "model_state_dict": best_model_state,
        }

        torch.save(
            checkpoint,
            BEST_MODEL_PATH,
        )

        print(
            f"  -> Best model saved "
            f"(Val Acc: {best_val_accuracy * 100:.2f}%)"
        )

    else:

        patience_counter += 1

        print(
            f"  -> No improvement "
            f"({patience_counter}/{EARLY_STOPPING_PATIENCE})"
        )

    # --------------------------------------------------------
    # EARLY STOPPING
    # --------------------------------------------------------

    if patience_counter >= EARLY_STOPPING_PATIENCE:

        print("\nEarly stopping triggered.")

        break


# ============================================================
# LOAD BEST MODEL
# ============================================================

if best_model_state is not None:

    model.load_state_dict(best_model_state)

else:

    checkpoint = torch.load(
        BEST_MODEL_PATH,
        map_location=DEVICE,
        weights_only=False,
    )

    model.load_state_dict(
        checkpoint["model_state_dict"]
    )


# ============================================================
# FINAL TEST EVALUATION
# ============================================================

print("\n" + "=" * 70)
print("FINAL TEST EVALUATION")
print("=" * 70)

(
    test_loss,
    test_accuracy,
    test_labels,
    test_predictions,
) = evaluate(
    model,
    test_loader,
    criterion,
)


print(f"\nTest Loss     : {test_loss:.4f}")
print(f"Test Accuracy : {test_accuracy * 100:.2f}%")


# ============================================================
# CLASSIFICATION REPORT
# ============================================================

report = classification_report(
    test_labels,
    test_predictions,
    target_names=class_names,
    digits=4,
    zero_division=0,
)

print("\nClassification Report:")
print(report)


# ============================================================
# CONFUSION MATRIX
# ============================================================

cm = confusion_matrix(
    test_labels,
    test_predictions,
)

print("Confusion Matrix:")
print(cm)

with open(
    CONFUSION_MATRIX_PATH,
    "w",
    encoding="utf-8",
) as file:

    file.write("Classes:\n")

    for index, name in enumerate(class_names):
        file.write(f"{index}: {name}\n")

    file.write("\nConfusion Matrix:\n")

    for row in cm:
        file.write(" ".join(map(str, row)) + "\n")


# ============================================================
# SAVE TRAINING RESULTS
# ============================================================

results = {
    "model": "EfficientNet-B0",
    "dataset": "pigeonpea_disease_clean",
    "classes": class_names,
    "num_classes": num_classes,
    "image_size": IMAGE_SIZE,
    "batch_size": BATCH_SIZE,
    "epochs_requested": EPOCHS,
    "best_epoch": best_epoch,
    "best_validation_accuracy": best_val_accuracy,
    "test_loss": test_loss,
    "test_accuracy": test_accuracy,
    "train_samples": len(train_dataset),
    "validation_samples": len(val_dataset),
    "test_samples": len(test_dataset),
    "history": history,
}

with open(
    RESULTS_PATH,
    "w",
    encoding="utf-8",
) as file:

    json.dump(
        results,
        file,
        indent=4,
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("TRAINING COMPLETE")
print("=" * 70)

print(f"Best validation accuracy : {best_val_accuracy * 100:.2f}%")
print(f"Best epoch              : {best_epoch}")
print(f"Test accuracy           : {test_accuracy * 100:.2f}%")

print(f"\nBest model:")
print(BEST_MODEL_PATH)

print(f"\nTraining results:")
print(RESULTS_PATH)

print(f"\nConfusion matrix:")
print(CONFUSION_MATRIX_PATH)

print("=" * 70)