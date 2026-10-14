# STAGE F28 REPORT: MODEL AND INTEGRATION READINESS DECISION

**Project:** TurSathi AI / AgriMind AI — Pigeonpea Disease Detection  
**Stage:** F28 (Model and Integration Readiness Decision)  
**Execution Timestamp:** 2026-10-13T13:42:30+05:30  
**Overall Decision:** **HOLD FOR GENERAL PRODUCTION RELEASE** (Authorized for Restricted Pilot Only)

---

### 1. Audit Summary Across Evaluation Dimensions

| Audit Dimension | Evaluated State | Status | Evidence / Notes |
| :--- | :--- | :---: | :--- |
| **Five-Class Ordering & Mapping** | Index-to-label mapping in `tur_predictor.py` | **PASS** | Exact match with checkpoint metadata: `[Healthy: 0, Leaf_Spot: 1, Leaf_webber: 2, Sterilic_mosaic: 3, Wilt: 4]`. |
| **Preprocessing & Normalization** | Resize (224, 224), ToTensor, ImageNet normalization | **PASS** | Identical transforms applied across gate and predictor. |
| **Gate & Classifier Integration** | Sequential two-stage evaluation in `prediction_service.py` | **PASS** | Gate filters non-tur leaves before classifier; clean 422 responses on rejection. |
| **Confidence Handling & Guards** | Softmax confidence with $< 0.65$ rejection threshold | **PASS** | Enforces secondary rejection for uncertain predictions. |
| **Error Handling & Security** | Safe messages, in-memory DB isolation, no leaked paths | **PASS** | Zero credential/stack trace exposure across 26 passing backend tests. |
| **Dataset Cleanliness & Independence** | 24 cross-label collisions & 51/58 leaked Wilt test derivatives | **HOLD** | True clean accuracy is 95.68% (288/301), but Wilt evaluation is structurally compromised by data augmentation leakage. |
| **OOD & Arbitrary-Background Safety** | Binary gate accepts 40/40 exploratory unverified leaf images | **HOLD** | Strong rejection on curated crops (0/79 and 0/54), but unconstrained domain drift can bypass the binary gate. |

---

### 2. Deep Dive: Why Full Production Release is on HOLD

1. **Wilt Test Split Contamination:**
   All 58 test images for Wilt originate from a tiny pool of 30 physical plant photographs in `_temp_wilt_staging`. 51 of those 58 images are synthetic augmented derivatives of plants present in the training set. While the model achieves high training and testing scores on these variants, real-world generalization to novel, unaugmented Wilt cases in farmers' fields cannot be scientifically guaranteed from this test set alone.

2. **Cross-Label Training Collisions:**
   The presence of 24 test images with contradictory labels across `Leaf_Spot` and `Sterilic_mosaic` reveals historical label noise in the underlying dataset. While our quarantined evaluation established a 95.68% accuracy baseline on the 301 verified samples, ambiguous leaf spot vs. mosaic patterns remain vulnerable to classification flipping.

3. **Arbitrary Foliage OOD Bypass:**
   While `TurImageGate` demonstrated 0.00% false acceptances against specific crop leaves (CAT-2) and unsupported pigeonpea diseases (CAT-3), the exploratory CAT-4 audit revealed that 40/40 non-standard leaf photographs passed the gate. In an open-world setting, a farmer uploading a weed, wild shrub, or ambiguous garden plant with green foliage could pass through to the 5-class classifier.

---

### 3. Formal Readiness Decision

**DECISION: HOLD FOR GENERAL OPEN-WORLD RELEASE**  
**CONDITIONAL STATUS: READY FOR RESTRICTED PILOT TESTING**

The system is stable, functional, and architecturally sound for piloted testing under controlled conditions (e.g. extension officers or selected farmers instructed to photograph pigeonpea leaves), but cannot be certified for unmonitored global deployment until the OOD and dataset gaps are addressed.

---

### 4. Required Evidence to Lift the HOLD

To graduate from HOLD to an unconditional production GO, the following work must be completed:
1. **Independent Wilt Dataset:** Collect and benchmark at least 50–100 genuine, unaugmented field photographs of Wilt from geographically diverse pigeonpea plots.
2. **Annotation Clean-up:** Re-label or remove the 55 ambiguous image duplicates colliding between `Leaf_Spot` and `Sterilic_mosaic`.
3. **Hard Negative Gate Retraining:** Augment the binary image validator's negative training set with diverse agricultural weeds, background soils, and non-target foliage to eliminate the CAT-4 exploratory bypass.

---

### 5. Transition to Stage F29

The HOLD decision does not block Stage F29 (Frontend/Backend Functional Regression). We proceed to Stage F29 to verify the end-to-end user experience, UI rendering, authentication flows, and error presentation.
