# -*- coding: utf-8 -*-
"""
TurSathi AI - Phase 4B: Isolated Experimental Training Pipeline
Training script for the five-class pigeonpea disease classifier on clean candidate dataset v1.

Safety Rules & Isolation Guarantees:
1. Strict Data Path: Reads ONLY from datasets/pigeonpea_disease_clean_candidate_v1.
2. Strict Output Path: Writes ONLY to models/experimental/pigeonpea_clean_candidate_v1.
3. Production Protection: Hard assertions prevent writing to production checkpoints.
4. Overwrite Protection: Refuses to overwrite existing experimental artifacts without --overwrite.
5. Atomic Checkpoint Persistence: Checkpoints are written to temp files and atomically replaced.
6. Dry-Run Mode: Validates paths, data integrity, and class mapping without training.
"""

import sys
import os
import argparse
import json
import random
import time
from pathlib import Path
from collections import Counter

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
ALLOWED_DATASET_DIR = (PROJECT_ROOT / "datasets" / "pigeonpea_disease_clean_candidate_v1").resolve()
ALLOWED_OUTPUT_DIR = (PROJECT_ROOT / "models" / "experimental" / "pigeonpea_clean_candidate_v1").resolve()
PRODUCTION_CHECKPOINT_PATH = (PROJECT_ROOT / "models" / "best_pigeonpea_disease_final_efficientnet_b0.pth").resolve()

EXPECTED_CLASSES = ["Healthy", "Leaf_Spot", "Leaf_webber", "Sterilic_mosaic", "Wilt"]
SPLITS = ["train", "val", "test"]

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
        print("ERROR: CUDA is not available. GPU is required for training. Stopping.")
        sys.exit(1)
    device = torch.device("cuda")
    gpu_name = torch.cuda.get_device_name(0)
    vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    print(f"Device   : CUDA ({gpu_name}, {vram:.2f} GB VRAM)")
    return device

def validate_paths(data_dir_arg, output_dir_arg, overwrite=False):
    """Enforce strict isolation guarantees against production files."""
    data_dir = Path(data_dir_arg).resolve()
    output_dir = Path(output_dir_arg).resolve()

    # 1. Dataset safety check
    if data_dir != ALLOWED_DATASET_DIR:
        print(f"SAFETY VIOLATION: Dataset path must resolve strictly to {ALLOWED_DATASET_DIR}")
        print(f"Provided path: {data_dir}")
        sys.exit(1)

    # 2. Output directory safety check
    if not str(output_dir).startswith(str(PROJECT_ROOT / "models" / "experimental")):
        print(f"SAFETY VIOLATION: Output directory must be inside models/experimental/")
        print(f"Provided path: {output_dir}")
        sys.exit(1)

    # 3. Production checkpoint protection
    checkpoint_target = output_dir / "best_pigeonpea_clean_candidate_v1_efficientnet_b0.pth"
    if checkpoint_target == PRODUCTION_CHECKPOINT_PATH:
        print(f"CRITICAL SAFETY VIOLATION: Target matches production checkpoint path!")
        sys.exit(1)

    # 4. Overwrite protection
    if output_dir.exists() and any(output_dir.iterdir()) and not overwrite:
        print(f"OVERWRITE PROTECTION: Output directory {output_dir} already contains files.")
        print("Use --overwrite to allow overwriting experimental artifacts.")
        sys.exit(1)

    return data_dir, output_dir

def get_dataloaders(data_dir, img_size=224, batch_size=16, num_workers=2):
    train_dir = data_dir / "train"
    val_dir = data_dir / "val"
    test_dir = data_dir / "test"

    for d in [train_dir, val_dir, test_dir]:
        if not d.exists():
            print(f"ERROR: Missing split directory: {d}")
            sys.exit(1)

    train_transforms = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    eval_transforms = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    train_dataset = datasets.ImageFolder(train_dir, transform=train_transforms)
    val_dataset = datasets.ImageFolder(val_dir, transform=eval_transforms)
    test_dataset = datasets.ImageFolder(test_dir, transform=eval_transforms)

    # Class verification
    for dset, name in [(train_dataset, "train"), (val_dataset, "val"), (test_dataset, "test")]:
        if dset.classes != EXPECTED_CLASSES:
            print(f"ERROR: {name} dataset classes {dset.classes} do not match expected {EXPECTED_CLASSES}")
            sys.exit(1)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=num_workers, pin_memory=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers, pin_memory=True)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers, pin_memory=True)

    return train_loader, val_loader, test_loader, train_dataset.classes, {
        "train": len(train_dataset),
        "val": len(val_dataset),
        "test": len(test_dataset)
    }

def save_atomic_checkpoint(checkpoint_dict, target_path):
    """Save checkpoint atomically via temp file to prevent partial file writes."""
    target_path = Path(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target_path.with_suffix(".tmp")
    torch.save(checkpoint_dict, temp_path)
    os.replace(temp_path, target_path)

def main():
    parser = argparse.ArgumentParser(description="TurSathi AI - Isolated Clean Candidate Training Pipeline")
    parser.add_argument("--data-dir", type=str, default=str(ALLOWED_DATASET_DIR),
                        help="Path to clean candidate dataset (must resolve to allowed dir)")
    parser.add_argument("--output-dir", type=str, default=str(ALLOWED_OUTPUT_DIR),
                        help="Path to experimental output dir (must be inside models/experimental/)")
    parser.add_argument("--epochs", type=int, default=20, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=16, help="Training batch size")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--dry-run", action="store_true", help="Perform safety validation without training")
    parser.add_argument("--overwrite", action="store_true", help="Allow overwriting existing experimental outputs")
    args = parser.parse_args()

    print("=" * 80)
    print("TurSathi AI — Isolated Clean Candidate v1 Training Pipeline")
    print("=" * 80)

    # 1. Enforce strict isolation and path validation
    data_dir, output_dir = validate_paths(args.data_dir, args.output_dir, overwrite=args.overwrite)
    set_deterministic_seed(args.seed)

    print(f"Dataset Path : {data_dir}")
    print(f"Output Path  : {output_dir}")
    print(f"Seed         : {args.seed}")
    print(f"Dry-Run Mode : {args.dry_run}")
    print(f"Overwrite    : {args.overwrite}")

    # 2. Check CUDA
    device = check_cuda()

    # 3. Load & verify datasets
    train_loader, val_loader, test_loader, classes, counts = get_dataloaders(
        data_dir, img_size=224, batch_size=args.batch_size, num_workers=2
    )
    print(f"\nDataset Verified:")
    print(f"  Classes ({len(classes)}): {classes}")
    print(f"  Split Counts: Train={counts['train']}, Val={counts['val']}, Test={counts['test']} (Total={sum(counts.values())})")

    # Dry-Run Mode Exit
    if args.dry_run:
        print("\n" + "=" * 80)
        print("DRY-RUN VALIDATION PASSED")
        print("=" * 80)
        print("1. All dataset paths resolve strictly to datasets/pigeonpea_disease_clean_candidate_v1.")
        print("2. Output path is strictly isolated under models/experimental/pigeonpea_clean_candidate_v1.")
        print("3. Production checkpoint models/best_pigeonpea_disease_final_efficientnet_b0.pth is untouched.")
        print("4. CUDA is available and operational.")
        print("5. Classes and split counts verified.")
        print("6. Zero files were modified or trained.")
        sys.exit(0)

    # -------------------------------------------------------------
    # Actual Training Execution (Only runs when --dry-run is False)
    # -------------------------------------------------------------
    output_dir.mkdir(parents=True, exist_ok=True)
    model_save_path = output_dir / "best_pigeonpea_clean_candidate_v1_efficientnet_b0.pth"
    results_save_path = output_dir / "clean_candidate_v1_training_results.json"
    cm_save_path = output_dir / "clean_candidate_v1_confusion_matrix.txt"

    # Secondary safety assert
    assert model_save_path != PRODUCTION_CHECKPOINT_PATH, "CRITICAL: Attempting to save to production checkpoint!"

    print("\nInitializing EfficientNet-B0 architecture...")
    model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
    num_ftrs = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(num_ftrs, len(classes))
    model = model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=args.lr)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=0.1, patience=3)
    scaler = torch.amp.GradScaler('cuda')

    best_val_acc = 0.0
    best_epoch = 0
    results = {"train_loss": [], "train_acc": [], "val_loss": [], "val_acc": []}

    print(f"\nStarting Training ({args.epochs} epochs)...")
    for epoch in range(args.epochs):
        model.train()
        running_loss, corrects, total = 0.0, 0, 0
        for inputs, labels in train_loader:
            inputs, labels = inputs.to(device), labels.to(device)
            optimizer.zero_grad()
            with torch.amp.autocast('cuda'):
                outputs = model(inputs)
                loss = criterion(outputs, labels)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            running_loss += loss.item() * inputs.size(0)
            _, preds = torch.max(outputs, 1)
            corrects += torch.sum(preds == labels.data)
            total += inputs.size(0)

        epoch_loss = running_loss / total
        epoch_acc = corrects.double() / total

        # Validation Phase
        model.eval()
        val_running_loss, val_corrects, val_total = 0.0, 0, 0
        with torch.no_grad():
            for inputs, labels in val_loader:
                inputs, labels = inputs.to(device), labels.to(device)
                with torch.amp.autocast('cuda'):
                    outputs = model(inputs)
                    loss = criterion(outputs, labels)
                val_running_loss += loss.item() * inputs.size(0)
                _, preds = torch.max(outputs, 1)
                val_corrects += torch.sum(preds == labels.data)
                val_total += inputs.size(0)

        val_loss = val_running_loss / val_total
        val_acc = val_corrects.double() / val_total
        scheduler.step(val_acc)

        print(f"Epoch {epoch+1:02d}/{args.epochs:02d} | Train Loss: {epoch_loss:.4f} Acc: {epoch_acc:.4f} | Val Loss: {val_loss:.4f} Acc: {val_acc:.4f}")
        results["train_loss"].append(epoch_loss)
        results["train_acc"].append(epoch_acc.item())
        results["val_loss"].append(val_loss)
        results["val_acc"].append(val_acc.item())

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_epoch = epoch + 1
            ckpt_payload = {
                "model_state_dict": model.state_dict(),
                "classes": classes,
                "num_classes": len(classes),
                "best_val_accuracy": best_val_acc.item(),
                "best_epoch": best_epoch,
                "image_size": 224,
                "model_name": "efficientnet_b0",
                "dataset_name": "pigeonpea_disease_clean_candidate_v1",
                "experiment_id": "clean_candidate_v1_run",
                "hyperparameters": vars(args)
            }
            save_atomic_checkpoint(ckpt_payload, model_save_path)
            print(f"  -> Best model saved atomically to {model_save_path.name} (Epoch {best_epoch}, Val Acc: {best_val_acc:.4f})")

    # Evaluation on Clean Test Set
    print("\nEvaluating Best Model on Clean Test Set...")
    best_ckpt = torch.load(model_save_path)
    model.load_state_dict(best_ckpt["model_state_dict"])
    model.eval()

    test_corrects, test_total = 0, 0
    all_preds, all_labels = [], []
    with torch.no_grad():
        for inputs, labels in test_loader:
            inputs, labels = inputs.to(device), labels.to(device)
            with torch.amp.autocast('cuda'):
                outputs = model(inputs)
            _, preds = torch.max(outputs, 1)
            test_corrects += torch.sum(preds == labels.data)
            test_total += inputs.size(0)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    test_acc = test_corrects.double() / test_total
    report = classification_report(all_labels, all_preds, target_names=classes, digits=4)
    cm = confusion_matrix(all_labels, all_preds)

    print(f"\nFinal Clean Test Accuracy: {test_acc:.4f}")
    print("\nClassification Report:\n", report)
    print("\nConfusion Matrix:\n", cm)

    with open(cm_save_path, "w", encoding="utf-8") as f:
        f.write("Clean Candidate v1 Test Confusion Matrix\n")
        f.write(np.array2string(cm, separator=', '))
        f.write("\n\nClassification Report:\n")
        f.write(report)

    results["test_acc"] = test_acc.item()
    results["best_val_acc"] = best_val_acc.item()
    results["best_epoch"] = best_epoch
    results["wilt_test_support"] = 5
    with open(results_save_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4)

    print(f"\nArtifacts saved successfully to {output_dir}")

if __name__ == "__main__":
    main()
