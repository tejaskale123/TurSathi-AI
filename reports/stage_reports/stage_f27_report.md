# STAGE F27 REPORT: END-TO-END PIPELINE VERIFICATION

**Project:** TurSathi AI / AgriMind AI — Pigeonpea Disease Detection  
**Stage:** F27 (End-to-End Pipeline Verification)  
**Execution Timestamp:** 2026-10-13T13:42:00+05:30  
**Status:** COMPLETE (All 26 backend regression and end-to-end pipeline tests passing)

---

### 1. Executive Summary

Stage F27 performed an end-to-end pipeline verification of the TurSathi AI backend, validating the intake and prediction routes, `TurImageGate` validation, `TurDiseasePredictor` inference, schema serialization, tenant isolation, and error handling.

All tests executed against an isolated in-process FastAPI TestClient backed by an in-memory SQLite database and isolated temporary file storage. No live database writes were made to PostgreSQL, and no production assets or upload directories were touched.

---

### 2. Actual Route Architecture & Verification

The codebase implements a two-step asynchronous workflow rather than a single monolith predict endpoint:

1. **Intake Route (`POST /api/v1/scans`):**
   - Receives multipart/form-data upload (`image`, `crop`).
   - Validates MIME type (`JPEG`, `PNG`, `WebP`, `HEIC`) and file size ($\le 20\text{ MB}$).
   - Persists the file to storage using UUID filenames (preventing path traversal).
   - Creates a `TurScan` record with `status="received"` and `prediction_status="pending"`.
   - Returns `ScanCreateResponse(scan_id=scan.id, crop=scan.crop, status=scan.status)` (HTTP 201).

2. **Prediction Route (`POST /api/v1/predictions/tur-leaf/{scan_id}`):**
   - Enforces Bearer JWT authentication and multi-tenant scan ownership.
   - Stage 1 Gate (`TurImageGate`): Performs PIL image verification (`Image.open(p).verify()`), dimension checks (min $32 \times 32$), and binary classification (`EfficientNet-B0 v3`). If invalid or non-tur, updates scan status to `"rejected"` and raises HTTP 422 (`{"status": "validation_failed", "message": "Please upload a clear Tur/Pigeonpea leaf image."}`).
   - Stage 2 Classifier (`TurDiseasePredictor`): Runs 5-class EfficientNet-B0 inference. If confidence $< 0.65$, marks scan as `"rejected"` and raises HTTP 422 (`{"status": "unsupported_disease"}`). If confidence $\ge 0.65$, updates scan status to `"completed"` and returns HTTP 200 `PredictionResponse`.

3. **Scan History Route (`GET /api/v1/scans/{scan_id}`):**
   - Returns `ScanDetailResponse` with persisted prediction, confidence, and timestamps.
   - Enforces strict tenant ownership (other users receive HTTP 403/404).

4. **Recommendation Route (`GET /api/v1/recommendations/tur/{disease_name}/spray-guidance`):**
   - Returns verified agricultural guidance from `tur_disease_recommendations`.
   - Safely returns HTTP 404 when unseeded without exposing server internals.

---

### 3. Test Suite Execution & Results

A new isolated test suite was created at [`backend/tests/test_end_to_end_pipeline.py`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/backend/tests/test_end_to_end_pipeline.py), adding 10 targeted end-to-end tests:

| Test Name | Focus Area | Result |
| :--- | :--- | :---: |
| `test_five_classes_schema_integrity` | Confirms all 5 classes match model weights & serialize in `PredictionResponse` | **PASSED** |
| `test_valid_pigeonpea_end_to_end_flow` | Real pigeonpea image passes gate, reaches classifier, returns HTTP 200 completed | **PASSED** |
| `test_image_gate_rejection_non_tur` | Non-tur leaf (`curl106.jpg`) rejected by gate with HTTP 422 & user guidance | **PASSED** |
| `test_empty_image_upload_rejected` | 0-byte upload rejected with HTTP 422 | **PASSED** |
| `test_corrupted_image_caught_safely` | Corrupted bytes accepted at intake, safely trapped by gate at prediction (HTTP 422) | **PASSED** |
| `test_disallowed_mime_type_rejected` | PDF uploaded as image rejected at intake (HTTP 422) | **PASSED** |
| `test_unauthenticated_requests_blocked` | Missing header returns 422; invalid token returns 401 | **PASSED** |
| `test_cross_tenant_scan_isolation` | User B cannot view or predict User A's scan (HTTP 403/404) | **PASSED** |
| `test_nonexistent_route_clean_404` | Request to `/api/v1/predict/` returns clean 404 without path leakage | **PASSED** |
| `test_recommendation_endpoint_handled_safely` | Safe 404 handling without crashes on unseeded conditions | **PASSED** |

**Full Backend Test Summary:**
- `backend/tests/test_auth.py`: 1 PASSED
- `backend/tests/test_claude_guidance.py`: 15 PASSED
- `backend/tests/test_end_to_end_pipeline.py`: 10 PASSED
- **Total:** **26 PASSED**, 0 FAILED (Duration: 18.81s)

---

### 4. Identified Defects & Observations

1. **Intake Validation Granularity:** `POST /api/v1/scans` checks only the MIME header and file length; it does not decode image bytes with PIL at upload time. Structural decoding occurs when `POST /api/v1/predictions/tur-leaf/{scan_id}` invokes `TurImageGate`. While this is safe because `TurImageGate` catches corruption, decoding at intake would allow immediate rejection before disk storage.
2. **Missing Aliases:** Calls to `/api/v1/predict/` return 404 because the actual route is `/api/v1/predictions/tur-leaf/{scan_id}`. Client documentation must reflect the correct route path.
3. **Deprecation Warnings:** FastAPI `HTTP_422_UNPROCESSABLE_ENTITY` triggers a minor Python deprecation warning suggesting `HTTP_422_UNPROCESSABLE_CONTENT`. This does not affect runtime stability.

---

### 5. Readiness for Stage F28

The pipeline satisfies all functional and architectural prerequisites for Stage F28. No production code changes were required.
