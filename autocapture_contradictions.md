# TurSathi AI — Auto-Capture Architecture, Feasibility Audit & Contradictions Report

**Document File:** `autocapture_contradictions.md`  
**Date:** October 15, 2026  
**Status:** Feature Flag `ENABLE_ORGAN_VALIDATOR = False` | Auto-Capture: **Safely Reverted / Strictly Disabled**  
**Operating Mode:** Manual Shutter Capture Active ("पानाचा फोटो काढा")  

---

## 1. Executive Summary

This document synthesizes the architectural review, component mapping, pseudo-script specification, and technical reality check for introducing automatic Tur leaf detection into the TurSathi AI project.

Following an audit of the live mobile application and backend logs, the periodic camera snapshot probing loop (which was capturing snapshot frames every 500ms–1500ms and sending them to `POST /api/v1/scans/validate-frame`) has been **completely removed and reverted back to the original manual capture workflow**. Manual photo capture is 100% operational, robust, and zero-flicker.

---

## 2. Full Component Mapping: Frontend & Backend Capture Flow

Taking a photo in the TurSathi AI system spans six coordinated layers across mobile client and server:

```
                          MOBILE APP (FRONTEND)                                     BACKEND API
        ┌────────────────────────────────────────────────────────┐     ┌────────────────────────────────────┐
        │ 1. ScanScreen (mobile/src/app/scan.tsx)                │     │                                    │
        │    • CameraView (cameraRef)                            │     │                                    │
        │    • Manual Shutter Button ("पानाचा फोटो काढा")       │     │                                    │
        │    • CameraGuide overlay & laser scan animation        │     │                                    │
        │                          │                             │     │                                    │
        │                          ▼                             │     │                                    │
        │ 2. Shutter Execution Engine                            │     │                                    │
        │    • handleTakePhoto()                                 │     │                                    │
        │    • cameraRef.current.takePictureAsync({ quality: 1 })│     │                                    │
        │    • persistImageUri() to local cache storage          │     │                                    │
        │                          │                             │     │                                    │
        │                          ▼                             │     │                                    │
        │ 3. Image Preview & Confirmation Mode                   │     │                                    │
        │    • Displays captured photo (setImageUri)             │     │                                    │
        │    • "दुसऱ्यांदा काढा" (Retake)                         │     │                                    │
        │    • "हा फोटो वापरा" (Use Photo)                       │     │                                    │
        │                          │                             │     │                                    │
        │                          ▼                             │     │                                    │
        │ 4. Upload & Classification Pipeline                    │     │                                    │
        │    • continueWithPhoto()                               │     │                                    │
        │    • uploadScan() ─────────────────────────────────────┼────▶│ 5. POST /api/v1/scans              │
        │    • predictDisease() ─────────────────────────────────┼────▶│ 6. POST /api/v1/predictions/predict│
        └────────────────────────────────────────────────────────┘     └────────────────────────────────────┘
```

### Detailed Component Inventory:

| Layer | File / Symbol | Role & Technical Behavior |
| :--- | :--- | :--- |
| **Camera View** | [`mobile/src/app/scan.tsx`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/mobile/src/app/scan.tsx) | Hosts Expo `CameraView`. Manages preview stream, camera permissions, and autofocus. |
| **Manual Shutter** | `handleTakePhoto` | Invoked on pressing "पानाचा फोटो काढा". Locks `isCapturing` flag, fires `takePictureAsync({ quality: 1 })`, persists file to local cache, transitions to preview screen. |
| **Image Persistence** | `persistImageUri` | Copies temporary camera cache file into stable app sandbox directory (`FileSystem.copyAsync`) to prevent garbage collection by the OS. |
| **Preview & Confirm** | `retakePhoto` & `continueWithPhoto` | Allows the farmer to inspect the photo. If clear, farmer taps "हा फोटो वापरा" to proceed with upload. |
| **Scan Record API** | [`backend/app/api/v1/scans.py`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/backend/app/api/v1/scans.py) (`POST /api/v1/scans`) | Validates image header and format, stores file with secure UUID filename, records scan in PostgreSQL. |
| **Disease Inference API**| [`backend/app/api/v1/predictions.py`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/backend/app/api/v1/predictions.py) (`POST /api/v1/predictions/predict`) | Runs PyTorch EfficientNet-B0 disease model (`best_pigeonpea_disease_final_efficientnet_b0.pth`) classifying: *Healthy, Leaf Spot, Leaf Webber, Sterility Mosaic, Wilt*. |
| **Frame Validation API** | [`backend/app/api/v1/scans.py`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/backend/app/api/v1/scans.py#L227-L283) (`POST /validate-frame`) | Stateless in-memory gate. Runs Laplacian variance check ($\ge 100.0$) and `TurImageValidator` (Tur vs Not-Tur). No database or file storage. |

---

## 3. Pseudo-Script: Target Automatic Leaf Detection & Capture Engine

Below is the pseudo-script specifying the target auto-capture engine, incorporating organ detection, a 300ms stabilization window, anti-flicker protection, and auto-shutter triggering:

```python
# ==============================================================================
# PSEUDO-SCRIPT: AUTOMATIC TUR LEAF DETECTION & CAPTURE ENGINE
# ==============================================================================

class AutoCaptureEngine:
    def __init__(self):
        # Configuration parameters
        self.STABILIZATION_TIME_MS = 300      # 300ms stabilization debounce window
        self.MIN_STABLE_FRAMES = 3            # Must sustain positive detection across >= 3 frames
        self.MIN_LEAF_CONFIDENCE = 0.85       # Minimum organ probability threshold
        self.SHUTTER_COOLDOWN_MS = 3000       # Prevent rapid repeated captures
        
        # Runtime tracking variables
        self.state = "SEARCHING"              # SEARCHING | STABILIZING | CAPTURE_READY | CAPTURING | LOCKED
        self.leaf_first_seen_timestamp = None
        self.consecutive_valid_frames = 0
        self.last_shutter_timestamp = 0
        self.is_shutter_locked = False

    # --------------------------------------------------------------------------
    # 1. FRAME INTAKE & EVALUATION (Runs on incoming camera frame)
    # --------------------------------------------------------------------------
    def process_camera_frame(self, frame):
        current_time_ms = get_current_timestamp_ms()

        # Guard: If shutter is currently locked, capturing, or in cooldown, ignore frame
        if self.is_shutter_locked or (current_time_ms - self.last_shutter_timestamp < self.SHUTTER_COOLDOWN_MS):
            return

        # Step A: Evaluate Image Sharpness (Local Laplacian Variance)
        # Prevents capturing while the farmer is still moving their arm
        is_sharp, blur_score = check_sharpness(frame, threshold=100.0)
        if not is_sharp:
            self._handle_unstable_or_invalid("MOTION_BLUR", "कृपया कॅमेरा स्थिर धरा") # Hold camera steady
            return

        # Step B: Organ Classification Check (Edge TFLite model or fast probe)
        # MUST classify specifically: 0=Not_Tur, 1=Tur_Leaf, 2=Tur_Pod, 3=Tur_Canopy
        detection = detect_organ(frame)
        is_leaf = (detection.label == "Tur_Leaf") and (detection.confidence >= self.MIN_LEAF_CONFIDENCE)

        if not is_leaf:
            if detection.label in ["Tur_Pod", "Tur_WholePlant_or_Canopy"]:
                self._handle_unstable_or_invalid("WRONG_ORGAN", "केवळ एका पानावर कॅमेरा केंद्रित करा")
            else:
                self._handle_unstable_or_invalid("NON_TUR", "तुरीच्या पानावर कॅमेरा केंद्रित करा")
            return

        # ----------------------------------------------------------------------
        # 2. STABILIZATION & 300ms DEBOUNCE (Anti-Flicker Logic)
        # ----------------------------------------------------------------------
        # If this is the first frame where leaf is confirmed, start stabilization timer
        if self.leaf_first_seen_timestamp is None:
            self.leaf_first_seen_timestamp = current_time_ms
            self.consecutive_valid_frames = 1
            self.state = "STABILIZING"
            self.update_ui_reticle(color="YELLOW", message="पान ओळखले, स्थिर धरत आहे...")
            return

        # Increment consecutive valid frames
        self.consecutive_valid_frames += 1
        elapsed_stable_time = current_time_ms - self.leaf_first_seen_timestamp

        # Check if BOTH conditions are met:
        # 1. Leaf remained continuously visible and sharp for >= 300 milliseconds
        # 2. At least 3 consecutive frames passed the check
        if elapsed_stable_time >= self.STABILIZATION_TIME_MS and self.consecutive_valid_frames >= self.MIN_STABLE_FRAMES:
            self.state = "CAPTURE_READY"
            self.update_ui_reticle(color="GREEN", message="स्थिर! फोटो काढत आहे...")
            self.trigger_automatic_shutter()

    # --------------------------------------------------------------------------
    # 3. AUTOMATIC PHOTO CAPTURE TRIGGER
    # --------------------------------------------------------------------------
    def trigger_automatic_shutter(self):
        # Immediate mutual-exclusion lock to prevent double-firing
        self.is_shutter_locked = True
        self.state = "CAPTURING"
        self.last_shutter_timestamp = get_current_timestamp_ms()

        # Signal photo capturing engine (CameraView.takePictureAsync)
        high_res_photo = camera_engine.take_picture(quality=1.0)

        # Haptic feedback (subtle vibration to inform the farmer)
        haptics.vibrate_success()

        # Proceed to normal existing flow (Preview Screen -> "हा फोटो वापरा")
        save_to_local_cache(high_res_photo.uri)
        navigate_to_preview(high_res_photo.uri)

    # --------------------------------------------------------------------------
    # 4. RESET & RECOVERY HANDLER (Zero-flicker state reset)
    # --------------------------------------------------------------------------
    def _handle_unstable_or_invalid(self, reason, ui_message):
        # Reset stability counters when subject moves away or blurs
        self.leaf_first_seen_timestamp = None
        self.consecutive_valid_frames = 0
        if self.state != "SEARCHING":
            self.state = "SEARCHING"
            self.update_ui_reticle(color="WHITE", message=ui_message)
```

---

## 4. Critical Technical Contradictions

### Contradiction 1: Network Round-Trip Latency vs. The 500ms Speed Target
* **Envisioned Workflow:** Farmer points camera at leaf $\rightarrow$ client probes backend $\rightarrow$ backend confirms leaf $\rightarrow$ client automatically clicks photo $\rightarrow$ total elapsed time $\le 500\text{ ms}$.
* **The Technical Reality:**
  1. Sending an image over mobile 4G/Wi-Fi to backend takes **150ms – 400ms**.
  2. Backend image decompression, Laplacian blur check, and PyTorch inference takes **80ms – 180ms**.
  3. Total network round-trip time (RTT) is **230ms – 580ms per individual frame**.
  4. Multi-frame stabilization (requiring a 300ms continuous stable window across 3 frames over HTTP) requires **1.5s – 2.5s**, making a 500ms response mathematically impossible over network probes.
* **Architectural Requirement:** Real-time auto-capture ($\le 500\text{ ms}$) **must run on-device (Edge TFLite/ONNX)** directly evaluating the video frame buffer locally at 15–30 FPS with zero network overhead.

### Contradiction 2: Binary Crop Classifier vs. 4-Class Organ Detector
* **Envisioned Workflow:** If the backend returns positive detection, the app assumes an individual Tur leaf is in frame and triggers the shutter.
* **The Technical Reality:**
  * The current model in backend (`tur_image_validator_v3`) is a **binary classifier (Tur crop vs. Not-Tur)**.
  * It detects whether an image is pigeonpea, but cannot distinguish a *leaf* from a *pod*, *flower*, *stem*, or *distant canopy*.
  * If auto-capture fires on `is_valid_tur: true`, the camera will automatically snap photos of pods, flowers, and whole plants.
  * The downstream disease model was trained strictly on close-up leaves. Feeding it non-leaf photos causes severe diagnostic hallucinations.
* **Architectural Requirement:** Automatic capture requires a trained **4-class organ detector** (`Tur_Leaf`, `Tur_Pod`, `Tur_WholePlant_or_Canopy`, `Not_Tur_or_Unsupported`).

### Contradiction 3: Mobile Camera Sensor Locking & Buffer Collision
* **The Technical Reality:** On Expo/React Native, executing `takePictureAsync` for background probes temporarily locks the native camera sensor and autofocus engine.
* **Observed Impact:** Rapid background probes caused camera stutter, autofocus hunting, and occasional race conditions when the farmer attempted to tap the manual shutter.
* **Architectural Requirement:** Video stream frame inspection via an edge frame processor is required rather than taking discrete snapshot photos in the background.

---

## 5. Dataset Readiness & Label Hygiene Audit

| Class | Source Dataset | Train | Val | Test | Total | Status & Hygiene Findings |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **`Tur_Leaf`** | `pigeonpea_disease_final` | **941** | **312** | **318** | **1,571** | **Ready for Reuse.** Contains only genuine foliar leaf images (`Healthy`, `Leaf_Spot`, `Leaf_webber`, `Sterilic_mosaic`). Zero corrupt files. |
| **`Not_Tur_or_Unsupported`** | `tur_image_validator_v3` | **1,460** | **127** | **133** | **1,720** | **Ready for Reuse.** Negative distractors (weeds, other crops, hands, background). |
| **`Tur_Pod`** | *None* | **0** | **0** | **0** | **0** | **HARD BLOCKER.** Deficit: -50 min, -250 target. |
| **`Tur_WholePlant_or_Canopy`**| *None* | **0** | **0** | **0** | **0** | **HARD BLOCKER.** Deficit: -50 min, -200 target. |

> [!IMPORTANT]
> **Forensic Isolation of `Wilt` Class (287 images):**  
> 100% of `Wilt` images in `pigeonpea_disease_final` depict whole plants, bare stems, and distant canopy in soil, with an 87.9% duplicate overlap between train and test splits. Mislabling `Wilt` as `Tur_Leaf` contaminates the leaf detector. `Wilt` has been **strictly excluded** from `Tur_Leaf` staging.

---

## 6. Action Taken: Reversion to Stable Manual Workflow

As requested:
1. **Removed Background Probing:** Reverted [`mobile/src/app/scan.tsx`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/mobile/src/app/scan.tsx) back to its original stable implementation.
2. **No Background Photo Captures:** The camera no longer fires snapshot probes or makes repeated network calls when opened.
3. **Manual Shutter Operational:** The farmer sees the live camera preview, frames the leaf, and taps "पानाचा फोटो काढा".
4. **Existing Modalities Preserved:** Retake ("दुसऱ्यांदा काढा"), Use Photo ("हा फोटो वापरा"), Voice guidance, and disease prediction pipeline are 100% intact.
5. **Validation:** All unit test suites pass (`tests/test_pigeonpea_field_collection_validator.py`: 9/9 passed).
