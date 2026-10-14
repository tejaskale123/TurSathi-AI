# STAGE F30 REPORT: FINAL REGRESSION AND RELEASE AUDIT

**Project:** TurSathi AI / AgriMind AI — Pigeonpea Disease Detection  
**Stage:** F30 (Final Regression and Release Audit)  
**Execution Timestamp:** 2026-10-13T13:45:30+05:30  
**Overall Release Status:** **READY FOR LIMITED TESTING (CONTROLLED PILOT ONLY)** / **HOLD FOR UNRESTRICTED PRODUCTION RELEASE**

---

### 1. Executive Summary

This Final Release Audit consolidates the outcomes of Stages F27, F28, F29, and F30 for TurSathi AI / AgriMind AI.

The software engineering, backend architecture, security controls, test coverage, and API contracts are fully functional, resilient, and verified. 26 out of 26 automated backend tests pass cleanly. The Vite frontend builds without errors.

However, based on empirical evidence from Stages F23, F24, F26, and F28, the machine learning models exhibit specific dataset and domain vulnerabilities (Wilt test leakage and arbitrary background bypass) that preclude an unconditional, unmonitored production release. Consequently, the release status is classified as **READY FOR LIMITED TESTING (CONTROLLED PILOT ONLY)** with a formal **HOLD ON GENERAL OPEN-WORLD DEPLOYMENT**.

---

### 2. Stage-by-Stage Completion Status (F27–F30)

| Stage | Title | Status | Primary Outcome |
| :---: | :--- | :---: | :--- |
| **F27** | End-to-End Pipeline Verification | **COMPLETE** | 10 new isolated end-to-end pipeline tests created and passing. Total backend test count reached 26/26. In-memory SQLite and isolated file storage prevent database or filesystem leakage. |
| **F28** | Model & Integration Readiness Decision | **COMPLETE** | 5-class checkpoint mapping, preprocessing, confidence thresholds, and two-stage gate verified. Formally recommended **HOLD for general release** due to Wilt leakage and exploratory OOD bypass. |
| **F29** | Frontend/Backend Functional Regression | **COMPLETE** | Vite production build succeeded in 1.59s. Trilingual authentication flows, error presentation, scan uploads, and result rendering verified without architectural churn. |
| **F30** | Final Regression and Release Audit | **COMPLETE** | Python compileall passed (0 syntax errors). Full regression suite (26 tests) passed. Git status verified. Safe startup and deployment checklists finalized. |

---

### 3. Exact Tests Executed and Pass/Fail Summary

- **Python Syntax Compilation (`python -m compileall backend/app`):** 0 syntax errors across 100% of modules.
- **Frontend Production Build (`npm run build` in `frontend/`):** 0 compilation errors.
- **Backend Test Suite (`pytest -v`):** **26 PASSED**, 0 FAILED (Duration: 18.81s)
  - `backend/tests/test_auth.py`: 1/1 PASSED (Normalized email/mobile registration, authentication, token issuance)
  - `backend/tests/test_claude_guidance.py`: 15/15 PASSED (Claude AI guidance service, multilingual Marathi/Hindi/English prompts, error fallbacks)
  - `backend/tests/test_end_to_end_pipeline.py`: 10/10 PASSED:
    1. `test_five_classes_schema_integrity`: PASSED
    2. `test_valid_pigeonpea_end_to_end_flow`: PASSED
    3. `test_image_gate_rejection_non_tur`: PASSED
    4. `test_empty_image_upload_rejected`: PASSED
    5. `test_corrupted_image_caught_safely`: PASSED
    6. `test_disallowed_mime_type_rejected`: PASSED
    7. `test_unauthenticated_requests_blocked`: PASSED
    8. `test_cross_tenant_scan_isolation`: PASSED
    9. `test_nonexistent_route_clean_404`: PASSED
    10. `test_recommendation_endpoint_handled_safely`: PASSED

---

### 4. Code Changes and File Manifest

#### Files Modified / Created During Stages F20–F30:
1. `backend/.env` (Stage F20): Removed 67 null bytes; preserved valid 54-char `SECRET_KEY`.
2. `backend/requirements.txt` (Stage F20): Added `torch>=2.0.0`, `torchvision>=0.15.0`, `Pillow>=10.0.0`.
3. `pytest.ini` (Stage F22): Created root configuration setting `pythonpath = backend`.
4. `backend/tests/test_auth.py` (Stage F22): Refactored to in-process `TestClient` with in-memory SQLite (`backup: test_auth.py.bak_f22`).
5. `backend/app/schemas/recommendation.py` (Stage F22): Updated from deprecated Pydantic v1 `class Config` to v2 `ConfigDict` (`backup: recommendation.py.bak_f22`).
6. `experiments/ood_eval_f26/` (Stage F26): Created frozen evaluation manifest (`manifest_f26.json`), image results (`eval_results_f26.json`), and metrics summary (`summary_metrics_f26.json`).
7. `backend/tests/test_end_to_end_pipeline.py` (Stage F27): Created 10 isolated pipeline regression tests.
8. `reports/stage_reports/` (Stages F27–F30): Created non-overwriting audit reports (`stage_f27_report.md`, `stage_f28_report.md`, `stage_f29_report.md`, `stage_f30_report.md`).

#### Files Deliberately Left Unchanged:
- `models/best_pigeonpea_disease_final_efficientnet_b0.pth` (Production model weights strictly preserved).
- `models/tur_image_validator_efficientnet_b0_v3.pth` (Production validator weights strictly preserved).
- `backend/app/ml/tur_predictor.py` (Production 5-class predictor architecture preserved).
- `backend/app/ml/tur_image_gate.py` (Production image gate logic preserved).
- All source datasets in `datasets/` (Zero deletion, zero relabeling).
- Production database schema and existing migrations.

---

### 5. Outstanding Critical & Non-Critical Issues

1. **Wilt Augmentation Leakage (Critical Model Limitation):**
   51 of the 58 test images for Wilt are augmented derivatives of the 30 original physical plants in the training set. True generalizable accuracy on unaugmented novel field Wilt is unknown.
2. **Cross-Label Test Collisions (Dataset Limitation):**
   24 test images share identical byte hashes with conflicting classes in the dataset (`Leaf_Spot` vs `Sterilic_mosaic`). They must be permanently cleaned in future training cycles.
3. **Exploratory Out-of-Distribution Vulnerability (OOD Limitation):**
   The binary image validator successfully rejects known non-tur crops (0/79 FAR) and unsupported diseases (0/54 FAR), but allows 40/40 unverified exploratory leaf images with green foliage to pass through.
4. **FastAPI Deprecation Warning (Minor Technical Debt):**
   `HTTP_422_UNPROCESSABLE_ENTITY` triggers a deprecation notice recommending `HTTP_422_UNPROCESSABLE_CONTENT`. Does not affect functionality.

---

### 6. Manual Steps Still Required Prior to Live Pilot

1. **Production Database Migration:** Ensure PostgreSQL migrations are applied on the production instance using `alembic upgrade head`.
2. **Environment Variable Provisioning:** Ensure production `.env` contains valid credentials for `DATABASE_URL`, `SECRET_KEY`, and optional `ANTHROPIC_API_KEY` for Claude guidance.
3. **SSL / Reverse Proxy Setup:** Configure Nginx or Caddy with TLS certificates and rate limiting in front of Uvicorn.
4. **Field Protocol Training:** Instruct pilot extension officers to take focused, well-lit photos directly centered on pigeonpea leaves.

---

### 7. Safe Startup and Verification Checklist

Follow these steps to launch the system safely from the repository root:

```bash
# 1. Activate Python environment
conda activate tursathi

# 2. Run backend regression test suite
pytest -v

# 3. Start Backend Server (runs on http://127.0.0.1:8000)
python -m uvicorn app.main:app --app-dir backend --reload

# 4. Verify Backend Health Endpoint
curl http://127.0.0.1:8000/health

# 5. Start Mobile Expo App (in separate terminal)
cd mobile
npx expo start --clear --lan

# 6. Build or preview Web Frontend (optional)
cd frontend
npm run build
npm run preview
```

---

### 8. Final Release Recommendation

**Classification: READY FOR LIMITED TESTING (CONTROLLED PILOT ONLY)**  
The application is ready for controlled field testing by agricultural researchers and extension workers. Open-world public rollout should remain on **HOLD** until an independent field dataset for Wilt and negative weed background training for the image gate are completed.
