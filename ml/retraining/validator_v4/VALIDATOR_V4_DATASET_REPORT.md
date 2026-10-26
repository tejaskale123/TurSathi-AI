# TurSathi AI — Validator v4 Dataset Integrity & Leakage Audit Report

**Date:** 2026-10-26 14:00:18  
**Source Dataset:** `datasets/tur_image_validator_v3/`  
**Manifest Path:** `ml/retraining/validator_v4/validator_v4_manifest.json`  

---

## 1. Executive Summary

A forensic cryptographic audit was conducted on `datasets/tur_image_validator_v3/`.
The audit uncovered that **100% of the Tur images in the original validation and test sets were exact duplicates of the training set**, explaining why previous evaluation reports claimed an unrealistic 100% accuracy.

This script constructed a clean, deduplicated, stratified split manifest (`validator_v4_manifest.json`) guaranteeing **0% cross-split leakage**.

---

## 2. Leakage Analysis in Original v3 Dataset

| Metric | Measured Value | Forensic Finding |
| :--- | :---: | :--- |
| **Total Files in v3** | 3561 | Includes exact redundant copies |
| **Unique Image Hashes** | 3301 | True distinct photographic images |
| **Tur Val in Train Leakage** | **127 / 127 (100.0%)** | Every single Tur validation image existed in train |
| **Tur Test in Train Leakage** | **133 / 133 (100.0%)** | Every single Tur test image existed in train |
| **Class Label Conflicts** | 0 | Identical hashes assigned to conflicting classes |

---

## 3. Clean Stratified Split Manifest (v4 Leak-Free)

Partitioned using stratified random sampling with fixed seed (`42`):

| Split | Tur (Positive) | Not_Tur (Negative) | Total Images | Proportion | Cross-Split Leakage |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Train** | 1106 | 1204 | **2310** | 70% | **0%** |
| **Validation** | 237 | 258 | **495** | 15% | **0%** |
| **Test (Untouched Holdout)** | 238 | 258 | **496** | 15% | **0%** |
| **Total Clean** | **1581** | **1720** | **3301** | 100% | **0%** |

---

## 4. Audit of `datasets/new_disease_images/` (41 items)

1. Contains **5 internal duplicate pairs** (36 unique image hashes).
2. Contains confirmed genuine pigeonpea: `Pigeon pea plant in fruit, Kitui, Kenya. In this form, the pods have striations. © Maundu, 2021.jpg`.
3. Contains pigeonpea Alternaria blight (`AAlternaria-blight-symptom-on-leaves...`).
4. **Conclusion:** Cannot be automatically relabeled as `Not_Tur` negatives. Doing so would train the model to reject real pigeonpea pods and non-target diseases as 'Not_Tur'.
