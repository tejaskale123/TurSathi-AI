# TurSathi AI — Pigeonpea Organ Detector Dataset Collection & Training Workflow

## 1. Executive Summary

A real-time on-device automatic camera capture requires distinguishing an individual **Tur Leaf** from **Tur Pods**, **Tur Whole Plant / Canopy**, and **Non-Tur Backgrounds**. 

The current TurSathi AI project contains server-side PyTorch disease classification checkpoints (`models/best_pigeonpea_disease_final_efficientnet_b0.pth`), but **zero** on-device edge detector models (`.tflite`). Furthermore, the dataset audit revealed that the repository currently contains **zero** pigeonpea pod images and **zero** canopy images.

This workflow outlines the exact requirements to collect the missing data, train the genuine MobileNetV3-Small organ detector, quantize it to INT8 TFLite, and deploy it to the native Android camera pipeline.

---

## 2. Dataset Requirements and Current Deficits

| Organ Class | Minimum Required | Current Verified Images | Deficit | Status |
| :--- | :---: | :---: | :---: | :---: |
| **`Tur_Leaf`** | 500 | 0 in field collection | -500 | ❌ Blocker |
| **`Tur_Pod`** | 500 | 0 | -500 | ❌ Blocker |
| **`Tur_WholePlant_or_Canopy`** | 500 | 0 | -500 | ❌ Blocker |
| **`Not_Tur_or_Unsupported`** | 500 | 0 in field collection | -500 | ❌ Blocker |
| **Distinct Farms** | $\ge 5$ | 0 | -5 | ❌ Blocker |

> **Anti-Leakage Mandate:** Images must be collected across at least 5 physically separated farms ($\ge 5\text{ km}$ apart). Splitting must be performed at the **farm/plot level**, not random image-level, to avoid spatial data leakage.

---

## 3. Field Photography & Annotation Protocol

### A. Photography Guidelines
1. **Tur_Leaf:** Single leaf filling 50–80% of the viewfinder. Include both healthy leaves and diseased leaves across morning and afternoon light.
2. **Tur_Pod:** Developing green pods, flowering clusters, and mature pods.
3. **Tur_WholePlant_or_Canopy:** Distant canopy views, whole bush, and row perspectives (simulating farmer pointing camera from standing position).
4. **Not_Tur_or_Unsupported:** Neighboring crops (cotton, soybean, sorghum), weeds, bare soil, hands holding leaves, and equipment.

### B. Directory Structure
Images should be placed into:
```
datasets/pigeonpea_organ_dataset/
├── train/
│   ├── Tur_Leaf/
│   ├── Tur_Pod/
│   ├── Tur_WholePlant_or_Canopy/
│   └── Not_Tur_or_Unsupported/
├── val/
│   ├── Tur_Leaf/
│   ├── Tur_Pod/
│   ├── Tur_WholePlant_or_Canopy/
│   └── Not_Tur_or_Unsupported/
└── test/
    ├── Tur_Leaf/
    ├── Tur_Pod/
    ├── Tur_WholePlant_or_Canopy/
    └── Not_Tur_or_Unsupported/
```

---

## 4. Model Training & Export Pipeline

The training pipeline is pre-implemented in:
[`ml/training/train_pigeonpea_organ_detector.py`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/ml/training/train_pigeonpea_organ_detector.py)

### Execution Command:
```bash
python ml/training/train_pigeonpea_organ_detector.py \
  --dataset-dir datasets/pigeonpea_organ_dataset \
  --output-dir models/organ_detector \
  --epochs 20 \
  --batch-size 32
```

### Export to Mobile TFLite:
The script exports:
1. PyTorch weights: `models/organ_detector/pigeonpea_organ_mobilenetv3.pth`
2. ONNX graph: `models/organ_detector/pigeonpea_organ_mobilenetv3.onnx`
3. INT8 Quantized TFLite: `mobile/assets/models/pigeonpea_organ_detector.tflite` (target size: $\approx 2.5\text{ MB}$)

---

## 5. Native Android Build Requirements

To compile the real-time frame processor onto a physical Android device:

### Prerequisites:
1. **JDK 17:** Install OpenJDK 17 and configure `JAVA_HOME`.
2. **Android SDK:** Install Android Studio, Android SDK Build-Tools (API 34/35), and CMake/NDK. Set `ANDROID_HOME`.
3. **Expo Prebuild:**
   ```bash
   cd mobile
   npx expo prebuild --platform android
   ```
4. **Compile Development APK:**
   ```bash
   npx expo run:android --variant debug
   ```
   Or cloud build via EAS:
   ```bash
   eas build --profile development --platform android
   ```

---

## 6. Physical Device Testing Checklist

When the Development Build APK is installed on the physical Android device:

1. **Manual Mode Verification:**
   - Tap Camera action. Verify the viewfinder displays the golden reticle HUD with **Manual Mode** (`मॅन्युअल मोड` / `मैनुअल मोड`).
   - Tap manual shutter button. Photo captures and opens in preview screen.
   - Tap **Use This Photo**. Verify image uploads to backend and prediction displays.
2. **Organ Rejection Tests:**
   - Present Tur Pods to camera $\to$ State machine remains in `SEARCHING`, stability stays 0.
   - Present Distant Canopy $\to$ State machine remains in `SEARCHING`, stability stays 0.
   - Present Non-Tur leaf (cotton/soybean) $\to$ State machine remains in `SEARCHING`.
3. **Clarity & Motion Tests:**
   - Move camera quickly $\to$ Reticle turns red with **Hold Steady** badge (`स्पष्टता तपासा`).
4. **Automatic Leaf Capture Test:**
   - Hold steady over a genuine Tur leaf inside reticle.
   - Reticle turns amber (**Leaf Detected** $\to$ stability counter counts 1..2..3..4..5).
   - Upon reaching 5 frames, reticle turns green (**Capturing...**) and automatically takes the photo without pressing the shutter button.
   - Review screen opens with **Retake** and **Use This Photo**.
