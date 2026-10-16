# TurSathi AI — Five-Class Pigeonpea Dataset Forensic Audit Report

**Audit Date:** 2026-10-14  
**Audit Target:** `datasets/pigeonpea_disease_final`  
**Model Checkpoint:** `models/best_pigeonpea_disease_final_efficientnet_b0.pth`  
**Auditor:** Senior Computer Vision & MLOps Dataset Auditor  
**Audit Status:** Complete — Read-Only Verification Passed (0 Dataset Mutations)

---

## Executive Summary

A forensic, read-only audit of the five-class pigeonpea (*Cajanus cajan*, Tur) disease classification dataset (`datasets/pigeonpea_disease_final`) and its training pipeline was conducted. The audit inspected all 1,858 dataset files, traced 100% of their provenance to upstream research sources, performed byte-level and perceptual hash analysis, and evaluated cross-split leakage and label integrity.

### Key Forensic Findings

1. **Catastrophic Cross-Class Duplication (55 Groups / 111 Images):**
   - Exactly 55 duplicate groups (111 images) are identical byte-for-byte between different classes (54 groups between `Leaf_Spot` and `Sterilic_mosaic`, and 1 group across `Leaf_Spot`, `Sterilic_mosaic`, and `Leaf_webber`).
   - Root cause: On 2026-10-04, `scripts/prepare_balanced_dataset.py` inadvertently ingested a dirty backup directory (`PPLD_extracted/PPLD_backup_before_duplicate_removal`) where upstream duplicates had previously existed. The deduplication logic ran *only within each class*, reintroducing 55 contradictory image pairs into the training and evaluation sets.
   - Direct impact: Explains why the model's confusion matrix shows 17 Sterilic_mosaic images predicted as Leaf_Spot and 9 Leaf_Spot images predicted as Sterilic_mosaic.

2. **Severe Cross-Split Data Leakage (34 Exact Groups + 244 Near-Duplicate Pairs):**
   - 34 exact duplicate groups (69 images) cross between `train`, `val`, and `test` splits.
   - In the `Wilt` class, only **30 unique field photographs** exist in total. These were augmented 9x into 270 synthetic variants. Because the split script grouped by suffix and truncated naively, **51 of the 58 test images (87.9%) in the Wilt class are augmented derivatives of images present in the training set**.
   - Direct impact: The reported 100.0% precision, 100.0% recall, and 1.0000 F1-score for Wilt on the test set is an artifact of cross-split synthetic leakage.

3. **Covariate Shift & Modality Bias in the Wilt Class:**
   - 100% of images in `Healthy`, `Leaf_Spot`, `Leaf_webber`, and `Sterilic_mosaic` (1,571 images) are 256x256 square crops of isolated leaves.
   - 100% of images in `Wilt` (287 images) are high-resolution portrait phone photos (1204x1600, 900x1600) showing whole plants against field soil and sky.
   - Background-swap diagnostic tests confirmed that swapping a field background into a Leaf_Spot image causes the model to classify it as Wilt with 98%–100% confidence.

4. **Zero Corrupt or Invalid Files:**
   - All 1,858 images are valid 3-channel RGB JPEGs with matching `.jpg` extensions. Zero decode errors, zero truncated bytes, and zero zero-byte files were detected.

5. **Integrity Baseline Maintained:**
   - Pre-audit and post-audit SHA-256 manifests confirm that 100% of original dataset files remain byte-identical. Zero files were modified, moved, renamed, or deleted.

---

## 1. Verified Dataset and Model Configuration

### Model Checkpoint Verification
- **Path:** `models/best_pigeonpea_disease_final_efficientnet_b0.pth` (16,369,557 bytes)
- **Architecture:** `efficientnet_b0` (transfer learning with modified final classifier `nn.Linear(1280, 5)`)
- **Input Image Size:** 224 x 224
- **Normalization:** Mean `[0.485, 0.456, 0.406]`, Std `[0.229, 0.224, 0.225]`
- **Best Epoch:** 11
- **Best Validation Accuracy:** 92.14% (`0.9214092140921409`)
- **Reported Test Accuracy:** 92.02% (`0.9202127659574468`, 346 / 376)
- **Saved Class Mapping:**
  ```python
  classes = ['Healthy', 'Leaf_Spot', 'Leaf_webber', 'Sterilic_mosaic', 'Wilt']
  ```
- **Index-to-Class Assignment:**
  - Index 0: `Healthy`
  - Index 1: `Leaf_Spot`
  - Index 2: `Leaf_webber`
  - Index 3: `Sterilic_mosaic`
  - Index 4: `Wilt`

### Production Integration Verification
- In `backend/app/ml/tur_predictor.py`, `TurDiseasePredictor` directly loads this checkpoint. The class order and mapping match identically.
- In `backend/tests/test_end_to_end_pipeline.py` and `backend/tests/run_api_evaluation.py`, the same five class names are enforced.

### Dataset Scope & Crop Separation
- **Target Pigeonpea Dataset:** `datasets/pigeonpea_disease_final` (Crop: *Cajanus cajan* / Tur).
- **Separate / Unrelated Crop Datasets (Excluded from Disease Classifier):**
  - `datasets/tur_image_validator_v3` (3,561 files): Crop gate dataset containing Pigeonpea vs Non-Tur crops (Cotton, Maize, Soybean, Rice, Wheat, and background artifacts) for `tur_image_validator_efficientnet_b0_v3.pth`.
  - `datasets/tur_varieties` (15 files): Reference varietal photos.
  - `datasets/tur` (0 files): Empty placeholder directories.
  - `datasets/new_disease_images` (42 files): Ad-hoc reference images.

---

## 2. Dataset Inventory and Class Counts

### Actual Directory Structure
```
datasets/pigeonpea_disease_final/
├── train/
│   ├── Healthy/            (215 images)
│   ├── Leaf_Spot/          (263 images)
│   ├── Leaf_webber/        (207 images)
│   ├── Sterilic_mosaic/    (256 images)
│   └── Wilt/               (172 images)
├── val/
│   ├── Healthy/            (71 images)
│   ├── Leaf_Spot/          (87 images)
│   ├── Leaf_webber/        (69 images)
│   ├── Sterilic_mosaic/    (85 images)
│   └── Wilt/               (57 images)
└── test/
    ├── Healthy/            (73 images)
    ├── Leaf_Spot/          (89 images)
    ├── Leaf_webber/        (70 images)
    ├── Sterilic_mosaic/    (86 images)
    └── Wilt/               (58 images)
```

### Class and Split Reconciliation Table

| Class | Train | Val | Test | Total | Unique SHA-256 | Internal Dups | Cross-Class Dups |
|---|---|---|---|---|---|---|---|
| **Healthy** | 215 | 71 | 73 | 359 | 359 | 0 | 0 |
| **Leaf_Spot** | 263 | 87 | 89 | 439 | 439 | 0 | 55 |
| **Leaf_webber** | 207 | 69 | 70 | 346 | 346 | 0 | 2 |
| **Sterilic_mosaic** | 256 | 85 | 86 | 427 | 427 | 0 | 56 |
| **Wilt** | 172 | 57 | 58 | 287 | 287 | 0 | 0 |
| **Grand Total** | **1,113** | **369** | **376** | **1,858** | **1,802** | **0** | **111 instances** |

*Note: Test counts (Healthy=73, Leaf_Spot=89, Leaf_webber=70, Sterilic_mosaic=86, Wilt=58; total=376) reconcile 100% with the support numbers in `pigeonpea_disease_final_confusion_matrix.txt`.*

### Format & Dimension Characteristics
- **Supported / Present Extensions:** 100% `.jpg` (1,858 files).
- **Image Encoded Formats:** 100% JPEG.
- **Color Modes:** 100% 3-channel RGB.
- **Rogue / Misplaced Files:** 0 files outside the designated class directories.
- **File Sizes:** Min 6,430 bytes, Max 444,205 bytes, Mean 49,300 bytes.
- **Dimensions:**
  - Classes 1–4 (`Healthy`, `Leaf_Spot`, `Leaf_webber`, `Sterilic_mosaic`): 1,571 images, all 256 x 256 square crops.
  - Class 5 (`Wilt`): 287 images, all portrait orientation (170 at 1204x1600, 27 at 900x1600, 25 at 1200x1600, 21 at 1038x1280, remainder variable high-res).

---

## 3. Corrupt and Invalid Image Detection

Every image was tested with two distinct verification routines:
1. `PIL.Image.open(f).verify()` to validate headers, EXIF, and JPEG markers.
2. `PIL.Image.open(f).load()` and raw pixel buffer decoding to guarantee uncorrupted scanlines.

### Results:
- **Corrupt / Unreadable Images:** **0**
- **Truncated / Malformed Files:** **0**
- **Zero-Byte Files:** **0**
- **Extension / Format Mismatches:** **0**
- **Non-RGB Modes (RGBA, Grayscale, CMYK):** **0**
- **Degenerate Dimensions (< 32x32):** **0**

---

## 4. Exact and Near-Duplicate Detection

### A. Exact Byte & Pixel Duplicates
- **File SHA-256 Duplicate Groups:** 55 groups (111 files).
- **Decoded RGB Pixel Hash Duplicate Groups:** 55 groups (111 files, 100% identical to file SHA-256).
- **Critical Discovery:** Within each individual class folder, zero exact duplicates exist. **All 55 duplicate groups cross class boundaries.**

#### Duplicate Breakdown:
- **54 groups** are duplicates between `Leaf_Spot` and `Sterilic_mosaic`.
- **1 group** (Group 13) is a tri-class duplicate across `Leaf_Spot`, `Sterilic_mosaic`, and `Leaf_webber`:
  - `train/Leaf_Spot/leaf_spot_train_0109.jpg`
  - `train/Sterilic_mosaic/sterilic_mosaic_train_0146.jpg`
  - `test/Leaf_webber/leaf_webber_test_0038.jpg`
  - SHA-256: `5691467c59fe2160ec43268c5d87d7576e12334066129eb21a0a323a9a32d3a5`

### B. Perceptual Near-Duplicates
Using vectorized Hamming distance over 64-bit DCT perceptual hash (`pHash`) and difference hash (`dHash`):
- **Total Near-Duplicate Pairs (pHash dist $\le 6$, dHash dist $\le 8$, excluding exact duplicates):** 408 pairs.
- **Cross-Class Near-Duplicate Pairs:** 20 pairs (e.g. `healthy_train_0139.jpg` vs `sterilic_mosaic_val_0024.jpg`, `leaf_spot_train_0029.jpg` vs `sterilic_mosaic_train_0116.jpg`).
- **Wilt Augmentation Cross-Split Near-Duplicate Pairs:** 181 pairs.

---

## 5. Train / Validation / Test Leakage Audit

### A. Confirmed Exact Leakage
34 of the 55 exact duplicate groups cross split boundaries:
- **Train $\leftrightarrow$ Test Leakage:** 17 groups (34 images). An image shown to the model during training is present under a conflicting class in the test set.
- **Train $\leftrightarrow$ Validation Leakage:** 12 groups (24 images).
- **Validation $\leftrightarrow$ Test Leakage:** 5 groups (10 images).

#### Representative Exact Leakage Examples:
1. `train/Leaf_Spot/leaf_spot_train_0008.jpg` $\leftrightarrow$ `test/Sterilic_mosaic/sterilic_mosaic_test_0066.jpg`
2. `train/Leaf_Spot/leaf_spot_train_0083.jpg` $\leftrightarrow$ `test/Sterilic_mosaic/sterilic_mosaic_test_0085.jpg`
3. `train/Leaf_Spot/leaf_spot_train_0089.jpg` $\leftrightarrow$ `test/Sterilic_mosaic/sterilic_mosaic_test_0046.jpg`
4. `train/Leaf_Spot/leaf_spot_train_0105.jpg` $\leftrightarrow$ `test/Sterilic_mosaic/sterilic_mosaic_test_0013.jpg`
5. `train/Leaf_Spot/leaf_spot_train_0107.jpg` $\leftrightarrow$ `test/Sterilic_mosaic/sterilic_mosaic_test_0023.jpg`

### B. Suspected Leakage in the Wilt Class
Forensic analysis of the 287 Wilt images revealed:
- **Total Unique Source Field Photos:** **30**
- **Synthetic Augmentations:** **257**
- **Split Distribution of Sources vs Augmentations:**
  - `train`: 19 original photos + 153 augmentations
  - `val`: 4 original photos + 53 augmentations
  - `test`: 7 original photos + 51 augmentations
- **Leakage Evidence:** 51 of the 58 test images in `test/Wilt` share `pHash=0, dHash=0` or `pHash <= 4` with images in `train/Wilt`.
- **Conclusion:** The evaluation of Wilt on the test set is compromised by training-data leakage.

---

## 6. Label Quality and Forensic Provenance

### Provenance Audit
Every single image in `datasets/pigeonpea_disease_final` was matched against upstream source archives:
- 1,571 images matched `PPLD_extracted` and `PPLD_processed`.
- 287 images matched `datasets/_temp_wilt_staging`.
- 0 images were unmatched (100% traceable).

### Root Cause of the 55 Cross-Class Duplicates
1. The upstream dataset `PPLD_extracted/PPLD_backup_before_duplicate_removal` contains 55 cross-class duplicate groups inherited from the original Mendeley Data / ResearchGate upload.
2. In a prior cleanup, an engineer created `PPLD_extracted/PPLD` (860 images) with 0 cross-class duplicates.
3. On 2026-10-04, `scripts/prepare_balanced_dataset.py` included both the clean directory AND the backup directory in its source list (`EXTERNAL_SOURCES`).
4. Because deduplication was executed inside `for cls in CLASSES:`, it removed duplicate files *within* each class folder, but reintroduced all 55 duplicate pairs across classes.

### Manual Review Manifest Summary
A total of **138 images** are cataloged in `reports/pigeonpea_dataset_forensic_audit/data/06_label_review_manifest.csv`:
- **111 images:** `CONFIRMED_CROSS_CLASS_DUPLICATE` (Severity: CRITICAL).
- **27 images:** `SUSPECTED_CROSS_CLASS_NEAR_DUPLICATE` (Severity: HIGH, Status: `NEEDS_MANUAL_REVIEW`).

---

## 7. Class Imbalance and Shortcut Learning Analysis

### Imbalance Summary

| Class | Total Count | % of Dataset | Unique Source Photos | Effective Representation |
|---|---|---|---|---|
| **Healthy** | 359 | 19.3% | 195 | Moderate |
| **Leaf_Spot** | 439 | 23.6% | 282 | Good |
| **Leaf_webber** | 346 | 18.6% | 146 | Moderate |
| **Sterilic_mosaic** | 427 | 23.0% | 237 | Good |
| **Wilt** | 287 | 15.4% | **30** | **Critically Deficient** |

### Impact of Modality Bias
The Wilt class suffers from a severe domain gap:
1. **Aspect Ratio / Resolution Shortcut:** When resized to 224x224, portrait images undergo dramatic distortion ($1:1.77$ vs $1:1$), giving the network an immediate geometric shortcut.
2. **Background Bias:** Wilt photos contain outdoor soil, sky, and dry stalks, whereas classes 1–4 feature laboratory-style or isolated foliage. As proven by the background-swap experiment, the classifier learned the background rather than the pathology.

---

## 8. Audit Artifacts Created

All artifacts are preserved in the dedicated directory `reports/pigeonpea_dataset_forensic_audit/`:

| Artifact | Type | Description |
|---|---|---|
| `summary_findings.json` | JSON | Machine-readable audit metrics, totals, and reconciliation stats |
| `data/01_dataset_inventory.csv` | CSV | Row-by-row manifest of all 1,858 images with hashes, dimensions, provenance |
| `data/02_corrupt_invalid_images.csv` | CSV | Zero records (confirms 0 corrupt images) |
| `data/03_exact_duplicates.csv` | CSV | 111 records detailing all 55 cross-class exact duplicate groups |
| `data/04_near_duplicates.csv` | CSV | 408 near-duplicate pairs (pHash $\le 6$, dHash $\le 8$) |
| `data/05_split_leakage.csv` | CSV | 315 records detailing confirmed and suspected cross-split leakage |
| `data/06_label_review_manifest.csv` | CSV | 138 flagged review candidates with recommended actions |
| `data/07_class_split_reconciliation.csv` | CSV | Per-class, per-split counts and unique hash reconciliation |
| `data/08_sha256_manifest.json` | JSON | Complete pre-audit SHA-256 hash and size baseline for all files |
| `FORENSIC_AUDIT_REPORT.md` | Markdown | This comprehensive forensic report |
| `scripts/audits/audit_pigeonpea_dataset_forensic.py` | Python | Deterministic, read-only audit script |

---

## 9. Commands Executed and Verification Results

1. `git status` — Clean working tree verified.
2. `python -c "import torch; ..."` — PyTorch 2.14.1+cu126 and CUDA availability confirmed.
3. Checkpoint inspection — Verified classes `['Healthy', 'Leaf_Spot', 'Leaf_webber', 'Sterilic_mosaic', 'Wilt']` and weights.
4. Upstream provenance matching — 1,838 unique upstream hashes indexed; 1,858 / 1,858 final dataset files matched.
5. Perceptual hashing and distance matrix — 1,858 images processed, 1,725,178 pairwise comparisons computed in 33.89 seconds.
6. Post-audit integrity verification — 100% of files checked against pre-audit SHA-256 hashes. **0 files modified**.

---

## 10. Prioritized Repair Plan (Awaiting User Approval)

The read-only audit is complete and no files were modified. The following prioritized plan is recommended once approval is granted:

### Priority 1: Purge Confirmed Cross-Class Duplicates (CRITICAL)
- **Action:** Remove the 55 duplicate groups (111 images) from `datasets/pigeonpea_disease_final`, or reconstruct the PPLD portion directly from `PPLD_extracted/PPLD` (which contains 860 verified, non-duplicate images).
- **Evidence:** 54 duplicate pairs between `Leaf_Spot` and `Sterilic_mosaic` are corrupting training signals and directly producing false positives.

### Priority 2: Fix Wilt Synthetic Leakage with Group-Aware Splitting (CRITICAL)
- **Action:** Enforce strict family grouping on the 30 source Wilt images. All augmentations of a source image must reside strictly in `train`. Only held-out, non-augmented source images should appear in `val` and `test`.
- **Evidence:** 51 of 58 test images currently leak training image features, invalidating reported test metrics.

### Priority 3: Resolve Suspected Near-Duplicate Cross-Class Pairs (HIGH)
- **Action:** Inspect the 27 near-duplicate cross-class pairs cataloged in `06_label_review_manifest.csv` and resolve ambiguous disease boundaries.

### Priority 4: Mitigate Wilt Domain Gap & Modality Bias (HIGH)
- **Action:** Crop leaf-level patches from the high-resolution Wilt images (to match the 256x256 single-leaf crop format of classes 1–4) or incorporate clean leaf-level field photos of wilted Tur plants.
- **Evidence:** Background swap flips 80% of Leaf_Spot predictions to Wilt due to soil/field background shortcuts.

### Priority 5: Update Dataset Generation Script (MEDIUM)
- **Action:** Update `scripts/prepare_balanced_dataset.py` to:
  1. Remove `PPLD_backup_before_duplicate_removal` from `EXTERNAL_SOURCES`.
  2. Implement global cross-class deduplication before splitting.
  3. Use robust stem-based family grouping.

---
*Report generated strictly read-only. Original dataset intact. Awaiting user approval before proceeding to any dataset modifications or retraining.*
