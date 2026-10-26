#!/usr/bin/env python3
"""
================================================================================
TurSathi AI - Enterprise Clean Retraining Pipeline
Leak-Free Stratified Dataset, Multi-Layer Validation, Feature Extraction,
Class-Weighted Loss, Per-Class OOD Boundary Calibration & Safe Candidate Export.
================================================================================

Classes (Strict 5-Class Target):
  0: Healthy
  1: Leaf_Spot        (Cercospora Leaf Spot)
  2: Leaf_webber      (Maruca vitrata / Cydia critica)
  3: Sterilic_mosaic  (Sterility Mosaic Disease / SMD)
  4: Wilt             (Fusarium Wilt)

Candidate Checkpoint:
  models/candidates/tursathi_efficientnet_b0_candidate_<experiment_id>.pth
================================================================================
"""

import os
import sys
import json
import time
import random
import argparse
from pathlib import Path
from datetime import datetime

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models
from PIL import Image

try:
    from sklearn.metrics import classification_report, confusion_matrix
except ImportError:
    os.system("pip install -q scikit-learn")
    from sklearn.metrics import classification_report, confusion_matrix

# ==============================================================================
# 1. CONSTANTS & HYPERPARAMETERS
# ==============================================================================

SEED = 42

def seed_everything(seed=SEED):
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False

seed_everything(SEED)

EXPECTED_CLASSES = ["Healthy", "Leaf_Spot", "Leaf_webber", "Sterilic_mosaic", "Wilt"]
NUM_CLASSES = len(EXPECTED_CLASSES)
IMG_SIZE = 224
BATCH_SIZE = 16
NUM_EPOCHS = 20
LEARNING_RATE = 1e-4
WEIGHT_DECAY = 1e-4
FEATURE_DIM = 1280

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ==============================================================================
# 2. TRANSFORMS & AUGMENTATIONS
# ==============================================================================

def get_transforms():
    """
    Agricultural foliar transforms:
    - Training: mild rotation, horizontal/vertical flip, controlled color jitter
    - Validation/Testing: clean deterministic resize and ImageNet normalization (NO augmentation)
    """
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

    return train_transform, eval_transform


# ==============================================================================
# 3. MODEL ARCHITECTURE
# ==============================================================================

class TurEfficientNetB0(nn.Module):
    """
    EfficientNet-B0 with dedicated 1280-D feature extractor tap.
    Fully compatible with production TurDiseasePredictor.
    """
    def __init__(self, num_classes=NUM_CLASSES, pretrained=True):
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


# ==============================================================================
# 4. TRAINING LOOP
# ==============================================================================

def train_model(
    model,
    train_loader,
    val_loader,
    class_weights=None,
    epochs=NUM_EPOCHS,
    lr=LEARNING_RATE,
    checkpoint_dir=None,
    checkpoint_interval=10,
):
    if class_weights is not None:
        weights_tensor = torch.tensor(class_weights, dtype=torch.float32).to(DEVICE)
        criterion = nn.CrossEntropyLoss(weight=weights_tensor, label_smoothing=0.05)
        print(f"[Training] Using Class-Weighted CrossEntropyLoss: {class_weights}")
    else:
        criterion = nn.CrossEntropyLoss(label_smoothing=0.05)

    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=WEIGHT_DECAY)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)

    best_val_acc = 0.0
    best_weights = None
    best_epoch = 0
    history = {"train_loss": [], "train_acc": [], "val_loss": [], "val_acc": []}

    ckpt_path = Path(checkpoint_dir) if checkpoint_dir else None
    if ckpt_path:
        ckpt_path.mkdir(parents=True, exist_ok=True)
        print(f"[Checkpoints] Drive Checkpoints enabled -> {ckpt_path.resolve()}")

    print(f"\n[Training] Starting fine-tuning for {epochs} epochs on {DEVICE}...")

    for epoch in range(1, epochs + 1):
        # ── Train ────────────────────────────────────────
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        for inputs, targets in train_loader:
            inputs, targets = inputs.to(DEVICE), targets.to(DEVICE)
            optimizer.zero_grad()
            logits, _ = model(inputs)
            loss = criterion(logits, targets)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * inputs.size(0)
            preds = logits.argmax(dim=1)
            correct += (preds == targets).sum().item()
            total += targets.size(0)

        scheduler.step()
        train_loss = running_loss / total
        train_acc = correct / total

        # ── Validate ─────────────────────────────────────
        model.eval()
        val_loss_sum = 0.0
        val_correct = 0
        val_total = 0

        with torch.no_grad():
            for inputs, targets in val_loader:
                inputs, targets = inputs.to(DEVICE), targets.to(DEVICE)
                logits, _ = model(inputs)
                loss = criterion(logits, targets)
                val_loss_sum += loss.item() * inputs.size(0)
                preds = logits.argmax(dim=1)
                val_correct += (preds == targets).sum().item()
                val_total += targets.size(0)

        val_loss = val_loss_sum / val_total
        val_acc = val_correct / val_total

        history["train_loss"].append(train_loss)
        history["train_acc"].append(train_acc)
        history["val_loss"].append(val_loss)
        history["val_acc"].append(val_acc)

        print(f"Epoch {epoch:02d}/{epochs:02d} | "
              f"Train Loss: {train_loss:.4f} Acc: {train_acc*100:.2f}% | "
              f"Val Loss: {val_loss:.4f} Acc: {val_acc*100:.2f}%")

        # Checkpoint: Best Validation Accuracy
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_epoch = epoch
            best_weights = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            if ckpt_path:
                best_file = ckpt_path / "best_model_checkpoint.pth"
                torch.save({
                    "epoch": epoch,
                    "model_state_dict": best_weights,
                    "classes": EXPECTED_CLASSES,
                    "best_val_accuracy": best_val_acc,
                }, best_file)
                print(f"  ★ New best model checkpoint saved: {best_file.name} ({best_val_acc*100:.2f}%)")

        # Periodic Interval Checkpoint
        if ckpt_path and (epoch % checkpoint_interval == 0 or epoch == epochs):
            interval_file = ckpt_path / f"checkpoint_epoch_{epoch:02d}.pth"
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "classes": EXPECTED_CLASSES,
                "val_accuracy": val_acc,
            }, interval_file)

    print(f"\n[Training] Best Validation Accuracy: {best_val_acc*100:.2f}% at Epoch {best_epoch}")
    model.load_state_dict(best_weights)
    model.to(DEVICE)
    return model, history, best_val_acc, best_epoch


# ==============================================================================
# 5. FEATURE CENTROIDS & PER-CLASS OOD BOUNDARY CALIBRATION
# ==============================================================================

def compute_calibrated_ood_profile(model, train_loader, val_loader):
    """
    Extracts 1280-D features from training samples to construct:
    1. Per-class centroids mu_c.
    2. Per-class calibrated cosine thresholds tau_c (calibrated on clean validation data).
    3. Global Mahalanobis distance parameters.
    """
    print("\n[OOD Calibration] Extracting 1280-D latent embeddings for 5 classes...")
    model.eval()

    class_features = {c: [] for c in range(NUM_CLASSES)}
    with torch.no_grad():
        for inputs, targets in train_loader:
            inputs = inputs.to(DEVICE)
            feat = model.extract_features(inputs).cpu().numpy()
            for f, t in zip(feat, targets.numpy()):
                class_features[t].append(f)

    centroids = {}
    norm_centroids = {}
    class_stds = {}

    for c in range(NUM_CLASSES):
        c_feats = np.array(class_features[c])
        cent = np.mean(c_feats, axis=0)
        centroids[c] = cent
        norm_centroids[c] = cent / (np.linalg.norm(cent) + 1e-8)
        class_stds[c] = float(np.mean(np.std(c_feats, axis=0)))

    # Compute shared centered covariance matrix
    centered = []
    for c in range(NUM_CLASSES):
        for f in class_features[c]:
            centered.append(f - centroids[c])
    centered = np.array(centered)
    cov = np.cov(centered, rowvar=False)
    reg_eps = 1e-4 * np.trace(cov) / FEATURE_DIM
    cov_reg = cov + np.eye(FEATURE_DIM) * reg_eps
    inv_cov = np.linalg.pinv(cov_reg)

    # Helper for distance
    def mahalanobis_dist(feat_vec):
        dists = []
        for c in range(NUM_CLASSES):
            diff = feat_vec - centroids[c]
            d = np.sqrt(np.maximum(0.0, np.dot(np.dot(diff, inv_cov), diff)))
            dists.append(d)
        return min(dists)

    def cosine_dist_to_centroid(feat_vec, c_idx):
        norm_v = feat_vec / (np.linalg.norm(feat_vec) + 1e-8)
        return float(1.0 - np.dot(norm_v, norm_centroids[c_idx]))

    # Calibrate PER-CLASS cosine thresholds on clean validation samples
    val_class_cos_dists = {c: [] for c in range(NUM_CLASSES)}
    val_m_dists = []

    with torch.no_grad():
        for inputs, targets in val_loader:
            inputs = inputs.to(DEVICE)
            feats = model.extract_features(inputs).cpu().numpy()
            for f, t in zip(feats, targets.numpy()):
                cos_d = cosine_dist_to_centroid(f, t)
                val_class_cos_dists[t].append(cos_d)
                val_m_dists.append(mahalanobis_dist(f))

    # Calibrate thresholds at 97.5th percentile of in-distribution validation samples
    per_class_thresholds = {}
    for c in range(NUM_CLASSES):
        dists = val_class_cos_dists[c]
        p975 = float(np.percentile(dists, 97.5)) if dists else 0.45
        # Enforce safety ceiling: Wilt boundary must not exceed 0.40 to prevent sinkhole
        if EXPECTED_CLASSES[c] == "Wilt":
            p975 = min(p975, 0.40)
        per_class_thresholds[EXPECTED_CLASSES[c]] = round(p975, 4)

    ood_m_threshold = float(np.percentile(val_m_dists, 98.0))
    global_cos_threshold = float(np.percentile([d for ds in val_class_cos_dists.values() for d in ds], 98.0))

    print(f"[OOD Calibration] Per-Class Calibrated Cosine Thresholds (97.5% In-Dist):")
    for c_name, th in per_class_thresholds.items():
        print(f"  - {c_name:18s}: {th:.4f}")
    print(f"[OOD Calibration] Mahalanobis Threshold: {ood_m_threshold:.4f}")

    profile = {
        "classes": EXPECTED_CLASSES,
        "feature_dim": FEATURE_DIM,
        "centroids": {EXPECTED_CLASSES[c]: centroids[c].tolist() for c in range(NUM_CLASSES)},
        "class_thresholds": per_class_thresholds,
        "class_stds": {EXPECTED_CLASSES[c]: class_stds[c] for c in range(NUM_CLASSES)},
        "ood_mahalanobis_threshold": ood_m_threshold,
        "ood_cosine_threshold": global_cos_threshold,
        "min_confidence_floor": 0.70,
        "min_margin_floor": 0.20,
    }

    return profile, centroids, norm_centroids, inv_cov, per_class_thresholds, ood_m_threshold


# ==============================================================================
# 6. EVALUATION ON TEST SET & OOD DATASET
# ==============================================================================

def evaluate_test_set(model, test_loader):
    model.eval()
    all_preds = []
    all_targets = []
    total_loss = 0.0
    criterion = nn.CrossEntropyLoss()

    with torch.no_grad():
        for inputs, targets in test_loader:
            inputs, targets = inputs.to(DEVICE), targets.to(DEVICE)
            logits, _ = model(inputs)
            loss = criterion(logits, targets)
            total_loss += loss.item() * inputs.size(0)
            preds = logits.argmax(dim=1)
            all_preds.extend(preds.cpu().numpy())
            all_targets.extend(targets.cpu().numpy())

    test_loss = total_loss / len(all_targets)
    test_acc = (np.array(all_preds) == np.array(all_targets)).mean()

    report = classification_report(all_targets, all_preds, target_names=EXPECTED_CLASSES, output_dict=True)
    cm = confusion_matrix(all_targets, all_preds)

    print("\n" + "=" * 60)
    print("FINAL TEST SET CLASSIFICATION REPORT (CLEAN DATASET)")
    print("=" * 60)
    print(classification_report(all_targets, all_preds, target_names=EXPECTED_CLASSES))
    print("CONFUSION MATRIX:")
    print(cm)
    print("=" * 60)

    return test_loss, float(test_acc), report, cm


def evaluate_ood_rejection(model, ood_dir, norm_centroids, per_class_thresholds, eval_transform):
    """
    Evaluates real-world external images against multi-layer OOD guard:
    1. Distance to predicted class centroid <= per_class_threshold
    2. Confidence >= 0.70
    3. Probability Margin >= 0.20
    """
    ood_path = Path(ood_dir)
    if not ood_path.exists():
        print(f"[OOD Evaluation] Directory {ood_dir} not found. Skipping.")
        return None

    valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    img_files = [f for f in ood_path.iterdir() if f.is_file() and f.suffix.lower() in valid_exts]
    if not img_files:
        print(f"[OOD Evaluation] No images found in {ood_dir}. Skipping.")
        return None

    print(f"\n[OOD Evaluation] Testing {len(img_files)} external images against OOD Guard...")
    model.eval()
    rejected_count = 0
    results = []

    for img_path in img_files:
        try:
            raw_img = Image.open(img_path).convert("RGB")
            tensor = eval_transform(raw_img).unsqueeze(0).to(DEVICE)
            with torch.no_grad():
                logits, feat_tensor = model(tensor)
                probs = torch.softmax(logits, dim=1)[0].cpu().numpy()
                feat = feat_tensor[0].cpu().numpy()

            pred_idx = int(np.argmax(probs))
            conf = float(probs[pred_idx])
            pred_class = EXPECTED_CLASSES[pred_idx]

            sorted_probs = np.sort(probs)[::-1]
            margin = float(sorted_probs[0] - sorted_probs[1]) if len(sorted_probs) > 1 else 1.0

            # Cosine distance to predicted class centroid
            norm_v = feat / (np.linalg.norm(feat) + 1e-8)
            cos_dist = float(1.0 - np.dot(norm_v, norm_centroids[pred_idx]))

            class_th = per_class_thresholds.get(pred_class, 0.45)
            is_rejected = (cos_dist > class_th) or (conf < 0.70) or (margin < 0.20)

            if is_rejected:
                rejected_count += 1
                verdict = "REJECTED (Correct OOD Rejection)"
            else:
                verdict = f"FAILED REJECTION (Classified as {pred_class}, conf={conf:.3f}, dist={cos_dist:.3f})"

            results.append({
                "filename": img_path.name,
                "predicted_class": pred_class,
                "confidence": conf,
                "probability_margin": margin,
                "cosine_distance": cos_dist,
                "threshold": class_th,
                "is_rejected": is_rejected,
                "verdict": verdict
            })
        except Exception as e:
            continue

    rejection_rate = (rejected_count / len(img_files)) * 100 if img_files else 0
    print(f"[OOD Evaluation] Successfully Rejected: {rejected_count}/{len(img_files)} ({rejection_rate:.1f}%)")
    print("=" * 60)
    return {
        "total_tested": len(img_files),
        "rejected_count": rejected_count,
        "rejection_rate_percent": rejection_rate,
        "sample_verdicts": results[:8]
    }


# ==============================================================================
# 7. MAIN RETRAINING ORCHESTRATOR
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="TurSathi AI Clean Retraining Pipeline")
    parser.add_argument("--data_dir", type=str, default="dataset", help="Path to extracted clean dataset root")
    parser.add_argument("--ood_dir", type=str, default="dataset/ood_evaluation", help="Path to OOD images")
    parser.add_argument("--output_dir", type=str, default="candidates", help="Directory to save candidate model & metrics")
    parser.add_argument("--checkpoint_dir", type=str, default=None, help="Google Drive path for periodic checkpoints")
    parser.add_argument("--drive_output_dir", type=str, default=None, help="Google Drive path to mirror final outputs")
    parser.add_argument("--epochs", type=int, default=NUM_EPOCHS, help="Number of epochs")
    parser.add_argument("--batch_size", type=int, default=BATCH_SIZE, help="Batch size")
    parser.add_argument("--experiment_id", type=str, default=None, help="Unique experiment identifier")
    args = parser.parse_args()

    exp_id = args.experiment_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    drive_out_path = Path(args.drive_output_dir) if args.drive_output_dir else None
    if drive_out_path:
        drive_out_path.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("   TURSATHI AI — CLEAN RETRAINING & MULTI-LAYER OOD PIPELINE   ")
    print(f"   Experiment ID: {exp_id}")
    print(f"   Device       : {DEVICE} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")
    print(f"   Target Classes: {EXPECTED_CLASSES}")
    print("=" * 70)

    # 1. Transforms & Dataloaders
    train_tf, eval_tf = get_transforms()
    train_dataset = datasets.ImageFolder(data_dir / "train", transform=train_tf)
    val_dataset = datasets.ImageFolder(data_dir / "val", transform=eval_tf)
    test_dataset = datasets.ImageFolder(data_dir / "test", transform=eval_tf)

    assert train_dataset.classes == EXPECTED_CLASSES, (
        f"Dataset classes {train_dataset.classes} do not match expected {EXPECTED_CLASSES}"
    )

    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=2, pin_memory=True)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False, num_workers=2, pin_memory=True)
    test_loader = DataLoader(test_dataset, batch_size=args.batch_size, shuffle=False, num_workers=2, pin_memory=True)

    # Calculate class weights from training distribution to address Wilt asymmetry
    class_counts = [len(np.where(np.array(train_dataset.targets) == c)[0]) for c in range(NUM_CLASSES)]
    max_count = max(class_counts)
    class_weights = [round(max_count / max(1, cnt), 4) for cnt in class_counts]

    print(f"Dataset Loaded: Train={len(train_dataset)}, Val={len(val_dataset)}, Test={len(test_dataset)}")
    print(f"Training Class Counts: {dict(zip(EXPECTED_CLASSES, class_counts))}")
    print(f"Calculated Class Weights: {dict(zip(EXPECTED_CLASSES, class_weights))}")

    # 2. Build Model
    model = TurEfficientNetB0(num_classes=NUM_CLASSES, pretrained=True).to(DEVICE)

    # 3. Train & Fine-Tune
    model, history, best_val_acc, best_epoch = train_model(
        model,
        train_loader,
        val_loader,
        class_weights=class_weights,
        epochs=args.epochs,
        lr=LEARNING_RATE,
        checkpoint_dir=args.checkpoint_dir,
    )

    # 4. Feature Extraction & Per-Class Calibrated OOD Profile
    profile, centroids, norm_centroids, inv_cov, per_class_th, ood_m_th = compute_calibrated_ood_profile(
        model, train_loader, val_loader
    )

    # 5. Final Evaluation on Untouched Test Set
    test_loss, test_acc, test_report, cm = evaluate_test_set(model, test_loader)

    # 6. Real-World OOD Evaluation
    ood_results = evaluate_ood_rejection(
        model, args.ood_dir, norm_centroids, per_class_th, eval_tf
    )

    # 7. Safe Candidate Model Export (Preserves Production Checkpoint!)
    candidate_filename = f"tursathi_efficientnet_b0_candidate_{exp_id}.pth"
    candidate_save_path = output_dir / candidate_filename

    candidate_metadata = {
        "experiment_id": exp_id,
        "model_state_dict": model.state_dict(),
        "classes": EXPECTED_CLASSES,
        "num_classes": NUM_CLASSES,
        "best_val_accuracy": best_val_acc,
        "best_epoch": best_epoch,
        "test_accuracy": test_acc,
        "image_size": IMG_SIZE,
        "model_name": "EfficientNet-B0",
        "created_at": datetime.now().isoformat(),
        "ood_profile": profile,
    }

    torch.save(candidate_metadata, candidate_save_path)
    print(f"\n[Export] Candidate Model -> {candidate_save_path} ({candidate_save_path.stat().st_size / (1024*1024):.2f} MB)")
    if drive_out_path:
        torch.save(candidate_metadata, drive_out_path / candidate_filename)
        print(f"[Drive] Mirrored Candidate Model -> {drive_out_path / candidate_filename}")

    # 8. Save OOD Profile JSON & Evaluation Report
    profile_filename = f"ood_feature_profile_{exp_id}.json"
    with open(output_dir / profile_filename, "w") as f:
        json.dump(profile, f, indent=2)

    report_filename = f"training_report_{exp_id}.json"
    report_data = {
        "experiment_id": exp_id,
        "model_name": "EfficientNet-B0",
        "classes": EXPECTED_CLASSES,
        "best_epoch": best_epoch,
        "best_val_accuracy": best_val_acc,
        "test_loss": test_loss,
        "test_accuracy": test_acc,
        "per_class_thresholds": per_class_th,
        "classification_report": test_report,
        "confusion_matrix": cm.tolist(),
        "ood_evaluation": ood_results,
        "history": history,
    }
    with open(output_dir / report_filename, "w") as f:
        json.dump(report_data, f, indent=2)

    if drive_out_path:
        with open(drive_out_path / profile_filename, "w") as f:
            json.dump(profile, f, indent=2)
        with open(drive_out_path / report_filename, "w") as f:
            json.dump(report_data, f, indent=2)

    print("\n" + "=" * 70)
    print("   RETRAINING & CANDIDATE EXPORT COMPLETED SUCCESSFULLY!   ")
    print(f"   Candidate Checkpoint : {candidate_save_path.resolve()}")
    print(f"   OOD Profile JSON     : {(output_dir / profile_filename).resolve()}")
    print(f"   Training Report JSON : {(output_dir / report_filename).resolve()}")
    print("=" * 70)

if __name__ == "__main__":
    main()
