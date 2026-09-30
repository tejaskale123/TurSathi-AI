import { useEffect, useRef, useState } from 'react';
import { useLocalSearchParams, useRouter } from 'expo-router';
import {
  ActivityIndicator,
  Animated,
  Easing,
  Image,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLanguage } from '../i18n/LanguageContext';

type StageInfo = {
  nameKey: string;
  messageKey: string;
};

const STAGES: StageInfo[] = [
  { nameKey: 'analysis.stageImageQuality', messageKey: 'analysis.stageImageQuality' },
  { nameKey: 'analysis.stageLeafStructure', messageKey: 'analysis.stageLeafStructure' },
  { nameKey: 'analysis.stageDiseasePatterns', messageKey: 'analysis.stageDiseasePatterns' },
];

function Glyph({ name, color = '#1F5137' }: { name: 'back' | 'check' | 'arrow' | 'info'; color?: string }) {
  if (name === 'back') {
    return (
      <View style={styles.backGlyph}>
        <View style={[styles.backShaft, { backgroundColor: color }]} />
        <View style={[styles.backHead, { borderColor: color }]} />
      </View>
    );
  }

  if (name === 'check') {
    return (
      <View style={styles.checkGlyph}>
        <View style={[styles.checkShort, { backgroundColor: color }]} />
        <View style={[styles.checkLong, { backgroundColor: color }]} />
      </View>
    );
  }

  if (name === 'arrow') {
    return (
      <View style={styles.arrowGlyph}>
        <View style={[styles.arrowHead, { borderColor: color }]} />
      </View>
    );
  }

  return (
    <View style={styles.infoGlyph}>
      <View style={[styles.infoCircle, { borderColor: color }]}>
        <View style={[styles.infoDot, { backgroundColor: color }]} />
        <View style={[styles.infoStem, { backgroundColor: color }]} />
      </View>
    </View>
  );
}

export default function AnalysisScreen() {
  const router = useRouter();
  const { t } = useLanguage();
  const { imageUri, voiceUri } = useLocalSearchParams<{
    imageUri?: string | string[];
    voiceUri?: string | string[];
  }>();

  // Extract and decode route parameter safely
  const rawImageUri = Array.isArray(imageUri)
    ? imageUri[0]
    : (imageUri ?? '');

  const rawVoiceUri = Array.isArray(voiceUri)
    ? voiceUri[0]
    : (voiceUri ?? '');

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

  let normalizedVoiceUri = '';
  try {
    if (
      rawVoiceUri.startsWith('file%3A') ||
      rawVoiceUri.startsWith('http%3A') ||
      rawVoiceUri.startsWith('https%3A') ||
      rawVoiceUri.includes('%2525') ||
      !rawVoiceUri.includes('://')
    ) {
      normalizedVoiceUri = decodeURIComponent(rawVoiceUri);
    } else {
      normalizedVoiceUri = rawVoiceUri;
    }
  } catch {
    normalizedVoiceUri = rawVoiceUri;
  }

  useEffect(() => {
    console.log('[ANALYSIS] raw route URI:', rawImageUri);
    console.log('[ANALYSIS] decoded image URI:', normalizedImageUri);
    if (normalizedVoiceUri) {
      console.log('[ANALYSIS] decoded voice URI:', normalizedVoiceUri);
    }
  }, [rawImageUri, normalizedImageUri, normalizedVoiceUri]);

  // Image loading & error state management
  const [isImageLoading, setIsImageLoading] = useState(true);
  const [isImageLoaded, setIsImageLoaded] = useState(false);
  const [imageLoadError, setImageLoadError] = useState(false);

  // Analysis stages state
  const [activeStage, setActiveStage] = useState(0);
  const [isComplete, setIsComplete] = useState(false);

  // Animations
  const progressAnim = useRef(new Animated.Value(0)).current;
  const scanLineAnim = useRef(new Animated.Value(0)).current;
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const fadeAnim = useRef(new Animated.Value(0)).current;

  // Staged analysis sequence (0-2s Stage 1, 2-4s Stage 2, 4-6s Stage 3, then Complete)
  useEffect(() => {
    // Fade in page content
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: 300,
      useNativeDriver: true,
    }).start();

    // Stage progression timers
    const timer1 = setTimeout(() => {
      setActiveStage(1);
    }, 2000);

    const timer2 = setTimeout(() => {
      setActiveStage(2);
    }, 4000);

    // Smooth progress bar filling over 6 seconds
    const progressAnimation = Animated.timing(progressAnim, {
      toValue: 1,
      duration: 6000,
      easing: Easing.bezier(0.25, 0.1, 0.25, 1),
      useNativeDriver: false,
    });

    progressAnimation.start(({ finished }) => {
      if (finished) {
        setActiveStage(STAGES.length - 1);
        setIsComplete(true);
      }
    });

    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
      progressAnimation.stop();
    };
  }, [fadeAnim, progressAnim]);

  // Scanning line animation over leaf image
  useEffect(() => {
    if (isComplete) {
      scanLineAnim.stopAnimation();
      return;
    }

    const scanLoop = Animated.loop(
      Animated.sequence([
        Animated.timing(scanLineAnim, {
          toValue: 1,
          duration: 2200,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
        Animated.timing(scanLineAnim, {
          toValue: 0,
          duration: 2200,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
      ]),
    );

    scanLoop.start();
    return () => scanLoop.stop();
  }, [isComplete, scanLineAnim]);

  // Subtle pulsing dot animation for active stage and analyzing badge
  useEffect(() => {
    if (isComplete) {
      pulseAnim.setValue(1);
      return;
    }

    const pulseLoop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 0.45, duration: 650, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1, duration: 650, useNativeDriver: true }),
      ]),
    );

    pulseLoop.start();
    return () => pulseLoop.stop();
  }, [isComplete, pulseAnim]);

  const handleContinueToResults = () => {
    const params: { imageUri?: string; voiceUri?: string } = {};
    if (normalizedImageUri) {
      params.imageUri = encodeURIComponent(normalizedImageUri);
    }
    if (normalizedVoiceUri) {
      params.voiceUri = encodeURIComponent(normalizedVoiceUri);
    }
    router.push({
      pathname: '/result',
      params: Object.keys(params).length > 0 ? params : undefined,
    });
  };

  const handleBackToScan = () => {
    router.push('/scan');
  };

  // Interpolated progress bar width
  const progressWidth = progressAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ['4%', '100%'],
  });

  // Current dynamic status message
  const currentStatusMessage = isComplete
    ? t('analysis.analysisReady')
    : STAGES[activeStage]?.messageKey
      ? t(STAGES[activeStage].messageKey)
      : t('analysis.stageImageQuality');

  // 1. Error state: No image URI provided at all
  if (!normalizedImageUri) {
    return (
      <SafeAreaView edges={['top', 'bottom']} style={styles.safeArea}>
        <View style={styles.errorContainer}>
          <View style={styles.errorCard}>
            <View style={styles.errorIconWrap}>
              <Glyph name="info" color="#C7A45A" />
            </View>
            <Text style={styles.errorTitle}>{t('analysis.noPhotoTitle')}</Text>
            <Text style={styles.errorSubtitle}>
              {t('analysis.noPhotoSubtitle')}
            </Text>
            <Pressable
              accessibilityHint="Returns to the scan screen to take a photo"
              accessibilityLabel={t('analysis.backToScan')}
              accessibilityRole="button"
              onPress={handleBackToScan}
              style={({ pressed }) => [styles.primaryButton, pressed && styles.buttonPressed]}
            >
              <Text style={styles.primaryButtonText}>{t('analysis.backToScan')}</Text>
            </Pressable>
          </View>
        </View>
      </SafeAreaView>
    );
  }

  // 2. Error state: Image failed to load via actual Image onError event
  if (imageLoadError) {
    return (
      <SafeAreaView edges={['top', 'bottom']} style={styles.safeArea}>
        <View style={styles.errorContainer}>
          <View style={styles.errorCard}>
            <View style={styles.errorIconWrap}>
              <Glyph name="info" color="#C7A45A" />
            </View>
            <Text style={styles.errorTitle}>{t('analysis.unableLoadTitle')}</Text>
            <Text style={styles.errorSubtitle}>
              {t('analysis.unableLoadSubtitle')}
            </Text>
            <Pressable
              accessibilityHint="Returns to the scan screen to retake photo"
              accessibilityLabel={t('analysis.retakePhoto')}
              accessibilityRole="button"
              onPress={handleBackToScan}
              style={({ pressed }) => [styles.primaryButton, pressed && styles.buttonPressed]}
            >
              <Text style={styles.primaryButtonText}>{t('analysis.retakePhoto')}</Text>
            </Pressable>
          </View>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView edges={['top', 'bottom']} style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        <Animated.View style={[styles.page, { opacity: fadeAnim }]}>

          {/* 1. COMPACT PREMIUM HEADER */}
          <View style={styles.header}>
            <Pressable
              accessibilityHint="Returns to the previous screen"
              accessibilityLabel="Go back"
              accessibilityRole="button"
              hitSlop={8}
              onPress={() => router.back()}
              style={({ pressed }) => [styles.backButton, pressed && styles.backPressed]}
            >
              <Glyph name="back" color="#1F5137" />
            </Pressable>

            <View style={styles.headerCopy}>
              <Text style={styles.brand}>TurSathi AI</Text>
              <Text style={styles.headerTitle}>{t('analysis.headerTitle')}</Text>
              <Text style={styles.headerSubtitle}>{t('analysis.headerSubtitle')}</Text>
            </View>

            {/* Symmetrical 44px balance spacer */}
            <View style={styles.headerSpacer} />
          </View>

          {/* 2. MAIN TITLE AREA */}
          <View style={styles.titleArea}>
            <View style={styles.statusLabelBadge}>
              <Text style={styles.statusLabelText}>{t('analysis.badge')}</Text>
            </View>
            <Text style={styles.mainTitle}>{t('analysis.mainTitle')}</Text>
            <Text style={styles.mainSubtitle}>
              {t('analysis.mainSubtitle')}
            </Text>
          </View>

          {/* 3. SELECTED IMAGE CARD WITH SCANNING EFFECT */}
          <View style={styles.imageCardWrap}>
            <View style={styles.imageHeaderRow}>
              <Text style={styles.imageSectionTitle}>{t('analysis.yourTurLeaf')}</Text>
            </View>

            <View style={styles.imageFrame} accessibilityLabel="Selected Tur leaf photo undergoing analysis">
              <Image
                accessibilityLabel="Selected Tur leaf photo"
                onError={(e) => {
                  console.log('[ANALYSIS] image load error:', e.nativeEvent?.error ?? e);
                  setIsImageLoading(false);
                  setIsImageLoaded(false);
                  setImageLoadError(true);
                }}
                onLoad={() => {
                  console.log('[ANALYSIS] image loaded successfully');
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

              {/* Subtle Loading Overlay inside image frame while asynchronous loading takes place */}
              {isImageLoading && !imageLoadError && (
                <View style={styles.imageLoadingOverlay}>
                  <ActivityIndicator color="#E9D9A8" size="small" />
                  <Text style={styles.imageLoadingText}>{t('analysis.loadingPhoto')}</Text>
                </View>
              )}

              {/* Status Badge Overlaid on Image */}
              <View style={[styles.imageStatusBadge, isComplete && styles.imageStatusBadgeComplete]}>
                <Animated.View
                  style={[
                    styles.statusBadgeDot,
                    isComplete ? styles.statusDotComplete : styles.statusDotActive,
                    !isComplete && { opacity: pulseAnim },
                  ]}
                />
                <Text style={styles.statusBadgeText}>
                  {isComplete ? t('analysis.analysisReady') : t('analysis.analyzing')}
                </Text>
              </View>

              {/* Thin horizontal scanning line (top to bottom smoothly) */}
              {!isComplete && (
                <Animated.View
                  pointerEvents="none"
                  style={[
                    styles.scanLaser,
                    {
                      transform: [
                        {
                          translateY: scanLineAnim.interpolate({
                            inputRange: [0, 1],
                            outputRange: [15, 270],
                          }),
                        },
                      ],
                    },
                  ]}
                />
              )}

              {/* Bottom Subtle Overlay Label */}
              <View pointerEvents="none" style={styles.imageOverlayFooter}>
                <Text style={styles.imageOverlayFooterText}>
                  {isComplete ? t('analysis.imageReadyNext') : t('analysis.reviewingDetails')}
                </Text>
              </View>
            </View>
          </View>

          {/* 4. ANALYSIS PROGRESS CARD */}
          <View style={styles.progressCard}>
            <View style={styles.progressHeader}>
              <Text style={styles.progressCardTitle}>{t('analysis.progressTitle')}</Text>
              <Text style={styles.progressCardSubtitle}>{currentStatusMessage}</Text>
            </View>

            {/* Continuous Progress Bar */}
            <View style={styles.progressBarTrack}>
              <Animated.View style={[styles.progressBarFill, { width: progressWidth }]} />
            </View>

            {/* Three Ordered Stages */}
            <View style={styles.stagesList}>
              {STAGES.map((stage, index) => {
                const isStageDone = isComplete || index < activeStage;
                const isStageActive = !isComplete && index === activeStage;

                return (
                  <View
                    key={stage.nameKey}
                    style={[
                      styles.stageRow,
                      index < STAGES.length - 1 && styles.stageRowDivider,
                    ]}
                  >
                    {/* Stage Marker Indicator */}
                    <View
                      style={[
                        styles.stageMarker,
                        isStageDone && styles.stageMarkerDone,
                        isStageActive && styles.stageMarkerActive,
                      ]}
                    >
                      {isStageDone ? (
                        <Glyph name="check" color="#1F5137" />
                      ) : isStageActive ? (
                        <Animated.View style={[styles.activeDot, { opacity: pulseAnim }]} />
                      ) : (
                        <View style={styles.pendingDot} />
                      )}
                    </View>

                    {/* Stage Name */}
                    <Text
                      style={[
                        styles.stageName,
                        (isStageDone || isStageActive) && styles.stageNameActive,
                      ]}
                    >
                      {t(stage.nameKey)}
                    </Text>

                    {/* Stage Status Text */}
                    <Text
                      style={[
                        styles.stageStatusLabel,
                        isStageDone && styles.stageStatusComplete,
                        isStageActive && styles.stageStatusInProgress,
                      ]}
                    >
                      {isStageDone ? t('analysis.stageComplete') : isStageActive ? t('analysis.stageInProgress') : t('analysis.stagePending')}
                    </Text>
                  </View>
                );
              })}
            </View>
          </View>

          {/* 5. HELPFUL PHOTO QUALITY CARD */}
          <View style={styles.infoCard}>
            <View style={styles.infoIconCol}>
              <Glyph name="info" color="#1F5137" />
            </View>
            <View style={styles.infoCopy}>
              <Text style={styles.infoTitle}>{t('analysis.qualityTitle')}</Text>
              <Text style={styles.infoText}>
                {t('analysis.qualityText')}
              </Text>
            </View>
          </View>

          {/* 6. COMPLETION STATE & CONTINUE TO RESULTS BUTTON */}
          {isComplete ? (
            <View style={styles.completionContainer}>
              <View style={styles.readyNote}>
                <View style={styles.readyIconWrap}>
                  <Glyph name="check" color="#1F5137" />
                </View>
                <View style={styles.readyCopy}>
                  <Text style={styles.readyTitle}>{t('analysis.readyTitle')}</Text>
                  <Text style={styles.readySubtitle}>{t('analysis.readySubtitle')}</Text>
                </View>
              </View>

              <Pressable
                accessibilityHint="Navigates to the disease results screen"
                accessibilityLabel={t('analysis.continueToResults')}
                accessibilityRole="button"
                onPress={handleContinueToResults}
                style={({ pressed }) => [styles.continueButton, pressed && styles.buttonPressed]}
              >
                <Text style={styles.continueButtonText}>{t('analysis.continueToResults')}</Text>
                <Glyph name="arrow" color="#D5BB79" />
              </Pressable>
            </View>
          ) : (
            <View style={styles.waitingContainer}>
              <Text accessibilityLiveRegion="polite" style={styles.waitingText}>
                {t('analysis.waitingText')}
              </Text>
            </View>
          )}

        </Animated.View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#F5F4EC',
  },
  scrollContent: {
    flexGrow: 1,
    alignItems: 'center',
    paddingBottom: 28,
  },
  page: {
    width: '100%',
    maxWidth: 560,
    paddingHorizontal: 20,
    paddingTop: 8,
  },

  /* 1. Header */
  header: {
    minHeight: 58,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  backButton: {
    width: 44,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#E3E2D9',
    borderRadius: 22,
    backgroundColor: '#FFFEFA',
    shadowColor: '#163B2C',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.06,
    shadowRadius: 7,
    elevation: 2,
  },
  backPressed: {
    opacity: 0.86,
    transform: [{ scale: 0.96 }],
  },
  headerCopy: {
    flex: 1,
    alignItems: 'center',
    paddingHorizontal: 8,
  },
  brand: {
    color: '#1F5137',
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  headerTitle: {
    marginTop: 1,
    color: '#1A3626',
    fontSize: 16,
    fontWeight: '700',
  },
  headerSubtitle: {
    marginTop: 2,
    color: '#6B7C70',
    fontSize: 11,
  },
  headerSpacer: {
    width: 44,
    height: 44,
  },

  /* 2. Main Title Area */
  titleArea: {
    marginTop: 16,
    marginBottom: 16,
  },
  statusLabelBadge: {
    alignSelf: 'flex-start',
    paddingHorizontal: 8,
    paddingVertical: 3,
    marginBottom: 6,
    borderRadius: 6,
    backgroundColor: '#E8EFE5',
  },
  statusLabelText: {
    color: '#1F5137',
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.6,
  },
  mainTitle: {
    color: '#1A3626',
    fontSize: 24,
    fontWeight: '700',
    lineHeight: 30,
  },
  mainSubtitle: {
    marginTop: 4,
    color: '#5C6E61',
    fontSize: 13,
    lineHeight: 18,
  },

  /* 3. Selected Image Card */
  imageCardWrap: {
    marginTop: 4,
  },
  imageSectionTitle: {
    marginBottom: 8,
    color: '#1A3626',
    fontSize: 13,
    fontWeight: '700',
  },
  imageHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  imageFrame: {
    aspectRatio: 0.92,
    position: 'relative',
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: '#E2D9C3',
    borderRadius: 24,
    backgroundColor: '#113326',
    shadowColor: '#0E2B1E',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.12,
    shadowRadius: 16,
    elevation: 4,
  },
  leafPhoto: {
    width: '100%',
    height: '100%',
  },
  imageLoadingOverlay: {
    ...StyleSheet.absoluteFill,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: 'rgba(17, 51, 38, 0.85)',
    zIndex: 5,
  },
  imageLoadingText: {
    color: '#FFFEFA',
    fontSize: 12,
    fontWeight: '600',
  },
  imageStatusBadge: {
    position: 'absolute',
    top: 14,
    left: 14,
    zIndex: 6,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 11,
    paddingVertical: 6,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.24)',
    borderRadius: 12,
    backgroundColor: 'rgba(17, 51, 38, 0.8)',
  },
  imageStatusBadgeComplete: {
    backgroundColor: 'rgba(26, 68, 48, 0.9)',
    borderColor: '#D5BB79',
  },
  statusBadgeDot: {
    width: 7,
    height: 7,
    borderRadius: 3.5,
  },
  statusDotActive: {
    backgroundColor: '#D5BB79',
  },
  statusDotComplete: {
    backgroundColor: '#7BD389',
  },
  statusBadgeText: {
    color: '#FFFEFA',
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  scanLaser: {
    position: 'absolute',
    left: 16,
    right: 16,
    zIndex: 6,
    height: 2,
    borderRadius: 1,
    backgroundColor: '#D5BB79',
    shadowColor: '#D5BB79',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.9,
    shadowRadius: 8,
    elevation: 4,
  },
  imageOverlayFooter: {
    position: 'absolute',
    right: 14,
    bottom: 14,
    left: 14,
    zIndex: 6,
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.2)',
    borderRadius: 12,
    backgroundColor: 'rgba(17, 51, 38, 0.72)',
  },
  imageOverlayFooterText: {
    color: '#FFFEFA',
    fontSize: 11,
    fontWeight: '600',
  },

  /* 4. Analysis Progress Card */
  progressCard: {
    marginTop: 18,
    padding: 16,
    borderWidth: 1,
    borderColor: '#D8E3D7',
    borderRadius: 20,
    backgroundColor: '#F2F5EF',
    shadowColor: '#0E2B1E',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.05,
    shadowRadius: 10,
    elevation: 1,
  },
  progressHeader: {
    marginBottom: 10,
  },
  progressCardTitle: {
    color: '#1A3626',
    fontSize: 14,
    fontWeight: '700',
  },
  progressCardSubtitle: {
    marginTop: 2,
    color: '#5C6E61',
    fontSize: 12,
  },
  progressBarTrack: {
    height: 6,
    overflow: 'hidden',
    marginTop: 4,
    marginBottom: 14,
    borderRadius: 3,
    backgroundColor: '#D8E2D7',
  },
  progressBarFill: {
    height: '100%',
    borderRadius: 3,
    backgroundColor: '#1F5137',
  },
  stagesList: {
    borderTopWidth: 1,
    borderColor: '#E2EAE0',
  },
  stageRow: {
    minHeight: 46,
    flexDirection: 'row',
    alignItems: 'center',
  },
  stageRowDivider: {
    borderBottomWidth: 1,
    borderBottomColor: '#E6EFE4',
  },
  stageMarker: {
    width: 22,
    height: 22,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
    borderWidth: 1,
    borderColor: '#CBD6C8',
    borderRadius: 11,
    backgroundColor: '#FFFEFA',
  },
  stageMarkerActive: {
    borderColor: '#D5BB79',
    backgroundColor: '#FFFBF2',
  },
  stageMarkerDone: {
    borderColor: '#C0D8BE',
    backgroundColor: '#E8F2E6',
  },
  activeDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#C7A45A',
  },
  pendingDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#D1DAD0',
  },
  stageName: {
    flex: 1,
    color: '#748176',
    fontSize: 13,
    fontWeight: '500',
  },
  stageNameActive: {
    color: '#1A3626',
    fontWeight: '600',
  },
  stageStatusLabel: {
    color: '#8A9689',
    fontSize: 11,
  },
  stageStatusComplete: {
    color: '#1F5137',
    fontWeight: '600',
  },
  stageStatusInProgress: {
    color: '#A0783D',
    fontWeight: '600',
  },

  /* 5. Helpful Info Card */
  infoCard: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginTop: 14,
    padding: 13,
    borderWidth: 1,
    borderColor: '#E2E5DC',
    borderRadius: 14,
    backgroundColor: '#FFFEFA',
  },
  infoIconCol: {
    marginRight: 10,
    marginTop: 1,
  },
  infoCopy: {
    flex: 1,
  },
  infoTitle: {
    color: '#1A3626',
    fontSize: 12,
    fontWeight: '700',
  },
  infoText: {
    marginTop: 2,
    color: '#6B7C70',
    fontSize: 11,
    lineHeight: 16,
  },

  /* 6. Completion & CTA */
  completionContainer: {
    marginTop: 18,
  },
  readyNote: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
    padding: 12,
    borderWidth: 1,
    borderColor: '#D6E4D3',
    borderRadius: 14,
    backgroundColor: '#EDF4E9',
  },
  readyIconWrap: {
    width: 24,
    height: 24,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
    borderRadius: 12,
    backgroundColor: '#D7EAD2',
  },
  readyCopy: {
    flex: 1,
  },
  readyTitle: {
    color: '#1A3626',
    fontSize: 12,
    fontWeight: '700',
  },
  readySubtitle: {
    marginTop: 1,
    color: '#5C6E61',
    fontSize: 11,
  },
  continueButton: {
    width: '100%',
    minHeight: 54,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    borderWidth: 1.5,
    borderColor: '#D5BB79',
    borderRadius: 16,
    backgroundColor: '#1F5137',
    shadowColor: '#0E2B1E',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.16,
    shadowRadius: 10,
    elevation: 3,
  },
  continueButtonText: {
    color: '#FFFEFA',
    fontSize: 15,
    fontWeight: '700',
    letterSpacing: 0.3,
  },
  buttonPressed: {
    opacity: 0.9,
    transform: [{ scale: 0.98 }],
  },
  waitingContainer: {
    marginTop: 18,
  },
  waitingText: {
    color: '#748176',
    fontSize: 11,
    lineHeight: 16,
    textAlign: 'center',
  },

  /* Error State Views */
  errorContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 24,
  },
  errorCard: {
    width: '100%',
    maxWidth: 400,
    alignItems: 'center',
    padding: 24,
    borderWidth: 1,
    borderColor: '#E2D9C3',
    borderRadius: 20,
    backgroundColor: '#FFFEFA',
    shadowColor: '#0E2B1E',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08,
    shadowRadius: 10,
    elevation: 2,
  },
  errorIconWrap: {
    width: 48,
    height: 48,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 14,
    borderRadius: 24,
    backgroundColor: '#F9F6ED',
  },
  errorTitle: {
    color: '#1A3626',
    fontSize: 16,
    fontWeight: '700',
    textAlign: 'center',
  },
  errorSubtitle: {
    marginTop: 6,
    marginBottom: 20,
    color: '#6B7C70',
    fontSize: 13,
    lineHeight: 18,
    textAlign: 'center',
  },
  primaryButton: {
    width: '100%',
    minHeight: 48,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#D5BB79',
    borderRadius: 14,
    backgroundColor: '#1F5137',
  },
  primaryButtonText: {
    color: '#FFFEFA',
    fontSize: 14,
    fontWeight: '700',
  },

  /* Glyphs Styling */
  backGlyph: {
    width: 20,
    height: 20,
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
    left: 3,
    width: 9,
    height: 9,
    borderTopWidth: 2,
    borderLeftWidth: 2,
    transform: [{ rotate: '-45deg' }],
  },
  checkGlyph: {
    width: 12,
    height: 12,
    position: 'relative',
  },
  checkShort: {
    position: 'absolute',
    top: 7,
    left: 1,
    width: 5,
    height: 1.5,
    borderRadius: 1,
    transform: [{ rotate: '45deg' }],
  },
  checkLong: {
    position: 'absolute',
    top: 5,
    left: 4,
    width: 8,
    height: 1.5,
    borderRadius: 1,
    transform: [{ rotate: '-45deg' }],
  },
  arrowGlyph: {
    width: 12,
    height: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  arrowHead: {
    width: 7,
    height: 7,
    borderTopWidth: 2,
    borderRightWidth: 2,
    transform: [{ rotate: '45deg' }],
  },
  infoGlyph: {
    width: 18,
    height: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  infoCircle: {
    width: 17,
    height: 17,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1.5,
    borderRadius: 9,
  },
  infoDot: {
    width: 2,
    height: 2,
    marginBottom: 1.5,
    borderRadius: 1,
  },
  infoStem: {
    width: 2,
    height: 5,
    borderRadius: 1,
  },
});
