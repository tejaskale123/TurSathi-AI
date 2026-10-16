# TurSathi AI — Phase 5D-B2: Field Dataset Collection Tracker and Verification Audit Report

**Audit Date:** 2026-10-14  
**Project:** TurSathi AI / AgriMind AI  
**Scope:** Automated, non-destructive tracking utility and verification suite for pigeonpea field dataset collection.  
**Audited Artifacts:**
- [`reports/pigeonpea_organ_validator_design/PHASE5D_A_DESIGN_REPORT.md`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/reports/pigeonpea_organ_validator_design/PHASE5D_A_DESIGN_REPORT.md)
- [`reports/pigeonpea_organ_dataset_collection/FIELD_COLLECTION_PREPARATION.md`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/reports/pigeonpea_organ_dataset_collection/FIELD_COLLECTION_PREPARATION.md)
- [`reports/pigeonpea_organ_dataset_collection/field_metadata_template.csv`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/reports/pigeonpea_organ_dataset_collection/field_metadata_template.csv)

---

## Executive Summary

Phase 5D-A and Phase 5D-B established the architectural design and operational collection protocols for the upcoming pigeonpea organ validator (`Tur_Pod` and `Tur_WholePlant_or_Canopy`). A critical risk identified in historical audits was the manual tracking of dataset ingestion, which previously allowed 51 synthetic augmented duplicates of only 30 plants to contaminate the Wilt test split (documented in Stage F28).

In Phase 5D-B2, we built and verified an automated, read-only validation tracker utility:
[`scripts/audits/validate_pigeonpea_field_collection.py`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/scripts/audits/validate_pigeonpea_field_collection.py)

This utility programmatically verifies incoming field collection manifests against all schema constraints, enforces isolation of quarantined records, verifies image file integrity and cryptographic SHA-256 deduplication, prevents cross-split plant and farm leakage, and checks progress against mandatory targets without fabricating collection numbers.

**Zero code, production/experimental models, training datasets, database records, API routes, or mobile screens were modified.**

---

## 1. Newly Implemented Validation Utility

**Location:** [`scripts/audits/validate_pigeonpea_field_collection.py`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/scripts/audits/validate_pigeonpea_field_collection.py)

### Core Safeguards Enforced:
1. **Strict Metadata Schema:**
   - Enforces required columns: `filename`, `class_label`, `plant_id`, `farm_id`, `capture_date`, `verification_status`, `verifier_reference`.
   - Rejects null or blank entries in mandatory fields.
2. **Category and Status Validation:**
   - Allowed class labels: `{"Tur_Pod", "Tur_WholePlant_or_Canopy", "Tur_Leaf", "Not_Tur_or_Unsupported"}`.
   - Allowed verification statuses: `{"verified", "quarantined", "rejected"}`.
3. **Quarantine Isolation:**
   - Quarantined and rejected records are strictly excluded from verified progress counts.
   - Any unresolved quarantined record automatically triggers an active blocker preventing dataset readiness approval.
4. **Image File Existence & Decode Verification:**
   - When an image directory is provided, verifies physical file existence and valid image structure via PIL `verify()`.
   - Flags files with dimensions $< 224 \times 224$ pixels.
5. **Cryptographic Deduplication (SHA-256):**
   - Hashes all image files and flags identical files, even if uploaded under different filenames.
6. **Split Leakage Prevention (Plant & Farm Level):**
   - If dataset split designations (`split` column) are provided, verifies that no `plant_id` or `farm_id` appears across multiple partitions (e.g. train vs test).
7. **Readiness Target Evaluation:**
   - `Tur_Pod`: Target $\ge 250$ verified images.
   - `Tur_WholePlant_or_Canopy`: Target $\ge 200$ verified images.
   - `Not_Tur_or_Unsupported`: Target $\ge 100$ verified distractor images.
   - `Distinct_Farms`: Target $\ge 5$ distinct geographic farm plots.
   - Readiness status is approved (`is_dataset_ready = True`) **only** when all numerical targets are met, zero leakage is detected, zero critical errors exist, and zero quarantined records remain unreviewed.

---

## 2. Focused Regression Test Suite

**Location:** [`tests/test_pigeonpea_field_collection_validator.py`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/tests/test_pigeonpea_field_collection_validator.py)

The test suite exercises the auditor using temporary synthetic test fixtures in isolated scratch directories, guaranteeing zero pollution of project datasets:

| Test Case | Description | Expected Result | Actual Result |
| :--- | :--- | :--- | :---: |
| `test_01_empty_manifest_reports_zero_progress` | Empty manifest with header only | Reports 0 records, HOLD status, explicit zero-collection blocker | **PASS** |
| `test_02_template_comments_ignored_cleanly` | Manifest containing `#` comments / examples | Ignores comment lines cleanly without error | **PASS** |
| `test_03_missing_required_columns_flagged` | Manifest missing mandatory schema headers | Flags `MISSING_COLUMNS` error issue | **PASS** |
| `test_04_quarantined_records_excluded` | Mixed manifest with verified, quarantined, and rejected rows | Quarantined/rejected excluded from verified count; triggers quarantine blocker | **PASS** |
| `test_05_duplicate_sha256_hashes_flagged` | Identical image binary copied to different filenames | Detects collision, flags `EXACT_DUPLICATE_HASH` error | **PASS** |
| `test_06_plant_level_split_leakage_detected` | Same `plant_id` assigned to both `train` and `test` | Flags `PLANT_SPLIT_LEAKAGE` error and blocks readiness | **PASS** |
| `test_07_insufficient_targets_enforce_hold` | 10 verified pod images (below 250 target) | Calculates deficit (-240), maintains `is_dataset_ready=False` | **PASS** |

**Execution Result:**
```
Ran 7 tests in 0.228s
OK
```

---

## 3. Baseline Dry-Run Against Field Collection Template

We executed the newly created utility against the official repository template ([`field_metadata_template.csv`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/reports/pigeonpea_organ_dataset_collection/field_metadata_template.csv)):

```bash
python scripts/audits/validate_pigeonpea_field_collection.py --manifest reports/pigeonpea_organ_dataset_collection/field_metadata_template.csv
```

### Actual Output:
```
======================================================================
TUR SATHI AI — FIELD DATASET COLLECTION AUDIT REPORT
======================================================================
Total Collection Records:     0
Verified Records:             0
Quarantined Records:          0
Rejected Records:             0
Distinct Farms:               0 -> []
Distinct Plants:              0
----------------------------------------------------------------------
PROGRESS VS TARGET THRESHOLDS:
  Tur_Pod                   :    0 /  250  [DEFICIT (-250)]
  Tur_WholePlant_or_Canopy  :    0 /  200  [DEFICIT (-200)]
  Not_Tur_or_Unsupported    :    0 /  100  [DEFICIT (-100)]
  Distinct_Farms            :    0 /    5  [DEFICIT (-5)]
----------------------------------------------------------------------
DATASET READY FOR TRAINING:   NO [HOLD]

ACTIVE BLOCKERS:
  * Manifest contains zero collection records (Collection has not started).
  * Tur_Pod deficit: 0/250 verified images.
  * Tur_WholePlant_or_Canopy deficit: 0/200 verified images.
  * Not_Tur_or_Unsupported deficit: 0/100 verified images.
  * Distinct farm deficit: 0/5 distinct farms.
======================================================================
```

**Confirmation:** The tracker accurately reflects that real field collection has not yet begun, without inventing progress or falsifying readiness.

---

## 4. Preservation & System Integrity Verification

We confirm that all preservation constraints remain strictly intact:

1. **Production Model Checkpoint:** [`models/best_pigeonpea_disease_final_efficientnet_b0.pth`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/models/best_pigeonpea_disease_final_efficientnet_b0.pth)
   * SHA-256: `5baecdc3911502c4cb345101c6f2fd84824eb4cb025e300d66e00231a4834b99` (**Untouched**)
2. **Experimental Model Checkpoint:** [`models/experimental/pigeonpea_clean_candidate_v1/best_pigeonpea_clean_candidate_v1_efficientnet_b0.pth`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/models/experimental/pigeonpea_clean_candidate_v1/best_pigeonpea_clean_candidate_v1_efficientnet_b0.pth)
   * SHA-256: `28d1578ae88e86ef49e8389e20c57b1ba18288aee19815e54e75f5530dc91ff7` (**Untouched**)
3. **Training & Holdout Datasets:**
   * `datasets/pigeonpea_disease_final/`: 1,858 files (**Untouched**)
   * `datasets/pigeonpea_disease_clean_candidate_v1/`: 1,676 files (**Untouched**)
   * `datasets/new_disease_images/`: 41 images (**Untouched**)
4. **Application Code & Existing Changes:**
   * Working tree edits in [`backend/app/api/v1/predictions.py`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/backend/app/api/v1/predictions.py) remain preserved.
   * Zero Git staging, commits, resets, stashes, or cleans were executed.
   * No backend APIs, database records, frontend pages, or mobile screens were modified.

---

## 5. Summary of Files Created in Phase 5D-B2

1. [`scripts/audits/validate_pigeonpea_field_collection.py`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/scripts/audits/validate_pigeonpea_field_collection.py): The read-only field collection validation utility.
2. [`tests/test_pigeonpea_field_collection_validator.py`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/tests/test_pigeonpea_field_collection_validator.py): 7 unit tests covering schema, quarantine isolation, duplicate hash detection, and split leakage.
3. [`reports/pigeonpea_organ_dataset_collection/PHASE5D_B2_TRACKER_REPORT.md`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/reports/pigeonpea_organ_dataset_collection/PHASE5D_B2_TRACKER_REPORT.md): This verification report.
