import sys
from pathlib import Path
import torch
from PIL import Image
from torchvision import models
from torchvision.models import MobileNet_V3_Small_Weights

# Add backend to path
backend_path = Path("backend").resolve()
sys.path.append(str(backend_path))

from app.ml.tur_image_validator import TurImageValidator

def run_experiment():
    print("=" * 80)
    print("PHASE 3: INDEPENDENT VALIDATION EXPERIMENT")
    print("=" * 80)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    print("\n[1] Loading TurImageValidator...")
    validator = TurImageValidator()
    
    print("[2] Loading MobileNetV3-Small (ImageNet)...")
    weights = MobileNet_V3_Small_Weights.DEFAULT
    imagenet_model = models.mobilenet_v3_small(weights=weights).to(device)
    imagenet_model.eval()
    imagenet_transform = weights.transforms()
    categories = weights.meta["categories"]
    
    images = [
        ("Tur", "datasets/tur_image_validator/real_world_test/Tur/realworld_tur_01.png"),
        ("Tur", "datasets/tur_image_validator/real_world_test/Tur/realworld_tur_10.jpg"),
        ("Not_Tur", "datasets/tur_image_validator/real_world_test/Not_Tur/realworld_nottur_01.png"),
        ("Not_Tur", "datasets/tur_image_validator/real_world_test/Not_Tur/realworld_nottur_02.png"),
    ]
    
    print("\n[3] Running inference on 4 frozen holdout images...\n")
    
    for actual, path_str in images:
        path = Path(path_str)
        print(f"--- Image: {path.name} | Actual: {actual} ---")
        
        image = Image.open(path).convert("RGB")
        
        # Validator
        val_res = validator.predict(image)
        val_label = val_res["label"]
        val_conf = val_res["confidence"]
        print(f"Tur Validator: {val_label} ({val_conf:.4f})")
        
        # ImageNet
        input_tensor = imagenet_transform(image).unsqueeze(0).to(device)
        with torch.no_grad():
            output = imagenet_model(input_tensor)
            probs = torch.nn.functional.softmax(output[0], dim=0)
            top5_prob, top5_catid = torch.topk(probs, 5)
            
        print("ImageNet Top-5:")
        for i in range(5):
            cat_id = top5_catid[i].item()
            prob = top5_prob[i].item()
            cat_name = categories[cat_id]
            print(f"  {i+1}. {cat_name} (ID: {cat_id}) - {prob:.4f}")
            
        print()

if __name__ == "__main__":
    run_experiment()
