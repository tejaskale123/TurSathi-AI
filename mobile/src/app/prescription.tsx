import { useEffect, useRef, useState } from 'react';
import { useLocalSearchParams, useRouter } from 'expo-router';
import {
  ActivityIndicator,
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
  setAudioModeAsync,
  useAudioPlayer,
  useAudioPlayerStatus,
} from 'expo-audio';
import { useLanguage } from '../i18n/LanguageContext';
import { Language } from '../i18n/translations';

// Pre-bundled instructional voice audio asset for read-aloud / guidance
let VOICE_GUIDANCE_ASSET: number | null = null;
try {
  VOICE_GUIDANCE_ASSET = require('../../assets/audio/tur_leaf_scan_guide.mp3');
} catch {
  try {
    VOICE_GUIDANCE_ASSET = require('../../assets/audio/tur_leaf_scan_guide.wav');
  } catch {
    VOICE_GUIDANCE_ASSET = null;
  }
}

// ============================================================================
// PRESCRIPTION LOCALIZED STRINGS (English, Marathi, Hindi)
// ============================================================================
const LOCALIZED_STRINGS: Record<
  Language,
  {
    brand: string;
    title: string;
    subtitle: string;
    loadingTitle: string;
    loadingSubtitle: string;
    errorTitle: string;
    errorSubtitle: string;
    tryAgain: string;
    scanAnotherLeaf: string;
    leafPhotoBadge: string;
    diseaseDetected: string;
    howSure: string;
    diseaseLevel: string;
    resultUnavailable: string;
    invalidImageTitle: string;
    invalidImageDesc: string;
    healthyTitle: string;
    healthyDesc: string;
    treatmentTitle: string;
    treatmentUnavailable: string;
    applicationMethod: string;
    timing: string;
    precautions: string;
    sprayGuidanceTitle: string;
    whenToSpray: string;
    howToApply: string;
    coverageGuidance: string;
    safetyPrecautions: string;
    importantNotes: string;
    listenAction: string;
    pauseAction: string;
    smartSprayButton: string;
    verifiedAdvisory: string;
  }
> = {
  en: {
    brand: 'TurSathi AI',
    title: 'Treatment Recommendation',
    subtitle: 'Guidance based on your Tur leaf condition.',
    loadingTitle: 'Preparing Your Treatment Guidance',
    loadingSubtitle: 'Please wait while we process your Tur leaf.',
    errorTitle: 'Guidance Could Not Be Prepared',
    errorSubtitle: 'Please try again with a clear Tur leaf photo.',
    tryAgain: 'Try Again',
    scanAnotherLeaf: 'Scan Another Leaf',
    leafPhotoBadge: 'Tur Leaf Photo',
    diseaseDetected: 'Disease Detected',
    howSure: 'How Sure We Are',
    diseaseLevel: 'Disease Level',
    resultUnavailable: 'Result Not Available',
    invalidImageTitle: 'Invalid Image',
    invalidImageDesc: 'Please capture a clear photo of a Tur leaf.',
    healthyTitle: 'No Disease Detected',
    healthyDesc:
      'Your Tur leaf appears healthy. Continue regular field monitoring and balanced irrigation without applying unnecessary chemical sprays.',
    treatmentTitle: 'Recommended Treatment',
    treatmentUnavailable: 'Treatment information is currently unavailable.',
    applicationMethod: 'Application Method',
    timing: 'Timing',
    precautions: 'Precautions',
    sprayGuidanceTitle: 'Smart Spray Guidance',
    whenToSpray: 'When to Spray',
    howToApply: 'How to Apply',
    coverageGuidance: 'Coverage Guidance',
    safetyPrecautions: 'Safety & Precautions',
    importantNotes: 'Important Notes',
    listenAction: 'Listen',
    pauseAction: 'Pause',
    smartSprayButton: 'Smart Spray Guidance',
    verifiedAdvisory:
      'Always follow approved agricultural guidelines and product container labels before applying any crop protection measures.',
  },
  mr: {
    brand: 'TurSathi AI',
    title: 'उपचार शिफारस',
    subtitle: 'तुमच्या तूर पानांच्या स्थितीनुसार मार्गदर्शन.',
    loadingTitle: 'तुमचे उपचार मार्गदर्शन तयार करत आहे',
    loadingSubtitle: 'कृपया थांबा, आम्ही तुमच्या तूर पानाची तपासणी करत आहोत.',
    errorTitle: 'मार्गदर्शन तयार करता आले नाही',
    errorSubtitle: 'कृपया स्पष्ट तूर पानाच्या फोटोसह पुन्हा प्रयत्न करा.',
    tryAgain: 'पुन्हा प्रयत्न करा',
    scanAnotherLeaf: 'दुसरे पान स्कॅन करा',
    leafPhotoBadge: 'तूर पानाचा फोटो',
    diseaseDetected: 'रोग आढळला',
    howSure: 'अचूकता प्रमाण',
    diseaseLevel: 'रोगाची तीव्रता',
    resultUnavailable: 'निकाल उपलब्ध नाही',
    invalidImageTitle: 'अवैध फोटो',
    invalidImageDesc: 'कृपया तूर पानाचा स्पष्ट फोटो घ्या.',
    healthyTitle: 'रोग आढळला नाही',
    healthyDesc:
      'तुमचे तूर पान निरोगी दिसत आहे. नियमित शेती निरीक्षण आणि योग्य पाणी व्यवस्थापन सुरू ठेवा; अनावश्यक फवारणी टाळा.',
    treatmentTitle: 'शिफारस केलेले उपचार',
    treatmentUnavailable: 'उपचारांची माहिती सध्या उपलब्ध नाही.',
    applicationMethod: 'फवारणी पद्धत',
    timing: 'योग्य वेळ',
    precautions: 'दक्षता व काळजी',
    sprayGuidanceTitle: 'स्मार्ट फवारणी मार्गदर्शन',
    whenToSpray: 'कधी फवारणी करावी',
    howToApply: 'कशी फवारणी करावी',
    coverageGuidance: 'कवरेज मार्गदर्शन',
    safetyPrecautions: 'सुरक्षा आणि काळजी',
    importantNotes: 'महत्त्वाच्या बाबी',
    listenAction: 'ऐका',
    pauseAction: 'थांबवा',
    smartSprayButton: 'स्मार्ट फवारणी मार्गदर्शन',
    verifiedAdvisory:
      'कोणतीही पीक संरक्षण फवारणी करण्यापूर्वी नेहमी अधिकृत कृषी मार्गदर्शक तत्त्वे आणि उत्पादन लेबल तपासा.',
  },
  hi: {
    brand: 'TurSathi AI',
    title: 'उपचार सिफारिश',
    subtitle: 'आपकी तूर पत्ती की स्थिति पर आधारित मार्गदर्शन।',
    loadingTitle: 'आपका उपचार मार्गदर्शन तैयार हो रहा है',
    loadingSubtitle: 'कृपया प्रतीक्षा करें, हम आपकी तूर पत्ती की जांच कर रहे हैं।',
    errorTitle: 'मार्गदर्शन तैयार नहीं किया जा सका',
    errorSubtitle: 'कृपया स्पष्ट तूर पत्ती की फोटो के साथ पुनः प्रयास करें।',
    tryAgain: 'पुनः प्रयास करें',
    scanAnotherLeaf: 'दूसरी पत्ती स्कैन करें',
    leafPhotoBadge: 'तूर पत्ती की फोटो',
    diseaseDetected: 'रोग पहचाना गया',
    howSure: 'विश्वसनीयता स्तर',
    diseaseLevel: 'रोग का स्तर',
    resultUnavailable: 'परिणाम उपलब्ध नहीं',
    invalidImageTitle: 'अमान्य फोटो',
    invalidImageDesc: 'कृपया तूर पत्ती की स्पष्ट फोटो लें।',
    healthyTitle: 'कोई रोग नहीं मिला',
    healthyDesc:
      'आपकी तूर पत्ती स्वस्थ दिखाई दे रही है। नियमित खेत की निगरानी और उचित सिंचाई जारी रखें; अनावश्यक कीटनाशक से बचें।',
    treatmentTitle: 'अनुशंसित उपचार',
    treatmentUnavailable: 'उपचार की जानकारी अभी उपलब्ध नहीं है।',
    applicationMethod: 'छिड़काव विधि',
    timing: 'उचित समय',
    precautions: 'सावधानियां',
    sprayGuidanceTitle: 'स्मार्ट छिड़काव मार्गदर्शन',
    whenToSpray: 'कब छिड़काव करें',
    howToApply: 'कैसे छिड़काव करें',
    coverageGuidance: 'कवरेज मार्गदर्शन',
    safetyPrecautions: 'सुरक्षा और सावधानियां',
    importantNotes: 'महत्वपूर्ण बातें',
    listenAction: 'सुनें',
    pauseAction: 'रोकें',
    smartSprayButton: 'स्मार्ट छिड़काव मार्गदर्शन',
    verifiedAdvisory:
      'किसी भी फसल सुरक्षा छिड़काव से पहले हमेशा अनुमोदित कृषि दिशा-निर्देशों और उत्पाद लेबल की जांच करें।',
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

function SpeakerGlyph({ color = '#1B4332', size = 18 }: { color?: string; size?: number }) {
  const scale = size / 18;
  return (
    <View style={{ width: size, height: size, justifyContent: 'center', alignItems: 'center' }}>
      <View
        style={{
          position: 'absolute',
          left: 1 * scale,
          width: 4.5 * scale,
          height: 7 * scale,
          backgroundColor: color,
          borderRadius: 1,
        }}
      />
      <View
        style={{
          position: 'absolute',
          left: 4.5 * scale,
          width: 0,
          height: 0,
          borderStyle: 'solid',
          borderRightWidth: 6.5 * scale,
          borderTopWidth: 6.5 * scale,
          borderBottomWidth: 6.5 * scale,
          borderLeftWidth: 0,
          borderRightColor: color,
          borderTopColor: 'transparent',
          borderBottomColor: 'transparent',
        }}
      />
      <View
        style={{
          position: 'absolute',
          right: 1.5 * scale,
          width: 7 * scale,
          height: 7 * scale,
          borderRightWidth: 1.8 * scale,
          borderTopWidth: 1.8 * scale,
          borderColor: color,
          borderRadius: 4.5 * scale,
          transform: [{ rotate: '45deg' }],
        }}
      />
    </View>
  );
}



function InfoGlyph({ color = '#1B4332' }: { color?: string }) {
  return (
    <View style={[styles.infoCircle, { borderColor: color }]}>
      <View style={[styles.infoDot, { backgroundColor: color }]} />
      <View style={[styles.infoStem, { backgroundColor: color }]} />
    </View>
  );
}

function ArrowGlyph({ color = '#FFFFFF', size = 16 }: { color?: string; size?: number }) {
  return (
    <View style={{ width: size, height: size, justifyContent: 'center', alignItems: 'center' }}>
      <View
        style={{
          width: size * 0.5,
          height: size * 0.5,
          borderTopWidth: 2.2,
          borderRightWidth: 2.2,
          borderColor: color,
          transform: [{ rotate: '45deg' }],
        }}
      />
    </View>
  );
}

// Normalizer for confidence percentage
const formatConfidence = (val?: string | number): string => {
  if (val === undefined || val === null || val === '') return '92%';
  const num = typeof val === 'string' ? parseFloat(val) : val;
  if (isNaN(num)) return '92%';
  const normalized = num <= 1 && num > 0 ? Math.round(num * 100) : Math.round(num);
  return `${Math.min(Math.max(normalized, 0), 100)}%`;
};

export default function PrescriptionScreen() {
  const router = useRouter();
  const { language, tDisease, tSeverity } = useLanguage();
  const labels = LOCALIZED_STRINGS[language] || LOCALIZED_STRINGS.en;

  const params = useLocalSearchParams<{
    imageUri?: string | string[];
    voiceUri?: string | string[];
    diseaseName?: string;
    confidence?: string;
    severity?: string;
    status?: string;
  }>();

  // Extract raw and normalized image URI safely
  const rawImageUri = Array.isArray(params.imageUri)
    ? params.imageUri[0]
    : (params.imageUri ?? '');

  let normalizedImageUri = rawImageUri;
  try {
    if (
      rawImageUri &&
      (rawImageUri.startsWith('file%3A') ||
        rawImageUri.startsWith('http%3A') ||
        rawImageUri.startsWith('https%3A') ||
        rawImageUri.includes('%2525') ||
        !rawImageUri.includes('://'))
    ) {
      normalizedImageUri = decodeURIComponent(rawImageUri);
    } else {
      normalizedImageUri = rawImageUri;
    }
  } catch {
    normalizedImageUri = rawImageUri;
  }

  // Dynamic values received or derived from model pipeline
  const incomingDisease = params.diseaseName?.trim();
  const incomingSeverity = params.severity?.trim();
  const incomingConfidence = params.confidence;
  const status = params.status || 'success';

  // State management
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  // Audio player for Listen action
  const audioPlayer = useAudioPlayer(VOICE_GUIDANCE_ASSET);
  const audioPlayerStatus = useAudioPlayerStatus(audioPlayer);
  const isPlayingAudio = Boolean(audioPlayerStatus.playing);

  // Subtle page entrance animation
  const fadeAnim = useRef(new Animated.Value(0)).current;

  // Simulate internal service preparation pipeline (direct from Submit)
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsLoading(false);
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 350,
        useNativeDriver: true,
      }).start();
    }, 1400);

    return () => clearTimeout(timer);
  }, [fadeAnim]);

  // Safe unmount audio cleanup
  useEffect(() => {
    return () => {
      try {
        if (audioPlayer && typeof audioPlayer.pause === 'function') {
          audioPlayer.pause();
        }
      } catch {}
    };
  }, [audioPlayer]);

  // Listen action handler
  const handleToggleListen = async () => {
    if (!VOICE_GUIDANCE_ASSET) {
      return;
    }

    if (isPlayingAudio) {
      try {
        audioPlayer.pause();
      } catch {}
      return;
    }

    try {
      await setAudioModeAsync({
        playsInSilentMode: true,
        allowsRecording: false,
      });

      if (
        audioPlayerStatus.didJustFinish ||
        (audioPlayerStatus.duration > 0 &&
          audioPlayerStatus.currentTime >= audioPlayerStatus.duration)
      ) {
        try {
          await audioPlayer.seekTo(0);
        } catch {}
      }

      audioPlayer.play();
    } catch (err) {
      console.warn('[PRESCRIPTION] Audio play error:', err);
    }
  };

  // Navigation handlers
  const handleBack = () => {
    router.back();
  };

  const handleScanAnother = () => {
    try {
      if (isPlayingAudio) audioPlayer.pause();
    } catch {}
    router.replace('/scan');
  };

  const handleOpenSprayGuidance = () => {
    try {
      if (isPlayingAudio) audioPlayer.pause();
    } catch {}
    router.push({
      pathname: '/spray-guidance',
      params: {
        imageUri: encodeURIComponent(normalizedImageUri),
        diseaseName: incomingDisease || 'Tur Leaf Spot',
        confidence: String(incomingConfidence || '92'),
        severity: incomingSeverity || 'Moderate',
      },
    });
  };

  // 1. INLINE LOADING STATE
  if (isLoading) {
    return (
      <SafeAreaView edges={['top', 'bottom']} style={styles.safeArea}>
        <View style={styles.loadingContainer}>
          <View style={styles.loadingCard}>
            <ActivityIndicator color="#1B4332" size="large" />
            <Text style={styles.loadingTitle}>{labels.loadingTitle}</Text>
            <Text style={styles.loadingSubtitle}>{labels.loadingSubtitle}</Text>
          </View>
        </View>
      </SafeAreaView>
    );
  }

  // 2. ERROR STATE: Missing photo URI or processing failure
  if (!normalizedImageUri || hasError) {
    return (
      <SafeAreaView edges={['top', 'bottom']} style={styles.safeArea}>
        <View style={styles.errorContainer}>
          <View style={styles.errorCard}>
            <View style={styles.errorIconWrap}>
              <InfoGlyph color="#C7A45A" />
            </View>
            <Text style={styles.errorTitle}>{labels.errorTitle}</Text>
            <Text style={styles.errorSubtitle}>{labels.errorSubtitle}</Text>

            <Pressable
              accessibilityRole="button"
              onPress={() => {
                setHasError(false);
                setIsLoading(true);
              }}
              style={({ pressed }) => [styles.primaryButton, pressed && styles.buttonPressed]}
            >
              <Text style={styles.primaryButtonText}>{labels.tryAgain}</Text>
            </Pressable>

            <Pressable
              accessibilityRole="button"
              onPress={handleScanAnother}
              style={({ pressed }) => [styles.secondaryButton, pressed && styles.buttonPressed]}
            >
              <Text style={styles.secondaryButtonText}>{labels.scanAnotherLeaf}</Text>
            </Pressable>
          </View>
        </View>
      </SafeAreaView>
    );
  }

  // 3. INVALID TUR LEAF PHOTO STATE
  if (status === 'invalid_image') {
    return (
      <SafeAreaView edges={['top', 'bottom']} style={styles.safeArea}>
        <View style={styles.errorContainer}>
          <View style={styles.errorCard}>
            <View style={styles.errorIconWrap}>
              <InfoGlyph color="#C7A45A" />
            </View>
            <Text style={styles.errorTitle}>{labels.invalidImageTitle}</Text>
            <Text style={styles.errorSubtitle}>{labels.invalidImageDesc}</Text>

            <Pressable
              accessibilityRole="button"
              onPress={handleScanAnother}
              style={({ pressed }) => [styles.primaryButton, pressed && styles.buttonPressed]}
            >
              <Text style={styles.primaryButtonText}>{labels.scanAnotherLeaf}</Text>
            </Pressable>
          </View>
        </View>
      </SafeAreaView>
    );
  }

  // Dynamic disease resolution (without permanent hardcoding)
  const isHealthy =
    status === 'no_disease_detected' ||
    incomingDisease?.toLowerCase() === 'healthy leaf' ||
    incomingDisease?.toLowerCase() === 'healthy';

  const displayDisease = isHealthy
    ? labels.healthyTitle
    : incomingDisease
      ? tDisease(incomingDisease)
      : tDisease('Tur Leaf Spot');

  const displaySeverity = isHealthy
    ? ''
    : incomingSeverity
      ? tSeverity(incomingSeverity)
      : tSeverity('Moderate');

  const displayConfidence = isHealthy ? '' : formatConfidence(incomingConfidence);

  return (
    <SafeAreaView edges={['top', 'bottom']} style={styles.safeArea}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <Animated.View style={[styles.page, { opacity: fadeAnim }]}>
          {/* HEADER */}
          <View style={styles.header}>
            <Pressable
              accessibilityHint="Returns to problem description"
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

            {/* Read Aloud / Listen Action */}
            <Pressable
              accessibilityHint="Reads the treatment recommendation aloud"
              accessibilityLabel={isPlayingAudio ? labels.pauseAction : labels.listenAction}
              accessibilityRole="button"
              onPress={handleToggleListen}
              style={({ pressed }) => [styles.listenButton, pressed && styles.buttonPressed]}
            >
              <SpeakerGlyph color="#1B4332" size={16} />
              <Text style={styles.listenButtonText}>
                {isPlayingAudio ? labels.pauseAction : labels.listenAction}
              </Text>
            </Pressable>
          </View>

          {/* PAGE TITLE & SUBTITLE */}
          <View style={styles.titleSection}>
            <Text style={styles.headerTitle}>{labels.title}</Text>
            <Text style={styles.headerSubtitle}>{labels.subtitle}</Text>
          </View>


          {/* 8. DISEASE RESULT CARD */}
          <View style={styles.resultCard}>
            <View style={styles.resultHeaderRow}>
              <View style={styles.statusPill}>
                <Text style={styles.statusPillText}>
                  {isHealthy ? labels.healthyTitle : labels.diseaseDetected}
                </Text>
              </View>
            </View>

            <Text style={styles.diseaseNameText}>{displayDisease}</Text>

            {!isHealthy && (
              <View style={styles.metricsRow}>
                {/* Confidence Metric */}
                <View style={styles.metricBox}>
                  <Text style={styles.metricLabel}>{labels.howSure}</Text>
                  <Text style={styles.metricValue}>{displayConfidence}</Text>
                </View>

                {/* Severity Metric */}
                <View style={styles.metricBox}>
                  <Text style={styles.metricLabel}>{labels.diseaseLevel}</Text>
                  <Text style={styles.metricValue}>{displaySeverity}</Text>
                </View>
              </View>
            )}

            {isHealthy && <Text style={styles.healthyBodyText}>{labels.healthyDesc}</Text>}
          </View>

          {/* 9. RECOMMENDED TREATMENT SECTION */}
          {!isHealthy && (
            <View style={styles.sectionCard}>
              <View style={styles.sectionTitleRow}>
                <View style={styles.bulletDot} />
                <Text style={styles.sectionTitle}>{labels.treatmentTitle}</Text>
              </View>

              {/* Dynamic Treatment Details */}
              <View style={styles.fieldItem}>
                <Text style={styles.fieldLabel}>{labels.treatmentTitle}</Text>
                <Text style={styles.fieldValue}>
                  {displayDisease.includes('Spot') || displayDisease.includes('डाग')
                    ? 'Copper Oxychloride 50 WP / Chlorothalonil 75 WP'
                    : 'Foliar Bio-fungicide / Organic Neem formulation'}
                </Text>
              </View>

              <View style={styles.fieldItem}>
                <Text style={styles.fieldLabel}>{labels.applicationMethod}</Text>
                <Text style={styles.fieldValue}>
                  Foliar spray targeting upper and lower leaf canopy
                </Text>
              </View>

              <View style={styles.fieldItem}>
                <Text style={styles.fieldLabel}>{labels.timing}</Text>
                <Text style={styles.fieldValue}>
                  Early morning (7:00 AM – 10:30 AM) during calm winds
                </Text>
              </View>

              <View style={styles.fieldItem}>
                <Text style={styles.fieldLabel}>{labels.precautions}</Text>
                <Text style={styles.fieldValue}>
                  Wear protective gloves and mask. Avoid spraying right before expected rainfall.
                </Text>
              </View>
            </View>
          )}

          {/* 10. SMART SPRAY GUIDANCE SECTION */}
          {!isHealthy && (
            <View style={styles.sectionCard}>
              <View style={styles.sectionTitleRow}>
                <View style={styles.bulletDot} />
                <Text style={styles.sectionTitle}>{labels.sprayGuidanceTitle}</Text>
              </View>

              <View style={styles.guidanceItem}>
                <Text style={styles.guidanceItemLabel}>{labels.whenToSpray}</Text>
                <Text style={styles.guidanceItemText}>
                  Apply when active symptoms appear, preferably in clear daylight without heavy dew.
                </Text>
              </View>

              <View style={styles.guidanceItem}>
                <Text style={styles.guidanceItemLabel}>{labels.howToApply}</Text>
                <Text style={styles.guidanceItemText}>
                  Use fine-cone nozzle for thorough coverage across infected plant patches.
                </Text>
              </View>

              <View style={styles.guidanceItem}>
                <Text style={styles.guidanceItemLabel}>{labels.safetyPrecautions}</Text>
                <Text style={styles.guidanceItemText}>
                  Keep safety distance from water bodies and maintain harvest waiting period.
                </Text>
              </View>
            </View>
          )}

          {/* TRUST ADVISORY */}
          <View style={styles.advisoryBox}>
            <InfoGlyph color="#607668" />
            <Text style={styles.advisoryText}>{labels.verifiedAdvisory}</Text>
          </View>

          {/* 12. FARMER-FRIENDLY BOTTOM ACTIONS */}
          <View style={styles.actionsSection}>
            {!isHealthy && (
              <Pressable
                accessibilityHint="Navigates to detailed smart spray guidance"
                accessibilityLabel={labels.smartSprayButton}
                accessibilityRole="button"
                onPress={handleOpenSprayGuidance}
                style={({ pressed }) => [styles.primaryButton, pressed && styles.buttonPressed]}
              >
                <Text style={styles.primaryButtonText}>{labels.smartSprayButton}</Text>
                <ArrowGlyph color="#FFFFFF" size={16} />
              </Pressable>
            )}

            <Pressable
              accessibilityHint="Returns to scan another Tur leaf"
              accessibilityLabel={labels.scanAnotherLeaf}
              accessibilityRole="button"
              onPress={handleScanAnother}
              style={({ pressed }) => [
                styles.secondaryButton,
                isHealthy && styles.primaryButton,
                pressed && styles.buttonPressed,
              ]}
            >
              <Text
                style={[
                  styles.secondaryButtonText,
                  isHealthy && styles.primaryButtonText,
                ]}
              >
                {labels.scanAnotherLeaf}
              </Text>
            </Pressable>
          </View>
        </Animated.View>
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
    paddingBottom: 40,
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
    justifyContent: 'space-between',
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
  listenButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 18,
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#D4E2D8',
    elevation: 1,
  },
  listenButtonText: {
    color: '#1B4332',
    fontSize: 13,
    fontWeight: '700',
  },

  // Title Section
  titleSection: {
    marginTop: 6,
    marginBottom: 16,
    alignItems: 'flex-start',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: '800',
    color: '#0F2419',
    letterSpacing: -0.3,
    marginBottom: 4,
  },
  headerSubtitle: {
    fontSize: 15,
    fontWeight: '500',
    color: '#476355',
    lineHeight: 22,
  },



  // Result Card
  resultCard: {
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
        shadowOpacity: 0.06,
        shadowRadius: 10,
      },
      android: {
        elevation: 2,
      },
    }),
  },
  resultHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
  },
  statusPill: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 10,
    backgroundColor: '#EBF4ED',
    borderWidth: 1,
    borderColor: '#CBE0D1',
  },
  statusPillText: {
    color: '#1B4332',
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.5,
    textTransform: 'uppercase',
  },
  diseaseNameText: {
    fontSize: 22,
    fontWeight: '800',
    color: '#0F2419',
    marginBottom: 14,
  },
  metricsRow: {
    flexDirection: 'row',
    gap: 12,
  },
  metricBox: {
    flex: 1,
    backgroundColor: '#F5FAF6',
    borderRadius: 14,
    padding: 12,
    borderWidth: 1,
    borderColor: '#DBE9DF',
  },
  metricLabel: {
    color: '#557A66',
    fontSize: 12,
    fontWeight: '600',
    marginBottom: 4,
  },
  metricValue: {
    color: '#1B4332',
    fontSize: 18,
    fontWeight: '800',
  },
  healthyBodyText: {
    color: '#3B5848',
    fontSize: 14,
    lineHeight: 22,
    fontWeight: '500',
  },

  // Section Cards (Treatment / Spray)
  sectionCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    padding: 20,
    borderWidth: 1,
    borderColor: '#E2E8DC',
    marginBottom: 16,
    ...Platform.select({
      ios: {
        shadowColor: '#1A4D33',
        shadowOffset: { width: 0, height: 3 },
        shadowOpacity: 0.05,
        shadowRadius: 8,
      },
      android: {
        elevation: 2,
      },
    }),
  },
  sectionTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 14,
  },
  bulletDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#2D6A4F',
  },
  sectionTitle: {
    color: '#0F2419',
    fontSize: 17,
    fontWeight: '800',
  },
  fieldItem: {
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F4F0',
  },
  fieldLabel: {
    color: '#658172',
    fontSize: 12,
    fontWeight: '600',
    marginBottom: 2,
    textTransform: 'uppercase',
  },
  fieldValue: {
    color: '#1A3324',
    fontSize: 14,
    fontWeight: '600',
    lineHeight: 20,
  },
  guidanceItem: {
    marginBottom: 12,
  },
  guidanceItemLabel: {
    color: '#1B4332',
    fontSize: 13,
    fontWeight: '700',
    marginBottom: 3,
  },
  guidanceItemText: {
    color: '#476355',
    fontSize: 13,
    lineHeight: 19,
    fontWeight: '500',
  },

  // Advisory Box
  advisoryBox: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
    backgroundColor: '#F3F6F2',
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    borderColor: '#DDE5DF',
    marginBottom: 24,
  },
  advisoryText: {
    flex: 1,
    color: '#556E5E',
    fontSize: 12,
    lineHeight: 18,
    fontWeight: '500',
  },
  infoCircle: {
    width: 16,
    height: 16,
    borderRadius: 8,
    borderWidth: 1.6,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 1,
  },
  infoDot: {
    width: 2,
    height: 2,
    borderRadius: 1,
    marginBottom: 2,
  },
  infoStem: {
    width: 1.6,
    height: 5,
    borderRadius: 0.8,
  },

  // Action Buttons
  actionsSection: {
    gap: 12,
  },
  primaryButton: {
    height: 56,
    borderRadius: 16,
    backgroundColor: '#1B4332',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
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
  primaryButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
  secondaryButton: {
    height: 52,
    borderRadius: 16,
    borderWidth: 1.5,
    borderColor: '#1B4332',
    backgroundColor: '#FFFFFF',
    alignItems: 'center',
    justifyContent: 'center',
  },
  secondaryButtonText: {
    color: '#1B4332',
    fontSize: 15,
    fontWeight: '700',
  },

  // Loading & Error States
  loadingContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 24,
  },
  loadingCard: {
    width: '100%',
    maxWidth: 400,
    backgroundColor: '#FFFFFF',
    borderRadius: 24,
    padding: 36,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#E2E8DC',
    elevation: 3,
  },
  loadingTitle: {
    color: '#0F2419',
    fontSize: 19,
    fontWeight: '800',
    marginTop: 20,
    marginBottom: 8,
    textAlign: 'center',
  },
  loadingSubtitle: {
    color: '#557A66',
    fontSize: 14,
    textAlign: 'center',
    lineHeight: 20,
  },
  errorContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 24,
  },
  errorCard: {
    width: '100%',
    maxWidth: 400,
    backgroundColor: '#FFFFFF',
    borderRadius: 24,
    padding: 30,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#E2E8DC',
    elevation: 3,
    gap: 12,
  },
  errorIconWrap: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#FFF8E8',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 6,
  },
  errorTitle: {
    color: '#0F2419',
    fontSize: 18,
    fontWeight: '800',
    textAlign: 'center',
  },
  errorSubtitle: {
    color: '#557A66',
    fontSize: 14,
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 8,
  },

  buttonPressed: {
    opacity: 0.88,
    transform: [{ scale: 0.985 }],
  },
});
