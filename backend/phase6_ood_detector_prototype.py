import os
import sys
import numpy as np
import torch
import torch.nn.functional as F
from pathlib import Path
from PIL import Image
import logging

# Silence noisy loggers
logging.getLogger("tursathi.ml").setLevel(logging.ERROR)

# Setup paths relative to backend directory
PROJECT_ROOT = Path("..").resolve()
TRAIN_DIR = PROJECT_ROOT / "datasets" / "pigeonpea_disease_final" / "train"
VAL_DIR = PROJECT_ROOT / "datasets" / "pigeonpea_disease_final" / "val"
TEST_DIR = PROJECT_ROOT / "datasets" / "pigeonpea_disease_final" / "test"
OOD_DIR = PROJECT_ROOT / "datasets" / "new_disease_images"

# Add backend to sys.path
sys.path.insert(0, str(Path(".").resolve()))

from app.ml.tur_predictor import get_predictor

print("Loading model...")
predictor = get_predictor()
if not predictor.is_available():
    print("Error: Model is not available.")
    sys.exit(1)

model = predictor._model
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
model.eval()

# Verify classes
classes = predictor._classes
print(f"Verified classes: {classes}")

# Hook for extracting embeddings
embeddings = {}
def get_features(name):
    def hook(model, input, output):
        embeddings[name] = input[0].detach().cpu().numpy()
    return hook

# Attach hook to the final linear layer
# For efficientnet_b0 in torchvision, classifier is a Sequential:
# classifier[0] = Dropout
# classifier[1] = Linear
hook_handle = model.classifier[1].register_forward_hook(get_features("features"))

def extract_features_and_confidence(img_path):
    try:
        image = Image.open(img_path).convert("RGB")
        input_tensor = predictor._transform(image).unsqueeze(0).to(device)
        with torch.no_grad():
            output = model(input_tensor)
            probs = torch.softmax(output, dim=1)[0]
            pred_idx = probs.argmax().item()
            conf = probs[pred_idx].item()
            feat = embeddings["features"][0]  # shape (1280,)
        return feat, pred_idx, conf
    except Exception as e:
        return None, None, None

def process_directory(directory, limit_per_class=None):
    results = []
    if not directory.exists():
        print(f"Warning: Directory not found {directory}")
        return results
        
    for cls_name in classes:
        cls_dir = directory / cls_name
        if not cls_dir.exists():
            continue
            
        imgs = list(cls_dir.glob("*.jpg")) + list(cls_dir.glob("*.jpeg")) + list(cls_dir.glob("*.png"))
        if limit_per_class:
            imgs = imgs[:limit_per_class]
            
        for img_path in imgs:
            feat, pred_idx, conf = extract_features_and_confidence(img_path)
            if feat is not None:
                results.append({
                    "path": img_path,
                    "true_class": cls_name,
                    "pred_class": classes[pred_idx],
                    "confidence": conf,
                    "feature": feat
                })
    return results

def process_ood_directory(directory):
    results = []
    if not directory.exists():
        print(f"Warning: Directory not found {directory}")
        return results
        
    imgs = list(directory.glob("*.jpg")) + list(directory.glob("*.jpeg")) + list(directory.glob("*.png")) + list(directory.glob("*.webp"))
    for img_path in imgs:
        feat, pred_idx, conf = extract_features_and_confidence(img_path)
        if feat is not None:
            results.append({
                "path": img_path,
                "true_class": "Unsupported",
                "pred_class": classes[pred_idx],
                "confidence": conf,
                "feature": feat
            })
    return results

print("\n--- Step 1: Building Centroids (Train Set) ---")
train_results = process_directory(TRAIN_DIR, limit_per_class=100) # limit to 100 per class for prototype speed
print(f"Processed {len(train_results)} training images.")

centroids = {}
for cls_name in classes:
    cls_feats = [res["feature"] for res in train_results if res["true_class"] == cls_name]
    if cls_feats:
        centroids[cls_name] = np.mean(cls_feats, axis=0)

print("\n--- Step 2: Calibrating Threshold (Val Set) ---")
val_results = process_directory(VAL_DIR)
print(f"Processed {len(val_results)} validation images.")

def cosine_distance(feat1, feat2):
    norm1 = np.linalg.norm(feat1)
    norm2 = np.linalg.norm(feat2)
    if norm1 == 0 or norm2 == 0:
        return 1.0
    return 1 - np.dot(feat1, feat2) / (norm1 * norm2)

val_distances = []
for res in val_results:
    pred_cls = res["pred_class"]
    dist = cosine_distance(res["feature"], centroids[pred_cls])
    res["distance"] = dist
    val_distances.append(dist)

if val_distances:
    ood_threshold = np.percentile(val_distances, 95)
    print(f"95th percentile distance on validation set: {ood_threshold:.4f}")
else:
    print("Failed to compute threshold.")
    sys.exit(1)

print("\n--- Step 3: Evaluation (Test Sets) ---")
test_id_results = process_directory(TEST_DIR)
print(f"Processed {len(test_id_results)} Supported Test images.")

test_ood_results = process_ood_directory(OOD_DIR)
print(f"Processed {len(test_ood_results)} Unsupported images.")

def eval_metrics(id_res, ood_res, conf_thresh, dist_thresh):
    id_baseline_rejects = sum(1 for r in id_res if r["confidence"] < conf_thresh)
    ood_baseline_accepts = sum(1 for r in ood_res if r["confidence"] >= conf_thresh)
    
    id_dist_rejects = 0
    for r in id_res:
        dist = cosine_distance(r["feature"], centroids[r["pred_class"]])
        if dist > dist_thresh:
            id_dist_rejects += 1
            
    ood_dist_accepts = 0
    for r in ood_res:
        dist = cosine_distance(r["feature"], centroids[r["pred_class"]])
        if dist <= dist_thresh:
            ood_dist_accepts += 1
            
    return {
        "baseline_frr": id_baseline_rejects / max(1, len(id_res)),
        "baseline_far": ood_baseline_accepts / max(1, len(ood_res)),
        "proposed_frr": id_dist_rejects / max(1, len(id_res)),
        "proposed_far": ood_dist_accepts / max(1, len(ood_res)),
    }

metrics = eval_metrics(test_id_results, test_ood_results, 0.65, ood_threshold)

print("\n" + "="*50)
print("EVALUATION RESULTS")
print("="*50)
print(f"Supported Test Images (ID) : {len(test_id_results)}")
print(f"Unsupported Images (OOD)   : {len(test_ood_results)}")
print(f"\nBaseline (Confidence < 0.65):")
print(f"  False Rejection Rate (ID wrongly rejected) : {metrics['baseline_frr']:.2%}")
print(f"  False Acceptance Rate (OOD wrongly accepted): {metrics['baseline_far']:.2%}")

print(f"\nProposed OOD Detector (Distance > {ood_threshold:.4f}):")
print(f"  False Rejection Rate (ID wrongly rejected) : {metrics['proposed_frr']:.2%}")
print(f"  False Acceptance Rate (OOD wrongly accepted): {metrics['proposed_far']:.2%}")

print("\nPer-Class Breakdown (Supported Test):")
for cls_name in classes:
    cls_imgs = [r for r in test_id_results if r["true_class"] == cls_name]
    if not cls_imgs:
        continue
    correct = sum(1 for r in cls_imgs if r["pred_class"] == cls_name)
    rejected_baseline = sum(1 for r in cls_imgs if r["confidence"] < 0.65)
    rejected_proposed = sum(1 for r in cls_imgs if cosine_distance(r["feature"], centroids[r["pred_class"]]) > ood_threshold)
    print(f"  {cls_name:<15}: {len(cls_imgs):>3} imgs | Acc: {correct/len(cls_imgs):>6.2%} | FRR Baseline: {rejected_baseline/len(cls_imgs):>6.2%} | FRR Proposed: {rejected_proposed/len(cls_imgs):>6.2%}")

print("\nLimitations:")
print("- Validated on 42 unsupported images only. Does not guarantee 100% rejection on all unknown diseases.")
print("- The 5% False Rejection Rate on validation data does not guarantee exactly 5% on unseen data.")
print("="*50)

hook_handle.remove()
