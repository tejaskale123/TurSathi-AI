import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import {
  AutoCaptureController,
  DEFAULT_AUTO_CAPTURE_CONFIG,
} from '../src/services/detector/useAutoCaptureStateMachine.ts';

describe('Auto-Capture State Machine Test Suite', () => {
  test('1. Automatic capture is strictly disabled by default', () => {
    const controller = new AutoCaptureController();
    const state = controller.state;

    assert.equal(state.state, 'DETECTOR_UNAVAILABLE');
    assert.equal(state.autoCaptureEnabled, false);
    assert.equal(state.isDetectorAvailable, false);
    assert.equal(state.stableFramesCount, 0);
    assert.equal(state.isCaptureLocked, false);

    // Simulated frame is completely ignored when disabled
    const afterFrame = controller.processFrame({
      isLeafDetected: true,
      confidence: 0.99,
      isSharp: true,
      isLightingAcceptable: true,
    });
    assert.equal(afterFrame.state, 'DETECTOR_UNAVAILABLE');
    assert.equal(afterFrame.stableFramesCount, 0);
  });

  test('2. Detector-unavailable fallback requires BOTH enablement and detector presence', () => {
    // Only enabled, but no detector
    const c1 = new AutoCaptureController({ autoCaptureEnabled: true, isDetectorAvailable: false });
    assert.equal(c1.state.state, 'DETECTOR_UNAVAILABLE');

    // Detector present, but auto-capture not enabled
    const c2 = new AutoCaptureController({ autoCaptureEnabled: false, isDetectorAvailable: true });
    assert.equal(c2.state.state, 'DETECTOR_UNAVAILABLE');

    // Both present -> starts in SEARCHING
    const c3 = new AutoCaptureController({ autoCaptureEnabled: true, isDetectorAvailable: true });
    assert.equal(c3.state.state, 'SEARCHING');

    // Dynamically toggling enablement
    c1.setDetectorAvailable(true);
    assert.equal(c1.state.state, 'SEARCHING');
    c1.setEnabled(false);
    assert.equal(c1.state.state, 'DETECTOR_UNAVAILABLE');
  });

  test('3. State transitions: SEARCHING -> LEAF_CANDIDATE -> CAPTURE_READY', () => {
    const controller = new AutoCaptureController({
      autoCaptureEnabled: true,
      isDetectorAvailable: true,
      requiredStableFrames: 3,
      minConfidence: 0.85,
    });

    assert.equal(controller.state.state, 'SEARCHING');

    // Frame 1: Valid leaf detected
    controller.processFrame({
      isLeafDetected: true,
      confidence: 0.90,
      isSharp: true,
      isLightingAcceptable: true,
    });
    assert.equal(controller.state.state, 'LEAF_CANDIDATE');
    assert.equal(controller.state.stableFramesCount, 1);

    // Frame 2: Valid leaf detected
    controller.processFrame({
      isLeafDetected: true,
      confidence: 0.92,
      isSharp: true,
      isLightingAcceptable: true,
    });
    assert.equal(controller.state.state, 'LEAF_CANDIDATE');
    assert.equal(controller.state.stableFramesCount, 2);

    // Frame 3: Reaches threshold (3/3)
    controller.processFrame({
      isLeafDetected: true,
      confidence: 0.95,
      isSharp: true,
      isLightingAcceptable: true,
    });
    assert.equal(controller.state.state, 'CAPTURE_READY');
    assert.equal(controller.state.stableFramesCount, 3);
  });

  test('4. Stability counter resets immediately on low confidence or lost subject', () => {
    const controller = new AutoCaptureController({
      autoCaptureEnabled: true,
      isDetectorAvailable: true,
      requiredStableFrames: 4,
      minConfidence: 0.85,
    });

    // 2 consecutive good frames
    controller.processFrame({ isLeafDetected: true, confidence: 0.90, isSharp: true, isLightingAcceptable: true });
    controller.processFrame({ isLeafDetected: true, confidence: 0.91, isSharp: true, isLightingAcceptable: true });
    assert.equal(controller.state.stableFramesCount, 2);

    // Frame 3: Confidence drops below 0.85
    controller.processFrame({ isLeafDetected: true, confidence: 0.60, isSharp: true, isLightingAcceptable: true });
    assert.equal(controller.state.state, 'SEARCHING');
    assert.equal(controller.state.stableFramesCount, 0);

    // Frame 4: No leaf detected
    controller.processFrame({ isLeafDetected: false, confidence: 0.10, isSharp: true, isLightingAcceptable: true });
    assert.equal(controller.state.state, 'SEARCHING');
    assert.equal(controller.state.stableFramesCount, 0);
  });

  test('5. Quality rejection handles blur and bad lighting with counter reset', () => {
    const controller = new AutoCaptureController({
      autoCaptureEnabled: true,
      isDetectorAvailable: true,
      requiredStableFrames: 3,
    });

    // Valid frame first
    controller.processFrame({ isLeafDetected: true, confidence: 0.92, isSharp: true, isLightingAcceptable: true });
    assert.equal(controller.state.stableFramesCount, 1);

    // Motion blur detected
    controller.processFrame({
      isLeafDetected: true,
      confidence: 0.92,
      isSharp: false,
      isLightingAcceptable: true,
    });
    assert.equal(controller.state.state, 'QUALITY_REJECTED');
    assert.equal(controller.state.rejectionReason, 'BLUR');
    assert.equal(controller.state.stableFramesCount, 0);

    // Harsh glare / underexposure
    controller.processFrame({
      isLeafDetected: true,
      confidence: 0.90,
      isSharp: true,
      isLightingAcceptable: false,
    });
    assert.equal(controller.state.state, 'QUALITY_REJECTED');
    assert.equal(controller.state.rejectionReason, 'BAD_LIGHTING');
    assert.equal(controller.state.stableFramesCount, 0);
  });

  test('6. Capture lock prevents duplicate shutter triggers', () => {
    const controller = new AutoCaptureController({
      autoCaptureEnabled: true,
      isDetectorAvailable: true,
      requiredStableFrames: 2,
    });

    // Drive to CAPTURE_READY
    controller.processFrame({ isLeafDetected: true, confidence: 0.95, isSharp: true, isLightingAcceptable: true });
    controller.processFrame({ isLeafDetected: true, confidence: 0.95, isSharp: true, isLightingAcceptable: true });
    assert.equal(controller.state.state, 'CAPTURE_READY');

    // First trigger succeeds
    const firstTrigger = controller.triggerCapture();
    assert.equal(firstTrigger, true);
    assert.equal(controller.state.state, 'CAPTURING');
    assert.equal(controller.state.isCaptureLocked, true);

    // Duplicate trigger is rejected
    const secondTrigger = controller.triggerCapture();
    assert.equal(secondTrigger, false);
    assert.equal(controller.state.state, 'CAPTURING');

    // Subsequent frames during CAPTURING are locked out and do not alter state
    controller.processFrame({ isLeafDetected: true, confidence: 0.99, isSharp: true, isLightingAcceptable: true });
    assert.equal(controller.state.state, 'CAPTURING');
    assert.equal(controller.state.isCaptureLocked, true);
  });

  test('7. End-to-end capture lifecycle: CAPTURING -> UPLOADING -> RESULT_READY -> Cooldown', () => {
    const controller = new AutoCaptureController({
      autoCaptureEnabled: true,
      isDetectorAvailable: true,
      requiredStableFrames: 1,
      cooldownMs: 500,
    });

    controller.processFrame({ isLeafDetected: true, confidence: 0.95, isSharp: true, isLightingAcceptable: true });
    assert.equal(controller.state.state, 'CAPTURE_READY');

    controller.triggerCapture();
    assert.equal(controller.state.state, 'CAPTURING');

    controller.notifyCaptureSuccess();
    assert.equal(controller.state.state, 'UPLOADING');

    controller.notifyResultReady();
    assert.equal(controller.state.state, 'RESULT_READY');
    assert.equal(controller.state.isInCooldown, true);

    // During cooldown, frames are ignored
    controller.processFrame({ isLeafDetected: true, confidence: 0.99, isSharp: true, isLightingAcceptable: true });
    assert.equal(controller.state.state, 'RESULT_READY');
  });

  test('8. Error handling and retry recovery', () => {
    const controller = new AutoCaptureController({
      autoCaptureEnabled: true,
      isDetectorAvailable: true,
      requiredStableFrames: 1,
    });

    controller.processFrame({ isLeafDetected: true, confidence: 0.95, isSharp: true, isLightingAcceptable: true });
    controller.triggerCapture();
    controller.notifyCaptureSuccess();

    // Network error during upload
    controller.notifyError('Network connection timed out');
    assert.equal(controller.state.state, 'ERROR');
    assert.equal(controller.state.errorMessage, 'Network connection timed out');
    assert.equal(controller.state.isCaptureLocked, false);

    // Retry resets error and returns to SEARCHING
    controller.retry();
    assert.equal(controller.state.state, 'SEARCHING');
    assert.equal(controller.state.errorMessage, null);
    assert.equal(controller.state.stableFramesCount, 0);
  });

  test('9. Reset clears all locks, errors, and cooldowns', () => {
    const controller = new AutoCaptureController({
      autoCaptureEnabled: true,
      isDetectorAvailable: true,
    });

    controller.notifyError('Fatal error');
    assert.equal(controller.state.state, 'ERROR');

    controller.reset();
    assert.equal(controller.state.state, 'SEARCHING');
    assert.equal(controller.state.errorMessage, null);
    assert.equal(controller.state.isCaptureLocked, false);
    assert.equal(controller.state.isInCooldown, false);
  });
});
