# TurSathi AI — Phase 2: Experimental Model Training Report

**Date:** 2026-10-22 17:12:21  
**Experimental Checkpoint:** `experimental_efficientnet_b0_clean_v1.pth`  
**SHA-256:** `dd9d96b0a33513da84fcdca5756966148526c6ad43cfc0337f11e3c05f8503a6`  
**Production Checkpoint Preservation:** Confirmed (`5baecdc3911502c4cb345101c6f2fd84824eb4cb025e300d66e00231a4834b99`)  
**Training Time:** 17.04 minutes  

## 1. Best Validation Performance (Model Selection Split)

- **Best Epoch:** 17 / 20
- **Best Validation Accuracy:** **94.70%**

### Per-Class Validation Metrics (Epoch 17)

| Class | Precision | Recall | F1-Score | Validation Support |
|---|:---:|:---:|:---:|:---:|
| **Healthy** | 1.0000 | 1.0000 | 1.0000 | 28.0 |
| **Leaf_Spot** | 0.9592 | 0.8868 | 0.9216 | 53.0 |
| **Leaf_webber** | 1.0000 | 1.0000 | 1.0000 | 27.0 |
| **Sterilic_mosaic** | 0.8571 | 0.9474 | 0.9000 | 38.0 |
| **Wilt** | 1.0000 | 1.0000 | 1.0000 | 5.0 |
| **Macro Avg** | 0.9633 | 0.9668 | 0.9643 | 151.0 |
| **Weighted Avg** | 0.9497 | 0.9470 | 0.9473 | 151.0 |

### Validation Confusion Matrix (Epoch 17)

```
Rows = True Labels, Columns = Predicted Labels
Classes order: ['Healthy', 'Leaf_Spot', 'Leaf_webber', 'Sterilic_mosaic', 'Wilt']

[[28,  0,  0,  0,  0],
 [ 0, 47,  0,  6,  0],
 [ 0,  0, 27,  0,  0],
 [ 0,  2,  0, 36,  0],
 [ 0,  0,  0,  0,  5]]
```

## 2. Loss & Accuracy History Across Epochs

| Epoch | Train Loss | Train Acc (%) | Val Loss | Val Acc (%) | Learning Rate |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 01 | 0.5714 | 80.69% | 0.3936 | 84.11% | 1.0e-03 |
| 02 | 0.3534 | 86.60% | 0.2606 | 91.39% | 1.0e-03 |
| 03 | 0.2690 | 90.04% | 0.2998 | 86.09% | 1.0e-03 |
| 04 | 0.2407 | 91.99% | 0.2099 | 90.07% | 1.0e-03 |
| 05 | 0.1602 | 94.01% | 0.4075 | 88.74% | 1.0e-03 |
| 06 | 0.2517 | 90.72% | 0.2760 | 87.42% | 1.0e-03 |
| 07 | 0.1186 | 96.18% | 0.2038 | 91.39% | 1.0e-04 |
| 08 | 0.1038 | 96.18% | 0.1889 | 90.73% | 1.0e-04 |
| 09 | 0.0867 | 97.08% | 0.2038 | 91.39% | 1.0e-04 |
| 10 | 0.0905 | 96.41% | 0.1825 | 92.05% | 1.0e-04 |
| 11 | 0.0752 | 97.53% | 0.1730 | 92.05% | 1.0e-04 |
| 12 | 0.0708 | 97.08% | 0.1987 | 92.72% | 1.0e-04 |
| 13 | 0.0682 | 97.60% | 0.1953 | 92.72% | 1.0e-04 |
| 14 | 0.0612 | 97.75% | 0.1577 | 93.38% | 1.0e-04 |
| 15 | 0.0665 | 97.38% | 0.1739 | 92.72% | 1.0e-04 |
| 16 | 0.0556 | 98.43% | 0.1725 | 94.04% | 1.0e-04 |
| 17 | 0.0538 | 98.20% | 0.1643 | 94.70% ★ | 1.0e-04 |
| 18 | 0.0535 | 98.13% | 0.1987 | 93.38% | 1.0e-04 |
| 19 | 0.0604 | 97.83% | 0.1987 | 92.72% | 1.0e-04 |
| 20 | 0.0550 | 97.83% | 0.1655 | 93.38% | 1.0e-04 |
