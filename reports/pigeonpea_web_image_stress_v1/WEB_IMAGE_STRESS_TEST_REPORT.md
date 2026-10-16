# TurSathi AI — Phase 5A: Exploratory Web Image Stress Test Report

**Date:** 2026-10-14T15:17:17  
**Input Directory:** `C:\Users\admin\OneDrive\Documents\Desktop\TurSathi AI\datasets\new_disease_images` (42 total items)  
**Production Model:** `best_pigeonpea_disease_final_efficientnet_b0.pth`  
**Experimental Model:** `best_pigeonpea_clean_candidate_v1_efficientnet_b0.pth`  

## 1. Executive Summary & File Ingestion

- **Total Files Evaluated:** 42
- **Valid Decodable Images:** 41 (36 JPEG, 4 PNG, 1 WebP)
- **Skipped Files:** 1 (`new_disease_images`: 0-byte non-image file)
- **Exact Duplicate Files:** 5 redundant copies (10 files total)
- **Unique Decodable Images:** **36**

## 2. Agreement & Comparative Metrics

| Metric | All Decodable Images ($N=41$) | Unique Decodable Images ($N=36$) |
|---|:---:|:---:|
| **Agreements** | 40 | **35** |
| **Disagreements** | 1 | **1** |
| **Agreement Rate** | 97.56% | **97.22%** |

## 3. Class Distribution Comparison (Unique Images, $N=36$)

| Disease Class | Production Model Predictions | Experimental Model Predictions |
|---|:---:|:---:|
| **Healthy** | 0 | 0 |
| **Leaf_Spot** | 0 | 0 |
| **Leaf_webber** | 0 | 0 |
| **Sterilic_mosaic** | 2 | 1 |
| **Wilt** | 34 | 35 |

## 4. Disagreement Breakdown (Unique Images)

| Image Filename | Dimensions | Production Prediction (Conf) | Experimental Prediction (Conf) |
|---|:---:|---|---|
| `images (2).jpg` | 488x250 | Sterilic_mosaic (0.49) | Wilt (0.98) |

## 5. Observations on Out-of-Distribution Reference Images

Specific notable non-field reference images:

- **`AAlternaria-blight-symptom-on-leaves-and-B-aerial-plant-parts-leaves-stem-buds-and.webp`** (459x244):
  - Production: `Wilt` (0.53)
  - Experimental: `Wilt` (0.97)
  - Agreement: `AGREE`
- **`488313_0_En_25-1_Fig1_HTML.jpg`** (685x433):
  - Production: `Wilt` (1.00)
  - Experimental: `Wilt` (1.00)
  - Agreement: `AGREE`
- **`Pigeon pea plant in fruit, Kitui, Kenya. In this form, the pods have striations. © Maundu, 2021.jpg`** (350x240):
  - Production: `Wilt` (1.00)
  - Experimental: `Wilt` (1.00)
  - Agreement: `AGREE`

## 6. Critical Safety & Protocol Notices

> [!IMPORTANT]
> 1. **Exploratory Observation Only:** These images originate from uncurated web searches and scientific figures. They do NOT constitute ground-truth field data.
> 2. **No Diagnostic Accuracy Claims:** Agreement between models does not prove diagnostic correctness. Both models may agree on an incorrect label when confronted with novel symptoms or out-of-scope pathogens (e.g. *Alternaria*).
> 3. **Zero Spray/Chemical Recommendations:** No prescriptive pesticide or chemical treatment guidance was generated from these test predictions.
