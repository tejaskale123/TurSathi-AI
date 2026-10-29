import { useEffect, useRef, useState } from 'react';
import { useLocalSearchParams, useRouter } from 'expo-router';
import {
  Alert,
  Animated,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import {
  getRecordingPermissionsAsync,
  RecordingPresets,
  requestRecordingPermissionsAsync,
  setAudioModeAsync,
  useAudioPlayer,
  useAudioPlayerStatus,
  useAudioRecorder,
} from 'expo-audio';
import { useLanguage } from '../i18n/LanguageContext';
import { Language } from '../i18n/translations';
import { uploadVoiceReport, ScanUploadError } from '../config/scanApi';
import { getAuthToken } from '../config/tokenStore';

// ============================================================================
// STEP 2 LOCALIZED STRINGS (English, Marathi, Hindi)
// ============================================================================
const LOCALIZED_STRINGS: Record<
  Language,
  {
    brand: string;
    title: string;
    subtitle: string;
    tapToRecord: string;
    recording: string;
    tapToStop: string;
    listeningSubtext: string;
    yourVoiceMessage: string;
    recordAgain: string;
    submit: string;
    securityTitle: string;
    securityText: string;
    permissionTitle: string;
    permissionRequired: string;
    recordingError: string;
  }
> = {
  en: {
    brand: 'TurSathi AI',
    title: 'Describe Your Problem',
    subtitle: 'Tell us what you noticed on your Tur plant.',
    tapToRecord: 'Tap to Record',
    recording: 'Recording...',
    tapToStop: 'Tap to stop',
    listeningSubtext: 'Describe what you see on the Tur plant.',
    yourVoiceMessage: 'Your Voice Message',
    recordAgain: 'Record Again',
    submit: 'Submit',
    securityTitle: 'Your Voice Is Secure',
    securityText:
      'Your voice message is used only to understand your Tur leaf problem and provide relevant guidance.',
    permissionTitle: 'Microphone Permission',
    permissionRequired:
      'Microphone permission is required to record your problem description.',
    recordingError:
      'Unable to start recording. Please check your microphone permissions.',
  },
  mr: {
    brand: 'TurSathi AI',
    title: 'तुमच्या समस्येचे वर्णन करा',
    subtitle: 'तुमच्या तुरीच्या झाडावर काय दिसले ते सांगा.',
    tapToRecord: 'रेकॉर्ड करण्यासाठी टॅप करा',
    recording: 'रेकॉर्डिंग सुरू आहे...',
    tapToStop: 'थांबवण्यासाठी टॅप करा',
    listeningSubtext: 'तूर पिकावर तुम्हाला काय दिसते त्याचे वर्णन करा.',
    yourVoiceMessage: 'तुमचा व्हॉइस संदेश',
    recordAgain: 'पुन्हा रेकॉर्ड करा',
    submit: 'पाठवा',
    securityTitle: 'तुमचा व्हॉइस सुरक्षित आहे',
    securityText:
      'तुमच्या तूर पिकाची समस्या समजून घेण्यासाठी आणि योग्य मार्गदर्शन देण्यासाठीच तुमचा व्हॉइस संदेश वापरला जातो.',
    permissionTitle: 'मायक्रोफोन परवानगी',
    permissionRequired:
      'समस्या रेकॉर्ड करण्यासाठी मायक्रोफोन परवानगी आवश्यक आहे.',
    recordingError:
      'रेकॉर्डिंग सुरू करता आले नाही. कृपया मायक्रोफोन परवानगी तपासा.',
  },
  hi: {
    brand: 'TurSathi AI',
    title: 'अपनी समस्या का वर्णन करें',
    subtitle: 'अपने तूर के पौधे पर क्या दिखाई दे रहा है बताएं।',
    tapToRecord: 'रिकॉर्ड करने के लिए टैप करें',
    recording: 'रिकॉर्डिंग जारी है...',
    tapToStop: 'रोकने के लिए टैप करें',
    listeningSubtext: 'तूर फसल पर आपको क्या दिखाई दे रहा है, उसका वर्णन करें।',
    yourVoiceMessage: 'आपका वॉइस संदेश',
    recordAgain: 'फिर से रिकॉर्ड करें',
    submit: 'जमा करें',
    securityTitle: 'आपकी वॉइस सुरक्षित है',
    securityText:
      'आपकी तूर फसल की समस्या को समझने और उचित मार्गदर्शन देने के लिए ही आपके वॉइस संदेश का उपयोग किया जाता है।',
    permissionTitle: 'माइक्रोफ़ोन अनुमति',
    permissionRequired:
      'समस्या रिकॉर्ड करने के लिए माइक्रोफ़ोन की अनुमति आवश्यक है।',
    recordingError:
      'रिकॉर्डिंग शुरू नहीं हो सकी। कृपया माइक्रोफ़ोन अनुमति जांचें।',
  },
};

// ============================================================================
// VECTOR GLYPHS (Strictly NO emojis, NO robot graphics, NO stickers)
// ============================================================================
function BackGlyph({ color = '#1A4D33' }: { color?: string }) {
  return (
    <View style={styles.backBox}>
      <View style={[styles.backShaft, { backgroundColor: color }]} />
      <View style={[styles.backHead, { borderColor: color }]} />
    </View>
  );
}

function ShieldGlyph({ color = '#1B4332', size = 18 }: { color?: string; size?: number }) {
  const scale = size / 18;
  return (
    <View style={{ width: size, height: size * 1.15, alignItems: 'center', justifyContent: 'center' }}>
      <View
        style={{
          width: 14 * scale,
          height: 16 * scale,
          borderWidth: 2 * scale,
          borderColor: color,
          borderTopLeftRadius: 3 * scale,
          borderTopRightRadius: 3 * scale,
          borderBottomLeftRadius: 8 * scale,
          borderBottomRightRadius: 8 * scale,
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <View
          style={{
            width: 4 * scale,
            height: 5 * scale,
            backgroundColor: color,
            borderRadius: 1,
          }}
        />
      </View>
    </View>
  );
}

function MicGlyph({ size = 48, color = '#FFFFFF' }: { size?: number; color?: string }) {
  const scale = size / 48;
  return (
    <View
      style={{
        width: size,
        height: size * 1.3,
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <View
        style={{
          width: 20 * scale,
          height: 32 * scale,
          borderRadius: 10 * scale,
          backgroundColor: color,
        }}
      />
      <View
        style={{
          position: 'absolute',
          top: 9 * scale,
          width: 36 * scale,
          height: 28 * scale,
          borderBottomLeftRadius: 18 * scale,
          borderBottomRightRadius: 18 * scale,
          borderWidth: 3.5 * scale,
          borderTopWidth: 0,
          borderColor: color,
        }}
      />
      <View
        style={{
          width: 3.8 * scale,
          height: 11 * scale,
          backgroundColor: color,
          marginTop: 3 * scale,
        }}
      />
      <View
        style={{
          width: 26 * scale,
          height: 3.6 * scale,
          borderRadius: 1.8 * scale,
          backgroundColor: color,
        }}
      />
    </View>
  );
}

function StopGlyph({ size = 22, color = '#FFFFFF' }: { size?: number; color?: string }) {
  return (
    <View
      style={{
        width: size,
        height: size,
        backgroundColor: color,
        borderRadius: 4,
      }}
    />
  );
}

function PlayGlyph({ size = 18, color = '#FFFFFF' }: { size?: number; color?: string }) {
  return (
    <View
      style={{
        width: 0,
        height: 0,
        borderStyle: 'solid',
        borderLeftWidth: size,
        borderTopWidth: size * 0.6,
        borderBottomWidth: size * 0.6,
        borderLeftColor: color,
        borderTopColor: 'transparent',
        borderBottomColor: 'transparent',
        marginLeft: 2,
      }}
    />
  );
}

function PauseGlyph({ size = 18, color = '#FFFFFF' }: { size?: number; color?: string }) {
  return (
    <View
      style={{
        flexDirection: 'row',
        width: size,
        height: size,
        justifyContent: 'space-between',
        alignItems: 'center',
      }}
    >
      <View style={{ width: size * 0.32, height: size, backgroundColor: color, borderRadius: 2 }} />
      <View style={{ width: size * 0.32, height: size, backgroundColor: color, borderRadius: 2 }} />
    </View>
  );
}

function RefreshGlyph({ size = 18, color = '#1B4332' }: { size?: number; color?: string }) {
  return (
    <View style={{ width: size, height: size, justifyContent: 'center', alignItems: 'center' }}>
      <View
        style={{
          width: size - 3,
          height: size - 3,
          borderRadius: (size - 3) / 2,
          borderWidth: 2.2,
          borderColor: color,
          borderTopColor: 'transparent',
        }}
      />
      <View
        style={{
          position: 'absolute',
          top: 0,
          right: 0,
          width: 0,
          height: 0,
          borderLeftWidth: 4,
          borderRightWidth: 4,
          borderBottomWidth: 6,
          borderLeftColor: 'transparent',
          borderRightColor: 'transparent',
          borderBottomColor: color,
          transform: [{ rotate: '45deg' }],
        }}
      />
    </View>
  );
}

function ArrowGlyph({ color = '#FFFFFF', size = 16 }: { color?: string; size?: number }) {
  return (
    <View style={{ width: size, height: size, justifyContent: 'center', alignItems: 'center' }}>
      <View
        style={{
          width: size * 0.52,
          height: size * 0.52,
          borderTopWidth: 2.2,
          borderRightWidth: 2.2,
          borderColor: color,
          transform: [{ rotate: '45deg' }],
        }}
      />
    </View>
  );
}

function formatTimer(totalSeconds: number): string {
  const safeSecs = Math.max(0, Math.floor(totalSeconds));
  const minutes = Math.floor(safeSecs / 60);
  const seconds = safeSecs % 60;
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

export default function VoiceRecordScreen() {
  const router = useRouter();
  const { language } = useLanguage();
  const labels = LOCALIZED_STRINGS[language] || LOCALIZED_STRINGS.en;

  // Route parameters received from problem-description screen
  const params = useLocalSearchParams<{ imageUri?: string | string[]; scanId?: string | string[] }>();
  const rawImageUri = Array.isArray(params.imageUri)
    ? params.imageUri[0]
    : (params.imageUri ?? '');

  // scanId links this voice recording to the backend scan/case
  const rawScanId = Array.isArray(params.scanId) ? params.scanId[0] : (params.scanId ?? '');
  const scanId = rawScanId ? parseInt(rawScanId, 10) : null;

  let normalizedImageUri = '';
  try {
    if (
      rawImageUri.startsWith('file%3A') ||
      rawImageUri.startsWith('http%3A') ||
      rawImageUri.startsWith('https%3A') ||
      rawImageUri.includes('%2525') ||
      !rawImageUri.includes('://')
    ) {
      normalizedImageUri = decodeURIComponent(rawImageUri);
    } else {
      normalizedImageUri = rawImageUri;
    }
  } catch {
    normalizedImageUri = rawImageUri;
  }

  // Audio recording state
  const [isRecording, setIsRecording] = useState(false);
  const [recordedUri, setRecordedUri] = useState<string | null>(null);
  const [timerSeconds, setTimerSeconds] = useState(0);
  const [recordedDuration, setRecordedDuration] = useState(0);

  // Animations for subtle pulse recording indicator
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const rippleAnim = useRef(new Animated.Value(1)).current;
  const rippleOpacity = useRef(new Animated.Value(0.4)).current;
  const submitGuard = useRef(false);

  // expo-audio recorder instance
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);

  // expo-audio player instance for recorded voice preview
  const player = useAudioPlayer(recordedUri ? { uri: recordedUri } : null);
  const playerStatus = useAudioPlayerStatus(player);

  const isPlaying = Boolean(playerStatus.playing);
  const isFinished = Boolean(
    playerStatus.didJustFinish ||
      (playerStatus.duration > 0 && playerStatus.currentTime >= playerStatus.duration)
  );

  const durationSeconds =
    recordedDuration > 0
      ? recordedDuration
      : Math.floor(playerStatus.duration || 0);

  const currentSeconds = Math.floor(playerStatus.currentTime || 0);
  const progressPercent =
    durationSeconds > 0
      ? Math.min(Math.max(currentSeconds / durationSeconds, 0), 1)
      : isFinished
        ? 1
        : 0;

  // Subtle recording animation loop
  useEffect(() => {
    if (isRecording) {
      const pulseLoop = Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, {
            toValue: 1.08,
            duration: 650,
            useNativeDriver: true,
          }),
          Animated.timing(pulseAnim, {
            toValue: 1.0,
            duration: 650,
            useNativeDriver: true,
          }),
        ])
      );

      const rippleLoop = Animated.loop(
        Animated.parallel([
          Animated.timing(rippleAnim, {
            toValue: 1.35,
            duration: 1300,
            useNativeDriver: true,
          }),
          Animated.sequence([
            Animated.timing(rippleOpacity, {
              toValue: 0.1,
              duration: 1100,
              useNativeDriver: true,
            }),
            Animated.timing(rippleOpacity, {
              toValue: 0.4,
              duration: 200,
              useNativeDriver: true,
            }),
          ]),
        ])
      );

      pulseLoop.start();
      rippleLoop.start();

      return () => {
        pulseLoop.stop();
        rippleLoop.stop();
      };
    } else {
      pulseAnim.setValue(1);
      rippleAnim.setValue(1);
      rippleOpacity.setValue(0.4);
    }
  }, [isRecording, pulseAnim, rippleAnim, rippleOpacity]);

  // Timer interval for recording duration
  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | null = null;
    if (isRecording) {
      interval = setInterval(() => {
        setTimerSeconds((prev) => prev + 1);
      }, 1000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isRecording]);

  // Safe cleanup on unmount
  useEffect(() => {
    return () => {
      try {
        if (player && typeof player.pause === 'function') {
          player.pause();
        }
      } catch {}
    };
  }, [player]);

  useEffect(() => {
    return () => {
      try {
        if (recorder && recorder.isRecording) {
          recorder.stop().catch(() => {});
        }
      } catch {}
    };
  }, [recorder]);

  // 1. START RECORDING
  const handleStartRecording = async () => {
    try {
      if (isPlaying) {
        try {
          player.pause();
        } catch {}
      }

      // Check / request microphone permissions
      const perm = await getRecordingPermissionsAsync();
      let granted = perm.granted;
      if (!granted) {
        const requested = await requestRecordingPermissionsAsync();
        granted = requested.granted;
      }

      if (!granted) {
        Alert.alert(labels.permissionTitle, labels.permissionRequired);
        return;
      }

      // Configure audio mode for recording
      await setAudioModeAsync({
        allowsRecording: true,
        playsInSilentMode: true,
      });

      await recorder.prepareToRecordAsync();
      recorder.record();
      setIsRecording(true);
      setTimerSeconds(0);
      setRecordedUri(null);
    } catch (err) {
      console.error('[VOICE-RECORD] Failed to start recording:', err);
      Alert.alert(labels.permissionTitle, labels.recordingError);
      setIsRecording(false);
    }
  };

  // 2. STOP RECORDING
  const handleStopRecording = async () => {
    try {
      await recorder.stop();
      setIsRecording(false);
      const uri = recorder.uri;
      console.log('[VOICE-RECORD] Recording completed. URI:', uri);
      if (uri) {
        setRecordedUri(uri);
        setRecordedDuration(timerSeconds > 0 ? timerSeconds : 1);
      }
    } catch (err) {
      console.error('[VOICE-RECORD] Failed to stop recording:', err);
      setIsRecording(false);
    }
  };

  // 3. PLAY / PAUSE RECORDED AUDIO
  const handleTogglePlayback = async () => {
    if (!recordedUri) return;

    if (isPlaying) {
      try {
        player.pause();
      } catch {}
      return;
    }

    try {
      await setAudioModeAsync({
        allowsRecording: false,
        playsInSilentMode: true,
      });

      if (isFinished || (durationSeconds > 0 && currentSeconds >= durationSeconds)) {
        try {
          await player.seekTo(0);
        } catch {}
      }

      player.play();
    } catch (err) {
      console.warn('[VOICE-RECORD] Playback error:', err);
    }
  };

  // 4. RECORD AGAIN: Reset previous recording state and return to recording state
  const handleRecordAgain = async () => {
    try {
      if (isPlaying) {
        player.pause();
      }
    } catch {}
    setRecordedUri(null);
    setTimerSeconds(0);
    setRecordedDuration(0);
  };

  // 5. SUBMIT: Upload voice recording (best-effort), then navigate to /prescription
  const handleSubmit = async () => {
    if (!recordedUri || submitGuard.current) {
      return;
    }
    submitGuard.current = true;

    if (isPlaying) {
      try {
        player.pause();
      } catch {}
    }

    const tSubmitStart = Date.now();
    console.log(`[PERF][VOICE_RECORD] Submit pressed at: ${tSubmitStart}`);
    const finalImageUri = normalizedImageUri || rawImageUri;
    console.log('[VOICE-RECORD] Submitting to Prescription:');
    console.log('  imageUri:', finalImageUri);
    console.log('  voiceUri:', recordedUri);
    console.log('  scanId:', scanId);

    let voiceTranscription: string | null = null;

    // Upload voice recording to backend (best-effort: failure doesn't block prescription)
    if (scanId !== null && !isNaN(scanId)) {
      try {
        const token = await getAuthToken();
        if (token) {
          const langCode = language === 'mr' ? 'mr' : language === 'hi' ? 'hi' : 'en';
          const tUploadStart = Date.now();
          const voiceRes = await uploadVoiceReport(
            scanId,
            recordedUri,
            token,
            langCode,
            recordedDuration > 0 ? recordedDuration : undefined,
          );
          if (voiceRes && typeof voiceRes.transcription === 'string' && voiceRes.transcription.trim()) {
            voiceTranscription = voiceRes.transcription.trim();
          }
          const tUploadEnd = Date.now();
          console.log(`[PERF][VOICE_RECORD] Voice uploaded in ${tUploadEnd - tUploadStart}ms for scan_id: ${scanId}`);
        }
      } catch (uploadErr) {
        // Log but do NOT block the farmer — prescription must always be reachable
        if (uploadErr instanceof ScanUploadError) {
          console.warn('[VOICE-RECORD] Voice upload failed (HTTP', uploadErr.httpStatus, '):', uploadErr.message);
        } else {
          console.warn('[VOICE-RECORD] Voice upload error:', uploadErr);
        }
      }
    } else {
      console.warn('[VOICE-RECORD] No scanId available — voice upload skipped.');
    }

    submitGuard.current = false;
    router.push({
      pathname: '/prescription',
      params: {
        imageUri: encodeURIComponent(finalImageUri),
        voiceUri: encodeURIComponent(recordedUri),
        ...(voiceTranscription ? { transcription: voiceTranscription } : {}),
        ...(scanId !== null && !isNaN(scanId) ? { scanId: String(scanId) } : {}),
      },
    });
  };

  const handleBack = () => {
    try {
      if (isRecording) {
        recorder.stop().catch(() => {});
      }
      if (isPlaying) {
        player.pause();
      }
    } catch {}
    const finalImageUri = normalizedImageUri || rawImageUri;
    router.push({
      pathname: '/problem-description',
      params: {
        imageUri: encodeURIComponent(finalImageUri),
        ...(scanId !== null && !isNaN(scanId) ? { scanId: String(scanId) } : {}),
      },
    });
  };

  return (
    <SafeAreaView edges={['top', 'bottom']} style={styles.safeArea}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.page}>
          {/* HEADER */}
          <View style={styles.header}>
            <Pressable
              accessibilityHint="Returns to voice guidance"
              accessibilityLabel="Go back"
              accessibilityRole="button"
              hitSlop={8}
              onPress={handleBack}
              style={({ pressed }) => [styles.backButton, pressed && styles.buttonPressed]}
            >
              <BackGlyph color="#1A4D33" />
            </Pressable>

            <View style={styles.headerCopy}>
              <Text style={styles.brand}>{labels.brand}</Text>
            </View>

            <View style={styles.headerRightSpacer} />
          </View>

          {/* PAGE TITLE & SUBTITLE */}
          <View style={styles.titleSection}>
            <Text style={styles.headerTitle}>{labels.title}</Text>
            <Text style={styles.headerSubtitle}>{labels.subtitle}</Text>
          </View>

          {/* VOICE CARD & ACTIONS */}
          {!recordedUri ? (
            /* RECORDING INTERFACE (Idle or Active) */
            <View style={styles.voiceCard}>
              {isRecording ? (
                /* RECORDING ACTIVE */
                <View style={styles.recordingCenterArea}>
                  <View style={styles.micCircleWrapper}>
                    {/* Subtle pulsing ripple ring */}
                    <Animated.View
                      style={[
                        styles.rippleRing,
                        {
                          transform: [{ scale: rippleAnim }],
                          opacity: rippleOpacity,
                        },
                      ]}
                    />

                    {/* Animated circular recording button */}
                    <Animated.View style={{ transform: [{ scale: pulseAnim }] }}>
                      <Pressable
                        accessibilityHint="Stops recording your voice"
                        accessibilityLabel={labels.tapToStop}
                        accessibilityRole="button"
                        onPress={handleStopRecording}
                        style={({ pressed }) => [
                          styles.micCircle,
                          styles.micCircleRecording,
                          pressed && styles.buttonPressed,
                        ]}
                      >
                        <StopGlyph color="#FFFFFF" size={26} />
                      </Pressable>
                    </Animated.View>
                  </View>

                  {/* Recording indicator dot and text */}
                  <View style={styles.recordingStatusRow}>
                    <View style={styles.recordingDot} />
                    <Text style={styles.recordingText}>{labels.recording}</Text>
                  </View>

                  {/* Digital Timer */}
                  <Text style={styles.timerDisplay}>{formatTimer(timerSeconds)}</Text>

                  {/* Secondary guidance text */}
                  <Text style={styles.listeningSubtext}>{labels.listeningSubtext}</Text>

                  {/* Tap to stop action button */}
                  <Pressable
                    accessibilityHint="Stops recording"
                    accessibilityLabel={labels.tapToStop}
                    accessibilityRole="button"
                    onPress={handleStopRecording}
                    style={({ pressed }) => [styles.stopPill, pressed && styles.buttonPressed]}
                  >
                    <Text style={styles.stopPillText}>{labels.tapToStop}</Text>
                  </Pressable>
                </View>
              ) : (
                /* IDLE STATE: TAP TO RECORD */
                <View style={styles.idleCenterArea}>
                  <Pressable
                    accessibilityHint="Tap to record your farming problem"
                    accessibilityLabel={labels.tapToRecord}
                    accessibilityRole="button"
                    onPress={handleStartRecording}
                    style={({ pressed }) => [
                      styles.micCircle,
                      styles.micCircleIdle,
                      pressed && styles.buttonPressed,
                    ]}
                  >
                    <MicGlyph color="#FFFFFF" size={52} />
                  </Pressable>

                  <Text style={styles.tapToRecordLabel}>{labels.tapToRecord}</Text>
                  <Text style={styles.tapToRecordSubtext}>{labels.listeningSubtext}</Text>
                </View>
              )}
            </View>
          ) : (
            /* AFTER RECORDING: PROFESSIONAL AUDIO PLAYER CARD + RECORD AGAIN */
            <View style={styles.afterRecordingSection}>
              {/* Professional Audio Player Card */}
              <View style={styles.audioPlayerCard}>
                <View style={styles.playerTopRow}>
                  {/* Play / Pause Toggle Button */}
                  <Pressable
                    accessibilityHint="Plays or pauses your recorded voice message"
                    accessibilityLabel={isPlaying ? 'Pause' : 'Play'}
                    accessibilityRole="button"
                    onPress={handleTogglePlayback}
                    style={({ pressed }) => [
                      styles.playRoundButton,
                      pressed && styles.buttonPressed,
                    ]}
                  >
                    {isPlaying ? (
                      <PauseGlyph color="#FFFFFF" size={18} />
                    ) : (
                      <PlayGlyph color="#FFFFFF" size={18} />
                    )}
                  </Pressable>

                  {/* Message Title & Duration */}
                  <View style={styles.playerInfo}>
                    <Text style={styles.playerTitle}>{labels.yourVoiceMessage}</Text>
                    <Text style={styles.playerDurationText}>
                      {isPlaying
                        ? `${formatTimer(currentSeconds)} / ${formatTimer(durationSeconds)}`
                        : formatTimer(durationSeconds)}
                    </Text>
                  </View>
                </View>

                {/* Clean Playback Progress Bar */}
                <View style={styles.progressBarTrack}>
                  <View
                    style={[
                      styles.progressBarFill,
                      { width: `${Math.round(progressPercent * 100)}%` },
                    ]}
                  />
                </View>
              </View>

              {/* Record Again Button (Secondary Outlined) */}
              <Pressable
                accessibilityHint="Deletes the previous recording and lets you record a new message"
                accessibilityLabel={labels.recordAgain}
                accessibilityRole="button"
                onPress={handleRecordAgain}
                style={({ pressed }) => [
                  styles.recordAgainButton,
                  pressed && styles.buttonPressed,
                ]}
              >
                <RefreshGlyph color="#1B4332" size={18} />
                <Text style={styles.recordAgainText}>{labels.recordAgain}</Text>
              </Pressable>
            </View>
          )}

          {/* 3. VOICE PRIVACY / SECURITY INFORMATION BOX */}
          <View style={styles.securityBox}>
            <View style={styles.securityIconWrap}>
              <ShieldGlyph color="#1B4332" size={18} />
            </View>
            <View style={styles.securityCopy}>
              <Text style={styles.securityTitle}>{labels.securityTitle}</Text>
              <Text style={styles.securityText}>{labels.securityText}</Text>
            </View>
          </View>

          {/* PRIMARY SUBMIT BUTTON */}
          <View style={styles.submitSection}>
            <Pressable
              accessibilityHint="Submits your Tur leaf photo and recorded voice for prescription guidance"
              accessibilityLabel={labels.submit}
              accessibilityRole="button"
              disabled={!recordedUri}
              onPress={handleSubmit}
              style={({ pressed }) => [
                styles.submitButton,
                Boolean(recordedUri) ? styles.submitButtonEnabled : styles.submitButtonDisabled,
                pressed && Boolean(recordedUri) && styles.buttonPressed,
              ]}
            >
              <Text
                style={[
                  styles.submitButtonText,
                  Boolean(recordedUri)
                    ? styles.submitButtonTextEnabled
                    : styles.submitButtonTextDisabled,
                ]}
              >
                {labels.submit}
              </Text>
              {Boolean(recordedUri) && <ArrowGlyph color="#FFFFFF" size={16} />}
            </Pressable>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

// ============================================================================
// STYLES (TurSathi AI Premium Agricultural System)
// ============================================================================
const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#F8F6F0',
  },
  scrollContent: {
    flexGrow: 1,
    alignItems: 'center',
    paddingBottom: 36,
  },
  page: {
    width: '100%',
    maxWidth: 560,
    paddingHorizontal: 20,
    paddingTop: 8,
  },

  // Header
  header: {
    minHeight: 52,
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  backButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#E2E8DC',
    alignItems: 'center',
    justifyContent: 'center',
    elevation: 2,
    shadowColor: '#1A4D33',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 6,
  },
  backBox: {
    width: 20,
    height: 20,
    justifyContent: 'center',
    alignItems: 'center',
  },
  backShaft: {
    width: 12,
    height: 2,
    borderRadius: 1,
    marginRight: -4,
  },
  backHead: {
    position: 'absolute',
    left: 3,
    width: 8,
    height: 8,
    borderLeftWidth: 2,
    borderBottomWidth: 2,
    transform: [{ rotate: '45deg' }],
  },
  headerCopy: {
    flex: 1,
    alignItems: 'center',
    paddingHorizontal: 8,
  },
  brand: {
    fontSize: 12,
    fontWeight: '700',
    color: '#1A4D33',
    letterSpacing: 1.1,
    textTransform: 'uppercase',
  },
  headerRightSpacer: {
    width: 44,
  },

  // Title Section
  titleSection: {
    marginTop: 6,
    marginBottom: 20,
    alignItems: 'flex-start',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: '800',
    color: '#0F2419',
    letterSpacing: -0.3,
    marginBottom: 6,
  },
  headerSubtitle: {
    fontSize: 15,
    fontWeight: '500',
    color: '#476355',
    lineHeight: 22,
  },

  // Voice Card
  voiceCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 24,
    paddingVertical: 36,
    paddingHorizontal: 20,
    borderWidth: 1,
    borderColor: '#E6ECE7',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 20,
    ...Platform.select({
      ios: {
        shadowColor: '#1A4D33',
        shadowOffset: { width: 0, height: 6 },
        shadowOpacity: 0.08,
        shadowRadius: 14,
      },
      android: {
        elevation: 3,
      },
    }),
  },
  idleCenterArea: {
    alignItems: 'center',
    justifyContent: 'center',
    width: '100%',
  },
  micCircle: {
    width: 110,
    height: 110,
    borderRadius: 55,
    alignItems: 'center',
    justifyContent: 'center',
  },
  micCircleIdle: {
    backgroundColor: '#1B4332',
    ...Platform.select({
      ios: {
        shadowColor: '#1B4332',
        shadowOffset: { width: 0, height: 8 },
        shadowOpacity: 0.3,
        shadowRadius: 16,
      },
      android: {
        elevation: 8,
      },
    }),
  },
  micCircleRecording: {
    backgroundColor: '#D90429',
    ...Platform.select({
      ios: {
        shadowColor: '#D90429',
        shadowOffset: { width: 0, height: 8 },
        shadowOpacity: 0.35,
        shadowRadius: 16,
      },
      android: {
        elevation: 8,
      },
    }),
  },
  tapToRecordLabel: {
    color: '#1B4332',
    fontSize: 19,
    fontWeight: '800',
    marginTop: 22,
    textAlign: 'center',
  },
  tapToRecordSubtext: {
    color: '#658172',
    fontSize: 13,
    textAlign: 'center',
    marginTop: 4,
  },

  // Recording State
  recordingCenterArea: {
    alignItems: 'center',
    justifyContent: 'center',
    width: '100%',
  },
  micCircleWrapper: {
    width: 140,
    height: 140,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 8,
  },
  rippleRing: {
    position: 'absolute',
    width: 130,
    height: 130,
    borderRadius: 65,
    backgroundColor: 'rgba(217, 4, 41, 0.2)',
  },
  recordingStatusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginTop: 6,
    marginBottom: 4,
  },
  recordingDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: '#D90429',
  },
  recordingText: {
    color: '#D90429',
    fontSize: 17,
    fontWeight: '700',
    letterSpacing: 0.3,
  },
  timerDisplay: {
    color: '#0F2419',
    fontSize: 34,
    fontWeight: '800',
    letterSpacing: 1.5,
    fontVariant: ['tabular-nums'],
    marginVertical: 8,
  },
  listeningSubtext: {
    color: '#476355',
    fontSize: 14,
    fontWeight: '500',
    textAlign: 'center',
    marginBottom: 18,
  },
  stopPill: {
    paddingHorizontal: 22,
    paddingVertical: 10,
    borderRadius: 20,
    backgroundColor: '#FDE8E8',
    borderWidth: 1,
    borderColor: '#F8B4B4',
  },
  stopPillText: {
    color: '#D90429',
    fontSize: 14,
    fontWeight: '700',
  },

  // After Recording: Audio Player Card
  afterRecordingSection: {
    width: '100%',
    marginBottom: 16,
  },
  audioPlayerCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    padding: 20,
    borderWidth: 1,
    borderColor: '#E2E8DC',
    marginBottom: 16,
    ...Platform.select({
      ios: {
        shadowColor: '#1A4D33',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.08,
        shadowRadius: 12,
      },
      android: {
        elevation: 3,
      },
    }),
  },
  playerTopRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
    marginBottom: 16,
  },
  playRoundButton: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: '#1B4332',
    alignItems: 'center',
    justifyContent: 'center',
    ...Platform.select({
      ios: {
        shadowColor: '#1B4332',
        shadowOffset: { width: 0, height: 3 },
        shadowOpacity: 0.25,
        shadowRadius: 6,
      },
      android: {
        elevation: 3,
      },
    }),
  },
  playerInfo: {
    flex: 1,
    justifyContent: 'center',
  },
  playerTitle: {
    color: '#0F2419',
    fontSize: 16,
    fontWeight: '800',
    marginBottom: 4,
  },
  playerDurationText: {
    color: '#557A66',
    fontSize: 14,
    fontWeight: '700',
    fontVariant: ['tabular-nums'],
  },
  progressBarTrack: {
    width: '100%',
    height: 6,
    borderRadius: 3,
    backgroundColor: '#E8EFEA',
    overflow: 'hidden',
  },
  progressBarFill: {
    height: '100%',
    borderRadius: 3,
    backgroundColor: '#2D6A4F',
  },

  // Record Again Button (Secondary Outlined)
  recordAgainButton: {
    height: 50,
    borderRadius: 14,
    borderWidth: 1.5,
    borderColor: '#1B4332',
    backgroundColor: '#FFFFFF',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  recordAgainText: {
    color: '#1B4332',
    fontSize: 15,
    fontWeight: '700',
  },

  // Voice Privacy / Security Info Box
  securityBox: {
    backgroundColor: '#F3F7F4',
    borderRadius: 16,
    padding: 14,
    borderWidth: 1,
    borderColor: '#D8E5DC',
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
    marginBottom: 16,
  },
  securityIconWrap: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#E5EFE8',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 1,
  },
  securityCopy: {
    flex: 1,
  },
  securityTitle: {
    color: '#1B4332',
    fontSize: 14,
    fontWeight: '700',
    marginBottom: 2,
  },
  securityText: {
    color: '#476355',
    fontSize: 13,
    lineHeight: 18,
    fontWeight: '500',
  },

  // Primary Submit Button
  submitSection: {
    marginTop: 'auto',
    paddingTop: 4,
  },
  submitButton: {
    height: 56,
    borderRadius: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
  },
  submitButtonEnabled: {
    backgroundColor: '#1B4332',
    ...Platform.select({
      ios: {
        shadowColor: '#1B4332',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.28,
        shadowRadius: 8,
      },
      android: {
        elevation: 4,
      },
    }),
  },
  submitButtonDisabled: {
    backgroundColor: '#E0E7E2',
  },
  submitButtonText: {
    fontSize: 18,
    fontWeight: '700',
    letterSpacing: 0.2,
  },
  submitButtonTextEnabled: {
    color: '#FFFFFF',
  },
  submitButtonTextDisabled: {
    color: '#8CA094',
  },

  buttonPressed: {
    opacity: 0.88,
    transform: [{ scale: 0.985 }],
  },
});
