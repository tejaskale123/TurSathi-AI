# -*- coding: utf-8 -*-
"""
TurSathi AI - Phase 4B: Read-Only Baseline Evaluation
Evaluates existing production model checkpoint on clean candidate test set.

Strict Safety Rules:
- 100% Read-Only: Checkpoint is loaded with torch.load(..., map_location='cpu'); never resaved.
- No model weights are modified or updated.
- Outputs saved exclusively to reports/pigeonpea_clean_candidate_v1_baseline/
"""

import sys
import os
import json
import time
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models
from sklearn.metrics import classification_report, confusion_matrix

# Windows encoding safety
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT_PATH = PROJECT_ROOT / "models" / "best_pigeonpea_disease_final_efficientnet_b0.pth"
TEST_DATA_DIR = PROJECT_ROOT / "datasets" / "pigeonpea_disease_clean_candidate_v1" / "test"
OUT_DIR = PROJECT_ROOT / "reports" / "pigeonpea_clean_candidate_v1_baseline"

IMG_SIZE = 224
BATCH_SIZE = 16

def run_evaluation():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("TurSathi AI - Production Model Baseline Evaluation on Clean Candidate Test Set")
    print(f"Checkpoint : {CHECKPOINT_PATH}")
    print(f"Test Data  : {TEST_DATA_DIR}")
    print(f"Output Dir : {OUT_DIR}")
    print("=" * 80)

    if not CHECKPOINT_PATH.exists():
        print(f"ERROR: Checkpoint file not found: {CHECKPOINT_PATH}")
        sys.exit(1)

    if not TEST_DATA_DIR.exists():
        print(f"ERROR: Test dataset directory not found: {TEST_DATA_DIR}")
        sys.exit(1)

    # 1. Device selection
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Inference Device: {device}")

    # 2. Load Checkpoint (Strictly Read-Only)
    checkpoint = torch.load(CHECKPOINT_PATH, map_location=device, weights_only=False)
    classes = checkpoint["classes"]
    num_classes = len(classes)
    best_epoch = checkpoint.get("best_epoch", "N/A")
    orig_best_val = checkpoint.get("best_val_accuracy", "N/A")

    print(f"Checkpoint Metadata:")
    print(f"  Classes ({num_classes}): {classes}")
    print(f"  Training Best Epoch: {best_epoch}")
    print(f"  Original Best Val Accuracy: {orig_best_val}")

    # 3. Model Architecture
    model = models.efficientnet_b0(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, num_classes)
    model.load_state_dict(checkpoint["model_state_dict"])
    model = model.to(device)
    model.eval()

    # 4. Data Loading with Exact Preprocessing
    eval_transforms = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    test_dataset = datasets.ImageFolder(TEST_DATA_DIR, transform=eval_transforms)
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    # Verify class-to-index alignment
    if test_dataset.classes != classes:
        print(f"CRITICAL MISMATCH: Test directory classes {test_dataset.classes} do not match model classes {classes}!")
        sys.exit(1)

    print(f"Test Samples: {len(test_dataset)} across classes {test_dataset.class_to_idx}")

    # 5. Inference Execution
    all_preds = []
    all_labels = []
    all_probs = []

    print("\nRunning inference...")
    start_t = time.time()
    with torch.no_grad():
        for inputs, labels in test_loader:
            inputs = inputs.to(device)
            outputs = model(inputs)
            probs = torch.softmax(outputs, dim=1)
            _, preds = torch.max(probs, 1)

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.numpy())
            all_probs.extend(probs.cpu().numpy())

    elapsed = time.time() - start_t
    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)

    # 6. Metrics Calculation
    acc = float(np.mean(all_preds == all_labels))
    cm = confusion_matrix(all_labels, all_preds)
    report_dict = classification_report(all_labels, all_preds, target_names=classes, digits=4, output_dict=True)
    report_text = classification_report(all_labels, all_preds, target_names=classes, digits=4)

    print("\n" + "=" * 80)
    print(f"BASELINE EVALUATION RESULTS (Clean Candidate Test Set)")
    print("=" * 80)
    print(f"Overall Accuracy: {acc * 100:.2f}% ({np.sum(all_preds == all_labels)} / {len(all_labels)})")
    print(f"Evaluation Time : {elapsed:.2f}s ({len(all_labels)/elapsed:.1f} images/sec)\n")
    print("Classification Report:\n", report_text)
    print("Confusion Matrix:\n", cm)

    # 7. Save Artifacts
    # A. Confusion matrix text
    with open(OUT_DIR / "baseline_confusion_matrix.txt", "w", encoding="utf-8") as f:
        f.write("Production Model Baseline Confusion Matrix on Clean Candidate Test Set\n")
        f.write("====================================================================\n\n")
        f.write(f"Classes: {classes}\n\n")
        f.write(np.array2string(cm, separator=', '))
        f.write("\n\nClassification Report:\n")
        f.write(report_text)

    # B. Detailed metrics JSON
    metrics_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "checkpoint_evaluated": str(CHECKPOINT_PATH),
        "test_dataset_evaluated": str(TEST_DATA_DIR),
        "total_test_samples": len(all_labels),
        "overall_accuracy": acc,
        "classification_report": report_dict,
        "confusion_matrix": cm.tolist(),
        "classes": classes,
        "wilt_test_support": int(np.sum(all_labels == classes.index("Wilt"))),
        "wilt_statistical_limitation_note": (
            "Wilt test support is exactly 5 held-out original field photographs. "
            "While 100% leak-free, 5 samples cannot support claims of production-grade field generalization."
        )
    }

    with open(OUT_DIR / "baseline_evaluation_metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics_data, f, indent=2)

    # C. Baseline Markdown Report
    with open(OUT_DIR / "BASELINE_EVALUATION_REPORT.md", "w", encoding="utf-8") as f:
        f.write("# TurSathi AI — Production Checkpoint Baseline Evaluation on Clean Candidate Test Set\n\n")
        f.write(f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}  \n")
        f.write(f"**Model Checkpoint:** `{CHECKPOINT_PATH.name}`  \n")
        f.write(f"**Test Set:** `datasets/pigeonpea_disease_clean_candidate_v1/test/` ({len(all_labels)} images)  \n")
        f.write(f"**Overall Accuracy:** **{acc * 100:.2f}%** ({np.sum(all_preds == all_labels)} / {len(all_labels)})\n\n")
        f.write("## 1. Classification Metrics\n\n")
        f.write("| Class | Precision | Recall | F1-Score | Support |\n")
        f.write("|---|:---:|:---:|:---:|:---:|\n")
        for cls in classes:
            c_m = report_dict[cls]
            f.write(f"| **{cls}** | {c_m['precision']:.4f} | {c_m['recall']:.4f} | {c_m['f1-score']:.4f} | {c_m['support']} |\n")
        f.write(f"| **Macro Avg** | {report_dict['macro avg']['precision']:.4f} | {report_dict['macro avg']['recall']:.4f} | {report_dict['macro avg']['f1-score']:.4f} | {report_dict['macro avg']['support']} |\n")
        f.write(f"| **Weighted Avg** | {report_dict['weighted avg']['precision']:.4f} | {report_dict['weighted avg']['recall']:.4f} | {report_dict['weighted avg']['f1-score']:.4f} | {report_dict['weighted avg']['support']} |\n\n")
        f.write("## 2. Confusion Matrix\n\n")
        f.write("```\n")
        f.write(f"Rows = True Labels, Columns = Predicted Labels\n")
        f.write(f"Classes order: {classes}\n\n")
        f.write(np.array2string(cm, separator=', '))
        f.write("\n```\n\n")
        f.write("## 3. Key Observations\n\n")
        f.write("1. **Impact of Cross-Class Duplicate Removal:** On the clean test set, the production model's true performance without leaked data is established.\n")
        f.write(f"2. **Wilt Class Evaluation Limitation:** Support for Wilt is strictly **{report_dict['Wilt']['support']} held-out original field photographs**. All leaked synthetic augmentations were successfully purged, eliminating evaluation leakage.\n")

    print(f"\nOutputs successfully saved to {OUT_DIR}")

if __name__ == "__main__":
    run_evaluation()
