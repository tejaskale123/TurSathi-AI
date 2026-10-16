# TurSathi AI — Phase 5D Agronomist Verification Form

**Form Purpose:** Standard printable review sheet for qualified agronomists to independently examine, classify, and verify field-collected pigeonpea organ photographs.  
**Phase:** Phase 5D Field Kit  
**Usage:** Printable blank evaluation template. Fill out one section per image review session or batch.  
**Strict Rule:** No prefilled fake names, simulated credentials, or mock approvals. Only authentic agronomist sign-offs are valid.

---

## 1. Review Session Header (To be completed by Verifier)

* **Review Date (`YYYY-MM-DD`):** _______________________________________
* **Review Location / Laboratory:** _______________________________________
* **Display / Hardware Device Used:** [ ] Calibrated Monitor  [ ] Tablet / Screen  [ ] Other: _________________
* **Batch / Folder Reference:** _______________________________________
* **Total Image Files Examined in Session:** ___________________

---

## 2. Individual Image Review & Decision Protocol

For each image file, inspect the high-resolution photograph alongside its manifest metadata row and complete the evaluation below:

```text
================================================================================
IMAGE VERIFICATION RECORD
================================================================================

1. IMAGE IDENTIFIERS:
   Filename:          __________________________________________________________
   Plant ID:          ____________________     Farm ID: ________________________
   Capture Date:      ____________________     Cultivar: _______________________

2. SPECIES CONFIRMATION:
   Is the plant confirmed as Cajanus cajan (Pigeonpea / Tur)?
   [ ] YES — Species Confirmed
   [ ] NO  — Non-pigeonpea species / Unsupported weed or crop
   [ ] UNCERTAIN — Requires field re-examination

3. MORPHOLOGICAL CLASS DECISION (Check exactly ONE):
   [ ] Tur_Leaf                   (Close-up foliar lamina, >= 60% area, < 40 cm)
   [ ] Tur_Pod                    (Pod cluster / flowers, >= 30% area or focal)
   [ ] Tur_WholePlant_or_Canopy   (Full shrub architecture, > 1.0 m distance)
   [ ] Not_Tur_or_Unsupported     (Weeds, intercrops, soil, farm implements)

4. IMAGE QUALITY & DIAGNOSTIC USABILITY:
   - Sharpness & Focus:           [ ] PASS (Sharp)       [ ] FAIL (Motion / Defocus blur)
   - Lighting & Glare:            [ ] PASS (Clear)       [ ] FAIL (Severe flare / Shadow)
   - Background Authenticity:     [ ] PASS (Natural farm)[ ] FAIL (Artificial backdrop)
   - Artifact / Privacy Check:    [ ] PASS (Clean)       [ ] FAIL (Human hands / Faces)

5. FINAL VERIFICATION STATUS (Check exactly ONE):
   [ ] VERIFIED     — Meets all species, class, and quality criteria.
                      Eligible for model training dataset.

   [ ] QUARANTINED  — Ambiguous framing, mixed pod/leaf dominance, or borderline distance.
                      Quarantined away from training pool until panel review.

   [ ] REJECTED     — Unusable blur, severe distortion, accidental duplicate, or invalid input.
                      Permanently excluded from dataset.

6. SPECIFIC REASON FOR QUARANTINE OR REJECTION (If applicable):
   [ ] Blurry / Laplacian score below threshold     [ ] Operator / camera shadow over subject
   [ ] Lens flare / Extreme backlighting            [ ] Camera distance borderline (0.5m - 0.9m)
   [ ] Pod vs Leaf area ambiguous (~50/50)          [ ] Human hands or personal items in frame
   [ ] Species identity unverified                  [ ] Duplicate angle of previous shot
   Detailed Notes: _____________________________________________________________
   _____________________________________________________________________________

================================================================================
```

---

## 3. Agronomist Credential Verification & Affirmation

> [!IMPORTANT]
> **Verifier Declaration:**
> By signing below, the verifying specialist confirms that they have independently examined the image file(s) listed above, verified botanical species identity, confirmed morphological organ categorization according to the project taxonomy, and applied objective image-quality standards.

* **Verifier Full Name:** ___________________________________________________________
* **Professional Title / Designation:** ___________________________________________________________
* **Institution / University / KVK / Department:** ___________________________________________________________
* **Professional Registration / Employee ID No.:** ___________________________________________________________
* **Official Email Address:** ___________________________________________________________
* **Contact Phone / Extension:** ___________________________________________________________

**Verifier Signature:** _______________________________________ **Date:** ___________________

---

## 4. Manifest Entry Instruction for Data Entry Operator

Once the agronomist has signed the verification record:
1. Open the field metadata sheet ([`field_metadata_template.csv`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/reports/pigeonpea_organ_dataset_collection/field_metadata_template.csv)).
2. Locate the row corresponding to `filename`.
3. Set `class_label` to the verified class checked in Section 3.
4. Set `verification_status` to `"verified"`, `"quarantined"`, or `"rejected"` matching Section 5.
5. In `verifier_reference`, enter the verifier’s name and professional ID (e.g., `Dr. [Name] ([Title], [Institution] #[ID])`).
6. Save the CSV and execute `validate_pigeonpea_field_collection.py` to confirm manifest syntax and target accumulation.
