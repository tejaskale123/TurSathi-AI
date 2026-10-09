# PHASE 5A: ARCHITECTURE AUDIT

## 1. Existing Production Flow

**Upload**: `POST /api/v1/scans` (Saves image to disk, returns `scan_id`)
**Storage**: Configured via `app.services.storage_service.UPLOAD_DIR`
**Prediction Endpoint**: `POST /api/v1/predictions/tur-leaf/{scan_id}`
**Prediction Service**: `app.services.prediction_service.run_prediction()`
**Disease Predictor**: `TurDiseasePredictor`
**Existing Validator**: `TurImageValidator` (currently configured for `tur_image_validator_efficientnet_b0.pth` - V1). Note: The checkpoint format expects a dictionary with `classes`, `class_to_idx`, and `model_state_dict`.
**Existing Gate**: `TurImageGate` in `backend/app/ml/tur_image_gate.py`. It calls `TurImageValidator.predict(image)` and returns a `ValidationResult`.
**Error Handling**: If predictor throws an error, it is caught and wrapped. Unidentified images raise 500 or fallback gracefully.
**Authentication**: Bearer JWT.

**Current Unmodified Flow:**
Upload
  ↓
Scan creation (Scan status = "received")
  ↓
Prediction request (`run_prediction` via `POST /predictions/tur-leaf/...`)
  ↓
Disease predictor (loads image, runs inference)
  ↓
Disease result (saves to db, returns to client)

Wait, currently `TurImageGate` is NOT wired into `run_prediction`!
Checking `backend/app/services/prediction_service.py`, `get_tur_image_gate()` is not imported or used. The prediction service directly calls `get_predictor().predict(image_abs_path)`.
So the gate exists but is disconnected from the main request flow.

## 2. Intended Production Flow

Upload
  ↓
Scan creation
  ↓
Prediction request (`POST /predictions/tur-leaf/{scan_id}`)
  ↓
`TurImageGate.validate(image)` (Powered by V3 Checkpoint)
  ↓
 ┌──────────────────────────┐
 │                          │
Not_Tur                    Tur
 │                          │
Reject                 Existing Disease Predictor
 │                          ↓
HTTP 422             Disease Result Saved & Returned
"Not a Tur leaf"

The V3 validator will be swapped into `TurImageValidator`. Since the V3 checkpoint was saved directly as a `state_dict`, the `TurImageValidator` must be updated slightly to handle both the old dict format and the direct `state_dict` format, OR simply hardcode the classes `['Not_Tur', 'Tur']` if keys are missing.
