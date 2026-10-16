# TurSathi AI — Phase 2: Safe Dataset Repair Preparation Plan

**Date:** 2026-10-14  
**Author:** Senior Computer Vision & MLOps Dataset Auditor  
**Dataset Target:** `datasets/pigeonpea_disease_final`  
**Status:** Preparation Complete — Awaiting Approval Before Application  
**Original Dataset Integrity:** 100% Unchanged (1,858 / 1,858 Files Verified Byte-Identical)

---

## Executive Summary

Following the forensic audit, this document provides the formal preparation plan for repairing the five-class pigeonpea disease classification dataset. 

Every proposal in this plan adheres strictly to the **Mandatory Safety Rules**:
- **Zero In-Place Modifications:** No files have been deleted, moved, renamed, or modified in `datasets/pigeonpea_disease_final`.
- **Zero Retraining:** The active production checkpoint `models/best_pigeonpea_disease_final_efficientnet_b0.pth` remains untouched.
- **Strict Crop Isolation:** Pigeonpea data is isolated from all other crop datasets (cotton, maize, soybean, rice, wheat).
- **Class Mapping Preserved:** Class names and indices remain identical: `['Healthy', 'Leaf_Spot', 'Leaf_webber', 'Sterilic_mosaic', 'Wilt']`.
- **Evidence-Based:** All findings are backed by file SHA-256 hashes, perceptual hashes, and upstream provenance.

All manifests and the patch diff are preserved in [reports/pigeonpea_dataset_repair_plan/](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/reports/pigeonpea_dataset_repair_plan/).

---

## Phase A — Exact Duplicate Repair Plan

### Scope & Evidence
- **Total Duplicate Groups:** 55 groups involving **111 images**.
- **Nature of Conflicts:** 100% of these groups cross class boundaries.
  - **54 groups** are duplicate pairs between `Leaf_Spot` and `Sterilic_mosaic`.
  - **1 group** (Group 13) is an identical image labeled as `Leaf_Spot` (in train), `Sterilic_mosaic` (in train), and `Leaf_webber` (in test) (`SHA-256: 5691467c59fe...`).
- **Traceability:** Every single duplicate image was traced directly to `PPLD_extracted/PPLD_backup_before_duplicate_removal`, where duplicate filenames (e.g. `images (90).jpg` in Leaf_Spot vs `images(200).jpg` in Sterilic_mosaic) had been copied during previous batch preparation.

### Proposed Repair Strategy
1. **Zero Automatic Relabeling:** It is mathematically and scientifically unsound to assign a label based on majority vote or model predictions when ground truth is contradictory.
2. **Immediate Exclusion from Training Candidates:** All 111 conflicting images are marked `NEEDS_MANUAL_LABEL_REVIEW` and proposed for exclusion from the candidate training pool until an agricultural expert or plant pathologist verifies the true symptom.
3. **Artifact Generated:** [data/01_exact_duplicate_exclusion_manifest.csv](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/reports/pigeonpea_dataset_repair_plan/data/01_exact_duplicate_exclusion_manifest.csv) logs every conflicting image path, current split, assigned class, conflicting class, and upstream source filename.

---

## Phase B — Split Leakage Resolution & Wilt Source-Family Mapping

### 1. Wilt Source-Family Provenance
The 287 Wilt images in the current dataset were traced to **30 original field photographs** and **257 synthetic augmentations**.

To prevent cross-split leakage, every original and its augmentations are mapped to a canonical family identifier:
- **Family Range:** `WILT_FAM_00` to `WILT_FAM_29` (30 independent families).
- **Mapping Manifest:** [data/03_wilt_source_family_manifest.csv](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/reports/pigeonpea_dataset_repair_plan/data/03_wilt_source_family_manifest.csv) records every Wilt image, its assigned family, whether it is an original or augmentation, and its Hamming distance to the original photo.

### 2. Group-Aware Split Design
To resolve the catastrophic leakage where 51 of 58 test images were augmented copies of training images:
1. **Partitioning by Family:**
   - **Train Pool (20 Families):** `WILT_FAM_00` through `WILT_FAM_19` (20 original photos + all 186 of their augmentations = 206 images).
   - **Validation Pool (5 Families):** `WILT_FAM_20` through `WILT_FAM_24`. **Validation receives ONLY the 5 original, unaugmented field photos.** All synthetic derivatives of these 5 families are excluded from evaluation.
   - **Test Pool (5 Families):** `WILT_FAM_25` through `WILT_FAM_29`. **Test receives ONLY the 5 original, unaugmented field photos.** All synthetic derivatives of these 5 families are excluded from evaluation.
2. **Leakage Elimination:**
   - Cross-split Hamming distance between train and test Wilt images: $\ge 12$ bits.
   - **Zero synthetic augmentations are permitted in validation or test.**

### 3. Statistical Limitation & Risk Disclosure
> [!WARNING]
> Having only **5 independent test photos** for Wilt is a severe statistical limitation. While it guarantees zero data leakage, 5 images cannot provide high-confidence validation of real-world generalization across varying field lighting, soil conditions, and plant varieties. It is strongly recommended to collect at least 50–100 additional independent field photographs of Wilted Tur plants before production re-deployment.

---

## Phase C — Near-Duplicate Cross-Class Review

Using perceptual hashes (`pHash` and `dHash`), 15 distinct pairs (**27 images**) were detected with $\text{pHash distance} \le 4$ across conflicting classes:
- **Example 1:** `healthy_train_0139.jpg` (Healthy) vs `sterilic_mosaic_val_0024.jpg` (Sterilic_mosaic) ($\text{pHash}=4, \text{dHash}=8$).
- **Example 2:** `leaf_spot_train_0029.jpg` (Leaf_Spot) vs `sterilic_mosaic_train_0116.jpg` (Sterilic_mosaic) ($\text{pHash}=0, \text{dHash}=2$).
- **Example 3:** `sterilic_mosaic_train_0020.jpg` (Sterilic_mosaic) vs `leaf_spot_val_0070.jpg` (Leaf_Spot) ($\text{pHash}=0, \text{dHash}=0$).

### Review Policy
- All 27 images are cataloged in [data/02_near_duplicate_review_manifest.csv](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/reports/pigeonpea_dataset_repair_plan/data/02_near_duplicate_review_manifest.csv).
- Status assigned: `NEEDS_MANUAL_REVIEW`.
- None are automatically relabeled or deleted.

---

## Phase D — Dataset Preparation Script Patch

A minimal proposed patch for [scripts/prepare_balanced_dataset.py](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/scripts/prepare_balanced_dataset.py) has been prepared and saved to [reports/pigeonpea_dataset_repair_plan/patch_prepare_balanced_dataset.diff](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/reports/pigeonpea_dataset_repair_plan/patch_prepare_balanced_dataset.diff).

### Key Architectural Fixes in the Proposed Patch:
1. **Exclude Dirty Upstream Sources:** Removes all references to `PPLD_backup_before_duplicate_removal`.
2. **Explicit Wilt Source Pool:** Explicitly points to `datasets/_temp_wilt_staging` rather than relying on stale output staging.
3. **Global Cross-Class Deduplication:** Runs SHA-256 deduplication across the entire combined pool *before* class assignment and splitting.
4. **Group-Aware Splitting:** Enforces source-family grouping for Wilt and prevents augmentations from leaking into `val` and `test`.

*The patch has NOT been applied to `scripts/prepare_balanced_dataset.py` and awaits user approval.*

---

## Phase E — Clean Candidate Pool Summary & Reconciliation

### Independent Clean Original Photos vs Augmentations

| Class | Original Dataset | Excluded Duplicates | Clean Originals | Offline Augmentations | Proposed Clean Pool |
|---|:---:|:---:|:---:|:---:|:---:|
| **Healthy** | 359 | 0 | 195 | 164 | **359** |
| **Leaf_Spot** | 439 | 54 | 282 | 103 | **385** |
| **Leaf_webber** | 346 | 2 | 146 | 198 | **344** |
| **Sterilic_mosaic** | 427 | 55 | 237 | 135 | **372** |
| **Wilt** | 287 | 0 (71 eval augs held out) | 30 | 186 (train only) | **216** |
| **Total** | **1,858** | **111** | **890** | **786** | **1,676** |

### Proposed Group-Aware Split Distribution

| Class | Train | Val (Held-out Originals) | Test (Held-out Originals) | Total Clean |
|---|:---:|:---:|:---:|:---:|
| **Healthy** | 285 | 28 | 46 | **359** |
| **Leaf_Spot** | 278 | 53 | 54 | **385** |
| **Leaf_webber** | 285 | 27 | 32 | **344** |
| **Sterilic_mosaic** | 282 | 38 | 52 | **372** |
| **Wilt** | 206 (20 families) | 5 (5 held-out originals) | 5 (5 held-out originals) | **216** |
| **Total** | **1,336** | **151** | **189** | **1,676** |

*Note: In this proposed split, all validation and test images are verified unique original field/leaf photos with zero augmentation leakage.*

---

## Deliverables & Integrity Verification

1. **Manifests Saved in `reports/pigeonpea_dataset_repair_plan/data/`:**
   - `01_exact_duplicate_exclusion_manifest.csv` (111 records)
   - `02_near_duplicate_review_manifest.csv` (15 pairs / 27 images)
   - `03_wilt_source_family_manifest.csv` (287 records with family assignments)
   - `04_proposed_group_aware_split_manifest.csv` (1,858 records with proposed split mapping)
   - `summary_repair_metrics.json`
   - `patch_prepare_balanced_dataset.diff`

2. **Original Dataset Integrity Check:**
   Every single file in `datasets/pigeonpea_disease_final` was verified against the pre-audit SHA-256 manifest.
   **Result:** `1,858 / 1,858 files MATCHED. 0 files modified.`

---
*Preparation complete. All artifacts are stored safely in reports/. Awaiting your instruction before executing any file operations or updating dataset scripts.*
