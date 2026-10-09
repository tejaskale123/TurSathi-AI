import os
import torch
import torch.nn as nn
from torchvision import datasets, transforms, models
from torch.utils.data import DataLoader
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import numpy as np
from pathlib import Path

def evaluate():
    print("=" * 80)
    print("PHASE 4K: INTERNAL TEST EVALUATION (V3)")
    print("=" * 80)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    img_size = 224
    batch_size = 32
    
    dataset_dir = Path("datasets/tur_image_validator_v3/test")
    model_path = "models/tur_image_validator_efficientnet_b0_v3.pth"
    
    test_transforms = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    
    test_dataset = datasets.ImageFolder(dataset_dir, transform=test_transforms)
    test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    
    class_names = test_dataset.classes
    print(f"Classes: {class_names}")
    
    model = models.efficientnet_b0(weights=None)
    num_ftrs = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(num_ftrs, len(class_names))
    model.load_state_dict(torch.load(model_path, map_location=device, weights_only=True))
    model = model.to(device)
    model.eval()
    
    all_preds = []
    all_labels = []
    all_probs = []
    
    with torch.no_grad():
        for inputs, labels in test_loader:
            inputs = inputs.to(device)
            labels = labels.to(device)
            
            outputs = model(inputs)
            probs = torch.nn.functional.softmax(outputs, dim=1)
            _, preds = torch.max(outputs, 1)
            
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
            all_probs.extend(probs.cpu().numpy())
            
    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)
    all_probs = np.array(all_probs)
    
    acc = accuracy_score(all_labels, all_preds)
    cm = confusion_matrix(all_labels, all_preds)
    cr = classification_report(all_labels, all_preds, target_names=class_names, output_dict=True)
    
    tur_idx = class_names.index("Tur")
    not_tur_idx = class_names.index("Not_Tur")
    
    tur_precision = cr["Tur"]["precision"]
    tur_recall = cr["Tur"]["recall"]
    not_tur_precision = cr["Not_Tur"]["precision"]
    not_tur_recall = cr["Not_Tur"]["recall"]
    
    correct_preds = np.sum(all_preds == all_labels)
    incorrect_preds = len(all_labels) - correct_preds
    
    report = []
    report.append("============================================================")
    report.append("V3 INTERNAL TEST REPORT")
    report.append("============================================================")
    report.append(f"Total test images      : {len(all_labels)}")
    report.append(f"Correct predictions    : {correct_preds}")
    report.append(f"Incorrect predictions  : {incorrect_preds}")
    report.append(f"Accuracy               : {acc:.4f}")
    report.append(f"Macro Precision        : {cr['macro avg']['precision']:.4f}")
    report.append(f"Macro Recall           : {cr['macro avg']['recall']:.4f}")
    report.append(f"Macro F1-score         : {cr['macro avg']['f1-score']:.4f}")
    report.append("-" * 60)
    report.append(f"Tur Precision          : {tur_precision:.4f}")
    report.append(f"Tur Recall             : {tur_recall:.4f}")
    report.append(f"Not_Tur Precision      : {not_tur_precision:.4f}")
    report.append(f"Not_Tur Recall         : {not_tur_recall:.4f}")
    report.append("-" * 60)
    report.append("Confusion Matrix:")
    report.append(f"                 Predicted {class_names[0]}    Predicted {class_names[1]}")
    report.append(f"Actual {class_names[0]}        {cm[0][0]:<15} {cm[0][1]}")
    report.append(f"Actual {class_names[1]}        {cm[1][0]:<15} {cm[1][1]}")
    
    # Confidence distribution
    report.append("-" * 60)
    report.append("Confidence Distribution:")
    tur_probs = all_probs[:, tur_idx]
    bins = [0.0, 0.5, 0.7, 0.9, 1.0]
    tur_actual_probs = tur_probs[all_labels == tur_idx]
    not_tur_actual_probs = tur_probs[all_labels == not_tur_idx]
    
    report.append("Tur Images (Predicted Tur Probability):")
    hist, _ = np.histogram(tur_actual_probs, bins=bins)
    report.append(f"  [0.0 - 0.5): {hist[0]}")
    report.append(f"  [0.5 - 0.7): {hist[1]}")
    report.append(f"  [0.7 - 0.9): {hist[2]}")
    report.append(f"  [0.9 - 1.0]: {hist[3]}")
    
    report.append("Not_Tur Images (Predicted Tur Probability):")
    hist, _ = np.histogram(not_tur_actual_probs, bins=bins)
    report.append(f"  [0.0 - 0.5): {hist[0]}")
    report.append(f"  [0.5 - 0.7): {hist[1]}")
    report.append(f"  [0.7 - 0.9): {hist[2]}")
    report.append(f"  [0.9 - 1.0]: {hist[3]}")
    
    report.append("============================================================")
    
    report_text = "\n".join(report)
    print(report_text)
    
    with open("v3_internal_test_report.txt", "w", encoding="utf-8") as f:
        f.write(report_text)
        
if __name__ == "__main__":
    evaluate()
