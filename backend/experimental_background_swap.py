import os
import sys
import json
import random
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import numpy as np
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
VAL_DIR = PROJECT_ROOT / "datasets" / "pigeonpea_disease_final" / "val"
LEAF_SPOT_DIR = VAL_DIR / "Leaf_Spot"
WILT_DIR = VAL_DIR / "Wilt"
MODEL_PATH = PROJECT_ROOT / "models" / "best_pigeonpea_disease_final_efficientnet_b0.pth"
OUTPUT_PATH = PROJECT_ROOT / "models" / "experimental_background_swap_results.json"
SCRATCH_DIR = PROJECT_ROOT / "backend" / "scratch_bias_experiment" / "swap_experiment"

# Check for high-quality segmentation prerequisites
HAS_REMBG = False
try:
    import rembg
    HAS_REMBG = True
except ImportError:
    pass

HAS_SAM = False
try:
    import segment_anything
    HAS_SAM = True
except ImportError:
    pass

def check_safety():
    if not MODEL_PATH.exists():
        print(f"ERROR: Production checkpoint not found at {MODEL_PATH}")
        return False
    if not LEAF_SPOT_DIR.exists() or not WILT_DIR.exists():
        print("ERROR: Validation directories for Leaf_Spot and Wilt are missing.")
        return False
    if OUTPUT_PATH.exists():
        print(f"ERROR: Output path {OUTPUT_PATH} already exists. Refusing to overwrite.")
        return False
    
    # We must have a reliable segmentation model
    if not HAS_REMBG and not HAS_SAM:
        print("ERROR: Missing prerequisite. A high-quality segmentation model (like 'rembg' or 'segment_anything') is not installed.")
        print("Falling back to primitive NumPy thresholding is forbidden by safety rules.")
        return False
        
    return True

def load_predictor_model(device):
    ckpt = torch.load(MODEL_PATH, map_location=device, weights_only=False)
    classes = ckpt["classes"]
    
    model = models.efficientnet_b0(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, len(classes))
    model.load_state_dict(ckpt["model_state_dict"])
    model.to(device)
    model.eval()
    
    return model, classes

def predict(model, classes, img, device):
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    input_tensor = transform(img).unsqueeze(0).to(device)
    with torch.no_grad():
        out = model(input_tensor)
        probs = torch.softmax(out, dim=1)[0]
        pred_idx = probs.argmax().item()
    return classes[pred_idx], probs[pred_idx].item()

def create_mask(img_np):
    """Create a segmentation mask using rembg (if available). Returns binary mask (H,W)."""
    if HAS_REMBG:
        # rembg returns RGBA, where A is the mask
        rgba = rembg.remove(Image.fromarray(img_np))
        alpha = np.array(rgba)[:, :, 3]
        return alpha > 128
    else:
        raise NotImplementedError("No segmentation model available.")

def check_mask_quality(mask):
    """
    Reject masks that are too small (missing leaf), too large (failed segmentation),
    or have too many disjoint components (ragged edges).
    """
    mask_ratio = np.sum(mask) / mask.size
    if mask_ratio < 0.10:
        return False, "Mask too small (leaf missing)"
    if mask_ratio > 0.95:
        return False, "Mask too large (failed background removal)"
    return True, "Valid"

def composite_image(fg_img_np, mask, bg_img_np):
    """Composite the foreground over the background using the mask."""
    # Ensure BG is same size as FG
    bg_img = Image.fromarray(bg_img_np).resize((fg_img_np.shape[1], fg_img_np.shape[0]))
    bg_img_np = np.array(bg_img)
    
    out = np.copy(bg_img_np)
    # Mask is 2D boolean, need to expand for RGB
    mask_3d = np.stack([mask]*3, axis=2)
    out[mask_3d] = fg_img_np[mask_3d]
    return Image.fromarray(out)

def main():
    if not check_safety():
        sys.exit(1)
        
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    
    model, classes = load_predictor_model(device)
    
    # 1. Pre-register images deterministically
    random.seed(42)
    leaf_spot_files = sorted(list(LEAF_SPOT_DIR.glob("*.jpg")))
    wilt_files = sorted(list(WILT_DIR.glob("*.jpg")))
    
    if len(leaf_spot_files) < 50 or len(wilt_files) < 50:
        print(f"ERROR: Insufficient images. Found {len(leaf_spot_files)} Leaf_Spot and {len(wilt_files)} Wilt.")
        sys.exit(1)
        
    selected_leaf_spot = random.sample(leaf_spot_files, 50)
    selected_wilt = random.sample(wilt_files, 50)
    
    dataset = [("Leaf_Spot", f) for f in selected_leaf_spot] + [("Wilt", f) for f in selected_wilt]
    
    # Pre-select adversarial backgrounds (shifted by 1 to ensure different image)
    adv_bgs = {}
    for i, (_, f) in enumerate(dataset):
        if "Leaf_Spot" in str(f):
            adv_bgs[f] = selected_wilt[(i % 50)]
        else:
            adv_bgs[f] = selected_leaf_spot[(i % 50)]

    results = []
    segmentation_failures = 0
    valid_count = 0
    
    print("\nStarting experimental image processing...")
    
    for true_cls, img_path in dataset:
        try:
            img = Image.open(img_path).convert("RGB")
            img_np = np.array(img)
            
            # Group A: Original
            pred_A, conf_A = predict(model, classes, img, device)
            
            # Segment
            mask = create_mask(img_np)
            is_valid, reason = check_mask_quality(mask)
            if not is_valid:
                segmentation_failures += 1
                continue
                
            valid_count += 1
            
            # Group B: Original background (re-composited to check for artifacts)
            img_B = composite_image(img_np, mask, img_np)
            pred_B, conf_B = predict(model, classes, img_B, device)
            
            # Group C: Neutral background (50% gray)
            gray_bg = np.full(img_np.shape, 128, dtype=np.uint8)
            img_C = composite_image(img_np, mask, gray_bg)
            pred_C, conf_C = predict(model, classes, img_C, device)
            
            # Group D: Adversarial background
            adv_bg_path = adv_bgs[img_path]
            adv_bg_img = np.array(Image.open(adv_bg_path).convert("RGB"))
            img_D = composite_image(img_np, mask, adv_bg_img)
            pred_D, conf_D = predict(model, classes, img_D, device)
            
            # Save images for offline inspection
            base_name = img_path.name
            img_B.save(SCRATCH_DIR / f"B_{base_name}")
            img_C.save(SCRATCH_DIR / f"C_{base_name}")
            img_D.save(SCRATCH_DIR / f"D_{base_name}")
            
            results.append({
                "path": base_name,
                "true_class": true_cls,
                "A_pred": pred_A, "A_conf": conf_A,
                "B_pred": pred_B, "B_conf": conf_B,
                "C_pred": pred_C, "C_conf": conf_C,
                "D_pred": pred_D, "D_conf": conf_D
            })
            
        except Exception as e:
            segmentation_failures += 1
            continue
            
    # Calculate Metrics
    def calc_metrics(subset_class):
        subset = [r for r in results if r["true_class"] == subset_class]
        count = len(subset)
        if count == 0: return None
        
        baseline_acc = sum(1 for r in subset if r["A_pred"] == subset_class) / count
        agreements_B = sum(1 for r in subset if r["A_pred"] == r["B_pred"]) / count
        agreements_C = sum(1 for r in subset if r["A_pred"] == r["C_pred"]) / count
        agreements_D = sum(1 for r in subset if r["A_pred"] == r["D_pred"]) / count
        
        avg_conf_change_C = sum((r["C_conf"] - r["A_conf"]) for r in subset) / count
        
        return {
            "valid_images": count,
            "baseline_accuracy": baseline_acc,
            "A_vs_B_agreement": agreements_B,
            "A_vs_C_agreement": agreements_C,
            "A_vs_C_avg_conf_change": avg_conf_change_C,
            "A_vs_D_agreement": agreements_D
        }

    metrics_leaf_spot = calc_metrics("Leaf_Spot")
    metrics_wilt = calc_metrics("Wilt")
    
    output_data = {
        "metadata": {
            "segmentation_failures": segmentation_failures,
            "total_valid_images": valid_count,
            "limitations": [
                "Two classes cannot establish bias severity for all 5 classes.",
                "If A vs B agreement is low, segmentation artifacts are confounding the results.",
                "Changes in confidence do not strictly equate to changes in correctness."
            ]
        },
        "metrics_leaf_spot": metrics_leaf_spot,
        "metrics_wilt": metrics_wilt,
        "raw_results": results
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output_data, f, indent=4)
        
    print(f"\nExperiment complete. Results saved to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
