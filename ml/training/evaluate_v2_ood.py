import os
import json
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODEL_PATH = PROJECT_ROOT / "models" / "experimental_efficientnet_b0_bias_v2.pth"
DATA_DIR = PROJECT_ROOT / "datasets" / "new_disease_images"
OUTPUT_PATH = PROJECT_ROOT / "models" / "experimental_bias_v2_ood_predictions.json"

def check_safety():
    if not MODEL_PATH.exists():
        print(f"ERROR: Model checkpoint not found at {MODEL_PATH}")
        return False
    if not DATA_DIR.exists():
        print(f"ERROR: Dataset not found at {DATA_DIR}")
        return False
    if OUTPUT_PATH.exists():
        print(f"ERROR: Output path {OUTPUT_PATH} already exists. Refusing to overwrite.")
        return False
    return True

def main():
    if not check_safety():
        return

    print("=" * 70)
    print("V2 OOD EVALUATION SCRIPT")
    print("=" * 70)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    
    # Load model checkpoint to get classes
    checkpoint = torch.load(MODEL_PATH, map_location=device, weights_only=False)
    classes = checkpoint["classes"]
    num_classes = len(classes)
    print(f"Classes found: {classes}")

    # Build model
    model = models.efficientnet_b0(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, num_classes)
    model.load_state_dict(checkpoint["model_state_dict"])
    model = model.to(device)
    model.eval()

    # Preprocessing (Verified against production predictor)
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    # Gather images
    image_files = []
    for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
        image_files.extend(DATA_DIR.rglob(ext))
    
    total_images = len(image_files)
    print(f"Found {total_images} images in {DATA_DIR}")

    predictions = []
    processed = 0
    unreadable = 0
    class_counts = {cls: 0 for cls in classes}

    for img_path in sorted(image_files):
        try:
            image = Image.open(img_path).convert("RGB")
            tensor = transform(image).unsqueeze(0).to(device)
            
            with torch.no_grad():
                output = model(tensor)
                probs = torch.softmax(output, dim=1)[0]
                confidence, pred_idx = torch.max(probs, dim=0)
                
            pred_class = classes[pred_idx.item()]
            conf_val = confidence.item()
            
            predictions.append({
                "file": img_path.name,
                "predicted": pred_class,
                "confidence": conf_val
            })
            
            class_counts[pred_class] += 1
            processed += 1
            print(f"Processed: {img_path.name} -> {pred_class} ({conf_val:.4f})")
            
        except Exception as e:
            print(f"ERROR reading {img_path.name}: {e}")
            unreadable += 1

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total Found: {total_images}")
    print(f"Processed: {processed}")
    print(f"Unreadable: {unreadable}")
    print("\nClass Prediction Counts:")
    for cls, count in class_counts.items():
        print(f"  {cls}: {count}")

    # Write output
    with open(OUTPUT_PATH, "w") as f:
        json.dump({
            "summary": {
                "total_found": total_images,
                "processed": processed,
                "unreadable": unreadable,
                "class_counts": class_counts
            },
            "predictions": predictions
        }, f, indent=4)
        
    print(f"\nUnverified predictions saved to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
