import { useEffect, useRef, useState } from 'react';
import { useLocalSearchParams, useRouter } from 'expo-router';
import {
  ActivityIndicator,
  Animated,
  Image,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLanguage } from '../i18n/LanguageContext';

// Reusable professional vector glyphs (no emojis)
function Glyph({
  name,
  color = '#1A4D33',
  size = 18,
}: {
  name: 'back' | 'check' | 'arrow' | 'info' | 'search';
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

  if (name === 'search') {
    return (
      <View style={[styles.searchBox, { width: size, height: size }]}>
        <View style={[styles.searchGlass, { borderColor: color }]} />
        <View style={[styles.searchHandle, { backgroundColor: color }]} />
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

// Extensible result data model ready for real ML/backend API integration
export type DiseaseResultData = {
  diseaseName: string;
  confidence: number;
  severity: string;
  observedSigns: string[];
  description: string;
  isValidTurLeaf?: boolean;
  status?: 'success' | 'invalid_image' | 'no_disease_detected' | string;
};

// Temporary demo result.
// Replace with validated ML API response when backend is connected.
const demoResult: DiseaseResultData = {
  diseaseName: 'Tur Leaf Spot',
  confidence: 92,
  severity: 'Moderate',
  observedSigns: [
    'Visible leaf spotting',
    'Localized discoloration',
    'Changes on the leaf surface',
  ],
  description:
    'Tur Leaf Spot can appear as visible spots or areas of discoloration on the leaf surface. Farmers should also inspect nearby plants for similar symptoms.',
  isValidTurLeaf: true,
  status: 'success',
};

// 4 concise field observation point translation keys
const FIELD_CHECK_KEYS = [
  'result.fieldCheck1',
  'result.fieldCheck2',
  'result.fieldCheck3',
  'result.fieldCheck4',
];

// Safe confidence normalizer (e.g. 0.92 -> 92%, 92 -> 92%, avoiding 9200%)
const formatConfidence = (val: number): string => {
  if (typeof val !== 'number' || isNaN(val)) return '0%';
  const normalized = val <= 1 && val > 0 ? Math.round(val * 100) : Math.round(val);
  return `${Math.min(Math.max(normalized, 0), 100)}%`;
};

export default function ResultScreen() {
  const router = useRouter();
  const { t, tDisease, tSeverity } = useLanguage();
  const { imageUri } = useLocalSearchParams<{ imageUri?: string | string[] }>();

  // Extract raw route URI
  const rawImageUri = Array.isArray(imageUri) ? imageUri[0] : (imageUri ?? '');

  // Safely decode URI only if it hasn't been auto-decoded by Expo Router,
  // preserving Android scoped directory percent sequences (%2540 / %252F)
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

  // Development logs
  useEffect(() => {
    console.log('[RESULT] raw route URI:', rawImageUri);
    console.log('[RESULT] normalized image URI:', normalizedImageUri);
  }, [rawImageUri, normalizedImageUri]);

  // Image loading states
  const [isImageLoading, setIsImageLoading] = useState(true);
  const [isImageLoaded, setIsImageLoaded] = useState(false);
  const [imageLoadError, setImageLoadError] = useState(false);

  // Dynamic Disease Result Data (ready to accept ML model API response)
  const [resultData] = useState<DiseaseResultData>(demoResult);

  // Subtle page entrance animation
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: 350,
      useNativeDriver: true,
    }).start();
  }, [fadeAnim]);

  // Navigation handlers
  const handleBack = () => {
    router.back();
  };

  const handleReturnToScan = () => {
    router.replace('/scan');
  };

  const handleViewSprayGuidance = () => {
    router.push({
      pathname: '/spray-guidance',
      params: {
        imageUri: encodeURIComponent(normalizedImageUri),
        diseaseName: resultData.diseaseName,
        confidence: String(resultData.confidence),
        severity: resultData.severity,
      },
    });
  };

  // 1. Missing image state
  if (!normalizedImageUri) {
    return (
      <SafeAreaView edges={['top', 'bottom']} style={styles.safeArea}>
        <View style={styles.errorContainer}>
          <View style={styles.errorCard}>
            <View style={styles.errorIconWrap}>
              <Glyph color="#C7A45A" name="info" />
            </View>
            <Text style={styles.errorTitle}>{t('result.noPhotoTitle')}</Text>
            <Text style={styles.errorSubtitle}>
              {t('result.noPhotoDesc')}
            </Text>
            <Pressable
              accessibilityHint="Returns to the scan screen"
              accessibilityLabel={t('result.returnToScan')}
              accessibilityRole="button"
              onPress={handleReturnToScan}
              style={({ pressed }) => [styles.primaryButton, pressed && styles.buttonPressed]}
            >
              <Text style={styles.primaryButtonText}>{t('result.returnToScan')}</Text>
            </Pressable>
          </View>
        </View>
      </SafeAreaView>
    );
  }

  // 2. Leaf validation state (for future model validation)
  if (resultData.isValidTurLeaf === false || resultData.status === 'invalid_image') {
    return (
      <SafeAreaView edges={['top', 'bottom']} style={styles.safeArea}>
        <View style={styles.errorContainer}>
          <View style={styles.errorCard}>
            <View style={styles.errorIconWrap}>
              <Glyph color="#C7A45A" name="info" />
            </View>
            <Text style={styles.errorTitle}>{t('result.unidentifiedTitle')}</Text>
            <Text style={styles.errorSubtitle}>
              {t('result.unidentifiedDesc')}
            </Text>
            <Pressable
              accessibilityHint="Returns to the scan screen to capture photo again"
              accessibilityLabel={t('result.scanAgain')}
              accessibilityRole="button"
              onPress={handleReturnToScan}
              style={({ pressed }) => [styles.primaryButton, pressed && styles.buttonPressed]}
            >
              <Text style={styles.primaryButtonText}>{t('result.scanAgain')}</Text>
            </Pressable>
          </View>
        </View>
      </SafeAreaView>
    );
  }

  // 3. Image failed to load via actual onError
  if (imageLoadError) {
    return (
      <SafeAreaView edges={['top', 'bottom']} style={styles.safeArea}>
        <View style={styles.errorContainer}>
          <View style={styles.errorCard}>
            <View style={styles.errorIconWrap}>
              <Glyph color="#C7A45A" name="info" />
            </View>
            <Text style={styles.errorTitle}>{t('result.unableLoadTitle')}</Text>
            <Text style={styles.errorSubtitle}>
              {t('result.unableLoadDesc')}
            </Text>
            <Pressable
              accessibilityHint="Returns to the scan screen to retake photo"
              accessibilityLabel={t('result.returnToScan')}
              accessibilityRole="button"
              onPress={handleReturnToScan}
              style={({ pressed }) => [styles.primaryButton, pressed && styles.buttonPressed]}
            >
              <Text style={styles.primaryButtonText}>{t('result.returnToScan')}</Text>
            </Pressable>
          </View>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView edges={['top', 'bottom']} style={styles.safeArea}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <Animated.View style={[styles.page, { opacity: fadeAnim }]}>
          {/* 1. HEADER */}
          <View style={styles.header}>
            <Pressable
              accessibilityHint="Returns to the previous screen"
              accessibilityLabel="Go back"
              accessibilityRole="button"
              hitSlop={8}
              onPress={handleBack}
              style={({ pressed }) => [styles.backButton, pressed && styles.buttonPressed]}
            >
              <Glyph color="#1A4D33" name="back" />
            </Pressable>

            <View style={styles.headerCopy}>
              <Text style={styles.brand}>TurSathi AI</Text>
              <Text style={styles.headerTitle}>{t('result.headerTitle')}</Text>
              <Text style={styles.headerSubtitle}>
                {t('result.headerSubtitle')}
              </Text>
            </View>

            <View style={styles.headerSpacer} />
          </View>

          {/* 2. PAGE INTRO */}
          <View style={styles.introSection}>
            <View style={styles.sectionBadge}>
              <Text style={styles.sectionBadgeText}>{t('result.badge')}</Text>
            </View>
            <Text style={styles.mainHeading}>{t('result.mainHeading')}</Text>
            <Text style={styles.mainSubtitle}>
              {t('result.mainSubtitle')}
            </Text>
          </View>

          {/* 3. CAPTURED LEAF IMAGE */}
          <View style={styles.photoCard}>
            <Image
              accessibilityLabel="Captured Tur leaf photo"
              onError={(e) => {
                console.log('[RESULT] image load error:', e.nativeEvent?.error ?? e);
                setIsImageLoading(false);
                setIsImageLoaded(false);
                setImageLoadError(true);
              }}
              onLoad={() => {
                console.log('[RESULT] image loaded successfully');
                setIsImageLoading(false);
                setIsImageLoaded(true);
                setImageLoadError(false);
              }}
              onLoadStart={() => {
                setIsImageLoading(true);
                setImageLoadError(false);
              }}
              resizeMode="cover"
              source={{ uri: normalizedImageUri }}
              style={styles.leafPhoto}
            />

            {/* In-card loading overlay */}
            {isImageLoading && !imageLoadError && (
              <View style={styles.imageLoadingOverlay}>
                <ActivityIndicator color="#E9D9A8" size="small" />
                <Text style={styles.imageLoadingText}>{t('result.loadingPhoto')}</Text>
              </View>
            )}

            {/* Status badge overlaid on image */}
            <View style={styles.imageStatusBadge}>
              <View style={styles.statusDot} />
              <Text style={styles.statusBadgeText}>{t('result.analysisReady')}</Text>
            </View>
          </View>

          {/* 4. DETECTION RESULT */}
          <View style={styles.card}>
            <View style={styles.detectionHeader}>
              <Text style={styles.cardOverline}>{t('result.detectionResult')}</Text>
              <View style={styles.conditionTag}>
                <Text style={styles.conditionTagText}>{t('result.detectedCondition')}</Text>
              </View>
            </View>

            <Text style={styles.diseaseName}>{tDisease(resultData.diseaseName)}</Text>
            <Text style={styles.diseaseSubtitle}>{t('result.identifiedCondition')}</Text>

            {/* Metrics Row: Confidence & Severity */}
            <View style={styles.metricsContainer}>
              <View style={styles.metricBox}>
                <Text style={styles.metricLabel}>{t('result.confidence')}</Text>
                <Text style={styles.metricValue}>
                  {formatConfidence(resultData.confidence)}
                </Text>
              </View>

              <View style={styles.metricDivider} />

              <View style={styles.metricBox}>
                <Text style={styles.metricLabel}>{t('result.severity')}</Text>
                <View style={styles.severityBadge}>
                  <Text style={styles.severityBadgeText}>{tSeverity(resultData.severity)}</Text>
                </View>
              </View>
            </View>
          </View>

          {/* 5. ANALYSIS SUMMARY */}
          <View style={styles.card}>
            <View style={styles.cardHeaderRow}>
              <View style={styles.cardIconWrap}>
                <Glyph color="#1A4D33" name="check" size={14} />
              </View>
              <Text style={styles.cardTitle}>{t('result.summaryTitle')}</Text>
            </View>
            <Text style={styles.cardBodyText}>
              {t('result.summaryTextPrefix')}
              <Text style={styles.boldText}>{tDisease(resultData.diseaseName)}</Text>
              {t('result.summaryTextSuffix')}
            </Text>
          </View>

          {/* 6. OBSERVED SIGNS */}
          <View style={styles.card}>
            <View style={styles.cardHeaderRow}>
              <View style={styles.cardIconWrap}>
                <Glyph color="#1A4D33" name="search" size={14} />
              </View>
              <Text style={styles.cardTitle}>{t('result.observedSigns')}</Text>
            </View>

            <View style={styles.observationList}>
              {resultData.observedSigns.map((sign, index) => (
                <View key={index} style={styles.observationRow}>
                  <View style={styles.checkWrap}>
                    <Glyph color="#1A4D33" name="check" size={13} />
                  </View>
                  <Text style={styles.observationText}>{sign}</Text>
                </View>
              ))}
            </View>
          </View>

          {/* 7. WHAT THIS CONDITION MEANS */}
          <View style={styles.card}>
            <View style={styles.cardHeaderRow}>
              <View style={styles.cardIconWrap}>
                <Glyph color="#1A4D33" name="info" size={14} />
              </View>
              <Text style={styles.cardTitle}>{t('result.whatMeansTitle')}</Text>
            </View>
            <Text style={styles.cardBodyText}>{resultData.description}</Text>
            <Text style={styles.cardSupportingText}>
              {t('result.whatMeansSupport')}
            </Text>
          </View>

          {/* 8. WHAT TO CHECK IN THE FIELD */}
          <View style={styles.card}>
            <View style={styles.cardHeaderRow}>
              <View style={styles.cardIconWrap}>
                <Glyph color="#1A4D33" name="check" size={14} />
              </View>
              <Text style={styles.cardTitle}>{t('result.fieldCheckTitle')}</Text>
            </View>
            <Text style={styles.fieldCheckIntro}>
              {t('result.fieldCheckIntro')}
            </Text>

            <View style={styles.fieldCheckList}>
              {FIELD_CHECK_KEYS.map((key, index) => (
                <View key={index} style={styles.fieldCheckRow}>
                  <View style={styles.fieldCheckNumberCircle}>
                    <Text style={styles.fieldCheckNumberText}>
                      {String(index + 1).padStart(2, '0')}
                    </Text>
                  </View>
                  <Text style={styles.fieldCheckText}>{t(key)}</Text>
                </View>
              ))}
            </View>
          </View>

          {/* 9. RESULT RELIABILITY */}
          <View style={styles.card}>
            <View style={styles.reliabilityHeader}>
              <Text style={styles.cardTitle}>{t('result.reliabilityTitle')}</Text>
              <View style={styles.confidenceScoreBadge}>
                <Text style={styles.confidenceScoreLabel}>{t('result.modelConfidence')}</Text>
                <Text style={styles.confidenceScoreValue}>
                  {formatConfidence(resultData.confidence)}
                </Text>
              </View>
            </View>
            <Text style={styles.cardBodyText}>
              {t('result.reliabilityDesc')}
            </Text>
          </View>

          {/* 10. PRIMARY CTA */}
          <Pressable
            accessibilityHint="Navigates to treatment and spray decision support"
            accessibilityLabel={t('result.viewSprayGuidance')}
            accessibilityRole="button"
            onPress={handleViewSprayGuidance}
            style={({ pressed }) => [styles.primaryCta, pressed && styles.buttonPressed]}
          >
            <Text style={styles.primaryCtaText}>{t('result.viewSprayGuidance')}</Text>
            <View style={styles.primaryCtaArrow}>
              <Glyph color="#FFFFFF" name="arrow" size={16} />
            </View>
          </Pressable>

          {/* 11. SECONDARY CTA */}
          <Pressable
            accessibilityHint="Returns to the camera scan screen"
            accessibilityLabel={t('result.scanAnotherLeaf')}
            accessibilityRole="button"
            onPress={handleReturnToScan}
            style={({ pressed }) => [styles.secondaryCta, pressed && styles.buttonPressed]}
          >
            <Text style={styles.secondaryCtaText}>{t('result.scanAnotherLeaf')}</Text>
          </Pressable>

          {/* 12. FIELD VERIFICATION ADVISORY NOTICE */}
          <View style={styles.trustCard}>
            <View style={styles.trustIconWrap}>
              <Glyph color="#8B743D" name="info" size={16} />
            </View>
            <View style={styles.trustCopy}>
              <Text style={styles.trustTitle}>{t('result.fieldVerificationTitle')}</Text>
              <Text style={styles.trustText}>
                {t('result.fieldVerificationDesc')}
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

  // 1. Header
  header: {
    minHeight: 52,
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
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
  },
  headerSpacer: {
    width: 44,
  },

  // 2. Intro
  introSection: {
    marginBottom: 16,
  },
  sectionBadge: {
    alignSelf: 'flex-start',
    backgroundColor: '#E7F0E8',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
    marginBottom: 8,
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
    color: '#55695C',
    lineHeight: 18,
    marginTop: 4,
  },

  // 3. Photo Card
  photoCard: {
    width: '100%',
    height: 270,
    borderRadius: 22,
    overflow: 'hidden',
    backgroundColor: '#123624',
    borderWidth: 1,
    borderColor: '#E2EBDC',
    marginBottom: 16,
    elevation: 4,
    shadowColor: '#1A4D33',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.12,
    shadowRadius: 10,
  },
  leafPhoto: {
    width: '100%',
    height: '100%',
  },
  imageLoadingOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(18, 54, 36, 0.82)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  imageLoadingText: {
    color: '#E9D9A8',
    fontSize: 12,
    fontWeight: '600',
    marginTop: 8,
  },
  imageStatusBadge: {
    position: 'absolute',
    top: 14,
    left: 14,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(18, 54, 36, 0.88)',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#C7A45A',
  },
  statusDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#6EE7B7',
    marginRight: 6,
  },
  statusBadgeText: {
    color: '#FFFFFF',
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.6,
  },

  // 4. Cards (General)
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
  detectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  cardOverline: {
    fontSize: 11,
    fontWeight: '700',
    color: '#708375',
    textTransform: 'uppercase',
    letterSpacing: 0.7,
  },
  conditionTag: {
    backgroundColor: '#FBF3DD',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#E6D49C',
  },
  conditionTagText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#8B6822',
  },
  diseaseName: {
    fontSize: 25,
    fontWeight: '800',
    color: '#163826',
    letterSpacing: -0.3,
  },
  diseaseSubtitle: {
    fontSize: 12,
    color: '#75887B',
    marginTop: 2,
    marginBottom: 16,
  },
  metricsContainer: {
    flexDirection: 'row',
    backgroundColor: '#F8FAF5',
    borderRadius: 14,
    paddingVertical: 14,
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
    fontSize: 20,
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

  // Card Content Details
  cardHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
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
  },
  cardSupportingText: {
    fontSize: 12,
    color: '#728578',
    marginTop: 8,
    fontStyle: 'italic',
  },
  boldText: {
    fontWeight: '700',
    color: '#163826',
  },

  // 6. Observed Signs List
  observationList: {
    gap: 10,
    marginTop: 4,
  },
  observationRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  checkWrap: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: '#EBF4EC',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
  },
  observationText: {
    fontSize: 13,
    color: '#3B5243',
    fontWeight: '500',
    flex: 1,
  },

  // 8. What To Check In The Field
  fieldCheckIntro: {
    fontSize: 12,
    color: '#6E8074',
    marginBottom: 12,
  },
  fieldCheckList: {
    gap: 10,
  },
  fieldCheckRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    backgroundColor: '#FAFCF8',
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#EDF2E8',
  },
  fieldCheckNumberCircle: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: '#E7F2E8',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
    marginTop: 1,
  },
  fieldCheckNumberText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#1A4D33',
  },
  fieldCheckText: {
    fontSize: 13,
    color: '#324C3B',
    lineHeight: 18,
    flex: 1,
  },

  // 9. Result Reliability
  reliabilityHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
    flexWrap: 'wrap',
    gap: 6,
  },
  confidenceScoreBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F8FAF5',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#E6EEE0',
    gap: 6,
  },
  confidenceScoreLabel: {
    fontSize: 11,
    color: '#708375',
    fontWeight: '600',
  },
  confidenceScoreValue: {
    fontSize: 13,
    fontWeight: '800',
    color: '#1A4D33',
  },

  // 10. Primary CTA
  primaryCta: {
    width: '100%',
    height: 54,
    borderRadius: 16,
    backgroundColor: '#1A4D33',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 6,
    marginBottom: 12,
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

  // 11. Secondary CTA
  secondaryCta: {
    width: '100%',
    height: 50,
    borderRadius: 16,
    backgroundColor: '#FFFFFF',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 20,
    borderWidth: 1,
    borderColor: '#D4DDD3',
    elevation: 1,
    shadowColor: '#1A4D33',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
  },
  secondaryCtaText: {
    color: '#1A4D33',
    fontSize: 14,
    fontWeight: '600',
  },

  // 12. Decision Support Trust Card
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

  // Error Card States
  errorContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 24,
  },
  errorCard: {
    width: '100%',
    maxWidth: 420,
    backgroundColor: '#FFFFFF',
    borderRadius: 22,
    padding: 24,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#E5ECE0',
    elevation: 3,
    shadowColor: '#1A4D33',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08,
    shadowRadius: 10,
  },
  errorIconWrap: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#FAF5E8',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 14,
  },
  errorTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#163826',
    textAlign: 'center',
    marginBottom: 6,
  },
  errorSubtitle: {
    fontSize: 13,
    color: '#65776B',
    textAlign: 'center',
    lineHeight: 19,
    marginBottom: 20,
  },
  primaryButton: {
    width: '100%',
    height: 48,
    borderRadius: 14,
    backgroundColor: '#1A4D33',
    alignItems: 'center',
    justifyContent: 'center',
  },
  primaryButtonText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '700',
  },
  buttonPressed: {
    opacity: 0.86,
    transform: [{ scale: 0.98 }],
  },

  // Glyphs styling
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
  searchBox: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  searchGlass: {
    width: 10,
    height: 10,
    borderRadius: 5,
    borderWidth: 1.5,
  },
  searchHandle: {
    position: 'absolute',
    right: 2,
    bottom: 2,
    width: 4,
    height: 1.5,
    transform: [{ rotate: '45deg' }],
    borderRadius: 1,
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
