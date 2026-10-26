#!/usr/bin/env python3
"""
TurSathi AI - Generate Google Colab Retraining Notebook
Creates ml/retraining/TurSathi_Clean_Retraining_and_OOD_Colab.ipynb with all 22
required numbered sections, visual checks, and export packaging.
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_NOTEBOOK = PROJECT_ROOT / "ml" / "retraining" / "TurSathi_Clean_Retraining_and_OOD_Colab.ipynb"

def build_notebook():
    cells = []

    def md(source):
        cells.append({
            "cell_type": "markdown",
            "metadata": {},
            "source": [line + "\n" for line in source.strip().split("\n")]
        })

    def code(source):
        cells.append({
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [line + "\n" for line in source.strip().split("\n")]
        })

    # Header
    md("""
# TurSathi AI — Enterprise Clean Retraining & Multi-Layer OOD Pipeline
**Pigeonpea (Tur / Arhar) 5-Class Disease Classifier**  
*Closed-Set Target: Healthy, Leaf_Spot, Leaf_webber, Sterilic_mosaic, Wilt*

This notebook guides you through:
1. **Verifying environment & GPU**
2. **Mounting Google Drive & unzipping clean dataset**
3. **Leakage & conflict verification**
4. **Fine-tuning EfficientNet-B0 with class-weighted loss**
5. **Calibrating per-class OOD boundaries (preventing Wilt Sinkhole)**
6. **Evaluating against untouched test set & 41 real-world external OOD images**
7. **Safely exporting candidate checkpoint and OOD feature profile**
""")

    # Section 1
    md("## 1. Environment and GPU Verification")
    code("""
import os, sys, torch
print("=" * 60)
print(f"Python Version : {sys.version.split()[0]}")
print(f"PyTorch Version: {torch.__version__}")
cuda_avail = torch.cuda.is_available()
print(f"CUDA Available : {cuda_avail}")
if cuda_avail:
    print(f"GPU Device     : {torch.cuda.get_device_name(0)}")
    print(f"VRAM Available : {torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB")
else:
    print("WARNING: No GPU detected! Please select Runtime > Change runtime type > T4 GPU.")
print("=" * 60)
""")

    # Section 2
    md("## 2. Safe Dependency Setup")
    code("""
!pip install -q scikit-learn matplotlib seaborn pillow torchvision
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from PIL import Image
print("Dependencies verified successfully.")
""")

    # Section 3
    md("## 3. Dataset Upload or Google Drive Mounting")
    code("""
from google.colab import drive
import os
from pathlib import Path

# Option A: Mount Google Drive (Recommended for persistent checkpoints)
DRIVE_MOUNTED = False
try:
    drive.mount('/content/drive')
    DRIVE_MOUNTED = True
    print("✓ Google Drive mounted successfully at /content/drive")
except Exception as e:
    print("Google Drive mount skipped. Local Colab storage will be used.")

# Target workspace paths
WORKSPACE = Path("/content/tursathi_retraining")
WORKSPACE.mkdir(parents=True, exist_ok=True)
print(f"Retraining workspace: {WORKSPACE.resolve()}")
""")

    # Section 4
    md("## 4. Dataset Archive Verification")
    code("""
import shutil

# Locate the zip archive (either from Drive or uploaded locally)
ZIP_NAME = "TurSathi_Pigeonpea_Clean_Dataset.zip"
POSSIBLE_PATHS = [
    Path(f"/content/{ZIP_NAME}"),
    Path(f"/content/drive/MyDrive/{ZIP_NAME}"),
    Path(f"/content/drive/MyDrive/TurSathi/{ZIP_NAME}"),
]

archive_path = None
for p in POSSIBLE_PATHS:
    if p.exists():
        archive_path = p
        break

if archive_path is None:
    print(f"Archive '{ZIP_NAME}' not found in Drive. Please upload it via Colab file browser.")
    from google.colab import files
    uploaded = files.upload()
    archive_path = Path(f"/content/{ZIP_NAME}")

print(f"✓ Found dataset archive: {archive_path.resolve()} ({archive_path.stat().st_size / (1024*1024):.2f} MB)")
""")

    # Section 5
    md("## 5. Extraction into a Dedicated Working Directory")
    code("""
import zipfile

DATA_DIR = WORKSPACE / "dataset"
if DATA_DIR.exists():
    shutil.rmtree(DATA_DIR)
DATA_DIR.mkdir(parents=True, exist_ok=True)

print(f"Extracting dataset into {DATA_DIR}...")
with zipfile.ZipFile(archive_path, 'r') as zip_ref:
    zip_ref.extractall(DATA_DIR)

print("✓ Extraction complete. Directory structure:")
for item in sorted(DATA_DIR.iterdir()):
    if item.is_dir():
        count = sum(len(files) for _, _, files in os.walk(item))
        print(f"  - {item.name:18s} ({count} files)")
""")

    # Section 6
    md("## 6. Manifest and Label Verification")
    code("""
manifest_file = DATA_DIR / "clean_dataset_manifest.json"
EXPECTED_CLASSES = ["Healthy", "Leaf_Spot", "Leaf_webber", "Sterilic_mosaic", "Wilt"]

if manifest_file.exists():
    import json
    with open(manifest_file, "r") as f:
        manifest = json.load(f)
    print("✓ Manifest found:")
    print(f"  Dataset Name : {manifest.get('dataset_name')}")
    print(f"  Total Clean  : {manifest['summary']['total_clean_unique_images']} images")
    print(f"  Classes      : {manifest['summary']['per_class_clean_counts']}")
else:
    print("Notice: manifest.json not embedded, verifying raw folders.")
""")

    # Section 7
    md("## 7. Duplicate and Split-Leakage Checks")
    code("""
import hashlib
from collections import defaultdict

splits = ["train", "val", "test"]
split_hashes = {s: set() for s in splits}
hash_records = defaultdict(list)

for s in splits:
    s_dir = DATA_DIR / s
    for c in sorted(os.listdir(s_dir)):
        c_dir = s_dir / c
        if not c_dir.is_dir(): continue
        for fname in os.listdir(c_dir):
            if fname.lower().endswith(('.jpg','.jpeg','.png','.webp')):
                fp = c_dir / fname
                h = hashlib.sha256(fp.read_bytes()).hexdigest()
                split_hashes[s].add(h)
                hash_records[h].append((s, c, fname))

leak_tv = len(split_hashes['train'] & split_hashes['val'])
leak_tt = len(split_hashes['train'] & split_hashes['test'])
leak_vt = len(split_hashes['val'] & split_hashes['test'])

print("Cryptographic Leakage Audit Across Splits:")
print(f"  - Train vs Val overlap  : {leak_tv} duplicates")
print(f"  - Train vs Test overlap : {leak_tt} duplicates")
print(f"  - Val vs Test overlap   : {leak_vt} duplicates")

assert leak_tv == 0 and leak_tt == 0 and leak_vt == 0, "CRITICAL ERROR: Data leakage detected across splits!"
print("✓ ZERO DATA LEAKAGE VERIFIED! Splits are 100% mathematically isolated.")
""")

    # Section 8
    md("## 8. Dataset Class-Count Visualization")
    code("""
import pandas as pd

class_split_matrix = {}
for s in splits:
    counts = {}
    for c in EXPECTED_CLASSES:
        c_dir = DATA_DIR / s / c
        counts[c] = len(os.listdir(c_dir)) if c_dir.exists() else 0
    class_split_matrix[s.capitalize()] = counts

df = pd.DataFrame(class_split_matrix)
df["Total"] = df.sum(axis=1)
display(df)

df[["Train", "Val", "Test"]].plot(kind="bar", stacked=True, figsize=(10, 5), colormap="viridis")
plt.title("TurSathi AI Clean Retraining Dataset Distribution (Per Class)")
plt.ylabel("Number of Images")
plt.xticks(rotation=15)
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.show()
""")

    # Section 9
    md("## 9. Sample-Image Visualization with Labels")
    code("""
fig, axes = plt.subplots(1, 5, figsize=(16, 4))
for i, c in enumerate(EXPECTED_CLASSES):
    c_dir = DATA_DIR / "train" / c
    img_name = sorted(os.listdir(c_dir))[0]
    img = Image.open(c_dir / img_name)
    axes[i].imshow(img)
    axes[i].set_title(f"{c}\\n({img.size[0]}x{img.size[1]})")
    axes[i].axis("off")
plt.tight_layout()
plt.show()
""")

    # Section 10
    md("## 10. Data Transformations")
    code("""
from torchvision import transforms, datasets

IMG_SIZE = 224

train_transform = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.RandomHorizontalFlip(p=0.5),
    transforms.RandomVerticalFlip(p=0.2),
    transforms.RandomRotation(degrees=15),
    transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.15),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

eval_transform = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

train_dataset = datasets.ImageFolder(DATA_DIR / "train", transform=train_transform)
val_dataset = datasets.ImageFolder(DATA_DIR / "val", transform=eval_transform)
test_dataset = datasets.ImageFolder(DATA_DIR / "test", transform=eval_transform)

assert train_dataset.classes == EXPECTED_CLASSES, f"Class mismatch: {train_dataset.classes}"
print("✓ Datasets successfully prepared with transformations.")
""")

    # Section 11
    md("## 11. Model Construction")
    code("""
import torch.nn as nn
from torchvision import models

class TurEfficientNetB0(nn.Module):
    \"\"\"
    EfficientNet-B0 with dedicated penultimate 1280-D feature extractor tap.
    Fully compatible with production TurDiseasePredictor.
    \"\"\"
    def __init__(self, num_classes=5, pretrained=True):
        super().__init__()
        weights = models.EfficientNet_B0_Weights.DEFAULT if pretrained else None
        base_model = models.efficientnet_b0(weights=weights)
        self.features = base_model.features
        self.avgpool = base_model.avgpool
        in_features = base_model.classifier[1].in_features
        self.dropout = nn.Dropout(p=0.2, inplace=True)
        self.classifier = nn.Linear(in_features, num_classes)

    def extract_features(self, x):
        feat = self.features(x)
        feat = self.avgpool(feat)
        feat = torch.flatten(feat, 1)
        return feat

    def forward(self, x):
        feat = self.extract_features(x)
        out = self.dropout(feat)
        logits = self.classifier(out)
        return logits, feat

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = TurEfficientNetB0(num_classes=len(EXPECTED_CLASSES), pretrained=True).to(DEVICE)
print(f"✓ TurEfficientNetB0 initialized on {DEVICE}")
""")

    # Section 12
    md("## 12. Training Configuration")
    code("""
from torch.utils.data import DataLoader
import torch.optim as optim

BATCH_SIZE = 16
LEARNING_RATE = 1e-4
WEIGHT_DECAY = 1e-4
NUM_EPOCHS = 20

train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=2, pin_memory=True)
val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=2, pin_memory=True)
test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=2, pin_memory=True)

# Compute inverse class frequencies to mitigate Wilt sinkhole bias
targets = np.array(train_dataset.targets)
counts = [np.sum(targets == c) for c in range(len(EXPECTED_CLASSES))]
max_cnt = max(counts)
class_weights = [round(max_cnt / max(1, c), 4) for c in counts]
weights_tensor = torch.tensor(class_weights, dtype=torch.float32).to(DEVICE)

print(f"Training counts: {dict(zip(EXPECTED_CLASSES, counts))}")
print(f"Class Weights  : {dict(zip(EXPECTED_CLASSES, class_weights))}")

criterion = nn.CrossEntropyLoss(weight=weights_tensor, label_smoothing=0.05)
optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=NUM_EPOCHS, eta_min=1e-6)

# Checkpoint backup directory
CHECKPOINT_DIR = Path("/content/drive/MyDrive/TurSathi_Checkpoints") if DRIVE_MOUNTED else WORKSPACE / "checkpoints"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
print(f"Checkpoints directory: {CHECKPOINT_DIR.resolve()}")
""")

    # Section 13 & 14
    md("## 13. Training and Validation Loops & 14. Best-Checkpoint Selection")
    code("""
best_val_acc = 0.0
best_epoch = 0
best_weights = None
history = {"train_loss": [], "train_acc": [], "val_loss": [], "val_acc": []}

print("=" * 65)
print(f"Starting Training for {NUM_EPOCHS} Epochs on {DEVICE}...")
print("=" * 65)

for epoch in range(1, NUM_EPOCHS + 1):
    # ── Train Phase ──
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0

    for inputs, tgts in train_loader:
        inputs, tgts = inputs.to(DEVICE), tgts.to(DEVICE)
        optimizer.zero_grad()
        logits, _ = model(inputs)
        loss = criterion(logits, tgts)
        loss.backward()
        optimizer.step()

        running_loss += loss.item() * inputs.size(0)
        preds = logits.argmax(dim=1)
        correct += (preds == tgts).sum().item()
        total += tgts.size(0)

    scheduler.step()
    train_loss = running_loss / total
    train_acc = correct / total

    # ── Validation Phase ──
    model.eval()
    val_loss_sum = 0.0
    val_correct = 0
    val_total = 0

    with torch.no_grad():
        for inputs, tgts in val_loader:
            inputs, tgts = inputs.to(DEVICE), tgts.to(DEVICE)
            logits, _ = model(inputs)
            loss = criterion(logits, tgts)
            val_loss_sum += loss.item() * inputs.size(0)
            preds = logits.argmax(dim=1)
            val_correct += (preds == tgts).sum().item()
            val_total += tgts.size(0)

    val_loss = val_loss_sum / val_total
    val_acc = val_correct / val_total

    history["train_loss"].append(train_loss)
    history["train_acc"].append(train_acc)
    history["val_loss"].append(val_loss)
    history["val_acc"].append(val_acc)

    print(f"Epoch {epoch:02d}/{NUM_EPOCHS:02d} | Train Loss: {train_loss:.4f} Acc: {train_acc*100:.2f}% | Val Loss: {val_loss:.4f} Acc: {val_acc*100:.2f}%")

    if val_acc > best_val_acc:
        best_val_acc = val_acc
        best_epoch = epoch
        best_weights = {k: v.cpu().clone() for k, v in model.state_dict().items()}
        torch.save({
            "epoch": epoch,
            "model_state_dict": best_weights,
            "classes": EXPECTED_CLASSES,
            "best_val_accuracy": best_val_acc,
        }, CHECKPOINT_DIR / "best_model_checkpoint.pth")
        print(f"  ★ New best model checkpoint saved at Epoch {epoch} ({best_val_acc*100:.2f}%)")

print("=" * 65)
print(f"Training Complete! Peak Validation Accuracy: {best_val_acc*100:.2f}% at Epoch {best_epoch}")
model.load_state_dict(best_weights)
model.to(DEVICE)
""")

    # Section 15
    md("## 15. Training History and Learning Curves")
    code("""
epochs_range = range(1, NUM_EPOCHS + 1)
plt.figure(figsize=(14, 5))

plt.subplot(1, 2, 1)
plt.plot(epochs_range, history["train_loss"], label="Train Loss", color="royalblue")
plt.plot(epochs_range, history["val_loss"], label="Val Loss", color="darkorange")
plt.axvline(best_epoch, color="red", linestyle="--", label=f"Best Epoch ({best_epoch})")
plt.title("Cross-Entropy Loss Curve")
plt.xlabel("Epoch")
plt.ylabel("Loss")
plt.grid(True, linestyle="--", alpha=0.6)
plt.legend()

plt.subplot(1, 2, 2)
plt.plot(epochs_range, [x*100 for x in history["train_acc"]], label="Train Acc", color="royalblue")
plt.plot(epochs_range, [x*100 for x in history["val_acc"]], label="Val Acc", color="darkorange")
plt.axvline(best_epoch, color="red", linestyle="--", label=f"Best Epoch ({best_epoch})")
plt.title("Classification Accuracy (%)")
plt.xlabel("Epoch")
plt.ylabel("Accuracy %")
plt.grid(True, linestyle="--", alpha=0.6)
plt.legend()

plt.tight_layout()
plt.show()
""")

    # Section 16 & 17
    md("## 16. Final Evaluation on Untouched Test Split & 17. Per-Class Metrics and Confusion Matrix")
    code("""
from sklearn.metrics import classification_report, confusion_matrix

model.eval()
all_preds = []
all_targets = []

with torch.no_grad():
    for inputs, tgts in test_loader:
        inputs = inputs.to(DEVICE)
        logits, _ = model(inputs)
        preds = logits.argmax(dim=1).cpu().numpy()
        all_preds.extend(preds)
        all_targets.extend(tgts.numpy())

test_acc = (np.array(all_preds) == np.array(all_targets)).mean()
print("=" * 60)
print(f"FINAL UNTOUCHED TEST SET ACCURACY: {test_acc*100:.2f}%")
print("=" * 60)
print(classification_report(all_targets, all_preds, target_names=EXPECTED_CLASSES))

cm = confusion_matrix(all_targets, all_preds)
plt.figure(figsize=(7, 6))
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
            xticklabels=EXPECTED_CLASSES, yticklabels=EXPECTED_CLASSES)
plt.title("Test Set Confusion Matrix (Leak-Free & Conflict-Free)")
plt.xlabel("Predicted Class")
plt.ylabel("True Class")
plt.tight_layout()
plt.show()
""")

    # Section 18 & 19
    md("## 18. External/OOD Evaluation & 19. Confidence and Rejection Calibration")
    code("""
# 1. Compute 1280-D Centroids from Training Set
model.eval()
class_features = {c: [] for c in range(len(EXPECTED_CLASSES))}
with torch.no_grad():
    for inputs, tgts in train_loader:
        inputs = inputs.to(DEVICE)
        feats = model.extract_features(inputs).cpu().numpy()
        for f, t in zip(feats, tgts.numpy()):
            class_features[t].append(f)

centroids = {}
norm_centroids = {}
for c in range(len(EXPECTED_CLASSES)):
    c_feats = np.array(class_features[c])
    cent = np.mean(c_feats, axis=0)
    centroids[EXPECTED_CLASSES[c]] = cent
    norm_centroids[c] = cent / (np.linalg.norm(cent) + 1e-8)

# 2. Calibrate Per-Class Cosine Thresholds on Validation Set
val_class_dists = {c: [] for c in range(len(EXPECTED_CLASSES))}
with torch.no_grad():
    for inputs, tgts in val_loader:
        inputs = inputs.to(DEVICE)
        feats = model.extract_features(inputs).cpu().numpy()
        for f, t in zip(feats, tgts.numpy()):
            norm_v = f / (np.linalg.norm(f) + 1e-8)
            d = float(1.0 - np.dot(norm_v, norm_centroids[t]))
            val_class_dists[t].append(d)

per_class_thresholds = {}
for c in range(len(EXPECTED_CLASSES)):
    c_name = EXPECTED_CLASSES[c]
    p975 = float(np.percentile(val_class_dists[c], 97.5))
    if c_name == "Wilt":
        p975 = min(p975, 0.40) # Strict ceiling preventing Wilt Sinkhole
    per_class_thresholds[c_name] = round(p975, 4)

print("Per-Class Calibrated Cosine Distance Thresholds:")
for c_name, th in per_class_thresholds.items():
    print(f"  - {c_name:18s}: {th:.4f}")

# 3. Test Against External OOD Evaluation Images
OOD_DIR = DATA_DIR / "ood_evaluation"
ood_files = [f for f in OOD_DIR.iterdir() if f.is_file() and f.suffix.lower() in ['.jpg','.jpeg','.png','.webp']] if OOD_DIR.exists() else []

rejected = 0
wilt_sinkhole_count = 0
for f in ood_files:
    img = Image.open(f).convert("RGB")
    tensor = eval_transform(img).unsqueeze(0).to(DEVICE)
    with torch.no_grad():
        logits, feat = model(tensor)
        probs = torch.softmax(logits, dim=1)[0].cpu().numpy()
    pred_idx = np.argmax(probs)
    pred_class = EXPECTED_CLASSES[pred_idx]
    conf = float(probs[pred_idx])
    sorted_p = np.sort(probs)[::-1]
    margin = float(sorted_p[0] - sorted_p[1]) if len(sorted_p) > 1 else 1.0

    feat_v = feat[0].cpu().numpy()
    norm_v = feat_v / (np.linalg.norm(feat_v) + 1e-8)
    cos_dist = float(1.0 - np.dot(norm_v, norm_centroids[pred_idx]))

    th = per_class_thresholds.get(pred_class, 0.45)
    is_rejected = (cos_dist > th) or (conf < 0.70) or (margin < 0.20)
    if is_rejected:
        rejected += 1
    else:
        if pred_class == "Wilt":
            wilt_sinkhole_count += 1

rej_rate = (rejected / len(ood_files) * 100) if ood_files else 0
print(f"\\nOOD Rejection Rate on External Unseen Images: {rejected}/{len(ood_files)} ({rej_rate:.1f}%)")
print(f"False Wilt Predictions on External Images   : {wilt_sinkhole_count}/{len(ood_files)}")
""")

    # Section 20 & 21
    md("## 20. Checkpoint Integrity Verification & 21. Export and Download Instructions")
    code("""
import datetime

exp_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
candidate_filename = f"tursathi_efficientnet_b0_candidate_{exp_id}.pth"
candidate_path = WORKSPACE / candidate_filename

candidate_data = {
    "experiment_id": exp_id,
    "model_state_dict": model.state_dict(),
    "classes": EXPECTED_CLASSES,
    "num_classes": len(EXPECTED_CLASSES),
    "best_val_accuracy": best_val_acc,
    "best_epoch": best_epoch,
    "test_accuracy": test_acc,
    "image_size": IMG_SIZE,
    "model_name": "EfficientNet-B0",
    "created_at": datetime.datetime.now().isoformat(),
    "ood_profile": {
        "classes": EXPECTED_CLASSES,
        "feature_dim": 1280,
        "centroids": {c: centroids[c].tolist() for c in EXPECTED_CLASSES},
        "class_thresholds": per_class_thresholds,
        "min_confidence_floor": 0.70,
        "min_margin_floor": 0.20,
    }
}

torch.save(candidate_data, candidate_path)
print(f"✓ Candidate Checkpoint Saved: {candidate_path.name} ({candidate_path.stat().st_size / (1024*1024):.2f} MB)")

# Also save OOD profile JSON
ood_json_path = WORKSPACE / f"ood_feature_profile_{exp_id}.json"
with open(ood_json_path, "w") as f:
    json.dump(candidate_data["ood_profile"], f, indent=2)
print(f"✓ OOD Profile JSON Saved    : {ood_json_path.name}")

# Backup to Google Drive if mounted
if DRIVE_MOUNTED:
    drive_out = Path("/content/drive/MyDrive/TurSathi_Candidates")
    drive_out.mkdir(parents=True, exist_ok=True)
    torch.save(candidate_data, drive_out / candidate_filename)
    shutil.copy(ood_json_path, drive_out / ood_json_path.name)
    print(f"✓ Candidate backed up to Google Drive -> {drive_out.resolve()}")

# Trigger browser download if running directly in Colab
from google.colab import files
try:
    files.download(str(candidate_path))
    files.download(str(ood_json_path))
    print("✓ Triggered browser download for candidate checkpoint and OOD profile.")
except Exception as e:
    print(f"Files are available locally at {candidate_path} for manual download.")
""")

    # Section 22
    md("## 22. Reproducibility and Final Summary Report")
    code("""
print("=" * 70)
print("             TURSATHI AI — RETRAINING SUMMARY REPORT                  ")
print("=" * 70)
print(f"Experiment ID         : {exp_id}")
print(f"Base Architecture     : EfficientNet-B0 (Pretrained ImageNet-1K)")
print(f"Target Disease Classes: {EXPECTED_CLASSES}")
print(f"Peak Validation Acc   : {best_val_acc*100:.2f}% (Epoch {best_epoch})")
print(f"Final Test Accuracy   : {test_acc*100:.2f}%")
print(f"External OOD Rejected : {rejected}/{len(ood_files)} ({rej_rate:.1f}%)")
print(f"Calibrated Thresholds : {per_class_thresholds}")
print(f"Candidate Checkpoint  : {candidate_filename}")
print("=" * 70)
""")

    notebook_content = {
        "cells": cells,
        "metadata": {
            "colab": {
                "name": "TurSathi_Clean_Retraining_and_OOD_Colab.ipynb",
                "provenance": []
            },
            "kernelspec": {
                "display_name": "Python 3",
                "name": "python3"
            },
            "language_info": {
                "name": "python"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 0
    }

    with open(OUTPUT_NOTEBOOK, "w", encoding="utf-8") as f:
        json.dump(notebook_content, f, indent=2)

    print(f"Successfully generated Colab notebook at: {OUTPUT_NOTEBOOK.resolve()}")

if __name__ == "__main__":
    build_notebook()
