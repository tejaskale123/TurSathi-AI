# TurSathi AI — Unsupported Pigeonpea Diseases & Non-Leaf Organ Governance Guide

**Document ID:** `GUIDE-V4-OOD-ORGAN-01`  
**Location:** `ml/retraining/validator_v4/UNSUPPORTED_DISEASES_AND_ORGAN_HANDLING_GUIDE.md`  
**Scope:** Architecture, labeling policy, and diagnostic routing for unsupported pigeonpea pathologies and plant organs.  

---

## 1. The Core Scientific Dilemma

Pigeonpea (*Cajanus cajan*, Tur/Arhar) in Maharashtra fields is susceptible to over 20 distinct fungal, viral, and bacterial pathologies. 
TurSathi AI explicitly targets **five canonical classes**:
1. `Healthy`
2. `Leaf_Spot` (*Cercospora indica*)
3. `Leaf_webber` (*Cydia critica* / *Maruca vitrata*)
4. `Sterilic_mosaic` (Pigeonpea sterility mosaic virus, SMD)
5. `Wilt` (*Fusarium udum*)

### The Diagnostic Failure Mode Observed in Testing:
When unsupported pathologies (such as *Alternaria blight*, *Phytophthora stem blight*, or *Macrophomina collar rot*) or non-leaf organs (seed pods, woody stems, flowers) are uploaded:
- **The Upstream Validator (`TurImageValidator`):** Identifies the plant tissue as pigeonpea (`is_tur = True`).
- **The Closed-Set Disease Classifier (`TurDiseasePredictor`):** Softmax forces the 1280-D embedding into one of the 5 closed classes.
- **The Wilt Sinkhole:** Because Wilt training samples contain brown, necrotic canopy foliage and branches (unlike the green foliar surfaces of Leaf Spot or SMD), any uncataloged necrotic leaf or woody pod activates the **Wilt** feature weights, producing $\mathbf{>90\%}$ **false Wilt confidence**.

---

## 2. Policy: Why Unsupported Pathologies Must NOT Be Labeled as `Not_Tur`

A common but fatal machine learning error is to throw all unsupported diseases into the negative `Not_Tur` training folder. 

### Why This Destroys Model Performance:
1. **Contradictory Morphological Features:** An Alternaria-infected leaf has identical venation, trifoliate leaf margin, and stipule geometry to a Cercospora leaf spot. Forcing the binary validator to classify it as `Not_Tur` causes severe label noise and gradient thrashing.
2. **False Rejection of Genuine Crops:** If the model learns that a pigeonpea leaf with irregular brown necrosis is `Not_Tur`, it will falsely reject real farmer pigeonpea leaves that have mixed symptoms.
3. **Loss of Agronomic Context:** Telling a farmer *"This is not a pigeonpea plant"* when they photograph their actual pigeonpea crop destroys trust in the tool.

---

## 3. The 4-Stage Hierarchical Solution Architecture

Rather than forcing a single model to solve crop identity, organ discrimination, disease classification, and anomaly detection simultaneously, TurSathi AI enforces a **strict 4-stage pipeline**:

```
[Uploaded Image / Camera Frame]
              │
              ▼
STAGE 1: Technical Quality & Integrity Gate (tur_image_gate.py)
├── Resolution Floor: width >= 224, height >= 224
├── Laplacian Blur Variance: score >= 100.0 (rejects motion blur)
└── Exposure Range: brightness in [20, 240], contrast >= 15.0
              │
              ▼
STAGE 2: Upstream Organ & Crop Validator (Validator v4)
├── Class 0 (Not_Tur): Weeds, other crop leaves (cotton, soybean, maize), soil, hands
├── Class 1 (Tur_Leaf): Genuine pigeonpea foliage (healthy or diseased)
└── Organ Rejection: Seed pods, woody stalks, and roots are rejected at this stage
     └── Response: "Pigeonpea pod/stalk detected. Please photograph an individual leaf."
              │
              ▼
STAGE 3: Closed-Set Disease Model (Candidate EfficientNet-B0)
├── Extracts 1280-D latent feature vector
└── Computes softmax logits across the 5 canonical classes
              │
              ▼
STAGE 4: Multi-Layer Out-of-Distribution (OOD) Guard (tur_predictor.py)
├── 1. Centroid Cosine Distance Gate: dist <= class_threshold
├── 2. Softmax Confidence Floor: confidence >= 0.70
└── 3. Top-1 vs. Top-2 Margin Floor: margin >= 0.20
              │
              ├── IF ALL GATES PASS:
              │     └── Returns Confirmed Diagnosis (HTTP 200)
              │
              └── IF OOD DISTANCE EXCEEDED (e.g. Alternaria Blight):
                    └── Intercepts prediction before persisting to DB
                    └── Rejects with HTTP 422 ("unsupported_disease")
                    └── Emits Marathi Guidance:
                        "हा फोटो तुरीच्या पानाचा आहे, परंतु हे लक्षण तूर साथीच्या ५ मुख्य 
                         रोगांपेक्षा वेगळे (उदा. अल्टरनेरिया किंवा फायटोप्थोरा) असू शकते. 
                         कृपया जवळच्या कृषी विज्ञान केंद्राचा सल्ला घ्या."
```

---

## 4. Operational Classification of Problematic Repository Samples

| Sample File | True Botanical Identity | Correct Verified Label | Correct Stage Handling |
| :--- | :--- | :--- | :--- |
| `Pigeon pea plant in fruit, Kitui, Kenya...jpg` | Genuine pigeonpea plant with striated seed pods. | `Tur_Non_Leaf_Organ` (`pigeonpea_pod`) | **Stage 2 Rejection:** Blocked by organ validator as non-foliar material. |
| `AAlternaria-blight-symptom-on-leaves...webp` | Genuine pigeonpea leaves with Alternaria blight. | `Tur_Unsupported_Disease` | **Stage 2:** Passes as Tur Leaf.<br>**Stage 4:** Blocked by OOD centroid distance ($\text{dist} > 0.40$). |
| `488313_0_En_25-1_Fig1_HTML.jpg` | Springer Nature scientific figure with text and letters. | `Not_Tur` (`academic_figure`) | **Stage 2 Rejection:** Blocked by validator as non-crop clutter. |
| `realworld_nottur_01.png` - `09.png` | Cotton, soybean, and weed foliage. | `Not_Tur` (`other_crop_leaf`) | **Stage 2 Rejection:** Blocked by validator as non-Tur species. |

---

## 5. Reviewer Protocol for New Field Submissions

When human agronomists review incoming candidate images in `ml/retraining/validator_v4/hard_negative_collection_manifest.json`:

1. **Rule 1 (Leaf Verification):** If the image depicts whole bushes, pods, or bare stalks, set `organ_category = "pigeonpea_pod"` or `"pigeonpea_stem_root"`. Set `verified_label = "Tur_Non_Leaf_Organ"`. Do NOT set `verified_label = "Not_Tur"`.
2. **Rule 2 (Unknown Pathology):** If the leaf is undeniably pigeonpea but exhibits symptoms inconsistent with Cercospora, SMD, Webber, or Fusarium Wilt (e.g. concentric zonate rings indicating Alternaria), set `organ_category = "unsupported_pigeonpea_disease"` and `verified_label = "Tur_Unsupported_Disease"`.
3. **Rule 3 (Weeds & Clutter):** If the image depicts field weeds, non-legume plants, soil, hands, boots, or equipment, set `verified_label = "Not_Tur"` and assign the appropriate `organ_category`.
4. **Rule 4 (Duplicate Tracking):** If the image is a duplicate or slight crop of an existing image, record its `duplicate_group_id`. Never assign duplicate group members to different splits.
