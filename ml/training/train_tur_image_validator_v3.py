import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models
import time
from pathlib import Path

def train_model():
    print("=" * 80)
    print("PHASE 4J: V3 MODEL TRAINING (EFFICIENTNET-B0)")
    print("=" * 80)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    # Hyperparameters
    batch_size = 32
    num_epochs = 15
    learning_rate = 1e-4
    img_size = 224
    
    dataset_dir = Path("datasets/tur_image_validator_v3")
    model_save_path = "models/tur_image_validator_efficientnet_b0_v3.pth"
    
    # Augmentations designed for real-world mobile/field images
    train_transforms = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        transforms.RandomResizedCrop(img_size, scale=(0.8, 1.0)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    
    val_transforms = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    
    # Load Datasets
    train_dataset = datasets.ImageFolder(dataset_dir / "train", transform=train_transforms)
    val_dataset = datasets.ImageFolder(dataset_dir / "val", transform=val_transforms)
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    
    class_names = train_dataset.classes
    print(f"Classes: {class_names}")
    
    # Initialize Model
    # Using torchvision.models.efficientnet_b0 with updated weights parameter
    model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
    
    # Modify classifier for binary classification
    num_ftrs = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(num_ftrs, len(class_names))
    model = model.to(device)
    
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', patience=3, factor=0.5)
    
    best_val_acc = 0.0
    best_epoch = 0
    final_train_acc = 0.0
    final_train_loss = 0.0
    final_val_loss = 0.0
    
    # Training Loop
    for epoch in range(num_epochs):
        print(f"\nEpoch {epoch+1}/{num_epochs}")
        print("-" * 10)
        
        # Train
        model.train()
        running_loss = 0.0
        running_corrects = 0
        
        for inputs, labels in train_loader:
            inputs = inputs.to(device)
            labels = labels.to(device)
            
            optimizer.zero_grad()
            
            outputs = model(inputs)
            _, preds = torch.max(outputs, 1)
            loss = criterion(outputs, labels)
            
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item() * inputs.size(0)
            running_corrects += torch.sum(preds == labels.data)
            
        epoch_loss = running_loss / len(train_dataset)
        epoch_acc = running_corrects.double() / len(train_dataset)
        print(f"Train Loss: {epoch_loss:.4f} Acc: {epoch_acc:.4f}")
        
        # Validation
        model.eval()
        val_running_loss = 0.0
        val_running_corrects = 0
        
        with torch.no_grad():
            for inputs, labels in val_loader:
                inputs = inputs.to(device)
                labels = labels.to(device)
                
                outputs = model(inputs)
                _, preds = torch.max(outputs, 1)
                loss = criterion(outputs, labels)
                
                val_running_loss += loss.item() * inputs.size(0)
                val_running_corrects += torch.sum(preds == labels.data)
                
        val_epoch_loss = val_running_loss / len(val_dataset)
        val_epoch_acc = val_running_corrects.double() / len(val_dataset)
        print(f"Val Loss: {val_epoch_loss:.4f} Acc: {val_epoch_acc:.4f}")
        
        scheduler.step(val_epoch_acc)
        
        if val_epoch_acc > best_val_acc:
            best_val_acc = val_epoch_acc
            best_epoch = epoch + 1
            final_train_acc = epoch_acc
            final_train_loss = epoch_loss
            final_val_loss = val_epoch_loss
            torch.save(model.state_dict(), model_save_path)
            print("  --> Saved new best model")
            
    print("\nTraining Complete!")
    print(f"Best Val Acc: {best_val_acc:.4f} (Epoch {best_epoch})")
    
    # Generate Report
    report = []
    report.append("============================================================")
    report.append("V3 TRAINING REPORT")
    report.append("============================================================")
    report.append(f"Model Architecture       : EfficientNet-B0")
    report.append(f"Pretrained Initialization: ImageNet (DEFAULT weights)")
    report.append(f"Input Image Size         : {img_size}x{img_size}")
    report.append(f"Augmentations Used       : Resize, RandomHorizontalFlip, RandomVerticalFlip, RandomRotation(15), ColorJitter, RandomResizedCrop")
    report.append(f"Optimizer                : AdamW")
    report.append(f"Initial Learning Rate    : {learning_rate}")
    report.append(f"Batch Size               : {batch_size}")
    report.append(f"Total Epochs Run         : {num_epochs}")
    report.append(f"Best Epoch               : {best_epoch}")
    report.append(f"Best Training Loss       : {final_train_loss:.4f}")
    report.append(f"Best Validation Loss     : {final_val_loss:.4f}")
    report.append(f"Best Training Acc        : {final_train_acc:.4f}")
    report.append(f"Best Validation Acc      : {best_val_acc:.4f}")
    report.append(f"Checkpoint Path          : {model_save_path}")
    report.append("============================================================")
    
    report_text = "\n".join(report)
    with open("v3_training_report.txt", "w", encoding="utf-8") as f:
        f.write(report_text)
        
if __name__ == "__main__":
    train_model()
