import { useEffect, useState } from 'react';
import { useLocalSearchParams, useRouter } from 'expo-router';
import {
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import * as Speech from 'expo-speech';
import { useLanguage } from '../i18n/LanguageContext';
import { Language } from '../i18n/translations';

// ============================================================================
// SPEECH LOCALES
// ============================================================================
const SPEECH_LOCALES: Record<Language, string> = {
  en: 'en-IN',
  mr: 'mr-IN',
  hi: 'hi-IN',
};

// ============================================================================
// STEP 1 LOCALIZED STRINGS (English, Marathi, Hindi)
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

export default function ProblemDescriptionScreen() {
  const router = useRouter();
  const { language } = useLanguage();
  const labels = LOCALIZED_STRINGS[language] || LOCALIZED_STRINGS.en;
  const [isSpeaking, setIsSpeaking] = useState(false);

  // Route parameters received from scan screen
  const params = useLocalSearchParams<{ imageUri?: string | string[] }>();
  const rawImageUri = Array.isArray(params.imageUri)
    ? params.imageUri[0]
    : (params.imageUri ?? '');

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

  // Unmount cleanup - safely stop speech
  useEffect(() => {
    return () => {
      try {
        Speech.stop();
      } catch {}
    };
  }, []);

  // Stop speech if application language changes
  useEffect(() => {
    try {
      Speech.stop();
    } catch {}
    setIsSpeaking(false);
  }, [language]);

  // TOGGLE GUIDANCE AUDIO PLAYBACK VIA EXPO-SPEECH
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

  // NAVIGATE TO STEP 2 (VOICE RECORDING PAGE)
  const handleStartRecording = () => {
    // Immediately stop speech before user starts recording problem
    try {
      Speech.stop();
    } catch {}
    setIsSpeaking(false);

    const finalImageUri = normalizedImageUri || rawImageUri;
    router.push({
      pathname: '/voice-record',
      params: {
        imageUri: encodeURIComponent(finalImageUri),
      },
    });
  };

  const handleBackToScan = () => {
    // Stop speech when navigating back
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

            {/* Compact Audio Player */}
            <View style={styles.compactPlayerBox}>
              <Pressable
                accessibilityHint="Plays instructional voice guidance"
                accessibilityLabel={
                  isSpeaking ? labels.stopAccessibilityLabel : labels.playAccessibilityLabel
                }
                accessibilityRole="button"
                onPress={handleToggleGuidance}
                style={({ pressed }) => [
                  styles.playButtonCompact,
                  pressed && styles.buttonPressed,
                ]}
              >
                {isSpeaking ? (
                  <PauseGlyph color="#FFFFFF" size={14} />
                ) : (
                  <PlayGlyph color="#FFFFFF" size={14} />
                )}
              </Pressable>

              <View style={styles.playerMetaCol}>
                <Text style={styles.playerMetaTitle}>{labels.playerLabel}</Text>
                <Text style={styles.playerMetaTimer}>
                  {isSpeaking ? labels.playerSpeakingStatus : labels.playerIdleStatus}
                </Text>
              </View>
            </View>

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

          {/* STEP 1: MAIN MICROPHONE ACTION AREA */}
          <View style={styles.mainActionCard}>
            <Pressable
              accessibilityHint="Navigates to the voice recording screen"
              accessibilityLabel={labels.mainActionLabel}
              accessibilityRole="button"
              onPress={handleStartRecording}
              style={({ pressed }) => [
                styles.largeMicButton,
                pressed && styles.buttonPressed,
              ]}
            >
              <MicGlyph color="#FFFFFF" size={54} />
            </Pressable>

            <Pressable
              accessibilityRole="button"
              onPress={handleStartRecording}
            >
              <Text style={styles.actionLabel}>{labels.mainActionLabel}</Text>
            </Pressable>
            <Text style={styles.actionSubtext}>{labels.mainActionSubtext}</Text>
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
  compactPlayerBox: {
    backgroundColor: '#F7FAF7',
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#DDE9DF',
    paddingVertical: 12,
    paddingHorizontal: 14,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 10,
  },
  playButtonCompact: {
    width: 42,
    height: 42,
    borderRadius: 21,
    backgroundColor: '#1B4332',
    alignItems: 'center',
    justifyContent: 'center',
    ...Platform.select({
      ios: {
        shadowColor: '#1B4332',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.2,
        shadowRadius: 4,
      },
      android: {
        elevation: 2,
      },
    }),
  },
  playerMetaCol: {
    flex: 1,
  },
  playerMetaTitle: {
    color: '#0F2419',
    fontSize: 14,
    fontWeight: '700',
    marginBottom: 2,
  },
  playerMetaTimer: {
    color: '#557A66',
    fontSize: 12,
    fontWeight: '600',
    fontVariant: ['tabular-nums'],
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
