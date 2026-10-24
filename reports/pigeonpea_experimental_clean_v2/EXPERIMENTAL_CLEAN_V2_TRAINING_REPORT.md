# TurSathi AI — Phase 4: Candidate v2 Experimental Training Report

**Date:** 2026-10-22 17:51:35  
**Candidate Checkpoint:** `experimental_efficientnet_b0_clean_v2.pth`  
**SHA-256:** `3d762b90dc4892e6aab0ac80e907bd520dd9e20c3b069f1f83a1f41bbbde7daf`  
**Resolution:** 288x288  
**Loss Weighting:** `biological`  
**Production Checkpoint Preservation:** Confirmed  

## 1. Best Validation Metrics (Model Selection Split)

- **Best Epoch:** 12 / 20
- **Best Validation Accuracy:** **93.38%**

### Per-Class Validation Breakdown

| Class | Precision | Recall | F1-Score | Support |
|---|:---:|:---:|:---:|:---:|
| **Healthy** | 1.0000 | 1.0000 | 1.0000 | 28.0 |
| **Leaf_Spot** | 0.9057 | 0.9057 | 0.9057 | 53.0 |
| **Leaf_webber** | 1.0000 | 0.9630 | 0.9811 | 27.0 |
| **Sterilic_mosaic** | 0.8718 | 0.8947 | 0.8831 | 38.0 |
| **Wilt** | 1.0000 | 1.0000 | 1.0000 | 5.0 |
| **Macro Avg** | 0.9555 | 0.9527 | 0.9540 | 151.0 |
| **Weighted Avg** | 0.9346 | 0.9338 | 0.9341 | 151.0 |

### Validation Confusion Matrix

```
Classes order: ['Healthy', 'Leaf_Spot', 'Leaf_webber', 'Sterilic_mosaic', 'Wilt']
[[28,  0,  0,  0,  0],
 [ 0, 48,  0,  5,  0],
 [ 0,  1, 26,  0,  0],
 [ 0,  4,  0, 34,  0],
 [ 0,  0,  0,  0,  5]]
```
