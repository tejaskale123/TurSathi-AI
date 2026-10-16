import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import {
  AutoCaptureController,
} from '../src/services/detector/useAutoCaptureStateMachine.ts';
import {
  LeafDetectorAdapter,
} from '../src/services/detector/LeafDetectorAdapter.ts';
import type { LeafDetectionResult } from '../src/services/detector/LeafDetectorAdapter.ts';

describe('Leaf Detector Adapter & Auto-Capture Integration Suite', () => {
  test('1. Detector availability check honestly reports absence of on-device TFLite model', () => {
    const status = LeafDetectorAdapter.checkAvailability();
    assert.equal(status.isAvailable, false);
    assert.equal(status.engine, 'NONE');
    assert.equal(status.modelPath, null);
    assert.deepEqual(status.supportedClasses, [
      'Tur_Leaf',
      'Tur_Pod',
      'Tur_WholePlant_or_Canopy',
      'Not_Tur_or_Unsupported',
    ]);
    assert.ok(status.unavailabilityReason.includes('No trained on-device Pigeonpea organ detector model'));
  });

  test('2. Rejection of Tur_Pod: resets stability counter immediately', () => {
    const controller = new AutoCaptureController({
      autoCaptureEnabled: true,
      isDetectorAvailable: true,
      requiredStableFrames: 5,
    });

    // Seed with 2 valid Tur_Leaf frames
    const validLeaf: LeafDetectionResult = {
      detectedClass: 'Tur_Leaf',
      confidence: 0.94,
      isSharp: true,
      isLightingAcceptable: true,
      isCentrallyFramed: true,
    };
    controller.processFrame(LeafDetectorAdapter.evaluateFrame(validLeaf));
    controller.processFrame(LeafDetectorAdapter.evaluateFrame(validLeaf));
    assert.equal(controller.state.stableFramesCount, 2);

    // Present a Tur_Pod
    const podDetection: LeafDetectionResult = {
      detectedClass: 'Tur_Pod',
      confidence: 0.96,
      isSharp: true,
      isLightingAcceptable: true,
      isCentrallyFramed: true,
    };
    const evalResult = LeafDetectorAdapter.evaluateFrame(podDetection);
    assert.equal(evalResult.isLeafDetected, false);

    controller.processFrame(evalResult);
    assert.equal(controller.state.state, 'SEARCHING');
    assert.equal(controller.state.stableFramesCount, 0);
  });

  test('3. Rejection of Tur_WholePlant_or_Canopy: resets stability counter immediately', () => {
    const controller = new AutoCaptureController({
      autoCaptureEnabled: true,
      isDetectorAvailable: true,
      requiredStableFrames: 5,
    });

    // Seed 1 valid leaf
    controller.processFrame(LeafDetectorAdapter.evaluateFrame({
      detectedClass: 'Tur_Leaf',
      confidence: 0.91,
      isSharp: true,
      isLightingAcceptable: true,
      isCentrallyFramed: true,
    }));
    assert.equal(controller.state.stableFramesCount, 1);

    // Present canopy / distant view
    const canopyDetection: LeafDetectionResult = {
      detectedClass: 'Tur_WholePlant_or_Canopy',
      confidence: 0.88,
      isSharp: true,
      isLightingAcceptable: true,
      isCentrallyFramed: true,
    };
    const evalResult = LeafDetectorAdapter.evaluateFrame(canopyDetection);
    assert.equal(evalResult.isLeafDetected, false);

    controller.processFrame(evalResult);
    assert.equal(controller.state.state, 'SEARCHING');
    assert.equal(controller.state.stableFramesCount, 0);
  });

  test('4. Rejection of Not_Tur_or_Unsupported crop: resets stability counter immediately', () => {
    const controller = new AutoCaptureController({
      autoCaptureEnabled: true,
      isDetectorAvailable: true,
      requiredStableFrames: 5,
    });

    const nonTurDetection: LeafDetectionResult = {
      detectedClass: 'Not_Tur_or_Unsupported',
      confidence: 0.99,
      isSharp: true,
      isLightingAcceptable: true,
      isCentrallyFramed: true,
    };
    const evalResult = LeafDetectorAdapter.evaluateFrame(nonTurDetection);
    assert.equal(evalResult.isLeafDetected, false);

    controller.processFrame(evalResult);
    assert.equal(controller.state.state, 'SEARCHING');
    assert.equal(controller.state.stableFramesCount, 0);
  });

  test('5. Blur rejection: identifies blur and triggers QUALITY_REJECTED state', () => {
    const controller = new AutoCaptureController({
      autoCaptureEnabled: true,
      isDetectorAvailable: true,
      requiredStableFrames: 3,
    });

    const blurryLeaf: LeafDetectionResult = {
      detectedClass: 'Tur_Leaf',
      confidence: 0.92,
      isSharp: false,
      isLightingAcceptable: true,
      isCentrallyFramed: true,
    };
    const evalResult = LeafDetectorAdapter.evaluateFrame(blurryLeaf);
    assert.equal(evalResult.isLeafDetected, true);
    assert.equal(evalResult.isSharp, false);
    assert.equal(evalResult.rejectionReason, 'BLUR');

    controller.processFrame(evalResult);
    assert.equal(controller.state.state, 'QUALITY_REJECTED');
    assert.equal(controller.state.rejectionReason, 'BLUR');
    assert.equal(controller.state.stableFramesCount, 0);
  });

  test('6. Lighting rejection: identifies unsuitable illumination', () => {
    const controller = new AutoCaptureController({
      autoCaptureEnabled: true,
      isDetectorAvailable: true,
      requiredStableFrames: 3,
    });

    const badLightingLeaf: LeafDetectionResult = {
      detectedClass: 'Tur_Leaf',
      confidence: 0.90,
      isSharp: true,
      isLightingAcceptable: false,
      isCentrallyFramed: true,
    };
    const evalResult = LeafDetectorAdapter.evaluateFrame(badLightingLeaf);
    assert.equal(evalResult.isLeafDetected, true);
    assert.equal(evalResult.isLightingAcceptable, false);
    assert.equal(evalResult.rejectionReason, 'BAD_LIGHTING');

    controller.processFrame(evalResult);
    assert.equal(controller.state.state, 'QUALITY_REJECTED');
    assert.equal(controller.state.rejectionReason, 'BAD_LIGHTING');
  });

  test('7. Out-of-bounds rejection: leaf not framed within reticle', () => {
    const uncenteredLeaf: LeafDetectionResult = {
      detectedClass: 'Tur_Leaf',
      confidence: 0.95,
      isSharp: true,
      isLightingAcceptable: true,
      isCentrallyFramed: false,
    };
    const evalResult = LeafDetectorAdapter.evaluateFrame(uncenteredLeaf);
    assert.equal(evalResult.isLeafDetected, true);
    assert.equal(evalResult.rejectionReason, 'OUT_OF_BOUNDS');
  });

  test('8. Consecutive valid frames progress to CAPTURE_READY and fire automatic trigger', () => {
    const controller = new AutoCaptureController({
      autoCaptureEnabled: true,
      isDetectorAvailable: true,
      requiredStableFrames: 4,
      minConfidence: 0.85,
    });

    const validLeaf: LeafDetectionResult = {
      detectedClass: 'Tur_Leaf',
      confidence: 0.93,
      isSharp: true,
      isLightingAcceptable: true,
      isCentrallyFramed: true,
    };

    // Frames 1 to 3: LEAF_CANDIDATE
    for (let i = 1; i <= 3; i++) {
      controller.processFrame(LeafDetectorAdapter.evaluateFrame(validLeaf));
      assert.equal(controller.state.state, 'LEAF_CANDIDATE');
      assert.equal(controller.state.stableFramesCount, i);
    }

    // Frame 4: CAPTURE_READY
    controller.processFrame(LeafDetectorAdapter.evaluateFrame(validLeaf));
    assert.equal(controller.state.state, 'CAPTURE_READY');
    assert.equal(controller.state.stableFramesCount, 4);

    // Trigger capture
    const triggered = controller.triggerCapture();
    assert.equal(triggered, true);
    assert.equal(controller.state.state, 'CAPTURING');
    assert.equal(controller.state.isCaptureLocked, true);
  });

  test('9. Capture lock prevents duplicate captures while capture is in flight', () => {
    const controller = new AutoCaptureController({
      autoCaptureEnabled: true,
      isDetectorAvailable: true,
      requiredStableFrames: 1,
    });

    const validLeaf: LeafDetectionResult = {
      detectedClass: 'Tur_Leaf',
      confidence: 0.95,
      isSharp: true,
      isLightingAcceptable: true,
      isCentrallyFramed: true,
    };

    controller.processFrame(LeafDetectorAdapter.evaluateFrame(validLeaf));
    assert.equal(controller.state.state, 'CAPTURE_READY');

    // First trigger succeeds
    const firstTrigger = controller.triggerCapture();
    assert.equal(firstTrigger, true);
    assert.equal(controller.state.isCaptureLocked, true);

    // Second trigger fails due to lock
    const secondTrigger = controller.triggerCapture();
    assert.equal(secondTrigger, false);

    // Further frames are ignored while locked
    controller.processFrame(LeafDetectorAdapter.evaluateFrame(validLeaf));
    assert.equal(controller.state.state, 'CAPTURING');
  });

  test('10. Camera cleanup and recovery: reset clears locks and errors', () => {
    const controller = new AutoCaptureController({
      autoCaptureEnabled: true,
      isDetectorAvailable: true,
    });

    controller.notifyError('Camera hardware timeout');
    assert.equal(controller.state.state, 'ERROR');

    // Resetting when camera is closed
    controller.reset();
    assert.equal(controller.state.state, 'SEARCHING');
    assert.equal(controller.state.stableFramesCount, 0);
    assert.equal(controller.state.isCaptureLocked, false);
    assert.equal(controller.state.errorMessage, null);
  });

  test('11. Captured-image handoff to preview and upload pipeline with cooldown', () => {
    const controller = new AutoCaptureController({
      autoCaptureEnabled: true,
      isDetectorAvailable: true,
      requiredStableFrames: 1,
      cooldownMs: 50,
    });

    // Reach CAPTURING
    controller.processFrame(LeafDetectorAdapter.evaluateFrame({
      detectedClass: 'Tur_Leaf',
      confidence: 0.90,
      isSharp: true,
      isLightingAcceptable: true,
      isCentrallyFramed: true,
    }));
    controller.triggerCapture();
    assert.equal(controller.state.state, 'CAPTURING');

    // Photo captured and saved -> transitions to UPLOADING / preview
    controller.notifyCaptureSuccess();
    assert.equal(controller.state.state, 'UPLOADING');

    // Backend analysis complete -> RESULT_READY engages cooldown
    controller.notifyResultReady();
    assert.equal(controller.state.state, 'RESULT_READY');
    assert.equal(controller.state.isInCooldown, true);
  });
});
