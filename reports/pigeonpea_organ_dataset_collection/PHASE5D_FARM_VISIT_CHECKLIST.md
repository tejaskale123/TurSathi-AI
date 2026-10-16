# TurSathi AI — Phase 5D Farm Visit Checklist

**Document Purpose:** Operational logistics checklist and progress-tracking worksheet for planning, executing, and recording pigeonpea field photography visits.  
**Phase:** Phase 5D Field Kit  
**Usage:** Printable operational worksheet for field collection coordinators and agronomists.

---

## 1. Pre-Visit Logistics & Farm Qualification Checklist

Complete these preparation steps at least 48 hours before departing for the farm plots:

- [ ] **Farm Plot Selection & Spatial Separation:**
  - Selected farm is an active pigeonpea (*Cajanus cajan*) cultivation plot.
  - Plot is geographically separated by **at least 5 kilometers** from all other participating collection farms.
  - GPS coordinates of the plot entrance/boundary documented for internal records.
- [ ] **Farmer Coordination & Consent:**
  - Plot owner / cultivator contacted and briefed on project objectives.
  - Verbal or written farmer consent granted to walk field rows and photograph crops.
  - Farmer informed that **no personal data, household faces, or home structures** will be photographed.
- [ ] **Agronomist Scheduling:**
  - Qualified agronomist, plant pathologist, or agricultural extension officer confirmed for on-site visit or scheduled post-visit review.
  - Verifier informed of the 4-class taxonomy (`Tur_Pod`, `Tur_WholePlant_or_Canopy`, `Tur_Leaf`, `Not_Tur_or_Unsupported`).
- [ ] **Hardware & Camera Preparation:**
  - Smartphones or cameras cleaned (lens glass wiped free of farm dust and fingerprints).
  - Storage verified: At least $10\text{ GB}$ of free internal storage per device.
  - Native resolution configured ($\ge 1920 \times 1080$, ideally native sensor resolution).
  - Portrait mode, artificial bokeh, beautification filters, and digital zoom disabled.
  - Backup power: Fully charged power bank and cables packed.
- [ ] **Field Metadata Tools Prepared:**
  - Working copy of [`field_metadata_template.csv`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/reports/pigeonpea_organ_dataset_collection/field_metadata_template.csv) loaded onto a field tablet or printed on paper sheets.
  - Clipboard, waterproof pen, and photo marker tags packed.

---

## 2. On-Farm Execution & Privacy Protocol Checklist

Complete these operational checks while walking field rows:

- [ ] **Time-of-Day Window:** Capturing strictly between **8:30 AM and 4:30 PM** under natural ambient sunlight.
- [ ] **Privacy Guard Enforced:**
  - Zero farmer or bystander faces captured in foreground or background.
  - Zero vehicle registration plates, residential houses, or cattle tags in frame.
  - EXIF location sanitization planned (raw GPS tags to be stripped prior to repository ingestion).
- [ ] **Lighting & Angle Guard:**
  - No direct shooting into the sun (zero lens flare).
  - No operator head, hat, or smartphone shadows falling across target plant tissue.
- [ ] **Focus & Stability:**
  - Lens tapped to lock focus directly on target organ.
  - Every capture reviewed immediately at $100\%$ zoom; blurred or wind-shaken shots deleted and re-taken on the spot.
- [ ] **Anti-Duplicate Discipline:**
  - Maximum 2–3 photos per shrub (`plant_id`).
  - Stance repositioned by at least $45^\circ$ between photos of the same plant.
  - Zero burst captures taken.

---

## 3. Farm Plot Information & Separation Record

Fill out this section upon arriving at each qualified farm plot:

```text
================================================================================
FARM PLOT IDENTIFICATION SHEET
================================================================================
Farm Identifier (e.g. FARM_MAH_01):        _____________________________________
Farm / Village Location (District/Taluka):  _____________________________________
Approximate GPS Center (Internal use):     Lat: ______________ Long: ___________
Distance from Nearest Other Study Plot:    ______ km  (Must be >= 5.0 km)
Pigeonpea Cultivar / Hybrid Variety:       _____________________________________
Crop Sowing Date (if known):               _____________________________________
Predominant Growth Stage:                  [ ] Vegetative        [ ] Flowering
                                           [ ] Pod Filling       [ ] Maturity/Harvest
Soil & Field Context:                      [ ] Black Cotton      [ ] Loamy / Red
Intercropping Context:                     [ ] Pure Tur Stand    [ ] Intercropped Cotton
                                           [ ] Intercropped Soy  [ ] Other: ____________
Lead Photographer Name:                    _____________________________________
Accompanying Agronomist Name:              _____________________________________
================================================================================
```

---

## 4. Empirical Target Accumulation Tracker

Track progress across the 5 required farms to fulfill the minimum Phase 5D quotas:

| Category | Target Quota | Farm 1 | Farm 2 | Farm 3 | Farm 4 | Farm 5 | Total Verified | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`Tur_Pod`** | **$\ge 250$** | _____ | _____ | _____ | _____ | _____ | _____ / 250 | [ ] Met  [ ] Deficit |
| **`Tur_WholePlant_or_Canopy`** | **$\ge 200$** | _____ | _____ | _____ | _____ | _____ | _____ / 200 | [ ] Met  [ ] Deficit |
| **`Not_Tur_or_Unsupported`** | **$\ge 100$** | _____ | _____ | _____ | _____ | _____ | _____ / 100 | [ ] Met  [ ] Deficit |
| **Distinct Qualifying Farms** | **$\ge 5$ plots** | [ ] | [ ] | [ ] | [ ] | [ ] | _____ / 5 | [ ] Met  [ ] Deficit |

*Deficit Rule:* If any category shows a deficit after visiting 5 farms, additional qualifying farms must be scheduled. Model training cannot begin while a deficit exists.

---

## 5. Post-Visit Ingestion & Validation Protocol

Complete immediately upon return from the field:

1. **Backup Raw Files:** Copy photos from mobile device to secure primary and backup storage drives.
2. **Metadata Logging:** Populate [`datasets/pigeonpea_field_collection/field_manifest.csv`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/datasets/pigeonpea_field_collection/field_manifest.csv) with verified records matching the signed Agronomist Verification Forms.
3. **Quarantine Segregation:** Move images marked as `quarantined` to a separate `quarantine/` holding folder.
4. **Automated Audit CLI Verification:**
   Run the repository audit script to programmatically certify dataset readiness:
   ```powershell
   python scripts/audits/validate_pigeonpea_field_collection.py `
     --manifest datasets/pigeonpea_field_collection/field_manifest.csv `
     --image-dir datasets/pigeonpea_field_collection/images/
   ```
5. **Readiness Check:** Confirm output displays:
   `DATASET READY FOR TRAINING: YES [APPROVED]`
