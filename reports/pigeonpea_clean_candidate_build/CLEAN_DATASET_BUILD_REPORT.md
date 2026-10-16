# TurSathi AI — Phase 3: Clean Pigeonpea Dataset Build and Validation Report

**Build Date:** 2026-10-14  
**Source Dataset:** `datasets/pigeonpea_disease_final` (1,858 files)  
**Destination Dataset:** `datasets/pigeonpea_disease_clean_candidate_v1` (1,676 files)  
**Model Checkpoint Target:** `models/best_pigeonpea_disease_final_efficientnet_b0.pth`  
**Status:** Build & Independent Validation Complete — All 10/10 Checks Passed  
**Integrity:** 100% Byte-Identical Preservation of Source Dataset and Checkpoint

---

## 1. Executive Summary

In accordance with Phase 3 specifications, a separate, clean candidate dataset (`datasets/pigeonpea_disease_clean_candidate_v1`) has been built and validated.

All operations were strictly non-destructive:
- Zero source files in `datasets/pigeonpea_disease_final` were modified, moved, renamed, or deleted.
- The active model checkpoint `models/best_pigeonpea_disease_final_efficientnet_b0.pth` was not retrained or modified.
- Zero unrelated crop datasets (cotton, maize, soybean, rice, wheat) were included.
- All 55 cross-class exact duplicate groups (111 images) were excluded from training and evaluation.
- All Wilt synthetic augmentations derived from validation and test source families (71 images) were excluded to eliminate cross-split leakage.
- Validation and test splits for Wilt contain **only held-out original field photographs**.

---

## 2. Manifest Discrepancy Investigation and Resolution

During pre-build manifest auditing, the mathematical relationship between the numbers reported in Phase 2 was verified and resolved:

### The Reconciliation Accounting
- **Original Dataset Total:** **1,858 images**
- **Excluded Exact Cross-Class Duplicates:** **111 images** (55 groups)
  - 54 images in `Leaf_Spot`
  - 55 images in `Sterilic_mosaic`
  - 2 images in `Leaf_webber`
  - 0 images in `Healthy` / `Wilt`
  - *Sum: 54 + 55 + 2 = 111 images (cataloged in `01_exact_duplicate_exclusion_manifest.csv`)*
- **Excluded Wilt Evaluation Synthetic Augmentations:** **71 images**
  - The 30 original Wilt photos were split into 20 train, 5 validation, and 5 test families.
  - To prevent evaluation leakage, all 34 augmentations of the 5 validation families and all 37 augmentations of the 5 test families were excluded from the dataset.
  - *Sum: 34 + 37 = 71 images (marked `EXCLUDE_SYNTHETIC_EVAL_DERIVATIVE` in `04_proposed_group_aware_split_manifest.csv`)*
- **Total Excluded Images:** $111 + 71 = 182$ images.
- **Clean Candidate Pool:** $1,858 - 182 = \mathbf{1,676}$ **images**.

### Clean Originals vs Offline Augmentations Breakdown
- **Clean Independent Original Field/Leaf Photos:**
  - `Healthy`: 195
  - `Leaf_Spot`: 282
  - `Leaf_webber`: 146
  - `Sterilic_mosaic`: 237
  - `Wilt`: 30
  - **Subtotal Clean Originals:** **890 images**
- **Offline Augmentations in Clean Pool:**
  - `Healthy`: 164
  - `Leaf_Spot`: 103
  - `Leaf_webber`: 198
  - `Sterilic_mosaic`: 135
  - `Wilt`: 186 (derived strictly from the 20 training families)
  - **Subtotal Augmentations:** **786 images**
- **Total Clean Candidate Pool:** $890 + 786 = \mathbf{1,676}$ **images**.

*Finding:* Zero missing or unaccounted-for images. Every single one of the 1,858 source images is fully traced.

---

## 3. Clean Candidate Dataset Structure and Counts

### Directory Layout
```
datasets/pigeonpea_disease_clean_candidate_v1/
├── train/
│   ├── Healthy/            (285 images)
│   ├── Leaf_Spot/          (278 images)
│   ├── Leaf_webber/        (285 images)
│   ├── Sterilic_mosaic/    (282 images)
│   └── Wilt/               (206 images)
├── val/
│   ├── Healthy/            (28 images)
│   ├── Leaf_Spot/          (53 images)
│   ├── Leaf_webber/        (27 images)
│   ├── Sterilic_mosaic/    (38 images)
│   └── Wilt/               (5 images - held-out originals only)
└── test/
    ├── Healthy/            (46 images)
    ├── Leaf_Spot/          (54 images)
    ├── Leaf_webber/        (32 images)
    ├── Sterilic_mosaic/    (52 images)
    └── Wilt/               (5 images - held-out originals only)
```

### Class and Split Reconciliation Table

| Class | Train | Val (Held-out Originals) | Test (Held-out Originals) | Total Clean | Clean Originals | Augmentations (Train Only) |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Healthy** | 285 | 28 | 46 | **359** | 195 | 164 |
| **Leaf_Spot** | 278 | 53 | 54 | **385** | 282 | 103 |
| **Leaf_webber** | 285 | 27 | 32 | **344** | 146 | 198 |
| **Sterilic_mosaic** | 282 | 38 | 52 | **372** | 237 | 135 |
| **Wilt** | 206 | 5 | 5 | **216** | 30 | 186 |
| **Total** | **1,336** | **151** | **189** | **1,676** | **890** | **786** |

---

## 4. Independent Validation Results (10/10 Checks Passed)

The separate validator script `scripts/audits/validate_clean_pigeonpea_dataset.py` executed ten automated checks against `datasets/pigeonpea_disease_clean_candidate_v1`:

| # | Check Name | Status | Details |
|:---:|---|:---:|---|
| **1** | All 15 Split/Class Folders Exist | **PASS** | All 3 splits $\times$ 5 classes created and populated |
| **2** | Filesystem vs Manifest Count Reconciliation | **PASS** | Manifest rows: 1,676; Files on disk: 1,676 |
| **3** | Image Decodability and Mode Integrity | **PASS** | 0 corrupt images. All 1,676 images verified and loaded as 3-channel RGB JPEG |
| **4** | Zero Exact Duplicates in Clean Dataset | **PASS** | Exactly 1,676 unique SHA-256 hashes (zero internal or cross-class duplicate files) |
| **5** | Provenance & Hash Re-Traceability to Source | **PASS** | 100% of copied files match their original source relative path and SHA-256 hash |
| **6** | Original Dataset Byte-Identical Preservation | **PASS** | 0 mutations across all 1,858 original files in `datasets/pigeonpea_disease_final` |
| **7** | Model Checkpoint Byte-Identical Preservation | **PASS** | Checkpoint SHA-256 `5baecdc3911502c4...` matches pre-build baseline |
| **8** | Zero Wilt Source-Family Leakage Across Splits | **PASS** | Train families: 20, Val families: 5, Test families: 5. Overlap: 0 |
| **9** | Wilt Evaluation Splits Contain Zero Augmentations | **PASS** | Exactly 0 augmentations in val or test. Val: 5 originals, Test: 5 originals |
| **10** | Strict Crop Isolation Verified | **PASS** | Exactly 0 files sourced from cotton, maize, soybean, rice, wheat, or validator v3 |

---

## 5. Statistical Limitation of the Wilt Evaluation Set

> [!IMPORTANT]
> The Wilt class evaluation set has been purged of all synthetic augmentations, leaving **5 held-out original field photographs in validation** and **5 held-out original field photographs in test**.
> 
> **Scientific Implication:**
> - Cross-split leakage has been reduced to zero (Hamming distance $\ge 12$ bits).
> - However, a test set of 5 images has wide binomial confidence intervals ($\pm 25\%$).
> - While this clean split prevents false accuracy claims, it is **strongly recommended to collect 50–100 new independent field photographs of wilted Tur plants** before asserting production-grade field generalization.

---

## 6. Remaining Manual-Review Cases

The 15 near-duplicate cross-class pairs (**27 images**) cataloged in `reports/pigeonpea_dataset_repair_plan/data/02_near_duplicate_review_manifest.csv` remain intact in the dataset:
- These images exhibit visual similarity across disease boundaries (e.g., subtle chlorosis in early Sterilic Mosaic vs nutrient deficiency or early Leaf Spot).
- Per the safety protocol, they have **not** been automatically relabeled or deleted, preserving ground truth for review by agricultural specialists.

---

## 7. Deliverables & Artifacts Generated

1. **Clean Candidate Dataset:**
   - Path: `datasets/pigeonpea_disease_clean_candidate_v1/`
   - Total Images: 1,676 (Train: 1,336, Val: 151, Test: 189)
2. **Build Manifest:**
   - Path: [reports/pigeonpea_clean_candidate_build/clean_candidate_v1_manifest.csv](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/reports/pigeonpea_clean_candidate_build/clean_candidate_v1_manifest.csv)
   - Tracks each copied image's `candidate_id`, destination path, source path, SHA-256 hash, family ID, and provenance.
3. **Build Metadata & Validation Results:**
   - Path: [reports/pigeonpea_clean_candidate_build/build_metadata.json](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/reports/pigeonpea_clean_candidate_build/build_metadata.json)
   - Path: [reports/pigeonpea_clean_candidate_build/validation_results.json](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/reports/pigeonpea_clean_candidate_build/validation_results.json)
4. **Execution Scripts:**
   - [scripts/audits/build_clean_pigeonpea_dataset.py](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/scripts/audits/build_clean_pigeonpea_dataset.py)
   - [scripts/audits/validate_clean_pigeonpea_dataset.py](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/scripts/audits/validate_clean_pigeonpea_dataset.py)

---

## 8. Status & Next Steps

- **Model Training:** **NOT STARTED.**
- **Production Checkpoint:** Unchanged.
- **Application Code & APIs:** Unchanged.

The clean candidate dataset is built, isolated, and verified. Awaiting your approval before proceeding to any experimental model training or evaluation.
