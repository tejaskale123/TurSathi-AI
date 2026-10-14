import os
import sys
import json
import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms
from pathlib import Path
from PIL import Image

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRAIN_DIR = PROJECT_ROOT / "datasets" / "pigeonpea_disease_final" / "train"
VAL_DIR = PROJECT_ROOT / "datasets" / "pigeonpea_disease_final" / "val"
TEST_DIR = PROJECT_ROOT / "datasets" / "pigeonpea_disease_final" / "test"
OOD_DIR = PROJECT_ROOT / "datasets" / "new_disease_images"
MODEL_PATH = PROJECT_ROOT / "models" / "best_pigeonpea_disease_final_efficientnet_b0.pth"
OUTPUT_PATH = PROJECT_ROOT / "models" / "experimental_embedding_eval_results.json"

def check_safety():
    if not MODEL_PATH.exists():
        print(f"ERROR: Production checkpoint not found at {MODEL_PATH}")
        return False
    for d in [TRAIN_DIR, VAL_DIR, TEST_DIR, OOD_DIR]:
        if not d.exists():
            print(f"ERROR: Dataset not found at {d}")
            return False
    if OUTPUT_PATH.exists():
        print(f"ERROR: Output path {OUTPUT_PATH} already exists. Refusing to overwrite.")
        return False
    return True

def cosine_distance(feat1, feat2):
    norm1 = np.linalg.norm(feat1)
    norm2 = np.linalg.norm(feat2)
    if norm1 == 0 or norm2 == 0:
        return 1.0
    return float(1 - np.dot(feat1, feat2) / (norm1 * norm2))

def main():
    if not check_safety():
        sys.exit(1)

    print("="*70)
    print("SAFE EMBEDDING-BASED OOD EVALUATION SCRIPT")
    print("="*70)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # 1. Load Model (Read-Only)
    checkpoint = torch.load(MODEL_PATH, map_location=device, weights_only=False)
    classes = checkpoint["classes"]
    num_classes = len(classes)
    
    model = models.efficientnet_b0(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, num_classes)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)
    model.eval()

    # Hook for extracting embeddings
    embeddings = {}
    def get_features(name):
        def hook(model, input, output):
            embeddings[name] = input[0].detach().cpu().numpy()
        return hook
    hook_handle = model.classifier[1].register_forward_hook(get_features("features"))

    # Preprocessing matching production
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    def extract_feature(img_path):
        try:
            image = Image.open(img_path).convert("RGB")
            input_tensor = transform(image).unsqueeze(0).to(device)
            with torch.no_grad():
                output = model(input_tensor)
                probs = torch.softmax(output, dim=1)[0]
                pred_idx = probs.argmax().item()
                conf = probs[pred_idx].item()
                feat = embeddings["features"][0]
            return feat, pred_idx, conf
        except Exception as e:
            return None, None, None

    def process_directory(directory, is_ood=False):
        results = []
        if is_ood:
            imgs = list(directory.glob("*.jpg")) + list(directory.glob("*.jpeg")) + list(directory.glob("*.png")) + list(directory.glob("*.webp"))
            for img_path in imgs:
                feat, pred_idx, conf = extract_feature(img_path)
                if feat is not None:
                    results.append({
                        "path": img_path.name,
                        "true_class": "Unsupported",
                        "pred_class": classes[pred_idx],
                        "confidence": float(conf),
                        "feature": feat
                    })
        else:
            for cls_name in classes:
                cls_dir = directory / cls_name
                if not cls_dir.exists(): continue
                imgs = list(cls_dir.glob("*.jpg")) + list(cls_dir.glob("*.jpeg")) + list(cls_dir.glob("*.png"))
                for img_path in imgs:
                    feat, pred_idx, conf = extract_feature(img_path)
                    if feat is not None:
                        results.append({
                            "path": img_path.name,
                            "true_class": cls_name,
                            "pred_class": classes[pred_idx],
                            "confidence": float(conf),
                            "feature": feat
                        })
        return results

    # 2. Build Centroids (Train Set)
    print("\n--- Step 1: Building Centroids (Train Set) ---")
    train_results = process_directory(TRAIN_DIR, is_ood=False)
    print(f"Processed {len(train_results)} training images.")
    
    centroids = {}
    train_counts = {}
    for cls_name in classes:
        cls_feats = [res["feature"] for res in train_results if res["true_class"] == cls_name]
        train_counts[cls_name] = len(cls_feats)
        if cls_feats:
            centroids[cls_name] = np.mean(cls_feats, axis=0)

    # 3. Calibrate Threshold (Val Set)
    print("\n--- Step 2: Calibrating Threshold (Validation Set) ---")
    val_results = process_directory(VAL_DIR, is_ood=False)
    print(f"Processed {len(val_results)} validation images.")
    
    val_distances = []
    for res in val_results:
        pred_cls = res["pred_class"]
        if pred_cls in centroids:
            dist = cosine_distance(res["feature"], centroids[pred_cls])
            val_distances.append(dist)

    if not val_distances:
        print("ERROR: Failed to compute distances on validation set.")
        sys.exit(1)

    ood_threshold = float(np.percentile(val_distances, 95))
    print(f"95th percentile distance on validation set: {ood_threshold:.4f}")

    # 4. Evaluate
    print("\n--- Step 3: Evaluation (Test Sets) ---")
    test_id_results = process_directory(TEST_DIR, is_ood=False)
    test_ood_results = process_directory(OOD_DIR, is_ood=True)
    
    total_id = len(test_id_results)
    total_ood = len(test_ood_results)
    
    id_rejects = 0
    for r in test_id_results:
        dist = cosine_distance(r["feature"], centroids[r["pred_class"]]) if r["pred_class"] in centroids else 1.0
        r["distance"] = dist
        if dist > ood_threshold:
            id_rejects += 1
            
    ood_accepts = 0
    for r in test_ood_results:
        dist = cosine_distance(r["feature"], centroids[r["pred_class"]]) if r["pred_class"] in centroids else 1.0
        r["distance"] = dist
        if dist <= ood_threshold:
            ood_accepts += 1

    frr = id_rejects / max(1, total_id)
    exploratory_far = ood_accepts / max(1, total_ood)

    # Class-wise Test Rejections
    class_rejections = {}
    for cls_name in classes:
        cls_imgs = [r for r in test_id_results if r["true_class"] == cls_name]
        if not cls_imgs: continue
        rejected = sum(1 for r in cls_imgs if r["distance"] > ood_threshold)
        class_rejections[cls_name] = {
            "total": len(cls_imgs),
            "rejected": rejected,
            "frr": rejected / max(1, len(cls_imgs))
        }

    # Output Summary
    print("\n" + "="*50)
    print("EVALUATION RESULTS")
    print("="*50)
    print(f"Supported Test Images (ID) : {total_id}")
    print(f"Unsupported Images (OOD)   : {total_ood} (Exploratory Only)")
    print(f"\nDetector (Distance > {ood_threshold:.4f}):")
    print(f"  False Rejection Rate (ID wrongly rejected) : {frr:.2%}")
    print(f"  False Acceptance Rate (OOD wrongly accepted): {exploratory_far:.2%} (Exploratory)")

    # Prepare JSON output (remove raw feature vectors to save space)
    for r in train_results + val_results + test_id_results + test_ood_results:
        if "feature" in r:
            del r["feature"]

    output_data = {
        "metadata": {
            "checkpoint": str(MODEL_PATH),
            "embedding_layer": "model.classifier[1] (Linear)",
            "embedding_dimension": 1280, # EfficientNet-b0
            "distance_metric": "cosine",
            "threshold_method": "95th percentile validation distances",
            "threshold_value": ood_threshold,
            "train_counts": train_counts,
            "limitations": [
                "OOD data is exploratory and unlabeled",
                "High cosine distance is not definitive proof of unsupported disease",
                "Low cosine distance is not definitive proof of supported disease"
            ]
        },
        "metrics": {
            "total_supported_test": total_id,
            "false_rejection_rate": frr,
            "total_exploratory_ood": total_ood,
            "exploratory_false_acceptance_rate": exploratory_far,
            "class_rejections": class_rejections
        },
        "id_results": test_id_results,
        "ood_results": test_ood_results
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output_data, f, indent=4)
        
    print(f"\nResults safely saved to {OUTPUT_PATH}")
    hook_handle.remove()

if __name__ == "__main__":
    main()
