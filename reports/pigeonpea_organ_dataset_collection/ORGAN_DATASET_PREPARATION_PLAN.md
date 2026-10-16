# TurSathi AI — Organ Detector Dataset Preparation Plan & Reuse Inventory

## 1. Executive Summary & Policy Compliance

This document establishes the safe, non-destructive data preparation plan for the 4-class on-device Pigeonpea Organ Detector.

### Strict Safety Boundaries:
1. **Original Datasets Are Immutable:** Zero files in `datasets/pigeonpea_disease_final/` or `datasets/tur_image_validator_v3/` are modified, renamed, moved, or deleted.
2. **No Data Fabrication:** We do not invent labels, generate fake images, or claim missing classes have data.
3. **Training Prohibited Until Complete:** Model training (`train_pigeonpea_organ_detector.py`) is blocked until all 4 classes contain verified, correctly labeled real-world images.

---

## 2. Reusable Image Inventory & Split Mapping

From the existing immutable datasets, **3,578 images** can be safely reused for two of the four classes:

| Organ Detector Class | Source Dataset | Train Images | Val Images | Test Images | Total Reusable | Readiness Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **`Tur_Leaf`** | `datasets/pigeonpea_disease_final/` | 1,113 | 369 | 376 | **1,858** | ✅ **READY FOR REUSE** |
| **`Not_Tur_or_Unsupported`** | `datasets/tur_image_validator_v3/Not_Tur/` | 1,460 | 127 | 133 | **1,720** | ✅ **READY FOR REUSE** |
| **`Tur_Pod`** | *None in workspace* | 0 | 0 | 0 | **0** | ❌ **MISSING BLOCKER** |
| **`Tur_WholePlant_or_Canopy`** | *None in workspace* | 0 | 0 | 0 | **0** | ❌ **MISSING BLOCKER** |
| **TOTALS** | | **2,573** | **496** | **509** | **3,578** | **BLOCKED (2/4 Classes)** |

### Class Source Details:
- **`Tur_Leaf` (1,858 images):**
  - Mapped directly from the 5 disease subdirectories of `pigeonpea_disease_final/` (`Healthy`, `Leaf_Spot`, `Leaf_webber`, `Sterilic_mosaic`, `Wilt`).
  - All images depict verified individual pigeonpea leaves under varied real-world lighting and field conditions.
  - Using the pre-established split preserves test set isolation.
- **`Not_Tur_or_Unsupported` (1,720 images):**
  - Mapped directly from `tur_image_validator_v3/{train,val,test}/Not_Tur/`.
  - Depicts neighboring agricultural crops (cotton, corn, soybean, rice, wheat), weeds, soil, and field equipment.

---

## 3. Training Pipeline Requirements Confirmation

Inspection of [`ml/training/train_pigeonpea_organ_detector.py`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/ml/training/train_pigeonpea_organ_detector.py) confirms the following exact specifications:

1. **Exact Class Names & Indices:**
   ```python
   CANONICAL_ORGAN_CLASSES = [
       "Not_Tur_or_Unsupported",  # Index 0
       "Tur_Leaf",                # Index 1
       "Tur_Pod",                 # Index 2
       "Tur_WholePlant_or_Canopy" # Index 3
   ]
   ```
2. **Directory Structure:**
   The training script supports standard ImageFolder layout:
   ```
   datasets/pigeonpea_organ_dataset/
   ├── train/
   │   ├── Not_Tur_or_Unsupported/
   │   ├── Tur_Leaf/
   │   ├── Tur_Pod/
   │   └── Tur_WholePlant_or_Canopy/
   ├── val/
   │   ├── Not_Tur_or_Unsupported/
   │   ├── Tur_Leaf/
   │   ├── Tur_Pod/
   │   └── Tur_WholePlant_or_Canopy/
   └── test/
       ├── Not_Tur_or_Unsupported/
       ├── Tur_Leaf/
       ├── Tur_Pod/
       └── Tur_WholePlant_or_Canopy/
   ```
3. **Image Formats & Thresholds:**
   - Supported extensions: `.jpg`, `.jpeg`, `.png`, `.webp`.
   - Minimum threshold per class: `MIN_IMAGES_PER_CLASS = 50` (fail-safe hard stop).
   - Recommended target for field robustness: 250–500 images per class across $\ge 5$ distinct farms.
4. **Model Architecture & Export Format:**
   - Architecture: MobileNetV3-Small (lightweight for mobile NPU/DSP execution).
   - PyTorch Output: `models/organ_detector/pigeonpea_organ_mobilenetv3.pth`
   - ONNX Output: `models/organ_detector/pigeonpea_organ_mobilenetv3.onnx`
   - Mobile TFLite Output: `mobile/assets/models/pigeonpea_organ_detector.tflite` (INT8 post-training quantized, target size $< 3.5\text{ MB}$).

---

## 4. Staging Script for Safe Assembly

When the missing `Tur_Pod` and `Tur_WholePlant_or_Canopy` images are provided, the following non-destructive assembly procedure safely copies the reusable images without altering the originals:

```bash
# Safe staging script command:
python -c "
import shutil
from pathlib import Path

dest_root = Path('datasets/pigeonpea_organ_dataset')
leaf_src = Path('datasets/pigeonpea_disease_final')
nottur_src = Path('datasets/tur_image_validator_v3')

for split in ['train', 'val', 'test']:
    # Stage Tur_Leaf
    leaf_dest = dest_root / split / 'Tur_Leaf'
    leaf_dest.mkdir(parents=True, exist_ok=True)
    for disease in ['Healthy', 'Leaf_Spot', 'Leaf_webber', 'Sterilic_mosaic', 'Wilt']:
        for img in (leaf_src / split / disease).glob('*.*'):
            target = leaf_dest / f'{disease.lower()}_{img.name}'
            if not target.exists():
                shutil.copy2(img, target)

    # Stage Not_Tur_or_Unsupported
    nottur_dest = dest_root / split / 'Not_Tur_or_Unsupported'
    nottur_dest.mkdir(parents=True, exist_ok=True)
    for img in (nottur_src / split / 'Not_Tur').glob('*.*'):
        target = nottur_dest / img.name
        if not target.exists():
            shutil.copy2(img, target)
print('Assembly of reusable classes completed successfully without modifying originals.')
"
```

---

## 5. What Must Be Collected & Single Next Action

### What Must Be Collected:
1. **`Tur_Pod`:** Minimum 50 (recommended 250–500) field photos of pigeonpea pods (developing green pods, mature brown pods, flowering pod clusters).
2. **`Tur_WholePlant_or_Canopy`:** Minimum 50 (recommended 200–500) field photos of full pigeonpea shrubs, branch canopies, and field rows from 1.0–2.5 meters away.

### The Single Next Action:
Deposit the missing real-world field photographs into:
- `datasets/pigeonpea_organ_dataset/train/Tur_Pod/` (plus `val/` and `test/`)
- `datasets/pigeonpea_organ_dataset/train/Tur_WholePlant_or_Canopy/` (plus `val/` and `test/`)

Once deposited, the training pipeline will execute cleanly and produce the genuine `pigeonpea_organ_detector.tflite` model.
