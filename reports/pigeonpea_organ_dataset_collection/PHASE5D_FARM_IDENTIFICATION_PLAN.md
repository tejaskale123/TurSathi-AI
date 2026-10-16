# TurSathi AI — Phase 5D Farm Identification and Visit Planning Document

**Document Title:** Farm Plot Identification, Spatial Separation Protocol, and Field Visit Schedule  
**Document Phase:** Phase 5D Field Kit (Planning Only)  
**Date:** 2026-10-14  
**Status:** Operational Planning Template (Blank / Unscheduled)  
**Strict Rule:** This is strictly an operational planning template. **No real farms, coordinates, farmer permissions, or agronomist commitments are claimed or prefilled.** All records remain blank pending real-world scheduling by the project owner.

---

## 1. Candidate Farm Plots Planning Table

Use this planning sheet to record candidate farm plots during preliminary field scouting. A minimum of 5 qualifying plots must be confirmed prior to conducting data collection:

| Farm ID | Target Village / Taluka | Regional District | Actual Coordinates (Lat, Long) | Tur Crop Presence & Stage | Farmer Permission Status | Agronomist Availability | Farm Visit Status |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **`FARM_01`** | `[Village 1]` | `[District]` | `(__.____, __.____)` | [ ] Flowering<br>[ ] Pod Filling<br>[ ] Maturing | [ ] Pending<br>[ ] Granted<br>[ ] Denied | [ ] Confirmed<br>[ ] Tentative<br>[ ] Unavailable | [ ] Candidate<br>[ ] Scheduled<br>[ ] Completed |
| **`FARM_02`** | `[Village 2]` | `[District]` | `(__.____, __.____)` | [ ] Flowering<br>[ ] Pod Filling<br>[ ] Maturing | [ ] Pending<br>[ ] Granted<br>[ ] Denied | [ ] Confirmed<br>[ ] Tentative<br>[ ] Unavailable | [ ] Candidate<br>[ ] Scheduled<br>[ ] Completed |
| **`FARM_03`** | `[Village 3]` | `[District]` | `(__.____, __.____)` | [ ] Flowering<br>[ ] Pod Filling<br>[ ] Maturing | [ ] Pending<br>[ ] Granted<br>[ ] Denied | [ ] Confirmed<br>[ ] Tentative<br>[ ] Unavailable | [ ] Candidate<br>[ ] Scheduled<br>[ ] Completed |
| **`FARM_04`** | `[Village 4]` | `[District]` | `(__.____, __.____)` | [ ] Flowering<br>[ ] Pod Filling<br>[ ] Maturing | [ ] Pending<br>[ ] Granted<br>[ ] Denied | [ ] Confirmed<br>[ ] Tentative<br>[ ] Unavailable | [ ] Candidate<br>[ ] Scheduled<br>[ ] Completed |
| **`FARM_05`** | `[Village 5]` | `[District]` | `(__.____, __.____)` | [ ] Flowering<br>[ ] Pod Filling<br>[ ] Maturing | [ ] Pending<br>[ ] Granted<br>[ ] Denied | [ ] Confirmed<br>[ ] Tentative<br>[ ] Unavailable | [ ] Candidate<br>[ ] Scheduled<br>[ ] Completed |
| **`FARM_06`** *(Backup)* | `[Village 6]` | `[District]` | `(__.____, __.____)` | [ ] Flowering<br>[ ] Pod Filling<br>[ ] Maturing | [ ] Pending<br>[ ] Granted<br>[ ] Denied | [ ] Confirmed<br>[ ] Tentative<br>[ ] Unavailable | [ ] Candidate<br>[ ] Scheduled<br>[ ] Completed |

---

## 2. Spatial Separation Verification Method ($\ge 5\text{ km}$ Rule)

To prevent localized environmental bias and spatial correlation, all selected farm plots must be geographically separated by **at least 5.0 kilometers**.

### 2.1 Coordinate Verification Protocol
1. Record the decimal latitude and longitude $(\phi, \lambda)$ at the entrance/center of each plot using a standard smartphone GPS tool.
2. For every pair of candidate farms $(A, B)$, compute the great-circle surface distance using the **Haversine Formula**:

$$a = \sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta \lambda}{2}\right)$$
$$c = 2 \cdot \text{atan2}\left(\sqrt{a}, \sqrt{1-a}\right)$$
$$d = R \cdot c \quad \text{where } R = 6,371\text{ km}$$

### 2.2 Pairwise Distance Verification Matrix (Fill upon coordinate logging)

Every cell between distinct farms must satisfy $d \ge 5.0\text{ km}$:

| Plot ID | `FARM_01` | `FARM_02` | `FARM_03` | `FARM_04` | `FARM_05` |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **`FARM_01`** | — | ____ km | ____ km | ____ km | ____ km |
| **`FARM_02`** | — | — | ____ km | ____ km | ____ km |
| **`FARM_03`** | — | — | — | ____ km | ____ km |
| **`FARM_04`** | — | — | — | — | ____ km |
| **`FARM_05`** | — | — | — | — | — |

*Spatial Qualification Check:*
* [ ] All pairwise distances confirmed $\ge 5.0\text{ km}$ by coordinator. Date: _______________

---

## 3. Proposed Field Visit Schedule

| Visit Phase | Target Farm ID | Scheduled Date | Lead Photographer | Accompanying Agronomist | Expected Quota Focus | Contingency Backup Date |
| :---: | :---: | :---: | :--- | :--- | :--- | :---: |
| **Visit 1** | `FARM_01` | `YYYY-MM-DD` | ____________________ | ____________________ | Pods + Canopy + Distractors | `YYYY-MM-DD` |
| **Visit 2** | `FARM_02` | `YYYY-MM-DD` | ____________________ | ____________________ | Pods + Canopy + Distractors | `YYYY-MM-DD` |
| **Visit 3** | `FARM_03` | `YYYY-MM-DD` | ____________________ | ____________________ | Pods + Canopy + Distractors | `YYYY-MM-DD` |
| **Visit 4** | `FARM_04` | `YYYY-MM-DD` | ____________________ | ____________________ | Pods + Canopy + Distractors | `YYYY-MM-DD` |
| **Visit 5** | `FARM_05` | `YYYY-MM-DD` | ____________________ | ____________________ | Pods + Canopy + Distractors | `YYYY-MM-DD` |
| **Review** | *All Plots* | `YYYY-MM-DD` | ____________________ | ____________________ | Agronomist Sign-Off Audit | `YYYY-MM-DD` |

---

## 4. Per-Farm Quota Allocation & Progress Tracker

To ensure balanced data distribution across all 5 farms without over-representing a single parcel:

| Category | Recommended Target per Farm | `FARM_01` Verified | `FARM_02` Verified | `FARM_03` Verified | `FARM_04` Verified | `FARM_05` Verified | Total Cumulative Verified | Minimum Required Target | Threshold Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`Tur_Pod`** | **$\sim 50$ images** | _____ | _____ | _____ | _____ | _____ | _____ | **$\ge 250$** | [ ] Met [ ] Deficit |
| **`Tur_WholePlant_or_Canopy`** | **$\sim 40$ images** | _____ | _____ | _____ | _____ | _____ | _____ | **$\ge 200$** | [ ] Met [ ] Deficit |
| **`Not_Tur_or_Unsupported`** | **$\sim 20$ images** | _____ | _____ | _____ | _____ | _____ | _____ | **$\ge 100$** | [ ] Met [ ] Deficit |
| **Target Plants per Farm** | **$\ge 10$ distinct shrubs** | _____ | _____ | _____ | _____ | _____ | _____ | **$\ge 50$ shrubs** | [ ] Met [ ] Deficit |

*Deficit Management:* If any farm under-delivers (e.g., due to early harvesting or crop damage), the deficit must be redistributed across remaining farms or an additional candidate farm (`FARM_06`) must be scheduled.

---

## 5. Pre-Visit Readiness Checklist

Verify all items 24 hours prior to field departure:

- [ ] **Farmer Access Confirmed:** Contacted the cultivator within 24 hours to confirm plot availability.
- [ ] **Agronomist Availability Confirmed:** Reviewing agronomist confirmed attendance on-site or scheduled for batch verification review.
- [ ] **Weather Forecast Inspection:** Clean sunny/partly cloudy weather forecasted between 8:30 AM and 4:30 PM (zero rain/fog).
- [ ] **Camera Device Readiness:** Storage cleared ($\ge 10\text{ GB}$), lenses cleaned, native resolution checked, beauty/portrait mode disabled.
- [ ] **Power Reserves:** Smartphone battery $100\%$ charged; external power bank ($> 10,000\text{ mAh}$) charged and packed.
- [ ] **Physical Manifest & Forms:** Clean printouts of [`PHASE5D_AGRONOMIST_VERIFICATION_FORM.md`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/reports/pigeonpea_organ_dataset_collection/PHASE5D_AGRONOMIST_VERIFICATION_FORM.md) and [`PHASE5D_FARM_VISIT_CHECKLIST.md`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/reports/pigeonpea_organ_dataset_collection/PHASE5D_FARM_VISIT_CHECKLIST.md) packed.

---

## 6. Mandatory Criteria for Postponing a Farm Visit

A field visit must be **immediately postponed or cancelled** if any of the following conditions arise:

1. **Adverse Weather / Poor Light:** Heavy rain, severe overcast darkness, thick ground fog, or dust storms that reduce ambient light below acceptable optical thresholds.
2. **Crop Unavailability / Sudden Harvest:** The farmer has prematurely harvested the crop, pruned the branches, or sprayed dense chemical residues that mask natural morphology.
3. **Severe Pest Devastation / Crop Flattening:** Extreme hail or localized lodging has destroyed natural shrub architecture across the plot.
4. **Farmer Permission Revocation:** The plot owner or manager withdraws consent or requests rescheduling.
5. **Absence of Qualified Agronomist:** If the agronomist cannot accompany the team or cannot commit to inspecting the batch within 48 hours of capture.
6. **Hardware Malfunction:** Smartphone camera optical sensor damage, lens scratching, or persistent focus-hunting failure.

---

## 7. Verification and Planning Disclaimer

> [!NOTE]
> **Planning Document Notice:**  
> This file is strictly an operational schedule and planning template.
> * Zero farm visits have taken place as of this document’s creation.
> * Zero GPS coordinates or farm agreements have been finalized.
> * Current verified collection counts across all categories remain at **0 (Zero)**.
> * Model training and live integration remain strictly on hold until real farm visits produce agronomist-verified data certified by [`scripts/audits/validate_pigeonpea_field_collection.py`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/scripts/audits/validate_pigeonpea_field_collection.py).
