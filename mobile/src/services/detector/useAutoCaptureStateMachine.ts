/**
 * TurSathi AI — Isolated Auto-Capture State Machine (Phase 3)
 *
 * ARCHITECTURAL CONSTRAINTS:
 * 1. This state machine manages simulated/mocked frame events ONLY.
 * 2. It does NOT invoke a real ML detector or claim live on-device predictions.
 * 3. Automatic capture is DISABLED BY DEFAULT (autoCaptureEnabled = false).
 * 4. Detector availability defaults to false (isDetectorAvailable = false).
 * 5. This module is completely decoupled from the live camera and backend pipeline.
 */

import { useCallback, useEffect, useReducer, useRef } from 'react';

// ==============================================================================
// State Taxonomy
// ==============================================================================

export type AutoCaptureState =
  | 'DETECTOR_UNAVAILABLE'
  | 'SEARCHING'
  | 'LEAF_CANDIDATE'
  | 'QUALITY_REJECTED'
  | 'CAPTURE_READY'
  | 'CAPTURING'
  | 'UPLOADING'
  | 'RESULT_READY'
  | 'ERROR';

export type QualityRejectionReason =
  | 'BLUR'
  | 'BAD_LIGHTING'
  | 'MOTION'
  | 'OUT_OF_BOUNDS'
  | null;

// ==============================================================================
// Data Contracts
// ==============================================================================

export interface SimulatedFrameResult {
  isLeafDetected: boolean;
  confidence: number;
  isSharp?: boolean;
  isLightingAcceptable?: boolean;
  rejectionReason?: QualityRejectionReason;
}

export interface AutoCaptureConfig {
  /** Master toggle: auto capture must be explicitly enabled by user/config */
  autoCaptureEnabled: boolean;
  /** Whether the underlying detector model is verified and available on device */
  isDetectorAvailable: boolean;
  /** Number of consecutive valid, sharp frames required before firing shutter */
  requiredStableFrames: number;
  /** Cooldown time after capture completion before re-arming (milliseconds) */
  cooldownMs: number;
  /** Minimum detection confidence score to qualify as a leaf candidate */
  minConfidence: number;
}

export const DEFAULT_AUTO_CAPTURE_CONFIG: AutoCaptureConfig = {
  autoCaptureEnabled: false, // STRICT SAFETY DEFAULT: OFF
  isDetectorAvailable: false, // STRICT SAFETY DEFAULT: UNAVAILABLE
  requiredStableFrames: 5,
  cooldownMs: 3000,
  minConfidence: 0.85,
};

export interface AutoCaptureMachineState {
  state: AutoCaptureState;
  stableFramesCount: number;
  requiredStableFrames: number;
  isCaptureLocked: boolean;
  isInCooldown: boolean;
  rejectionReason: QualityRejectionReason;
  errorMessage: string | null;
  lastConfidence: number;
  autoCaptureEnabled: boolean;
  isDetectorAvailable: boolean;
}

// ==============================================================================
// Actions & Deterministic Transitions
// ==============================================================================

export type AutoCaptureAction =
  | { type: 'FRAME_EVALUATED'; payload: SimulatedFrameResult }
  | { type: 'TRIGGER_CAPTURE' }
  | { type: 'CAPTURE_SUCCESS' }
  | { type: 'RESULT_READY' }
  | { type: 'CAPTURE_ERROR'; payload: { message: string } }
  | { type: 'RESET' }
  | { type: 'RETRY' }
  | { type: 'SET_COOLDOWN_EXPIRED' }
  | { type: 'SET_ENABLED'; payload: boolean }
  | { type: 'SET_DETECTOR_AVAILABLE'; payload: boolean };

export function autoCaptureReducer(
  state: AutoCaptureMachineState,
  action: AutoCaptureAction,
  config: AutoCaptureConfig = DEFAULT_AUTO_CAPTURE_CONFIG,
): AutoCaptureMachineState {
  switch (action.type) {
    case 'SET_ENABLED': {
      const newEnabled = action.payload;
      const isReady = newEnabled && state.isDetectorAvailable;
      return {
        ...state,
        autoCaptureEnabled: newEnabled,
        state: isReady ? 'SEARCHING' : 'DETECTOR_UNAVAILABLE',
        stableFramesCount: 0,
        isCaptureLocked: false,
        rejectionReason: null,
        errorMessage: null,
      };
    }

    case 'SET_DETECTOR_AVAILABLE': {
      const newAvailable = action.payload;
      const isReady = state.autoCaptureEnabled && newAvailable;
      return {
        ...state,
        isDetectorAvailable: newAvailable,
        state: isReady ? 'SEARCHING' : 'DETECTOR_UNAVAILABLE',
        stableFramesCount: 0,
        isCaptureLocked: false,
        rejectionReason: null,
        errorMessage: null,
      };
    }

    case 'FRAME_EVALUATED': {
      // 1. Guard against non-scanning or locked states
      if (
        !state.autoCaptureEnabled ||
        !state.isDetectorAvailable ||
        state.isCaptureLocked ||
        state.isInCooldown ||
        state.state === 'CAPTURING' ||
        state.state === 'UPLOADING' ||
        state.state === 'RESULT_READY' ||
        state.state === 'ERROR'
      ) {
        return state;
      }

      const frame = action.payload;
      const meetsConfidence =
        frame.isLeafDetected && frame.confidence >= config.minConfidence;

      // 2. Not detected or low confidence -> revert to SEARCHING
      if (!meetsConfidence) {
        return {
          ...state,
          state: 'SEARCHING',
          stableFramesCount: 0,
          rejectionReason: null,
          lastConfidence: frame.confidence,
        };
      }

      // 3. Quality evaluation (sharpness and lighting)
      const isSharp = frame.isSharp !== false;
      const isLightOk = frame.isLightingAcceptable !== false;

      if (!isSharp || !isLightOk) {
        const reason: QualityRejectionReason = !isSharp
          ? 'BLUR'
          : !isLightOk
            ? 'BAD_LIGHTING'
            : frame.rejectionReason || 'MOTION';
        return {
          ...state,
          state: 'QUALITY_REJECTED',
          stableFramesCount: 0,
          rejectionReason: reason,
          lastConfidence: frame.confidence,
        };
      }

      // 4. Stable frame progression
      const nextStableCount = state.stableFramesCount + 1;
      const isReady = nextStableCount >= state.requiredStableFrames;

      return {
        ...state,
        state: isReady ? 'CAPTURE_READY' : 'LEAF_CANDIDATE',
        stableFramesCount: nextStableCount,
        rejectionReason: null,
        lastConfidence: frame.confidence,
      };
    }

    case 'TRIGGER_CAPTURE': {
      // Shutter can only be triggered from CAPTURE_READY and when not locked
      if (state.state !== 'CAPTURE_READY' || state.isCaptureLocked) {
        return state;
      }

      return {
        ...state,
        state: 'CAPTURING',
        isCaptureLocked: true, // ENGAGE LOCK IMMEDIATELY
      };
    }

    case 'CAPTURE_SUCCESS': {
      if (state.state !== 'CAPTURING') {
        return state;
      }
      return {
        ...state,
        state: 'UPLOADING',
      };
    }

    case 'RESULT_READY': {
      return {
        ...state,
        state: 'RESULT_READY',
        isInCooldown: true, // Engage cooldown upon result readiness
      };
    }

    case 'CAPTURE_ERROR': {
      return {
        ...state,
        state: 'ERROR',
        isCaptureLocked: false,
        errorMessage: action.payload.message,
      };
    }

    case 'RESET': {
      const isReady = state.autoCaptureEnabled && state.isDetectorAvailable;
      return {
        ...state,
        state: isReady ? 'SEARCHING' : 'DETECTOR_UNAVAILABLE',
        stableFramesCount: 0,
        isCaptureLocked: false,
        isInCooldown: false,
        rejectionReason: null,
        errorMessage: null,
      };
    }

    case 'RETRY': {
      if (state.state !== 'ERROR') {
        return state;
      }
      const isReady = state.autoCaptureEnabled && state.isDetectorAvailable;
      return {
        ...state,
        state: isReady ? 'SEARCHING' : 'DETECTOR_UNAVAILABLE',
        stableFramesCount: 0,
        isCaptureLocked: false,
        errorMessage: null,
      };
    }

    case 'SET_COOLDOWN_EXPIRED': {
      return {
        ...state,
        isInCooldown: false,
      };
    }

    default:
      return state;
  }
}

// ==============================================================================
// Pure Controller (For deterministic testing outside React)
// ==============================================================================

export class AutoCaptureController {
  private _state: AutoCaptureMachineState;
  private _config: AutoCaptureConfig;
  private _cooldownTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(customConfig?: Partial<AutoCaptureConfig>) {
    this._config = { ...DEFAULT_AUTO_CAPTURE_CONFIG, ...customConfig };
    this._state = {
      state:
        this._config.autoCaptureEnabled && this._config.isDetectorAvailable
          ? 'SEARCHING'
          : 'DETECTOR_UNAVAILABLE',
      stableFramesCount: 0,
      requiredStableFrames: this._config.requiredStableFrames,
      isCaptureLocked: false,
      isInCooldown: false,
      rejectionReason: null,
      errorMessage: null,
      lastConfidence: 0,
      autoCaptureEnabled: this._config.autoCaptureEnabled,
      isDetectorAvailable: this._config.isDetectorAvailable,
    };
  }

  public get state(): AutoCaptureMachineState {
    return { ...this._state };
  }

  public dispatch(action: AutoCaptureAction): AutoCaptureMachineState {
    this._state = autoCaptureReducer(this._state, action, this._config);
    return this.state;
  }

  public processFrame(frame: SimulatedFrameResult): AutoCaptureMachineState {
    return this.dispatch({ type: 'FRAME_EVALUATED', payload: frame });
  }

  public triggerCapture(): boolean {
    if (this._state.state !== 'CAPTURE_READY' || this._state.isCaptureLocked) {
      return false;
    }
    this.dispatch({ type: 'TRIGGER_CAPTURE' });
    return true;
  }

  public notifyCaptureSuccess(): void {
    this.dispatch({ type: 'CAPTURE_SUCCESS' });
  }

  public notifyResultReady(): void {
    this.dispatch({ type: 'RESULT_READY' });
    this._startCooldown();
  }

  public notifyError(message: string): void {
    this.dispatch({ type: 'CAPTURE_ERROR', payload: { message } });
  }

  public reset(): void {
    if (this._cooldownTimer) {
      clearTimeout(this._cooldownTimer);
      this._cooldownTimer = null;
    }
    this.dispatch({ type: 'RESET' });
  }

  public retry(): void {
    this.dispatch({ type: 'RETRY' });
  }

  public setEnabled(enabled: boolean): void {
    this._config.autoCaptureEnabled = enabled;
    this.dispatch({ type: 'SET_ENABLED', payload: enabled });
  }

  public setDetectorAvailable(available: boolean): void {
    this._config.isDetectorAvailable = available;
    this.dispatch({ type: 'SET_DETECTOR_AVAILABLE', payload: available });
  }

  private _startCooldown(): void {
    if (this._cooldownTimer) clearTimeout(this._cooldownTimer);
    this._cooldownTimer = setTimeout(() => {
      this.dispatch({ type: 'SET_COOLDOWN_EXPIRED' });
    }, this._config.cooldownMs);
  }
}

// ==============================================================================
// React Hook Wrapper
// ==============================================================================

export function useAutoCaptureStateMachine(
  customConfig?: Partial<AutoCaptureConfig>,
) {
  const mergedConfig: AutoCaptureConfig = {
    ...DEFAULT_AUTO_CAPTURE_CONFIG,
    ...customConfig,
  };

  const [machineState, dispatch] = useReducer(
    (s: AutoCaptureMachineState, a: AutoCaptureAction) =>
      autoCaptureReducer(s, a, mergedConfig),
    {
      state:
        mergedConfig.autoCaptureEnabled && mergedConfig.isDetectorAvailable
          ? 'SEARCHING'
          : 'DETECTOR_UNAVAILABLE',
      stableFramesCount: 0,
      requiredStableFrames: mergedConfig.requiredStableFrames,
      isCaptureLocked: false,
      isInCooldown: false,
      rejectionReason: null,
      errorMessage: null,
      lastConfidence: 0,
      autoCaptureEnabled: mergedConfig.autoCaptureEnabled,
      isDetectorAvailable: mergedConfig.isDetectorAvailable,
    },
  );

  const cooldownTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (cooldownTimerRef.current) {
        clearTimeout(cooldownTimerRef.current);
      }
    };
  }, []);

  const processFrame = useCallback((frame: SimulatedFrameResult) => {
    dispatch({ type: 'FRAME_EVALUATED', payload: frame });
  }, []);

  const triggerCapture = useCallback((): boolean => {
    if (
      machineState.state !== 'CAPTURE_READY' ||
      machineState.isCaptureLocked
    ) {
      return false;
    }
    dispatch({ type: 'TRIGGER_CAPTURE' });
    return true;
  }, [machineState.state, machineState.isCaptureLocked]);

  const notifyCaptureSuccess = useCallback(() => {
    dispatch({ type: 'CAPTURE_SUCCESS' });
  }, []);

  const notifyResultReady = useCallback(() => {
    dispatch({ type: 'RESULT_READY' });
    if (cooldownTimerRef.current) clearTimeout(cooldownTimerRef.current);
    cooldownTimerRef.current = setTimeout(() => {
      dispatch({ type: 'SET_COOLDOWN_EXPIRED' });
    }, mergedConfig.cooldownMs);
  }, [mergedConfig.cooldownMs]);

  const notifyError = useCallback((message: string) => {
    dispatch({ type: 'CAPTURE_ERROR', payload: { message } });
  }, []);

  const reset = useCallback(() => {
    if (cooldownTimerRef.current) {
      clearTimeout(cooldownTimerRef.current);
      cooldownTimerRef.current = null;
    }
    dispatch({ type: 'RESET' });
  }, []);

  const retry = useCallback(() => {
    dispatch({ type: 'RETRY' });
  }, []);

  const setEnabled = useCallback((enabled: boolean) => {
    dispatch({ type: 'SET_ENABLED', payload: enabled });
  }, []);

  const setDetectorAvailable = useCallback((available: boolean) => {
    dispatch({ type: 'SET_DETECTOR_AVAILABLE', payload: available });
  }, []);

  return {
    ...machineState,
    processFrame,
    triggerCapture,
    notifyCaptureSuccess,
    notifyResultReady,
    notifyError,
    reset,
    retry,
    setEnabled,
    setDetectorAvailable,
  };
}
