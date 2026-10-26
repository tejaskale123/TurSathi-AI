# TurSathi AI — Hard-Negative Data Collection & Validation Workflow

**Document ID:** `SOP-V4-HARD-NEGATIVE-01`  
**Location:** `ml/retraining/validator_v4/HARD_NEGATIVE_COLLECTION_WORKFLOW.md`  
**Scope:** Standard operating procedure for staging, reviewing, labeling, and validating hard-negative imagery for Validator v4.  

---

## 1. Botanical Label Policy & Organ Suitability

To eliminate the "Wilt sinkhole" and prevent data contamination, field collectors and reviewing agronomists must adhere to the following labeling matrix:

| Real-World Image Category | Visual Description | Correct `organ_category` | Correct `verified_label` | Pipeline Action | Model Training Eligibility |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Valid Pigeonpea Leaf** | Close-up green leaflet or leaf cluster, healthy or with supported disease. | `tur_leaf` | `Tur` | Passes Stage 2 (Validator) to Stage 3 (Disease Classifier). | Eligible for `Tur` positive training split. |
| **Pigeonpea Non-Leaf Organ** | Seed pods, woody stalks, roots, flowers, or whole shrubs without clear leaf focal point. | `pigeonpea_pod` or `pigeonpea_stem_root` | `Tur_Non_Leaf_Organ` | **Rejected at Stage 2** with guidance: *"Pigeonpea pod/stalk detected. Please photograph a leaf."* | **NEVER label as `Not_Tur`**. Held out for organ-gate evaluation only. |
| **Agricultural Weed** | Wild weeds (Parthenium, Commelina, Celosia, Amaranthus) in pigeonpea fields. | `weed_foliage` | `Not_Tur` | **Rejected at Stage 2** with guidance: *"Non-pigeonpea plant detected."* | **Eligible for `Not_Tur` training split.** |
| **Non-Pigeonpea Crop** | Intercrop leaves (Cotton, Soybean, Maize, Green Gram, Cowpea). | `other_crop_leaf` | `Not_Tur` | **Rejected at Stage 2** with guidance: *"Non-pigeonpea crop detected."* | **Eligible for `Not_Tur` training split.** |
| **Field Clutter & Soil** | Farmer hands holding leaves, black soil, footwear, irrigation pipe, fertilizer bag. | `non_crop_clutter` | `Not_Tur` | **Rejected at Stage 2** with guidance: *"Non-crop background detected."* | **Eligible for `Not_Tur` training split.** |
| **Genuine Tur Unsupported Disease** | Authentic pigeonpea leaf with Alternaria blight, Phytophthora stem blight, or powdery mildew. | `unsupported_pigeonpea_disease` | `Tur_Unsupported_Disease` | **Passes Stage 2** as Tur Leaf; **Rejected at Stage 4** (OOD distance $> 0.40$) as unsupported condition. | **NEVER label as `Not_Tur`**. Held out for OOD gate testing only. |

> [!CAUTION]
> **Crop Identity vs. Leaf Suitability:** An authentic pigeonpea leaf suffering from Alternaria blight *is* pigeonpea tissue. Labeling it `Not_Tur` injects contradictory training signals and degrades model accuracy on real crops. It must be marked `Tur_Unsupported_Disease` and handled by the OOD distance guard.

---

## 2. Directory Structure & Intake Staging

Collected field photos must be copied into isolated staging directories under `ml/retraining/validator_v4/incoming_hard_negatives/`:

```
ml/retraining/validator_v4/
├── incoming_hard_negatives/
│   ├── agricultural_weeds/              <-- Photos of field weeds
│   ├── field_clutter_and_soil/          <-- Photos of soil, hands, boots, tools
│   ├── pigeonpea_non_leaf_organs/       <-- Photos of pods, bare stems, roots
│   ├── unsupported_pigeonpea_diseases/  <-- Photos of Alternaria blight, Phytophthora
│   └── valid_pigeonpea_leaves_audit/    <-- Control photos of genuine leaves
├── hard_negative_intake_template.csv     <-- Human review spreadsheet template
├── process_hard_negative_intake.py      <-- Automated validator and hash auditor
├── hard_negative_schema.py              <-- Pydantic / Dataclass constraint engine
└── validate_hard_negatives.py           <-- Comprehensive manifest audit tool
```

---

## 3. PowerShell Guide for Staging & Automated Collection

You can either automatically harvest approved licensed imagery or manually stage field photos:

### Option A: Fully Automated Licensed Collection (Recommended for Quick Staging)
To automatically download and stage 21 approved, open-licensed hard-negative images (with verified CC-BY / CC-BY-SA / Public Domain licenses and zero collision with baseline data):
```powershell
# 1. Harvest approved licensed images and auto-generate intake CSV:
python ml/retraining/validator_v4/prepare_hard_negatives.py

# 2. Process intake CSV and generate the candidate manifest:
python ml/retraining/validator_v4/process_hard_negative_intake.py

# 3. Validate candidate manifest integrity and shortage status:
python ml/retraining/validator_v4/validate_hard_negatives.py --manifest ml/retraining/validator_v4/candidate_hard_negatives_manifest.json
```

### Option B: Manual Photo Staging Procedure
If staging your own original field photos:

#### Step 1: Copy incoming photos to the staging directory
```powershell
# Copy weed photos from your mobile download or camera folder:
Copy-Item "C:\Path\To\WeedPhotos\*.jpg" -Destination "ml\retraining\validator_v4\incoming_hard_negatives\agricultural_weeds\"

# Copy pigeonpea pod photos:
Copy-Item "C:\Path\To\PodPhotos\*.jpg" -Destination "ml\retraining\validator_v4\incoming_hard_negatives\pigeonpea_non_leaf_organs\"

# Copy soil / clutter photos:
Copy-Item "C:\Path\To\SoilPhotos\*.jpg" -Destination "ml\retraining\validator_v4\incoming_hard_negatives\field_clutter_and_soil\"
```

#### Step 2: Catalog entries in the intake spreadsheet
Open [`hard_negative_intake_template.csv`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/ml/retraining/validator_v4/hard_negative_intake_template.csv) and add rows corresponding to your staged photos:
```csv
image_id,relative_file_path,source_provenance,verified_label,organ_category,reviewer_status,reviewer_notes,duplicate_group_id,split_assignment
HN_NEW_001,ml/retraining/validator_v4/incoming_hard_negatives/agricultural_weeds/parthenium_01.jpg,Wardha_Survey_2026,Not_Tur,weed_foliage,PENDING_REVIEW,Parthenium weed leaf,,unassigned
HN_NEW_002,ml/retraining/validator_v4/incoming_hard_negatives/field_clutter_and_soil/soil_footwear_01.jpg,Amravati_Field_2026,Not_Tur,non_crop_clutter,PENDING_REVIEW,Black soil background,,unassigned
```

#### Step 3: Run the automated intake processor in dry-run mode
```powershell
python ml/retraining/validator_v4/process_hard_negative_intake.py --dry-run
```

#### Step 4: Validate and generate the candidate manifest
```powershell
python ml/retraining/validator_v4/process_hard_negative_intake.py
```

#### Step 5: Execute comprehensive manifest integrity validation
```powershell
python ml/retraining/validator_v4/validate_hard_negatives.py
```

---

## 4. Manifest Analysis: Training Eligibility vs. Holdout Separation

Inspecting [`hard_negative_collection_manifest.json`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/ml/retraining/validator_v4/hard_negative_collection_manifest.json) reveals the following eligibility accounting:

### Current Manifest Accounting (50 Cataloged Images):
1. **Eligible for Training Splits (`train` / `val`):** **0 images.**  
   No hard negatives have been added to the active training splits yet.
2. **Held Out for Final Test (`test_holdout`):** **10 images.**  
   - `HN_RW_001` through `HN_RW_009` (9 non-tur crop foliage images from the frozen holdout).
   - `HN_EXP_001` (`488313...Fig1_HTML.jpg` academic figure).
3. **Held Out for OOD Diagnostic Evaluation (`unassigned`):** **2 images.**  
   - `HN_EXP_003` (Alternaria blight: genuine pigeonpea disease outside 5 classes).
   - `HN_EXP_041` (Kenyan pigeonpea pod cluster: genuine pigeonpea non-leaf organ).
4. **Pending Human Review (`unassigned`):** **38 images.**  
   - Uncurated Google Image downloads (containing 5 duplicate pairs). These cannot be trained on until an agronomist confirms their labels.

---

## 5. Stop / Go Checklist for Training Readiness

Before initiating Google Colab training for Validator v4, all conditions below must be satisfied:

| Checkpoint | Condition | Current Status | Decision |
| :--- | :--- | :---: | :---: |
| **1. Zero Leakage Invariant** | Baseline `validator_v4_manifest.json` has 0 cross-split hash collisions. | **PASSED** (3,301 unique hashes) | **GO** |
| **2. Production Immutability** | `git diff --stat` is completely empty (zero production files modified). | **PASSED** | **GO** |
| **3. Automated Safety Tests** | `tests/test_candidate_and_validator_safety.py` passes all 5 tests. | **PASSED** | **GO** |
| **4. Verified Weed Negatives** | Minimum 50 verified agricultural weed photos cataloged in `train`/`val`. | **0 / 50 cataloged** | **STOP** |
| **5. Verified Pod / Clutter Negatives** | Minimum 50 non-leaf organ & clutter photos cataloged in `train`/`val`. | **0 / 50 cataloged** | **STOP** |
| **6. Zero Unreviewed Images** | No image with `reviewer_status == "PENDING_REVIEW"` is assigned to `train` or `val`. | **PASSED** | **GO** |
| **7. Final Decision** | **Proceed to Google Colab training?** | **BLOCKED ON DATA COLLECTION** | **STOP** |

---

## 6. Exact Next Action

1. Place real field photographs of weeds, soil, and pigeonpea pods into `ml/retraining/validator_v4/incoming_hard_negatives/`.
2. Add records to `ml/retraining/validator_v4/hard_negative_intake_template.csv`.
3. Run `python ml/retraining/validator_v4/process_hard_negative_intake.py` to compile the candidate staging manifest.
4. Verify with `python ml/retraining/validator_v4/validate_hard_negatives.py`.
