import os
import sys
import argparse
import json
import random
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models
from sklearn.metrics import classification_report, confusion_matrix
from pathlib import Path

# Fix random seed for reproducibility
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "datasets" / "pigeonpea_disease_final"
MODELS_DIR = PROJECT_ROOT / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# SAFE EXPERIMENTAL PATHS
MODEL_SAVE_PATH = MODELS_DIR / "experimental_efficientnet_b0_bias_v2.pth"
RESULTS_SAVE_PATH = MODELS_DIR / "experimental_bias_v2_results.json"
CM_SAVE_PATH = MODELS_DIR / "experimental_bias_v2_cm.txt"

# Parameters
BATCH_SIZE = 16
NUM_WORKERS = 2
EPOCHS = 20
IMG_SIZE = 224
EXPECTED_CLASSES = ["Healthy", "Leaf_Spot", "Leaf_webber", "Sterilic_mosaic", "Wilt"]

def check_safety():
    """Ensure we do not overwrite existing experimental outputs or production weights."""
    if MODEL_SAVE_PATH.exists():
        print(f"ERROR: Safety violation. Checkpoint already exists at {MODEL_SAVE_PATH}")
        sys.exit(1)
    if RESULTS_SAVE_PATH.exists() or CM_SAVE_PATH.exists():
        print("ERROR: Safety violation. Experimental reports already exist.")
        sys.exit(1)
    
    # Extra check to ensure we aren't somehow pointing to the production model
    if "best_pigeonpea_disease_final" in str(MODEL_SAVE_PATH):
        print("ERROR: Safety violation. Pointing at production model path.")
        sys.exit(1)

def check_cuda():
    if not torch.cuda.is_available():
        print("ERROR: CUDA is not available. GPU is required for this training script. Stopping.")
        sys.exit(1)
    
    device = torch.device("cuda")
    gpu_name = torch.cuda.get_device_name(0)
    vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    
    print(f"DEVICE: CUDA")
    print(f"GPU: {gpu_name}")
    print(f"VRAM: {vram:.2f} GB")
    return device

def get_dataloaders():
    train_dir = DATA_DIR / "train"
    val_dir = DATA_DIR / "val"
    test_dir = DATA_DIR / "test"
    
    if not train_dir.exists() or not val_dir.exists() or not test_dir.exists():
        print("ERROR: Missing train, val, or test directories in dataset.")
        sys.exit(1)

    # EXPERIMENTAL AUGMENTATIONS:
    # 1. RandomResizedCrop replaces pure Resize. This forces the model to look at different 
    #    sub-regions of the image, breaking its reliance on the global background layout.
    #    We limit the scale to (0.4, 1.0) so we don't accidentally zoom too far into an 
    #    empty background patch.
    # 2. ColorJitter is retained to handle varying lighting conditions.
    # 3. RandomHorizontalFlip and RandomVerticalFlip added to break orientation bias.
    train_transforms = transforms.Compose([
        transforms.RandomResizedCrop(IMG_SIZE, scale=(0.8, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.RandomRotation(30),
        transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3, hue=0.0),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    
    # Deterministic validation transforms (same as production)
    eval_transforms = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    train_dataset = datasets.ImageFolder(train_dir, transform=train_transforms)
    val_dataset = datasets.ImageFolder(val_dir, transform=eval_transforms)
    test_dataset = datasets.ImageFolder(test_dir, transform=eval_transforms)

    if len(train_dataset.classes) != 5:
        print(f"ERROR: Expected exactly 5 classes, found {len(train_dataset.classes)}")
        sys.exit(1)
        
    for cls in EXPECTED_CLASSES:
        if cls not in train_dataset.classes:
            print(f"ERROR: Expected class {cls} not found in train dataset.")
            sys.exit(1)
            
    if train_dataset.classes != val_dataset.classes or train_dataset.classes != test_dataset.classes:
        print("ERROR: Class order differs between train, val, and test datasets.")
        sys.exit(1)
        
    print(f"CLASSES: {len(train_dataset.classes)}")
    print(f"Class names and indices: {train_dataset.class_to_idx}")
    print(f"TRAIN: {len(train_dataset)}")
    print(f"VAL: {len(val_dataset)}")
    print(f"TEST: {len(test_dataset)}")

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=NUM_WORKERS, pin_memory=True)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=NUM_WORKERS, pin_memory=True)
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=NUM_WORKERS, pin_memory=True)

    return train_loader, val_loader, test_loader, train_dataset.classes

def main():
    check_safety()
    device = check_cuda()
    
    train_loader, val_loader, test_loader, classes = get_dataloaders()
    num_classes = len(classes)

    model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
    num_ftrs = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(num_ftrs, num_classes)
    model = model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=1e-3)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=0.1, patience=3)

    best_val_acc = 0.0
    best_epoch = 0
    scaler = torch.amp.GradScaler('cuda')

    results = {
        "train_loss": [], "train_acc": [],
        "val_loss": [], "val_acc": []
    }

    print(f"\nStarting Experimental Bias-Fixed Training...")
    print(f"Saving to: {MODEL_SAVE_PATH}")
    
    for epoch in range(EPOCHS):
        # Training Phase
        model.train()
        running_loss = 0.0
        corrects = 0
        total = 0
        
        for inputs, labels in train_loader:
            inputs, labels = inputs.to(device), labels.to(device)
            optimizer.zero_grad()
            
            with torch.amp.autocast('cuda'):
                outputs = model(inputs)
                loss = criterion(outputs, labels)
                
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            
            running_loss += loss.item() * inputs.size(0)
            _, preds = torch.max(outputs, 1)
            corrects += torch.sum(preds == labels.data)
            total += inputs.size(0)
            
        epoch_loss = running_loss / total
        epoch_acc = corrects.double() / total
        
        # Validation Phase
        model.eval()
        val_running_loss = 0.0
        val_corrects = 0
        val_total = 0
        
        with torch.no_grad():
            for inputs, labels in val_loader:
                inputs, labels = inputs.to(device), labels.to(device)
                with torch.amp.autocast('cuda'):
                    outputs = model(inputs)
                    loss = criterion(outputs, labels)
                    
                val_running_loss += loss.item() * inputs.size(0)
                _, preds = torch.max(outputs, 1)
                val_corrects += torch.sum(preds == labels.data)
                val_total += inputs.size(0)
                
        val_loss = val_running_loss / val_total
        val_acc = val_corrects.double() / val_total
        
        scheduler.step(val_acc)
        
        print(f"Epoch {epoch+1}/{EPOCHS} | Train Loss: {epoch_loss:.4f} Acc: {epoch_acc:.4f} | Val Loss: {val_loss:.4f} Acc: {val_acc:.4f}")
        
        results["train_loss"].append(epoch_loss)
        results["train_acc"].append(epoch_acc.item())
        results["val_loss"].append(val_loss)
        results["val_acc"].append(val_acc.item())
        
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_epoch = epoch + 1
            checkpoint = {
                "model_state_dict": model.state_dict(),
                "classes": classes,
                "num_classes": num_classes,
                "best_val_accuracy": best_val_acc.item(),
                "best_epoch": best_epoch,
                "image_size": IMG_SIZE,
                "model_name": "experimental_efficientnet_b0"
            }
            torch.save(checkpoint, MODEL_SAVE_PATH)
            print(f"  -> Best model saved at epoch {best_epoch} with Val Acc: {best_val_acc:.4f}")
            
    print("\nTraining Complete.")
    
    print("\nEvaluating on Test Set with Best Model...")
    checkpoint = torch.load(MODEL_SAVE_PATH)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    
    test_running_loss, test_corrects, test_total = 0.0, 0, 0
    all_preds, all_labels = [], []
    
    with torch.no_grad():
        for inputs, labels in test_loader:
            inputs, labels = inputs.to(device), labels.to(device)
            with torch.amp.autocast('cuda'):
                outputs = model(inputs)
                loss = criterion(outputs, labels)
            
            test_running_loss += loss.item() * inputs.size(0)
            _, preds = torch.max(outputs, 1)
            test_corrects += torch.sum(preds == labels.data)
            test_total += inputs.size(0)
            
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
            
    test_loss = test_running_loss / test_total
    test_acc = test_corrects.double() / test_total
    
    print(f"\nTest Loss: {test_loss:.4f} | Accuracy: {test_acc:.4f}")
    
    report = classification_report(all_labels, all_preds, target_names=classes, digits=4)
    cm = confusion_matrix(all_labels, all_preds)
    
    with open(CM_SAVE_PATH, "w") as f:
        f.write("Confusion Matrix:\n" + np.array2string(cm, separator=', ') + "\n\nClassification Report:\n" + report)
        
    results["test_loss"] = test_loss
    results["test_acc"] = test_acc.item()
    results["best_val_accuracy"] = best_val_acc.item()
    results["best_epoch"] = best_epoch
    
    with open(RESULTS_SAVE_PATH, "w") as f:
        json.dump(results, f, indent=4)
        
    print(f"\nResults saved to {RESULTS_SAVE_PATH}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Experimental Training Script for Bias Mitigation")
    parser.add_argument("--start-training", action="store_true", help="Required flag to actually start training.")
    args = parser.parse_args()
    
    if not args.start_training:
        print("ERROR: You must pass --start-training to begin execution. Stopping to ensure safety.")
        sys.exit(1)
        
    main()
