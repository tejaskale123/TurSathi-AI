import os
import torch
import torch.nn as nn
from torchvision import transforms, models
from PIL import Image
from pathlib import Path
import json

def evaluate_holdout():
    print("=" * 80)
    print("PHASE 4L: FROZEN REAL-WORLD HOLDOUT EVALUATION (V3)")
    print("=" * 80)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    img_size = 224
    
    holdout_dir = Path("datasets/tur_image_validator/real_world_test")
    model_path = "models/tur_image_validator_efficientnet_b0_v3.pth"
    
    test_transforms = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    
    class_names = ["Not_Tur", "Tur"]
    
    model = models.efficientnet_b0(weights=None)
    num_ftrs = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(num_ftrs, len(class_names))
    model.load_state_dict(torch.load(model_path, map_location=device, weights_only=True))
    model = model.to(device)
    model.eval()
    
    results = []
    
    tur_correct = 0
    tur_total = 0
    not_tur_correct = 0
    not_tur_total = 0
    
    false_accepts = []
    false_rejects = []
    
    cm = {"Tur": {"Tur": 0, "Not_Tur": 0}, "Not_Tur": {"Tur": 0, "Not_Tur": 0}}
    
    with torch.no_grad():
        for cls_name in class_names:
            cls_dir = holdout_dir / cls_name
            if not cls_dir.exists():
                continue
                
            for img_path in cls_dir.glob("*.*"):
                if img_path.suffix.lower() not in [".jpg", ".jpeg", ".png", ".webp"]:
                    continue
                    
                try:
                    img = Image.open(img_path).convert("RGB")
                    tensor = test_transforms(img).unsqueeze(0).to(device)
                    
                    outputs = model(tensor)
                    probs = torch.nn.functional.softmax(outputs, dim=1)[0]
                    _, pred_idx = torch.max(outputs, 1)
                    
                    pred_class = class_names[pred_idx.item()]
                    
                    is_correct = pred_class == cls_name
                    
                    if cls_name == "Tur":
                        tur_total += 1
                        if is_correct:
                            tur_correct += 1
                        else:
                            false_rejects.append((img_path.name, cls_name, pred_class, probs.cpu().numpy().tolist()))
                    else:
                        not_tur_total += 1
                        if is_correct:
                            not_tur_correct += 1
                        else:
                            false_accepts.append((img_path.name, cls_name, pred_class, probs.cpu().numpy().tolist()))
                            
                    cm[cls_name][pred_class] += 1
                    
                    results.append({
                        "filename": img_path.name,
                        "actual": cls_name,
                        "predicted": pred_class,
                        "tur_prob": probs[class_names.index("Tur")].item(),
                        "not_tur_prob": probs[class_names.index("Not_Tur")].item(),
                        "correct": is_correct
                    })
                except Exception as e:
                    print(f"Error processing {img_path.name}: {e}")
                    
    total = tur_total + not_tur_total
    correct = tur_correct + not_tur_correct
    
    acc = correct / total if total > 0 else 0
    tur_acc = tur_correct / tur_total if tur_total > 0 else 0
    not_tur_acc = not_tur_correct / not_tur_total if not_tur_total > 0 else 0
    
    report = []
    report.append("============================================================")
    report.append("V3 FROZEN REAL-WORLD HOLDOUT REPORT")
    report.append("============================================================")
    report.append(f"Total images      : {total}")
    report.append(f"Total Correct     : {correct}")
    report.append(f"Total Accuracy    : {acc:.4f}")
    report.append("-" * 60)
    report.append(f"Tur Total         : {tur_total}")
    report.append(f"Tur Correct       : {tur_correct}")
    report.append(f"Tur Recall/Acc    : {tur_acc:.4f}")
    report.append("-" * 60)
    report.append(f"Not_Tur Total     : {not_tur_total}")
    report.append(f"Not_Tur Correct   : {not_tur_correct}")
    report.append(f"Not_Tur Recall/Acc: {not_tur_acc:.4f}")
    report.append("-" * 60)
    report.append("Confusion Matrix:")
    report.append(f"                 Predicted {class_names[0]}    Predicted {class_names[1]}")
    report.append(f"Actual {class_names[0]}        {cm[class_names[0]][class_names[0]]:<15} {cm[class_names[0]][class_names[1]]}")
    report.append(f"Actual {class_names[1]}        {cm[class_names[1]][class_names[0]]:<15} {cm[class_names[1]][class_names[1]]}")
    report.append("-" * 60)
    report.append(f"False Acceptance (Predicted Tur, Actual Not_Tur) : {len(false_accepts)}")
    report.append(f"False Rejection  (Predicted Not_Tur, Actual Tur) : {len(false_rejects)}")
    
    report.append("\n============================================================")
    report.append("IMAGE PREDICTIONS")
    report.append("============================================================")
    for r in results:
        status = "CORRECT" if r["correct"] else "INCORRECT"
        report.append(f"{r['filename']}")
        report.append(f"  Actual: {r['actual']} -> Predicted: {r['predicted']} [{status}]")
        report.append(f"  Probs : Tur={r['tur_prob']:.4f}, Not_Tur={r['not_tur_prob']:.4f}")
        report.append("")
        
    report_text = "\n".join(report)
    print(report_text)
    
    with open("v3_realworld_holdout_report.txt", "w", encoding="utf-8") as f:
        f.write(report_text)
        
    with open("v3_realworld_holdout_results.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    evaluate_holdout()
