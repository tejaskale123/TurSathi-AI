#!/usr/bin/env python3
"""
================================================================================
TurSathi AI - Comprehensive Offline Evaluation & Shadow Simulation
================================================================================
Evaluates end-to-end pipeline under different gating policies:
- Policy A: Raw 5-Class Disease Predictor (No Gate)
- Policy B: Current Production Gate (TurImageGate + Argmax Validator + Baseline Predictor)
- Policy C: Candidate Model with Static Thresholds
- Policy D: Candidate Model with Calibrated OOD Gate (th=0.35, conf=0.70, margin=0.20)

STRICT SAFETY:
- Completely offline, non-destructive read-only simulation.
- Does not modify database, production code, or live API endpoints.
- Saves results to ml/retraining/candidate_validation_v2/offline_evaluation_matrix.json.
================================================================================
"""

import os
import io
import sys
import json
import zipfile
from pathlib import Path
from collections import defaultdict
from datetime import datetime

import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "backend"))

CLEAN_ZIP_PATH = PROJECT_ROOT / "ml" / "retraining" / "TurSathi_Pigeonpea_Clean_Dataset.zip"
OOD_DIR = PROJECT_ROOT / "datasets" / "new_disease_images"
OUTPUT_DIR = PROJECT_ROOT / "ml" / "retraining" / "candidate_validation_v2"

CANDIDATE_CKPT_PATH = PROJECT_ROOT / "models" / "candidates" / "tursathi_efficientnet_b0_candidate_20261026_072810 (1).pth"
CANDIDATE_OOD_PATH = PROJECT_ROOT / "models" / "candidates" / "ood_feature_profile_20261026_072810 (1).json"

CLASSES = ["Healthy", "Leaf_Spot", "Leaf_webber", "Sterilic_mosaic", "Wilt"]
IMG_SIZE = 224
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class TurEfficientNetB0(nn.Module):
    def __init__(self, num_classes=5):
        super().__init__()
        base = models.efficientnet_b0(weights=None)
        self.features = base.features
        self.avgpool = base.avgpool
        in_f = base.classifier[1].in_features
        self.dropout = nn.Dropout(p=0.2, inplace=True)
        self.classifier = nn.Linear(in_f, num_classes)

    def extract_features(self, x):
        feat = self.features(x)
        feat = self.avgpool(feat)
        return torch.flatten(feat, 1)

    def forward(self, x):
        feat = self.extract_features(x)
        out = self.dropout(feat)
        return self.classifier(out), feat


def run_offline_matrix_simulation():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 80)
    print("TUR SATHI AI — COMPREHENSIVE OFFLINE EVALUATION MATRIX")
    print("=" * 80)

    # 1. Load Candidate Model & Profile
    ckpt = torch.load(CANDIDATE_CKPT_PATH, map_location=DEVICE, weights_only=False)
    cand_model = TurEfficientNetB0(num_classes=5)
    cand_model.load_state_dict(ckpt["model_state_dict"], strict=True)
    cand_model.to(DEVICE)
    cand_model.eval()

    with open(CANDIDATE_OOD_PATH, "r", encoding="utf-8") as f:
        ood_profile = json.load(f)

    norm_centroids = {}
    for c, vec in ood_profile["centroids"].items():
        arr = np.array(vec, dtype=np.float32)
        norm_centroids[c] = arr / (np.linalg.norm(arr) + 1e-8)

    # 2. Load Active Validator
    from app.ml.tur_image_validator import TurImageValidator
    from app.ml.tur_image_gate import TurImageGate
    validator = TurImageValidator()
    gate = TurImageGate()

    eval_tf = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    # 3. Load Untouched Test Set (261 images)
    test_samples = []
    with zipfile.ZipFile(CLEAN_ZIP_PATH, 'r') as zf:
        for name in zf.namelist():
            parts = name.split('/')
            if len(parts) >= 3 and parts[0] == "test":
                cls_name = parts[1]
                if cls_name in CLASSES and parts[2]:
                    data = zf.read(name)
                    test_samples.append((name, cls_name, data))

    print(f"Loaded {len(test_samples)} untouched in-distribution test samples.")

    # 4. Load External OOD Images (41 images)
    valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    ood_samples = []
    for f in sorted(OOD_DIR.iterdir()):
        if f.is_file() and f.suffix.lower() in valid_exts:
            ood_samples.append((f.name, f.read_bytes()))

    print(f"Loaded {len(ood_samples)} external diagnostic OOD samples.")

    # 5. Evaluate Matrix
    matrix_results = {}

    for policy_name in ["Policy_A_Raw_Predictor", "Policy_B_Active_Gate", "Policy_D_Calibrated_Gate"]:
        print(f"\nEvaluating {policy_name}...")
        
        # Test Set Evaluation
        test_correct = 0
        test_false_reject = 0
        test_class_accepted = defaultdict(int)
        test_class_total = defaultdict(int)

        for name, true_cls, img_bytes in test_samples:
            test_class_total[true_cls] += 1
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            
            # Gate check
            gate_pass = True
            if policy_name in ["Policy_B_Active_Gate", "Policy_D_Calibrated_Gate"]:
                val_res = validator.predict(img)
                if policy_name == "Policy_B_Active_Gate":
                    gate_pass = val_res["is_tur"]
                elif policy_name == "Policy_D_Calibrated_Gate":
                    # Calibrated validator threshold: confidence >= 0.85
                    gate_pass = (val_res["label"] == "Tur") and (val_res["confidence"] >= 0.85)

            if not gate_pass:
                test_false_reject += 1
                continue

            # Predictor check
            tensor = eval_tf(img).unsqueeze(0).to(DEVICE)
            with torch.no_grad():
                logits, feats = cand_model(tensor)
                probs = torch.softmax(logits, dim=1)[0].cpu().numpy()
                feat = feats[0].cpu().numpy()

            pred_idx = int(np.argmax(probs))
            conf = float(probs[pred_idx])
            pred_cls = CLASSES[pred_idx]
            
            # OOD check for Policy D
            ood_pass = True
            if policy_name == "Policy_D_Calibrated_Gate":
                norm_f = feat / (np.linalg.norm(feat) + 1e-8)
                dist = float(1.0 - np.dot(norm_f, norm_centroids[pred_cls]))
                th = 0.35 if pred_cls == "Wilt" else ood_profile["class_thresholds"].get(pred_cls, 0.45)
                ood_pass = (dist <= th) and (conf >= 0.70)

            if not ood_pass:
                test_false_reject += 1
                continue

            if pred_cls == true_cls:
                test_correct += 1
                test_class_accepted[true_cls] += 1

        # External OOD Set Evaluation
        ext_passed = 0
        ext_wilt_false_accept = 0
        ext_blocked = 0

        for name, img_bytes in ood_samples:
            img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            
            # Gate check
            gate_pass = True
            if policy_name in ["Policy_B_Active_Gate"]:
                val_res = validator.predict(img)
                gate_pass = val_res["is_tur"]
            elif policy_name in ["Policy_D_Calibrated_Gate"]:
                val_res = validator.predict(img)
                gate_pass = (val_res["label"] == "Tur") and (val_res["confidence"] >= 0.85)

            if not gate_pass:
                ext_blocked += 1
                continue

            tensor = eval_tf(img).unsqueeze(0).to(DEVICE)
            with torch.no_grad():
                logits, feats = cand_model(tensor)
                probs = torch.softmax(logits, dim=1)[0].cpu().numpy()
                feat = feats[0].cpu().numpy()

            pred_idx = int(np.argmax(probs))
            conf = float(probs[pred_idx])
            pred_cls = CLASSES[pred_idx]

            ood_pass = True
            if policy_name == "Policy_D_Calibrated_Gate":
                norm_f = feat / (np.linalg.norm(feat) + 1e-8)
                dist = float(1.0 - np.dot(norm_f, norm_centroids[pred_cls]))
                th = 0.35 if pred_cls == "Wilt" else ood_profile["class_thresholds"].get(pred_cls, 0.45)
                ood_pass = (dist <= th) and (conf >= 0.70)

            if ood_pass:
                ext_passed += 1
                if pred_cls == "Wilt":
                    ext_wilt_false_accept += 1
            else:
                ext_blocked += 1

        matrix_results[policy_name] = {
            "in_distribution_test": {
                "total": len(test_samples),
                "correct_accepted": test_correct,
                "overall_accuracy_rate": round(test_correct / len(test_samples), 4),
                "false_rejection_count": test_false_reject,
                "false_rejection_rate": round(test_false_reject / len(test_samples), 4),
            },
            "external_diagnostic_ood": {
                "total": len(ood_samples),
                "blocked_correctly": ext_blocked,
                "rejection_rate": round(ext_blocked / len(ood_samples), 4),
                "false_accepted_total": ext_passed,
                "false_accepted_as_wilt": ext_wilt_false_accept,
                "false_acceptance_rate": round(ext_passed / len(ood_samples), 4),
            }
        }

        print(f"  In-Dist Correct: {test_correct}/{len(test_samples)} ({test_correct/len(test_samples)*100:.1f}%) | False Rejections: {test_false_reject}")
        print(f"  External Blocked: {ext_blocked}/{len(ood_samples)} ({ext_blocked/len(ood_samples)*100:.1f}%) | Wilt False Accept: {ext_wilt_false_accept}")

    out_file = OUTPUT_DIR / "offline_evaluation_matrix.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "simulation_matrix": matrix_results
        }, f, indent=2)
    print(f"\n[Saved] Offline Matrix Results -> {out_file}")


if __name__ == "__main__":
    run_offline_matrix_simulation()
