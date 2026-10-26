# TurSathi AI — Candidate Model Calibration and Validation Report

**Experiment ID:** `20261026_072810`  
**Evaluation Date:** 2026-10-26T13:44:45  
**Candidate Checkpoint:** `tursathi_efficientnet_b0_candidate_20261026_072810 (1).pth`  
**Candidate OOD Profile:** `ood_feature_profile_20261026_072810 (1).json`  
**Evaluation Mode:** Isolated, Non-Destructive Offline Evaluation (Production remains 100% untouched)  

---

## 1. Executive Summary

A deep, multi-phase evaluation and OOD threshold calibration was conducted on the Google Colab candidate EfficientNet-B0 model (`20261026_072810`). 

### Key Highlights:
1. **High In-Distribution Performance:**
   - **Validation Accuracy:** `96.96%` (255 / 263 correct)
   - **Untouched Test Accuracy:** `96.93%` (253 / 261 correct)
   - Both drastically outperform the baseline production model (`92.02%`).
2. **Dataset Provenance & Zero Leakage:**
   - 1,747 clean, deduplicated images (Train: 1,223, Val: 263, Test: 261).
   - Zero hash overlap between splits (verified across 100% of samples).
   - Zero hash overlap between external OOD images and any clean split.
   - Identified that the 41 external OOD files contain **5 duplicate pairs (36 unique image hashes)**.
3. **The Wilt Sinkhole & Threshold Dilemma:**
   - Raw classifier maps **40 of 41 external images (97.6%)** to `Wilt` with average confidence of `91.6%`.
   - At the candidate's original threshold (`Wilt = 0.40`), **23 of 41 external images (56.1%)** leak through the OOD gate, while retaining **39 of 43 genuine Wilt validation images (90.7%)**.
   - Lowering the Wilt threshold to **`0.35`** cuts external leakage to **4 of 41 (9.8%)**, but causes severe collateral damage: it rejects **20 of 43 genuine Wilt validation images (46.5% false rejection)** and **14 of 43 genuine Wilt test images (32.6% false rejection)**.
   - Forcing the Wilt threshold down to **`0.33`** completely stops the 41 external images (100% rejection), but **discards more than half of all genuine Wilt samples (24 of 43, 55.8% false rejection)**.
   - **Critical Conclusion:** The distance distributions of genuine Wilt and external non-pigeonpea foliage heavily overlap between `0.33` and `0.40`. Post-hoc threshold tuning cannot separate them without crippling genuine Wilt recall. The upstream Leaf Validator must serve as the primary defensive barrier.

---

## 2. In-Distribution Performance Comparison

### 2.1 Validation Set Performance (N=263)

| Class | Precision | Recall | F1-Score | Support |
| :--- | :---: | :---: | :---: | :---: |
| **Healthy** | 1.0000 | 1.0000 | 1.0000 | 54.0 |
| **Leaf_Spot** | 0.9322 | 0.9483 | 0.9402 | 58.0 |
| **Leaf_webber** | 0.9630 | 1.0000 | 0.9811 | 52.0 |
| **Sterilic_mosaic** | 0.9623 | 0.9107 | 0.9358 | 56.0 |
| **Wilt** | 1.0000 | 1.0000 | 1.0000 | 43.0 |
| **Overall Accuracy** | **96.96%** | - | - | **5** |

### 2.2 Untouched Test Set Performance (N=261)
*(Strictly held out; zero threshold tuning performed on this set)*

| Class | Precision | Recall | F1-Score | Support |
| :--- | :---: | :---: | :---: | :---: |
| **Healthy** | 1.0000 | 1.0000 | 1.0000 | 54.0 |
| **Leaf_Spot** | 0.9180 | 0.9825 | 0.9492 | 57.0 |
| **Leaf_webber** | 0.9615 | 0.9804 | 0.9709 | 51.0 |
| **Sterilic_mosaic** | 0.9804 | 0.8929 | 0.9346 | 56.0 |
| **Wilt** | 1.0000 | 1.0000 | 1.0000 | 43.0 |
| **Overall Accuracy** | **96.93%** | - | - | **261** |

---

## 3. Distance Distribution Analysis (Validation Data Only)

Distance to class centroid in 1280-D L2-normalized feature space:

| Class | Min | 25th % | Median | 75th % | 95th % | 97.5th % | Max |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Healthy** | 0.1761 | 0.2466 | 0.2644 | 0.2859 | 0.3471 | 0.3628 | 0.4370 |
| **Leaf_Spot** | 0.1938 | 0.2843 | 0.3352 | 0.4052 | 0.6038 | 0.7043 | 0.9823 |
| **Leaf_webber** | 0.1600 | 0.2275 | 0.2622 | 0.3187 | 0.3750 | 0.3829 | 0.6894 |
| **Sterilic_mosaic** | 0.1706 | 0.2475 | 0.3151 | 0.4274 | 0.7711 | 0.8020 | 0.8295 |
| **Wilt** | 0.2153 | 0.3084 | 0.3395 | 0.3727 | 0.4120 | 0.4152 | 0.4251 |

---

## 4. Wilt Threshold Calibration Sweep (Validation vs External OOD)

The following table documents the trade-off across candidate Wilt thresholds on **Validation Genuine Wilt (N=43)** vs **External Diagnostic OOD Images (N=41)**:

| Threshold | Genuine Wilt Retained | Genuine Wilt Acceptance | External OOD Rejected | External Rejection Rate | External False Acceptance |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **0.30** | 8/43 | 18.6% | 41/41 | 100.0% | 0/41 (0.0%) |
| **0.31** | 13/43 | 30.2% | 41/41 | 100.0% | 0/41 (0.0%) |
| **0.32** | 16/43 | 37.2% | 41/41 | 100.0% | 0/41 (0.0%) |
| **0.33** | 19/43 | 44.2% | 41/41 | 100.0% | 0/41 (0.0%) |
| **0.34** | 22/43 | 51.2% | 39/41 | 95.1% | 2/41 (4.9%) |
| **0.35** | 23/43 | 53.5% | 37/41 | 90.2% | 4/41 (9.8%) |
| **0.36** | 30/43 | 69.8% | 31/41 | 75.6% | 10/41 (24.4%) |
| **0.37** | 32/43 | 74.4% | 27/41 | 65.8% | 14/41 (34.2%) |
| **0.38** | 34/43 | 79.1% | 25/41 | 61.0% | 16/41 (39.0%) |
| **0.39** | 36/43 | 83.7% | 22/41 | 53.7% | 19/41 (46.3%) |
| **0.40** | 39/43 | 90.7% | 18/41 | 43.9% | 23/41 (56.1%) |
| **0.42** | 42/43 | 97.7% | 16/41 | 39.0% | 25/41 (61.0%) |

### Key Threshold Observations:
- **0.40 (Candidate Profile Default):** Retains 39 / 43 (90.7%) genuine Wilt in validation, but **leaks 23 / 41 external images (56.1% false acceptance)**.
- **0.35 (Operating Trade-off Point):** Rejects 37 / 41 (90.2%) external images, but **sacrifices 20 of 43 genuine Wilt validation images (46.5% false rejection)** and **14 of 43 genuine Wilt test images (32.6% false rejection)**.
- **0.33 (Zero-Leakage Filtering):** Achieves **100% rejection** on the 41 external diagnostic images, but **sacrifices more than half (24 of 43, 55.8%) of genuine Wilt validation images**.

---

## 5. Proposed Calibrated OOD Thresholds

| Disease Class | Original Profile Threshold | Proposed Calibrated Threshold | Basis & Justification |
| :--- | :---: | :---: | :--- |
| **Healthy** | 0.3628 | **0.3628** | 97.5th percentile of clean in-dist validation data. (100% precision/recall). |
| **Leaf_Spot** | 0.7043 | **0.7043** | 97.5th percentile of clean in-dist validation data. Accommodates foliar spot variance. |
| **Leaf_webber** | 0.3829 | **0.3829** | 97.5th percentile of clean in-dist validation data. |
| **Sterilic_mosaic** | 0.8020 | **0.8020** | 97.5th percentile of clean in-dist validation data. Mitigates the production false-rejection bug. |
| **Wilt** | 0.4000 | **0.3500 (Diagnostic Trade-off)** | Illustrates the severe precision/recall trade-off; requires upstream Leaf Validator to safely handle out-of-domain images. |

---

## 6. Verification on Untouched Final Test Set (N=261)

Passing the untouched test set through the proposed calibrated gate (Confidence >= 0.70, Margin >= 0.20, Cosine Distance <= tau_c):

| Class | Total Test Images | Retained & Accepted | False OOD Rejection | Low Confidence Rejection | Low Margin Rejection | Acceptance Rate |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Healthy** | 54 | 53 | 1 | 0 | 0 | **98.1%** |
| **Leaf_Spot** | 57 | 50 | 0 | 7 | 2 | **87.7%** |
| **Leaf_webber** | 51 | 43 | 7 | 3 | 0 | **84.3%** |
| **Sterilic_mosaic** | 56 | 51 | 3 | 5 | 2 | **91.1%** |
| **Wilt** | 43 | 29 | 14 | 0 | 0 | **67.4%** |

---

## 7. Limitations & Honest Engineering Evaluation

1. **Small External OOD Sample Size:**
   The external diagnostic set consists of only 41 files, representing **only 36 unique images** (5 duplicates). While it provides an empirical directional signal, 36 images are statistically insufficient to guarantee zero leakage across thousands of open-world agricultural species.
2. **Persistent Softmax Wilt Bias:**
   Because 40 of 41 external images land in the Wilt softmax sector, the neural network treats Wilt as the default residual class. Feature space distance thresholds significantly narrow this loophole (from 56.1% leakage down to 9.8%), but cannot eliminate it without hurting true Wilt predictions.
3. **Upstream Dependency:**
   No 5-class closed-set classifier can reliably distinguish non-pigeonpea plants solely by output distance without trade-offs. The multi-stage pipeline architecture (Leaf Validator $ightarrow$ Disease Classifier) is essential.

---

## 8. Final Recommendation & Safe Action Plan

### Recommended Action:
**KEEP THE CANDIDATE IN ISOLATED SHADOW-TESTING; DO NOT DEPLOY TO PRODUCTION YET.**

### Concrete Next Steps:
1. **Zero Production Interruption:** Leave existing production models, thresholds, APIs, and database records untouched.
2. **Implement Shadow / Canary Routing:** If desired, route 10% of background inference logs to evaluate the candidate model side-by-side with production without returning predictions to end-users.
3. **Upgrade Upstream Tur Leaf Validator:** Retrain `tur_image_validator` with negative samples from other crop diseases (corn leaf blight, tomato spots, etc.) so that non-pigeonpea leaves are rejected before entering the 5-class model.
4. **Collect Real Field Wilt Samples:** Collect 50-100 high-resolution field photos of pigeonpea Fusarium wilt showing roots, stems, and drooping canopies to expand the Wilt training distribution.
