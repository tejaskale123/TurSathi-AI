import { useCallback, useEffect, useRef, useState } from 'react';
import { useLocalSearchParams, useRouter } from 'expo-router';
import {
  ActivityIndicator,
  Animated,
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
import { getAuthToken } from '../config/tokenStore';
import {
  fetchAIGuidance,
  RecommendationApiError,
  ClaudeGuidanceResponse,
} from '../config/recommendationApi';
import { getLocalizedRecommendation } from '../i18n/recommendationContent';

// Reusable SVG-like Glyph vectors (strictly no emojis, stickers, or AI graphics)
function Glyph({
  name,
  color = '#1A4D33',
  size = 18,
}: {
  name: 'back' | 'check' | 'arrow' | 'info' | 'shield' | 'speaker' | 'stop' | 'alert';
  color?: string;
  size?: number;
}) {
  if (name === 'back') {
    return (
      <View style={[styles.glyphBox, { width: size, height: size }]}>
        <View style={[styles.backShaft, { backgroundColor: color }]} />
        <View style={[styles.backHead, { borderColor: color }]} />
      </View>
    );
  }

  if (name === 'check') {
    return (
      <View style={[styles.checkCircle, { borderColor: color }]}>
        <View style={[styles.checkShort, { backgroundColor: color }]} />
        <View style={[styles.checkLong, { backgroundColor: color }]} />
      </View>
    );
  }

  if (name === 'arrow') {
    return (
      <View style={[styles.glyphBox, { width: size, height: size }]}>
        <View style={[styles.arrowHead, { borderColor: color }]} />
      </View>
    );
  }

  if (name === 'shield') {
    return (
      <View style={[styles.shieldBox, { borderColor: color }]}>
        <View style={[styles.shieldCheck, { backgroundColor: color }]} />
      </View>
    );
  }

  if (name === 'speaker') {
    const scale = size / 16;
    return (
      <View style={[styles.glyphBox, { width: size, height: size }]}>
        <View
          style={{
            position: 'absolute',
            left: 1 * scale,
            width: 4 * scale,
            height: 6 * scale,
            backgroundColor: color,
            borderRadius: 1,
          }}
        />
        <View
          style={{
            position: 'absolute',
            left: 4 * scale,
            width: 0,
            height: 0,
            borderStyle: 'solid',
            borderRightWidth: 5.5 * scale,
            borderTopWidth: 5.5 * scale,
            borderBottomWidth: 5.5 * scale,
            borderLeftWidth: 0,
            borderRightColor: color,
            borderTopColor: 'transparent',
            borderBottomColor: 'transparent',
          }}
        />
        <View
          style={{
            position: 'absolute',
            right: 1 * scale,
            width: 6 * scale,
            height: 6 * scale,
            borderRightWidth: 1.6 * scale,
            borderTopWidth: 1.6 * scale,
            borderColor: color,
            borderRadius: 4 * scale,
            transform: [{ rotate: '45deg' }],
          }}
        />
      </View>
    );
  }

  if (name === 'stop') {
    const boxSize = Math.round(size * 0.55);
    return (
      <View style={[styles.glyphBox, { width: size, height: size }]}>
        <View
          style={{
            width: boxSize,
            height: boxSize,
            backgroundColor: color,
            borderRadius: 1.5,
          }}
        />
      </View>
    );
  }

  if (name === 'alert') {
    return (
      <View style={[styles.alertIconWrap, { borderColor: color }]}>
        <View style={[styles.alertDot, { backgroundColor: color }]} />
        <View style={[styles.alertLine, { backgroundColor: color }]} />
      </View>
    );
  }

  // Default info glyph
  return (
    <View style={[styles.infoCircle, { borderColor: color }]}>
      <View style={[styles.infoDot, { backgroundColor: color }]} />
      <View style={[styles.infoStem, { backgroundColor: color }]} />
    </View>
  );
}

// Locale mapping for Text-to-Speech
const SPEECH_LOCALES: Record<Language, string> = {
  en: 'en-IN',
  mr: 'mr-IN',
  hi: 'hi-IN',
};

// Localized strings dictionary for Smart Spray Guidance screen
const UI_TEXT: Record<
  Language,
  {
    brand: string;
    headerTitle: string;
    headerSubtitle: string;
    importantTitle: string;
    importantMessage: string;
    leafConditionTitle: string;
    statusNeedsTreatment: string;
    statusMonitor: string;
    statusAttention: string;
    sprayGuidanceTitle: string;
    sprayGuidanceSubtitle: string;
    afterSprayingTitle: string;
    safetyTitle: string;
    farmerActionTitle: string;
    farmerActionMessage: string;
    listenGuidance: string;
    stopGuidance: string;
    moreInformation: string;
    scanAnotherLeaf: string;
    loadingTitle: string;
    errorTitle: string;
    unverifiedTitle: string;
    tryAgain: string;
    recordedObservationTitle: string;
  }
> = {
  en: {
    brand: 'TurSathi AI',
    headerTitle: 'SMART SPRAY GUIDANCE',
    headerSubtitle: 'Practical guidance for applying the recommended treatment safely.',
    importantTitle: 'Important',
    importantMessage:
      'Follow the verified treatment recommendation and product-label instructions while spraying.',
    leafConditionTitle: 'Leaf Condition',
    statusNeedsTreatment: 'Needs Treatment',
    statusMonitor: 'Monitor',
    statusAttention: 'Attention Required',
    sprayGuidanceTitle: 'Spray Guidance',
    sprayGuidanceSubtitle: 'What to do while spraying',
    afterSprayingTitle: 'After Spraying',
    safetyTitle: 'Safety & Precautions',
    farmerActionTitle: 'Farmer Action',
    farmerActionMessage:
      'Monitor your Tur crop regularly. If symptoms continue, increase, or change, scan a fresh leaf again.',
    listenGuidance: 'Listen to Guidance',
    stopGuidance: 'Stop',
    moreInformation: 'More Information',
    scanAnotherLeaf: 'Scan Another Leaf →',
    loadingTitle: 'Preparing spray guidance...',
    errorTitle: 'Verified spray guidance is currently unavailable.',
    unverifiedTitle: 'Verified spray guidance is not available for this condition yet.',
    tryAgain: 'Try Again',
    recordedObservationTitle: 'Your Recorded Observation',
  },
  mr: {
    brand: 'TurSathi AI',
    headerTitle: 'स्मार्ट फवारणी मार्गदर्शन',
    headerSubtitle: 'शिफारस केलेले उपचार सुरक्षितपणे वापरण्यासाठी प्रत्यक्ष मार्गदर्शन.',
    importantTitle: 'महत्त्वाचे',
    importantMessage:
      'फवारणी करताना नेहमी पडताळलेली कृषी शिफारस आणि उत्पादन लेबलच्या सूचनांचे पालन करा.',
    leafConditionTitle: 'पानाची स्थिती',
    statusNeedsTreatment: 'उपचार आवश्यक',
    statusMonitor: 'निरीक्षण करा',
    statusAttention: 'लक्ष देणे आवश्यक',
    sprayGuidanceTitle: 'फवारणी मार्गदर्शन',
    sprayGuidanceSubtitle: 'फवारणी करताना काय करावे',
    afterSprayingTitle: 'फवारणीनंतर',
    safetyTitle: 'सुरक्षा आणि काळजी',
    farmerActionTitle: 'शेतकरी कृती',
    farmerActionMessage:
      'तुमच्या तूर पिकाचे नियमित निरीक्षण करा. लक्षणे तशीच राहिल्यास, वाढल्यास किंवा बदलल्यास पुन्हा नवीन पान स्कॅन करा.',
    listenGuidance: 'मार्गदर्शन ऐका',
    stopGuidance: 'थांबवा',
    moreInformation: 'अधिक माहिती',
    scanAnotherLeaf: 'दुसरे पान स्कॅन करा →',
    loadingTitle: 'फवारणी मार्गदर्शन तयार होत आहे...',
    errorTitle: 'पडताळलेले फवारणी मार्गदर्शन सध्या उपलब्ध नाही.',
    unverifiedTitle: 'या स्थितीसाठी पडताळलेले फवारणी मार्गदर्शन अद्याप उपलब्ध नाही.',
    tryAgain: 'पुन्हा प्रयत्न करा',
    recordedObservationTitle: 'तुम्ही नोंदवलेली समस्या',
  },
  hi: {
    brand: 'TurSathi AI',
    headerTitle: 'स्मार्ट छिड़काव मार्गदर्शन',
    headerSubtitle: 'अनुशंसित उपचार का सुरक्षित उपयोग करने के लिए व्यावहारिक मार्गदर्शन।',
    importantTitle: 'महत्वपूर्ण',
    importantMessage:
      'छिड़काव करते समय हमेशा सत्यापित कृषि अनुशंसा और उत्पाद लेबल के निर्देशों का पालन करें।',
    leafConditionTitle: 'पत्ती की स्थिति',
    statusNeedsTreatment: 'उपचार आवश्यक',
    statusMonitor: 'निगरानी करें',
    statusAttention: 'ध्यान आवश्यक',
    sprayGuidanceTitle: 'छिड़काव मार्गदर्शन',
    sprayGuidanceSubtitle: 'छिड़काव करते समय क्या करें',
    afterSprayingTitle: 'छिड़काव के बाद',
    safetyTitle: 'सुरक्षा एवं सावधानियां',
    farmerActionTitle: 'किसान कार्रवाई',
    farmerActionMessage:
      'अपनी तूर फसल की नियमित निगरानी करें। यदि लक्षण बने रहते हैं, बढ़ते हैं या बदलते हैं, तो नई पत्ती स्कैन करें।',
    listenGuidance: 'मार्गदर्शन सुनें',
    stopGuidance: 'रोकें',
    moreInformation: 'अधिक जानकारी',
    scanAnotherLeaf: 'दूसरी पत्ती स्कैन करें →',
    loadingTitle: 'छिड़काव मार्गदर्शन तैयार हो रहा है...',
    errorTitle: 'सत्यापित छिड़काव मार्गदर्शन वर्तमान में उपलब्ध नहीं है।',
    unverifiedTitle: 'इस स्थिति के लिए सत्यापित छिड़काव मार्गदर्शन अभी उपलब्ध नहीं है।',
    tryAgain: 'पुनः प्रयास करें',
    recordedObservationTitle: 'आपकी दर्ज की गई समस्या',
  },
};

// Honest confidence formatter: deep learning softmax scores reflect visual pattern similarity,
// not 100% infallible truth. Cap at 99.0% to prevent misleading farmers.
const formatConfidenceHonest = (val: number | string | undefined | null): string => {
  const num = Number(val);
  if (!Number.isFinite(num) || num <= 0) return '0%';
  const normalized = num <= 1 ? num * 100 : num;
  const capped = Math.min(normalized, 99.0);
  return `${capped.toFixed(1)}%`;
};

// Static practical fallback content matching exact specifications
const DEFAULT_SPRAY_STEPS: Record<Language, string[]> = {
  en: [
    '01 Prepare the sprayer',
    '02 Follow the recommended treatment',
    '03 Spray the affected Tur plants evenly',
    '04 Avoid unnecessary overspray',
    '05 Keep people and animals away from the spray area',
  ],
  mr: [
    '01 फवारणी पंप तयार करा',
    '02 शिफारस केलेल्या उपचारांचे पालन करा',
    '03 बाधित तूर पिकावर एकसमान फवारणी करा',
    '04 अनावश्यक जास्त फवारणी टाळा',
    '05 फवारणी क्षेत्रापासून माणसे आणि जनावरांना दूर ठेवा',
  ],
  hi: [
    '01 छिड़काव पंप तैयार करें',
    '02 अनुशंसित उपचार का पालन करें',
    '03 प्रभावित तूर फसल पर एकसमान छिड़काव करें',
    '04 अनावश्यक अत्यधिक छिड़काव से बचें',
    '05 छिड़काव क्षेत्र से लोगों और पशुओं को दूर रखें',
  ],
};

const DEFAULT_AFTER_SPRAYING: Record<Language, string[]> = {
  en: [
    'Clean the sprayer properly',
    'Wash hands and exposed areas',
    'Observe the crop regularly',
    'Do not repeat spraying unnecessarily',
  ],
  mr: [
    'फवारणी पंप योग्य प्रकारे स्वच्छ करा',
    'हात आणि उघडे भाग स्वच्छ धुवा',
    'पिकाचे नियमित निरीक्षण करा',
    'अनावश्यक फवारणी पुन्हा करू नका',
  ],
  hi: [
    'छिड़काव पंप को अच्छी तरह साफ करें',
    'हाथ और खुले अंगों को अच्छी तरह धोएं',
    'फसल की नियमित निगरानी करें',
    'अनावश्यक छिड़काव दोबारा न करें',
  ],
};

const DEFAULT_SAFETY_PRECAUTIONS: Record<Language, string[]> = {
  en: [
    'Wear gloves and protective clothing',
    'Avoid direct contact with the spray',
    'Keep children and animals away',
    'Follow product-label instructions',
  ],
  mr: [
    'हातमोजे आणि संरक्षक कपडे वापरा',
    'फवारणीचा थेट संपर्क टाळा',
    'मुले आणि जनावरांना दूर ठेवा',
    'उत्पादन लेबलवरील सूचनांचे पालन करा',
  ],
  hi: [
    'दस्ताने और सुरक्षात्मक कपड़े पहनें',
    'छिड़काव के सीधे संपर्क से बचें',
    'बच्चों और पशुओं को दूर रखें',
    'उत्पाद लेबल के निर्देशों का पालन करें',
  ],
};

export default function SprayGuidanceScreen() {
  const router = useRouter();
  const { language, tDisease } = useLanguage();
  const ui = UI_TEXT[language] || UI_TEXT.en;

  const params = useLocalSearchParams<{
    diseaseName?: string;
    disease_name?: string;
    confidence?: string;
    severity?: string;
    status?: string;
    imageUri?: string;
    voiceUri?: string;
    transcription?: string | string[];
    scanId?: string;
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

  const rawDiseaseName = (params.diseaseName?.trim() || params.disease_name?.trim() || '').trim();
  const parsedConfidence = Number(params.confidence);
  const hasValidConfidence = Number.isFinite(parsedConfidence);
  const isConfidenceTooLow = hasValidConfidence && parsedConfidence < 0.60;

  // API State
  const [isGuidanceLoading, setIsGuidanceLoading] = useState<boolean>(true);
  const [isUnverified, setIsUnverified] = useState<boolean>(false);
  const [hasError, setHasError] = useState<boolean>(false);
  const [data, setData] = useState<ClaudeGuidanceResponse | null>(null);
  const [isLowConfidence, setIsLowConfidence] = useState<boolean>(isConfidenceTooLow);

  // Voice narration state
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false);
  const fadeAnim = useRef(new Animated.Value(0)).current;

  // Entrance animation
  useEffect(() => {
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: 350,
      useNativeDriver: true,
    }).start();
  }, [fadeAnim]);

  // Load spray guidance from API
  const loadGuidance = useCallback(async (signal?: AbortSignal) => {
    setIsGuidanceLoading(true);
    setHasError(false);
    setIsUnverified(false);

    const guidanceStartTime = Date.now();
    console.log(`[PERF][SPRAY_GUIDANCE] AI guidance requested at: ${guidanceStartTime}`);

    // Safety gate:
    // Do not request disease-specific spray guidance
    // when AI confidence is below 60%.
    if (!Number.isFinite(parsedConfidence) || parsedConfidence < 0.60) {
      console.warn(
        `[SPRAY GUIDANCE] Low confidence prediction. ` +
        `confidence=${params.confidence ?? 'missing'}`
      );

      setIsLowConfidence(true);
      setIsGuidanceLoading(false);
      return;
    }

    try {
      const token = await getAuthToken();

      const rawScanId = Array.isArray(params.scanId) ? params.scanId[0] : params.scanId;
      const parsedScanId = rawScanId ? parseInt(rawScanId, 10) : NaN;

      if (!Number.isFinite(parsedScanId)) {
        throw new RecommendationApiError(400, 'Missing or invalid scanId for spray guidance.');
      }

      const res = await fetchAIGuidance(
        parsedScanId,
        language,
        token || undefined,
        signal,
      );

      const guidanceDuration = Date.now() - guidanceStartTime;
      console.log(`[PERF][SPRAY_GUIDANCE] AI guidance loaded successfully in ${guidanceDuration}ms`);

      if (res.status === 'low_confidence') {
        setIsLowConfidence(true);
      } else if (
        res.spray_guidance_available === false &&
        res.disease_name?.toLowerCase() !== 'healthy' &&
        !res.disease_name?.toLowerCase().includes('webber')
      ) {
        setIsUnverified(true);
      }

      setData(res);
    } catch (err: any) {
      if (signal?.aborted || err?.message === 'Request was canceled.') {
        // Intentional cancellation when navigating away or unmounting
        return;
      }
      if ((err instanceof RecommendationApiError || err?.name === 'RecommendationApiError') && err.isNotFound) {
        if (!rawDiseaseName?.toLowerCase().includes('webber') && !rawDiseaseName?.toLowerCase().includes('healthy')) {
          setIsUnverified(true);
        }
      } else {
        console.warn('[SPRAY GUIDANCE] API Error:', err?.message || err);
        setHasError(true);
      }
    } finally {
      if (!signal?.aborted) {
        setIsGuidanceLoading(false);
      }
    }
  }, [rawDiseaseName, params.confidence, params.scanId, language, parsedConfidence]);

  useEffect(() => {
    const controller = new AbortController();
    loadGuidance(controller.signal);
    return () => {
      controller.abort();
    };
  }, [loadGuidance]);

  // Cleanup speech on unmount
  useEffect(() => {
    return () => {
      try {
        Speech.stop();
      } catch { }
    };
  }, []);

  // Determine dynamic leaf condition badge text
  const conditionStatus = data?.disease_name || rawDiseaseName || ui.statusNeedsTreatment;
  const displayConditionName = tDisease(conditionStatus) || conditionStatus;

  // Localized recommendation content matching verified ICAR/agricultural standards
  const loc = getLocalizedRecommendation(data, language, rawDiseaseName);

  // Text-to-Speech handler
  const handleToggleVoice = useCallback(() => {
    if (isSpeaking) {
      try {
        Speech.stop();
      } catch { }
      setIsSpeaking(false);
      return;
    }

    const steps = (loc.isHealthy || loc.isWebber)
      ? (loc.isHealthy
          ? [
              language === 'mr' ? 'नियमित शेत निरीक्षण करा' : language === 'hi' ? 'नियमित खेत निरीक्षण करें' : 'Continue regular field inspection',
              language === 'mr' ? 'संतुलित पाणी व खत व्यवस्थापन ठेवा' : language === 'hi' ? 'संतुलित पानी और उर्वरक प्रबंधन रखें' : 'Maintain balanced irrigation and nutrition',
              language === 'mr' ? 'शेत तणमुक्त व स्वच्छ ठेवा' : language === 'hi' ? 'खेत को खरपतवार मुक्त व साफ रखें' : 'Keep field clean and weed-free',
              language === 'mr' ? 'अनावश्यक रासायनिक फवारणी टाळा' : language === 'hi' ? 'अनावश्यक रासायनिक छिड़काव से बचें' : 'Avoid unnecessary chemical sprays',
            ]
          : [
              language === 'mr' ? 'शेतात शेंड्याकडील पाने व जाळी प्रत्यक्ष तपासा' : language === 'hi' ? 'खेत में शीर्ष पत्तियों व जालों की प्रत्यक्ष जांच करें' : 'Inspect shoot tips and webbed leaves in the field',
              language === 'mr' ? 'प्रत्यक्ष पाहणीवरून प्रादुर्भावाचे प्रमाण ठरवा' : language === 'hi' ? 'प्रत्यक्ष जांच से प्रकोप की गंभीरता का आकलन करें' : 'Assess infestation severity based on field observation',
              language === 'mr' ? 'सुरुवातीची जाळी झालेली पाने अळीसह तोडून नष्ट करा' : language === 'hi' ? 'शुरुआती जाले वाली पत्तियां इल्ली सहित तोड़कर नष्ट करें' : 'Manually collect and destroy webbed leaves with larvae',
              language === 'mr' ? 'रासायनिक फवारणी टाळा व KVK चा सल्ला घ्या' : language === 'hi' ? 'रासायनिक छिड़काव से बचें और KVK से सलाह लें' : 'Avoid unauthorized chemical sprays and consult local KVK',
            ])
      : [
          loc.treatment,
          loc.activeIngredient,
          loc.recommendedQuantity,
          loc.waterQuantity,
          loc.applicationTiming,
          loc.applicationMethod,
        ].filter(Boolean) as string[];

    const speechHeader = loc.headerTitle;
    const speechAlert = loc.importantAlert;
    const speechGuidance = (loc.isHealthy || loc.isWebber
      ? (loc.guidanceSectionTitle + ': ' + loc.guidanceSectionSubtitle + '. ')
      : (loc.isSeedTreatment
        ? (language === 'mr' ? 'बियाणे किंवा जमीन उपचार मार्गदर्शन: ' : language === 'hi' ? 'बीज या मृदा उपचार मार्गदर्शन: ' : 'Seed or soil treatment guidance: ')
        : (ui.sprayGuidanceTitle + ': ' + ui.sprayGuidanceSubtitle + '. '))) + steps.join('. ');

    const speechAfter = loc.afterSectionTitle + ': ' + loc.afterCareAdvisory.join('. ');
    const speechSafety = ui.safetyTitle + ': ' + loc.safetyPrecautions.join('. ');
    const speechFarmer = ui.farmerActionTitle + ': ' + loc.farmerAction.join('. ');

    const speechText = [
      speechHeader,
      ui.importantTitle + ': ' + speechAlert,
      speechGuidance,
      speechAfter,
      speechSafety,
      speechFarmer,
    ].join('\n\n');

    setIsSpeaking(true);

    try {
      Speech.speak(speechText, {
        language: SPEECH_LOCALES[language] || 'en-IN',
        rate: 0.9,
        pitch: 1.0,
        onDone: () => setIsSpeaking(false),
        onStopped: () => setIsSpeaking(false),
        onError: () => setIsSpeaking(false),
      });
    } catch {
      setIsSpeaking(false);
    }
  }, [isSpeaking, loc, language, ui]);

  // Navigation handlers
  const handleBack = () => {
    try {
      Speech.stop();
    } catch { }
    router.back();
  };

  const handleScanAnotherLeaf = () => {
    try {
      Speech.stop();
    } catch { }
    router.replace('/scan');
  };

  const handleMoreInformation = () => {
    try {
      Speech.stop();
    } catch { }
    const diseaseParam = params.disease_name || params.diseaseName;
    router.push({
      pathname: '/prescription',
      params: {
        ...(params.imageUri ? { imageUri: params.imageUri } : {}),
        ...(params.voiceUri ? { voiceUri: params.voiceUri } : {}),
        ...(normalizedTranscription ? { transcription: normalizedTranscription } : {}),
        ...(diseaseParam ? { disease_name: diseaseParam } : {}),
        ...(params.confidence ? { confidence: String(params.confidence) } : {}),
        ...(params.severity ? { severity: params.severity } : {}),
        ...(params.status ? { status: params.status } : {}),
        ...(params.scanId ? { scanId: params.scanId } : {}),
        ...(params.crop ? { crop: params.crop } : {}),
      },
    });
  };

  // Render Full-Screen Loading State only if no disease was forwarded and no data loaded yet
  const isInitialLoading = !rawDiseaseName && !data && isGuidanceLoading && !isLowConfidence && !hasError && !isUnverified;
  if (isInitialLoading) {
    return (
      <SafeAreaView edges={['top', 'bottom']} style={styles.safeArea}>
        <View style={styles.stateContainer}>
          <View style={styles.stateCard}>
            <ActivityIndicator color="#1A4D33" size="large" />
            <Text style={styles.loadingText}>{ui.loadingTitle}</Text>
          </View>
        </View>
      </SafeAreaView>
    );
  }

  // Render Low Confidence State
  if (isLowConfidence) {
    return (
      <SafeAreaView edges={['top', 'bottom']} style={styles.safeArea}>
        <View style={styles.stateContainer}>
          <View style={styles.stateCard}>
            <Glyph color="#8B6822" name="alert" size={28} />

            <Text style={styles.stateTitle}>
              {language === 'mr'
                ? 'निदानाची खात्री पुरेशी नाही'
                : language === 'hi'
                  ? 'निदान की पुष्टि पर्याप्त नहीं है'
                  : 'Prediction needs confirmation'}
            </Text>

            <Text style={styles.cardBodyText}>
              {language === 'mr'
                ? 'AI ला तूर पानाची स्थिती पुरेशा खात्रीने ओळखता आली नाही. कृपया चांगल्या प्रकाशात एका स्पष्ट तूर पानाचा फोटो पुन्हा घ्या.'
                : language === 'hi'
                  ? 'AI तूर की पत्ती की स्थिति को पर्याप्त विश्वास के साथ पहचान नहीं सका। कृपया अच्छी रोशनी में तूर की एक साफ पत्ती की फोटो फिर से लें।'
                  : 'The AI could not identify the Tur leaf condition with enough confidence. Please capture a clear photo of a single Tur leaf in good daylight.'}
            </Text>

            <View style={{ marginTop: 16, alignItems: 'center' }}>
              <Text
                style={{
                  fontSize: 13,
                  fontWeight: '700',
                  color: '#8B6822',
                }}
              >
                {language === 'mr'
                  ? `AI Confidence: ${(Number(params.confidence) * 100).toFixed(1)}%`
                  : language === 'hi'
                    ? `AI Confidence: ${(Number(params.confidence) * 100).toFixed(1)}%`
                    : `AI Confidence: ${(Number(params.confidence) * 100).toFixed(1)}%`}
              </Text>
            </View>

            <Pressable
              accessibilityRole="button"
              onPress={handleScanAnotherLeaf}
              style={({ pressed }) => [
                styles.primaryCta,
                pressed && styles.buttonPressed,
                { marginTop: 20 },
              ]}
            >
              <Text style={styles.primaryCtaText}>
                {ui.scanAnotherLeaf}
              </Text>
            </Pressable>
          </View>
        </View>
      </SafeAreaView>
    );
  }

  // Render Full-Screen Error State only if no disease prediction is available
  if (hasError && !rawDiseaseName) {
    return (
      <SafeAreaView edges={['top', 'bottom']} style={styles.safeArea}>
        <View style={styles.stateContainer}>
          <View style={styles.stateCard}>
            <Glyph color="#8B6822" name="info" size={24} />
            <Text style={styles.stateTitle}>{ui.errorTitle}</Text>

            <Pressable
              accessibilityRole="button"
              onPress={() => loadGuidance()}
              style={({ pressed }) => [styles.primaryCta, pressed && styles.buttonPressed]}
            >
              <Text style={styles.primaryCtaText}>{ui.tryAgain}</Text>
            </Pressable>

            <Pressable
              accessibilityRole="button"
              onPress={handleScanAnotherLeaf}
              style={({ pressed }) => [styles.secondaryCta, pressed && styles.buttonPressed]}
            >
              <Text style={styles.secondaryCtaText}>{ui.scanAnotherLeaf}</Text>
            </Pressable>
          </View>
        </View>
      </SafeAreaView>
    );
  }

  // Render Unverified / Empty Recommendation State
  if (isUnverified) {
    const confPct = formatConfidenceHonest(params.confidence);
    const isWebber = rawDiseaseName?.toLowerCase().includes('webber') || Boolean(data?.disease_name && data.disease_name.toLowerCase().includes('webber'));

    console.log(
      `[SPRAY_GUIDANCE_DIAGNOSTIC] conditionStatus="${conditionStatus}" displayConditionName="${displayConditionName}" rawConfidence="${params.confidence}" formattedConf="${confPct}" isUnverified=${isUnverified} isWebber=${isWebber}`
    );

    const unverifiedContent = {
      en: {
        title: isWebber ? "Potential Pest: Leaf Webber" : "AI Prediction: Verification Required",
        diseaseLabel: "Predicted Condition:",
        confLabel: "AI Visual Match:",
        confNote: "(Visual pattern similarity; field inspection required)",
        availLabel: "Spray Guidance:",
        availValue: isWebber ? "Chemical spray NOT recommended" : "Not available in verified database",
        statusNote: isWebber 
          ? "Unverified for chemical spraying (Safe cultural management only)" 
          : "Unverified in ICAR / agricultural database",
        message: isWebber
          ? "The AI model identified patterns matching Leaf Webber (Grapholita critica).\n\n⚠️ IMPORTANT SAFETY ADVISORY:\n• Verified chemical spray guidance is NOT available for Leaf Webber.\n• Do NOT spray unverified or banned pesticides (such as Dichlorvos).\n\n🌿 SAFE FARMER PRACTICES:\n• Inspect shoot tips and webbed leaf clusters regularly.\n• Manually collect and destroy folded / webbed leaves containing larvae in early stages.\n• Consult your local Krishi Vigyan Kendra (KVK) or agricultural extension officer for safe, approved management."
          : "The AI model produced a visual prediction, but verified agricultural spray guidance is currently unavailable for this condition.\n\nPlease consult a qualified agricultural expert or your local Krishi Vigyan Kendra (KVK) before applying any pesticide."
      },
      mr: {
        title: isWebber ? "Leaf Webber — पाने गुंडाळणारी अळी" : "AI अंदाज: पडताळणी आवश्यक",
        diseaseLabel: "अंदाजित स्थिती:",
        confLabel: "AI दृश्य साम्य (Visual Match):",
        confNote: "(पानातील लक्षणांचे साम्य; प्रत्यक्ष शेत तपासणी आवश्यक)",
        availLabel: "फवारणी मार्गदर्शन:",
        availValue: isWebber ? "रासायनिक फवारणी शिफारस नाही" : "प्रमाणित डेटामध्ये उपलब्ध नाही",
        statusNote: isWebber 
          ? "फवारणीसाठी अप्रमाणित (केवळ सुरक्षित एकात्मिक सल्ला)" 
          : "प्रमाणित कृषी डेटामध्ये उपलब्ध नाही",
        message: isWebber
          ? "AI मॉडेलने या पानात पाने गुंडाळणाऱ्या अळीची (Leaf Webber) लक्षणे ओळखली आहेत.\n\nमहत्त्वाची सुरक्षा सूचना:\n• पाने गुंडाळणाऱ्या अळीसाठी प्रमाणित रासायनिक फवारणी उपलब्ध नाही.\n• कोणतेही अनधिकृत किंवा बंदी घातलेले कीटकनाशक (उदा. डायक्लोर्व्हॉस) फवारू नका.\n\nशेतकऱ्यांसाठी सुरक्षित उपाय:\n• शेंड्याकडील पाने आणि जाळी बांधलेल्या पानांची नियमित पाहणी करा.\n• सुरुवातीच्या काळात जाळी झालेली पाने अळीसह तोडून नष्ट करा.\n• अधिकृत व सुरक्षित कीड व्यवस्थापनासाठी स्थानिक कृषी विज्ञान केंद्र (KVK) किंवा कृषी अधिकाऱ्यांचा सल्ला घ्या."
          : "AI मॉडेलने दृश्य लक्षणांवरून अंदाज दिला आहे, परंतु या आजारासाठी प्रमाणित फवारणी मार्गदर्शन सध्या उपलब्ध नाही.\n\nकोणतीही रासायनिक औषध फवारणी करण्यापूर्वी कृपया स्थानिक कृषी विज्ञान केंद्र (KVK) किंवा कृषी तज्ज्ञांचा सल्ला घ्या."
      },
      hi: {
        title: isWebber ? "संभावित कीट: लीफ वेबर (Leaf Webber)" : "AI अनुमान: सत्यापन आवश्यक",
        diseaseLabel: "अनुमानित स्थिति:",
        confLabel: "AI दृश्य समानता (Visual Match):",
        confNote: "(लक्षणों की दृश्य समानता; खेत में जांच आवश्यक)",
        availLabel: "छिड़काव मार्गदर्शन:",
        availValue: isWebber ? "रासायनिक छिड़काव अनुशंसित नहीं" : "सत्यापित डेटाबेस में उपलब्ध नहीं है",
        statusNote: isWebber 
          ? "छिड़काव हेतु असत्यापित (केवल सुरक्षित जैविक/भौतिक सलाह)" 
          : "प्रमाणित कृषि डेटाबेस में उपलब्ध नहीं",
        message: isWebber
          ? "AI मॉडल ने इस पत्ती में लीफ वेबर (Grapholita critica) कीट के लक्षणों की पहचान की है।\n\n⚠️ महत्वपूर्ण सुरक्षा सलाह:\n• लीफ वेबर कीट के लिए कोई रासायनिक छिड़काव सत्यापित नहीं है।\n• कोई भी अनधिकृत या प्रतिबंधित कीटनाशक (जैसे डाइक्लोरवोस) न छिड़कें।\n\n🌿 किसानों के लिए सुरक्षित उपाय:\n• शीर्ष पत्तियों और जाले वाले गुच्छों का नियमित निरीक्षण करें।\n• शुरुआती अवस्था में जाले वाली पत्तियों को इल्ली सहित इकट्ठा कर नष्ट करें।\n• सुरक्षित प्रबंधन हेतु स्थानीय कृषि विज्ञान केंद्र (KVK) या कृषि अधिकारी से संपर्क करें।"
          : "AI मॉडल ने दृश्य लक्षणों के आधार पर अनुमान लगाया है, लेकिन इस स्थिति के लिए सत्यापित छिड़काव मार्गदर्शन उपलब्ध नहीं है।\n\nकिसी भी कीटनाशक का उपयोग करने से पहले कृपया एक योग्य कृषि विशेषज्ञ से परामर्श लें।"
      }
    };
    
    // Fallback safely to 'en' if language isn't matched
    const localeStr = unverifiedContent[language as keyof typeof unverifiedContent] || unverifiedContent.en;

    return (
      <SafeAreaView edges={['top', 'bottom']} style={styles.safeArea}>
        <View style={styles.stateContainer}>
          <View style={styles.stateCard}>
            <Glyph color="#8B6822" name="info" size={28} />
            <Text style={styles.stateTitle}>{localeStr.title}</Text>

            <View style={{ marginTop: 16, width: '100%', backgroundColor: '#F9F5EC', padding: 14, borderRadius: 8, borderWidth: 1, borderColor: '#E8DEC4' }}>
              <View style={{ marginBottom: 8 }}>
                <Text style={{ fontSize: 12, color: '#6A7D71', fontWeight: '600' }}>{localeStr.diseaseLabel}</Text>
                <Text style={{ fontSize: 15, fontWeight: '700', color: '#1A4D33', marginTop: 2 }}>{displayConditionName}</Text>
              </View>

              <View style={{ marginBottom: 8, borderTopWidth: 1, borderTopColor: '#EFE7D2', paddingTop: 8 }}>
                <Text style={{ fontSize: 12, color: '#6A7D71', fontWeight: '600' }}>{localeStr.confLabel}</Text>
                <View style={{ flexDirection: 'row', alignItems: 'baseline', marginTop: 2, flexWrap: 'wrap' }}>
                  <Text style={{ fontSize: 15, fontWeight: '700', color: '#8B6822' }}>{confPct}</Text>
                  <Text style={{ fontSize: 11, color: '#8B6822', marginLeft: 6, fontStyle: 'italic' }}>{localeStr.confNote}</Text>
                </View>
              </View>

              <View style={{ borderTopWidth: 1, borderTopColor: '#EFE7D2', paddingTop: 8 }}>
                <Text style={{ fontSize: 12, color: '#6A7D71', fontWeight: '600' }}>{localeStr.availLabel}</Text>
                <Text style={{ fontSize: 14, fontWeight: '700', color: isWebber ? '#A34E36' : '#8B6822', marginTop: 2 }}>{localeStr.availValue}</Text>
                <Text style={{ fontSize: 11, color: '#6A7D71', marginTop: 2 }}>{localeStr.statusNote}</Text>
              </View>
            </View>

            <Text style={[styles.cardBodyText, { marginTop: 16 }]}>
              {localeStr.message}
            </Text>

            <Pressable
              accessibilityRole="button"
              onPress={handleScanAnotherLeaf}
              style={({ pressed }) => [
                styles.primaryCta,
                pressed && styles.buttonPressed,
                { marginTop: 24 },
              ]}
            >
              <Text style={styles.primaryCtaText}>{ui.scanAnotherLeaf}</Text>
            </Pressable>
          </View>
        </View>
      </SafeAreaView>
    );
  }

  // Dynamic arrays from backend data or localized default fallback steps
  const isSeedTreatment = loc.isSeedTreatment;
  const headerTitleText = loc.headerTitle;
  const headerSubtitleText = loc.isHealthy
    ? (language === 'mr' ? 'निरोगी पिकाची काळजी आणि शेतातील नियमित निरीक्षणासाठी मार्गदर्शक सूचना.' : language === 'hi' ? 'स्वस्थ फसल की देखभाल और नियमित खेत निरीक्षण के लिए मार्गदर्शन।' : 'Guidance for maintaining healthy crops and regular field inspection.')
    : isSeedTreatment
      ? (language === 'mr' ? 'शिफारस केलेले बियाणे/जमीन उपचार सुरक्षितपणे वापरण्यासाठी प्रत्यक्ष मार्गदर्शन.' : language === 'hi' ? 'अनुशंसित बीज/मृदा उपचार को सुरक्षित रूप से लागू करने के लिए व्यावहारिक मार्गदर्शन।' : 'Practical guidance for applying the recommended seed/soil treatment safely.')
      : loc.isWebber
        ? (language === 'mr' ? 'पाने गुंडाळणाऱ्या अळीसाठी सुरक्षित एकात्मिक व्यवस्थापन व शेत निरीक्षण सूचना.' : language === 'hi' ? 'लीफ वेबर कीट के लिए सुरक्षित एकीकृत प्रबंधन और खेत निरीक्षण मार्गदर्शन।' : 'Practical guidance for safe integrated management and regular field monitoring of Leaf Webber.')
        : ui.headerSubtitle;

  const importantAlertText = loc.importantAlert;
  const guidanceTitleText = loc.guidanceSectionTitle;
  const guidanceSubtitleText = loc.guidanceSectionSubtitle;
  const afterSprayingTitleText = loc.afterSectionTitle;

  const fieldLabels: Record<string, Record<Language, string>> = {
    treatment: { en: 'Treatment', mr: 'उपचार', hi: 'उपचार' },
    active_ingredient: { en: 'Active Ingredient', mr: 'सक्रिय घटक', hi: 'सक्रिय घटक' },
    recommended_quantity: { en: 'Recommended Qty', mr: 'शिफारस केलेले प्रमाण', hi: 'अनुशंसित मात्रा' },
    water_quantity: { en: 'Water Qty', mr: 'पाण्याचे प्रमाण', hi: 'पानी की मात्रा' },
    per_pump_quantity: { en: 'Per Pump Qty', mr: 'प्रति पंप प्रमाण', hi: 'प्रति पंप मात्रा' },
    spray_timing: { en: loc.timingLabel, mr: loc.timingLabel, hi: loc.timingLabel },
    application_method: { en: loc.methodLabel, mr: loc.methodLabel, hi: loc.methodLabel },
  };

  const PUMP_TITLE: Record<Language, string> = {
    en: 'For a 15-Litre Pump',
    mr: '15 लिटर पंपासाठी',
    hi: '15 लीटर पंप के लिए'
  };

  const MIXING_ADVISORY: Record<Language, string> = {
    en: 'Before mixing more than one product, check the product label or verified agricultural recommendation.',
    mr: 'एकापेक्षा जास्त औषधे एकत्र मिसळण्यापूर्वी उत्पादनाच्या label वरील सूचना किंवा अधिकृत कृषी शिफारस तपासा.',
    hi: 'एक से अधिक दवाओं को मिलाने से पहले उत्पाद के label या आधिकारिक कृषि सिफारिश की जांच करें।'
  };

  const getStepsList = () => {
      if (loc.isHealthy) {
          return [
              { id: '1', label: '', value: language === 'mr' ? '01 नियमित शेत निरीक्षण करा' : language === 'hi' ? '01 नियमित खेत निरीक्षण करें' : '01 Continue regular field inspection' },
              { id: '2', label: '', value: language === 'mr' ? '02 संतुलित पाणी व खत व्यवस्थापन ठेवा' : language === 'hi' ? '02 संतुलित पानी और उर्वरक प्रबंधन रखें' : '02 Maintain balanced irrigation and nutrition' },
              { id: '3', label: '', value: language === 'mr' ? '03 शेत तणमुक्त व स्वच्छ ठेवा' : language === 'hi' ? '03 खेत को खरपतवार मुक्त व साफ रखें' : '03 Keep field clean and weed-free' },
              { id: '4', label: '', value: language === 'mr' ? '04 अनावश्यक रासायनिक फवारणी टाळा' : language === 'hi' ? '04 अनावश्यक रासायनिक छिड़काव से बचें' : '04 Avoid unnecessary chemical sprays' },
          ];
      }
      if (loc.isWebber) {
          return [
              { id: '1', label: '', value: language === 'mr' ? '01 शेतात शेंड्याकडील पाने व जाळी प्रत्यक्ष तपासा' : language === 'hi' ? '01 खेत में शीर्ष पत्तियों व जालों की प्रत्यक्ष जांच करें' : '01 Inspect shoot tips and webbed leaves in the field' },
              { id: '2', label: '', value: language === 'mr' ? '02 प्रत्यक्ष पाहणीवरून प्रादुर्भावाचे प्रमाण ठरवा' : language === 'hi' ? '02 प्रत्यक्ष जांच से प्रकोप की गंभीरता का आकलन करें' : '02 Assess infestation severity based on field observation' },
              { id: '3', label: '', value: language === 'mr' ? '03 सुरुवातीची जाळी झालेली पाने अळीसह तोडून नष्ट करा' : language === 'hi' ? '03 शुरुआती जाले वाली पत्तियां इल्ली सहित तोड़कर नष्ट करें' : '03 Manually collect and destroy webbed leaves with larvae' },
              { id: '4', label: '', value: language === 'mr' ? '04 रासायनिक फवारणी टाळा व KVK चा सल्ला घ्या' : language === 'hi' ? '04 रासायनिक छिड़काव से बचें और KVK से सलाह लें' : '04 Avoid unauthorized chemical sprays & consult local KVK' },
          ];
      }
      if (!data?.spray_guidance && !loc.isVerified) {
          if (loc.farmerAction && loc.farmerAction.length > 0) {
              return loc.farmerAction.map((action, idx) => ({ id: String(idx + 1), label: '', value: action }));
          }
          return [
              { id: '1', label: '', value: language === 'mr' ? '01 प्रमाणित फवारणी मार्गदर्शन उपलब्ध नाही' : language === 'hi' ? '01 सत्यापित छिड़काव मार्गदर्शन उपलब्ध नहीं है' : '01 Verified spray guidance unavailable' },
              { id: '2', label: '', value: language === 'mr' ? '02 कोणतेही अनधिकृत कीटकनाशक फवारू नका' : language === 'hi' ? '02 किसी अनधिकृत कीटनाशक का छिड़काव न करें' : '02 Do not apply unverified chemical sprays' },
              { id: '3', label: '', value: language === 'mr' ? '03 स्थानिक कृषी विज्ञान केंद्र (KVK) चा सल्ला घ्या' : language === 'hi' ? '03 स्थानीय कृषि विज्ञान केंद्र (KVK) से परामर्श लें' : '03 Consult your local Krishi Vigyan Kendra (KVK)' },
          ];
      }
      const fields = [
          { key: 'treatment', label: fieldLabels.treatment[language], value: loc.treatment },
          { key: 'active_ingredient', label: fieldLabels.active_ingredient[language], value: loc.activeIngredient },
          { key: 'recommended_quantity', label: fieldLabels.recommended_quantity[language], value: loc.recommendedQuantity },
          loc.waterQuantity ? { key: 'water_quantity', label: fieldLabels.water_quantity[language], value: loc.waterQuantity } : null,
          { key: 'spray_timing', label: loc.timingLabel, value: loc.applicationTiming },
          { key: 'application_method', label: loc.methodLabel, value: loc.applicationMethod },
      ].filter(f => f && f.value) as { key: string; label: string; value: string }[];
      return fields.map(f => ({ id: f.key, label: f.label, value: f.value }));
  };

  const stepsList = getStepsList();
  const afterList = loc.afterCareAdvisory;
  const safetyList = loc.safetyPrecautions;
  const farmerAct = loc.farmerAction.join('\n\n');

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
              accessibilityHint="Returns to previous screen"
              accessibilityLabel="Go back"
              accessibilityRole="button"
              hitSlop={8}
              onPress={handleBack}
              style={({ pressed }) => [styles.backButton, pressed && styles.buttonPressed]}
            >
              <Glyph color="#1A4D33" name="back" />
            </Pressable>

            <View style={styles.headerCopy}>
              <Text style={styles.brand}>{ui.brand}</Text>
              <Text style={styles.headerTitle}>{headerTitleText}</Text>
              <Text style={styles.headerSubtitle}>{headerSubtitleText}</Text>
            </View>

            <View style={styles.headerSpacer} />
          </View>
          <View style={styles.headerDivider} />

          {/* SECTION A: IMPORTANT ALERT */}
          <View style={styles.alertCard}>
            <View style={styles.alertIconWrap}>
              <Glyph color="#8B6822" name="info" size={16} />
            </View>
            <View style={styles.alertCopy}>
              <Text style={styles.alertTitle}>{ui.importantTitle}</Text>
              <Text style={styles.alertMessage}>
                {importantAlertText}
              </Text>
            </View>
          </View>

          {/* RECORDED OBSERVATION */}
          {Boolean(normalizedTranscription) && (
            <View style={styles.card}>
              <View style={styles.conditionRow}>
                <Text style={styles.cardCategoryLabel}>{ui.recordedObservationTitle}</Text>
              </View>
              <Text style={[styles.cardBodyText, { marginTop: 8 }]}>
                {normalizedTranscription}
              </Text>
            </View>
          )}

          {/* SECTION B: LEAF CONDITION */}
          <View style={styles.card}>
            <View style={styles.conditionRow}>
              <Text style={styles.cardCategoryLabel}>{ui.leafConditionTitle}</Text>
              <View style={styles.conditionBadge}>
                <Text style={styles.conditionBadgeText}>{displayConditionName}</Text>
              </View>
            </View>

            {hasValidConfidence && (
              <View style={{ marginTop: 6 }}>
                <Text style={styles.confidenceSubText}>
                  {language === 'mr'
                    ? `AI खात्री (Confidence): ${(parsedConfidence * 100).toFixed(1)}%`
                    : language === 'hi'
                      ? `AI निश्चितता (Confidence): ${(parsedConfidence * 100).toFixed(1)}%`
                      : `AI Confidence: ${(parsedConfidence * 100).toFixed(1)}%`}
                </Text>
                <Text style={styles.confidenceDisclaimer}>
                  {loc.confidenceDisclaimer}
                </Text>
              </View>
            )}

            {isGuidanceLoading && !loc.diseaseExplanation && (
              <View style={styles.inlineAiStatusWrap}>
                <ActivityIndicator color="#1A4D33" size="small" />
                <Text style={styles.inlineAiStatusText}>
                  {language === 'mr'
                    ? 'तज्ज्ञ AI विश्लेषण आणि उपचार मार्गदर्शन तयार होत आहे...'
                    : language === 'hi'
                    ? 'विशेषज्ञ AI विश्लेषण और उपचार मार्गदर्शन तैयार हो रहा है...'
                    : 'Generating expert AI explanation & tailored dosage...'}
                </Text>
              </View>
            )}

            {Boolean(loc.diseaseExplanation) && (
              <Text style={[styles.cardBodyText, { marginTop: 12 }]}>
                {loc.diseaseExplanation}
              </Text>
            )}
          </View>

          {/* SECTION C: SPRAY GUIDANCE */}
          <View style={styles.card}>
            <View style={styles.sectionHeaderRow}>
              <Text style={styles.cardTitle}>{guidanceTitleText}</Text>
              <Text style={styles.cardSubtitle}>{guidanceSubtitleText}</Text>
            </View>

            {isGuidanceLoading && !data?.spray_guidance && (
              <View style={styles.inlineAiStatusWrap}>
                <ActivityIndicator color="#8B6822" size="small" />
                <Text style={styles.inlineAiStatusText}>
                  {language === 'mr'
                    ? 'पडताळलेल्या औषध शिफारसी व प्रमाण लोड होत आहेत...'
                    : language === 'hi'
                    ? 'सत्यापित दवा की सिफारिशें और मात्रा लोड हो रही हैं...'
                    : 'Loading verified spray recommendations and dosage...'}
                </Text>
              </View>
            )}

            {hasError && !data && (
              <View style={styles.inlineErrorWrap}>
                <Text style={styles.inlineErrorText}>
                  {language === 'mr'
                    ? 'तपशीलवार AI फवारणी मार्गदर्शन लोड करण्यात अडचण आली.'
                    : language === 'hi'
                    ? 'विस्तृत AI छिड़काव मार्गदर्शन लोड करने में समस्या आई।'
                    : 'Unable to load detailed AI spray guidance.'}
                </Text>
                <Pressable
                  accessibilityRole="button"
                  onPress={() => loadGuidance()}
                  style={({ pressed }) => [styles.inlineRetryButton, pressed && styles.buttonPressed]}
                >
                  <Text style={styles.inlineRetryButtonText}>{ui.tryAgain}</Text>
                </Pressable>
              </View>
            )}

            <View style={styles.stepsContainer}>
              {stepsList.map((stepItem: { id?: string; label: string; value: string }, idx: number) => {
                let numStr = String(idx + 1).padStart(2, '0');
                let bodyText = stepItem.value;
                if (!stepItem.label && /^\d{2}\s+/.test(stepItem.value)) {
                  numStr = stepItem.value.substring(0, 2);
                  bodyText = stepItem.value.substring(3).trim();
                }

                return (
                  <View key={idx}>
                    <View style={styles.stepCard}>
                      <View style={styles.stepBadge}>
                        <Text style={styles.stepNumber}>{numStr}</Text>
                      </View>
                      <View style={{ flex: 1 }}>
                        {Boolean(stepItem.label) && (
                          <Text style={[styles.stepText, { fontWeight: '700', marginBottom: 2 }]}>
                            {stepItem.label}
                          </Text>
                        )}
                        <Text style={styles.stepText}>{bodyText}</Text>
                      </View>
                    </View>

                    {stepItem.id === 'recommended_quantity' && data?.spray_guidance?.per_pump_quantity && (
                      <View style={{
                        marginTop: 2,
                        marginBottom: 4,
                        marginLeft: 40,
                        borderWidth: 1,
                        borderColor: '#EAD7A6',
                        borderRadius: 10,
                        backgroundColor: '#FBF3DD',
                        padding: 12,
                      }}>
                        <Text style={{ fontSize: 13, fontWeight: '700', color: '#8B6822', marginBottom: 4 }}>
                          {PUMP_TITLE[language] || PUMP_TITLE.en}
                        </Text>
                        <Text style={{ fontSize: 14, fontWeight: '700', color: '#2A4433', marginBottom: 8 }}>
                          {data.spray_guidance.per_pump_quantity}
                        </Text>
                        <Text style={{ fontSize: 12, color: '#6B5420', lineHeight: 16 }}>
                          {MIXING_ADVISORY[language] || MIXING_ADVISORY.en}
                        </Text>
                      </View>
                    )}
                  </View>
                );
              })}
            </View>
          </View>

          {/* SECTION D: AFTER SPRAYING */}
          <View style={styles.card}>
            <Text style={styles.cardTitle}>{afterSprayingTitleText}</Text>
            <View style={styles.checklistGroup}>
              {afterList.map((item: string, idx: number) => (
                <View key={idx} style={styles.checkRow}>
                  <View style={styles.checkIconWrap}>
                    <Glyph color="#1A4D33" name="check" size={12} />
                  </View>
                  <Text style={styles.checkText}>{item}</Text>
                </View>
              ))}
            </View>
          </View>

          {/* SECTION E: SAFETY & PRECAUTIONS */}
          <View style={styles.card}>
            <View style={styles.sectionHeaderRow}>
              <View style={styles.cardIconHeader}>
                <Glyph color="#1A4D33" name="shield" size={16} />
                <Text style={styles.cardTitle}>{ui.safetyTitle}</Text>
              </View>
            </View>

            <View style={styles.checklistGroup}>
              {safetyList.map((item: string, idx: number) => (
                <View key={idx} style={styles.checkRow}>
                  <View style={styles.safetyIconWrap}>
                    <Glyph color="#1A4D33" name="check" size={12} />
                  </View>
                  <Text style={styles.checkText}>{item}</Text>
                </View>
              ))}
            </View>
          </View>

          {/* SECTION F: FARMER ACTION */}
          <View style={styles.card}>
            <Text style={styles.cardTitle}>{ui.farmerActionTitle}</Text>
            <Text style={styles.cardBodyText}>
              {farmerAct}
            </Text>
          </View>

          {/* SECTION G: VOICE GUIDANCE */}
          <View style={styles.voiceSection}>
            <Pressable
              accessibilityHint={isSpeaking ? 'Stops reading spray guidance' : 'Reads spray guidance aloud'}
              accessibilityLabel={isSpeaking ? ui.stopGuidance : ui.listenGuidance}
              accessibilityRole="button"
              onPress={handleToggleVoice}
              style={({ pressed }) => [
                styles.voiceButton,
                isSpeaking && styles.voiceButtonActive,
                pressed && styles.buttonPressed,
              ]}
            >
              <Glyph
                color={isSpeaking ? '#FFFFFF' : '#1A4D33'}
                name={isSpeaking ? 'stop' : 'speaker'}
                size={16}
              />
              <Text
                style={[
                  styles.voiceButtonText,
                  isSpeaking && styles.voiceButtonTextActive,
                ]}
              >
                {isSpeaking ? ui.stopGuidance : ui.listenGuidance}
              </Text>
            </Pressable>
          </View>

          {/* SECTION H: FINAL CTA */}
          <View style={styles.ctaSection}>
            <Pressable
              accessibilityHint="Navigates to treatment recommendation page"
              accessibilityLabel={ui.moreInformation}
              accessibilityRole="button"
              onPress={handleMoreInformation}
              style={({ pressed }) => [styles.moreInfoCta, pressed && styles.buttonPressed]}
            >
              <Text style={styles.moreInfoCtaText}>{ui.moreInformation}</Text>
            </Pressable>

            <Pressable
              accessibilityHint="Navigates to scan screen to inspect another leaf"
              accessibilityLabel={ui.scanAnotherLeaf}
              accessibilityRole="button"
              onPress={handleScanAnotherLeaf}
              style={({ pressed }) => [styles.primaryCta, pressed && styles.buttonPressed]}
            >
              <Text style={styles.primaryCtaText}>{ui.scanAnotherLeaf}</Text>
            </Pressable>
          </View>
        </Animated.View>
      </ScrollView>
    </SafeAreaView>
  );
}

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

  // Glyph helpers
  glyphBox: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  backShaft: {
    width: 12,
    height: 2,
    borderRadius: 1,
  },
  backHead: {
    position: 'absolute',
    left: 2,
    width: 8,
    height: 8,
    borderLeftWidth: 2,
    borderBottomWidth: 2,
    transform: [{ rotate: '45deg' }],
  },
  checkCircle: {
    width: 18,
    height: 18,
    borderRadius: 9,
    borderWidth: 1.5,
    justifyContent: 'center',
    alignItems: 'center',
  },
  checkShort: {
    position: 'absolute',
    left: 4,
    top: 9,
    width: 4,
    height: 2,
    transform: [{ rotate: '45deg' }],
  },
  checkLong: {
    position: 'absolute',
    left: 6,
    top: 7,
    width: 7,
    height: 2,
    transform: [{ rotate: '-45deg' }],
  },
  arrowHead: {
    width: 8,
    height: 8,
    borderTopWidth: 2,
    borderRightWidth: 2,
    transform: [{ rotate: '45deg' }],
  },
  shieldBox: {
    width: 18,
    height: 20,
    borderWidth: 1.5,
    borderRadius: 4,
    alignItems: 'center',
    justifyContent: 'center',
  },
  shieldCheck: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  infoCircle: {
    width: 18,
    height: 18,
    borderRadius: 9,
    borderWidth: 1.5,
    alignItems: 'center',
    justifyContent: 'center',
  },
  infoDot: {
    width: 2,
    height: 2,
    borderRadius: 1,
    marginBottom: 2,
  },
  infoStem: {
    width: 2,
    height: 6,
    borderRadius: 1,
  },
  alertIconWrap: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#F3ECDC',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
  },
  alertDot: {
    width: 3,
    height: 3,
    borderRadius: 1.5,
    marginBottom: 2,
  },
  alertLine: {
    width: 2,
    height: 7,
    borderRadius: 1,
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
  headerCopy: {
    flex: 1,
    alignItems: 'center',
    paddingHorizontal: 8,
  },
  brand: {
    fontSize: 11,
    fontWeight: '700',
    color: '#1A4D33',
    letterSpacing: 1.0,
    textTransform: 'uppercase',
  },
  headerTitle: {
    fontSize: 15,
    fontWeight: '800',
    color: '#1A3324',
    marginTop: 2,
    letterSpacing: 0.2,
  },
  headerSubtitle: {
    fontSize: 11,
    color: '#6E8074',
    marginTop: 2,
    textAlign: 'center',
  },
  headerSpacer: {
    width: 44,
  },
  headerDivider: {
    height: 1,
    backgroundColor: '#EBEAE0',
    marginBottom: 16,
  },

  // Base Card
  card: {
    width: '100%',
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    padding: 18,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: '#E6ECE0',
    elevation: 2,
    shadowColor: '#1A4D33',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
  },

  // Section A: Important Alert Card
  alertCard: {
    width: '100%',
    backgroundColor: '#FDFCF6',
    borderRadius: 18,
    padding: 14,
    marginBottom: 14,
    flexDirection: 'row',
    alignItems: 'flex-start',
    borderWidth: 1.5,
    borderColor: '#E7DEC7',
    elevation: 2,
    shadowColor: '#8B6822',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 6,
  },
  alertCopy: {
    flex: 1,
  },
  alertTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: '#8B6822',
    marginBottom: 3,
  },
  alertMessage: {
    fontSize: 12,
    color: '#6B5420',
    lineHeight: 17,
  },

  // Section B: Leaf Condition Card
  conditionRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  cardCategoryLabel: {
    fontSize: 13,
    fontWeight: '700',
    color: '#708375',
    textTransform: 'uppercase',
    letterSpacing: 0.6,
  },
  conditionBadge: {
    backgroundColor: '#FBF3DD',
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#EAD7A6',
    maxWidth: '65%',
    flexShrink: 1,
  },
  conditionBadgeText: {
    fontSize: 13,
    fontWeight: '700',
    color: '#8B6822',
  },
  confidenceSubText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#8B6822',
  },
  confidenceDisclaimer: {
    fontSize: 11,
    color: '#6E8074',
    marginTop: 2,
    lineHeight: 15,
  },
  inlineAiStatusWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F4F7F4',
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 10,
    marginTop: 10,
    gap: 8,
    borderWidth: 1,
    borderColor: '#E2EBDD',
  },
  inlineAiStatusText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#1A4D33',
    flex: 1,
    lineHeight: 16,
  },
  inlineErrorWrap: {
    backgroundColor: '#FDF8F0',
    padding: 12,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#F3E4C8',
    marginTop: 10,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
  },
  inlineErrorText: {
    fontSize: 12,
    color: '#8B6822',
    fontWeight: '600',
    flex: 1,
  },
  inlineRetryButton: {
    backgroundColor: '#1A4D33',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
  },
  inlineRetryButtonText: {
    color: '#FFFFFF',
    fontSize: 12,
    fontWeight: '700',
  },

  // Section C: Spray Guidance
  sectionHeaderRow: {
    marginBottom: 12,
  },
  cardIconHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#163826',
  },
  cardSubtitle: {
    fontSize: 12,
    color: '#65776B',
    marginTop: 2,
  },
  cardBodyText: {
    fontSize: 13,
    color: '#476355',
    lineHeight: 20,
    marginTop: 6,
  },

  stepsContainer: {
    gap: 10,
  },
  stepCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F8FAF5',
    borderRadius: 14,
    padding: 12,
    borderWidth: 1,
    borderColor: '#E4ECE0',
  },
  stepBadge: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#1A4D33',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  stepNumber: {
    fontSize: 11,
    fontWeight: '800',
    color: '#FFFFFF',
  },
  stepText: {
    flex: 1,
    fontSize: 13,
    fontWeight: '600',
    color: '#2A4433',
    lineHeight: 18,
  },

  // Checklist Items (Sections D & E)
  checklistGroup: {
    marginTop: 10,
    gap: 10,
  },
  checkRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  checkIconWrap: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: '#EBF4EC',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
  },
  safetyIconWrap: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: '#EBF4EC',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
  },
  checkText: {
    flex: 1,
    fontSize: 13,
    color: '#3B5243',
    lineHeight: 18,
  },

  // Section G: Voice Guidance
  voiceSection: {
    width: '100%',
    alignItems: 'center',
    marginBottom: 16,
  },
  voiceButton: {
    height: 44,
    paddingHorizontal: 20,
    borderRadius: 22,
    backgroundColor: '#FFFFFF',
    borderWidth: 1.5,
    borderColor: '#1A4D33',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    elevation: 2,
    shadowColor: '#1A4D33',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 6,
  },
  voiceButtonActive: {
    backgroundColor: '#1A4D33',
    borderColor: '#1A4D33',
  },
  voiceButtonText: {
    fontSize: 14,
    fontWeight: '700',
    color: '#1A4D33',
  },
  voiceButtonTextActive: {
    color: '#FFFFFF',
  },

  // Section H: Final CTA
  ctaSection: {
    width: '100%',
    marginBottom: 12,
  },
  primaryCta: {
    width: '100%',
    height: 52,
    borderRadius: 16,
    backgroundColor: '#1A4D33',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#C7A45A',
    elevation: 3,
    shadowColor: '#1A4D33',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.16,
    shadowRadius: 8,
  },
  primaryCtaText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '700',
    letterSpacing: 0.2,
  },
  moreInfoCta: {
    width: '100%',
    height: 48,
    borderRadius: 16,
    backgroundColor: '#FFFFFF',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#D4E0D7',
    marginBottom: 10,
  },
  moreInfoCtaText: {
    color: '#1A4D33',
    fontSize: 14,
    fontWeight: '700',
    letterSpacing: 0.2,
  },
  secondaryCta: {
    width: '100%',
    height: 48,
    borderRadius: 16,
    backgroundColor: '#FFFFFF',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#D4E0D7',
    marginTop: 10,
  },
  secondaryCtaText: {
    color: '#1A4D33',
    fontSize: 14,
    fontWeight: '700',
  },

  // State Card (Loading / Error / Unverified)
  stateContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 20,
  },
  stateCard: {
    width: '100%',
    maxWidth: 420,
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    padding: 24,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#E6ECE0',
    elevation: 2,
    shadowColor: '#1A4D33',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.06,
    shadowRadius: 8,
  },
  loadingText: {
    fontSize: 15,
    fontWeight: '600',
    color: '#2A4433',
    marginTop: 16,
    textAlign: 'center',
  },
  stateTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: '#2A4433',
    marginTop: 14,
    marginBottom: 20,
    textAlign: 'center',
    lineHeight: 22,
  },

  buttonPressed: {
    opacity: 0.86,
    transform: [{ scale: 0.98 }],
  },
});
