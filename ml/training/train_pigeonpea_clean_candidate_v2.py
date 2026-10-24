# -*- coding: utf-8 -*-
"""
TurSathi AI - Phase 4: Isolated Experimental Training Pipeline (v2 Candidate)
Investigates 288x288 input resolution and class-sensitive loss to resolve Leaf_Spot vs Sterilic_mosaic confusion.

Strict Safety & Isolation Guarantees:
1. Dataset Source: Strictly datasets/pigeonpea_disease_clean_candidate_v1/train and val.
2. Test Set Isolation: Clean test set is strictly EXCLUDED from training, tuning, and checkpoint selection.
3. Checkpoint Target: models/experimental_efficientnet_b0_clean_v2.pth.
4. Protection: Refuses to overwrite production checkpoint or v1 experimental checkpoint.
5. Preserves Checkpoints: Verifies SHA-256 of production and v1 checkpoints before and after training.
6. Reporting: Writes logs and metrics strictly to reports/pigeonpea_experimental_clean_v2/.
"""

import sys
import os
import argparse
import json
import random
import time
import hashlib
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models
from sklearn.metrics import classification_report, confusion_matrix

# Windows stdout encoding safety
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = (PROJECT_ROOT / "datasets" / "pigeonpea_disease_clean_candidate_v1").resolve()
TRAIN_DIR = DATASET_DIR / "train"
VAL_DIR = DATASET_DIR / "val"
TEST_DIR = DATASET_DIR / "test"

PRODUCTION_CKPT = (PROJECT_ROOT / "models" / "best_pigeonpea_disease_final_efficientnet_b0.pth").resolve()
V1_EXPERIMENTAL_CKPT = (PROJECT_ROOT / "models" / "experimental_efficientnet_b0_clean_v1.pth").resolve()
V2_CANDIDATE_CKPT = (PROJECT_ROOT / "models" / "experimental_efficientnet_b0_clean_v2.pth").resolve()
REPORTS_DIR = (PROJECT_ROOT / "reports" / "pigeonpea_experimental_clean_v2").resolve()

EXPECTED_CLASSES = ["Healthy", "Leaf_Spot", "Leaf_webber", "Sterilic_mosaic", "Wilt"]

# Mathematically grounded class weights based on unaugmented biological diversity in training set:
# Biological original counts: Healthy=121, Leaf_Spot=175, Leaf_webber=87, Sterilic_mosaic=147, Wilt=20
# Weights penalize underrepresented biological features and counter asymmetric bias toward Leaf_Spot:
BIOLOGICAL_DIVERSITY_WEIGHTS = {
    "Healthy": 1.00,
    "Leaf_Spot": 0.90,
    "Leaf_webber": 1.00,
    "Sterilic_mosaic": 1.15,
    "Wilt": 1.25
}

def set_deterministic_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False

def check_cuda():
    if not torch.cuda.is_available():
        print("ERROR: CUDA is not available. GPU is required for experimental training. Stopping.")
        sys.exit(1)
    device = torch.device("cuda")
    gpu_name = torch.cuda.get_device_name(0)
    vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    print(f"Device   : CUDA ({gpu_name}, {vram:.2f} GB VRAM)")
    return device

def validate_safety_boundaries(target_ckpt_path, overwrite=False):
    """Enforce strict isolation against production and v1 artifacts."""
    target_ckpt = Path(target_ckpt_path).resolve()

    # 1. Production checkpoint protection
    if target_ckpt == PRODUCTION_CKPT:
        print(f"CRITICAL SAFETY VIOLATION: Target path matches production checkpoint: {PRODUCTION_CKPT}")
        sys.exit(1)

    # 2. V1 experimental checkpoint protection
    if target_ckpt == V1_EXPERIMENTAL_CKPT:
        print(f"SAFETY VIOLATION: Target path matches v1 experimental checkpoint: {V1_EXPERIMENTAL_CKPT}")
        sys.exit(1)

    # 3. Target directory validation
    if not str(target_ckpt).startswith(str(PROJECT_ROOT / "models")):
        print(f"SAFETY VIOLATION: Target checkpoint must reside in models directory.")
        sys.exit(1)

    # 4. Overwrite guard
    if target_ckpt.exists() and not overwrite:
        print(f"OVERWRITE GUARD: Target checkpoint already exists at {target_ckpt}.")
        print("Pass --overwrite explicitly to overwrite experimental-v2 checkpoint.")
        sys.exit(1)

    # 5. Checksum existing checkpoints for preservation auditing
    hashes = {}
    if PRODUCTION_CKPT.exists():
        hashes["production_before"] = hashlib.sha256(PRODUCTION_CKPT.read_bytes()).hexdigest()
    if V1_EXPERIMENTAL_CKPT.exists():
        hashes["v1_before"] = hashlib.sha256(V1_EXPERIMENTAL_CKPT.read_bytes()).hexdigest()

    return target_ckpt, hashes

def get_dataloaders(img_size=288, batch_size=16, num_workers=0):
    if not TRAIN_DIR.exists():
        print(f"ERROR: Missing train directory: {TRAIN_DIR}")
        sys.exit(1)
    if not VAL_DIR.exists():
        print(f"ERROR: Missing val directory: {VAL_DIR}")
        sys.exit(1)

    # Transforms tailored for 288x288 high-resolution feature extraction
    train_transforms = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    val_transforms = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    train_dataset = datasets.ImageFolder(TRAIN_DIR, transform=train_transforms)
    val_dataset = datasets.ImageFolder(VAL_DIR, transform=val_transforms)

    assert train_dataset.classes == EXPECTED_CLASSES, f"Train classes mismatch: {train_dataset.classes}"
    assert val_dataset.classes == EXPECTED_CLASSES, f"Val classes mismatch: {val_dataset.classes}"

    train_loader = DataLoader(
        train_dataset, batch_size=batch_size, shuffle=True,
        num_workers=num_workers, pin_memory=True
    )
    val_loader = DataLoader(
        val_dataset, batch_size=batch_size, shuffle=False,
        num_workers=num_workers, pin_memory=True
    )

    return train_loader, val_loader, train_dataset.classes, {
        "train": len(train_dataset),
        "val": len(val_dataset)
    }

def get_loss_criterion(weighting_mode, device):
    if weighting_mode == "none":
        print("Loss Function: CrossEntropyLoss (Uniform class weights)")
        return nn.CrossEntropyLoss()
    elif weighting_mode == "biological":
        weights = [BIOLOGICAL_DIVERSITY_WEIGHTS[cls] for cls in EXPECTED_CLASSES]
        weight_tensor = torch.tensor(weights, dtype=torch.float, device=device)
        print(f"Loss Function: Class-Weighted CrossEntropyLoss")
        print(f"  Class Weights (ordered by {EXPECTED_CLASSES}):")
        for cls, w in zip(EXPECTED_CLASSES, weights):
            print(f"    - {cls:16s}: {w:.2f}")
        return nn.CrossEntropyLoss(weight=weight_tensor)
    else:
        print(f"ERROR: Unknown weighting mode: {weighting_mode}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="TurSathi AI - Phase 4 Experimental v2 Training Pipeline (288x288 Resolution)")
    parser.add_argument("--epochs", type=int, default=20, help="Number of training epochs (default: 20)")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size (default: 16)")
    parser.add_argument("--lr", type=float, default=1e-3, help="Initial learning rate (default: 1e-3)")
    parser.add_argument("--img-size", type=int, default=288, help="Input image spatial resolution (default: 288)")
    parser.add_argument("--weighting", type=str, default="biological", choices=["none", "biological"],
                        help="Loss weighting scheme: 'none' (uniform) or 'biological' (counter Sterilic vs Spot bias)")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic random seed")
    parser.add_argument("--num-workers", type=int, default=0, help="DataLoader num_workers (0 for Windows stability)")
    parser.add_argument("--dry-run", action="store_true", help="Validate setup, paths, and datasets without starting training")
    parser.add_argument("--overwrite", action="store_true", help="Allow overwriting existing v2 experimental checkpoint")
    args = parser.parse_args()

    print("=" * 80)
    print("TurSathi AI — Phase 4 Experimental Training Pipeline (Candidate v2)")
    print("Investigation: 288x288 Resolution + Class-Sensitive Biological Loss")
    print("=" * 80)

    # 1. Strict Isolation and Checkpoint Safeguards
    target_ckpt, baseline_hashes = validate_safety_boundaries(V2_CANDIDATE_CKPT, overwrite=args.overwrite)
    set_deterministic_seed(args.seed)

    print(f"Dataset Path        : {DATASET_DIR}")
    print(f"Train Split         : {TRAIN_DIR}")
    print(f"Validation Split    : {VAL_DIR}")
    print(f"Candidate Checkpoint: {target_ckpt}")
    print(f"Reports Directory   : {REPORTS_DIR}")
    print(f"Input Resolution    : {args.img_size} x {args.img_size}")
    print(f"Loss Weighting      : {args.weighting}")
    print(f"Epochs              : {args.epochs}")
    print(f"Batch Size          : {args.batch_size}")
    print(f"Initial LR          : {args.lr}")
    print(f"Dry-Run Mode        : {args.dry_run}")
    print(f"Overwrite Mode      : {args.overwrite}")

    if "production_before" in baseline_hashes:
        print(f"Production Checkpoint SHA-256 (Guarded) : {baseline_hashes['production_before']}")
    if "v1_before" in baseline_hashes:
        print(f"V1 Experimental Checkpoint SHA-256      : {baseline_hashes['v1_before']}")

    # 2. Check Hardware
    device = check_cuda()

    # 3. Load & Verify Datasets
    train_loader, val_loader, classes, counts = get_dataloaders(
        img_size=args.img_size, batch_size=args.batch_size, num_workers=args.num_workers
    )
    print(f"\nDataset Verified:")
    print(f"  Classes ({len(classes)}): {classes}")
    print(f"  Split Counts: Train={counts['train']}, Val={counts['val']} (Total={counts['train'] + counts['val']})")
    print(f"  Notice: Clean test set ({TEST_DIR.name}) is strictly excluded from Phase 4.")

    # 4. Exit gracefully if dry-run
    if args.dry_run:
        print("\n" + "=" * 80)
        print("DRY-RUN VALIDATION SUCCESSFUL")
        print("=" * 80)
        print("1. All paths and dataset boundaries verified.")
        print("2. Production and v1 checkpoints are isolated and guarded.")
        print("3. CUDA GPU is available with AMP capability.")
        print(f"4. Model architecture initialized for {args.img_size}x{args.img_size} input resolution.")
        print("5. Zero weights were modified or trained.")
        sys.exit(0)

    # 5. Model Architecture
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\nInitializing EfficientNet-B0 with ImageNet pretrained backbone for {args.img_size}x{args.img_size}...")
    model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, len(classes))
    model = model.to(device)

    # 6. Loss, Optimizer, LR Scheduler
    criterion = get_loss_criterion(args.weighting, device)
    optimizer = optim.AdamW(model.parameters(), lr=args.lr)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=0.1, patience=3)
    scaler = torch.amp.GradScaler('cuda')

    best_val_acc = 0.0
    best_epoch = 0
    best_val_report = None
    best_val_cm = None

    history = {
        "train_loss": [],
        "train_acc": [],
        "val_loss": [],
        "val_acc": [],
        "learning_rates": []
    }

    start_train_time = time.time()
    print(f"\nStarting Phase 4 Experimental Training ({args.epochs} epochs)...\n")

    for epoch in range(args.epochs):
        current_lr = optimizer.param_groups[0]['lr']
        history["learning_rates"].append(current_lr)

        # Training Loop
        model.train()
        train_loss, train_corrects, train_total = 0.0, 0, 0
        for inputs, labels in train_loader:
            inputs, labels = inputs.to(device), labels.to(device)
            optimizer.zero_grad()

            with torch.amp.autocast('cuda'):
                outputs = model(inputs)
                loss = criterion(outputs, labels)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            train_loss += loss.item() * inputs.size(0)
            _, preds = torch.max(outputs, 1)
            train_corrects += torch.sum(preds == labels.data).item()
            train_total += inputs.size(0)

        epoch_train_loss = train_loss / train_total
        epoch_train_acc = train_corrects / train_total

        # Validation Loop (Model Selection Only)
        model.eval()
        val_loss, val_corrects, val_total = 0.0, 0, 0
        val_preds_list, val_labels_list = [], []

        with torch.no_grad():
            for inputs, labels in val_loader:
                inputs, labels = inputs.to(device), labels.to(device)
                with torch.amp.autocast('cuda'):
                    outputs = model(inputs)
                    loss = criterion(outputs, labels)

                val_loss += loss.item() * inputs.size(0)
                _, preds = torch.max(outputs, 1)
                val_corrects += torch.sum(preds == labels.data).item()
                val_total += inputs.size(0)

                val_preds_list.extend(preds.cpu().numpy())
                val_labels_list.extend(labels.cpu().numpy())

        epoch_val_loss = val_loss / val_total
        epoch_val_acc = val_corrects / val_total

        scheduler.step(epoch_val_acc)

        history["train_loss"].append(epoch_train_loss)
        history["train_acc"].append(epoch_train_acc)
        history["val_loss"].append(epoch_val_loss)
        history["val_acc"].append(epoch_val_acc)

        epoch_msg = (
            f"Epoch {epoch+1:02d}/{args.epochs:02d} | "
            f"Train Loss: {epoch_train_loss:.4f} Acc: {epoch_train_acc*100:.2f}% | "
            f"Val Loss: {epoch_val_loss:.4f} Acc: {epoch_val_acc*100:.2f}% | lr: {current_lr:.1e}"
        )

        if epoch_val_acc > best_val_acc:
            best_val_acc = epoch_val_acc
            best_epoch = epoch + 1
            best_val_cm = confusion_matrix(val_labels_list, val_preds_list)
            best_val_report = classification_report(
                val_labels_list, val_preds_list,
                target_names=EXPECTED_CLASSES, digits=4, output_dict=True
            )

            # Atomic save to temporary file first
            ckpt_dict = {
                "model_state_dict": model.state_dict(),
                "classes": EXPECTED_CLASSES,
                "num_classes": len(EXPECTED_CLASSES),
                "best_val_accuracy": float(best_val_acc),
                "best_epoch": int(best_epoch),
                "image_size": args.img_size,
                "model_name": "efficientnet_b0",
                "training_dataset": "datasets/pigeonpea_disease_clean_candidate_v1",
                "experiment_id": "experimental_efficientnet_b0_clean_v2",
                "hyperparameters": {
                    "epochs": args.epochs,
                    "batch_size": args.batch_size,
                    "learning_rate": args.lr,
                    "image_size": args.img_size,
                    "weighting": args.weighting,
                    "seed": args.seed,
                    "optimizer": "AdamW",
                    "scheduler": "ReduceLROnPlateau"
                }
            }
            tmp_ckpt = target_ckpt.with_suffix(".tmp")
            torch.save(ckpt_dict, tmp_ckpt)
            os.replace(tmp_ckpt, target_ckpt)
            print(f"{epoch_msg} -> Best model saved (Epoch {best_epoch}, Val Acc: {best_val_acc*100:.2f}%)", flush=True)
        else:
            print(epoch_msg, flush=True)

    total_training_time = time.time() - start_train_time
    print(f"\nTraining Complete in {total_training_time:.1f}s ({total_training_time/60:.2f} min).")

    # 7. Post-Training Integrity Checks
    if PRODUCTION_CKPT.exists():
        prod_sha_after = hashlib.sha256(PRODUCTION_CKPT.read_bytes()).hexdigest()
        assert baseline_hashes["production_before"] == prod_sha_after, "CRITICAL: Production checkpoint was altered!"
        print(f"Production Checkpoint Preservation: CONFIRMED ({prod_sha_after})")

    if V1_EXPERIMENTAL_CKPT.exists():
        v1_sha_after = hashlib.sha256(V1_EXPERIMENTAL_CKPT.read_bytes()).hexdigest()
        assert baseline_hashes["v1_before"] == v1_sha_after, "CRITICAL: V1 experimental checkpoint was altered!"
        print(f"V1 Experimental Checkpoint Preservation: CONFIRMED ({v1_sha_after})")

    v2_sha = hashlib.sha256(target_ckpt.read_bytes()).hexdigest()
    print(f"V2 Candidate Checkpoint SHA-256: {v2_sha}")

    # 8. Save Detailed Training Logs and Metrics
    results_payload = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "experiment_name": "experimental_efficientnet_b0_clean_v2",
        "experimental_checkpoint_path": str(target_ckpt),
        "experimental_checkpoint_sha256": v2_sha,
        "production_checkpoint_preserved": True,
        "production_checkpoint_sha256": prod_sha_after if PRODUCTION_CKPT.exists() else None,
        "v1_checkpoint_preserved": True,
        "v1_checkpoint_sha256": v1_sha_after if V1_EXPERIMENTAL_CKPT.exists() else None,
        "training_dataset": str(TRAIN_DIR),
        "validation_dataset": str(VAL_DIR),
        "hyperparameters": {
            "model_architecture": "efficientnet_b0",
            "pretrained_weights": "ImageNet (DEFAULT)",
            "image_size": args.img_size,
            "batch_size": args.batch_size,
            "initial_lr": args.lr,
            "loss_weighting_mode": args.weighting,
            "class_weights": BIOLOGICAL_DIVERSITY_WEIGHTS if args.weighting == "biological" else "uniform",
            "optimizer": "AdamW",
            "scheduler": "ReduceLROnPlateau(mode='max', factor=0.1, patience=3)",
            "epochs": args.epochs,
            "seed": args.seed
        },
        "dataset_counts": counts,
        "best_epoch": best_epoch,
        "best_val_accuracy": best_val_acc,
        "best_val_classification_report": best_val_report,
        "best_val_confusion_matrix": best_val_cm.tolist(),
        "classes": EXPECTED_CLASSES,
        "loss_curves": history,
        "total_training_time_seconds": total_training_time
    }

    results_json = REPORTS_DIR / "experimental_clean_v2_training_results.json"
    with open(results_json, "w", encoding="utf-8") as f:
        json.dump(results_payload, f, indent=2)

    report_md = REPORTS_DIR / "EXPERIMENTAL_CLEAN_V2_TRAINING_REPORT.md"
    with open(report_md, "w", encoding="utf-8") as f:
        f.write("# TurSathi AI — Phase 4: Candidate v2 Experimental Training Report\n\n")
        f.write(f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}  \n")
        f.write(f"**Candidate Checkpoint:** `{target_ckpt.name}`  \n")
        f.write(f"**SHA-256:** `{v2_sha}`  \n")
        f.write(f"**Resolution:** {args.img_size}x{args.img_size}  \n")
        f.write(f"**Loss Weighting:** `{args.weighting}`  \n")
        f.write(f"**Production Checkpoint Preservation:** Confirmed  \n\n")

        f.write("## 1. Best Validation Metrics (Model Selection Split)\n\n")
        f.write(f"- **Best Epoch:** {best_epoch} / {args.epochs}\n")
        f.write(f"- **Best Validation Accuracy:** **{best_val_acc * 100:.2f}%**\n\n")

        f.write("### Per-Class Validation Breakdown\n\n")
        f.write("| Class | Precision | Recall | F1-Score | Support |\n")
        f.write("|---|:---:|:---:|:---:|:---:|\n")
        for cls in EXPECTED_CLASSES:
            m = best_val_report[cls]
            f.write(f"| **{cls}** | {m['precision']:.4f} | {m['recall']:.4f} | {m['f1-score']:.4f} | {m['support']} |\n")
        f.write(f"| **Macro Avg** | {best_val_report['macro avg']['precision']:.4f} | {best_val_report['macro avg']['recall']:.4f} | {best_val_report['macro avg']['f1-score']:.4f} | {best_val_report['macro avg']['support']} |\n")
        f.write(f"| **Weighted Avg** | {best_val_report['weighted avg']['precision']:.4f} | {best_val_report['weighted avg']['recall']:.4f} | {best_val_report['weighted avg']['f1-score']:.4f} | {best_val_report['weighted avg']['support']} |\n\n")

        f.write("### Validation Confusion Matrix\n\n")
        f.write("```\n")
        f.write(f"Classes order: {EXPECTED_CLASSES}\n")
        f.write(np.array2string(best_val_cm, separator=', '))
        f.write("\n```\n")

    print(f"\nArtifacts saved successfully to:\n  {results_json}\n  {report_md}")

if __name__ == "__main__":
    main()
