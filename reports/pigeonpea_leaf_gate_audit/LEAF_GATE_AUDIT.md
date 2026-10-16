# TurSathi AI — Phase 5B: Read-Only Leaf Image Gate Audit

---

## 1. Executive Summary

This audit inspects the complete image upload, validation, and disease prediction pipeline in the TurSathi AI backend to determine how uploaded images reach the five-class pigeonpea classifier, what validation checks currently exist, and why whole-plant images, seed pods, and out-of-distribution (OOD) scientific figures collapse to **Wilt** with high confidence as observed in Phase 5A.

### Key Audit Findings:
1. **Binary Crop Gate Exists:** An upstream image gate ([`backend/app/ml/tur_image_gate.py`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/backend/app/ml/tur_image_gate.py)) and binary neural validator ([`backend/app/ml/tur_image_validator.py`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/backend/app/ml/tur_image_validator.py)) **do exist** and are actively wired into the prediction service.
2. **Effective Non-Tur Crop Rejection:** The binary validator (`tur_image_validator_efficientnet_b0_v3.pth`) accurately distinguishes pigeonpea (`Tur`) from other crops (`Not_Tur`), achieving 100% rejection (133/133) on non-pigeonpea crop test images.
3. **Absence of a "Leaf vs. Non-Leaf / Organ" Gate:** The validator was trained strictly on binary labels (`Tur` vs. `Not_Tur`). It validates whether the plant material is pigeonpea, but **has no mechanism to verify whether the image is an individual leaf** versus a whole bush, dried stalk, fruit pod, or scientific multi-panel diagram.
4. **Minimal Quality Standards:** Image quality filtering is limited to a PIL file-decode check and a trivial dimension floor of $32 \times 32$ pixels. There are no checks for blur, focus, lighting, or low web resolution.
5. **Softmax OOD Collapse Mechanism:** When non-leaf pigeonpea plant parts (e.g. pods, whole plants, Alternaria blight) pass the binary gate because they are pigeonpea, the 5-class disease classifier (`TurDiseasePredictor`) forces the representation into one of its five closed-set classes. Because whole-plant wilt images in the training set contain brown/dry foliage and branches (unlike the close-up green leaf surfaces of Healthy, Leaf_Spot, Leaf_webber, and Sterilic_mosaic), non-leaf imagery predominantly triggers the **Wilt** feature filters, producing high softmax confidence ($> 0.97$) and bypassing the post-prediction $< 0.65$ confidence filter.

---

## 2. End-to-End Pipeline Trace

The image ingestion and prediction workflow traverses the following route:

```
[Mobile / Client Upload]
         │
         ▼
1. POST /api/v1/scans (backend/app/api/v1/scans.py)
   ├── Size guard check: len(file_bytes) <= 20 MB
   └── create_scan_with_image() (backend/app/services/scan_service.py)
         └── validate_image_upload() (backend/app/services/storage_service.py)
               ├── Checks MIME type (JPEG, PNG, WebP, HEIC)
               └── Saves image to uploads/scans/{uuid}.{ext}
         └── Creates TurScan DB record (status="received", prediction_status="pending")
         │
         ▼
2. POST /api/v1/predictions/tur-leaf/{scan_id} (backend/app/api/v1/predictions.py)
   └── run_prediction() (backend/app/services/prediction_service.py)
         ├── Verifies user ownership and locates image on disk
         │
         ├── 3. Gate Validation: TurImageGate.validate() (backend/app/ml/tur_image_gate.py)
         │     ├── Sanity check: PIL Image.verify()
         │     ├── Dimension check: width >= 32 and height >= 32
         │     └── Calls TurImageValidator.predict() (backend/app/ml/tur_image_validator.py)
         │           └── Model: models/tur_image_validator_efficientnet_b0_v3.pth
         │           └── Binary Output: "Tur" vs "Not_Tur"
         │     └── IF Not_Tur: Raises HTTP 422 ("validation_failed")
         │
         ├── 4. Disease Inference: TurDiseasePredictor.predict() (backend/app/ml/tur_predictor.py)
         │     └── Preprocessing: Resize(224, 224), ToTensor(), ImageNet Normalize
         │     └── Model: models/best_pigeonpea_disease_final_efficientnet_b0.pth
         │     └── 5 Classes: ['Healthy', 'Leaf_Spot', 'Leaf_webber', 'Sterilic_mosaic', 'Wilt']
         │     └── Output: disease_name, confidence, confidence_level
         │
         └── 5. Post-Prediction Confidence Filter (backend/app/services/prediction_service.py)
               ├── IF confidence < 0.65:
               │     └── Raises HTTP 422 ("unsupported_disease")
               └── IF confidence >= 0.65:
                     └── Persists disease_name, confidence to DB; returns HTTP 200
```

---

## 3. Code Evidence: Existing Safeguards vs. Gaps

### A. Confirmed Existing Safeguards (Code-Verified)

1. **Upload Sanitation & MIME Filtering:**
   - **Location:** [`backend/app/services/storage_service.py:L164-L186`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/backend/app/services/storage_service.py#L164-L186)
   - **Mechanism:** Enforces allowed MIME types (`image/jpeg`, `image/png`, `image/webp`, `image/heic`) and maximum file size (20 MB). Generates server-side UUID filenames to prevent path traversal.
2. **Basic Decode Sanity:**
   - **Location:** [`backend/app/ml/tur_image_gate.py:L48-L82`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/backend/app/ml/tur_image_gate.py#L48-L82)
   - **Mechanism:** Catches unidentifiable or corrupt files via `Image.open().verify()` and rejects dimensions $< 32 \times 32$ pixels.
3. **Binary Crop Gate (`TurImageValidator`):**
   - **Location:** [`backend/app/ml/tur_image_validator.py:L9-L107`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/backend/app/ml/tur_image_validator.py#L9-L107)
   - **Model:** `models/tur_image_validator_efficientnet_b0_v3.pth`
   - **Mechanism:** Distinguishes pigeonpea from other vegetation (`classes = ["Not_Tur", "Tur"]`). Rejects non-pigeonpea images with HTTP 422 (`validation_failed`).
4. **Post-Prediction Confidence Floor:**
   - **Location:** [`backend/app/services/prediction_service.py:L100-L115`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/backend/app/services/prediction_service.py#L100-L115)
   - **Mechanism:** Rejects predictions with confidence $< 0.65$ with HTTP 422 (`unsupported_disease`).

---

### B. Identified Gaps (Root Cause of OOD Collapse)

1. **No Organ-Level Discrimination (Leaf vs. Whole Plant vs. Pod):**
   - **Code Reality:** `TurImageValidator` only answers: *"Is this pigeonpea?"*
   - **Gap:** When an uploaded image depicts pigeonpea seed pods (e.g. `Pigeon pea plant in fruit... Kitui, Kenya.jpg`) or a whole wilting bush or a textbook diagram (`488313...Fig1.jpg`), the validator correctly answers **`is_tur = True`** because the plant tissue is indeed pigeonpea.
   - **Result:** Non-leaf pigeonpea organs pass the gate unhindered.
2. **Minimal Quality & Resolution Filtering:**
   - **Code Reality:** The only dimension constraint is `if width < 32 or height < 32:` in `tur_image_gate.py:L56`.
   - **Gap:** A severely compressed, blurry, or low-resolution $335 \times 597$ web thumbnail passes as valid. There is no sharpness / Laplacian variance check, no blur detection, and no exposure verification.
3. **Overconfidence of Closed-Set Softmax on Non-Leaf Inputs:**
   - **Code Reality:** `TurDiseasePredictor` uses standard closed-set softmax over 5 classes (`Healthy`, `Leaf_Spot`, `Leaf_webber`, `Sterilic_mosaic`, `Wilt`).
   - **Gap:** Healthy, Leaf_Spot, Leaf_webber, and Sterilic_mosaic training samples are exclusively close-up leaf photographs. In contrast, Wilt training samples include distant canopy shots and woody branches. Consequently, any non-leaf or whole-plant pigeonpea image activates the Wilt output node, producing confidences exceeding $0.99$.
   - **Result:** The $< 0.65$ confidence floor is completely bypassed. As documented in [`backend/tests/ood_evaluation_report.txt`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/backend/tests/ood_evaluation_report.txt), 39 out of 41 exploratory web images (95.1%) passed through the gate and were predicted as Wilt.

---

## 4. Responsible Files and Function Map

| Component | File Path | Function / Class | Current Responsibility |
|---|---|---|---|
| **Scan Upload** | [`backend/app/api/v1/scans.py`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/backend/app/api/v1/scans.py) | `upload_scan()` | Receives multipart upload, verifies $\le 20\text{ MB}$, initiates scan persistence |
| **File Storage** | [`backend/app/services/storage_service.py`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/backend/app/services/storage_service.py) | `validate_image_upload()` | Validates MIME type and file size; saves to UUID file |
| **Prediction Orchestration** | [`backend/app/services/prediction_service.py`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/backend/app/services/prediction_service.py) | `run_prediction()` | Coordinates gate validation, disease prediction, confidence thresholding, and DB writes |
| **Image Gate Wrapper** | [`backend/app/ml/tur_image_gate.py`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/backend/app/ml/tur_image_gate.py) | `TurImageGate.validate()` | Validates $32\times 32$ size, decodability, and delegates to `TurImageValidator` |
| **Binary Crop Classifier** | [`backend/app/ml/tur_image_validator.py`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/backend/app/ml/tur_image_validator.py) | `TurImageValidator.predict()` | EfficientNet-B0 binary model classifying `Tur` vs `Not_Tur` |
| **Disease Predictor** | [`backend/app/ml/tur_predictor.py`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/backend/app/ml/tur_predictor.py) | `TurDiseasePredictor.predict()` | EfficientNet-B0 5-class closed-set classifier predicting leaf pathology |

---

## 5. Recommended Smallest Safe Next Step

> [!TIP]
> **Recommended Next Step (Do NOT Implement in this Phase):**
> 
> The smallest, non-breaking, and lowest-risk improvement to the pipeline is to enhance **Stage 1 (Basic Sanity)** in [`backend/app/ml/tur_image_gate.py`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/backend/app/ml/tur_image_gate.py#L48-L82) with deterministic image quality heuristics before touching any ML models:
> 
> 1. **Increase Resolution Floor:** Raise the minimum image dimension from $32 \times 32$ to at least $224 \times 224$ pixels (matching the model's native input resolution). Rejecting tiny thumbnails immediately blocks low-quality web snippets.
> 2. **Laplacian Blur / Focus Check:** Compute the variance of the Laplacian using OpenCV/NumPy. If blur score is below an empirically established threshold, reject with `"Image is too blurry. Please capture a clear, focused leaf photo."`
> 3. **Future Step (Model-Level):** When retraining the image validator, consider evolving it from a binary `Tur / Not_Tur` classifier into a 3-class validator: `Tur_Leaf`, `Tur_NonLeaf` (pods/stems/field shots), and `Not_Tur`. This will filter whole plants before they reach the disease classifier.

---

## 6. Preservation Verification

- **Production Model Checkpoint:** `models/best_pigeonpea_disease_final_efficientnet_b0.pth` (SHA-256: `5baecdc3911502c4cb345101c6f2fd84824eb4cb025e300d66e00231a4834b99` — **Untouched**)
- **Experimental Model Checkpoint:** `models/experimental/pigeonpea_clean_candidate_v1/best_pigeonpea_clean_candidate_v1_efficientnet_b0.pth` (**Untouched**)
- **Datasets:** `datasets/pigeonpea_disease_final/` (1,858 files), `datasets/pigeonpea_disease_clean_candidate_v1/` (1,676 files), and `datasets/new_disease_images/` (42 files) (**All Untouched**)
- **Application Code:** Zero changes made to `backend/app/`, `backend/app/ml/`, `frontend/`, `mobile/`, or database records.
- **Git Status:** Uncommitted user edit in `backend/app/api/v1/predictions.py` is safely preserved; no Git mutations were performed.
