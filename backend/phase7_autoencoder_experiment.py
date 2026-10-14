import os
import sys
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from pathlib import Path
from PIL import Image

# Setup paths relative to backend directory
PROJECT_ROOT = Path("..").resolve()
TRAIN_DIR = PROJECT_ROOT / "datasets" / "pigeonpea_disease_final" / "train"
VAL_DIR = PROJECT_ROOT / "datasets" / "pigeonpea_disease_final" / "val"
TEST_DIR = PROJECT_ROOT / "datasets" / "pigeonpea_disease_final" / "test"
OOD_DIR = PROJECT_ROOT / "datasets" / "new_disease_images"
MODEL_SAVE_PATH = PROJECT_ROOT / "models" / "experimental_autoencoder.pth"

# 1. Dataset Class
class TurDataset(Dataset):
    def __init__(self, directory, classes=None, limit_per_class=None):
        self.image_paths = []
        self.labels = []
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(), # scales to [0, 1]
            # No ImageNet normalization (0.485, etc.), because we use Sigmoid output [0, 1] in decoder
        ])
        
        if classes is None: # OOD directory
            imgs = list(directory.glob("*.jpg")) + list(directory.glob("*.jpeg")) + list(directory.glob("*.png")) + list(directory.glob("*.webp"))
            self.image_paths = imgs
            self.labels = ["Unsupported"] * len(imgs)
        else:
            for cls_name in classes:
                cls_dir = directory / cls_name
                if not cls_dir.exists():
                    continue
                imgs = list(cls_dir.glob("*.jpg")) + list(cls_dir.glob("*.jpeg")) + list(cls_dir.glob("*.png"))
                if limit_per_class:
                    imgs = imgs[:limit_per_class]
                self.image_paths.extend(imgs)
                self.labels.extend([cls_name] * len(imgs))

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        path = self.image_paths[idx]
        try:
            image = Image.open(path).convert("RGB")
            tensor = self.transform(image)
            return tensor, self.labels[idx], str(path)
        except Exception as e:
            return None, self.labels[idx], str(path)

def collate_fn(batch):
    batch = [b for b in batch if b[0] is not None]
    if len(batch) == 0:
        return torch.Tensor(), [], []
    tensors, labels, paths = zip(*batch)
    return torch.stack(tensors), labels, paths

# 2. Autoencoder Architecture
class LightweightCAE(nn.Module):
    def __init__(self):
        super(LightweightCAE, self).__init__()
        # Input: 3 x 224 x 224
        self.encoder = nn.Sequential(
            nn.Conv2d(3, 16, 3, stride=2, padding=1), # 16 x 112 x 112
            nn.ReLU(),
            nn.Conv2d(16, 32, 3, stride=2, padding=1), # 32 x 56 x 56
            nn.ReLU(),
            nn.Conv2d(32, 64, 3, stride=2, padding=1), # 64 x 28 x 28
            nn.ReLU(),
            nn.Conv2d(64, 128, 3, stride=2, padding=1), # 128 x 14 x 14
            nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.ConvTranspose2d(128, 64, 3, stride=2, padding=1, output_padding=1), # 64 x 28 x 28
            nn.ReLU(),
            nn.ConvTranspose2d(64, 32, 3, stride=2, padding=1, output_padding=1), # 32 x 56 x 56
            nn.ReLU(),
            nn.ConvTranspose2d(32, 16, 3, stride=2, padding=1, output_padding=1), # 16 x 112 x 112
            nn.ReLU(),
            nn.ConvTranspose2d(16, 3, 3, stride=2, padding=1, output_padding=1), # 3 x 224 x 224
            nn.Sigmoid() # Output [0, 1]
        )

    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded

# 3. Main execution
if __name__ == "__main__":
    torch.manual_seed(42)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    classes = ['Healthy', 'Leaf_Spot', 'Leaf_webber', 'Sterilic_mosaic', 'Wilt']
    
    train_dataset = TurDataset(TRAIN_DIR, classes, limit_per_class=100) # prototype speed
    val_dataset = TurDataset(VAL_DIR, classes)
    test_id_dataset = TurDataset(TEST_DIR, classes)
    test_ood_dataset = TurDataset(OOD_DIR, None)

    print(f"Datasets Loaded:\n - Train (ID): {len(train_dataset)}\n - Val (ID): {len(val_dataset)}\n - Test (ID): {len(test_id_dataset)}\n - Test (OOD): {len(test_ood_dataset)}")

    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True, collate_fn=collate_fn)
    val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False, collate_fn=collate_fn)

    model = LightweightCAE().to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=1e-3)

    epochs = 15
    print("\n--- Starting Training ---")
    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        for images, _, _ in train_loader:
            if len(images) == 0: continue
            images = images.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, images)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * images.size(0)
            
        train_loss /= len(train_dataset)
        
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for images, _, _ in val_loader:
                if len(images) == 0: continue
                images = images.to(device)
                outputs = model(images)
                loss = criterion(outputs, images)
                val_loss += loss.item() * images.size(0)
        val_loss /= len(val_dataset)
        
        print(f"Epoch {epoch+1:02d}/{epochs} | Train Loss: {train_loss:.6f} | Val Loss: {val_loss:.6f}")

    print(f"\nSaving model to {MODEL_SAVE_PATH}...")
    torch.save(model.state_dict(), MODEL_SAVE_PATH)

    print("\n--- Calibrating Threshold (Validation Set) ---")
    model.eval()
    val_errors = []
    with torch.no_grad():
        for images, _, _ in val_loader:
            if len(images) == 0: continue
            images = images.to(device)
            outputs = model(images)
            # MSE per image
            mse = torch.mean((outputs - images) ** 2, dim=[1,2,3]).cpu().numpy()
            val_errors.extend(mse)
            
    if val_errors:
        ood_threshold = np.percentile(val_errors, 95)
        print(f"95th Percentile MSE Threshold on Validation Set: {ood_threshold:.6f}")
    else:
        print("Failed to compute threshold.")
        sys.exit(1)

    print("\n--- Evaluation (Test Sets) ---")
    def evaluate(dataset):
        loader = DataLoader(dataset, batch_size=32, shuffle=False, collate_fn=collate_fn)
        results = []
        with torch.no_grad():
            for images, labels, paths in loader:
                if len(images) == 0: continue
                images = images.to(device)
                outputs = model(images)
                mse = torch.mean((outputs - images) ** 2, dim=[1,2,3]).cpu().numpy()
                for i in range(len(mse)):
                    results.append({"path": paths[i], "label": labels[i], "mse": mse[i]})
        return results

    id_results = evaluate(test_id_dataset)
    ood_results = evaluate(test_ood_dataset)

    id_rejects = sum(1 for r in id_results if r["mse"] > ood_threshold)
    ood_accepts = sum(1 for r in ood_results if r["mse"] <= ood_threshold)

    print("\n" + "="*50)
    print("EVALUATION RESULTS")
    print("="*50)
    print(f"Supported Test Images (ID) : {len(id_results)}")
    print(f"Unsupported Images (OOD)   : {len(ood_results)}")
    print(f"\nAutoencoder Detector (MSE > {ood_threshold:.6f}):")
    print(f"  False Rejection Rate (ID wrongly rejected) : {id_rejects/max(1, len(id_results)):.2%}")
    print(f"  False Acceptance Rate (OOD wrongly accepted): {ood_accepts/max(1, len(ood_results)):.2%}")

    print("\nPer-Class Breakdown (Supported Test):")
    for cls_name in classes:
        cls_imgs = [r for r in id_results if r["label"] == cls_name]
        if not cls_imgs: continue
        rejected = sum(1 for r in cls_imgs if r["mse"] > ood_threshold)
        print(f"  {cls_name:<15}: {len(cls_imgs):>3} imgs | FRR (Rejected): {rejected/len(cls_imgs):>6.2%}")

    print("\nLimitations:")
    print("- Autoencoders can sometimes generalize and reconstruct unseen anomalous textures with low error.")
    print("- Evaluated on only 41 readable unsupported images. True universal OOD performance may vary.")
    print("="*50)
