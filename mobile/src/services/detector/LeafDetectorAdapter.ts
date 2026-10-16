/**
 * TurSathi AI — Leaf Detector Adapter Contract & Evaluation Engine
 *
 * Provides a typed interface and validation gate for on-device pigeonpea (Tur)
 * leaf detection models.
 *
 * CANONICAL REJECTION & VALIDATION RULES:
 * 1. Target organ must be 'Tur_Leaf' (rejects 'Tur_Pod', 'Tur_WholePlant_or_Canopy', 'Not_Tur_or_Unsupported').
 * 2. Detection confidence must meet or exceed minConfidence threshold (default: 0.85).
 * 3. Subject must be centrally framed within the targeting reticle.
 * 4. Image must be sharp (rejects blur, motion, or severe defocus).
 * 5. Lighting must be adequate (rejects underexposed/overexposed frames).
 *
 * RUNTIME AVAILABILITY:
 * In the standard Expo Go / expo-camera environment, per-frame real-time ML execution
 * is not natively supported, and no on-device .tflite leaf-organ checkpoint exists in the bundle.
 * The adapter honestly reports isAvailable = false until a native development build
 * with a genuine trained TFLite model is provided.
 */

import type { QualityRejectionReason, SimulatedFrameResult } from './useAutoCaptureStateMachine';

export type PigeonpeaOrganClass =
  | 'Tur_Leaf'
  | 'Tur_Pod'
  | 'Tur_WholePlant_or_Canopy'
  | 'Not_Tur_or_Unsupported';

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface LeafDetectionResult {
  detectedClass: PigeonpeaOrganClass;
  confidence: number;
  isSharp: boolean;
  isLightingAcceptable: boolean;
  isCentrallyFramed: boolean;
  blurScore?: number;
  brightnessScore?: number;
  boundingBox?: BoundingBox;
}

export interface LeafDetectorStatus {
  isAvailable: boolean;
  engine: 'NONE' | 'TFLITE_VISION_CAMERA' | 'ONNX_RUNTIME';
  modelPath: string | null;
  supportedClasses: readonly PigeonpeaOrganClass[];
  unavailabilityReason: string;
}

export class LeafDetectorAdapter {
  public static readonly SUPPORTED_CLASSES: readonly PigeonpeaOrganClass[] = [
    'Tur_Leaf',
    'Tur_Pod',
    'Tur_WholePlant_or_Canopy',
    'Not_Tur_or_Unsupported',
  ] as const;

  /**
   * Inspects the device runtime and model bundle to determine whether
   * a genuine on-device organ detector model is loaded and ready.
   */
  public static checkAvailability(): LeafDetectorStatus {
    // Current reality: The project contains server-side PyTorch .pth models for disease
    // classification on the FastAPI backend, but no on-device .tflite leaf-organ detector.
    // Additionally, Expo Go does not support continuous camera frame processors.
    return {
      isAvailable: false,
      engine: 'NONE',
      modelPath: null,
      supportedClasses: LeafDetectorAdapter.SUPPORTED_CLASSES,
      unavailabilityReason:
        'No trained on-device Pigeonpea organ detector model (.tflite) is installed. Real-time frame processing requires an Expo Development Build with react-native-vision-camera and react-native-fast-tflite.',
    };
  }

  /**
   * Evaluates a frame detection against all automatic capture conditions.
   *
   * Rejection criteria:
   * - Non-leaf organ (pod, whole plant, canopy, unsupported crop) -> isLeafDetected: false
   * - Confidence below threshold -> isLeafDetected: false
   * - Blur or camera shake -> rejectionReason: 'BLUR'
   * - Inadequate illumination -> rejectionReason: 'BAD_LIGHTING'
   * - Out of reticle bounds -> rejectionReason: 'OUT_OF_BOUNDS'
   */
  public static evaluateFrame(
    detection: LeafDetectionResult,
    minConfidence: number = 0.85,
  ): SimulatedFrameResult {
    // 1. Organ class validation: ONLY Tur_Leaf is eligible for disease scanning
    if (detection.detectedClass !== 'Tur_Leaf') {
      return {
        isLeafDetected: false,
        confidence: detection.confidence,
        isSharp: detection.isSharp,
        isLightingAcceptable: detection.isLightingAcceptable,
        rejectionReason: null,
      };
    }

    // 2. Confidence threshold
    if (detection.confidence < minConfidence) {
      return {
        isLeafDetected: false,
        confidence: detection.confidence,
        isSharp: detection.isSharp,
        isLightingAcceptable: detection.isLightingAcceptable,
        rejectionReason: null,
      };
    }

    // 3. Framing / bounds check (leaf must be centered inside reticle)
    if (!detection.isCentrallyFramed) {
      return {
        isLeafDetected: true,
        confidence: detection.confidence,
        isSharp: detection.isSharp,
        isLightingAcceptable: detection.isLightingAcceptable,
        rejectionReason: 'OUT_OF_BOUNDS',
      };
    }

    // 4. Sharpness assessment
    if (!detection.isSharp) {
      return {
        isLeafDetected: true,
        confidence: detection.confidence,
        isSharp: false,
        isLightingAcceptable: detection.isLightingAcceptable,
        rejectionReason: 'BLUR',
      };
    }

    // 5. Lighting assessment
    if (!detection.isLightingAcceptable) {
      return {
        isLeafDetected: true,
        confidence: detection.confidence,
        isSharp: true,
        isLightingAcceptable: false,
        rejectionReason: 'BAD_LIGHTING',
      };
    }

    // All conditions satisfied: genuine Tur_Leaf candidate ready for stability progression
    return {
      isLeafDetected: true,
      confidence: detection.confidence,
      isSharp: true,
      isLightingAcceptable: true,
      rejectionReason: null,
    };
  }
}
