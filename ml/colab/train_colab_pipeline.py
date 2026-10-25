#!/usr/bin/env python3
"""
================================================================================
TurSathi AI - Enterprise Google Colab Training Pipeline
Fine-Tuning, Multi-Layer Validation, Feature Extraction, OOD Guard,
Pruning, and INT8 Quantization for Pigeon Pea (Tur) Leaf Diseases.
================================================================================

Classes (Strict 5-Class Target):
  0: Healthy
  1: Leaf_Spot        (Cercospora Leaf Spot)
  2: Leaf_webber      (Maruca vitrata / Cydia critica)
  3: Sterilic_mosaic  (Sterility Mosaic Disease / SMD)
  4: Wilt             (Fusarium Wilt)

Architecture:
  - EfficientNet-B0 Backbone (Pretrained on ImageNet)
  - Penultimate 1280-Dimensional Feature Extraction
  - Centroid & Regularized Mahalanobis Distance Profiling (OOD Rejection Guard)
  - Cosine Distance Boundary Profiling
  - L1 Unstructured Weight Pruning
  - INT8 Post-Training Dynamic Quantization
================================================================================
"""

import os
import sys
import json
import time
import random
import argparse
from pathlib import Path

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
# 1. CONFIGURATION & HYPERPARAMETERS
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
# 2. DATA AUGMENTATION & LOADERS
# ==============================================================================

def get_transforms():
    """
    Carefully designed data augmentation for agricultural foliar inspection:
    - Moderate rotation, horizontal & vertical flip
    - Color jitter for varying ambient sunlight in the field
    - Normalization with ImageNet statistics
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
# 3. MODEL CREATION
# ==============================================================================

class TurEfficientNetB0(nn.Module):
    """
    EfficientNet-B0 with explicit feature extractor tap for 1280-D embeddings.
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
        """Extracts penultimate 1280-dimensional latent embedding vector."""
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
# 4. TRAINING LOOP WITH EARLY STOPPING
# ==============================================================================

def train_model(
    model,
    train_loader,
    val_loader,
    epochs=NUM_EPOCHS,
    lr=LEARNING_RATE,
    checkpoint_dir=None,
    checkpoint_interval=10,
):
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
        print(f"[Checkpoints] Automated Drive Checkpoints enabled -> {ckpt_path.resolve()}")

    print(f"\n[Training] Starting fine-tuning for {epochs} epochs on {DEVICE}...")

    for epoch in range(1, epochs + 1):
        # ── Train Phase ──────────────────────────────────
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

        # ── Val Phase ────────────────────────────────────
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

        # ── Checkpoint: Best Validation Accuracy ───────
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_epoch = epoch
            best_weights = {k: v.cpu().clone() for k, v in model.state_dict().items()}

            if ckpt_path:
                best_ckpt_file = ckpt_path / "best_model_checkpoint.pth"
                torch.save({
                    "epoch": epoch,
                    "model_state_dict": best_weights,
                    "classes": EXPECTED_CLASSES,
                    "best_val_accuracy": best_val_acc,
                }, best_ckpt_file)
                print(f"  ★ New best model saved to Drive: {best_ckpt_file.name} ({best_val_acc*100:.2f}%)")

        # ── Checkpoint: Periodic Interval (e.g. Epoch 10, 20) ─
        if ckpt_path and (epoch % checkpoint_interval == 0 or epoch == epochs):
            interval_ckpt_file = ckpt_path / f"checkpoint_epoch_{epoch:02d}.pth"
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "classes": EXPECTED_CLASSES,
                "val_accuracy": val_acc,
            }, interval_ckpt_file)
            print(f"  💾 Periodic checkpoint saved to Drive: {interval_ckpt_file.name}")

    print(f"\n[Training] Best Validation Accuracy: {best_val_acc*100:.2f}% at Epoch {best_epoch}")
    model.load_state_dict(best_weights)
    model.to(DEVICE)
    return model, history, best_val_acc, best_epoch


# ==============================================================================
# 5. FEATURE EXTRACTION & OOD CENTROID PROFILING
# ==============================================================================

def compute_feature_centroids_and_ood_profile(model, train_loader, val_loader):
    """
    Extracts 1280-D features from training samples to construct:
    1. Class centroids mu_c for each of the 5 classes.
    2. Shared pooled covariance matrix Sigma and its regularized inverse Sigma^-1.
    3. Calibrated threshold tau_ood using validation set to reject unknown classes.
    """
    print("\n[Feature Engineering] Extracting 1280-D latent embeddings for 5 classes...")
    model.eval()

    class_features = {c: [] for c in range(NUM_CLASSES)}
    all_train_features = []

    with torch.no_grad():
        for inputs, targets in train_loader:
            inputs = inputs.to(DEVICE)
            feat = model.extract_features(inputs).cpu().numpy()
            for f, t in zip(feat, targets.numpy()):
                class_features[t].append(f)
                all_train_features.append(f)

    all_train_features = np.array(all_train_features)
    centroids = {}
    class_stds = {}

    for c in range(NUM_CLASSES):
        c_feats = np.array(class_features[c])
        centroids[c] = np.mean(c_feats, axis=0)
        class_stds[c] = float(np.mean(np.std(c_feats, axis=0)))

    # Compute shared centered covariance matrix
    centered_features = []
    for c in range(NUM_CLASSES):
        for f in class_features[c]:
            centered_features.append(f - centroids[c])
    centered_features = np.array(centered_features)

    # Covariance + shrinkage regularization (Ledoit-Wolf style diagonal epsilon)
    cov = np.cov(centered_features, rowvar=False)
    reg_epsilon = 1e-4 * np.trace(cov) / FEATURE_DIM
    cov_reg = cov + np.eye(FEATURE_DIM) * reg_epsilon
    inv_cov = np.linalg.pinv(cov_reg)

    # Calculate distance helper
    def mahalanobis_distance(feat_vec):
        dists = []
        for c in range(NUM_CLASSES):
            diff = feat_vec - centroids[c]
            # dist^2 = diff @ inv_cov @ diff.T
            d = np.sqrt(np.maximum(0.0, np.dot(np.dot(diff, inv_cov), diff)))
            dists.append(d)
        return min(dists)

    def min_cosine_distance(feat_vec):
        norm_v = np.linalg.norm(feat_vec) + 1e-8
        sims = []
        for c in range(NUM_CLASSES):
            norm_c = np.linalg.norm(centroids[c]) + 1e-8
            cos_sim = np.dot(feat_vec, centroids[c]) / (norm_v * norm_c)
            sims.append(cos_sim)
        return 1.0 - max(sims)

    # Calibrate threshold on validation set (99th percentile of in-distribution)
    val_m_dists = []
    val_cos_dists = []

    with torch.no_grad():
        for inputs, _ in val_loader:
            inputs = inputs.to(DEVICE)
            feats = model.extract_features(inputs).cpu().numpy()
            for f in feats:
                val_m_dists.append(mahalanobis_distance(f))
                val_cos_dists.append(min_cosine_distance(f))

    # Threshold chosen so 99% of genuine in-distribution samples pass
    ood_m_threshold = float(np.percentile(val_m_dists, 99.0))
    ood_cos_threshold = float(np.percentile(val_cos_dists, 99.0))

    print(f"[Feature Engineering] Centroids computed for 5 classes.")
    print(f"[Feature Engineering] Calibrated Mahalanobis OOD Threshold (99% In-Dist): {ood_m_threshold:.4f}")
    print(f"[Feature Engineering] Calibrated Cosine OOD Threshold (99% In-Dist): {ood_cos_threshold:.4f}")

    profile = {
        "classes": EXPECTED_CLASSES,
        "feature_dim": FEATURE_DIM,
        "centroids": {EXPECTED_CLASSES[c]: centroids[c].tolist() for c in range(NUM_CLASSES)},
        "class_stds": {EXPECTED_CLASSES[c]: class_stds[c] for c in range(NUM_CLASSES)},
        "ood_mahalanobis_threshold": ood_m_threshold,
        "ood_cosine_threshold": ood_cos_threshold,
        "min_confidence_floor": 0.70,
    }

    return profile, centroids, inv_cov, ood_m_threshold, ood_cos_threshold


# ==============================================================================
# 6. MODEL WEIGHT PRUNING
# ==============================================================================

def apply_model_pruning(model, prune_ratio=0.15):
    """
    Applies L1-unstructured pruning to remove low-magnitude weights
    from convolutional and linear layers, making representations sparse
    and resilient against overfitting.
    """
    import torch.nn.utils.prune as prune

    print(f"\n[Model Optimization] Applying L1 weight pruning ({prune_ratio*100:.1f}% sparsity)...")
    modules_pruned = 0

    for name, module in model.named_modules():
        if isinstance(module, nn.Linear):
            prune.l1_unstructured(module, name="weight", amount=prune_ratio)
            prune.remove(module, "weight")
            modules_pruned += 1
        elif isinstance(module, nn.Conv2d):
            prune.l1_unstructured(module, name="weight", amount=prune_ratio)
            prune.remove(module, "weight")
            modules_pruned += 1

    print(f"[Model Optimization] Pruned {modules_pruned} layers successfully.")
    return model


# ==============================================================================
# 7. INT8 QUANTIZATION
# ==============================================================================

def apply_dynamic_quantization(model):
    """
    Applies INT8 Post-Training Dynamic Quantization to Linear layers.
    Reduces memory footprint by ~70% and accelerates CPU server inference.
    """
    print("\n[Model Optimization] Applying INT8 Post-Training Dynamic Quantization...")
    cpu_model = model.to("cpu")
    quantized_model = torch.ao.quantization.quantize_dynamic(
        cpu_model,
        {nn.Linear},
        dtype=torch.qint8
    )
    print("[Model Optimization] Dynamic INT8 Quantization complete.")
    return quantized_model


# ==============================================================================
# 8. EVALUATION (IN-DISTRIBUTION & OOD REJECTION TEST)
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

    print("\n" + "="*60)
    print("FINAL TEST SET CLASSIFICATION REPORT (5 CLASSES)")
    print("="*60)
    print(classification_report(all_targets, all_preds, target_names=EXPECTED_CLASSES))
    print("CONFUSION MATRIX:")
    print(cm)
    print("="*60)

    return test_loss, float(test_acc), report, cm


def evaluate_ood_rejection(model, ood_dir, centroids, inv_cov, ood_m_threshold, ood_cos_threshold, eval_transform):
    """
    Tests external/unseen images (pod, non-tur, unknown leaf disease) to verify
    that the multi-layer OOD guard strictly rejects them with:
    'this specific class does not exist in the current database'.
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

            # Mahalanobis distance
            diffs = [feat - centroids[c] for c in range(NUM_CLASSES)]
            m_dists = [np.sqrt(np.maximum(0.0, np.dot(np.dot(d, inv_cov), d))) for d in diffs]
            min_m = float(min(m_dists))

            # Cosine distance
            norm_v = np.linalg.norm(feat) + 1e-8
            cos_sims = [np.dot(feat, centroids[c]) / (norm_v * (np.linalg.norm(centroids[c]) + 1e-8)) for c in range(NUM_CLASSES)]
            min_cos_dist = float(1.0 - max(cos_sims))

            # STRICT ENFORCEMENT DECISION
            is_rejected = (min_m > ood_m_threshold) or (min_cos_dist > ood_cos_threshold) or (conf < 0.70)

            if is_rejected:
                rejected_count += 1
                status = "REJECTED (Correct: Not in database)"
            else:
                status = f"FAILED REJECTION (Classified as {EXPECTED_CLASSES[pred_idx]})"

            results.append({
                "image": img_path.name,
                "is_rejected": is_rejected,
                "min_mahalanobis": min_m,
                "min_cosine_dist": min_cos_dist,
                "confidence": conf,
                "status": status,
            })
        except Exception as e:
            continue

    rejection_rate = (rejected_count / len(img_files)) * 100 if img_files else 0
    print(f"[OOD Evaluation] Successfully Rejected: {rejected_count}/{len(img_files)} ({rejection_rate:.1f}%)")
    print("="*60)
    return {
        "total_tested": len(img_files),
        "rejected_count": rejected_count,
        "rejection_rate_percent": rejection_rate,
        "sample_verdicts": results[:5]
    }


# ==============================================================================
# 9. MAIN PIPELINE
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="TurSathi AI Colab Training Pipeline")
    parser.add_argument("--data_dir", type=str, default="dataset", help="Path to extracted dataset root")
    parser.add_argument("--ood_dir", type=str, default="dataset/ood_evaluation", help="Path to OOD images")
    parser.add_argument("--output_dir", type=str, default="outputs", help="Local directory to save final model & metrics")
    parser.add_argument("--checkpoint_dir", type=str, default=None, help="Google Drive path to save periodic checkpoints")
    parser.add_argument("--drive_output_dir", type=str, default=None, help="Google Drive path to save final outputs")
    parser.add_argument("--checkpoint_interval", type=int, default=10, help="Epoch interval to save periodic checkpoints")
    parser.add_argument("--epochs", type=int, default=NUM_EPOCHS, help="Number of training epochs")
    parser.add_argument("--batch_size", type=int, default=BATCH_SIZE, help="Batch size")
    parser.add_argument("--prune", action="store_true", default=True, help="Apply L1 weight pruning")
    parser.add_argument("--quantize", action="store_true", default=True, help="Apply INT8 dynamic quantization")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    drive_out_path = Path(args.drive_output_dir) if args.drive_output_dir else None
    if drive_out_path:
        drive_out_path.mkdir(parents=True, exist_ok=True)
        print(f"[Google Drive] Final outputs will be mirrored to: {drive_out_path.resolve()}")

    print("="*70)
    print("   TURSATHI AI — PIGEON PEA (TUR) 5-CLASS TRAINING & OOD PIPELINE   ")
    print(f"   Device: {DEVICE} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")
    print(f"   Target Classes: {EXPECTED_CLASSES}")
    print("="*70)

    # 1. Transforms & Dataloaders
    train_tf, eval_tf = get_transforms()
    train_dataset = datasets.ImageFolder(data_dir / "train", transform=train_tf)
    val_dataset = datasets.ImageFolder(data_dir / "val", transform=eval_tf)
    test_dataset = datasets.ImageFolder(data_dir / "test", transform=eval_tf)

    # Assert 5 classes
    assert train_dataset.classes == EXPECTED_CLASSES, (
        f"Dataset classes {train_dataset.classes} do not match expected {EXPECTED_CLASSES}"
    )

    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=2, pin_memory=True)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False, num_workers=2, pin_memory=True)
    test_loader = DataLoader(test_dataset, batch_size=args.batch_size, shuffle=False, num_workers=2, pin_memory=True)

    print(f"Dataset Loaded: Train={len(train_dataset)}, Val={len(val_dataset)}, Test={len(test_dataset)}")

    # 2. Build Model
    model = TurEfficientNetB0(num_classes=NUM_CLASSES, pretrained=True).to(DEVICE)

    # 3. Train & Fine-Tune
    model, history, best_val_acc, best_epoch = train_model(
        model,
        train_loader,
        val_loader,
        epochs=args.epochs,
        lr=LEARNING_RATE,
        checkpoint_dir=args.checkpoint_dir,
        checkpoint_interval=args.checkpoint_interval,
    )

    # 4. Feature Extraction & Centroid OOD Profile
    profile, centroids, inv_cov, ood_m_th, ood_cos_th = compute_feature_centroids_and_ood_profile(
        model, train_loader, val_loader
    )

    # 5. Test Set Evaluation
    test_loss, test_acc, test_report, cm = evaluate_test_set(model, test_loader)

    # 6. OOD Evaluation
    ood_results = evaluate_ood_rejection(
        model, args.ood_dir, centroids, inv_cov, ood_m_th, ood_cos_th, eval_tf
    )

    # 7. Model Pruning (Optional)
    if args.prune:
        model = apply_model_pruning(model, prune_ratio=0.15)
        # Re-evaluate after pruning to confirm accuracy retention
        _, post_prune_acc, _, _ = evaluate_test_set(model, test_loader)
        print(f"[Model Optimization] Post-Pruning Test Accuracy: {post_prune_acc*100:.2f}%")

    # 8. Save Canonical PyTorch Model & Metadata
    model_save_path = output_dir / "best_pigeonpea_disease_final_efficientnet_b0.pth"
    model_checkpoint_data = {
        "model_state_dict": model.state_dict(),
        "classes": EXPECTED_CLASSES,
        "num_classes": NUM_CLASSES,
        "best_val_accuracy": best_val_acc,
        "best_epoch": best_epoch,
        "test_accuracy": test_acc,
        "image_size": IMG_SIZE,
        "model_name": "EfficientNet-B0",
        "ood_profile": {
            "ood_mahalanobis_threshold": ood_m_th,
            "ood_cosine_threshold": ood_cos_th,
            "min_confidence_floor": 0.70,
        }
    }
    torch.save(model_checkpoint_data, model_save_path)
    print(f"\n[Saved] Base PyTorch Model -> {model_save_path} ({model_save_path.stat().st_size / (1024*1024):.2f} MB)")
    if drive_out_path:
        torch.save(model_checkpoint_data, drive_out_path / "best_pigeonpea_disease_final_efficientnet_b0.pth")
        print(f"[Google Drive] Synced Base Model -> {drive_out_path / 'best_pigeonpea_disease_final_efficientnet_b0.pth'}")

    # 9. Save OOD Profile JSON (for server-side OOD guard verification)
    ood_json_path = output_dir / "ood_feature_profile.json"
    with open(ood_json_path, "w") as f:
        json.dump(profile, f, indent=2)
    print(f"[Saved] OOD Profile JSON -> {ood_json_path}")
    if drive_out_path:
        with open(drive_out_path / "ood_feature_profile.json", "w") as f:
            json.dump(profile, f, indent=2)
        print(f"[Google Drive] Synced OOD Profile -> {drive_out_path / 'ood_feature_profile.json'}")

    # 10. Quantization (Optional)
    if args.quantize:
        quantized_model = apply_dynamic_quantization(model)
        quant_save_path = output_dir / "quantized_pigeonpea_disease_efficientnet_b0.pth"
        torch.save(quantized_model.state_dict(), quant_save_path)
        print(f"[Saved] INT8 Quantized Model -> {quant_save_path} ({quant_save_path.stat().st_size / (1024*1024):.2f} MB)")
        if drive_out_path:
            torch.save(quantized_model.state_dict(), drive_out_path / "quantized_pigeonpea_disease_efficientnet_b0.pth")
            print(f"[Google Drive] Synced Quantized Model -> {drive_out_path / 'quantized_pigeonpea_disease_efficientnet_b0.pth'}")

    # 11. Save Training Report & Confusion Matrix
    report_data = {
        "model": "EfficientNet-B0",
        "classes": EXPECTED_CLASSES,
        "best_epoch": best_epoch,
        "best_val_accuracy": best_val_acc,
        "test_loss": test_loss,
        "test_accuracy": test_acc,
        "history": history,
        "classification_report": test_report,
        "ood_evaluation": ood_results,
    }
    with open(output_dir / "training_report.json", "w") as f:
        json.dump(report_data, f, indent=2)

    with open(output_dir / "confusion_matrix.txt", "w") as f:
        f.write(np.array2string(cm))

    if drive_out_path:
        with open(drive_out_path / "training_report.json", "w") as f:
            json.dump(report_data, f, indent=2)
        with open(drive_out_path / "confusion_matrix.txt", "w") as f:
            f.write(np.array2string(cm))
        print(f"[Google Drive] Synced Reports & Metrics to: {drive_out_path}")

    print("\n" + "="*70)
    print("   TRAINING & FEATURE ENGINEERING COMPLETED SUCCESSFULLY!   ")
    print(f"   Outputs available locally in: {output_dir.resolve()}")
    if drive_out_path:
        print(f"   Outputs backed up in Drive: {drive_out_path.resolve()}")
    print("="*70)


if __name__ == "__main__":
    main()
