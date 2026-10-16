/**
 * TurSathi AI — Isolated Auto-Capture Debug Sandbox (Phase 4)
 *
 * PURPOSE:
 * Developer sandbox for visually testing the AutoCaptureReticle HUD overlay,
 * state machine transitions, stability debounce counters, quality rejections,
 * capture locking, and multilingual guidance WITHOUT accessing the real camera
 * or making network requests.
 *
 * SAFETY GUARANTEES:
 * 1. 100% Mock / Simulated Events ONLY.
 * 2. Zero camera hardware access (expo-camera is NOT mounted here).
 * 3. Zero network requests (no backend API calls or uploads).
 * 4. Production scan screen (mobile/src/app/scan.tsx) is completely unaffected.
 */

import React, { useState } from 'react';
import { useRouter } from 'expo-router';
import {
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLanguage } from '../i18n/LanguageContext';
import { Language } from '../i18n/translations';
import { AutoCaptureReticle } from '../components/camera/AutoCaptureReticle';
import {
  DEFAULT_AUTO_CAPTURE_CONFIG,
  useAutoCaptureStateMachine,
} from '../services/detector/useAutoCaptureStateMachine';

export default function DebugAutoCaptureScreen() {
  const router = useRouter();
  const { language, setLanguage } = useLanguage();

  // Initialize the state machine in a sandbox configuration
  const machine = useAutoCaptureStateMachine({
    ...DEFAULT_AUTO_CAPTURE_CONFIG,
    requiredStableFrames: 5,
    cooldownMs: 3000,
    minConfidence: 0.85,
  });

  // Local sandbox simulation parameters
  const [simConfidence, setSimConfidence] = useState(0.92);
  const [isSimSharp, setIsSimSharp] = useState(true);
  const [isSimLightOk, setIsSimLightOk] = useState(true);

  // Helper to send a single simulated frame
  const handleSendFrame = (customOverrides?: {
    isLeafDetected?: boolean;
    confidence?: number;
    isSharp?: boolean;
    isLightingAcceptable?: boolean;
  }) => {
    machine.processFrame({
      isLeafDetected: customOverrides?.isLeafDetected ?? true,
      confidence: customOverrides?.confidence ?? simConfidence,
      isSharp: customOverrides?.isSharp ?? isSimSharp,
      isLightingAcceptable: customOverrides?.isLightingAcceptable ?? isSimLightOk,
    });
  };

  // Helper to burst 5 consecutive stable frames
  const handleBurstStableFrames = () => {
    for (let i = 0; i < machine.requiredStableFrames; i++) {
      machine.processFrame({
        isLeafDetected: true,
        confidence: 0.95,
        isSharp: true,
        isLightingAcceptable: true,
      });
    }
  };

  return (
    <SafeAreaView edges={['top', 'bottom']} style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        <View style={styles.page}>
          
          {/* 1. TOP HEADER & NAVIGATION */}
          <View style={styles.header}>
            <Pressable
              accessibilityLabel="Go back"
              accessibilityRole="button"
              hitSlop={8}
              onPress={() => router.back()}
              style={({ pressed }) => [styles.backButton, pressed && styles.buttonPressed]}
            >
              <Text style={styles.backButtonText}>← Back</Text>
            </Pressable>

            <View style={styles.headerBadge}>
              <Text style={styles.headerBadgeText}>DEV SANDBOX</Text>
            </View>

            {/* Language toggle for testing localized reticle guidance */}
            <View style={styles.langSelector}>
              {(['mr', 'hi', 'en'] as Language[]).map((lang) => (
                <Pressable
                  key={lang}
                  onPress={() => setLanguage(lang)}
                  style={[styles.langChip, language === lang && styles.langChipActive]}
                >
                  <Text style={[styles.langChipText, language === lang && styles.langChipTextActive]}>
                    {lang.toUpperCase()}
                  </Text>
                </Pressable>
              ))}
            </View>
          </View>

          {/* 2. SIMULATION NOTICE BANNER */}
          <View style={styles.simulationBanner}>
            <Text style={styles.simulationTitle}>⚠️ SIMULATED DETECTION ENVIRONMENT</Text>
            <Text style={styles.simulationNotice}>
              All frame events and confidence values are mock inputs. No camera hardware is active
              and no network requests are sent.
            </Text>
          </View>

          {/* 3. SIMULATED CAMERA PREVIEW BOX WITH RETICLE OVERLAY */}
          <View style={styles.previewCard}>
            <View style={styles.simulatedCameraView}>
              {/* Background watermark simulating camera backdrop */}
              <View style={styles.backdropWatermark}>
                <Text style={styles.backdropWatermarkText}>[ SIMULATED CAMERA FEED ]</Text>
                <Text style={styles.backdropSubtext}>No live camera attached</Text>
              </View>

              {/* The actual AutoCaptureReticle HUD component under test */}
              <AutoCaptureReticle
                errorMessage={machine.errorMessage}
                rejectionReason={machine.rejectionReason}
                requiredStableFrames={machine.requiredStableFrames}
                reticleSize={220}
                stableFramesCount={machine.stableFramesCount}
                state={machine.state}
              />
            </View>
          </View>

          {/* 4. REAL-TIME TELEMETRY DASHBOARD */}
          <View style={styles.telemetryCard}>
            <Text style={styles.cardHeader}>State Machine Telemetry</Text>
            <View style={styles.telemetryGrid}>
              <View style={styles.telemetryRow}>
                <Text style={styles.telemetryLabel}>Current State:</Text>
                <View style={styles.statePill}>
                  <Text style={styles.statePillText}>{machine.state}</Text>
                </View>
              </View>

              <View style={styles.telemetryRow}>
                <Text style={styles.telemetryLabel}>Stability Counter:</Text>
                <Text style={styles.telemetryValue}>
                  {machine.stableFramesCount} / {machine.requiredStableFrames} frames
                </Text>
              </View>

              <View style={styles.telemetryRow}>
                <Text style={styles.telemetryLabel}>Capture Lock:</Text>
                <Text style={[styles.telemetryValue, machine.isCaptureLocked && styles.valAlert]}>
                  {machine.isCaptureLocked ? 'ENGAGED (LOCKED)' : 'Disengaged'}
                </Text>
              </View>

              <View style={styles.telemetryRow}>
                <Text style={styles.telemetryLabel}>Cooldown Active:</Text>
                <Text style={[styles.telemetryValue, machine.isInCooldown && styles.valWarning]}>
                  {machine.isInCooldown ? 'YES (Cooling down)' : 'No'}
                </Text>
              </View>

              <View style={styles.telemetryRow}>
                <Text style={styles.telemetryLabel}>Detector Available:</Text>
                <Text style={styles.telemetryValue}>
                  {machine.isDetectorAvailable ? 'TRUE' : 'FALSE'}
                </Text>
              </View>

              <View style={styles.telemetryRow}>
                <Text style={styles.telemetryLabel}>Auto-Capture Enabled:</Text>
                <Text style={styles.telemetryValue}>
                  {machine.autoCaptureEnabled ? 'TRUE' : 'FALSE'}
                </Text>
              </View>
            </View>
          </View>

          {/* 5. INTERACTIVE CONTROLS */}
          <View style={styles.controlsSection}>
            <Text style={styles.cardHeader}>Sandbox Controls</Text>

            {/* Toggle Configuration */}
            <View style={styles.buttonGroup}>
              <Pressable
                onPress={() => machine.setDetectorAvailable(!machine.isDetectorAvailable)}
                style={[styles.toggleBtn, machine.isDetectorAvailable && styles.toggleBtnActive]}
              >
                <Text style={styles.toggleBtnText}>
                  Detector: {machine.isDetectorAvailable ? 'Available' : 'Unavailable'}
                </Text>
              </Pressable>

              <Pressable
                onPress={() => machine.setEnabled(!machine.autoCaptureEnabled)}
                style={[styles.toggleBtn, machine.autoCaptureEnabled && styles.toggleBtnActive]}
              >
                <Text style={styles.toggleBtnText}>
                  Auto-Capture: {machine.autoCaptureEnabled ? 'Enabled' : 'Disabled'}
                </Text>
              </Pressable>
            </View>

            {/* Simulated Confidence Inputs */}
            <Text style={styles.subHeader}>Simulated Leaf Confidence</Text>
            <View style={styles.chipRow}>
              {[0.95, 0.88, 0.70, 0.30].map((conf) => (
                <Pressable
                  key={conf}
                  onPress={() => setSimConfidence(conf)}
                  style={[styles.chip, simConfidence === conf && styles.chipActive]}
                >
                  <Text style={[styles.chipText, simConfidence === conf && styles.chipTextActive]}>
                    {(conf * 100).toFixed(0)}%
                  </Text>
                </Pressable>
              ))}
            </View>

            {/* Frame Feeder Buttons */}
            <Text style={styles.subHeader}>Frame Feeder Controls</Text>
            <View style={styles.actionGrid}>
              <Pressable
                onPress={() => handleSendFrame()}
                style={({ pressed }) => [styles.actionBtn, styles.actionPrimary, pressed && styles.buttonPressed]}
              >
                <Text style={styles.actionPrimaryText}>+ Send 1 Valid Frame</Text>
              </Pressable>

              <Pressable
                onPress={handleBurstStableFrames}
                style={({ pressed }) => [styles.actionBtn, styles.actionAccent, pressed && styles.buttonPressed]}
              >
                <Text style={styles.actionAccentText}>⚡ Burst 5 Stable Frames</Text>
              </Pressable>

              <Pressable
                onPress={() => handleSendFrame({ isSharp: false })}
                style={({ pressed }) => [styles.actionBtn, styles.actionWarning, pressed && styles.buttonPressed]}
              >
                <Text style={styles.actionWarningText}>⚠️ Send Blurry Frame</Text>
              </Pressable>

              <Pressable
                onPress={() => handleSendFrame({ isLightingAcceptable: false })}
                style={({ pressed }) => [styles.actionBtn, styles.actionWarning, pressed && styles.buttonPressed]}
              >
                <Text style={styles.actionWarningText}>☀️ Send Bad Lighting</Text>
              </Pressable>

              <Pressable
                onPress={() => handleSendFrame({ isLeafDetected: false, confidence: 0.1 })}
                style={({ pressed }) => [styles.actionBtn, styles.actionDanger, pressed && styles.buttonPressed]}
              >
                <Text style={styles.actionDangerText}>❌ Send No-Leaf Frame</Text>
              </Pressable>
            </View>

            {/* Lifecycle Progression Controls */}
            <Text style={styles.subHeader}>Capture Lifecycle Simulation</Text>
            <View style={styles.lifecycleRow}>
              <Pressable
                disabled={machine.state !== 'CAPTURE_READY'}
                onPress={() => machine.triggerCapture()}
                style={[
                  styles.lifecycleBtn,
                  machine.state === 'CAPTURE_READY' ? styles.btnReady : styles.btnDisabled,
                ]}
              >
                <Text style={styles.lifecycleBtnText}>Trigger Capture</Text>
              </Pressable>

              <Pressable
                disabled={machine.state !== 'CAPTURING'}
                onPress={() => machine.notifyCaptureSuccess()}
                style={[
                  styles.lifecycleBtn,
                  machine.state === 'CAPTURING' ? styles.btnReady : styles.btnDisabled,
                ]}
              >
                <Text style={styles.lifecycleBtnText}>Upload Success</Text>
              </Pressable>

              <Pressable
                disabled={machine.state !== 'UPLOADING'}
                onPress={() => machine.notifyResultReady()}
                style={[
                  styles.lifecycleBtn,
                  machine.state === 'UPLOADING' ? styles.btnReady : styles.btnDisabled,
                ]}
              >
                <Text style={styles.lifecycleBtnText}>Result Ready</Text>
              </Pressable>
            </View>

            {/* Error & Recovery */}
            <View style={styles.resetRow}>
              <Pressable
                onPress={() => machine.notifyError('Simulated Network Error (HTTP 500)')}
                style={[styles.utilBtn, styles.utilDanger]}
              >
                <Text style={styles.utilBtnText}>Simulate Error</Text>
              </Pressable>

              <Pressable
                disabled={machine.state !== 'ERROR'}
                onPress={() => machine.retry()}
                style={[styles.utilBtn, machine.state === 'ERROR' ? styles.utilPrimary : styles.btnDisabled]}
              >
                <Text style={styles.utilBtnText}>Retry</Text>
              </Pressable>

              <Pressable onPress={() => machine.reset()} style={[styles.utilBtn, styles.utilSecondary]}>
                <Text style={styles.utilSecondaryText}>Reset State</Text>
              </Pressable>
            </View>
          </View>

        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

// ==============================================================================
// Styles
// ==============================================================================

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#F5F4EC',
  },
  scrollContent: {
    paddingBottom: 40,
    alignItems: 'center',
  },
  page: {
    width: '100%',
    maxWidth: 540,
    paddingHorizontal: 16,
    paddingTop: 10,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  backButton: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    backgroundColor: '#FFFEFA',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#E3E2D9',
  },
  backButtonText: {
    fontSize: 14,
    fontWeight: '700',
    color: '#1F5137',
  },
  headerBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    backgroundColor: '#1F5137',
    borderRadius: 6,
  },
  headerBadgeText: {
    color: '#FFFEFA',
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  langSelector: {
    flexDirection: 'row',
    backgroundColor: '#EAE8DE',
    borderRadius: 8,
    padding: 2,
  },
  langChip: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  langChipActive: {
    backgroundColor: '#1F5137',
  },
  langChipText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#555',
  },
  langChipTextActive: {
    color: '#FFFEFA',
  },
  buttonPressed: {
    opacity: 0.7,
  },
  simulationBanner: {
    backgroundColor: '#FFF4E5',
    borderWidth: 1,
    borderColor: '#FFE2B8',
    borderRadius: 10,
    padding: 12,
    marginBottom: 16,
  },
  simulationTitle: {
    color: '#B25E00',
    fontSize: 12,
    fontWeight: '800',
    marginBottom: 4,
  },
  simulationNotice: {
    color: '#664214',
    fontSize: 12,
    lineHeight: 16,
  },
  previewCard: {
    borderRadius: 16,
    overflow: 'hidden',
    backgroundColor: '#163B2C',
    borderWidth: 2,
    borderColor: '#1F5137',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 4,
    marginBottom: 16,
  },
  simulatedCameraView: {
    width: '100%',
    height: 320,
    backgroundColor: '#1A2922',
    position: 'relative',
    alignItems: 'center',
    justifyContent: 'center',
  },
  backdropWatermark: {
    position: 'absolute',
    alignItems: 'center',
    opacity: 0.25,
  },
  backdropWatermarkText: {
    color: '#D5BB79',
    fontSize: 14,
    fontWeight: '700',
    letterSpacing: 1,
  },
  backdropSubtext: {
    color: '#FFFFFF',
    fontSize: 11,
    marginTop: 4,
  },
  telemetryCard: {
    backgroundColor: '#FFFEFA',
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: '#E3E2D9',
    marginBottom: 16,
  },
  cardHeader: {
    fontSize: 15,
    fontWeight: '700',
    color: '#1F5137',
    marginBottom: 10,
  },
  subHeader: {
    fontSize: 13,
    fontWeight: '700',
    color: '#444',
    marginTop: 12,
    marginBottom: 6,
  },
  telemetryGrid: {
    gap: 6,
  },
  telemetryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 3,
  },
  telemetryLabel: {
    fontSize: 13,
    color: '#555',
  },
  telemetryValue: {
    fontSize: 13,
    fontWeight: '600',
    color: '#1F5137',
  },
  statePill: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
    backgroundColor: '#EAF5EF',
    borderWidth: 1,
    borderColor: '#B9E0CB',
  },
  statePillText: {
    fontSize: 11,
    fontWeight: '800',
    color: '#1F5137',
  },
  valAlert: {
    color: '#D32F2F',
    fontWeight: '800',
  },
  valWarning: {
    color: '#B25E00',
    fontWeight: '800',
  },
  controlsSection: {
    backgroundColor: '#FFFEFA',
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: '#E3E2D9',
    marginBottom: 20,
  },
  buttonGroup: {
    flexDirection: 'row',
    gap: 8,
  },
  toggleBtn: {
    flex: 1,
    paddingVertical: 9,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#CCC',
    backgroundColor: '#F5F5F5',
    alignItems: 'center',
  },
  toggleBtnActive: {
    backgroundColor: '#E8F5E9',
    borderColor: '#2E7D32',
  },
  toggleBtnText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#333',
  },
  chipRow: {
    flexDirection: 'row',
    gap: 8,
  },
  chip: {
    flex: 1,
    paddingVertical: 6,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#D0CFC5',
    backgroundColor: '#F8F7F0',
    alignItems: 'center',
  },
  chipActive: {
    backgroundColor: '#1F5137',
    borderColor: '#1F5137',
  },
  chipText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#444',
  },
  chipTextActive: {
    color: '#FFFEFA',
  },
  actionGrid: {
    gap: 8,
  },
  actionBtn: {
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  actionPrimary: {
    backgroundColor: '#1F5137',
  },
  actionPrimaryText: {
    color: '#FFFEFA',
    fontWeight: '700',
    fontSize: 13,
  },
  actionAccent: {
    backgroundColor: '#D5BB79',
  },
  actionAccentText: {
    color: '#1A2922',
    fontWeight: '800',
    fontSize: 13,
  },
  actionWarning: {
    backgroundColor: '#FFF3E0',
    borderWidth: 1,
    borderColor: '#FFE0B2',
  },
  actionWarningText: {
    color: '#E65100',
    fontWeight: '700',
    fontSize: 13,
  },
  actionDanger: {
    backgroundColor: '#FFEBEE',
    borderWidth: 1,
    borderColor: '#FFCDD2',
  },
  actionDangerText: {
    color: '#C62828',
    fontWeight: '700',
    fontSize: 13,
  },
  lifecycleRow: {
    flexDirection: 'row',
    gap: 8,
  },
  lifecycleBtn: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: 'center',
  },
  btnReady: {
    backgroundColor: '#2E7D32',
  },
  btnDisabled: {
    backgroundColor: '#E0E0E0',
    opacity: 0.6,
  },
  lifecycleBtnText: {
    color: '#FFFFFF',
    fontWeight: '700',
    fontSize: 12,
  },
  resetRow: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 12,
  },
  utilBtn: {
    flex: 1,
    paddingVertical: 9,
    borderRadius: 8,
    alignItems: 'center',
  },
  utilDanger: {
    backgroundColor: '#C62828',
  },
  utilPrimary: {
    backgroundColor: '#1F5137',
  },
  utilSecondary: {
    backgroundColor: '#F0EFE7',
    borderWidth: 1,
    borderColor: '#D8D6C9',
  },
  utilBtnText: {
    color: '#FFFFFF',
    fontWeight: '700',
    fontSize: 12,
  },
  utilSecondaryText: {
    color: '#333333',
    fontWeight: '700',
    fontSize: 12,
  },
});
