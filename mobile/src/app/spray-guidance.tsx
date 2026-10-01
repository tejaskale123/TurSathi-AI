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
import { tokenStore } from '../config/tokenStore';
import {
  fetchTurSprayGuidance,
  RecommendationApiError,
  SprayGuidanceResponse,
} from '../config/recommendationApi';

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
    scanAnotherLeaf: string;
    loadingTitle: string;
    errorTitle: string;
    unverifiedTitle: string;
    tryAgain: string;
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
    scanAnotherLeaf: 'Scan Another Leaf →',
    loadingTitle: 'Preparing spray guidance...',
    errorTitle: 'Verified spray guidance is currently unavailable.',
    unverifiedTitle: 'Verified spray guidance is not available for this condition yet.',
    tryAgain: 'Try Again',
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
    scanAnotherLeaf: 'दुसरे पान स्कॅन करा →',
    loadingTitle: 'फवारणी मार्गदर्शन तयार होत आहे...',
    errorTitle: 'पडताळलेले फवारणी मार्गदर्शन सध्या उपलब्ध नाही.',
    unverifiedTitle: 'या स्थितीसाठी पडताळलेले फवारणी मार्गदर्शन अद्याप उपलब्ध नाही.',
    tryAgain: 'पुन्हा प्रयत्न करा',
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
    scanAnotherLeaf: 'दूसरी पत्ती स्कैन करें →',
    loadingTitle: 'छिड़काव मार्गदर्शन तैयार हो रहा है...',
    errorTitle: 'सत्यापित छिड़काव मार्गदर्शन वर्तमान में उपलब्ध नहीं है।',
    unverifiedTitle: 'इस स्थिति के लिए सत्यापित छिड़काव मार्गदर्शन अभी उपलब्ध नहीं है।',
    tryAgain: 'पुनः प्रयास करें',
  },
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
    confidence?: string;
    severity?: string;
    status?: string;
  }>();

  const diseaseName = params.diseaseName?.trim() || 'Tur Leaf Spot';

  // API State
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isUnverified, setIsUnverified] = useState<boolean>(false);
  const [hasError, setHasError] = useState<boolean>(false);
  const [data, setData] = useState<SprayGuidanceResponse | null>(null);

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
  const loadGuidance = useCallback(async () => {
    setIsLoading(true);
    setHasError(false);
    setIsUnverified(false);

    try {
      const token = await tokenStore.getToken();
      const res = await fetchTurSprayGuidance(diseaseName, token || undefined);
      setData(res);
    } catch (err: any) {
      if (err instanceof RecommendationApiError && err.isNotFound) {
        setIsUnverified(true);
      } else {
        console.warn('[SPRAY GUIDANCE] API Error:', err);
        setHasError(true);
      }
    } finally {
      setIsLoading(false);
    }
  }, [diseaseName]);

  useEffect(() => {
    loadGuidance();
  }, [loadGuidance]);

  // Cleanup speech on unmount
  useEffect(() => {
    return () => {
      try {
        Speech.stop();
      } catch {}
    };
  }, []);

  // Text-to-Speech handler
  const handleToggleVoice = useCallback(() => {
    if (isSpeaking) {
      try {
        Speech.stop();
      } catch {}
      setIsSpeaking(false);
      return;
    }

    const steps = data?.spray_guidance || DEFAULT_SPRAY_STEPS[language] || DEFAULT_SPRAY_STEPS.en;
    const after = data?.after_spraying || DEFAULT_AFTER_SPRAYING[language] || DEFAULT_AFTER_SPRAYING.en;
    const safety = data?.safety_precautions || DEFAULT_SAFETY_PRECAUTIONS[language] || DEFAULT_SAFETY_PRECAUTIONS.en;

    const speechText = [
      ui.headerTitle,
      ui.importantTitle + ': ' + ui.importantMessage,
      ui.sprayGuidanceTitle + ': ' + ui.sprayGuidanceSubtitle + '. ' + steps.join('. '),
      ui.afterSprayingTitle + ': ' + after.join('. '),
      ui.safetyTitle + ': ' + safety.join('. '),
      ui.farmerActionTitle + ': ' + ui.farmerActionMessage,
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
  }, [isSpeaking, data, language, ui]);

  // Navigation handlers
  const handleBack = () => {
    try {
      Speech.stop();
    } catch {}
    router.back();
  };

  const handleScanAnotherLeaf = () => {
    try {
      Speech.stop();
    } catch {}
    router.replace('/scan');
  };

  // Determine dynamic leaf condition badge text
  const conditionStatus = data?.leaf_condition || ui.statusNeedsTreatment;

  // Render Loading State
  if (isLoading) {
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

  // Render Error State
  if (hasError) {
    return (
      <SafeAreaView edges={['top', 'bottom']} style={styles.safeArea}>
        <View style={styles.stateContainer}>
          <View style={styles.stateCard}>
            <Glyph color="#8B6822" name="info" size={24} />
            <Text style={styles.stateTitle}>{ui.errorTitle}</Text>

            <Pressable
              accessibilityRole="button"
              onPress={loadGuidance}
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
    return (
      <SafeAreaView edges={['top', 'bottom']} style={styles.safeArea}>
        <View style={styles.stateContainer}>
          <View style={styles.stateCard}>
            <Glyph color="#8B6822" name="info" size={24} />
            <Text style={styles.stateTitle}>{ui.unverifiedTitle}</Text>

            <Pressable
              accessibilityRole="button"
              onPress={handleScanAnotherLeaf}
              style={({ pressed }) => [styles.primaryCta, pressed && styles.buttonPressed]}
            >
              <Text style={styles.primaryCtaText}>{ui.scanAnotherLeaf}</Text>
            </Pressable>
          </View>
        </View>
      </SafeAreaView>
    );
  }

  // Dynamic arrays from backend data or localized default fallback steps
  const stepsList = data?.spray_guidance || DEFAULT_SPRAY_STEPS[language] || DEFAULT_SPRAY_STEPS.en;
  const afterList = data?.after_spraying || DEFAULT_AFTER_SPRAYING[language] || DEFAULT_AFTER_SPRAYING.en;
  const safetyList = data?.safety_precautions || DEFAULT_SAFETY_PRECAUTIONS[language] || DEFAULT_SAFETY_PRECAUTIONS.en;

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
              <Text style={styles.headerTitle}>{ui.headerTitle}</Text>
              <Text style={styles.headerSubtitle}>{ui.headerSubtitle}</Text>
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
                {data?.important_alert || ui.importantMessage}
              </Text>
            </View>
          </View>

          {/* SECTION B: LEAF CONDITION */}
          <View style={styles.card}>
            <View style={styles.conditionRow}>
              <Text style={styles.cardCategoryLabel}>{ui.leafConditionTitle}</Text>
              <View style={styles.conditionBadge}>
                <Text style={styles.conditionBadgeText}>{conditionStatus}</Text>
              </View>
            </View>
          </View>

          {/* SECTION C: SPRAY GUIDANCE */}
          <View style={styles.card}>
            <View style={styles.sectionHeaderRow}>
              <Text style={styles.cardTitle}>{ui.sprayGuidanceTitle}</Text>
              <Text style={styles.cardSubtitle}>{ui.sprayGuidanceSubtitle}</Text>
            </View>

            <View style={styles.stepsContainer}>
              {stepsList.map((stepText, idx) => {
                // Parse "01 Step" if prefixed, otherwise format index
                let numStr = String(idx + 1).padStart(2, '0');
                let bodyText = stepText;
                if (/^\d{2}\s+/.test(stepText)) {
                  numStr = stepText.substring(0, 2);
                  bodyText = stepText.substring(3).trim();
                }

                return (
                  <View key={idx} style={styles.stepCard}>
                    <View style={styles.stepBadge}>
                      <Text style={styles.stepNumber}>{numStr}</Text>
                    </View>
                    <Text style={styles.stepText}>{bodyText}</Text>
                  </View>
                );
              })}
            </View>
          </View>

          {/* SECTION D: AFTER SPRAYING */}
          <View style={styles.card}>
            <Text style={styles.cardTitle}>{ui.afterSprayingTitle}</Text>
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
              {data?.farmer_action || ui.farmerActionMessage}
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
  },
  conditionBadgeText: {
    fontSize: 13,
    fontWeight: '700',
    color: '#8B6822',
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
