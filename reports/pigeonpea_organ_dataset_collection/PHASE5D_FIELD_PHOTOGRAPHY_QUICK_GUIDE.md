# TurSathi AI — Phase 5D Field Photography Quick Guide

**Document Purpose:** Practical, on-farm reference card for field photographers capturing pigeonpea organ validation imagery.  
**Phase:** Phase 5D Field Kit  
**Target Category Focus:** `Tur_Pod`, `Tur_WholePlant_or_Canopy`, `Not_Tur_or_Unsupported` (Negative/OOD classes).  
**Source Documents:**
* Protocol: [`reports/pigeonpea_organ_dataset_collection/PHASE5D_FIELD_COLLECTION_PROTOCOL.md`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/reports/pigeonpea_organ_dataset_collection/PHASE5D_FIELD_COLLECTION_PROTOCOL.md)
* Design Report: [`reports/pigeonpea_organ_validator_design/PHASE5D_A_DESIGN_REPORT.md`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/reports/pigeonpea_organ_validator_design/PHASE5D_A_DESIGN_REPORT.md)

---

## 1. How the Target Classes Differ

The existing TurSathi AI disease model already possesses $\sim 1,800$ close-up leaf images. This collection campaign specifically targets the non-leaf structures that currently confuse the classifier:

| Class | What to Photograph | Camera Distance | Visual Hierarchy Rule | Target Action |
| :--- | :--- | :---: | :--- | :--- |
| **`Tur_Pod`** *(Priority Target)* | Pod clusters, developing green pods, striated pods, dry mature pods, flower racemes. | **$15\text{ cm} - 35\text{ cm}$** | Pods or flowers must occupy **$\ge 30\%$ of foreground** or form the primary focal point of the shot. Overrides background leaves. | Rejected at Stage 4 with pod diagnostic message. |
| **`Tur_WholePlant_or_Canopy`** *(Priority Target)* | Whole shrub architecture, branching structure, lateral canopy spread, distant crop rows. | **$> 1.0\text{ meter}$**<br>*(typically $1.0\text{ m} - 2.5\text{ m}$)* | Individual leaf surfaces must occupy **$< 15\%$ of image area**. Captures the whole bush from soil to apex. | Rejected at Stage 4 with step-closer guidance message. |
| **`Not_Tur_or_Unsupported`** *(Priority Target)* | Companion crops (cotton, soybean, sorghum), field weeds (parthenium), bare soil, farm implements. | Varies by subject<br>*(typically $30\text{ cm} - 1.5\text{ m}$)* | Non-pigeonpea flora or non-plant subjects. | Rejected at Stage 4 with unsupported crop message. |
| **`Tur_Leaf`** *(Reference Only)* | Close-up view of pigeonpea foliar tissue suitable for disease diagnosis. | **$< 40\text{ cm}$**<br>*(typically $20\text{ cm} - 30\text{ cm}$)* | Leaf laminae clearly resolvable; individual leaflet or small cluster occupying **$\ge 60\%$ of foreground area**. | Passes to 5-Class Disease Predictor. |

> [!WARNING]
> **Provisional Guidance Notice:**
> Distances below $10\text{ cm}$ (macro lens) or above $4.0\text{ meters}$ (panoramic landscape) are **provisional** and must be noted in the manifest `notes` field for agronomist review.

---

## 2. On-Farm Photography Rules (Cheat Sheet)

### A. Focus and Sharpness
* **Tap-to-Focus:** Always tap your smartphone screen directly on the pod surface or target branch before capturing.
* **Inspect Every Shot:** Zoom in on your screen immediately after shooting. If hand jitter, motion blur, or wind shake is visible, **delete and re-shoot immediately**.
* **Wind Handling:** Wait for wind lulls. If branches sway continuously, gently steady the main stem below the focal zone, keeping your hand outside the frame.

### B. Lighting and Sun Position
* **Golden Window:** Photograph strictly between **8:30 AM and 4:30 PM** under natural daylight.
* **Sun Behind You:** Never point the camera lens directly into the sun. Position yourself so sunlight illuminates the subject from the side or over your shoulder.
* **No Operator Shadows:** Ensure your head, body, hat, or phone shadow does not fall across the target pods or foliage.

### C. Framing & Natural Field Background
* **Natural Context:** Keep background authentic (farm soil, adjacent branches, sky, weeds). Do not use white cardboard, black cloth, or paper backgrounds.
* **No Hands or Personal Objects:** Do not hold pods with fingers or tools inside the frame. The camera must capture the plant growing naturally on its stem.
* **Disable Beauty/Portrait Filters:** Turn off portrait mode, artificial background blur (bokeh), HDR exaggeration, and digital zoom. Capture native resolution optical files.

### D. Duplicate-Photo Prevention
The automated validation script calculates SHA-256 hashes and will reject exact or near duplicates:
* **No Burst Captures:** Never hold the shutter button to take 5 rapid burst shots.
* **Angle Rule:** Take at most 2–3 photos from the same shrub (`plant_id`). You **must move your physical standing position by at least $45^\circ$** between photos.

---

## 3. Resolving Tricky Field Situations

| What You See in the Field | Correct Classification | What to Do |
| :--- | :--- | :--- |
| Branch has 3 green pods and 4 healthy leaves together. | **`Tur_Pod`** | Apply the Reproductive Priority Rule: If pods occupy $\ge 30\%$ area or form the primary focus, classify as `Tur_Pod`. |
| Shrub is 2 meters tall, but you stand 2 meters away to capture the whole bush. | **`Tur_WholePlant_or_Canopy`** | Stand back $1.0\text{ m} - 2.5\text{ m}$. Frame the full shrub architecture. Do not label as pod even if small pods are visible on branches. |
| You see a weed (e.g. Congress grass / Parthenium) growing between pigeonpea rows. | **`Not_Tur_or_Unsupported`** | Frame the weed clearly. These negative distractors teach the model to reject non-tur vegetation. |
| Leaves have dark spots or yellowing. | **`Tur_Leaf`** *(or Quarantine)* | If capturing close-up foliar tissue, verify lamina fills $\ge 60\%$ frame. Do NOT label with disease names unless pathology is certified. |
| Framing is borderline (50% pod, 50% leaf, unclear dominance). | **`quarantined`** | In manifest, set `verification_status = "quarantined"`. Move image to quarantine folder for panel review. |

---

## 4. Items Requiring Formal Agronomist Confirmation

Before final ingestion, field photographers must confirm with the reviewing agronomist:
1. **Pod Maturation Ratio:** Confirm the desired proportion of green immature pods versus dried brown harvest pods across the target plots.
2. **Cultivar Peculiarities:** Check if local varieties (e.g., BDN-711, BSMR-736) exhibit dark purple streaks on pods that could be mistaken for disease necrosis.
3. **Distance Boundary Acceptance:** Confirm that the $15\text{ cm} - 35\text{ cm}$ pod distance and $1.0\text{ m} - 2.5\text{ m}$ canopy distance meet local agronomic classification standards.
