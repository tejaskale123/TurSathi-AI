# TurSathi AI — Final End-to-End Test Audit Report

**Date & Time:** 2026-10-23T11:25:00+05:30  
**Project:** TurSathi AI (Pigeonpea Disease Classification System)  
**Execution Environment:** Windows / Python 3.13 / Node.js v22.14.0 / Pytest 8.4.2  
**Audit Purpose:** Comprehensive audit of completed Phases 1–7, identifying verified executed tests across application, API, ML, database, and mobile layers versus pending items.

---

## 1. End-to-End Test Audit Matrix

| Test Category | Exact Test or Command Executed | Status | Evidence / Report Path | Remaining Action |
|---|---|---|---|---|
| **Checkpoint Integrity** | SHA-256 byte verification of `models/best_pigeonpea_disease_final_efficientnet_b0.pth` (`5baecdc3911...`), `models/experimental_efficientnet_b0_clean_v1.pth` (`dd9d96b0a...`), `models/experimental_efficientnet_b0_clean_v2.pth` (`3d762b90d...`), `models/best_tur_image_validator_v3_mobilenet_v3_large.pth` (`9baee1714...`) | **PASS** | `reports/pigeonpea_phase5_comparison/phase5_model_comparison_report.md` | Keep production checkpoint active and immutable. |
| **Dataset Integrity** | Manifest validation (`datasets/pigeonpea_disease_clean_candidate_v1/manifest.csv`): 1,677 total images (1,336 train, 152 val, 189 test), 5 canonical classes, class index mapping 0..4 | **PASS** | `reports/pigeonpea_clean_candidate_build/` | Do not reuse the 189 test images for model selection. |
| **ML Evaluation: Phase 1** | Baseline zero-shot evaluation of production model on clean test split (189 images) | **PASS** | `reports/pigeonpea_clean_candidate_v1_baseline/phase1_baseline_clean_test_evaluation.json` | Baseline established at 94.71% (179/189). |
| **ML Evaluation: Phase 2** | Experimental V1 clean training (224×224, 20 epochs, clean train/val splits) | **PASS** | `reports/pigeonpea_experimental_clean_v1/training_log.csv` | Reached best val acc 94.70% (Epoch 17). |
| **ML Evaluation: Phase 3** | Side-by-side production vs V1 clean candidate evaluation on 189 clean test images | **PASS** | `reports/model_comparison_clean_v1/PHASE3_COMPARISON_REPORT.md` | Both scored 94.71%; V1 reduced mutual confusion to 7. |
| **ML Evaluation: Phase 4** | Experimental V2 clean training (288×288, biological diversity loss) | **PASS** | `reports/pigeonpea_experimental_clean_v2/training_log.csv` | Best val acc 93.38% (Epoch 12). |
| **ML Evaluation: Phase 5** | 3-way controlled evaluation: Production vs V1 vs V2 on 189 clean test images | **PASS** | `reports/pigeonpea_phase5_comparison/phase5_model_comparison_report.md` | All three models scored 94.71%. V2 failed to beat V1 on ECE (0.0399) or confusion (8). |
| **ML Error Analysis: Phase 6** | Forensic error analysis on 189 test images across all 3 models | **PASS** | `reports/pigeonpea_phase6_error_analysis/phase6_error_analysis_report.md` | 176/189 (93.12%) unanimous. 4 core Sterilic_mosaic + 1 Leaf_Spot image persistently misclassified. |
| **Agronomic Review: Phase 7** | Package preparation for 5 core images (`sterilic_mosaic_test_0007.jpg`, `0014`, `0025`, `0033`, `leaf_spot_test_0051`) | **PASS** | `reports/pigeonpea_phase7_annotation_review/phase7_annotation_review_package.md` | Package created; expert review is pending. |
| **Agronomic Pathology Review** | Independent plant pathologist review and confirmation of the 5 core images | **BLOCKED / PENDING** | `reports/pigeonpea_phase7_annotation_review/phase7_annotation_review_package.md` | Requires agricultural university pathologist review. |
| **External Field Evaluation** | Evaluation on an independent, unseen 5-class field dataset | **BLOCKED / NOT RUN** | N/A (`datasets/external_pigeonpea_field` is empty) | Curate independent field holdout dataset before production replacement. |
| **Backend: Test Suite** | `pytest backend/tests -v` (73 tests passed, 0 failed) | **PASS** | Test run execution log (`task-2064`) | None; full suite passing. |
| **Backend: Image Gate & Quality** | `test_tur_image_gate_quality.py` (9 tests: real tur, undersized, corrupted, blurry, not found, grayscale/RGBA, low light, overexposed) | **PASS** | `backend/tests/test_tur_image_gate_quality.py` | None. |
| **Backend: Organ Validator Interface** | `test_tur_organ_validator_interface.py` (8 tests: 4 canonical classes, dataclass contract, unconfigured defaults, exception raising, feature flag False) | **PASS** | `backend/tests/test_tur_organ_validator_interface.py` | Keep feature flag `ENABLE_ORGAN_VALIDATOR=False` until model is trained. |
| **Backend: Organ Validator Adapter & Error Handling** | `test_tur_organ_validator_adapter.py` (7 tests) & `test_tur_organ_validator_error_handling.py` (7 tests) | **PASS** | `backend/tests/test_tur_organ_validator_adapter.py`, `test_tur_organ_validator_error_handling.py` | Boundary safely handles missing weights without faking predictions. |
| **Backend: Stateless Frame Validation** | `test_validate_frame_stateless.py` (8 tests: auth required, valid frame pass, blur/size rejection, zero DB writes, zero disk writes) | **PASS** | `backend/tests/test_validate_frame_stateless.py` | Ensures real-time probe does not pollute database. |
| **Backend: Claude AI Guidance** | `test_claude_guidance.py` (12 tests: missing API key fallback, verified Marathi translations, unverified leaf webber gate, low confidence gate) | **PASS** | `backend/tests/test_claude_guidance.py` | None. |
| **Backend: Auth & Tenant Security** | `test_auth.py` (11 tests: JWT Bearer auth, bcrypt verification, mobile number normalization, token refresh) | **PASS** | `backend/tests/test_auth.py` | None. |
| **Backend: Pipeline & Scan Isolation** | `test_end_to_end_pipeline.py` & `test_scan_history_and_isolation.py` (11 tests: multi-tenant scan isolation, 401/403/404 handling, zero PostgreSQL writes) | **PASS** | `backend/tests/test_end_to_end_pipeline.py`, `test_scan_history_and_isolation.py` | None. |
| **Backend: Live API Benchmarks** | `run_api_evaluation.py` & `run_ood_evaluation.py` (scripts hitting live `http://localhost:8000/api/v1` and mutating database) | **NOT RUN** | `backend/tests/run_api_evaluation.py`, `run_ood_evaluation.py` | Do not run against production database; run only in dedicated sandbox environment. |
| **Database: Schema & State** | Read-only inspection of PostgreSQL schema, foreign keys, and 38 scan records | **PASS** | `reports/phase5_staging_validation_report.md` | Zero modifications allowed to live database. |
| **Frontend Web: Unit & Services** | `npm test` in `frontend` (26 tests passed: apiFetch, authService, scanService, recommendationService, tokenService, authGuard) | **PASS** | `frontend/tests/` (executed via Node.js test runner) | None; web service layer validated. |
| **Mobile: Auth & Recommendation** | `node --test tests/authApi.test.mjs tests/recommendationApi.test.mjs` (30 tests passed: 422 unpack, Marathi localization, chemical safety) | **PASS** | `mobile/tests/` (executed via Node.js test runner) | None. |
| **Mobile: Auto-Capture State Machine** | `node --experimental-strip-types --test tests/autoCaptureStateMachine.test.ts` (9 tests: disabled by default, stability counter, quality checks, cooldown) | **PASS** | `mobile/tests/autoCaptureStateMachine.test.ts` | None. |
| **Mobile: Leaf Detector Integration** | `node --experimental-strip-types --test tests/leafDetectorIntegration.test.ts` (11 tests: absence of on-device TFLite model, reticle bounds, blur rejection, cooldown) | **PASS** | `mobile/tests/leafDetectorIntegration.test.ts` | On-device TFLite detector remains optional; server fallback verified. |
| **Mobile: Physical Device / UI E2E** | Live camera viewfinder, hardware sensor autofocus, physical tap, audio guidance playback on real Android/iOS device | **NOT RUN / REQUIRES MANUAL DEVICE TESTING** | Expo Go active on port 8081 | Requires physical handset smoke test. |

---

## 2. Summary Findings

### 1. Tests Genuinely Passed
- **Backend automated test suite:** 73/73 tests passed via Pytest in 25.90s.
  - Covers `/api/v1/scans`, `/api/v1/predictions/tur-leaf/{scan_id}`, `/api/v1/recommendations`, and `/api/v1/scans/validate-frame`.
  - Request validation (empty file, invalid MIME, corrupted image, undersized image, blurry image) verified.
  - Response schema compliance and 5 canonical pigeonpea classes validated.
  - Multi-tenant scan isolation, Bearer JWT authentication, and error sanitization verified.
  - TurImageGate crop validator quality gates and fallback behaviors passed.
  - TurOrganValidator interface, error boundaries, and unconfigured safety flags passed.
- **Frontend web automated suite:** 26/26 tests passed via Node.js test runner in 377ms.
  - API configuration, error extraction, auth persistence, scan service, and recommendation routing verified.
- **Mobile automated test suite:** 50/50 tests passed across 4 test suites.
  - Auth API & error normalization (7 tests passed).
  - Recommendation & Marathi localization rules (23 tests passed).
  - Auto-capture state machine transitions and safety gates (9 tests passed).
  - Leaf detector integration and camera state management (11 tests passed).
- **ML Evaluations (Phases 1–6):**
  - Production model baseline, V1 clean candidate, and V2 clean candidate all measured at 94.71% (179/189) on clean candidate test set.
  - Checkpoint SHA-256 hashes verified for Production, V1, V2, and MobileNetV3 Image Gate.
  - Deep error analysis (Phase 6) completed, identifying exact failure patterns and 93.12% unanimous agreement.
  - Phase 7 agronomic review package prepared with contact sheet and metadata.

### 2. Tests Failed
- **Zero automated tests failed** across backend (0/73 failed), frontend (0/26 failed), and mobile (0/50 failed).
- **Hypothesis Failure (Phase 5):** The experimental V2 candidate ($288\times 288$ + biological diversity loss) failed to reduce Leaf_Spot vs Sterilic_mosaic mutual confusion (8 errors) and produced higher ECE (0.0399 vs 0.0271 for V1), failing its promotion acceptance criteria.

### 3. Tests Not Run or Requiring Manual Verification
1. **Live Backend Mutation Scripts (`run_api_evaluation.py` & `run_ood_evaluation.py`):**
   - Not executed because they send mutating HTTP POST requests to the live backend, creating live user and scan records in PostgreSQL and altering report text files.
2. **Mobile Physical Handset UI / Camera E2E:**
   - Headless CLI environment cannot verify hardware camera autofocus, physical reticle framing, hardware accelerometer/gyroscope, or live speaker audio playback. This strictly requires manual verification on a physical Android or iOS device running Expo Go.
3. **Database Destructive Operations:**
   - Database migrations and table alteration tests intentionally not run against live PostgreSQL (strictly isolated via in-memory SQLite in automated tests).

### 4. Critical Blockers Before Production Model Replacement
1. **Agronomic Pathologist Review Pending:**
   - The 5 core test images (`sterilic_mosaic_test_0007.jpg`, `0014`, `0025`, `0033` and `leaf_spot_test_0051`) consistently fail across all three model architectures with high confidence (>94%). Without an accredited plant pathologist's ground-truth review, it cannot be determined whether these represent visual model ambiguity or dataset label noise.
2. **Exhaustion of the 189-Image Clean Test Set:**
   - The 189 test images have been evaluated repeatedly across Production, V1, and V2. Promoting or tuning any candidate based on repeated test-set evaluation creates statistical test-set contamination.
3. **Lack of Independent Field Evaluation Dataset:**
   - `datasets/external_pigeonpea_field` is currently empty. An independent holdout dataset collected from actual farmers' fields (with real sunlight, background variations, and diverse crop stages) is required before replacing the active production model.
4. **V2 Did Not Demonstrate Statistically Significant Superiority:**
   - Phase 5 comparative evaluation showed V2 did not outperform Production or V1 on accuracy (identical 94.71%) and worsened calibration (ECE 0.0399).

---

## 5. Single Highest-Priority Next Action
**Complete the agronomic plant pathology review of the five core images using the Phase 7 review package (`reports/pigeonpea_phase7_annotation_review/phase7_annotation_review_package.md`), while strictly maintaining the current production model (`models/best_pigeonpea_disease_final_efficientnet_b0.pth`) in active service.**
