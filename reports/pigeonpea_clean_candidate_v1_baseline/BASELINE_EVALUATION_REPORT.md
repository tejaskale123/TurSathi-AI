# TurSathi AI — Production Checkpoint Baseline Evaluation on Clean Candidate Test Set

**Date:** 2026-10-14 12:44:18  
**Model Checkpoint:** `best_pigeonpea_disease_final_efficientnet_b0.pth`  
**Test Set:** `datasets/pigeonpea_disease_clean_candidate_v1/test/` (189 images)  
**Overall Accuracy:** **94.71%** (179 / 189)

## 1. Classification Metrics

| Class | Precision | Recall | F1-Score | Support |
|---|:---:|:---:|:---:|:---:|
| **Healthy** | 1.0000 | 0.9783 | 0.9890 | 46.0 |
| **Leaf_Spot** | 0.8793 | 0.9444 | 0.9107 | 54.0 |
| **Leaf_webber** | 1.0000 | 0.9688 | 0.9841 | 32.0 |
| **Sterilic_mosaic** | 0.9400 | 0.9038 | 0.9216 | 52.0 |
| **Wilt** | 1.0000 | 1.0000 | 1.0000 | 5.0 |
| **Macro Avg** | 0.9639 | 0.9591 | 0.9611 | 189.0 |
| **Weighted Avg** | 0.9490 | 0.9471 | 0.9475 | 189.0 |

## 2. Confusion Matrix

```
Rows = True Labels, Columns = Predicted Labels
Classes order: ['Healthy', 'Leaf_Spot', 'Leaf_webber', 'Sterilic_mosaic', 'Wilt']

[[45,  1,  0,  0,  0],
 [ 0, 51,  0,  3,  0],
 [ 0,  1, 31,  0,  0],
 [ 0,  5,  0, 47,  0],
 [ 0,  0,  0,  0,  5]]
```

## 3. Key Observations

1. **Impact of Cross-Class Duplicate Removal:** On the clean test set, the production model's true performance without leaked data is established.
2. **Wilt Class Evaluation Limitation:** Support for Wilt is strictly **5.0 held-out original field photographs**. All leaked synthetic augmentations were successfully purged, eliminating evaluation leakage.
