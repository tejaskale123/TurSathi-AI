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
import { getAuthToken } from '../config/tokenStore';
import { fetchAIGuidance, ClaudeGuidanceResponse } from '../config/recommendationApi';
import { getLocalizedRecommendation } from '../i18n/recommendationContent';

// Pre-bundled instructional voice audio asset for read-aloud / guidance
let VOICE_GUIDANCE_ASSET: number | null = null;
try {
  VOICE_GUIDANCE_ASSET = require('../../assets/audio/tur_leaf_scan_guide.mp3');
} catch {
  VOICE_GUIDANCE_ASSET = null;
}

// ============================================================================
// LOCALIZED STRINGS (English, Marathi, Hindi)
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
    detectedProblem: string;
    detectionConfidence: string;
    whatDoesThisMean: string;
    recommendedTreatment: string;
    treatmentUnavailable: string;
    sprayGuidanceUnavailable: string;
    applicationDetails: string;
    recommendedQuantity: string;
    waterRequired: string;
    perPump: string;
    sprayTiming: string;
    importantTitle: string;
    importantNotice: string;
    viewSprayGuidance: string;
    listenAction: string;
    pauseAction: string;
    healthyTitle: string;
    healthyDesc: string;
    invalidImageTitle: string;
    invalidImageDesc: string;
    recordedObservationTitle: string;
  }
> = {
  en: {
    brand: 'TurSathi AI',
    title: 'Treatment Recommendation',
    subtitle: 'Recommended treatment based on your Tur leaf analysis',
    loadingTitle: 'Preparing Your Treatment Recommendation',
    loadingSubtitle: 'Please wait while we process your Tur leaf analysis.',
    errorTitle: 'Recommendation Could Not Be Prepared',
    errorSubtitle: 'Please try again with a clear Tur leaf photo.',
    tryAgain: 'Try Again',
    scanAnotherLeaf: 'Scan Another Leaf',
    detectedProblem: 'Diagnosis',
    detectionConfidence: 'Confidence',
    whatDoesThisMean: 'What does this mean?',
    recommendedTreatment: 'Treatment Guidance',
    treatmentUnavailable: 'Verified treatment information is currently unavailable for this disease.',
    sprayGuidanceUnavailable: 'Verified spray guidance is currently unavailable for this disease.',
    applicationDetails: 'Application Details',
    recommendedQuantity: 'Recommended Quantity',
    waterRequired: 'Water Required',
    perPump: 'Per Pump',
    sprayTiming: 'Spray Timing',
    importantTitle: 'Important',
    importantNotice:
      'Please consult a qualified agricultural expert before applying any pesticide.',
    viewSprayGuidance: 'View Spray Guidance',
    listenAction: 'Listen',
    pauseAction: 'Pause',
    healthyTitle: 'No Disease Detected',
    healthyDesc:
      'Your Tur leaf appears healthy. Continue regular field monitoring and balanced irrigation without applying unnecessary chemical sprays.',
    invalidImageTitle: 'Invalid Image',
    invalidImageDesc: 'Please capture a clear photo of a Tur leaf.',
    recordedObservationTitle: 'Your Recorded Observation',
  },
  mr: {
    brand: 'TurSathi AI',
    title: 'उपचार शिफारस',
    subtitle: 'तुमच्या तूर पानांच्या विश्लेषणावर आधारित शिफारस केलेले उपचार',
    loadingTitle: 'तुमची उपचार शिफारस तयार करत आहे',
    loadingSubtitle: 'कृपया थांबा, आम्ही तुमच्या तूर पानाचे विश्लेषण करत आहोत.',
    errorTitle: 'शिफारस तयार करता आली नाही',
    errorSubtitle: 'कृपया स्पष्ट तूर पानाच्या फोटोसह पुन्हा प्रयत्न करा.',
    tryAgain: 'पुन्हा प्रयत्न करा',
    scanAnotherLeaf: 'दुसरे पान स्कॅन करा',
    detectedProblem: 'निदान',
    detectionConfidence: 'खात्री (Confidence)',
    whatDoesThisMean: 'याचा अर्थ काय आहे?',
    recommendedTreatment: 'उपचार मार्गदर्शन',
    treatmentUnavailable: 'या आजारासाठी प्रमाणित उपचारांची माहिती सध्या उपलब्ध नाही.',
    sprayGuidanceUnavailable: 'या आजारासाठी प्रमाणित फवारणी मार्गदर्शन सध्या उपलब्ध नाही.',
    applicationDetails: 'वापर व फवारणी तपशील',
    recommendedQuantity: 'शिफारस केलेले प्रमाण',
    waterRequired: 'आवश्यक पाणी',
    perPump: 'प्रति पंप प्रमाण',
    sprayTiming: 'फवारणीची वेळ',
    importantTitle: 'महत्त्वाचे',
    importantNotice:
      'कोणतेही कीटकनाशक फवारण्यापूर्वी कृपया पात्र कृषी तज्ज्ञांचा सल्ला घ्या.',
    viewSprayGuidance: 'फवारणी मार्गदर्शन पहा',
    listenAction: 'ऐका',
    pauseAction: 'थांबवा',
    healthyTitle: 'रोग आढळला नाही',
    healthyDesc:
      'तुमचे तूर पान निरोगी दिसत आहे. नियमित शेती निरीक्षण आणि योग्य पाणी व्यवस्थापन सुरू ठेवा; अनावश्यक फवारणी टाळा.',
    invalidImageTitle: 'अवैध फोटो',
    invalidImageDesc: 'कृपया तूर पानाचा स्पष्ट फोटो घ्या.',
    recordedObservationTitle: 'तुम्ही नोंदवलेली समस्या',
  },
  hi: {
    brand: 'TurSathi AI',
    title: 'उपचार सिफारिश',
    subtitle: 'आपकी तूर पत्ती के विश्लेषण पर आधारित अनुशंसित उपचार',
    loadingTitle: 'आपकी उपचार सिफारिश तैयार हो रही है',
    loadingSubtitle: 'कृपया प्रतीक्षा करें, हम आपकी तूर पत्ती का विश्लेषण कर रहे हैं।',
    errorTitle: 'सिफारिश तैयार नहीं की जा सकी',
    errorSubtitle: 'कृपया स्पष्ट तूर पत्ती की फोटो के साथ पुनः प्रयास करें।',
    tryAgain: 'पुनः प्रयास करें',
    scanAnotherLeaf: 'दूसरी पत्ती स्कैन करें',
    detectedProblem: 'निदान',
    detectionConfidence: 'निश्चितता (Confidence)',
    whatDoesThisMean: 'इसका क्या अर्थ है?',
    recommendedTreatment: 'उपचार मार्गदर्शन',
    treatmentUnavailable: 'इस बीमारी के लिए सत्यापित उपचार जानकारी वर्तमान में उपलब्ध नहीं है।',
    sprayGuidanceUnavailable: 'इस बीमारी के लिए सत्यापित छिड़काव मार्गदर्शन वर्तमान में उपलब्ध नहीं है।',
    applicationDetails: 'उपयोग एवं विवरण',
    recommendedQuantity: 'अनुशंसित मात्रा',
    waterRequired: 'आवश्यक पाणी',
    perPump: 'प्रति पंप मात्रा',
    sprayTiming: 'छिड़काव का समय',
    importantTitle: 'महत्वपूर्ण',
    importantNotice:
      'किसी भी कीटनाशक का उपयोग करने से पहले कृपया एक योग्य कृषि विशेषज्ञ से परामर्श लें।',
    viewSprayGuidance: 'छिड़काव मार्गदर्शन देखें',
    listenAction: 'सुनें',
    pauseAction: 'रोकें',
    healthyTitle: 'कोई रोग नहीं मिला',
    healthyDesc:
      'आपकी तूर पत्ती स्वस्थ दिखाई दे रही है। नियमित खेत की निगरानी और उचित सिंचाई जारी रखें; अनावश्यक कीटनाशक से बचें।',
    invalidImageTitle: 'अमान्य फोटो',
    invalidImageDesc: 'कृपया तूर पत्ती की स्पष्ट फोटो लें।',
    recordedObservationTitle: 'आपकी दर्ज की गई समस्या',
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
  if (val === undefined || val === null || val === '') return '';
  const num = typeof val === 'string' ? parseFloat(val) : val;
  if (isNaN(num)) return '';
  const normalized = num <= 1 && num > 0 ? Math.round(num * 100) : Math.round(num);
  return `${Math.min(Math.max(normalized, 0), 100)}%`;
};

export default function PrescriptionScreen() {
  const router = useRouter();
  const { language, tDisease } = useLanguage();
  const labels = LOCALIZED_STRINGS[language] || LOCALIZED_STRINGS.en;

  const params = useLocalSearchParams<{
    imageUri?: string | string[];
    voiceUri?: string | string[];
    transcription?: string | string[];
    scanId?: string | string[];
    disease_name?: string;
    confidence?: string;
    severity?: string;
    status?: string;
    crop?: string;
  }>();

  // Extract and normalize transcription safely
  const rawTranscription = Array.isArray(params.transcription)
    ? params.transcription[0]
    : params.transcription;

  let normalizedTranscription = '';
  if (rawTranscription && typeof rawTranscription === 'string') {
    try {
      normalizedTranscription = rawTranscription.includes('%')
        ? decodeURIComponent(rawTranscription)
        : rawTranscription;
    } catch {
      normalizedTranscription = rawTranscription;
    }
    normalizedTranscription = normalizedTranscription.trim();
  }

  // Extract crop and capitalize
  const rawCrop = params.crop ? (Array.isArray(params.crop) ? params.crop[0] : params.crop) : 'Tur';
  const cropName = rawCrop.charAt(0).toUpperCase() + rawCrop.slice(1);

  // Helper to replace hardcoded crop names in localized strings
  const formatCrop = (text: string) => {
    if (!text) return text;
    return text.replace(/Tur/g, cropName).replace(/तूर/g, cropName);
  };

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

  // Dynamic values received from ML/backend parameters
  const incomingDisease = params.disease_name?.trim();
  const incomingConfidence = params.confidence;
  const status = params.status || 'completed';
  const scanId = params.scanId ? (Array.isArray(params.scanId) ? params.scanId[0] : params.scanId) : undefined;

  // State management
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(
    (status !== 'completed' && status !== 'success' && status !== 'invalid_image') || 
    (!incomingDisease && status !== 'invalid_image')
  );
  const [treatmentData, setTreatmentData] = useState<ClaudeGuidanceResponse | null>(null);

  // Load treatment guidance from API
  useEffect(() => {
    async function loadTreatment() {
      if (!scanId || !incomingDisease || incomingDisease.toLowerCase() === 'healthy' || incomingDisease.toLowerCase() === 'healthy leaf') {
        setIsLoading(false);
        return;
      }
      try {
        const token = await getAuthToken();
        const res = await fetchAIGuidance(Number(scanId), language, token || undefined);
        setTreatmentData(res);
      } catch (err) {
        console.warn('[PRESCRIPTION] Failed to load treatment:', err);
      } finally {
        setIsLoading(false);
      }
    }
    loadTreatment();
  }, [scanId, incomingDisease, language]);

  // Audio player for Read Aloud / Listen action
  const audioPlayer = useAudioPlayer(VOICE_GUIDANCE_ASSET);
  const audioPlayerStatus = useAudioPlayerStatus(audioPlayer);
  const isPlayingAudio = Boolean(audioPlayerStatus.playing);

  // Entrance animation
  const fadeAnim = useRef(new Animated.Value(0)).current;

  // Page entrance transition
  useEffect(() => {
    if (!isLoading) {
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 350,
        useNativeDriver: true,
      }).start();
    }
  }, [fadeAnim, isLoading]);

  // Audio cleanup on unmount
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

  // 1. INLINE LOADING STATE
  if (isLoading) {
    return (
      <SafeAreaView edges={['top', 'bottom']} style={styles.safeArea}>
        <View style={styles.loadingContainer}>
          <View style={styles.loadingCard}>
            <ActivityIndicator color="#1B4332" size="large" />
            <Text style={styles.loadingTitle}>{labels.loadingTitle}</Text>
            <Text style={styles.loadingSubtitle}>{formatCrop(labels.loadingSubtitle)}</Text>
          </View>
        </View>
      </SafeAreaView>
    );
  }

  // 2. ERROR STATE
  if (!normalizedImageUri || hasError) {
    return (
      <SafeAreaView edges={['top', 'bottom']} style={styles.safeArea}>
        <View style={styles.errorContainer}>
          <View style={styles.errorCard}>
            <View style={styles.errorIconWrap}>
              <InfoGlyph color="#C7A45A" />
            </View>
            <Text style={styles.errorTitle}>{labels.errorTitle}</Text>
            <Text style={styles.errorSubtitle}>{formatCrop(labels.errorSubtitle)}</Text>

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
            <Text style={styles.errorSubtitle}>{formatCrop(labels.invalidImageDesc)}</Text>

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

  // Dynamic disease & state resolution
  const isHealthy =
    status === 'no_disease_detected' ||
    incomingDisease?.toLowerCase() === 'healthy leaf' ||
    incomingDisease?.toLowerCase() === 'healthy';

  const displayDisease = isHealthy
    ? labels.healthyTitle
    : incomingDisease
      ? tDisease(incomingDisease)
      : labels.errorTitle;

  const displayConfidence = isHealthy ? '' : formatConfidence(incomingConfidence);

  // Localized verified recommendation helper
  const loc = getLocalizedRecommendation(treatmentData, language, incomingDisease);
  const isSeedTreatment = loc.isSeedTreatment;

  // Section 3: Farmer Explanation
  const explanationText = isHealthy
    ? formatCrop(labels.healthyDesc)
    : loc.diseaseExplanation;

  // Section 4: Recommended Treatment
  const treatmentText = isHealthy
    ? null
    : (loc.isVerified ? loc.treatment : labels.treatmentUnavailable);

  // Section 5: Application Details (Dynamic verified fields only)
  const reqQty = loc.isVerified ? loc.recommendedQuantity : undefined;
  const reqWater = loc.isVerified ? (loc.waterQuantity || undefined) : undefined;
  const reqPerPump = loc.isVerified ? (loc.perPumpQuantity || undefined) : undefined;
  const reqTiming = loc.isVerified ? loc.applicationTiming : undefined;
  const hasAppDetails = Boolean(!isHealthy && loc.isVerified && (reqQty || reqWater || reqPerPump || reqTiming));

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

          {/* SECTION 1 — PAGE HEADER */}
          <View style={styles.titleSection}>
            <Text style={styles.headerTitle}>{labels.title}</Text>
            <Text style={styles.headerSubtitle}>{formatCrop(labels.subtitle)}</Text>
          </View>

          {/* SECTION 2 — DETECTED PROBLEM */}
          <View style={styles.card}>
            <View style={styles.cardHeaderRow}>
              <Text style={styles.cardCategoryLabel}>{labels.detectedProblem}</Text>
            </View>

            <Text style={styles.diseaseNameText}>{displayDisease}</Text>

            {!isHealthy && displayConfidence !== '' && (
              <View style={{ marginTop: 4 }}>
                <View style={styles.confidenceRow}>
                  <Text style={styles.confidenceLabel}>{labels.detectionConfidence}</Text>
                  <Text style={styles.confidenceValue}>{displayConfidence}</Text>
                </View>
                <Text style={styles.confidenceDisclaimer}>
                  {loc.confidenceDisclaimer}
                </Text>
              </View>
            )}
          </View>

          {/* SECTION 2B — RECORDED OBSERVATION */}
          {Boolean(normalizedTranscription) && (
            <View style={styles.card}>
              <View style={styles.cardHeaderRow}>
                <Text style={styles.cardCategoryLabel}>{labels.recordedObservationTitle}</Text>
              </View>
              <Text style={styles.explanationText}>
                {normalizedTranscription}
              </Text>
            </View>
          )}

          {/* SECTION 3 — WHAT DOES THIS MEAN? */}
          <View style={styles.card}>
            <Text style={styles.cardTitle}>{labels.whatDoesThisMean}</Text>
            <Text style={styles.explanationText}>{explanationText}</Text>
          </View>

          {/* SECTION 4 — RECOMMENDED TREATMENT */}
          {!isHealthy && (
            <View style={styles.card}>
              <Text style={styles.cardTitle}>{labels.recommendedTreatment}</Text>
              <Text style={styles.treatmentText}>{treatmentText}</Text>
            </View>
          )}

          {/* SECTION 4B — SPRAY GUIDANCE UNAVAILABLE (If no data) */}
          {!isHealthy && !treatmentData?.spray_guidance && (
            <View style={styles.card}>
              <Text style={styles.cardTitle}>
                {isSeedTreatment
                  ? (language === 'mr' ? 'उपचार मार्गदर्शन' : language === 'hi' ? 'उपचार मार्गदर्शन' : 'Treatment Guidance')
                  : (language === 'mr' ? 'फवारणी मार्गदर्शन' : language === 'hi' ? 'छिड़काव मार्गदर्शन' : 'Spray Guidance')}
              </Text>
              <Text style={styles.treatmentText}>{labels.sprayGuidanceUnavailable}</Text>
            </View>
          )}

          {/* SECTION 5 — APPLICATION DETAILS (Only displayed if verified dynamic data exists) */}
          {!isHealthy && hasAppDetails && (
            <View style={styles.card}>
              <Text style={styles.cardTitle}>
                {isSeedTreatment
                  ? (language === 'mr' ? 'उपचार व वापर तपशील' : language === 'hi' ? 'उपचार एवं उपयोग विवरण' : 'Application Details')
                  : labels.applicationDetails}
              </Text>
              <View style={styles.appDetailsGrid}>
                {Boolean(reqQty) && (
                  <View style={styles.detailRow}>
                    <Text style={styles.detailLabel}>{labels.recommendedQuantity}</Text>
                    <Text style={styles.detailValue}>{reqQty}</Text>
                  </View>
                )}
                {Boolean(reqWater) && (
                  <View style={styles.detailRow}>
                    <Text style={styles.detailLabel}>{labels.waterRequired}</Text>
                    <Text style={styles.detailValue}>{reqWater}</Text>
                  </View>
                )}
                {Boolean(reqPerPump) && (
                  <View style={styles.detailRow}>
                    <Text style={styles.detailLabel}>{labels.perPump}</Text>
                    <Text style={styles.detailValue}>{reqPerPump}</Text>
                  </View>
                )}
                {Boolean(reqTiming) && (
                  <View style={styles.detailRow}>
                    <Text style={styles.detailLabel}>
                      {isSeedTreatment
                        ? (language === 'mr' ? 'वापराची वेळ' : language === 'hi' ? 'उपयोग का समय' : 'Application Timing')
                        : labels.sprayTiming}
                    </Text>
                    <Text style={styles.detailValue}>{reqTiming}</Text>
                  </View>
                )}
              </View>
            </View>
          )}

          {/* SECTION 6 — IMPORTANT NOTE */}
          <View style={styles.importantCard}>
            <View style={styles.importantIconWrap}>
              <InfoGlyph color="#1B4332" />
            </View>
            <View style={styles.importantCopyWrap}>
              <Text style={styles.importantTitle}>{labels.importantTitle}</Text>
              <Text style={styles.importantText}>
                {loc.importantAlert
                  ? `${loc.importantAlert}\n\n${labels.importantNotice}`
                  : labels.importantNotice}
              </Text>
            </View>
          </View>

          {/* SECTION 7 — PRIMARY NEXT ACTION */}
          <View style={styles.actionsSection}>
            <Pressable
              accessibilityHint="Returns to scan another Tur leaf"
              accessibilityLabel={labels.scanAnotherLeaf}
              accessibilityRole="button"
              onPress={handleScanAnother}
              style={({ pressed }) => [styles.primaryButton, pressed && styles.buttonPressed]}
            >
              <Text style={styles.primaryButtonText}>{labels.scanAnotherLeaf}</Text>
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
    height: 38,
    paddingHorizontal: 14,
    borderRadius: 19,
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#CBE2D1',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    elevation: 1,
    shadowColor: '#1B4332',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
  },
  listenButtonText: {
    color: '#1B4332',
    fontSize: 13,
    fontWeight: '700',
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

  // Cards
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 22,
    padding: 20,
    borderWidth: 1,
    borderColor: '#E2E8DC',
    marginBottom: 18,
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
    marginBottom: 10,
  },
  cardCategoryLabel: {
    fontSize: 12,
    fontWeight: '700',
    color: '#2D6A4F',
    textTransform: 'uppercase',
    letterSpacing: 0.8,
  },
  diseaseNameText: {
    fontSize: 22,
    fontWeight: '800',
    color: '#0F2419',
    letterSpacing: -0.3,
    marginBottom: 8,
  },
  confidenceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginTop: 4,
  },
  confidenceLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: '#557A66',
  },
  confidenceValue: {
    fontSize: 14,
    fontWeight: '800',
    color: '#1B4332',
  },
  confidenceDisclaimer: {
    fontSize: 12,
    color: '#476355',
    marginTop: 4,
    lineHeight: 16,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '800',
    color: '#0F2419',
    marginBottom: 10,
  },
  explanationText: {
    fontSize: 14,
    lineHeight: 22,
    fontWeight: '500',
    color: '#344E41',
  },
  treatmentText: {
    fontSize: 15,
    lineHeight: 23,
    fontWeight: '600',
    color: '#1B4332',
  },

  // Application Details Grid
  appDetailsGrid: {
    gap: 12,
    marginTop: 4,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: 12,
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#F0F4EE',
  },
  detailLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#557A66',
    flexShrink: 0,
    maxWidth: '45%',
  },
  detailValue: {
    fontSize: 14,
    fontWeight: '700',
    color: '#0F2419',
    flex: 1,
    textAlign: 'right',
    flexWrap: 'wrap',
  },

  // Important Card
  importantCard: {
    backgroundColor: '#F7FAF7',
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: '#DDE9DF',
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
    marginBottom: 24,
  },
  importantIconWrap: {
    marginTop: 2,
  },
  importantCopyWrap: {
    flex: 1,
  },
  importantTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: '#1B4332',
    marginBottom: 3,
  },
  importantText: {
    fontSize: 12,
    lineHeight: 18,
    fontWeight: '500',
    color: '#476355',
  },

  // Actions Section
  actionsSection: {
    gap: 12,
    marginBottom: 16,
  },
  primaryButton: {
    height: 52,
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
        shadowRadius: 10,
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
    height: 48,
    borderRadius: 16,
    backgroundColor: '#FFFFFF',
    borderWidth: 1.5,
    borderColor: '#CBE2D1',
    alignItems: 'center',
    justifyContent: 'center',
  },
  secondaryButtonText: {
    color: '#1B4332',
    fontSize: 15,
    fontWeight: '700',
  },

  // Loading & Error Containers
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  loadingCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 24,
    padding: 32,
    alignItems: 'center',
    width: '100%',
    maxWidth: 400,
    borderWidth: 1,
    borderColor: '#E2E8DC',
    elevation: 3,
  },
  loadingTitle: {
    fontSize: 18,
    fontWeight: '800',
    color: '#0F2419',
    marginTop: 18,
    marginBottom: 6,
    textAlign: 'center',
  },
  loadingSubtitle: {
    fontSize: 14,
    fontWeight: '500',
    color: '#557A66',
    textAlign: 'center',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  errorCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 24,
    padding: 28,
    alignItems: 'center',
    width: '100%',
    maxWidth: 400,
    borderWidth: 1,
    borderColor: '#E2E8DC',
    elevation: 3,
    gap: 12,
  },
  errorIconWrap: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#FFFBEB',
    alignItems: 'center',
    justifyContent: 'center',
  },
  errorTitle: {
    fontSize: 18,
    fontWeight: '800',
    color: '#0F2419',
    textAlign: 'center',
  },
  errorSubtitle: {
    fontSize: 14,
    fontWeight: '500',
    color: '#557A66',
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 8,
  },
  infoCircle: {
    width: 24,
    height: 24,
    borderRadius: 12,
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
  infoDot: {
    width: 3,
    height: 3,
    borderRadius: 1.5,
    marginBottom: 2,
  },
  infoStem: {
    width: 2,
    height: 8,
    borderRadius: 1,
  },
  buttonPressed: {
    opacity: 0.88,
    transform: [{ scale: 0.985 }],
  },
});
