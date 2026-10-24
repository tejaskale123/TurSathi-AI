# TurSathi AI — Phase 3: Side-by-Side Model Comparison Report

**Date:** 2026-10-22 17:21:26  
**Test Set:** `datasets/pigeonpea_disease_clean_candidate_v1/test/` (189 clean images)  
**Hardware:** Quadro P2000  

## 1. Executive Summary

| Metric | Production Model | Experimental Clean-Trained | Delta |
|---|:---:|:---:|:---:|
| **Overall Accuracy** | **94.71%** (179/189) | **94.71%** (179/189) | **+0.00%** |
| **Total Errors** | 10 images | 10 images | +0 errors |
| **Leaf_Spot -> Sterilic_mosaic** | 3 | 1 | -2 |
| **Sterilic_mosaic -> Leaf_Spot** | 5 | 6 | +1 |
| **Total Mutual Confusion** | **8** | **7** | **-1** |
| **Expected Calibration Error (ECE)** | 0.0326 | 0.0271 | -0.0056 |
| **Mean Latency (per image)** | 21.99 ms | 18.89 ms | -3.10 ms |

## 2. Per-Class Metrics Comparison

| Class | Metric | Production Model | Experimental Model | Delta |
|---|---|:---:|:---:|:---:|
| **Healthy** | Precision | 1.0000 | 1.0000 | +0.0000 |
| | Recall | 0.9783 | 0.9783 | +0.0000 |
| | F1-Score | 0.9890 | 0.9890 | +0.0000 |
| **Leaf_Spot** | Precision | 0.8793 | 0.8667 | -0.0126 |
| | Recall | 0.9444 | 0.9630 | +0.0185 |
| | F1-Score | 0.9107 | 0.9123 | +0.0016 |
| **Leaf_webber** | Precision | 1.0000 | 0.9688 | -0.0312 |
| | Recall | 0.9688 | 0.9688 | +0.0000 |
| | F1-Score | 0.9841 | 0.9688 | -0.0154 |
| **Sterilic_mosaic** | Precision | 0.9400 | 0.9787 | +0.0387 |
| | Recall | 0.9038 | 0.8846 | -0.0192 |
| | F1-Score | 0.9216 | 0.9293 | +0.0077 |
| **Wilt** | Precision | 1.0000 | 1.0000 | +0.0000 |
| | Recall | 1.0000 | 1.0000 | +0.0000 |
| | F1-Score | 1.0000 | 1.0000 | +0.0000 |
| **Macro Avg** | F1-Score | 0.9611 | 0.9599 | -0.0012 |
| **Weighted Avg** | F1-Score | 0.9475 | 0.9475 | -0.0000 |

## 3. Confusion Matrices

### Production Model Confusion Matrix
```
Classes order: ['Healthy', 'Leaf_Spot', 'Leaf_webber', 'Sterilic_mosaic', 'Wilt']
[[45,  1,  0,  0,  0],
 [ 0, 51,  0,  3,  0],
 [ 0,  1, 31,  0,  0],
 [ 0,  5,  0, 47,  0],
 [ 0,  0,  0,  0,  5]]
```

### Experimental Model Confusion Matrix
```
Classes order: ['Healthy', 'Leaf_Spot', 'Leaf_webber', 'Sterilic_mosaic', 'Wilt']
[[45,  1,  0,  0,  0],
 [ 0, 52,  1,  1,  0],
 [ 0,  1, 31,  0,  0],
 [ 0,  6,  0, 46,  0],
 [ 0,  0,  0,  0,  5]]
```

## 4. Checkpoint Verification

- **Production Checkpoint SHA-256:** `5baecdc3911502c4cb345101c6f2fd84824eb4cb025e300d66e00231a4834b99` (Unmodified: **True**)
- **Experimental Checkpoint SHA-256:** `dd9d96b0a33513da84fcdca5756966148526c6ad43cfc0337f11e3c05f8503a6` (Unmodified: **True**)
