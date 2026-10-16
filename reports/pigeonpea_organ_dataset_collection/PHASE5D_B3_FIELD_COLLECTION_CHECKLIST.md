# TurSathi AI — Phase 5D-B3: Real Field Dataset Collection Checklist

**Document Version:** 1.0  
**Date:** 2026-10-14  
**Project:** TurSathi AI / AgriMind AI  
**Scope:** Actionable, step-by-step field execution checklist for authentic pigeonpea organ dataset collection (`Tur_Pod` and `Tur_WholePlant_or_Canopy`).  
**Prerequisite Audits & Tools:**
- Design Report: [`reports/pigeonpea_organ_validator_design/PHASE5D_A_DESIGN_REPORT.md`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/reports/pigeonpea_organ_validator_design/PHASE5D_A_DESIGN_REPORT.md)
- Operational Plan: [`reports/pigeonpea_organ_dataset_collection/FIELD_COLLECTION_PREPARATION.md`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/reports/pigeonpea_organ_dataset_collection/FIELD_COLLECTION_PREPARATION.md)
- Manifest Template: [`reports/pigeonpea_organ_dataset_collection/field_metadata_template.csv`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/reports/pigeonpea_organ_dataset_collection/field_metadata_template.csv)
- Verification Tracker: [`scripts/audits/validate_pigeonpea_field_collection.py`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/scripts/audits/validate_pigeonpea_field_collection.py)
- Tracker Audit: [`reports/pigeonpea_organ_dataset_collection/PHASE5D_B2_TRACKER_REPORT.md`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/reports/pigeonpea_organ_dataset_collection/PHASE5D_B2_TRACKER_REPORT.md)

---

## 1. Ground-Truth Baseline Status

> [!IMPORTANT]
> ### Authentic Progress Status: ZERO (0) Collected Images
> As verified in Phase 5D-B2, **exactly zero authentic field images have been collected or verified** for the organ validator. Physical farm photography has not yet commenced.
> 
> * **`Tur_Pod`:** 0 / 250 verified images (DEFICIT: -250)
> * **`Tur_WholePlant_or_Canopy`:** 0 / 200 verified images (DEFICIT: -200)
> * **`Not_Tur_or_Unsupported` (Distractors):** 0 / 100 verified images (DEFICIT: -100)
> * **Qualifying Geographic Farms:** 0 / 5 distinct farm plots (DEFICIT: -5)
> 
> Fabricating images, metadata rows, verification sign-offs, or artificial progress is strictly prohibited. The dataset remains on **HOLD** until physical farm visits produce verified field evidence.

---

## 2. Quantitative Targets & Distribution Constraints

Collection must strictly fulfill the following empirical thresholds before any model training can be authorized:

| Target Category | Verified Target | Visual Criteria | Required Morphological Diversity | Minimum Geographic Distribution |
| :--- | :---: | :--- | :--- | :--- |
| **`Tur_Pod`** | **$\ge 250$ verified** | Pods/flowers occupy $\ge 30\%$ foreground or form primary camera focus. Distance: $15\text{ cm} - 35\text{ cm}$. | Green immature pods, mottled/striated pods, mature brown pods, borer/pest-damaged pods, floral clusters. | Across $\ge 5$ distinct farms ($\ge 10$ shrubs per farm). |
| **`Tur_WholePlant_or_Canopy`** | **$\ge 200$ verified** | Whole shrub or canopy view from $> 1.0\text{ m}$ distance. Individual leaves occupy $< 15\%$ area. | Vegetative branching, peak flowering canopy, mature fruiting shrub, naturally drying/senescing bushes. | Across $\ge 5$ distinct farms ($\ge 10$ shrubs per farm). |
| **`Not_Tur_or_Unsupported`** | **$\ge 100$ verified** | Agricultural negative distractors common in pigeonpea belts. | Intercropped crops (cotton, soybean, sorghum), field weeds (parthenium), bare soil, farm tools. | Across $\ge 5$ distinct farms. |
| **Distinct Farm Plots** | **$\ge 5$ farms** | Geographically separated agricultural plots. | Minimum $5\text{ km}$ distance between plots; multiple local cultivars (e.g., BDN-711, BSMR-736). | 5+ distinct GPS coordinates (anonymized). |

---

## 3. Step-by-Step Field Execution Checklist

### Phase 1: Pre-Field Logistics & Farm Coordination
- [ ] **Farm Selection:** Identify at least 5 qualifying pigeonpea farm plots separated by at least $5\text{ km}$ (e.g., across Marathwada/Vidarbha or regional pigeonpea belts).
- [ ] **Cultivar Documentation:** Note down the predominant cultivar per plot (e.g., BDN-2, BDN-711, BSMR-736, PKV-Tara).
- [ ] **Agronomist Engagement:** Secure participation of a qualified agronomist or agricultural extension officer for on-site or post-capture validation.
- [ ] **Camera Setup:** Configure smartphones to shoot at native resolution ($\ge 1280 \times 720$, ideally $1920 \times 1080$ or higher). Turn off aggressive beauty filters, AI distortion, or digital zoom.
- [ ] **Template Preparation:** Copy [`field_metadata_template.csv`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/reports/pigeonpea_organ_dataset_collection/field_metadata_template.csv) to a working field sheet.

### Phase 2: On-Farm Photography Protocol
- [ ] **Consent & Privacy:** Obtain verbal or written permission from the plot owner. **Do not capture farmer faces, clothing, bystanders, children, vehicle license plates, or homesteads.**
- [ ] **Natural Daylight Capture:** Photograph between 8:30 AM and 4:30 PM under natural ambient light. Avoid harsh lens flare directly facing the sun, and avoid casting operator shadows over the subject.
- [ ] **Focus & Sharpness:** Tap smartphone screen to lock focus directly on the target organ. Reject and re-take immediately if hand jitter or motion blur occurs.
- [ ] **No Artificial Burst Duplicates:** Do not take multiple identical bursts of the exact same organ from the same angle. Walk around the plant to capture distinct orientations and varying lighting angles.
- [ ] **Framing by Category:**
  - [ ] **`Tur_Pod`:** Center on pod clusters at $15\text{ cm} - 35\text{ cm}$ distance. Ensure pods dominate $\ge 30\%$ of the image area.
  - [ ] **`Tur_WholePlant_or_Canopy`:** Stand back $1.0\text{ m} - 2.5\text{ meters}$. Capture the full plant architecture from soil to canopy, or the lateral canopy spread.
  - [ ] **`Not_Tur_or_Unsupported`:** Capture common field weeds, companion intercrops (cotton, soybean), soil crust, and farm implements.

### Phase 3: Field Metadata Logging
- [ ] **Unique Filename Standard:** Name files systematically: `[farm_id]_[class]_[seq].jpg` (e.g., `FARM01_POD_001.jpg`).
- [ ] **Plant Tracking:** Assign each physical shrub a unique identifier: `F{farm}_P{seq}` (e.g., `F01_P001`). Note multiple organ photos taken from the same shrub with the same `plant_id`.
- [ ] **Real-Time Row Logging:** Record each capture in the metadata CSV with:
  - `filename`
  - `class_label`
  - `plant_id`
  - `farm_id`
  - `capture_date` (`YYYY-MM-DD`)
  - `growth_stage` (e.g., `flowering`, `pod_filling`, `maturity`)
  - `camera_device` (e.g., `Redmi_Note_11`, `Galaxy_M32`)
  - `lighting_condition` (e.g., `bright_sun`, `overcast`, `diffuse`)

### Phase 4: Agronomist Review & Verification
- [ ] **Independent Examination:** The agronomist independently inspects each photo on a calibrated monitor or high-resolution tablet.
- [ ] **Verification Criteria:**
  - Confirm the species is genuinely pigeonpea (*Cajanus cajan*).
  - Confirm the image framing unambiguously satisfies the organ definition (`Tur_Pod` vs `Tur_WholePlant_or_Canopy`).
  - Confirm absence of motion blur, lens flare, or extreme underexposure.
- [ ] **Sign-Off:** For passing images, mark `verification_status = "verified"` and record the agronomist's credential in `verifier_reference` (e.g., `Dr. A. Sharma (Agronomist #AG-104)`).

### Phase 5: Quarantine Management
- [ ] **Ambiguity Isolation:** If an image has mixed pod/leaf dominance or ambiguous distance, mark `verification_status = "quarantined"`.
- [ ] **Physical Segregation:** Move quarantined images to a designated `quarantine/` folder away from dataset staging.
- [ ] **No Automated Re-labeling:** Do not reclassify quarantined images using AI predictions or scripts. Retain in quarantine until a senior panel can review, or discard.
- [ ] **Discard Corrupt/Unusable:** Mark unresolvable or severely blurred images as `verification_status = "rejected"`.

### Phase 6: Privacy Scrubbing & Leakage Defense
- [ ] **EXIF Location Sanitization:** Truncate or strip exact household GPS coordinates. Retain only anonymized plot codes (`FARM_MAH_01`) in published manifests.
- [ ] **Visual Privacy Check:** Inspect all photos for accidental human hands, feet, jewelry, or personal tools before moving to ingestion.
- [ ] **Cryptographic Hash Check:** Compute SHA-256 hashes of all verified images to guarantee zero exact duplicates.
- [ ] **Group-Level Partitioning:** Ensure all images sharing a given `plant_id` and `farm_id` are grouped into the **same split** (train, val, or test). Under no circumstances may photos of the same plant appear across multiple splits.

---

## 4. Verification Commands for Validating Collection Manifests

Once a real field manifest and image directory have been assembled, execute the following audit commands to programmatically evaluate dataset readiness:

### A. Syntax & Manifest Schema Dry-Run
Validates columns, categories, missing values, and progress counts without needing image binaries:
```bash
python scripts/audits/validate_pigeonpea_field_collection.py --manifest path/to/real_field_manifest.csv
```

### B. Full Image Existence, Decode, and SHA-256 Deduplication Audit
Checks physical files, PIL decodability, resolution floors ($\ge 224\times 224$), duplicate hashes, and cross-split plant leakage:
```bash
python scripts/audits/validate_pigeonpea_field_collection.py \
  --manifest path/to/real_field_manifest.csv \
  --image-dir path/to/real_field_images/
```

### C. Automated Audit Logging to JSON
Saves a complete machine-readable audit report including all issue flags and blocker summaries:
```bash
python scripts/audits/validate_pigeonpea_field_collection.py \
  --manifest path/to/real_field_manifest.csv \
  --image-dir path/to/real_field_images/ \
  --json-out reports/pigeonpea_organ_dataset_collection/field_collection_audit_run.json
```

---

## 5. Dataset Approval Criteria (Go / No-Go Gate)

Before any developer may proceed to model architecture design or training, the automated validation utility must output:
```
DATASET READY FOR TRAINING: YES [APPROVED]
```

This state is achieved **only** when all of the following conditions are simultaneously met:
1. `Tur_Pod` verified images $\ge 250$.
2. `Tur_WholePlant_or_Canopy` verified images $\ge 200$.
3. `Not_Tur_or_Unsupported` verified distractor images $\ge 100$.
4. Geographically distinct farms $\ge 5$.
5. Zero unresolved quarantined images in the active pool (`quarantined_records == 0`).
6. Zero exact duplicate SHA-256 hashes.
7. Zero cross-split plant or farm leakage.
8. Zero unhandled CSV parse or schema errors.

---

## 6. Immediate Next Real-World Action Required

> [!TIP]
> ### First Real-World Action Required from the Project Owner:
> **Identify and schedule farm visits to at least five distinct pigeonpea plots with a participating agronomist.**
> 
> Technical software and automated verification tools are fully deployed in the repository. The next phase cannot progress through software alone; it requires authentic physical photography across real Maharashtra/regional pigeonpea farms during the current flowering/pod-maturation season.

---

## 7. System Preservation Verification

We confirm that during the preparation of this checklist:
1. **Production Model Checkpoint:** [`models/best_pigeonpea_disease_final_efficientnet_b0.pth`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/models/best_pigeonpea_disease_final_efficientnet_b0.pth) (SHA-256: `5baecdc3911502c4cb345101c6f2fd84824eb4cb025e300d66e00231a4834b99`) was **not modified**.
2. **Experimental Model Checkpoint:** [`models/experimental/pigeonpea_clean_candidate_v1/best_pigeonpea_clean_candidate_v1_efficientnet_b0.pth`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/models/experimental/pigeonpea_clean_candidate_v1/best_pigeonpea_clean_candidate_v1_efficientnet_b0.pth) (SHA-256: `28d1578ae88e86ef49e8389e20c57b1ba18288aee19815e54e75f5530dc91ff7`) was **not modified**.
3. **Datasets:** `datasets/pigeonpea_disease_final/` (1,858 files), `datasets/pigeonpea_disease_clean_candidate_v1/` (1,676 files), and `datasets/new_disease_images/` (41 images) were **not modified**.
4. **Existing Reports & Templates:** `FIELD_COLLECTION_PREPARATION.md`, `PHASE5D_B2_TRACKER_REPORT.md`, and `field_metadata_template.csv` were **preserved untouched**.
5. **Application Code & Git State:** Working tree edits in [`backend/app/api/v1/predictions.py`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/backend/app/api/v1/predictions.py) remain preserved. No Git commits, stashes, resets, or staging operations were executed.
