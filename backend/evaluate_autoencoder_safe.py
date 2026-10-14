import os
import sys
import json
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from pathlib import Path
from PIL import Image

# Setup paths relative to backend directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
VAL_DIR = PROJECT_ROOT / "datasets" / "pigeonpea_disease_final" / "val"
TEST_DIR = PROJECT_ROOT / "datasets" / "pigeonpea_disease_final" / "test"
OOD_DIR = PROJECT_ROOT / "datasets" / "new_disease_images"
MODEL_PATH = PROJECT_ROOT / "models" / "experimental_autoencoder.pth"
OUTPUT_PATH = PROJECT_ROOT / "models" / "experimental_autoencoder_eval_results.json"

CLASSES = ['Healthy', 'Leaf_Spot', 'Leaf_webber', 'Sterilic_mosaic', 'Wilt']

def check_safety():
    if not MODEL_PATH.exists():
        print(f"ERROR: Autoencoder checkpoint not found at {MODEL_PATH}")
        return False
    if not VAL_DIR.exists():
        print(f"ERROR: Validation dataset not found at {VAL_DIR}")
        return False
    if not TEST_DIR.exists():
        print(f"ERROR: Test dataset not found at {TEST_DIR}")
        return False
    if not OOD_DIR.exists():
        print(f"ERROR: OOD dataset not found at {OOD_DIR}")
        return False
    if OUTPUT_PATH.exists():
        print(f"ERROR: Output path {OUTPUT_PATH} already exists. Refusing to overwrite.")
        return False
    return True

# 1. Dataset Class (Matches Phase 7)
class TurDataset(Dataset):
    def __init__(self, directory, classes=None):
        self.image_paths = []
        self.labels = []
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(), # scales to [0, 1]
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

# 2. Autoencoder Architecture (Matches Phase 7)
class LightweightCAE(nn.Module):
    def __init__(self):
        super(LightweightCAE, self).__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(3, 16, 3, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv2d(16, 32, 3, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, 64, 3, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv2d(64, 128, 3, stride=2, padding=1),
            nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.ConvTranspose2d(128, 64, 3, stride=2, padding=1, output_padding=1),
            nn.ReLU(),
            nn.ConvTranspose2d(64, 32, 3, stride=2, padding=1, output_padding=1),
            nn.ReLU(),
            nn.ConvTranspose2d(32, 16, 3, stride=2, padding=1, output_padding=1),
            nn.ReLU(),
            nn.ConvTranspose2d(16, 3, 3, stride=2, padding=1, output_padding=1),
            nn.Sigmoid() 
        )

    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded

def main():
    if not check_safety():
        sys.exit(1)

    print("="*70)
    print("SAFE AUTOENCODER EVALUATION SCRIPT")
    print("="*70)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # Load Model (Read-Only)
    model = LightweightCAE()
    model.load_state_dict(torch.load(MODEL_PATH, map_location=device, weights_only=False))
    model.to(device)
    model.eval()

    # Load Datasets
    val_dataset = TurDataset(VAL_DIR, CLASSES)
    test_id_dataset = TurDataset(TEST_DIR, CLASSES)
    test_ood_dataset = TurDataset(OOD_DIR, None)

    val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False, collate_fn=collate_fn)
    test_id_loader = DataLoader(test_id_dataset, batch_size=32, shuffle=False, collate_fn=collate_fn)
    test_ood_loader = DataLoader(test_ood_dataset, batch_size=32, shuffle=False, collate_fn=collate_fn)

    # 1. Calibrate Threshold on Validation Set
    print("\n--- Calibrating Threshold (Validation Set) ---")
    val_errors = []
    with torch.no_grad():
        for images, _, _ in val_loader:
            if len(images) == 0: continue
            images = images.to(device)
            outputs = model(images)
            mse = torch.mean((outputs - images) ** 2, dim=[1,2,3]).cpu().numpy()
            val_errors.extend(mse)

    if not val_errors:
        print("ERROR: Validation set resulted in empty errors list.")
        sys.exit(1)

    ood_threshold = float(np.percentile(val_errors, 95))
    print(f"95th Percentile MSE Threshold on Validation Set: {ood_threshold:.6f}")

    # 2. Evaluate
    def evaluate(loader):
        results = []
        with torch.no_grad():
            for images, labels, paths in loader:
                if len(images) == 0: continue
                images = images.to(device)
                outputs = model(images)
                mse = torch.mean((outputs - images) ** 2, dim=[1,2,3]).cpu().numpy()
                for i in range(len(mse)):
                    results.append({"path": Path(paths[i]).name, "label": labels[i], "mse": float(mse[i])})
        return results

    print("\n--- Evaluation (Test Sets) ---")
    id_results = evaluate(test_id_loader)
    ood_results = evaluate(test_ood_loader)

    # 3. Calculate Metrics
    total_id = len(id_results)
    id_rejects = sum(1 for r in id_results if r["mse"] > ood_threshold)
    frr = id_rejects / max(1, total_id)

    total_ood = len(ood_results)
    ood_accepts = sum(1 for r in ood_results if r["mse"] <= ood_threshold)
    exploratory_far = ood_accepts / max(1, total_ood)

    # Class-wise Test Rejections
    class_rejections = {}
    for cls_name in CLASSES:
        cls_imgs = [r for r in id_results if r["label"] == cls_name]
        if not cls_imgs: continue
        rejected = sum(1 for r in cls_imgs if r["mse"] > ood_threshold)
        class_rejections[cls_name] = {
            "total": len(cls_imgs),
            "rejected": rejected,
            "frr": rejected / max(1, len(cls_imgs))
        }

    # Summary Output
    print("\n" + "="*50)
    print("EVALUATION RESULTS")
    print("="*50)
    print(f"Supported Test Images (ID) : {total_id}")
    print(f"Unsupported Images (OOD)   : {total_ood} (Exploratory Only)")
    print(f"\nAutoencoder Detector (MSE > {ood_threshold:.6f}):")
    print(f"  False Rejection Rate (ID wrongly rejected) : {frr:.2%}")
    print(f"  False Acceptance Rate (OOD wrongly accepted): {exploratory_far:.2%} (Exploratory)")

    print("\nPer-Class Breakdown (Supported Test):")
    for cls_name, stats in class_rejections.items():
        print(f"  {cls_name:<15}: {stats['total']:>3} imgs | FRR (Rejected): {stats['frr']:>6.2%}")

    # Write output to JSON safely
    output_data = {
        "metadata": {
            "checkpoint": str(MODEL_PATH),
            "threshold_method": "95th percentile validation MSE",
            "threshold_value": ood_threshold,
            "limitations": [
                "OOD data is exploratory and unlabeled",
                "Cannot formally establish exact FAR"
            ]
        },
        "metrics": {
            "total_supported_test": total_id,
            "false_rejection_rate": frr,
            "total_exploratory_ood": total_ood,
            "exploratory_false_acceptance_rate": exploratory_far,
            "class_rejections": class_rejections
        },
        "id_results": id_results,
        "ood_results": ood_results
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output_data, f, indent=4)
        
    print(f"\nResults safely saved to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
