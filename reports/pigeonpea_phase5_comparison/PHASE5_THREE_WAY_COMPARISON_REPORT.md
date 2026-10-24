# TurSathi AI — Phase 5: Controlled Three-Way Comparative Test Evaluation

**Date:** 2026-10-22 17:56:45  
**Test Set:** `datasets/pigeonpea_disease_clean_candidate_v1/test/` (189 clean images)  
**Hardware:** Quadro P2000  

## 1. Executive Summary Table

| Metric | Production Model | Experimental V1 (224x224) | Experimental V2 (288x288 + Weighted) |
|---|:---:|:---:|:---:|
| **Overall Accuracy** | **94.71%** (179/189) | **94.71%** (179/189) | **94.71%** (179/189) |
| **Total Errors** | 10 images | 10 images | 10 images |
| **Leaf_Spot -> Sterilic_mosaic** | 3 | 1 | 3 |
| **Sterilic_mosaic -> Leaf_Spot** | 5 | 6 | 5 |
| **Total Mutual Confusion** | **8** | **7** | **8** |
| **Macro F1-Score** | 0.9611 | 0.9599 | 0.9609 |
| **Weighted F1-Score** | 0.9475 | 0.9475 | 0.9474 |
| **Expected Calibration Error (ECE)** | 0.0326 | 0.0271 | 0.0399 |
| **Mean Latency (per image)** | 15.51 ms | 15.54 ms | 14.22 ms |
| **Throughput** | 64.5 img/s | 64.4 img/s | 70.3 img/s |

## 2. Per-Class Precision, Recall, and F1

| Class | Metric | Production Model | Experimental V1 | Experimental V2 |
|---|---|:---:|:---:|:---:|
| **Healthy** | Precision | 1.0000 | 1.0000 | 1.0000 |
| | Recall | 0.9783 | 0.9783 | 0.9783 |
| | F1-Score | 0.9890 | 0.9890 | 0.9890 |
| **Leaf_Spot** | Precision | 0.8793 | 0.8667 | 0.8947 |
| | Recall | 0.9444 | 0.9630 | 0.9444 |
| | F1-Score | 0.9107 | 0.9123 | 0.9189 |
| **Leaf_webber** | Precision | 1.0000 | 0.9688 | 1.0000 |
| | Recall | 0.9688 | 0.9688 | 0.9688 |
| | F1-Score | 0.9841 | 0.9688 | 0.9841 |
| **Sterilic_mosaic** | Precision | 0.9400 | 0.9787 | 0.9216 |
| | Recall | 0.9038 | 0.8846 | 0.9038 |
| | F1-Score | 0.9216 | 0.9293 | 0.9126 |
| **Wilt** | Precision | 1.0000 | 1.0000 | 1.0000 |
| | Recall | 1.0000 | 1.0000 | 1.0000 |
| | F1-Score | 1.0000 | 1.0000 | 1.0000 |

## 3. Confusion Matrices

```
Order: ['Healthy', 'Leaf_Spot', 'Leaf_webber', 'Sterilic_mosaic', 'Wilt']

Production Model Confusion Matrix:
[[45,  1,  0,  0,  0],
 [ 0, 51,  0,  3,  0],
 [ 0,  1, 31,  0,  0],
 [ 0,  5,  0, 47,  0],
 [ 0,  0,  0,  0,  5]]

Experimental V1 Confusion Matrix:
[[45,  1,  0,  0,  0],
 [ 0, 52,  1,  1,  0],
 [ 0,  1, 31,  0,  0],
 [ 0,  6,  0, 46,  0],
 [ 0,  0,  0,  0,  5]]

Experimental V2 Confusion Matrix:
[[45,  1,  0,  0,  0],
 [ 0, 51,  0,  3,  0],
 [ 0,  0, 31,  1,  0],
 [ 0,  5,  0, 47,  0],
 [ 0,  0,  0,  0,  5]]
```

## 4. Checkpoint Integrity Verification

- **Production Checkpoint SHA-256:** `5baecdc3911502c4cb345101c6f2fd84824eb4cb025e300d66e00231a4834b99` (Unmodified: **True**)
- **Experimental V1 Checkpoint SHA-256:** `dd9d96b0a33513da84fcdca5756966148526c6ad43cfc0337f11e3c05f8503a6` (Unmodified: **True**)
- **Experimental V2 Checkpoint SHA-256:** `3d762b90dc4892e6aab0ac80e907bd520dd9e20c3b069f1f83a1f41bbbde7daf` (Unmodified: **True**)

