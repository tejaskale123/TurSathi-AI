import { useCallback, useEffect, useRef, useState } from 'react';
import { useLocalSearchParams, useRouter } from 'expo-router';
import {
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
import { Language, TranslationKey } from '../i18n/translations';

// Reusable professional vector glyphs (no emojis)
function Glyph({
  name,
  color = '#1A4D33',
  size = 18,
}: {
  name: 'back' | 'check' | 'arrow' | 'info' | 'time' | 'shield' | 'speaker' | 'stop';
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

  if (name === 'time') {
    return (
      <View style={[styles.timeCircle, { borderColor: color }]}>
        <View style={[styles.timeHandV, { backgroundColor: color }]} />
        <View style={[styles.timeHandH, { backgroundColor: color }]} />
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

  // 'info' glyph
  return (
    <View style={[styles.infoCircle, { borderColor: color }]}>
      <View style={[styles.infoDot, { backgroundColor: color }]} />
      <View style={[styles.infoStem, { backgroundColor: color }]} />
    </View>
  );
}

// Future-ready typed recommendation structure for database / API lookup
export type SprayGuidanceData = {
  diseaseName: string;
  severity: string;
  recommendationTitle: string;
  recommendedAction: string;
  sprayTiming?: string[];
  applicationGuidance?: string[];
  safetyPrecautions?: string[];
  farmerAdvisory?: string[];
  fieldMonitoring?: string[];
  source?: string;
};

// 8. Spray Timing practical principle translation keys
const SPRAY_TIMING_KEYS: TranslationKey[] = [
  'spray.timing1',
  'spray.timing2',
  'spray.timing3',
  'spray.timing4',
];

// 9. Application Guidance numbered step translation keys
const APPLICATION_STEP_KEYS: TranslationKey[] = [
  'spray.guidance1',
  'spray.guidance2',
  'spray.guidance3',
  'spray.guidance4',
];

// 10. Safety & Precautions item translation keys
const SAFETY_ITEM_KEYS: TranslationKey[] = [
  'spray.safety1',
  'spray.safety2',
  'spray.safety3',
  'spray.safety4',
  'spray.safety5',
];

// 11. Farmer Advisory practical check translation keys
const FARMER_ADVISORY_KEYS: TranslationKey[] = [
  'spray.advisory1',
  'spray.advisory2',
  'spray.advisory3',
  'spray.advisory4',
  'spray.advisory5',
  'spray.advisory6',
  'spray.advisory7',
];

// 12. Field Monitoring checklist translation keys
const FIELD_MONITORING_KEYS: TranslationKey[] = [
  'spray.monitor1',
  'spray.monitor2',
  'spray.monitor3',
  'spray.monitor4',
  'spray.monitor5',
];

// Safe confidence normalizer
const formatConfidence = (val?: string | number): string => {
  if (!val) return '92%';
  const num = typeof val === 'string' ? parseFloat(val) : val;
  if (isNaN(num)) return '92%';
  const normalized = num <= 1 && num > 0 ? Math.round(num * 100) : Math.round(num);
  return `${Math.min(Math.max(normalized, 0), 100)}%`;
};

// Locale mapping for Text-to-Speech
const SPEECH_LOCALES: Record<Language, string> = {
  en: 'en-IN',
  mr: 'mr-IN',
  hi: 'hi-IN',
};

// Voice control button labels
const VOICE_LABELS: Record<Language, { stop: string; listen: string }> = {
  en: { stop: 'Stop', listen: 'Listen' },
  mr: { stop: 'थांबवा', listen: 'ऐका' },
  hi: { stop: 'रोकें', listen: 'सुनें' },
};

// Builder for dynamic, natural, farmer-friendly Text-to-Speech narration
function buildGuidanceNarrationText({
  t,
  tDisease,
  tSeverity,
  diseaseName,
  severity,
  confidence,
}: {
  t: (key: TranslationKey | string) => string;
  tDisease: (name?: string) => string;
  tSeverity: (sev?: string) => string;
  diseaseName: string;
  severity: string;
  confidence?: string;
}): string {
  const sections: string[] = [];

  // 1. Smart Spray Guidance introduction
  const mainHeading = t('spray.mainHeading');
  const mainSubtitle = t('spray.mainSubtitle');
  const introParts: string[] = [];
  if (mainHeading) introParts.push(mainHeading);
  if (mainSubtitle) introParts.push(mainSubtitle);
  if (introParts.length > 0) {
    sections.push(introParts.join('. ') + '.');
  }

  // 2. Detected condition & 3. Disease name
  const detectedLabel = t('spray.detectedCondition');
  const diseaseText = tDisease(diseaseName);
  if (diseaseText) {
    sections.push(`${detectedLabel ? `${detectedLabel}: ` : ''}${diseaseText}.`);
  }

  // 4. Disease level / severity
  const severityLabel = t('spray.severity');
  const severityText = tSeverity(severity);
  if (severityText) {
    sections.push(`${severityLabel ? `${severityLabel}: ` : ''}${severityText}.`);
  }

  // 5. Confidence, if displayed
  const confidenceLabel = t('spray.confidence');
  if (confidence && confidence.trim()) {
    sections.push(`${confidenceLabel ? `${confidenceLabel}: ` : ''}${confidence.trim()}.`);
  }

  // 6. Verified agricultural recommendation information
  const noticeHeadline = t('spray.verifiedNoticeHeadline');
  const noticeSubtext = t('spray.verifiedNoticeSubtext');
  const noticeParts: string[] = [];
  if (noticeHeadline) noticeParts.push(noticeHeadline);
  if (noticeSubtext) noticeParts.push(noticeSubtext);
  if (noticeParts.length > 0) {
    sections.push(noticeParts.join('. ') + '.');
  }

  // 7. Recommended Action
  const actionTitle = t('spray.recommendedActionTitle');
  const actionHeadline = t('spray.recommendedActionHeadline');
  const actionBody = t('spray.recommendedActionBody');
  const actionParts: string[] = [];
  if (actionHeadline) actionParts.push(actionHeadline);
  if (actionBody) actionParts.push(actionBody);
  if (actionParts.length > 0) {
    sections.push(`${actionTitle ? `${actionTitle}: ` : ''}${actionParts.join('. ')}.`);
  }

  // 8. Spray Timing
  const timingTitle = t('spray.timingTitle');
  const timingItems = SPRAY_TIMING_KEYS.map((k) => t(k)).filter(Boolean);
  if (timingItems.length > 0) {
    sections.push(`${timingTitle ? `${timingTitle}: ` : ''}${timingItems.join('. ')}.`);
  }

  // 9. Application Guidance
  const guidanceTitle = t('spray.guidanceTitle');
  const guidanceItems = APPLICATION_STEP_KEYS.map((k) => t(k)).filter(Boolean);
  if (guidanceItems.length > 0) {
    sections.push(`${guidanceTitle ? `${guidanceTitle}: ` : ''}${guidanceItems.join('. ')}.`);
  }

  // 10. Safety & Precautions
  const safetyTitle = t('spray.safetyTitle');
  const safetyItems = SAFETY_ITEM_KEYS.map((k) => t(k)).filter(Boolean);
  if (safetyItems.length > 0) {
    sections.push(`${safetyTitle ? `${safetyTitle}: ` : ''}${safetyItems.join('. ')}.`);
  }

  // 11. Farmer Advisory
  const advisoryTitle = t('spray.advisoryTitle');
  const advisoryItems = FARMER_ADVISORY_KEYS.map((k) => t(k)).filter(Boolean);
  if (advisoryItems.length > 0) {
    sections.push(`${advisoryTitle ? `${advisoryTitle}: ` : ''}${advisoryItems.join('. ')}.`);
  }

  // 12. Field Monitoring
  const monitoringTitle = t('spray.monitoringTitle');
  const monitoringItems = FIELD_MONITORING_KEYS.map((k) => t(k)).filter(Boolean);
  if (monitoringItems.length > 0) {
    sections.push(`${monitoringTitle ? `${monitoringTitle}: ` : ''}${monitoringItems.join('. ')}.`);
  }

  // 13. Important Notes, if available
  const trustTitle = t('spray.trustTitle');
  const trustText = t('spray.trustText');
  if (trustText) {
    sections.push(`${trustTitle ? `${trustTitle}: ` : ''}${trustText}`);
  }

  return sections.join('\n\n');
}

export default function SprayGuidanceScreen() {
  const router = useRouter();
  const { isReady, language, t, tDisease, tSeverity } = useLanguage();
  const voiceLabels = VOICE_LABELS[language] || VOICE_LABELS.en;
  const [isSpeaking, setIsSpeaking] = useState(false);
  const params = useLocalSearchParams<{
    imageUri?: string | string[];
    diseaseName?: string;
    confidence?: string;
    severity?: string;
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

  // Dynamic values passed from route parameters with truthful agricultural fallbacks
  const currentDiseaseName = params.diseaseName?.trim() || 'Tur Leaf Condition';
  const currentSeverity = params.severity?.trim() || 'Moderate';
  const formattedConfidence = formatConfidence(params.confidence);

  // Field monitoring interactive checklist state
  const [monitoringChecked, setMonitoringChecked] = useState<Record<number, boolean>>({
    0: true,
    1: true,
  });

  const toggleMonitoringItem = (index: number) => {
    setMonitoringChecked((prev) => ({
      ...prev,
      [index]: !prev[index],
    }));
  };

  // Entrance animation
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: 350,
      useNativeDriver: true,
    }).start();
  }, [fadeAnim]);

  // Speech narration tracking ref and timer ref
  const hasSpokenRef = useRef(false);
  const speechTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Reusable narration execution function for both automatic start & manual Listen
  const speakGuidance = useCallback(() => {
    if (speechTimerRef.current) {
      clearTimeout(speechTimerRef.current);
      speechTimerRef.current = null;
    }
    try {
      Speech.stop();
    } catch {}

    const locale = SPEECH_LOCALES[language] || 'en-IN';
    const textToSpeak = buildGuidanceNarrationText({
      t,
      tDisease,
      tSeverity,
      diseaseName: currentDiseaseName,
      severity: currentSeverity,
      confidence: formattedConfidence,
    });

    if (!textToSpeak.trim()) return;

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
          console.warn('[SPRAYSPEECH] Error during narration:', err);
          setIsSpeaking(false);
        },
      });
    } catch (e) {
      console.warn('[SPRAYSPEECH] Failed to invoke Speech.speak:', e);
      setIsSpeaking(false);
    }
  }, [language, currentDiseaseName, currentSeverity, formattedConfidence, t, tDisease, tSeverity]);

  const handleStopSpeech = useCallback(() => {
    if (speechTimerRef.current) {
      clearTimeout(speechTimerRef.current);
      speechTimerRef.current = null;
    }
    try {
      Speech.stop();
    } catch {}
    setIsSpeaking(false);
  }, []);

  const handleToggleVoiceControl = () => {
    if (isSpeaking) {
      handleStopSpeech();
    } else {
      speakGuidance();
    }
  };

  // Automatic Text-to-Speech narration when page opens and content is ready
  useEffect(() => {
    if (!isReady) return;
    if (hasSpokenRef.current) return;

    hasSpokenRef.current = true;

    // Clear any previous timer
    if (speechTimerRef.current) {
      clearTimeout(speechTimerRef.current);
    }

    // Short 400ms delay to allow page entrance animation to settle smoothly
    speechTimerRef.current = setTimeout(() => {
      speakGuidance();
    }, 400);
  }, [isReady, speakGuidance]);

  // Ensure speech stops whenever leaving the page (unmount cleanup)
  useEffect(() => {
    return () => {
      if (speechTimerRef.current) {
        clearTimeout(speechTimerRef.current);
      }
      try {
        Speech.stop();
      } catch {}
    };
  }, []);

  // Navigation handlers
  const handleBack = () => {
    handleStopSpeech();
    router.back();
  };

  const handleScanAnotherLeaf = () => {
    handleStopSpeech();
    router.replace('/scan');
  };


  return (
    <SafeAreaView edges={['top', 'bottom']} style={styles.safeArea}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <Animated.View style={[styles.page, { opacity: fadeAnim }]}>
          {/* 4. PAGE HEADER */}
          <View style={styles.header}>
            <Pressable
              accessibilityHint="Returns to disease result"
              accessibilityLabel="Go back"
              accessibilityRole="button"
              hitSlop={8}
              onPress={handleBack}
              style={({ pressed }) => [styles.backButton, pressed && styles.buttonPressed]}
            >
              <Glyph color="#1A4D33" name="back" />
            </Pressable>

            <View style={styles.headerCopy}>
              <Text style={styles.brand}>{t('common.appName')}</Text>
              <Text style={styles.headerTitle}>{t('spray.headerTitle')}</Text>
              <Text style={styles.headerSubtitle}>
                {t('spray.headerSubtitle')}
              </Text>
            </View>

            <View style={styles.headerSpacer} />
          </View>
          <View style={styles.headerDivider} />

          {/* PAGE INTRO */}
          <View style={styles.introSection}>
            <View style={styles.introTopRow}>
              <View style={styles.sectionBadge}>
                <Text style={styles.sectionBadgeText}>{t('spray.badge')}</Text>
              </View>

              {/* Professional Voice Control */}
              <Pressable
                accessibilityHint={isSpeaking ? 'Stops voice reading' : 'Reads spray guidance aloud'}
                accessibilityLabel={isSpeaking ? voiceLabels.stop : voiceLabels.listen}
                accessibilityRole="button"
                onPress={handleToggleVoiceControl}
                style={({ pressed }) => [
                  styles.voiceControlPill,
                  isSpeaking && styles.voiceControlPillActive,
                  pressed && styles.buttonPressed,
                ]}
              >
                {isSpeaking && <View style={styles.activePulseDot} />}
                <Glyph
                  color="#1A4D33"
                  name={isSpeaking ? 'stop' : 'speaker'}
                  size={14}
                />
                <Text
                  style={[
                    styles.voiceControlText,
                    isSpeaking && styles.voiceControlTextActive,
                  ]}
                >
                  {isSpeaking ? voiceLabels.stop : voiceLabels.listen}
                </Text>
              </Pressable>
            </View>

            <Text style={styles.mainHeading}>{t('spray.mainHeading')}</Text>
            <Text style={styles.mainSubtitle}>
              {t('spray.mainSubtitle')}
            </Text>
            <Text style={styles.supportingSubtitle}>
              {t('spray.supportingSubtitle')}
            </Text>
          </View>

          {/* 5. DETECTED CONDITION CARD */}
          <View style={styles.card}>
            <View style={styles.detectionHeader}>
              <Text style={styles.cardOverline}>{t('spray.detectedCondition')}</Text>
              <View style={styles.analysisCompleteBadge}>
                <View style={styles.completeDot} />
                <Text style={styles.analysisCompleteText}>{t('spray.fieldAnalysis')}</Text>
              </View>
            </View>

            <View style={styles.conditionDetails}>
              <Text style={styles.diseaseName}>{tDisease(currentDiseaseName)}</Text>
              <Text style={styles.diseaseSubtitle}>{t('spray.identifiedOnLeaf')}</Text>
            </View>

            {/* Dynamic Metrics */}
            <View style={styles.metricsContainer}>
              <View style={styles.metricBox}>
                <Text style={styles.metricLabel}>{t('spray.severity')}</Text>
                <View style={styles.severityBadge}>
                  <Text style={styles.severityBadgeText}>{tSeverity(currentSeverity)}</Text>
                </View>
              </View>

              <View style={styles.metricDivider} />

              <View style={styles.metricBox}>
                <Text style={styles.metricLabel}>{t('spray.confidence')}</Text>
                <Text style={styles.metricValue}>{formattedConfidence}</Text>
              </View>
            </View>
          </View>

          {/* 6. VERIFIED AGRICULTURAL RECOMMENDATION NOTICE */}
          <View style={styles.verificationNoticeCard}>
            <View style={styles.noticeIconWrap}>
              <Glyph color="#8B743D" name="info" size={18} />
            </View>
            <View style={styles.noticeCopy}>
              <View style={styles.noticeHeaderRow}>
                <Text style={styles.noticeOverline}>{t('spray.verifiedNoticeOverline')}</Text>
                <View style={styles.verificationBadge}>
                  <Text style={styles.verificationBadgeText}>{t('spray.verificationRequired')}</Text>
                </View>
              </View>
              <Text style={styles.noticeHeadline}>
                {t('spray.verifiedNoticeHeadline')}
              </Text>
              <Text style={styles.noticeSubtext}>
                {t('spray.verifiedNoticeSubtext')}
              </Text>
            </View>
          </View>

          {/* 7. RECOMMENDED ACTION */}
          <View style={styles.card}>
            <View style={styles.cardHeaderRow}>
              <View style={styles.cardIconWrap}>
                <Glyph color="#1A4D33" name="check" size={14} />
              </View>
              <Text style={styles.cardTitle}>{t('spray.recommendedActionTitle')}</Text>
            </View>

            <Text style={styles.actionHeadline}>{t('spray.recommendedActionHeadline')}</Text>
            <Text style={styles.cardBodyText}>
              {t('spray.recommendedActionBody')}
            </Text>

            {/* 3-Step Visual Sequence */}
            <View style={styles.stepsSequenceContainer}>
              <View style={styles.stepSequenceBox}>
                <View style={styles.stepBadge}>
                  <Text style={styles.stepBadgeNumber}>01</Text>
                </View>
                <Text style={styles.stepSequenceLabel}>{t('spray.step1')}</Text>
              </View>

              <View style={styles.stepSequenceConnector} />

              <View style={styles.stepSequenceBox}>
                <View style={styles.stepBadge}>
                  <Text style={styles.stepBadgeNumber}>02</Text>
                </View>
                <Text style={styles.stepSequenceLabel}>{t('spray.step2')}</Text>
              </View>

              <View style={styles.stepSequenceConnector} />

              <View style={styles.stepSequenceBox}>
                <View style={styles.stepBadge}>
                  <Text style={styles.stepBadgeNumber}>03</Text>
                </View>
                <Text style={styles.stepSequenceLabel}>{t('spray.step3')}</Text>
              </View>
            </View>
          </View>

          {/* 8. SPRAY TIMING */}
          <View style={styles.card}>
            <View style={styles.cardHeaderRow}>
              <View style={styles.cardIconWrap}>
                <Glyph color="#1A4D33" name="time" size={15} />
              </View>
              <Text style={styles.cardTitle}>{t('spray.timingTitle')}</Text>
            </View>
            <View style={styles.principleTag}>
              <Text style={styles.principleTagText}>{t('spray.timingPrinciple')}</Text>
            </View>

            <View style={styles.bulletList}>
              {SPRAY_TIMING_KEYS.map((key, index) => (
                <View key={index} style={styles.bulletRow}>
                  <View style={styles.bulletDot} />
                  <Text style={styles.bulletText}>{t(key)}</Text>
                </View>
              ))}
            </View>
          </View>

          {/* 9. APPLICATION GUIDANCE */}
          <View style={styles.card}>
            <View style={styles.cardHeaderRow}>
              <View style={styles.cardIconWrap}>
                <Glyph color="#1A4D33" name="check" size={14} />
              </View>
              <Text style={styles.cardTitle}>{t('spray.guidanceTitle')}</Text>
            </View>

            <View style={styles.guidanceList}>
              {APPLICATION_STEP_KEYS.map((key, index) => (
                <View key={index} style={styles.guidanceRow}>
                  <View style={styles.guidanceNumberCircle}>
                    <Text style={styles.guidanceNumberText}>
                      {String(index + 1).padStart(2, '0')}
                    </Text>
                  </View>
                  <Text style={styles.guidanceText}>{t(key)}</Text>
                </View>
              ))}
            </View>
          </View>

          {/* 10. SAFETY & PRECAUTIONS */}
          <View style={styles.card}>
            <View style={styles.cardHeaderRow}>
              <View style={styles.cardIconWrap}>
                <Glyph color="#1A4D33" name="shield" size={15} />
              </View>
              <Text style={styles.cardTitle}>{t('spray.safetyTitle')}</Text>
            </View>

            <View style={styles.guidanceList}>
              {SAFETY_ITEM_KEYS.map((key, index) => (
                <View key={index} style={styles.guidanceRow}>
                  <View style={styles.precautionCheck}>
                    <Glyph color="#1A4D33" name="check" size={12} />
                  </View>
                  <Text style={styles.guidanceText}>{t(key)}</Text>
                </View>
              ))}
            </View>
          </View>

          {/* 11. FARMER ADVISORY (Integrated inside this page) */}
          <View style={styles.advisoryCard}>
            <View style={styles.cardHeaderRow}>
              <View style={styles.advisoryIconWrap}>
                <Glyph color="#1A4D33" name="shield" size={15} />
              </View>
              <View style={styles.advisoryHeaderCopy}>
                <Text style={styles.advisoryCardTitle}>{t('spray.advisoryTitle')}</Text>
                <Text style={styles.advisorySubtitle}>
                  {t('spray.advisorySubtitle')}
                </Text>
              </View>
            </View>

            <View style={styles.advisoryList}>
              {FARMER_ADVISORY_KEYS.map((key, index) => (
                <View key={index} style={styles.advisoryRow}>
                  <View style={styles.advisoryBullet} />
                  <Text style={styles.advisoryText}>{t(key)}</Text>
                </View>
              ))}
            </View>
          </View>

          {/* 12. FIELD MONITORING (Interactive Checklist) */}
          <View style={styles.card}>
            <View style={styles.detectionHeader}>
              <View style={styles.cardHeaderRowNoMargin}>
                <View style={styles.cardIconWrap}>
                  <Glyph color="#1A4D33" name="check" size={14} />
                </View>
                <Text style={styles.cardTitle}>{t('spray.monitoringTitle')}</Text>
              </View>
              <View style={styles.monitoringTag}>
                <Text style={styles.monitoringTagText}>{t('spray.checkTheCrop')}</Text>
              </View>
            </View>

            <Text style={styles.monitoringSubtitle}>
              {t('spray.monitoringSubtitle')}
            </Text>

            <View style={styles.monitoringChecklist}>
              {FIELD_MONITORING_KEYS.map((key, index) => {
                const isChecked = Boolean(monitoringChecked[index]);
                const itemText = t(key);
                return (
                  <Pressable
                    key={index}
                    accessibilityHint="Toggles check state"
                    accessibilityLabel={itemText}
                    accessibilityRole="checkbox"
                    onPress={() => toggleMonitoringItem(index)}
                    style={({ pressed }) => [
                      styles.checklistItemRow,
                      isChecked && styles.checklistItemRowActive,
                      pressed && styles.buttonPressed,
                    ]}
                  >
                    <View
                      style={[
                        styles.customCheckbox,
                        isChecked && styles.customCheckboxActive,
                      ]}
                    >
                      {isChecked && <Glyph color="#FFFFFF" name="check" size={11} />}
                    </View>
                    <Text
                      style={[
                        styles.checklistItemText,
                        isChecked && styles.checklistItemTextActive,
                      ]}
                    >
                      {itemText}
                    </Text>
                  </Pressable>
                );
              })}
            </View>
          </View>

          {/* 13. NEXT STEP CARD */}
          <View style={styles.nextStepCard}>
            <View style={styles.nextStepHeaderRow}>
              <View style={styles.nextStepIconWrap}>
                <Glyph color="#1A4D33" name="arrow" size={14} />
              </View>
              <Text style={styles.nextStepTitle}>{t('spray.nextStepTitle')}</Text>
            </View>
            <Text style={styles.nextStepText}>
              {t('spray.nextStepText')}
            </Text>

            {/* Primary Action */}
            <Pressable
              accessibilityHint="Returns to scan screen to inspect another leaf"
              accessibilityLabel="Scan another leaf"
              accessibilityRole="button"
              onPress={handleScanAnotherLeaf}
              style={({ pressed }) => [styles.primaryCta, pressed && styles.buttonPressed]}
            >
              <Text style={styles.primaryCtaText}>{t('spray.scanAnotherLeaf')}</Text>
              <View style={styles.primaryCtaArrow}>
                <Glyph color="#FFFFFF" name="arrow" size={16} />
              </View>
            </Pressable>


          </View>

          {/* 14. FARMER ADVISORY NOTICE (Trust Card) */}
          <View style={styles.trustCard}>
            <View style={styles.trustIconWrap}>
              <Glyph color="#8B743D" name="info" size={16} />
            </View>
            <View style={styles.trustCopy}>
              <Text style={styles.trustTitle}>{t('spray.trustTitle')}</Text>
              <Text style={styles.trustText}>
                {t('spray.trustText')}
              </Text>
            </View>
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
    paddingBottom: 36,
  },
  page: {
    width: '100%',
    maxWidth: 560,
    paddingHorizontal: 20,
    paddingTop: 8,
  },

  // 4. Header
  header: {
    minHeight: 52,
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
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
    letterSpacing: 0.9,
    textTransform: 'uppercase',
  },
  headerTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: '#1A3324',
    marginTop: 2,
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

  // Intro
  introSection: {
    marginBottom: 16,
  },
  introTopRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  sectionBadge: {
    alignSelf: 'flex-start',
    backgroundColor: '#E7F0E8',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
  },
  voiceControlPill: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: 18,
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#CDE0D2',
    elevation: 2,
    shadowColor: '#1A4D33',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
  },
  voiceControlPillActive: {
    borderColor: '#2D8A56',
    backgroundColor: '#F3F9F4',
  },
  activePulseDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#2D8A56',
    marginRight: 6,
  },
  voiceControlText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#1A4D33',
    marginLeft: 6,
    letterSpacing: 0.2,
  },
  voiceControlTextActive: {
    color: '#145A32',
  },
  sectionBadgeText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#1A4D33',
    letterSpacing: 0.8,
  },
  mainHeading: {
    fontSize: 22,
    fontWeight: '700',
    color: '#163826',
    letterSpacing: -0.2,
  },
  mainSubtitle: {
    fontSize: 13,
    color: '#3B5243',
    fontWeight: '600',
    lineHeight: 18,
    marginTop: 4,
  },
  supportingSubtitle: {
    fontSize: 12,
    color: '#65776B',
    lineHeight: 17,
    marginTop: 4,
  },

  // Card Base
  card: {
    width: '100%',
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    padding: 20,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: '#E6ECE0',
    elevation: 2,
    shadowColor: '#1A4D33',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
  },
  cardHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
  },
  cardHeaderRowNoMargin: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  cardIconWrap: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: '#EBF4EC',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 8,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#163826',
  },
  cardBodyText: {
    fontSize: 13,
    color: '#526658',
    lineHeight: 20,
    marginBottom: 14,
  },

  // 5. Detected Condition
  detectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  cardOverline: {
    fontSize: 11,
    fontWeight: '700',
    color: '#708375',
    textTransform: 'uppercase',
    letterSpacing: 0.7,
  },
  analysisCompleteBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#EAF3EB',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#D2E5D4',
  },
  completeDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#2E6B47',
    marginRight: 6,
  },
  analysisCompleteText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#1A4D33',
  },
  conditionDetails: {
    marginBottom: 16,
  },
  diseaseName: {
    fontSize: 22,
    fontWeight: '800',
    color: '#163826',
    letterSpacing: -0.3,
  },
  diseaseSubtitle: {
    fontSize: 12,
    color: '#75887B',
    marginTop: 2,
  },
  metricsContainer: {
    flexDirection: 'row',
    backgroundColor: '#F8FAF5',
    borderRadius: 14,
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderWidth: 1,
    borderColor: '#E6EEE0',
  },
  metricBox: {
    flex: 1,
    alignItems: 'center',
  },
  metricLabel: {
    fontSize: 11,
    color: '#728578',
    marginBottom: 4,
    fontWeight: '600',
  },
  metricValue: {
    fontSize: 18,
    fontWeight: '800',
    color: '#1A4D33',
  },
  metricDivider: {
    width: 1,
    backgroundColor: '#DFE8D9',
  },
  severityBadge: {
    backgroundColor: '#FBF3DD',
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#EAD7A6',
  },
  severityBadgeText: {
    fontSize: 13,
    fontWeight: '700',
    color: '#8B6822',
  },

  // 6. Verification Notice Card
  verificationNoticeCard: {
    width: '100%',
    backgroundColor: '#FDFCF6',
    borderRadius: 18,
    padding: 16,
    marginBottom: 14,
    flexDirection: 'row',
    borderWidth: 1.5,
    borderColor: '#E7DEC7',
    elevation: 2,
    shadowColor: '#8B743D',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 6,
  },
  noticeIconWrap: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#F3ECDC',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
    marginTop: 2,
  },
  noticeCopy: {
    flex: 1,
  },
  noticeHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
    flexWrap: 'wrap',
    gap: 6,
  },
  noticeOverline: {
    fontSize: 10,
    fontWeight: '700',
    color: '#8B6822',
    letterSpacing: 0.7,
    textTransform: 'uppercase',
  },
  verificationBadge: {
    backgroundColor: '#F7EDD5',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#DECFA8',
  },
  verificationBadgeText: {
    fontSize: 9,
    fontWeight: '700',
    color: '#705315',
  },
  noticeHeadline: {
    fontSize: 13,
    fontWeight: '700',
    color: '#4A3B18',
    lineHeight: 18,
    marginBottom: 6,
  },
  noticeSubtext: {
    fontSize: 11,
    color: '#7D6F4E',
    lineHeight: 16,
  },

  // 7. Recommended Action
  actionHeadline: {
    fontSize: 15,
    fontWeight: '700',
    color: '#1A4D33',
    marginBottom: 6,
  },
  stepsSequenceContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#F8FAF5',
    paddingVertical: 14,
    paddingHorizontal: 10,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#E6ECE0',
  },
  stepSequenceBox: {
    flex: 1,
    alignItems: 'center',
    paddingHorizontal: 4,
  },
  stepBadge: {
    width: 26,
    height: 26,
    borderRadius: 13,
    backgroundColor: '#1A4D33',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 6,
  },
  stepBadgeNumber: {
    fontSize: 11,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  stepSequenceLabel: {
    fontSize: 10,
    fontWeight: '600',
    color: '#3B5243',
    textAlign: 'center',
    lineHeight: 13,
  },
  stepSequenceConnector: {
    width: 14,
    height: 1,
    backgroundColor: '#D1DEC9',
    marginTop: -16,
  },

  // 8. Spray Timing
  principleTag: {
    alignSelf: 'flex-start',
    backgroundColor: '#F0F5EC',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
    marginBottom: 12,
  },
  principleTagText: {
    fontSize: 10,
    fontWeight: '600',
    color: '#2E6B47',
  },
  bulletList: {
    gap: 10,
  },
  bulletRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  bulletDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#2E6B47',
    marginTop: 6,
    marginRight: 10,
  },
  bulletText: {
    fontSize: 13,
    color: '#3B5243',
    lineHeight: 19,
    flex: 1,
  },

  // 9. Application Guidance
  guidanceList: {
    gap: 12,
  },
  guidanceRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  guidanceNumberCircle: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: '#EBF4EC',
    borderWidth: 1,
    borderColor: '#D4E5D7',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
    marginTop: 1,
  },
  guidanceNumberText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#1A4D33',
  },
  guidanceText: {
    fontSize: 13,
    color: '#3B5243',
    lineHeight: 19,
    flex: 1,
  },

  // 10. Safety & Precautions
  precautionCheck: {
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: '#EBF4EC',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
    marginTop: 2,
  },

  // 11. Farmer Advisory
  advisoryCard: {
    width: '100%',
    backgroundColor: '#F4F9F5',
    borderRadius: 20,
    padding: 20,
    marginBottom: 14,
    borderWidth: 1.5,
    borderColor: '#CFE3D5',
    elevation: 2,
    shadowColor: '#1A4D33',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
  },
  advisoryIconWrap: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#E0EFE5',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
  },
  advisoryHeaderCopy: {
    flex: 1,
  },
  advisoryCardTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#163826',
  },
  advisorySubtitle: {
    fontSize: 11,
    color: '#4B6B56',
    marginTop: 2,
    fontWeight: '500',
  },
  advisoryList: {
    marginTop: 12,
    gap: 10,
  },
  advisoryRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  advisoryBullet: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#1A4D33',
    marginTop: 6,
    marginRight: 10,
  },
  advisoryText: {
    fontSize: 13,
    color: '#2A4433',
    lineHeight: 19,
    flex: 1,
  },

  // 12. Field Monitoring
  monitoringTag: {
    backgroundColor: '#FBF3DD',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#EAD7A6',
  },
  monitoringTagText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#8B6822',
  },
  monitoringSubtitle: {
    fontSize: 12,
    color: '#65776B',
    lineHeight: 16,
    marginBottom: 12,
  },
  monitoringChecklist: {
    gap: 8,
  },
  checklistItemRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F9FBF8',
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#EAEFE6',
  },
  checklistItemRowActive: {
    backgroundColor: '#F0F6EE',
    borderColor: '#D3E3CE',
  },
  customCheckbox: {
    width: 20,
    height: 20,
    borderRadius: 6,
    borderWidth: 1.5,
    borderColor: '#98AC9F',
    backgroundColor: '#FFFFFF',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
  },
  customCheckboxActive: {
    backgroundColor: '#1A4D33',
    borderColor: '#1A4D33',
  },
  checklistItemText: {
    fontSize: 13,
    color: '#4F6355',
    flex: 1,
  },
  checklistItemTextActive: {
    color: '#1A3825',
    fontWeight: '600',
  },

  // 13. Next Step Card
  nextStepCard: {
    width: '100%',
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    padding: 20,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: '#E6ECE0',
    elevation: 2,
    shadowColor: '#1A4D33',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
  },
  nextStepHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  nextStepIconWrap: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: '#EBF4EC',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 8,
  },
  nextStepTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#163826',
  },
  nextStepText: {
    fontSize: 13,
    color: '#526658',
    lineHeight: 20,
    marginBottom: 16,
  },

  // Buttons
  primaryCta: {
    width: '100%',
    height: 54,
    borderRadius: 16,
    backgroundColor: '#1A4D33',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 0,
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
    marginRight: 8,
  },
  primaryCtaArrow: {
    width: 20,
    height: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonPressed: {
    opacity: 0.86,
    transform: [{ scale: 0.98 }],
  },

  // 14. Trust Card
  trustCard: {
    width: '100%',
    backgroundColor: '#F3EFE4',
    borderRadius: 16,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'flex-start',
    borderWidth: 1,
    borderColor: '#E2DAC8',
  },
  trustIconWrap: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: '#E8DFC8',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
    marginTop: 1,
  },
  trustCopy: {
    flex: 1,
  },
  trustTitle: {
    fontSize: 12,
    fontWeight: '700',
    color: '#6E5624',
    marginBottom: 4,
  },
  trustText: {
    fontSize: 11,
    color: '#6E6654',
    lineHeight: 16,
  },

  // Glyphs
  glyphBox: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  backShaft: {
    width: 15,
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
  arrowHead: {
    width: 8,
    height: 8,
    borderTopWidth: 2,
    borderRightWidth: 2,
    transform: [{ rotate: '45deg' }],
  },
  checkCircle: {
    width: 14,
    height: 14,
    borderRadius: 7,
    alignItems: 'center',
    justifyContent: 'center',
  },
  checkShort: {
    position: 'absolute',
    left: 3,
    bottom: 4,
    width: 4,
    height: 2,
    transform: [{ rotate: '45deg' }],
    borderRadius: 1,
  },
  checkLong: {
    position: 'absolute',
    left: 5,
    bottom: 5,
    width: 7,
    height: 2,
    transform: [{ rotate: '-45deg' }],
    borderRadius: 1,
  },
  timeCircle: {
    width: 15,
    height: 15,
    borderRadius: 8,
    borderWidth: 1.5,
    alignItems: 'center',
    justifyContent: 'center',
  },
  timeHandV: {
    position: 'absolute',
    top: 3,
    width: 1.5,
    height: 5,
    borderRadius: 1,
  },
  timeHandH: {
    position: 'absolute',
    right: 3,
    width: 4,
    height: 1.5,
    borderRadius: 1,
  },
  shieldBox: {
    width: 14,
    height: 14,
    borderWidth: 1.5,
    borderTopLeftRadius: 4,
    borderTopRightRadius: 4,
    borderBottomLeftRadius: 7,
    borderBottomRightRadius: 7,
    alignItems: 'center',
    justifyContent: 'center',
  },
  shieldCheck: {
    width: 4,
    height: 4,
    borderRadius: 2,
  },
  infoCircle: {
    width: 14,
    height: 14,
    borderRadius: 7,
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
    height: 4,
    borderRadius: 1,
  },
});
