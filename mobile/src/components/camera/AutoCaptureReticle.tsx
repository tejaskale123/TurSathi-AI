/**
 * TurSathi AI — Auto-Capture Reticle Component (Phase 3)
 *
 * Visual HUD overlay displaying targeting guide brackets, state badges,
 * progress feedback, and localized agricultural instructions for the farmer.
 *
 * Reusable, isolated component with zero dependency on native frame processors.
 */

import React, { useEffect, useRef } from 'react';
import {
  Animated,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useLanguage } from '../../i18n/LanguageContext';
import { Language } from '../../i18n/translations';
import {
  AutoCaptureState,
  QualityRejectionReason,
} from '../../services/detector/useAutoCaptureStateMachine';

// ==============================================================================
// Localized Guidance Strings
// ==============================================================================

interface StateGuidance {
  badge: string;
  instruction: string;
}

const RETICLE_STRINGS: Record<
  Language,
  Record<AutoCaptureState, StateGuidance> & {
    reasons: Record<NonNullable<QualityRejectionReason>, string>;
    progressLabel: string;
  }
> = {
  mr: {
    DETECTOR_UNAVAILABLE: {
      badge: 'मॅन्युअल मोड',
      badgeColor: '#7C8A83',
      instruction: 'फोटो काढण्यासाठी कॅमेरा बटण दाबा',
    },
    SEARCHING: {
      badge: 'शोधत आहे...',
      instruction: 'चौकटीत तुरीचे एकच पान स्पष्ट ठेवा',
    },
    LEAF_CANDIDATE: {
      badge: 'पान आढळले',
      instruction: 'कृपया हात स्थिर ठेवा...',
    },
    QUALITY_REJECTED: {
      badge: 'स्पष्टता तपासा',
      instruction: 'फोटो अस्पष्ट आहे, कॅमेरा स्थिर धरा',
    },
    CAPTURE_READY: {
      badge: 'स्थिर - फोटो काढत आहे',
      instruction: 'हात हलवू नका...',
    },
    CAPTURING: {
      badge: 'फोटो घेतला जात आहे',
      instruction: 'कृपया थांबा...',
    },
    UPLOADING: {
      badge: 'अपलोड होत आहे',
      instruction: 'तूर पानाची तपासणी सुरू आहे...',
    },
    RESULT_READY: {
      badge: 'तपासणी पूर्ण',
      instruction: 'रोग निदान तयार आहे!',
    },
    ERROR: {
      badge: 'त्रुटी',
      instruction: 'पुन्हा प्रयत्न करा',
    },
    reasons: {
      BLUR: 'हात हलल्यामुळे फोटो अस्पष्ट झाला आहे',
      BAD_LIGHTING: 'प्रकाश कमी किंवा जास्त आहे',
      MOTION: 'कॅमेरा हलत आहे, स्थिर धरा',
      OUT_OF_BOUNDS: 'पान चौकटीच्या बाहेर गेले आहे',
    },
    progressLabel: 'स्थिरता:',
  },
  hi: {
    DETECTOR_UNAVAILABLE: {
      badge: 'मैनुअल मोड',
      instruction: 'फोटो खींचने के लिए कैमरा बटन दबाएं',
    },
    SEARCHING: {
      badge: 'खोज रहा है...',
      instruction: 'फ्रेम में तूर की एक पत्ती साफ रखें',
    },
    LEAF_CANDIDATE: {
      badge: 'पत्ती मिली',
      instruction: 'कृपया हाथ स्थिर रखें...',
    },
    QUALITY_REJECTED: {
      badge: 'गुणवत्ता जांचें',
      instruction: 'फोटो धुंधला है, कैमरा स्थिर रखें',
    },
    CAPTURE_READY: {
      badge: 'स्थिर - फोटो ली जा रही है',
      instruction: 'हाथ न हिलाएं...',
    },
    CAPTURING: {
      badge: 'फोटो कैप्चर हो रही है',
      instruction: 'कृपया प्रतीक्षा करें...',
    },
    UPLOADING: {
      badge: 'अपलोड हो रहा है',
      instruction: 'तूर पत्ती की जांच हो रही है...',
    },
    RESULT_READY: {
      badge: 'जांच पूरी',
      instruction: 'रोग विश्लेषण तैयार है!',
    },
    ERROR: {
      badge: 'त्रुटि',
      instruction: 'पुनः प्रयास करें',
    },
    reasons: {
      BLUR: 'हाथ हिलने से फोटो धुंधला हुआ',
      BAD_LIGHTING: 'रोशनी कम या बहुत तेज है',
      MOTION: 'कैमरा हिल रहा है, स्थिर रखें',
      OUT_OF_BOUNDS: 'पत्ती फ्रेम से बाहर है',
    },
    progressLabel: 'स्थिरता:',
  },
  en: {
    DETECTOR_UNAVAILABLE: {
      badge: 'Manual Mode',
      instruction: 'Tap the capture button to take a photo',
    },
    SEARCHING: {
      badge: 'Searching...',
      instruction: 'Place one clear Tur leaf inside the box',
    },
    LEAF_CANDIDATE: {
      badge: 'Leaf Detected',
      instruction: 'Hold camera steady...',
    },
    QUALITY_REJECTED: {
      badge: 'Hold Steady',
      instruction: 'Image is blurry or poorly lit',
    },
    CAPTURE_READY: {
      badge: 'Capturing...',
      instruction: 'Do not move the camera...',
    },
    CAPTURING: {
      badge: 'Capturing Photo',
      instruction: 'Please wait...',
    },
    UPLOADING: {
      badge: 'Uploading',
      instruction: 'Analyzing leaf for disease symptoms...',
    },
    RESULT_READY: {
      badge: 'Diagnosis Ready',
      instruction: 'Analysis complete!',
    },
    ERROR: {
      badge: 'Error',
      instruction: 'Please try again',
    },
    reasons: {
      BLUR: 'Motion blur detected. Hold steady.',
      BAD_LIGHTING: 'Lighting too dim or harsh.',
      MOTION: 'Camera moving. Keep focused.',
      OUT_OF_BOUNDS: 'Leaf is outside center target.',
    },
    progressLabel: 'Stability:',
  },
};

// ==============================================================================
// Component Props
// ==============================================================================

export interface AutoCaptureReticleProps {
  state: AutoCaptureState;
  stableFramesCount: number;
  requiredStableFrames: number;
  rejectionReason?: QualityRejectionReason;
  errorMessage?: string | null;
  /** Width and height of the central bounding reticle */
  reticleSize?: number;
}

export function AutoCaptureReticle({
  state,
  stableFramesCount,
  requiredStableFrames,
  rejectionReason,
  errorMessage,
  reticleSize = 250,
}: AutoCaptureReticleProps) {
  const { language } = useLanguage();
  const strings = RETICLE_STRINGS[language] || RETICLE_STRINGS.en;
  const currentGuidance = strings[state] || strings.SEARCHING;

  // Pulse animation for targeting corners
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const progressAnim = useRef(new Animated.Value(0)).current;

  // Corner bracket color based on current state
  const getReticleColor = () => {
    switch (state) {
      case 'CAPTURE_READY':
      case 'CAPTURING':
        return '#27AE60'; // Solid success green
      case 'LEAF_CANDIDATE':
        return '#F2C94C'; // Amber / Candidate yellow
      case 'QUALITY_REJECTED':
      case 'ERROR':
        return '#EB5757'; // Alert red
      case 'UPLOADING':
      case 'RESULT_READY':
        return '#2D9CDB'; // Info blue
      case 'DETECTOR_UNAVAILABLE':
      default:
        return '#D5BB79'; // TurSathi golden accent
    }
  };

  const reticleColor = getReticleColor();

  // Subtle breathing pulse in candidate / searching states
  useEffect(() => {
    if (state === 'SEARCHING' || state === 'LEAF_CANDIDATE') {
      const loop = Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, {
            toValue: 0.65,
            duration: 900,
            useNativeDriver: true,
          }),
          Animated.timing(pulseAnim, {
            toValue: 1,
            duration: 900,
            useNativeDriver: true,
          }),
        ]),
      );
      loop.start();
      return () => loop.stop();
    } else {
      pulseAnim.setValue(1);
    }
  }, [state, pulseAnim]);

  // Animate progress bar as stable frames accumulate
  const progressRatio = Math.min(
    1,
    Math.max(0, stableFramesCount / Math.max(1, requiredStableFrames)),
  );

  useEffect(() => {
    Animated.timing(progressAnim, {
      toValue: progressRatio,
      duration: 120,
      useNativeDriver: false,
    }).start();
  }, [progressRatio, progressAnim]);

  // Secondary descriptive message for rejection or errors
  const secondaryDetail =
    state === 'QUALITY_REJECTED' && rejectionReason
      ? strings.reasons[rejectionReason]
      : state === 'ERROR' && errorMessage
        ? errorMessage
        : null;

  return (
    <View pointerEvents="none" style={styles.overlayContainer}>
      {/* 1. TOP STATUS BADGE */}
      <View style={styles.topBadgeContainer}>
        <View style={[styles.statusBadge, { borderColor: reticleColor }]}>
          <View style={[styles.statusDot, { backgroundColor: reticleColor }]} />
          <Text style={styles.statusBadgeText}>{currentGuidance.badge}</Text>
        </View>
      </View>

      {/* 2. CENTRAL TARGETING RETICLE */}
      <View style={[styles.centerReticle, { width: reticleSize, height: reticleSize }]}>
        <Animated.View
          style={[
            styles.bracketGroup,
            {
              opacity: pulseAnim,
              width: reticleSize,
              height: reticleSize,
            },
          ]}
        >
          {/* Top-Left Bracket */}
          <View
            style={[
              styles.corner,
              styles.topLeft,
              { borderColor: reticleColor },
            ]}
          />
          {/* Top-Right Bracket */}
          <View
            style={[
              styles.corner,
              styles.topRight,
              { borderColor: reticleColor },
            ]}
          />
          {/* Bottom-Left Bracket */}
          <View
            style={[
              styles.corner,
              styles.bottomLeft,
              { borderColor: reticleColor },
            ]}
          />
          {/* Bottom-Right Bracket */}
          <View
            style={[
              styles.corner,
              styles.bottomRight,
              { borderColor: reticleColor },
            ]}
          />
        </Animated.View>

        {/* Center Crosshair / Leaf Aim Indicator */}
        <View style={styles.crosshair}>
          <View style={[styles.crosshairLineHorizontal, { backgroundColor: reticleColor }]} />
          <View style={[styles.crosshairLineVertical, { backgroundColor: reticleColor }]} />
        </View>

        {/* Progress Fill Bar at Bottom of Reticle */}
        {(state === 'LEAF_CANDIDATE' || state === 'CAPTURE_READY') && (
          <View style={styles.reticleProgressBarBg}>
            <Animated.View
              style={[
                styles.reticleProgressBarFill,
                {
                  backgroundColor: reticleColor,
                  width: progressAnim.interpolate({
                    inputRange: [0, 1],
                    outputRange: ['0%', '100%'],
                  }),
                },
              ]}
            />
          </View>
        )}
      </View>

      {/* 3. BOTTOM GUIDANCE BANNER */}
      <View style={styles.bottomInstructionContainer}>
        <View style={styles.guidanceCard}>
          <Text style={styles.instructionText}>
            {currentGuidance.instruction}
          </Text>

          {secondaryDetail && (
            <Text style={styles.secondaryText}>{secondaryDetail}</Text>
          )}

          {/* Progress dots indicator */}
          {state === 'LEAF_CANDIDATE' && requiredStableFrames > 1 && (
            <View style={styles.dotsRow}>
              <Text style={styles.dotsLabel}>{strings.progressLabel}</Text>
              {Array.from({ length: requiredStableFrames }).map((_, idx) => (
                <View
                  key={idx}
                  style={[
                    styles.dot,
                    idx < stableFramesCount && styles.dotActive,
                  ]}
                />
              ))}
            </View>
          )}
        </View>
      </View>
    </View>
  );
}

// ==============================================================================
// Styles
// ==============================================================================

const styles = StyleSheet.create({
  overlayContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    alignItems: 'center',
    justifyContent: 'center',
  },
  topBadgeContainer: {
    position: 'absolute',
    top: 20,
    alignItems: 'center',
    zIndex: 10,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 20,
    backgroundColor: 'rgba(22, 59, 44, 0.88)', // Deep TurSathi Forest Green semi-opaque
    borderWidth: 1.5,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
    elevation: 3,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 8,
  },
  statusBadgeText: {
    color: '#FFFEFA',
    fontSize: 13,
    fontWeight: '700',
    letterSpacing: 0.3,
  },
  centerReticle: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  bracketGroup: {
    position: 'absolute',
  },
  corner: {
    position: 'absolute',
    width: 32,
    height: 32,
    borderWidth: 3.5,
  },
  topLeft: {
    top: 0,
    left: 0,
    borderRightWidth: 0,
    borderBottomWidth: 0,
    borderTopLeftRadius: 10,
  },
  topRight: {
    top: 0,
    right: 0,
    borderLeftWidth: 0,
    borderBottomWidth: 0,
    borderTopRightRadius: 10,
  },
  bottomLeft: {
    bottom: 0,
    left: 0,
    borderRightWidth: 0,
    borderTopWidth: 0,
    borderBottomLeftRadius: 10,
  },
  bottomRight: {
    bottom: 0,
    right: 0,
    borderLeftWidth: 0,
    borderTopWidth: 0,
    borderBottomRightRadius: 10,
  },
  crosshair: {
    width: 20,
    height: 20,
    alignItems: 'center',
    justifyContent: 'center',
    opacity: 0.7,
  },
  crosshairLineHorizontal: {
    position: 'absolute',
    width: 14,
    height: 1.5,
    borderRadius: 1,
  },
  crosshairLineVertical: {
    position: 'absolute',
    width: 1.5,
    height: 14,
    borderRadius: 1,
  },
  reticleProgressBarBg: {
    position: 'absolute',
    bottom: -16,
    width: '80%',
    height: 4,
    backgroundColor: 'rgba(255, 255, 255, 0.25)',
    borderRadius: 2,
    overflow: 'hidden',
  },
  reticleProgressBarFill: {
    height: '100%',
    borderRadius: 2,
  },
  bottomInstructionContainer: {
    position: 'absolute',
    bottom: 24,
    width: '90%',
    maxWidth: 380,
    alignItems: 'center',
  },
  guidanceCard: {
    width: '100%',
    backgroundColor: 'rgba(15, 41, 30, 0.85)',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 10,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(213, 187, 121, 0.3)',
  },
  instructionText: {
    color: '#FFFEFA',
    fontSize: 14,
    fontWeight: '600',
    textAlign: 'center',
  },
  secondaryText: {
    color: '#E0D8B0',
    fontSize: 12,
    marginTop: 4,
    textAlign: 'center',
  },
  dotsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 8,
  },
  dotsLabel: {
    color: '#D5BB79',
    fontSize: 11,
    marginRight: 6,
    fontWeight: '600',
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: 'rgba(255, 255, 255, 0.3)',
    marginHorizontal: 3,
  },
  dotActive: {
    backgroundColor: '#27AE60',
    width: 8,
    height: 8,
    borderRadius: 4,
  },
});
