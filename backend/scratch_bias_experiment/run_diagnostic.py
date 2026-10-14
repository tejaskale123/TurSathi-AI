import os
import sys
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRATCH_DIR = PROJECT_ROOT / "backend" / "scratch_bias_experiment"
TRANSFORMED_DIR = SCRATCH_DIR / "transformed_images"
REPORT_PATH = SCRATCH_DIR / "diagnostic_report.txt"

# Prevent overwriting if report exists (failsafe)
if REPORT_PATH.exists():
    print(f"Error: {REPORT_PATH} already exists.")
    sys.exit(1)

TRANSFORMED_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = PROJECT_ROOT / "models" / "best_pigeonpea_disease_final_efficientnet_b0.pth"
LEAF_SPOT_DIR = PROJECT_ROOT / "datasets" / "pigeonpea_disease_final" / "train" / "Leaf_Spot"
WILT_DIR = PROJECT_ROOT / "datasets" / "pigeonpea_disease_final" / "train" / "Wilt"

# Pick a wilt image to use as a complex background
COMPLEX_BG_IMG = WILT_DIR / "wilt_train_0000.jpg"

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def get_complex_bg(size=(224, 224)):
    bg = Image.open(COMPLEX_BG_IMG).convert("RGB")
    bg = bg.resize(size)
    return bg

def apply_complex_background(image_path, out_path):
    # Load original Leaf Spot
    img = Image.open(image_path).convert("RGB")
    original_size = img.size
    
    img_np = np.array(img)
    
    # Simple grey background thresholding:
    # Grey implies R, G, B are similar and not too bright.
    r, g, b = img_np[:,:,0], img_np[:,:,1], img_np[:,:,2]
    
    # Calculate std across color channels to find colorless (grey) areas
    std_rgb = np.std(img_np, axis=2)
    # Brightness
    brightness = np.mean(img_np, axis=2)
    
    # Mask: background is where standard deviation is low (grey) and brightness is not very high or very low
    # We tweak these to get a reasonable cut of the leaf.
    bg_mask = (std_rgb < 20) & (brightness > 40) & (brightness < 180)
    
    # Get the complex background, resized to match original image
    bg_img = get_complex_bg(size=original_size)
    bg_np = np.array(bg_img)
    
    # Blend them:
    out_np = np.copy(img_np)
    out_np[bg_mask] = bg_np[bg_mask]
    
    out_img = Image.fromarray(out_np)
    out_img.save(out_path)
    return out_img, np.sum(bg_mask) / bg_mask.size

def load_model():
    ckpt = torch.load(MODEL_PATH, map_location=device, weights_only=False)
    classes = ckpt["classes"]
    
    model = models.efficientnet_b0(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, len(classes))
    model.load_state_dict(ckpt["model_state_dict"])
    model = model.to(device)
    model.eval()
    
    return model, classes

def predict(model, classes, img_path_or_obj):
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    
    if isinstance(img_path_or_obj, str) or isinstance(img_path_or_obj, Path):
        img = Image.open(img_path_or_obj).convert("RGB")
    else:
        img = img_path_or_obj.convert("RGB")
        
    t = transform(img).unsqueeze(0).to(device)
    
    with torch.no_grad():
        out = model(t)
        probs = torch.softmax(out, dim=1)[0]
        
    scores = {classes[i]: probs[i].item() for i in range(len(classes))}
    pred_idx = probs.argmax().item()
    return classes[pred_idx], probs[pred_idx].item(), scores

def main():
    model, classes = load_model()
    
    # Select 10 Leaf_Spot images
    files = sorted(list(LEAF_SPOT_DIR.glob("*.jpg")))[:10]
    
    report_lines = []
    report_lines.append("STAGE 7: CONTROLLED BACKGROUND-BIAS DIAGNOSTIC REPORT")
    report_lines.append("=====================================================")
    report_lines.append("DISCLAIMER: This is a small, one-sided diagnostic. It cannot independently prove or rule out dataset bias, establish field accuracy, or justify retraining. Segmentation artifacts may act as confounding factors.\n")
    
    for f in files:
        fname = f.name
        
        # 1. Baseline Prediction
        orig_pred, orig_conf, orig_scores = predict(model, classes, f)
        
        # 2. Transform Background
        out_path = TRANSFORMED_DIR / f"bgswap_{fname}"
        trans_img, bg_ratio = apply_complex_background(f, out_path)
        
        # 3. Transformed Prediction
        trans_pred, trans_conf, trans_scores = predict(model, classes, trans_img)
        
        report_lines.append(f"Image: {fname} (True Label: Leaf_Spot)")
        report_lines.append(f"  -> Replaced Background Ratio: {bg_ratio:.1%}")
        report_lines.append(f"  [Original] Prediction: {orig_pred} ({orig_conf:.4f})")
        report_lines.append(f"      Original Scores: " + ", ".join([f"{k}:{v:.4f}" for k,v in orig_scores.items()]))
        report_lines.append(f"  [Swapped]  Prediction: {trans_pred} ({trans_conf:.4f})")
        report_lines.append(f"      Swapped Scores:  " + ", ".join([f"{k}:{v:.4f}" for k,v in trans_scores.items()]))
        
        if orig_pred != trans_pred:
            report_lines.append(f"  *** PREDICTION CHANGED TO {trans_pred} ***")
        report_lines.append("-" * 50)
        
    report_lines.append("\nConclusion limitation: Visual artifacts (halos, ragged edges) are visible in the transformed images due to basic NumPy segmentation. These edges may be contributing to the prediction shift alongside the background itself.")
    
    with open(REPORT_PATH, "w") as rf:
        rf.write("\n".join(report_lines))
        
    print(f"Done. Report saved to {REPORT_PATH}")

if __name__ == "__main__":
    main()
