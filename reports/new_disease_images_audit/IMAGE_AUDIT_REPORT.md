# TurSathi AI — Audit of `datasets/new_disease_images/`

---

## 1. Executive Summary

A forensic, read-only audit of the 42 items in [`datasets/new_disease_images/`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/datasets/new_disease_images) was conducted. 

### Key Findings:
- **Total Files:** 42 items (41 decodable image files, 1 zero-byte non-image file).
- **Decodable Images:** 41 files (36 JPEG, 4 PNG, 1 WebP).
- **Non-Image Items:** 1 file (`new_disease_images`, 0 bytes).
- **Internal Exact Duplicates:** **5 duplicate groups** containing **10 files** (5 redundant copies).
- **Unique Decodable Images:** **36 unique images**.
- **Dataset Overlap:** **0 overlaps** with [`datasets/pigeonpea_disease_final/`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/datasets/pigeonpea_disease_final) and **0 overlaps** with [`datasets/pigeonpea_disease_clean_candidate_v1/`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/datasets/pigeonpea_disease_clean_candidate_v1).
- **Image Provenance:** Strong, confirmed evidence that the collection consists of **web-scraped, search-engine-downloaded, clipboard-pasted, and academic publication figures**, rather than direct farmer real-field photographs.

---

## 2. Inventory & Format Breakdown

The complete per-file inventory is saved in [`reports/new_disease_images_audit/image_inventory.csv`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/reports/new_disease_images_audit/image_inventory.csv).

| Metric | Count | Details |
|---|:---:|---|
| **Total Files** | 42 | 41 images, 1 zero-byte file |
| **JPEG (`.jpg`)** | 36 | File sizes range from 20.0 KB to 92.2 KB |
| **PNG (`.png`)** | 4 | File sizes range from 40.7 KB to 518.8 KB |
| **WebP (`.webp`)** | 1 | File size: 43.6 KB |
| **No Extension** | 1 | `new_disease_images` (0 bytes, invalid/empty) |
| **Color Space** | 41 RGB | All 41 decodable images decode in standard 3-channel RGB mode |
| **EXIF Camera Data** | 0 / 41 | **0 images possess camera metadata** (no make, model, shutter, lens, or GPS) |

---

## 3. Exact Duplicate Groups (Internal to `new_disease_images`)

Using cryptographic SHA-256 hashes, **5 pairs of byte-for-byte exact duplicates** (10 files total) were identified:

| Group | SHA-256 Prefix | Duplicate Filenames | Dimensions | File Size |
|:---:|---|---|:---:|:---:|
| **1** | `cbb731eb1f8876c2...` | `image.png`<br>`image copy.png` | $335 \times 597$ | 310,702 bytes |
| **2** | `0c6a858e775196f7...` | `images (3).jpg`<br>`images (10).jpg` | $335 \times 597$ | 55,914 bytes |
| **3** | `3f7be737fb12217c...` | `images (15).jpg`<br>`images (17).jpg` | $335 \times 597$ | 65,948 bytes |
| **4** | `9195b035179294e5...` | `images (18).jpg`<br>`images (23).jpg` | $316 \times 632$ | 56,985 bytes |
| **5** | `1a7fec062ddcc729...` | `images (9).jpg`<br>`images (20).jpg` | $335 \times 597$ | 45,037 bytes |

---

## 4. Dataset Overlap Audit

Cross-referencing the SHA-256 hashes of all 42 files against the existing repositories:
- **Overlap with Original Dataset (`datasets/pigeonpea_disease_final/` — 1,858 images):** **0 files (0.0%)**.
- **Overlap with Clean Candidate Dataset (`datasets/pigeonpea_disease_clean_candidate_v1/` — 1,676 images):** **0 files (0.0%)**.

*Fact:* None of these 42 files have ever been used in the project's training, validation, or holdout test splits.

---

## 5. Provenance & Origin Analysis: Facts vs. Observations

### A. Confirmed Facts (Reliable Evidence)
1. **Academic Publication Figures:**
   - `488313_0_En_25-1_Fig1_HTML.jpg`: Matches standard Springer Nature digital publication figure naming schema (`ArticleID_Language_Chapter/Article_Fig#_HTML.jpg`).
   - `AAlternaria-blight-symptom-on-leaves-and-B-aerial-plant-parts-leaves-stem-buds-and.webp`: Uses standard ResearchGate / scientific repository slug syntax describing multi-panel scientific figures (Panels A & B: "Alternaria blight symptom on leaves and aerial plant parts..."). Note: *Alternaria blight* is not one of TurSathi's five classified diseases.
2. **Online Educational / Reference Image:**
   - `Pigeon pea plant in fruit, Kitui, Kenya. In this form, the pods have striations. © Maundu, 2021.jpg`: Explicitly named with copyright attribution (`© Maundu, 2021`) and locality (`Kitui, Kenya`), tracing to open agroforestry / Wikimedia documentation.
3. **Browser Bulk Downloads:**
   - 34 files follow the pattern `images.jpg`, `images (1).jpg` through `images (33).jpg`. This is the signature default filename generated when saving multiple images in Chromium/Google Chrome from Google Images.
4. **Clipboard / Operating System Copies:**
   - `image.png`, `image copy.png`, `image copy 2.png` represent clipboard paste or local file duplication conventions.
   - `64c83c99-f128-4a18-b6d0-1fcfc8ed6e84.png` uses a cloud-storage / CMS UUID identifier.
5. **Absence of Camera EXIF:**
   - All 41 decodable images lack camera hardware metadata, timestamps, exposure settings, or GPS geolocation, which is typical for web-compressed and browser-downloaded media.
6. **Low Resolution & Web Dimensions:**
   - 12 images share identical web-thumbnail dimensions ($335 \times 597$).
   - Multiple images have low resolutions under $500 \times 500$ px (e.g. $281 \times 209$, $300 \times 400$, $350 \times 240$), characteristic of web thumbnails rather than raw mobile camera captures.

### B. Uncertain Observations (Do Not Assume Without Ground Truth)
- **Disease Pathology:** While filenames like `AAlternaria-blight...` reference plant pathology, the actual disease, crop variety, and pathology shown in the remaining 34 `images (*).jpg` files cannot be verified from filenames alone.
- **Geographic Representation:** None of these images have confirmed provenance from Maharashtra pigeonpea fields. `Pigeon pea plant in fruit... Kitui, Kenya` indicates non-Indian geographical origin for at least one file.
- **Absence of Ground-Truth Annotations:** No accompanying agricultural expert annotations or diagnostic lab reports exist for this folder.

---

## 6. Suitability Evaluation

### ❌ Real-Field Shadow Testing: **NOT SUITABLE**
**Rationale:**
1. **Lack of Verified Ground-Truth:** Shadow testing against these images cannot measure accuracy, sensitivity, or specificity because true clinical labels are unknown.
2. **Out-of-Scope Pathology:** Images like *Alternaria blight* or Kenyan pod cultivars introduce diseases and plant parts outside the 5-class leaf disease scope (`Healthy`, `Leaf_Spot`, `Leaf_webber`, `Sterilic_mosaic`, `Wilt`).
3. **Web Artifacts & Duplication:** 10 of the 41 images are duplicates; low-resolution web thumbnails do not reflect the camera sensor, focal distance, lighting, and compression characteristics of real farmer mobile devices in Vidarbha/Marathwada.
4. **Validating on Web Downloads Risks Misleading Metrics:** Agreement between production and experimental models on web downloads does not validate real-world agricultural effectiveness.

### ⚠️ Exploratory Stress Testing / Out-of-Distribution Diagnostics: **SUITABLE WITH CAVEATS**
**Rationale:**
- These images can serve as a qualitative "stress test" to observe how both models respond to noisy, diverse, out-of-distribution web images (e.g., checking if the model produces overconfident misdiagnoses on uncataloged diseases like Alternaria).
- Such tests must be reported purely as exploratory behavior, **never as a benchmark of model accuracy**.

---

## 7. Recommendations

1. **Do not use `datasets/new_disease_images/` as a real-field shadow test benchmark.**
2. **Keep `datasets/pigeonpea_real_field_shadow_v1/` reserved** for verified, raw mobile photographs captured directly in pigeonpea fields, accompanied by expert ground-truth labels.
3. If exploratory testing of `new_disease_images` is desired, deduplicate the 5 duplicate pairs first and evaluate in qualitative comparison mode only.
