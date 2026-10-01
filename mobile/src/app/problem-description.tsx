import { useEffect, useRef, useState } from 'react';
import { useLocalSearchParams, useRouter } from 'expo-router';
import {
  ActivityIndicator,
  Alert,
  Animated,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import * as Speech from 'expo-speech';
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
// SPEECH LOCALES FOR VOICE GUIDANCE
// ============================================================================
const SPEECH_LOCALES: Record<Language, string> = {
  en: 'en-IN',
  mr: 'mr-IN',
  hi: 'hi-IN',
};

// ============================================================================
// LOCALIZED STRINGS (English, Marathi, Hindi)
// ============================================================================
const LOCALIZED_STRINGS: Record<
  Language,
  {
    brand: string;
    title: string;
    subtitle: string;
    cardTitle: string;
    cardMessage: string;
    playerLabel: string;
    playerIdleStatus: string;
    playerSpeakingStatus: string;
    playAccessibilityLabel: string;
    stopAccessibilityLabel: string;
    guidanceQuote: string;
    mainActionLabel: string;
    mainActionSubtext: string;
    audioUnavailable: string;
    // Voice Modal strings
    modalTitle: string;
    modalSubtitle: string;
    tapToRecord: string;
    recording: string;
    tapToStop: string;
    listeningSubtext: string;
    yourVoiceMessage: string;
    recordAgain: string;
    submit: string;
    submitting: string;
    securityTitle: string;
    securityText: string;
    permissionTitle: string;
    permissionRequired: string;
    recordingError: string;
    close: string;
  }
> = {
  en: {
    brand: 'TurSathi AI',
    title: 'Tell Us About Your Problem',
    subtitle: 'Tell us what you noticed on your Tur plant.',
    cardTitle: 'Before You Start',
    cardMessage: 'Tap Play to hear how to describe your problem.',
    playerLabel: 'Voice Guidance',
    playerIdleStatus: 'Tap to Listen',
    playerSpeakingStatus: 'Speaking... (Tap to Stop)',
    playAccessibilityLabel: 'Play voice guidance',
    stopAccessibilityLabel: 'Stop voice guidance',
    guidanceQuote:
      'If you have any problem with your Tur plant, tap the microphone, start recording, and tell us what problem you are seeing.',
    mainActionLabel: 'Start Recording',
    mainActionSubtext: 'Tap the microphone and tell us about your problem.',
    audioUnavailable: 'Voice guidance is ready for audio playback.',
    modalTitle: 'Describe Your Problem',
    modalSubtitle: 'Tell us what you noticed on your Tur plant.',
    tapToRecord: 'Tap to Record',
    recording: 'Recording...',
    tapToStop: 'Tap to stop',
    listeningSubtext: 'Describe what you see on the Tur plant.',
    yourVoiceMessage: 'Your Voice Message',
    recordAgain: 'Record Again',
    submit: 'Submit Voice',
    submitting: 'Submitting...',
    securityTitle: 'Your Voice Is Secure',
    securityText:
      'Your voice message is used only to understand your Tur leaf problem and provide relevant guidance.',
    permissionTitle: 'Microphone Permission',
    permissionRequired:
      'Microphone permission is required to record your problem description.',
    recordingError:
      'Unable to start recording. Please check your microphone permissions.',
    close: 'Close',
  },
  mr: {
    brand: 'TurSathi AI',
    title: 'तुमच्या समस्येबद्दल सांगा',
    subtitle: 'तुमच्या तुरीच्या झाडावर काय दिसले ते सांगा.',
    cardTitle: 'सुरू करण्यापूर्वी',
    cardMessage: 'समस्या कशी सांगायची हे ऐकण्यासाठी Play वर टॅप करा.',
    playerLabel: 'मार्गदर्शन ऑडिओ',
    playerIdleStatus: 'ऐकण्यासाठी टॅप करा',
    playerSpeakingStatus: 'बोलत आहे... (थांबवण्यासाठी टॅप करा)',
    playAccessibilityLabel: 'मार्गदर्शन ऑडिओ ऐका',
    stopAccessibilityLabel: 'मार्गदर्शन ऑडिओ थांबवा',
    guidanceQuote:
      'तुमच्या तुरीच्या पिकात काही समस्या दिसत असेल, तर मायक्रोफोनवर टॅप करून रेकॉर्डिंग सुरू करा आणि तुम्हाला कोणती समस्या दिसत आहे ते सांगा.',
    mainActionLabel: 'रेकॉर्डिंग सुरू करा',
    mainActionSubtext: 'मायक्रोफोनवर टॅप करा आणि तुमच्या समस्येबद्दल सांगा.',
    audioUnavailable: 'मार्गदर्शन ऑडिओ उपलब्ध आहे.',
    modalTitle: 'तुमच्या समस्येचे वर्णन करा',
    modalSubtitle: 'तुमच्या तुरीच्या झाडावर काय दिसले ते सांगा.',
    tapToRecord: 'रेकॉर्ड करण्यासाठी टॅप करा',
    recording: 'रेकॉर्डिंग सुरू आहे...',
    tapToStop: 'थांबवण्यासाठी टॅप करा',
    listeningSubtext: 'तूर पिकावर तुम्हाला काय दिसते त्याचे वर्णन करा.',
    yourVoiceMessage: 'तुमचा व्हॉइस संदेश',
    recordAgain: 'पुन्हा रेकॉर्ड करा',
    submit: 'पाठवा',
    submitting: 'पाठवत आहे...',
    securityTitle: 'तुमचा व्हॉइस सुरक्षित आहे',
    securityText:
      'तुमच्या तूर पिकाची समस्या समजून घेण्यासाठी आणि योग्य मार्गदर्शन देण्यासाठीच तुमचा व्हॉइस संदेश वापरला जातो.',
    permissionTitle: 'मायक्रोफोन परवानगी',
    permissionRequired:
      'समस्या रेकॉर्ड करण्यासाठी मायक्रोफोन परवानगी आवश्यक आहे.',
    recordingError:
      'रेकॉर्डिंग सुरू करता आले नाही. कृपया मायक्रोफोन परवानगी तपासा.',
    close: 'बंद करा',
  },
  hi: {
    brand: 'TurSathi AI',
    title: 'अपनी समस्या के बारे में बताएं',
    subtitle: 'अपने तूर के पौधे पर क्या दिखाई दे रहा है बताएं।',
    cardTitle: 'शुरू करने से पहले',
    cardMessage: 'अपनी समस्या कैसे बताएं, यह सुनने के लिए Play पर टैप करें।',
    playerLabel: 'मार्गदर्शन ऑडियो',
    playerIdleStatus: 'सुनने के लिए टैप करें',
    playerSpeakingStatus: 'बोल रहा है... (रोकने के लिए टैप करें)',
    playAccessibilityLabel: 'मार्गदर्शन ऑडियो सुनें',
    stopAccessibilityLabel: 'मार्गदर्शन ऑडियो रोकें',
    guidanceQuote:
      'अगर आपकी तूर की फसल में कोई समस्या दिखाई दे रही है, तो माइक्रोफोन पर टैप करके रिकॉर्डिंग शुरू करें और बताएं कि आपको क्या समस्या दिखाई दे रही है।',
    mainActionLabel: 'रिकॉर्डिंग शुरू करें',
    mainActionSubtext: 'माइक्रोफोन पर टैप करें और अपनी समस्या के बारे में बताएं।',
    audioUnavailable: 'मार्गदर्शन ऑडियो उपलब्ध है।',
    modalTitle: 'अपनी समस्या का वर्णन करें',
    modalSubtitle: 'अपने तूर के पौधे पर क्या दिखाई दे रहा है बताएं।',
    tapToRecord: 'रिकॉर्ड करने के लिए टैप करें',
    recording: 'रिकॉर्डिंग जारी है...',
    tapToStop: 'रोकने के लिए टैप करें',
    listeningSubtext: 'तूर फसल पर आपको क्या दिखाई दे रहा है, उसका वर्णन करें।',
    yourVoiceMessage: 'आपका वॉइस संदेश',
    recordAgain: 'फिर से रिकॉर्ड करें',
    submit: 'जमा करें',
    submitting: 'जमा हो रहा है...',
    securityTitle: 'आपकी वॉइस सुरक्षित है',
    securityText:
      'आपकी तूर फसल की समस्या को समझने और उचित मार्गदर्शन देने के लिए ही आपके वॉइस संदेश का उपयोग किया जाता है।',
    permissionTitle: 'माइक्रोफ़ोन अनुमति',
    permissionRequired:
      'समस्या रिकॉर्ड करने के लिए माइक्रोफ़ोन की अनुमति आवश्यक है।',
    recordingError:
      'रिकॉर्डिंग शुरू नहीं हो सकी। कृपया माइक्रोफ़ोन अनुमति जांचें।',
    close: 'बंद करें',
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

function SpeakerGlyph({ color = '#1B4332', size = 20 }: { color?: string; size?: number }) {
  const scale = size / 20;
  return (
    <View style={{ width: size, height: size, justifyContent: 'center', alignItems: 'center' }}>
      <View
        style={{
          position: 'absolute',
          left: 1 * scale,
          width: 5 * scale,
          height: 8 * scale,
          backgroundColor: color,
          borderRadius: 1,
        }}
      />
      <View
        style={{
          position: 'absolute',
          left: 5 * scale,
          width: 0,
          height: 0,
          borderStyle: 'solid',
          borderRightWidth: 7 * scale,
          borderTopWidth: 7 * scale,
          borderBottomWidth: 7 * scale,
          borderLeftWidth: 0,
          borderRightColor: color,
          borderTopColor: 'transparent',
          borderBottomColor: 'transparent',
        }}
      />
      <View
        style={{
          position: 'absolute',
          right: 2 * scale,
          width: 8 * scale,
          height: 8 * scale,
          borderRightWidth: 2 * scale,
          borderTopWidth: 2 * scale,
          borderColor: color,
          borderRadius: 5 * scale,
          transform: [{ rotate: '45deg' }],
        }}
      />
    </View>
  );
}

function PlayGlyph({ size = 16, color = '#FFFFFF' }: { size?: number; color?: string }) {
  return (
    <View
      style={{
        width: 0,
        height: 0,
        borderStyle: 'solid',
        borderLeftWidth: size,
        borderTopWidth: size * 0.58,
        borderBottomWidth: size * 0.58,
        borderLeftColor: color,
        borderTopColor: 'transparent',
        borderBottomColor: 'transparent',
        marginLeft: 2,
      }}
    />
  );
}

function PauseGlyph({ size = 16, color = '#FFFFFF' }: { size?: number; color?: string }) {
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

function MicGlyph({ size = 52, color = '#FFFFFF' }: { size?: number; color?: string }) {
  const scale = size / 52;
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
          height: 34 * scale,
          borderRadius: 10 * scale,
          backgroundColor: color,
        }}
      />
      <View
        style={{
          position: 'absolute',
          top: 10 * scale,
          width: 38 * scale,
          height: 30 * scale,
          borderBottomLeftRadius: 19 * scale,
          borderBottomRightRadius: 19 * scale,
          borderWidth: 3.5 * scale,
          borderTopWidth: 0,
          borderColor: color,
        }}
      />
      <View
        style={{
          width: 4 * scale,
          height: 11 * scale,
          backgroundColor: color,
          marginTop: 3 * scale,
        }}
      />
      <View
        style={{
          width: 28 * scale,
          height: 3.8 * scale,
          borderRadius: 1.9 * scale,
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

function CloseGlyph({ size = 20, color = '#476355' }: { size?: number; color?: string }) {
  return (
    <View style={{ width: size, height: size, justifyContent: 'center', alignItems: 'center' }}>
      <View
        style={{
          position: 'absolute',
          width: size,
          height: 2,
          backgroundColor: color,
          borderRadius: 1,
          transform: [{ rotate: '45deg' }],
        }}
      />
      <View
        style={{
          position: 'absolute',
          width: size,
          height: 2,
          backgroundColor: color,
          borderRadius: 1,
          transform: [{ rotate: '-45deg' }],
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

export default function ProblemDescriptionScreen() {
  const router = useRouter();
  const { language } = useLanguage();
  const labels = LOCALIZED_STRINGS[language] || LOCALIZED_STRINGS.en;

  // Guidance audio playback state
  const [isSpeaking, setIsSpeaking] = useState(false);

  // Modal Overlay state
  const [isModalVisible, setIsModalVisible] = useState(false);

  // Audio recording state inside modal
  const [isRecording, setIsRecording] = useState(false);
  const [recordedUri, setRecordedUri] = useState<string | null>(null);
  const [timerSeconds, setTimerSeconds] = useState(0);
  const [recordedDuration, setRecordedDuration] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Route parameters received from scan screen
  const params = useLocalSearchParams<{ imageUri?: string | string[]; scanId?: string | string[] }>();
  const rawImageUri = Array.isArray(params.imageUri)
    ? params.imageUri[0]
    : (params.imageUri ?? '');

  // scanId links this session to the backend scan/case record
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

  // Animations for recording pulse indicator inside modal
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const rippleAnim = useRef(new Animated.Value(1)).current;
  const rippleOpacity = useRef(new Animated.Value(0.4)).current;

  // expo-audio recorder instance
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);

  // expo-audio player instance for recorded farmer voice playback
  const player = useAudioPlayer(recordedUri ? { uri: recordedUri } : null);
  const playerStatus = useAudioPlayerStatus(player);

  const isAudioPlaying = Boolean(playerStatus.playing);
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

  // Recording pulse animation loop
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

  // Unmount cleanup - safely stop speech and audio
  useEffect(() => {
    return () => {
      try {
        Speech.stop();
      } catch {}
      try {
        if (player && typeof player.pause === 'function') {
          player.pause();
        }
      } catch {}
      try {
        if (recorder && recorder.isRecording) {
          recorder.stop().catch(() => {});
        }
      } catch {}
    };
  }, []);

  // Stop speech if language changes
  useEffect(() => {
    try {
      Speech.stop();
    } catch {}
    setIsSpeaking(false);
  }, [language]);

  // Toggle voice guidance quote playback via expo-speech
  const handleToggleGuidance = async () => {
    if (isSpeaking) {
      try {
        await Speech.stop();
      } catch {}
      setIsSpeaking(false);
      return;
    }

    try {
      await Speech.stop();
    } catch {}

    const textToSpeak = labels.guidanceQuote;
    const locale = SPEECH_LOCALES[language] || 'en-IN';

    setIsSpeaking(true);

    try {
      Speech.speak(textToSpeak, {
        language: locale,
        rate: 0.9,
        pitch: 1.0,
        onStart: () => {
          setIsSpeaking(true);
        },
        onDone: () => {
          setIsSpeaking(false);
        },
        onStopped: () => {
          setIsSpeaking(false);
        },
        onError: (err) => {
          console.warn('[PROBLEM-DESCRIPTION] Speech error:', err);
          setIsSpeaking(false);
        },
      });
    } catch (err) {
      console.warn('[PROBLEM-DESCRIPTION] Failed to invoke Speech.speak:', err);
      setIsSpeaking(false);
    }
  };

  // Open Voice Recording Modal
  const handleOpenModal = () => {
    try {
      Speech.stop();
    } catch {}
    setIsSpeaking(false);
    setIsModalVisible(true);
  };

  // Close Voice Recording Modal safely
  const handleCloseModal = async () => {
    if (isSubmitting) return;

    try {
      if (isAudioPlaying) {
        player.pause();
      }
    } catch {}

    try {
      if (isRecording && recorder) {
        await recorder.stop().catch(() => {});
      }
    } catch {}

    setIsRecording(false);
    setIsModalVisible(false);
  };

  // 1. START RECORDING inside modal
  const handleStartRecording = async () => {
    try {
      if (isAudioPlaying) {
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
      console.error('[PROBLEM-DESCRIPTION] Failed to start recording:', err);
      Alert.alert(labels.permissionTitle, labels.recordingError);
      setIsRecording(false);
    }
  };

  // 2. STOP RECORDING inside modal
  const handleStopRecording = async () => {
    try {
      await recorder.stop();
      setIsRecording(false);
      const uri = recorder.uri;
      console.log('[PROBLEM-DESCRIPTION] Recording completed. URI:', uri);
      if (uri) {
        setRecordedUri(uri);
        setRecordedDuration(timerSeconds > 0 ? timerSeconds : 1);
      }
    } catch (err) {
      console.error('[PROBLEM-DESCRIPTION] Failed to stop recording:', err);
      setIsRecording(false);
    }
  };

  // 3. PLAY / PAUSE RECORDED AUDIO inside modal
  const handleTogglePlayback = async () => {
    if (!recordedUri) return;

    if (isAudioPlaying) {
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
      console.warn('[PROBLEM-DESCRIPTION] Playback error:', err);
    }
  };

  // 4. RECORD AGAIN inside modal
  const handleRecordAgain = async () => {
    try {
      if (isAudioPlaying) {
        player.pause();
      }
    } catch {}
    setRecordedUri(null);
    setTimerSeconds(0);
    setRecordedDuration(0);
  };

  // 5. SUBMIT RECORDED VOICE inside modal
  const handleSubmitVoice = async () => {
    if (!recordedUri || isSubmitting) return;

    if (isAudioPlaying) {
      try {
        player.pause();
      } catch {}
    }

    setIsSubmitting(true);
    const finalImageUri = normalizedImageUri || rawImageUri;

    console.log('[PROBLEM-DESCRIPTION] Submitting voice report:');
    console.log('  imageUri:', finalImageUri);
    console.log('  voiceUri:', recordedUri);
    console.log('  scanId:', scanId);

    // Upload voice recording to backend
    if (scanId !== null && !isNaN(scanId)) {
      try {
        const token = await getAuthToken();
        if (token) {
          const langCode = language === 'mr' ? 'mr' : language === 'hi' ? 'hi' : 'en';
          await uploadVoiceReport(
            scanId,
            recordedUri,
            token,
            langCode,
            recordedDuration > 0 ? recordedDuration : undefined,
          );
          console.log('[PROBLEM-DESCRIPTION] Voice uploaded successfully for scan_id:', scanId);
        }
      } catch (uploadErr) {
        if (uploadErr instanceof ScanUploadError) {
          console.warn('[PROBLEM-DESCRIPTION] Voice upload failed (HTTP', uploadErr.httpStatus, '):', uploadErr.message);
        } else {
          console.warn('[PROBLEM-DESCRIPTION] Voice upload error:', uploadErr);
        }
      }
    } else {
      console.warn('[PROBLEM-DESCRIPTION] No scanId available — voice upload skipped.');
    }

    setIsSubmitting(false);
    setIsModalVisible(false);

    router.push({
      pathname: '/prescription',
      params: {
        imageUri: encodeURIComponent(finalImageUri),
        voiceUri: encodeURIComponent(recordedUri),
        ...(scanId !== null && !isNaN(scanId) ? { scanId: String(scanId) } : {}),
      },
    });
  };

  const handleBackToScan = () => {
    try {
      Speech.stop();
    } catch {}
    setIsSpeaking(false);
    router.push('/scan');
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
              accessibilityHint="Returns to the photo capture screen"
              accessibilityLabel="Go back"
              accessibilityRole="button"
              hitSlop={8}
              onPress={handleBackToScan}
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

          {/* STEP 1: VOICE GUIDANCE CARD */}
          <View style={styles.guidanceCard}>
            <View style={styles.cardHeaderRow}>
              <View style={styles.speakerIconWrap}>
                <SpeakerGlyph color="#1B4332" size={20} />
              </View>
              <View style={styles.cardHeaderCopy}>
                <Text style={styles.cardTitle}>{labels.cardTitle}</Text>
                <Text style={styles.cardSubtitle}>{labels.cardMessage}</Text>
              </View>
            </View>

            {/* Full-width Play Voice Help button (matches Camera page) */}
            <Pressable
              accessibilityHint="Plays instructional voice guidance"
              accessibilityLabel={
                isSpeaking ? labels.stopAccessibilityLabel : labels.playAccessibilityLabel
              }
              accessibilityRole="button"
              onPress={handleToggleGuidance}
              style={({ pressed }) => [
                styles.voiceHelpButton,
                isSpeaking && styles.voiceHelpButtonActive,
                pressed && styles.buttonPressed,
              ]}
            >
              <View style={styles.voiceHelpIconWrap}>
                {isSpeaking ? (
                  <PauseGlyph color="#FFFFFF" size={12} />
                ) : (
                  <PlayGlyph color="#D5BB79" size={12} />
                )}
              </View>
              <Text style={styles.voiceHelpButtonText}>
                {isSpeaking ? labels.playerSpeakingStatus : labels.playerLabel}
              </Text>
            </Pressable>

            {/* Subtle Progress Bar */}
            <View style={styles.progressBarTrack}>
              <View
                style={[
                  styles.progressBarFill,
                  { width: isSpeaking ? '100%' : '0%' },
                ]}
              />
            </View>

            {/* Explanatory Quote */}
            <View style={styles.quoteBox}>
              <Text style={styles.quoteText}>{labels.guidanceQuote}</Text>
            </View>
          </View>

          {/* STEP 1: MAIN MICROPHONE ACTION AREA (Opens Modal) */}
          <View style={styles.mainActionCard}>
            <Pressable
              accessibilityHint="Opens the voice recording modal"
              accessibilityLabel={labels.mainActionLabel}
              accessibilityRole="button"
              onPress={handleOpenModal}
              style={({ pressed }) => [
                styles.largeMicButton,
                pressed && styles.buttonPressed,
              ]}
            >
              <MicGlyph color="#FFFFFF" size={54} />
            </Pressable>

            <Pressable
              accessibilityRole="button"
              onPress={handleOpenModal}
            >
              <Text style={styles.actionLabel}>{labels.mainActionLabel}</Text>
            </Pressable>
            <Text style={styles.actionSubtext}>{labels.mainActionSubtext}</Text>
          </View>
        </View>
      </ScrollView>

      {/* ==================================================================== */}
      {/* PREMIUM VOICE RECORDING MODAL (Native Overlay on Same Page) */}
      {/* ==================================================================== */}
      <Modal
        animationType="slide"
        hardwareAccelerated
        onRequestClose={handleCloseModal}
        transparent={true}
        visible={isModalVisible}
      >
        <View style={modalStyles.backdrop}>
          <Pressable style={modalStyles.backdropTouchable} onPress={handleCloseModal} />

          <View style={modalStyles.sheetContainer}>
            {/* Modal Header */}
            <View style={modalStyles.headerRow}>
              <View style={modalStyles.headerTextWrap}>
                <Text style={modalStyles.modalTitle}>{labels.modalTitle}</Text>
                <Text style={modalStyles.modalSubtitle}>{labels.modalSubtitle}</Text>
              </View>

              <Pressable
                accessibilityLabel={labels.close}
                hitSlop={12}
                onPress={handleCloseModal}
                style={({ pressed }) => [modalStyles.closeButton, pressed && styles.buttonPressed]}
              >
                <CloseGlyph color="#476355" size={18} />
              </Pressable>
            </View>

            {/* Modal Body */}
            {!recordedUri ? (
              /* State 1: Active Recording / Ready to Record */
              <View style={modalStyles.bodyContent}>
                <Text style={modalStyles.listeningSubtext}>{labels.listeningSubtext}</Text>

                <View style={modalStyles.timerContainer}>
                  <Text style={modalStyles.timerText}>{formatTimer(timerSeconds)}</Text>
                </View>

                <View style={modalStyles.micSection}>
                  {isRecording && (
                    <Animated.View
                      style={[
                        modalStyles.rippleRing,
                        {
                          transform: [{ scale: rippleAnim as any }],
                          opacity: rippleOpacity as any,
                        },
                      ]}
                    />
                  )}

                  <Animated.View
                    style={[
                      modalStyles.micButtonBase,
                      isRecording && modalStyles.micButtonActive,
                      { transform: [{ scale: pulseAnim as any }] },
                    ]}
                  >
                    {isRecording ? (
                      <Pressable
                        accessibilityLabel={labels.tapToStop}
                        onPress={handleStopRecording}
                        style={({ pressed }) => [modalStyles.micTouchable, pressed && styles.buttonPressed]}
                      >
                        <StopGlyph color="#FFFFFF" size={24} />
                      </Pressable>
                    ) : (
                      <Pressable
                        accessibilityLabel={labels.tapToRecord}
                        onPress={handleStartRecording}
                        style={({ pressed }) => [modalStyles.micTouchable, pressed && styles.buttonPressed]}
                      >
                        <MicGlyph color="#FFFFFF" size={44} />
                      </Pressable>
                    )}
                  </Animated.View>
                </View>

                <Text style={modalStyles.statusLabel}>
                  {isRecording ? labels.recording : labels.tapToRecord}
                </Text>
                {isRecording && (
                  <Text style={modalStyles.subStatusLabel}>{labels.tapToStop}</Text>
                )}

                {/* Security Footer */}
                <View style={modalStyles.securityBox}>
                  <ShieldGlyph color="#1B4332" size={16} />
                  <Text style={modalStyles.securityText}>{labels.securityText}</Text>
                </View>
              </View>
            ) : (
              /* State 2: Recorded Voice Review & Playback */
              <View style={modalStyles.bodyContent}>
                <Text style={modalStyles.reviewTitle}>{labels.yourVoiceMessage}</Text>

                {/* Playback Box */}
                <View style={modalStyles.playerCard}>
                  <Pressable
                    accessibilityLabel="Toggle Playback"
                    onPress={handleTogglePlayback}
                    style={({ pressed }) => [modalStyles.playButtonCircle, pressed && styles.buttonPressed]}
                  >
                    {isAudioPlaying ? (
                      <PauseGlyph color="#FFFFFF" size={16} />
                    ) : (
                      <PlayGlyph color="#FFFFFF" size={16} />
                    )}
                  </Pressable>

                  <View style={modalStyles.playerMeta}>
                    <Text style={modalStyles.playerTimer}>
                      {formatTimer(currentSeconds)} / {formatTimer(durationSeconds)}
                    </Text>
                    <View style={modalStyles.playerProgressTrack}>
                      <View
                        style={[
                          modalStyles.playerProgressFill,
                          { width: `${Math.round(progressPercent * 100)}%` },
                        ]}
                      />
                    </View>
                  </View>
                </View>

                {/* Modal Action Buttons */}
                <View style={modalStyles.actionsRow}>
                  <Pressable
                    accessibilityLabel={labels.recordAgain}
                    onPress={handleRecordAgain}
                    style={({ pressed }) => [modalStyles.recordAgainBtn, pressed && styles.buttonPressed]}
                  >
                    <RefreshGlyph color="#1B4332" size={16} />
                    <Text style={modalStyles.recordAgainText}>{labels.recordAgain}</Text>
                  </Pressable>

                  <Pressable
                    accessibilityLabel={labels.submit}
                    disabled={isSubmitting}
                    onPress={handleSubmitVoice}
                    style={({ pressed }) => [
                      modalStyles.submitBtn,
                      isSubmitting && modalStyles.submitBtnDisabled,
                      pressed && styles.buttonPressed,
                    ]}
                  >
                    {isSubmitting ? (
                      <ActivityIndicator color="#FFFFFF" size="small" />
                    ) : (
                      <>
                        <Text style={modalStyles.submitBtnText}>{labels.submit}</Text>
                        <ArrowGlyph color="#FFFFFF" size={14} />
                      </>
                    )}
                  </Pressable>
                </View>
              </View>
            )}
          </View>
        </View>
      </Modal>
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

  // Voice Guidance Card
  guidanceCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 22,
    padding: 20,
    borderWidth: 1,
    borderColor: '#E2E8DC',
    marginBottom: 24,
    ...Platform.select({
      ios: {
        shadowColor: '#1A4D33',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.06,
        shadowRadius: 10,
      },
      android: {
        elevation: 2,
      },
    }),
  },
  cardHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 16,
  },
  speakerIconWrap: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: '#EAF3EC',
    borderWidth: 1,
    borderColor: '#CBE2D1',
    alignItems: 'center',
    justifyContent: 'center',
  },
  cardHeaderCopy: {
    flex: 1,
  },
  cardTitle: {
    color: '#0F2419',
    fontSize: 16,
    fontWeight: '800',
    marginBottom: 2,
  },
  cardSubtitle: {
    color: '#557A66',
    fontSize: 13,
    fontWeight: '500',
  },
  voiceHelpButton: {
    minHeight: 42,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    borderWidth: 1,
    borderColor: '#D5BB79',
    borderRadius: 12,
    backgroundColor: '#1F5137',
    marginBottom: 10,
    ...Platform.select({
      ios: {
        shadowColor: '#0E2B1E',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
      },
      android: {
        elevation: 2,
      },
    }),
  },
  voiceHelpButtonActive: {
    backgroundColor: '#143825',
    borderColor: '#C7A45A',
  },
  voiceHelpIconWrap: {
    width: 18,
    height: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  voiceHelpButtonText: {
    color: '#FFFEFA',
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 0.3,
  },
  progressBarTrack: {
    width: '100%',
    height: 5,
    borderRadius: 2.5,
    backgroundColor: '#E6EFE8',
    overflow: 'hidden',
    marginBottom: 16,
  },
  progressBarFill: {
    height: '100%',
    borderRadius: 2.5,
    backgroundColor: '#2D6A4F',
  },
  quoteBox: {
    backgroundColor: '#F3F7F4',
    borderRadius: 12,
    padding: 14,
    borderLeftWidth: 3.5,
    borderLeftColor: '#2D6A4F',
  },
  quoteText: {
    color: '#2C493B',
    fontSize: 13,
    lineHeight: 20,
    fontWeight: '500',
    fontStyle: 'italic',
  },

  // Main Action Card
  mainActionCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 24,
    paddingVertical: 36,
    paddingHorizontal: 20,
    borderWidth: 1,
    borderColor: '#E2E8DC',
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
  largeMicButton: {
    width: 116,
    height: 116,
    borderRadius: 58,
    backgroundColor: '#1B4332',
    alignItems: 'center',
    justifyContent: 'center',
    ...Platform.select({
      ios: {
        shadowColor: '#1B4332',
        shadowOffset: { width: 0, height: 8 },
        shadowOpacity: 0.32,
        shadowRadius: 18,
      },
      android: {
        elevation: 8,
      },
    }),
  },
  actionLabel: {
    color: '#1B4332',
    fontSize: 20,
    fontWeight: '800',
    marginTop: 22,
    marginBottom: 6,
    textAlign: 'center',
  },
  actionSubtext: {
    color: '#557A66',
    fontSize: 14,
    fontWeight: '500',
    textAlign: 'center',
    paddingHorizontal: 16,
    lineHeight: 20,
  },

  buttonPressed: {
    opacity: 0.88,
    transform: [{ scale: 0.985 }],
  },
});

// ============================================================================
// MODAL OVERLAY STYLES
// ============================================================================
const modalStyles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(15, 36, 25, 0.62)',
    justifyContent: 'flex-end',
    alignItems: 'center',
  },
  backdropTouchable: {
    ...StyleSheet.absoluteFill,
  },
  sheetContainer: {
    width: '100%',
    maxWidth: 560,
    backgroundColor: '#FFFFFF',
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    paddingHorizontal: 24,
    paddingTop: 24,
    paddingBottom: Platform.OS === 'ios' ? 40 : 28,
    borderWidth: 1,
    borderColor: '#E2E8DC',
    ...Platform.select({
      ios: {
        shadowColor: '#000000',
        shadowOffset: { width: 0, height: -4 },
        shadowOpacity: 0.16,
        shadowRadius: 16,
      },
      android: {
        elevation: 12,
      },
    }),
  },

  // Modal Header
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 20,
  },
  headerTextWrap: {
    flex: 1,
    paddingRight: 12,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: '800',
    color: '#0F2419',
    letterSpacing: -0.2,
    marginBottom: 4,
  },
  modalSubtitle: {
    fontSize: 14,
    fontWeight: '500',
    color: '#557A66',
  },
  closeButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#F3F7F4',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#E2E8DC',
  },

  // Modal Body Content
  bodyContent: {
    alignItems: 'center',
  },
  listeningSubtext: {
    fontSize: 14,
    color: '#476355',
    fontWeight: '500',
    textAlign: 'center',
    marginBottom: 16,
  },
  timerContainer: {
    backgroundColor: '#F3F7F4',
    paddingHorizontal: 16,
    paddingVertical: 6,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#DDE9DF',
    marginBottom: 20,
  },
  timerText: {
    fontSize: 22,
    fontWeight: '800',
    color: '#1B4332',
    fontVariant: ['tabular-nums'],
  },

  // Mic Button Section
  micSection: {
    width: 130,
    height: 130,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
  },
  rippleRing: {
    position: 'absolute',
    width: 124,
    height: 124,
    borderRadius: 62,
    backgroundColor: '#D63031',
  },
  micButtonBase: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: '#1B4332',
    alignItems: 'center',
    justifyContent: 'center',
    ...Platform.select({
      ios: {
        shadowColor: '#1B4332',
        shadowOffset: { width: 0, height: 6 },
        shadowOpacity: 0.28,
        shadowRadius: 12,
      },
      android: {
        elevation: 6,
      },
    }),
  },
  micButtonActive: {
    backgroundColor: '#D63031',
  },
  micTouchable: {
    width: '100%',
    height: '100%',
    alignItems: 'center',
    justifyContent: 'center',
  },

  statusLabel: {
    fontSize: 16,
    fontWeight: '700',
    color: '#0F2419',
    marginBottom: 2,
  },
  subStatusLabel: {
    fontSize: 13,
    fontWeight: '500',
    color: '#557A66',
  },

  // Security Box
  securityBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F7FAF7',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#DDE9DF',
    gap: 10,
    marginTop: 20,
  },
  securityText: {
    flex: 1,
    fontSize: 12,
    fontWeight: '500',
    color: '#2C493B',
    lineHeight: 17,
  },

  // State 2: Review & Playback
  reviewTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#0F2419',
    marginBottom: 16,
  },
  playerCard: {
    width: '100%',
    backgroundColor: '#F7FAF7',
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: '#DDE9DF',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    marginBottom: 24,
  },
  playButtonCircle: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#1B4332',
    alignItems: 'center',
    justifyContent: 'center',
  },
  playerMeta: {
    flex: 1,
  },
  playerTimer: {
    fontSize: 13,
    fontWeight: '700',
    color: '#0F2419',
    fontVariant: ['tabular-nums'],
    marginBottom: 6,
  },
  playerProgressTrack: {
    height: 6,
    backgroundColor: '#E6EFE8',
    borderRadius: 3,
    overflow: 'hidden',
  },
  playerProgressFill: {
    height: '100%',
    backgroundColor: '#2D6A4F',
    borderRadius: 3,
  },

  // Modal Actions
  actionsRow: {
    width: '100%',
    flexDirection: 'row',
    gap: 12,
  },
  recordAgainBtn: {
    flex: 1,
    height: 48,
    borderRadius: 14,
    backgroundColor: '#FFFFFF',
    borderWidth: 1.5,
    borderColor: '#CBE2D1',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  recordAgainText: {
    fontSize: 14,
    fontWeight: '700',
    color: '#1B4332',
  },
  submitBtn: {
    flex: 1.3,
    height: 48,
    borderRadius: 14,
    backgroundColor: '#1B4332',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    ...Platform.select({
      ios: {
        shadowColor: '#1B4332',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.24,
        shadowRadius: 8,
      },
      android: {
        elevation: 4,
      },
    }),
  },
  submitBtnDisabled: {
    opacity: 0.6,
  },
  submitBtnText: {
    fontSize: 15,
    fontWeight: '700',
    color: '#FFFFFF',
  },
});
