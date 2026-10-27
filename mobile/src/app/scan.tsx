import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'expo-router';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';
import * as Speech from 'expo-speech';
import * as FileSystem from 'expo-file-system/legacy';
import {
  ActivityIndicator,
  Alert,
  Animated,
  Image,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLanguage } from '../i18n/LanguageContext';
import { Language } from '../i18n/translations';
import { uploadScanImage, predictTurLeaf, ScanUploadError } from '../config/scanApi';
import { getAuthToken, clearAuthToken } from '../config/tokenStore';

type GlyphName =
  | 'back'
  | 'camera'
  | 'gallery'
  | 'microphone'
  | 'speaker'
  | 'play'
  | 'stop'
  | 'sun'
  | 'leaf'
  | 'focus'
  | 'check'
  | 'globe';

type PhotoSource = 'camera' | 'gallery';

// Speech locales matching selected language
const SPEECH_LOCALES: Record<Language, string> = {
  en: 'en-IN',
  mr: 'mr-IN',
  hi: 'hi-IN',
};

// Centralized translations are defined in src/i18n/translations.ts

const LANGUAGE_CHOICES: {
  code: Language;
  nativeLabel: string;
  subLabel: string;
  badge: string;
}[] = [
  { code: 'mr', nativeLabel: 'मराठी', subLabel: 'Marathi', badge: 'म' },
  { code: 'en', nativeLabel: 'English', subLabel: 'English', badge: 'EN' },
  { code: 'hi', nativeLabel: 'हिन्दी', subLabel: 'Hindi', badge: 'हि' },
];

// Prominent geometric vector camera glyph for the hero action card
function PremiumCameraHeroGlyph({ color = '#1F5137' }: { color?: string }) {
  return (
    <View style={styles.heroCameraGlyph}>
      <View style={[styles.heroCameraTopBar, { backgroundColor: color }]} />
      <View style={styles.heroCameraFlashDot} />
      <View style={[styles.heroCameraBodyBox, { borderColor: color }]}>
        <View style={[styles.heroCameraOuterLens, { borderColor: color }]}>
          <View style={[styles.heroCameraInnerLens, { backgroundColor: color }]}>
            <View style={styles.heroCameraGlint} />
          </View>
        </View>
      </View>
    </View>
  );
}

function Glyph({ name, color = '#1F5137' }: { name: GlyphName; color?: string }) {
  if (name === 'globe') {
    return (
      <View style={styles.globeGlyph}>
        <View style={[styles.globeCircle, { borderColor: color }]}>
          <View style={[styles.globeEquator, { backgroundColor: color }]} />
          <View style={[styles.globeMeridian, { borderColor: color }]} />
        </View>
      </View>
    );
  }

  if (name === 'back') {
    return (
      <View style={styles.backGlyph}>
        <View style={[styles.backShaft, { backgroundColor: color }]} />
        <View style={[styles.backHead, { borderColor: color }]} />
      </View>
    );
  }

  if (name === 'camera') {
    return (
      <View style={styles.cameraGlyph}>
        <View style={[styles.cameraBody, { borderColor: color }]}>
          <View style={[styles.cameraLens, { borderColor: color }]} />
        </View>
        <View style={[styles.cameraTop, { backgroundColor: color }]} />
      </View>
    );
  }

  if (name === 'gallery') {
    return (
      <View style={[styles.galleryGlyph, { borderColor: color }]}>
        <View style={[styles.gallerySun, { backgroundColor: color }]} />
        <View style={[styles.gallerySlopeOne, { borderColor: color }]} />
        <View style={[styles.gallerySlopeTwo, { borderColor: color }]} />
      </View>
    );
  }

  if (name === 'microphone') {
    return (
      <View style={styles.microphoneGlyph}>
        <View style={[styles.microphoneHead, { backgroundColor: color }]} />
        <View style={[styles.microphoneArc, { borderColor: color }]} />
        <View style={[styles.microphoneStem, { backgroundColor: color }]} />
        <View style={[styles.microphoneBase, { backgroundColor: color }]} />
      </View>
    );
  }

  if (name === 'speaker') {
    return (
      <View style={styles.speakerGlyph}>
        <View style={[styles.speakerBox, { backgroundColor: color }]} />
        <View style={[styles.speakerCone, { borderRightColor: color }]} />
        <View style={[styles.speakerWave, { borderColor: color }]} />
      </View>
    );
  }

  if (name === 'play') {
    return (
      <View style={styles.playGlyph}>
        <View style={[styles.playTriangle, { borderLeftColor: color }]} />
      </View>
    );
  }

  if (name === 'stop') {
    return (
      <View style={styles.stopGlyph}>
        <View style={[styles.stopSquare, { backgroundColor: color }]} />
      </View>
    );
  }

  if (name === 'sun') {
    return (
      <View style={styles.sunGlyph}>
        <View style={[styles.sunCore, { borderColor: color }]} />
        <View style={[styles.sunRay, styles.sunRayTop, { backgroundColor: color }]} />
        <View style={[styles.sunRay, styles.sunRayBottom, { backgroundColor: color }]} />
        <View style={[styles.sunRay, styles.sunRayLeft, { backgroundColor: color }]} />
        <View style={[styles.sunRay, styles.sunRayRight, { backgroundColor: color }]} />
      </View>
    );
  }

  if (name === 'leaf') {
    return (
      <View style={styles.leafGlyph}>
        <View style={[styles.leafShape, { backgroundColor: color }]} />
        <View style={styles.leafVein} />
      </View>
    );
  }

  if (name === 'focus') {
    return (
      <View style={styles.focusGlyph}>
        <View style={[styles.focusCorner, styles.focusTopLeft, { borderColor: color }]} />
        <View style={[styles.focusCorner, styles.focusTopRight, { borderColor: color }]} />
        <View style={[styles.focusCorner, styles.focusBottomLeft, { borderColor: color }]} />
        <View style={[styles.focusCorner, styles.focusBottomRight, { borderColor: color }]} />
      </View>
    );
  }

  return (
    <View style={styles.checkGlyph}>
      <View style={[styles.checkShort, { backgroundColor: color }]} />
      <View style={[styles.checkLong, { backgroundColor: color }]} />
    </View>
  );
}

function CameraGuide({
  pulse,
  scanLineAnim,
  showScanLine,
}: {
  pulse: Animated.Value;
  scanLineAnim: Animated.Value;
  showScanLine: boolean;
}) {
  const { t } = useLanguage();
  return (
    <Animated.View pointerEvents="none" style={[styles.guide, { opacity: pulse }]}>
      {showScanLine && (
        <Animated.View
          style={[
            styles.scanLine,
            {
              transform: [
                {
                  translateY: scanLineAnim.interpolate({
                    inputRange: [0, 1],
                    outputRange: [10, 260],
                  }),
                },
              ],
            },
          ]}
        />
      )}
      <View style={[styles.guideCorner, styles.guideTopLeft]} />
      <View style={[styles.guideCorner, styles.guideTopRight]} />
      <View style={[styles.guideCorner, styles.guideBottomLeft]} />
      <View style={[styles.guideCorner, styles.guideBottomRight]} />
      <View style={styles.guideCopy}>
        <Text style={styles.guideTitle}>{t('scan.guideTitle')}</Text>
        <Text style={styles.guideSubtitle}>{t('scan.guideSubtitle')}</Text>
      </View>
    </Animated.View>
  );
}

export default function ScanScreen() {
  const router = useRouter();
  const { t, language, setLanguage } = useLanguage();
  const scanText = {
    title: t('scan.title'),
    subtitle: t('scan.subtitle'),
    actionText: t('scan.actionText'),
    tapToOpen: t('scan.tapToOpen'),
    voiceGuide: t('scan.voiceGuide'),
    needHelp: t('scan.needHelp'),
    playVoiceHelp: t('scan.playVoiceHelp'),
    closeCamera: t('scan.closeCamera'),
  };
  const cameraRef = useRef<CameraView>(null);

  // Language selection modal state
  const [isLanguageModalVisible, setIsLanguageModalVisible] = useState(false);

  // Animations
  const cameraFade = useRef(new Animated.Value(0)).current;
  const guidePulse = useRef(new Animated.Value(1)).current;
  const playbackPulse = useRef(new Animated.Value(1)).current;
  const scanLineAnim = useRef(new Animated.Value(0)).current;

  // Camera UX active state (Initial Scan Page has camera CLOSED; only opens on Camera action tap)
  const [isCameraActive, setIsCameraActive] = useState(false);

  // Permissions & Camera state
  const [cameraPermission, requestCameraPermission] = useCameraPermissions();
  const [cameraVersion, setCameraVersion] = useState(0);
  const [isCameraReady, setIsCameraReady] = useState(false);
  const [isCapturing, setIsCapturing] = useState(false);
  const [cameraMessage, setCameraMessage] = useState<string | null>(null);

  // Image & Navigation state
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [photoSource, setPhotoSource] = useState<PhotoSource | null>(null);
  const [isPhotoReady, setIsPhotoReady] = useState(false);
  const [galleryMessage, setGalleryMessage] = useState<string | null>(null);

  // Upload pipeline state
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const uploadGuard = useRef(false); // Prevents duplicate uploads from double-tap
  const logoutGuard = useRef(false); // Prevents duplicate logout calls from double-tap

  // Voice Help speech playback state (expo-speech)
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [hasPlayedOnce, setHasPlayedOnce] = useState(false);
  const [audioMessage, setAudioMessage] = useState<string | null>(null);

  const cameraAvailable = Boolean(cameraPermission?.granted);
  const isPlaying = isSpeaking;

  // Authenticated route guard: redirect to /login if no valid token exists
  useEffect(() => {
    let isMounted = true;
    getAuthToken().then((token) => {
      if (isMounted && !token) {
        router.replace('/login');
      }
    });
    return () => {
      isMounted = false;
    };
  }, [router]);

  // Guide corners pulsing animation
  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(guidePulse, { toValue: 0.72, duration: 1600, useNativeDriver: true }),
        Animated.timing(guidePulse, { toValue: 1, duration: 1600, useNativeDriver: true }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [guidePulse]);

  // Subtle pulse animation while audio guide is playing
  useEffect(() => {
    if (!isPlaying) {
      playbackPulse.setValue(1);
      return;
    }
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(playbackPulse, { toValue: 0.65, duration: 600, useNativeDriver: true }),
        Animated.timing(playbackPulse, { toValue: 1, duration: 600, useNativeDriver: true }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [isPlaying, playbackPulse]);

  // Unmount cleanup - stop speech
  useEffect(() => {
    return () => {
      try {
        Speech.stop();
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

  // Scanning laser animation
  useEffect(() => {
    if (isCameraActive && cameraAvailable && !imageUri && isCameraReady) {
      const animation = Animated.loop(
        Animated.sequence([
          Animated.timing(scanLineAnim, {
            toValue: 1,
            duration: 2400,
            useNativeDriver: true,
          }),
          Animated.timing(scanLineAnim, {
            toValue: 0,
            duration: 2400,
            useNativeDriver: true,
          }),
        ])
      );
      animation.start();
      return () => animation.stop();
    }
  }, [isCameraActive, cameraAvailable, imageUri, isCameraReady, scanLineAnim]);

  // Camera preview fade animation
  useEffect(() => {
    if (!isCameraActive && !imageUri) return;
    cameraFade.setValue(0);
    const fade = Animated.timing(cameraFade, {
      toValue: 1,
      duration: 240,
      useNativeDriver: true,
    });
    fade.start();
    return () => fade.stop();
  }, [isCameraActive, cameraAvailable, cameraFade, cameraVersion, imageUri]);

  const handleCameraReady = () => {
    setIsCameraReady(true);
  };

  const handleOpenCamera = async () => {
    setCameraMessage(null);
    if (cameraPermission?.granted) {
      setIsCameraActive(true);
      return;
    }
    const permission = await requestCameraPermission();
    setIsCameraActive(true);
    if (!permission.granted) {
      setCameraMessage(t('scan.cameraPermissionText'));
    }
  };

  const handleCloseCamera = () => {
    setIsCameraActive(false);
    setCameraMessage(null);
  };

  const handleBackPress = () => {
    if (imageUri) {
      retakePhoto();
    } else if (isCameraActive) {
      setIsCameraActive(false);
    } else {
      router.back();
    }
  };

  const handleLogout = async () => {
    if (logoutGuard.current) {
      return;
    }
    logoutGuard.current = true;
    try {
      await clearAuthToken();
    } catch (err) {
      console.warn('[SCAN] Error during logout:', err);
    }
    router.replace('/login');
  };

  const promptLogout = () => {
    Alert.alert(
      t('language.logoutConfirmTitle'),
      t('language.logoutConfirmMessage'),
      [
        {
          text: t('language.cancel'),
          style: 'cancel',
        },
        {
          text: t('language.logout'),
          style: 'destructive',
          onPress: () => void handleLogout(),
        },
      ],
      { cancelable: true }
    );
  };

  const requestCameraAccess = async () => {
    setCameraMessage(null);
    const permission = cameraPermission?.granted ? cameraPermission : await requestCameraPermission();
    if (!permission.granted) {
      setCameraMessage(t('scan.cameraPermissionText'));
    }
  };

  const persistImageUri = async (uri: string): Promise<string | null> => {
    if (Platform.OS === 'web') {
      return uri;
    }
    console.log('[SCAN] temporary camera URI:', uri);
    try {
      const filename = `tur_leaf_${Date.now()}_${Math.floor(Math.random() * 10000)}.jpg`;
      const targetDir = FileSystem.documentDirectory || FileSystem.cacheDirectory;
      if (!targetDir) {
        return uri;
      }
      const targetUri = `${targetDir}${filename}`;
      await FileSystem.copyAsync({
        from: uri,
        to: targetUri,
      });
      const fileInfo = await FileSystem.getInfoAsync(targetUri);
      if (fileInfo.exists) {
        console.log('[SCAN] stable image URI:', targetUri);
        return targetUri;
      }
      console.warn('[SCAN] File system report: copied file does not exist at targetUri');
    } catch (err) {
      console.error('[SCAN] Error persisting photo URI:', err);
    }
    return null;
  };

  const capturePhoto = async () => {
    if (!cameraRef.current || !isCameraReady || isCapturing) {
      return;
    }
    setCameraMessage(null);
    setIsCapturing(true);

    try {
      const photo = await cameraRef.current.takePictureAsync({ quality: 1 });
      if (photo?.uri) {
        const stableUri = await persistImageUri(photo.uri);
        if (stableUri) {
          setImageUri(stableUri);
          setPhotoSource('camera');
          setIsPhotoReady(false);
          setIsCameraReady(false);
        } else {
          Alert.alert(t('scan.photoPrepErrorTitle'), t('scan.photoPrepErrorMsg'));
        }
      }
    } catch {
      setCameraMessage(t('scan.photoCaptureError'));
    } finally {
      setIsCapturing(false);
    }
  };

  const chooseFromGallery = async () => {
    setGalleryMessage(null);

    try {
      const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!permission.granted) {
        setGalleryMessage(t('scan.galleryPermissionNeeded'));
        return;
      }

      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ['images'],
        allowsEditing: false,
        quality: 1,
      });

      const selectedUri = result.canceled ? null : result.assets?.[0]?.uri;
      if (selectedUri) {
        const stableUri = await persistImageUri(selectedUri);
        if (stableUri) {
          setImageUri(stableUri);
          setPhotoSource('gallery');
          setIsPhotoReady(false);
          setIsCameraReady(false);
        } else {
          Alert.alert(t('scan.photoPrepErrorTitle'), t('scan.photoPrepErrorMsg'));
        }
      }
    } catch {
      setGalleryMessage(t('scan.galleryOpenError'));
    }
  };

  const retakePhoto = () => {
    setImageUri(null);
    setPhotoSource(null);
    setIsPhotoReady(false);
    setCameraMessage(null);
    setGalleryMessage(null);
    setIsCameraReady(false);
    setIsCameraActive(true);
    setCameraVersion((current) => current + 1);
    uploadGuard.current = false;
    setIsUploading(false);
  };

  const continueWithPhoto = async () => {
    if (!imageUri) {
      Alert.alert(t('scan.photoUnavailableTitle'), t('scan.photoUnavailableMsg'));
      return;
    }

    // Prevent duplicate uploads from double-tap
    if (uploadGuard.current || isUploading) {
      return;
    }

    if (Platform.OS !== 'web') {
      try {
        const fileInfo = await FileSystem.getInfoAsync(imageUri);
        if (!fileInfo.exists) {
          Alert.alert(t('scan.photoPrepErrorTitle'), t('scan.photoPrepErrorMsg'));
          return;
        }
      } catch (err) {
        console.warn('[SCAN] Could not verify file existence before upload:', err);
      }
    }

    // ── Upload pipeline ────────────────────────────────────────────────────
    uploadGuard.current = true;
    setIsUploading(true);
    setUploadError(null);

    try {
      // Retrieve stored JWT token
      const token = await getAuthToken();
      if (!token) {
        setUploadError(t('scan.sessionExpired'));
        setIsUploading(false);
        uploadGuard.current = false;
        return;
      }

      console.log('[SCAN] Starting image upload to backend...');
      const scanResult = await uploadScanImage(imageUri, token, 'tur');
      console.log('[SCAN] Upload successful. scan_id:', scanResult.scan_id);

      console.log('[SCAN] Validating Tur image...');
      const prediction = await predictTurLeaf(scanResult.scan_id, token);
      console.log('[SCAN] Validation passed! Disease:', prediction.disease_name, 'Confidence:', prediction.confidence);

      const encodedImageUri = encodeURIComponent(imageUri);
      setIsPhotoReady(true);

      // Navigate to problem-description with imageUri, scan_id, and verified prediction details
      router.push({
        pathname: '/problem-description',
        params: {
          imageUri: encodedImageUri,
          scanId: String(scanResult.scan_id),
          diseaseName: prediction.disease_name ?? '',
          confidence:
            prediction.confidence !== null && prediction.confidence !== undefined
              ? String(prediction.confidence)
              : '',
          severity: prediction.severity ?? '',
          crop: prediction.crop ?? '',
          status: prediction.status ?? '',
        },
      });
    } catch (err) {
      setIsUploading(false);
      uploadGuard.current = false;

      if (err instanceof ScanUploadError) {
        const canRetry = err.isRetryable;
        if (err.httpStatus === 422) {
          setIsPhotoReady(false);
          let errMsg: string;
          if (language === 'mr') {
            if (err.messageMr) {
              errMsg = err.messageMr;
            } else if (err.reason === 'image_too_blurry') {
              errMsg = 'फोटो अस्पष्ट (blurry) दिसत आहे. कृपया फोन स्थिर धरून चांगल्या प्रकाशात तूर पानाचा फोटो पुन्हा घ्या.';
            } else if (err.reason === 'image_too_dark') {
              errMsg = 'फोटोमध्ये प्रकाश खूप कमी (अंधुक) आहे. कृपया चांगल्या सूर्यप्रकाशात किंवा उजेडात तूर पानाचा फोटो पुन्हा घ्या.';
            } else if (err.reason === 'image_too_bright') {
              errMsg = 'फोटोमध्ये प्रकाश खूप जास्त (ओव्हरएक्सपोज्ड) आहे. कृपया योग्य प्रकाशात तूर पानाचा फोटो पुन्हा घ्या.';
            } else if (err.reason === 'image_too_small') {
              errMsg = 'फोटोचा आकार खूप लहान आहे. कृपया जवळून तूर पानाचा स्पष्ट फोटो पुन्हा घ्या.';
            } else if (err.reason === 'low_confidence_unsupported') {
              errMsg = 'निदानाची खात्री पुरेशी नाही किंवा हा रोग समर्थित नाही. कृपया चांगल्या प्रकाशात स्पष्ट तूर पानाचा फोटो पुन्हा घ्या.';
            } else {
              errMsg = 'तूर पानाचा फोटो पुरेसा स्पष्ट नाही. कृपया चांगल्या प्रकाशात एका स्पष्ट तूर पानाचा फोटो पुन्हा घ्या.';
            }
          } else if (language === 'hi') {
            if (err.reason === 'image_too_blurry') {
              errMsg = 'फोटो धुंधला (blurry) दिख रहा है। कृपया कैमरा स्थिर रखकर अच्छी रोशनी में तूर पत्ती का फोटो दोबारा लें।';
            } else if (err.reason === 'image_too_dark') {
              errMsg = 'फोटो में रोशनी बहुत कम (अंधेरा) है। कृपया अच्छी धूप या रोशनी में तूर पत्ती का फोटो दोबारा लें।';
            } else if (err.reason === 'image_too_bright') {
              errMsg = 'फोटो में रोशनी बहुत अधिक (ओवरएक्सपोज्ड) है। कृपया उपयुक्त रोशनी में तूर पत्ती का फोटो दोबारा लें।';
            } else if (err.reason === 'image_too_small') {
              errMsg = 'फोटो का आकार बहुत छोटा है। कृपया पास से तूर पत्ती का स्पष्ट फोटो दोबारा लें।';
            } else if (err.reason === 'low_confidence_unsupported') {
              errMsg = 'निदान की पुष्टि पर्याप्त नहीं है। कृपया अच्छी रोशनी में स्पष्ट तूर पत्ती का फोटो दोबारा लें।';
            } else {
              errMsg = 'तूर पत्ती का फोटो स्पष्ट नहीं है। कृपया अच्छी रोशनी में एक साफ पत्ती का फोटो दोबारा लें।';
            }
          } else {
            errMsg = err.message || 'Image quality is insufficient. Please retake a clear photo of a Tur leaf in good daylight.';
          }
          setUploadError(errMsg);
        } else {
          setUploadError(
            err.message + (canRetry ? ` ${t('scan.retryPhotoTip')}` : '')
          );
        }
        console.error('[SCAN] Upload error (HTTP', err.httpStatus, '):', err.message);
      } else {
        setUploadError(t('scan.uploadFailed'));
        console.error('[SCAN] Unexpected upload error:', err);
      }

    }
  };

  // Play / Pause / Replay localized voice help using expo-speech
  const handlePlayVoiceGuide = async () => {
    setAudioMessage(null);

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

    const textToSpeak = scanText.voiceGuide;
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
          console.warn('[SCAN] Speech error:', err);
          setIsSpeaking(false);
        },
      });
      setHasPlayedOnce(true);
    } catch (err) {
      console.warn('[SCAN] Failed to invoke Speech.speak:', err);
      setIsSpeaking(false);
      setAudioMessage(t('scan.voiceUnavailable'));
    }
  };

  const photoStatus = photoSource === 'gallery' ? t('scan.photoSelected') : t('scan.photoCaptured');
  const canCapture = isCameraReady && !isCapturing;

  const playButtonLabel = isPlaying
    ? t('scan.playing')
    : hasPlayedOnce
      ? t('scan.playAgain')
      : scanText.playVoiceHelp;

  return (
    <SafeAreaView edges={['top', 'bottom']} style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        <View style={styles.page}>

          {/* 1. TOP HEADER */}
          <View style={styles.header}>
            <Pressable
              accessibilityHint={t('scan.backHint')}
              accessibilityLabel={t('common.back')}
              accessibilityRole="button"
              hitSlop={8}
              onPress={handleBackPress}
              style={({ pressed }) => [styles.headerButton, pressed && styles.iconPressed]}
            >
              <Glyph name="back" color="#1F5137" />
            </Pressable>

            {/* Top-right Controls: Language Selection & Standalone Logout */}
            <View style={styles.headerRight}>
              <Pressable
                accessibilityHint={t('scan.languageHint')}
                accessibilityLabel={t('language.selectLanguage')}
                accessibilityRole="button"
                hitSlop={8}
                onPress={() => setIsLanguageModalVisible(true)}
                style={({ pressed }) => [styles.headerButton, pressed && styles.iconPressed]}
              >
                <Glyph name="globe" color="#1F5137" />
              </Pressable>

              <Pressable
                accessibilityHint={t('language.logoutConfirmMessage')}
                accessibilityLabel={t('language.logout')}
                accessibilityRole="button"
                hitSlop={8}
                onPress={promptLogout}
                style={({ pressed }) => [styles.logoutButton, pressed && styles.iconPressed]}
              >
                <Text style={styles.logoutText}>{t('language.logout')}</Text>
              </Pressable>
            </View>
          </View>

          {/* 2. INSTRUCTION TITLE (Shown in Initial & Full Camera modes) */}
          {!imageUri && (
            <View style={styles.instruction}>
              <Text style={styles.instructionTitle}>{scanText.title}</Text>
              <Text style={styles.instructionText}>{scanText.subtitle}</Text>
            </View>
          )}

          {/* 3. CONDITIONAL MAIN BODY */}
          {imageUri ? (
            /* PHOTO PREVIEW MODE */
            <View>
              <View style={styles.cameraCard}>
                <View accessibilityLabel={t('scan.cameraPreviewLabel')} style={styles.cameraFrame}>
                  <Animated.View style={[styles.mediaLayer, { opacity: cameraFade }]}>
                    <Image
                      accessibilityLabel={t('scan.previewImageLabel')}
                      resizeMode="cover"
                      source={{ uri: imageUri }}
                      style={styles.photo}
                    />
                  </Animated.View>
                  <View style={styles.photoBadge}>
                    <View style={styles.photoBadgeDot} />
                    <Text style={styles.photoBadgeText}>{photoStatus}</Text>
                  </View>
                </View>
              </View>

              <View style={styles.previewContainer}>
                <View style={styles.previewActions}>
                  <Pressable
                    accessibilityHint={t('scan.retakeHint')}
                    accessibilityLabel={photoSource === 'gallery' ? t('scan.chooseAnother') : t('scan.retake')}
                    accessibilityRole="button"
                    disabled={isUploading}
                    onPress={photoSource === 'gallery' ? () => void chooseFromGallery() : retakePhoto}
                    style={({ pressed }) => [styles.secondaryButton, isUploading && { opacity: 0.4 }, pressed && !isUploading && styles.secondaryPressed]}
                  >
                    <Glyph name={photoSource === 'gallery' ? 'gallery' : 'camera'} color="#1F5137" />
                    <Text style={styles.secondaryButtonText}>
                      {photoSource === 'gallery' ? t('scan.chooseAnother') : t('scan.retake')}
                    </Text>
                  </Pressable>

                  <Pressable
                    accessibilityHint={t('scan.usePhotoHint')}
                    accessibilityLabel={isUploading ? t('scan.uploading') : t('scan.useThisPhoto')}
                    accessibilityRole="button"
                    disabled={isUploading}
                    onPress={() => void continueWithPhoto()}
                    style={({ pressed }) => [styles.primaryButton, isUploading && { opacity: 0.75 }, pressed && !isUploading && styles.buttonPressed]}
                  >
                    {isUploading ? (
                      <ActivityIndicator color="#FFFEFA" size="small" />
                    ) : (
                      <Text style={styles.primaryButtonText}>{t('scan.useThisPhoto')}</Text>
                    )}
                  </Pressable>
                </View>

                {/* Upload error message */}
                {uploadError && (
                  <Text accessibilityRole="alert" style={styles.uploadErrorText}>
                    {uploadError}
                  </Text>
                )}

                <View style={styles.photoReadyCard}>
                  <View style={styles.checkWrap}>
                    <Glyph name="check" color="#1F5137" />
                  </View>
                  <View style={styles.photoReadyCopy}>
                    <Text style={styles.photoReadyTitle}>
                      {isUploading ? t('scan.uploading') : t('scan.photoReady')}
                    </Text>
                    <Text style={styles.photoReadySubtitle}>
                      {isUploading ? t('scan.uploadingWait') : t('scan.reviewBeforeAnalysis')}
                    </Text>
                  </View>
                </View>
              </View>
            </View>
          ) : isCameraActive ? (
            /* FULL CAMERA INTERFACE */
            <View>
              <View style={styles.cameraCard}>
                <View accessibilityLabel={t('scan.cameraPreviewLabel')} style={styles.cameraFrame}>
                  {cameraAvailable ? (
                    <Animated.View style={[styles.mediaLayer, { opacity: cameraFade }]}>
                      <CameraView
                        key={cameraVersion}
                        ref={cameraRef}
                        facing="back"
                        mode="picture"
                        mute={false}
                        onCameraReady={handleCameraReady}
                        onMountError={() => setCameraMessage(t('scan.cameraMountError'))}
                        style={styles.camera}
                      />
                    </Animated.View>
                  ) : cameraPermission ? (
                    <View style={styles.permissionState}>
                      <View style={styles.permissionIcon}>
                        <Glyph name="camera" color="#D5BB79" />
                      </View>
                      <Text style={styles.permissionTitle}>{t('scan.cameraAccessNeeded')}</Text>
                      <Text style={styles.permissionText}>
                        {t('scan.cameraPermissionText')}
                      </Text>
                      <Pressable
                        accessibilityHint={t('scan.allowCameraHint')}
                        accessibilityLabel={t('scan.allowCamera')}
                        accessibilityRole="button"
                        onPress={() => void requestCameraAccess()}
                        style={({ pressed }) => [styles.permissionButton, pressed && styles.buttonPressed]}
                      >
                        <Text style={styles.permissionButtonText}>{t('scan.allowCamera')}</Text>
                      </Pressable>
                    </View>
                  ) : (
                    <View style={styles.loadingState}>
                      <ActivityIndicator color="#E9D9A8" size="small" />
                      <Text style={styles.loadingText}>{t('scan.openingCamera')}</Text>
                    </View>
                  )}

                  {cameraAvailable && (
                    <CameraGuide
                      pulse={guidePulse}
                      scanLineAnim={scanLineAnim}
                      showScanLine={Boolean(cameraAvailable && isCameraReady)}
                    />
                  )}

                  {cameraAvailable && !isCameraReady && (
                    <View pointerEvents="none" style={styles.cameraLoading}>
                      <ActivityIndicator color="#FFFEFA" size="small" />
                    </View>
                  )}
                </View>

                {cameraMessage && (
                  <Text accessibilityRole="alert" style={styles.cameraMessage}>
                    {cameraMessage}
                  </Text>
                )}
              </View>

              {/* Camera Controls */}
              <View style={styles.captureContainer}>
                {cameraAvailable && (
                  <Pressable
                    accessibilityHint={t('scan.captureHint')}
                    accessibilityLabel={t('scan.captureLeaf')}
                    accessibilityRole="button"
                    accessibilityState={{ disabled: !canCapture }}
                    disabled={!canCapture}
                    onPress={() => void capturePhoto()}
                    style={({ pressed }) => [
                      styles.captureButton,
                      !canCapture && styles.captureDisabled,
                      pressed && canCapture && styles.buttonPressed,
                    ]}
                  >
                    <View style={styles.captureIconWrap}>
                      {isCapturing ? (
                        <ActivityIndicator color="#FFFEFA" size="small" />
                      ) : (
                        <Glyph name="camera" color="#D5BB79" />
                      )}
                    </View>
                    <Text style={styles.captureButtonText}>{t('scan.captureLeaf')}</Text>
                  </Pressable>
                )}

                <Pressable
                  accessibilityHint={t('scan.galleryHint')}
                  accessibilityLabel={t('scan.chooseFromGallery')}
                  accessibilityRole="button"
                  onPress={() => void chooseFromGallery()}
                  style={({ pressed }) => [styles.galleryButton, pressed && styles.secondaryPressed]}
                >
                  <Glyph name="gallery" color="#1F5137" />
                  <Text style={styles.galleryButtonText}>{t('scan.chooseFromGallery')}</Text>
                </Pressable>

                <Pressable
                  accessibilityHint={t('scan.closeCameraHint')}
                  accessibilityLabel={scanText.closeCamera}
                  accessibilityRole="button"
                  onPress={handleCloseCamera}
                  style={({ pressed }) => [styles.closeCameraButton, pressed && styles.secondaryPressed]}
                >
                  <Text style={styles.closeCameraButtonText}>{scanText.closeCamera}</Text>
                </Pressable>

                {galleryMessage && (
                  <Text accessibilityRole="alert" style={styles.galleryMessage}>
                    {galleryMessage}
                  </Text>
                )}
              </View>
            </View>
          ) : (
            /* INITIAL SCAN PAGE: CAMERA IS CLOSED */
            <View>
              {/* Prominent Camera Action Card */}
              <Pressable
                accessibilityHint={t('scan.openCameraHint')}
                accessibilityLabel={scanText.actionText}
                accessibilityRole="button"
                onPress={() => void handleOpenCamera()}
                style={({ pressed }) => [styles.cameraHeroCard, pressed && styles.heroCardPressed]}
              >
                <View style={styles.heroIconCircle}>
                  <PremiumCameraHeroGlyph color="#1F5137" />
                </View>
                <Text style={styles.heroActionTitle}>{scanText.actionText}</Text>
                <View style={styles.heroBadge}>
                  <Text style={styles.heroBadgeText}>{scanText.tapToOpen}</Text>
                </View>
              </Pressable>

              {/* Gallery Option */}
              <Pressable
                accessibilityHint={t('scan.galleryHint')}
                accessibilityLabel={t('scan.chooseFromGallery')}
                accessibilityRole="button"
                onPress={() => void chooseFromGallery()}
                style={({ pressed }) => [styles.heroGalleryButton, pressed && styles.secondaryPressed]}
              >
                <Glyph name="gallery" color="#1F5137" />
                <Text style={styles.heroGalleryButtonText}>{t('scan.chooseFromGallery')}</Text>
              </Pressable>

              {galleryMessage && (
                <Text accessibilityRole="alert" style={styles.galleryMessage}>
                  {galleryMessage}
                </Text>
              )}

              {/* Compact Voice Help Section */}
              <View style={styles.compactVoiceCard}>
                <View style={styles.compactVoiceHeader}>
                  <View style={styles.voiceSmallIcon}>
                    <Glyph name="speaker" color="#1F5137" />
                  </View>
                  <View style={styles.compactVoiceTextWrap}>
                    <Text style={styles.compactVoiceTitle}>{scanText.needHelp}</Text>
                    <Text style={styles.compactVoiceSpoken}>{scanText.voiceGuide}</Text>
                  </View>
                </View>

                <Pressable
                  accessibilityHint={t('scan.playVoiceHint')}
                  accessibilityLabel={playButtonLabel}
                  accessibilityRole="button"
                  onPress={() => void handlePlayVoiceGuide()}
                  style={({ pressed }) => [
                    styles.compactPlayButton,
                    isPlaying && styles.compactPlayButtonActive,
                    pressed && styles.buttonPressed,
                  ]}
                >
                  <Animated.View style={[styles.compactPlayIconWrap, isPlaying && { opacity: playbackPulse }]}>
                    <Glyph
                      name={isPlaying ? 'stop' : 'play'}
                      color={isPlaying ? '#FFFEFA' : '#D5BB79'}
                    />
                  </Animated.View>
                  <Text style={[styles.compactPlayText, isPlaying && styles.compactPlayTextActive]}>
                    {playButtonLabel}
                  </Text>
                </Pressable>

                {audioMessage && (
                  <Text accessibilityRole="alert" style={styles.audioErrorMessage}>
                    {audioMessage}
                  </Text>
                )}
              </View>

              {/* Guidance Tips */}
              <View style={styles.tips}>
                <View style={styles.tip}>
                  <View style={styles.tipIcon}>
                    <Glyph name="sun" color="#C7A45A" />
                  </View>
                  <Text style={styles.tipTitle}>{t('scan.goodLightTitle')}</Text>
                  <Text style={styles.tipText}>{t('scan.goodLightDesc')}</Text>
                </View>
                <View style={styles.tipDivider} />
                <View style={styles.tip}>
                  <View style={styles.tipIcon}>
                    <Glyph name="leaf" color="#1F5137" />
                  </View>
                  <Text style={styles.tipTitle}>{t('scan.clearLeafTitle')}</Text>
                  <Text style={styles.tipText}>{t('scan.clearLeafDesc')}</Text>
                </View>
                <View style={styles.tipDivider} />
                <View style={styles.tip}>
                  <View style={styles.tipIcon}>
                    <Glyph name="focus" color="#1F5137" />
                  </View>
                  <Text style={styles.tipTitle}>{t('scan.sharpFocusTitle')}</Text>
                  <Text style={styles.tipText}>{t('scan.sharpFocusDesc')}</Text>
                </View>
              </View>

              {/* Trust Note */}
              <View style={styles.trustNote}>
                <Text style={styles.trustTitle}>{t('scan.trustTitle')}</Text>
                <Text style={styles.trustText}>{t('scan.trustText')}</Text>
              </View>
            </View>
          )}

          {isPhotoReady && (
            <View style={styles.photoReadyNote}>
              <View style={styles.checkWrap}>
                <Glyph name="check" color="#1F5137" />
              </View>
              <Text style={styles.photoReadyText}>{t('scan.photoReadyNote')}</Text>
            </View>
          )}

        </View>
      </ScrollView>

      {/* Language Selection Popup Modal */}
      <Modal
        animationType="fade"
        transparent
        visible={isLanguageModalVisible}
        onRequestClose={() => setIsLanguageModalVisible(false)}
        statusBarTranslucent
      >
        <View style={styles.modalOverlay}>
          <Pressable
            style={StyleSheet.absoluteFill}
            onPress={() => setIsLanguageModalVisible(false)}
            accessibilityLabel={t('language.close')}
          />
          <View style={styles.modalContent}>
            {/* Modal Header */}
            <View style={styles.modalHeader}>
              <View style={styles.modalTitleRow}>
                <View style={styles.modalHeaderIconBadge}>
                  <Glyph name="globe" color="#1F5137" />
                </View>
                <Text style={styles.modalTitle}>{t('language.selectLanguage')}</Text>
              </View>
              <Pressable
                hitSlop={10}
                onPress={() => setIsLanguageModalVisible(false)}
                style={({ pressed }) => [styles.modalCloseButton, pressed && styles.iconPressed]}
                accessibilityLabel={t('language.close')}
                accessibilityRole="button"
              >
                <Text style={styles.modalCloseText}>✕</Text>
              </Pressable>
            </View>

            {/* Language Cards */}
            <View style={styles.languageList}>
              {LANGUAGE_CHOICES.map((item) => {
                const isSelected = language === item.code;
                return (
                  <Pressable
                    key={item.code}
                    onPress={() => {
                      setLanguage(item.code);
                      setIsLanguageModalVisible(false);
                    }}
                    style={({ pressed }) => [
                      styles.languageCard,
                      isSelected ? styles.languageCardSelected : styles.languageCardUnselected,
                      pressed && styles.languageCardPressed,
                    ]}
                    accessibilityRole="radio"
                    accessibilityState={{ selected: isSelected }}
                    accessibilityLabel={`${item.nativeLabel} (${item.subLabel})`}
                  >
                    <View style={[styles.langBadge, isSelected && styles.langBadgeSelected]}>
                      <Text style={[styles.langBadgeText, isSelected && styles.langBadgeTextSelected]}>
                        {item.badge}
                      </Text>
                    </View>
                    <View style={styles.langTextContainer}>
                      <Text style={[styles.langNativeLabel, isSelected && styles.langNativeLabelSelected]}>
                        {item.nativeLabel}
                      </Text>
                      <Text style={styles.langSubLabel}>{item.subLabel}</Text>
                    </View>
                    <View style={[styles.langRadio, isSelected && styles.langRadioSelected]}>
                      {isSelected ? <Glyph name="check" color="#FFFFFF" /> : null}
                    </View>
                  </Pressable>
                );
              })}
            </View>

            {/* Divider */}
            <View style={styles.modalDivider} />

            {/* Close Button Footer */}
            <View style={styles.modalFooterActions}>
              <Pressable
                onPress={() => setIsLanguageModalVisible(false)}
                style={({ pressed }) => [
                  styles.modalCloseFooterButton,
                  pressed && styles.buttonPressed,
                ]}
                accessibilityRole="button"
                accessibilityLabel={t('language.close')}
              >
                <Text style={styles.modalCloseFooterText}>{t('language.close')}</Text>
              </Pressable>
            </View>
          </View>
        </View>
      </Modal>
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
    paddingBottom: 24,
  },
  page: {
    width: '100%',
    maxWidth: 560,
    paddingHorizontal: 20,
    paddingTop: 8,
  },
  header: {
    minHeight: 58,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  headerRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  headerButton: {
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
  headerSpacer: {
    width: 44,
    height: 44,
  },
  logoutButton: {
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 16,
    backgroundColor: '#FFFEFA',
    borderWidth: 1,
    borderColor: '#E3E2D9',
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#163B2C',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  logoutText: {
    color: '#8A2D2D',
    fontSize: 12,
    fontWeight: '600',
  },
  iconPressed: {
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
    fontSize: 17,
    fontWeight: '700',
  },
  headerSubtitle: {
    marginTop: 2,
    color: '#6B7C70',
    fontSize: 11,
  },
  instruction: {
    marginTop: 16,
    marginBottom: 14,
  },
  instructionTitle: {
    color: '#1A3626',
    fontSize: 24,
    fontWeight: '700',
    lineHeight: 30,
  },
  instructionText: {
    marginTop: 4,
    color: '#5C6E61',
    fontSize: 13,
    lineHeight: 18,
  },
  cameraCard: {
    padding: 5,
    borderWidth: 1,
    borderColor: '#E2D9C3',
    borderRadius: 26,
    backgroundColor: '#FFFEFA',
    shadowColor: '#0E2B1E',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.12,
    shadowRadius: 16,
    elevation: 4,
  },
  cameraFrame: {
    aspectRatio: 0.8,
    position: 'relative',
    overflow: 'hidden',
    borderRadius: 22,
    backgroundColor: '#113326',
  },
  mediaLayer: {
    ...StyleSheet.absoluteFill,
  },
  camera: {
    ...StyleSheet.absoluteFill,
  },
  photo: {
    width: '100%',
    height: '100%',
  },
  loadingState: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
  },
  loadingText: {
    color: '#F3EAD5',
    fontSize: 12,
    fontWeight: '600',
  },
  permissionState: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 32,
    backgroundColor: '#113326',
  },
  permissionIcon: {
    width: 56,
    height: 56,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
    borderWidth: 1,
    borderColor: 'rgba(213, 187, 121, 0.4)',
    borderRadius: 28,
    backgroundColor: 'rgba(255, 254, 250, 0.08)',
  },
  permissionTitle: {
    color: '#FFFEFA',
    fontSize: 17,
    fontWeight: '700',
    textAlign: 'center',
  },
  permissionText: {
    marginTop: 6,
    color: '#D2DED0',
    fontSize: 12,
    lineHeight: 18,
    textAlign: 'center',
  },
  permissionButton: {
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 20,
    paddingHorizontal: 20,
    borderRadius: 14,
    backgroundColor: '#C7A45A',
  },
  permissionButtonText: {
    color: '#1A3626',
    fontSize: 13,
    fontWeight: '700',
  },
  guide: {
    ...StyleSheet.absoluteFill,
  },
  scanLine: {
    position: 'absolute',
    left: 20,
    right: 20,
    height: 2,
    backgroundColor: '#D5BB79',
    shadowColor: '#D5BB79',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.9,
    shadowRadius: 8,
    elevation: 4,
  },
  guideCorner: {
    position: 'absolute',
    width: 28,
    height: 28,
    borderColor: '#D5BB79',
  },
  guideTopLeft: {
    top: '18%',
    left: '14%',
    borderTopWidth: 2.5,
    borderLeftWidth: 2.5,
    borderTopLeftRadius: 8,
  },
  guideTopRight: {
    top: '18%',
    right: '14%',
    borderTopWidth: 2.5,
    borderRightWidth: 2.5,
    borderTopRightRadius: 8,
  },
  guideBottomLeft: {
    bottom: '24%',
    left: '14%',
    borderBottomWidth: 2.5,
    borderLeftWidth: 2.5,
    borderBottomLeftRadius: 8,
  },
  guideBottomRight: {
    right: '14%',
    bottom: '24%',
    borderRightWidth: 2.5,
    borderBottomWidth: 2.5,
    borderBottomRightRadius: 8,
  },
  guideCopy: {
    position: 'absolute',
    right: 16,
    bottom: 16,
    left: 16,
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 9,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.2)',
    borderRadius: 14,
    backgroundColor: 'rgba(17, 51, 38, 0.72)',
  },
  guideTitle: {
    color: '#FFFEFA',
    fontSize: 12,
    fontWeight: '700',
    textAlign: 'center',
  },
  guideSubtitle: {
    marginTop: 2,
    color: '#E1E9DC',
    fontSize: 10,
    textAlign: 'center',
  },
  cameraLoading: {
    position: 'absolute',
    top: 14,
    right: 14,
    width: 34,
    height: 34,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 17,
    backgroundColor: 'rgba(17, 51, 38, 0.65)',
  },
  photoBadge: {
    position: 'absolute',
    top: 14,
    left: 14,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 11,
    paddingVertical: 7,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.24)',
    borderRadius: 12,
    backgroundColor: 'rgba(17, 51, 38, 0.75)',
  },
  photoBadgeDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#D5BB79',
  },
  photoBadgeText: {
    color: '#FFFEFA',
    fontSize: 11,
    fontWeight: '700',
  },
  cameraMessage: {
    marginHorizontal: 12,
    marginTop: 8,
    marginBottom: 6,
    color: '#954F3F',
    fontSize: 11,
    lineHeight: 16,
    textAlign: 'center',
  },
  captureContainer: {
    alignItems: 'center',
    marginTop: 18,
  },
  captureButton: {
    width: '100%',
    minHeight: 54,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    borderWidth: 1.5,
    borderColor: '#D5BB79',
    borderRadius: 18,
    backgroundColor: '#1F5137',
    shadowColor: '#0E2B1E',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.16,
    shadowRadius: 10,
    elevation: 3,
  },
  captureIconWrap: {
    width: 28,
    height: 28,
    alignItems: 'center',
    justifyContent: 'center',
  },
  captureButtonText: {
    color: '#FFFEFA',
    fontSize: 15,
    fontWeight: '700',
    letterSpacing: 0.3,
  },
  captureDisabled: {
    opacity: 0.55,
  },
  galleryButton: {
    width: '100%',
    minHeight: 48,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    marginTop: 12,
    borderWidth: 1,
    borderColor: '#D2DEC8',
    borderRadius: 16,
    backgroundColor: '#FFFEFA',
  },
  galleryButtonText: {
    color: '#1F5137',
    fontSize: 13,
    fontWeight: '700',
  },
  galleryMessage: {
    maxWidth: 320,
    marginTop: 6,
    color: '#954F3F',
    fontSize: 11,
    lineHeight: 16,
    textAlign: 'center',
  },
  previewContainer: {
    marginTop: 18,
  },
  previewActions: {
    flexDirection: 'row',
    gap: 10,
  },
  secondaryButton: {
    minHeight: 52,
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 7,
    borderWidth: 1,
    borderColor: '#DCE2D9',
    borderRadius: 16,
    backgroundColor: '#FFFEFA',
  },
  secondaryPressed: {
    opacity: 0.88,
    transform: [{ scale: 0.98 }],
    backgroundColor: '#F0F3ED',
  },
  secondaryButtonText: {
    color: '#1F5137',
    fontSize: 13,
    fontWeight: '700',
  },
  primaryButton: {
    minHeight: 52,
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#D5BB79',
    borderRadius: 16,
    backgroundColor: '#1F5137',
    shadowColor: '#0E2B1E',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.14,
    shadowRadius: 8,
    elevation: 3,
  },
  primaryButtonText: {
    color: '#FFFEFA',
    fontSize: 13,
    fontWeight: '700',
  },
  buttonPressed: {
    opacity: 0.9,
    transform: [{ scale: 0.98 }],
  },
  photoReadyCard: {
    minHeight: 48,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    marginTop: 12,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderWidth: 1,
    borderColor: '#D6E4D3',
    borderRadius: 14,
    backgroundColor: '#EDF4E9',
  },
  photoReadyCopy: {
    flex: 1,
  },
  photoReadyTitle: {
    color: '#1F5137',
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  photoReadySubtitle: {
    marginTop: 1,
    color: '#5C6E61',
    fontSize: 11,
  },
  photoReadyNote: {
    minHeight: 42,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    marginTop: 12,
    paddingHorizontal: 12,
    borderWidth: 1,
    borderColor: '#D6E4D3',
    borderRadius: 14,
    backgroundColor: '#EDF4E9',
  },
  checkWrap: {
    width: 20,
    height: 20,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 10,
    backgroundColor: '#D7EAD2',
  },
  photoReadyText: {
    color: '#1F5137',
    fontSize: 12,
    fontWeight: '600',
  },

  /* 5. Voice Help Section */
  voiceSection: {
    marginTop: 20,
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
  voiceHeader: {
    marginBottom: 14,
  },
  voiceTitle: {
    color: '#1A3626',
    fontSize: 14,
    fontWeight: '700',
  },
  voiceSubtitle: {
    marginTop: 3,
    color: '#5C6E61',
    fontSize: 12,
    lineHeight: 17,
  },
  voiceControls: {
    flexDirection: 'row',
    gap: 10,
  },
  voiceLabelBadge: {
    minHeight: 46,
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    borderWidth: 1,
    borderColor: '#D2DEC8',
    borderRadius: 14,
    backgroundColor: '#E8EFE5',
  },
  voiceBadgeIconWrap: {
    width: 22,
    height: 22,
    alignItems: 'center',
    justifyContent: 'center',
  },
  voiceLabelBadgeText: {
    color: '#1F5137',
    fontSize: 13,
    fontWeight: '700',
  },
  playButton: {
    minHeight: 46,
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    borderWidth: 1,
    borderColor: '#D5BB79',
    borderRadius: 14,
    backgroundColor: '#1F5137',
    shadowColor: '#0E2B1E',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.12,
    shadowRadius: 6,
    elevation: 2,
  },
  playButtonActive: {
    borderColor: '#C7A45A',
    backgroundColor: '#163E2A',
  },
  playIconWrap: {
    width: 20,
    height: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  playButtonText: {
    color: '#FFFEFA',
    fontSize: 13,
    fontWeight: '700',
  },
  playButtonTextActive: {
    color: '#FFFEFA',
  },
  audioErrorMessage: {
    marginTop: 10,
    color: '#954F3F',
    fontSize: 11,
    lineHeight: 16,
    textAlign: 'center',
  },

  /* 6. Guidance Tips */
  tips: {
    flexDirection: 'row',
    alignItems: 'stretch',
    marginTop: 22,
    paddingVertical: 4,
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: '#E2E1D8',
  },
  tip: {
    flex: 1,
    alignItems: 'center',
    paddingHorizontal: 3,
    paddingVertical: 10,
  },
  tipDivider: {
    width: 1,
    marginVertical: 10,
    backgroundColor: '#E2E1D8',
  },
  tipIcon: {
    width: 32,
    height: 32,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 6,
    borderRadius: 10,
    backgroundColor: '#E8EFE5',
  },
  tipTitle: {
    color: '#1F5137',
    fontSize: 9,
    fontWeight: '700',
    letterSpacing: 0.5,
    textAlign: 'center',
  },
  tipText: {
    marginTop: 3,
    color: '#6B7C70',
    fontSize: 10,
    textAlign: 'center',
  },
  trustNote: {
    marginTop: 18,
    paddingBottom: 4,
  },
  trustTitle: {
    color: '#1A3626',
    fontSize: 13,
    fontWeight: '700',
  },
  trustText: {
    marginTop: 4,
    color: '#6B7C70',
    fontSize: 11,
    lineHeight: 16,
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
  cameraGlyph: {
    width: 23,
    height: 21,
    alignItems: 'center',
    justifyContent: 'center',
  },
  cameraBody: {
    width: 22,
    height: 15,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1.8,
    borderRadius: 4,
  },
  cameraTop: {
    position: 'absolute',
    top: 1,
    left: 5,
    width: 8,
    height: 4,
    borderTopLeftRadius: 2,
    borderTopRightRadius: 2,
  },
  cameraLens: {
    width: 7,
    height: 7,
    borderWidth: 1.6,
    borderRadius: 4,
  },
  galleryGlyph: {
    width: 20,
    height: 18,
    overflow: 'hidden',
    borderWidth: 1.6,
    borderRadius: 4,
  },
  gallerySun: {
    position: 'absolute',
    top: 3,
    right: 3,
    width: 4,
    height: 4,
    borderRadius: 2,
  },
  gallerySlopeOne: {
    position: 'absolute',
    bottom: 1,
    left: 2,
    width: 9,
    height: 9,
    borderTopWidth: 1.5,
    borderLeftWidth: 1.5,
    transform: [{ rotate: '45deg' }],
  },
  gallerySlopeTwo: {
    position: 'absolute',
    right: 1,
    bottom: 1,
    width: 9,
    height: 7,
    borderTopWidth: 1.5,
    borderLeftWidth: 1.5,
    transform: [{ rotate: '45deg' }],
  },
  microphoneGlyph: {
    width: 20,
    height: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  microphoneHead: {
    position: 'absolute',
    top: 2,
    width: 7,
    height: 11,
    borderRadius: 5,
  },
  microphoneArc: {
    position: 'absolute',
    top: 8,
    width: 14,
    height: 9,
    borderBottomWidth: 1.5,
    borderLeftWidth: 1.5,
    borderRightWidth: 1.5,
    borderBottomLeftRadius: 8,
    borderBottomRightRadius: 8,
  },
  microphoneStem: {
    position: 'absolute',
    top: 13,
    width: 2,
    height: 5,
    borderRadius: 1,
  },
  microphoneBase: {
    position: 'absolute',
    bottom: 1,
    width: 9,
    height: 2,
    borderRadius: 1,
  },
  speakerGlyph: {
    width: 20,
    height: 18,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  speakerBox: {
    width: 4,
    height: 7,
    borderRadius: 1,
  },
  speakerCone: {
    width: 0,
    height: 0,
    borderTopWidth: 6,
    borderBottomWidth: 6,
    borderRightWidth: 6,
    borderTopColor: 'transparent',
    borderBottomColor: 'transparent',
    marginLeft: 1,
  },
  speakerWave: {
    width: 6,
    height: 10,
    borderTopWidth: 1.6,
    borderRightWidth: 1.6,
    borderBottomWidth: 1.6,
    borderTopRightRadius: 5,
    borderBottomRightRadius: 5,
    marginLeft: 2,
  },
  playGlyph: {
    width: 18,
    height: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  playTriangle: {
    width: 0,
    height: 0,
    borderTopWidth: 5,
    borderBottomWidth: 5,
    borderLeftWidth: 9,
    borderTopColor: 'transparent',
    borderBottomColor: 'transparent',
    marginLeft: 2,
  },
  stopGlyph: {
    width: 18,
    height: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stopSquare: {
    width: 10,
    height: 10,
    borderRadius: 2,
  },
  sunGlyph: {
    width: 18,
    height: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sunCore: {
    width: 9,
    height: 9,
    borderWidth: 1.5,
    borderRadius: 5,
  },
  sunRay: {
    position: 'absolute',
    width: 2,
    height: 4,
    borderRadius: 1,
  },
  sunRayTop: {
    top: 0,
  },
  sunRayBottom: {
    bottom: 0,
  },
  sunRayLeft: {
    left: 0,
    transform: [{ rotate: '90deg' }],
  },
  sunRayRight: {
    right: 0,
    transform: [{ rotate: '90deg' }],
  },
  leafGlyph: {
    width: 18,
    height: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  leafShape: {
    width: 11,
    height: 16,
    borderTopLeftRadius: 14,
    borderTopRightRadius: 2,
    borderBottomLeftRadius: 2,
    borderBottomRightRadius: 14,
    transform: [{ rotate: '35deg' }],
  },
  leafVein: {
    position: 'absolute',
    width: 1,
    height: 12,
    borderRadius: 1,
    backgroundColor: '#F5F4EC',
    opacity: 0.65,
    transform: [{ rotate: '35deg' }],
  },
  focusGlyph: {
    width: 18,
    height: 18,
    position: 'relative',
  },
  focusCorner: {
    position: 'absolute',
    width: 7,
    height: 7,
  },
  focusTopLeft: {
    top: 0,
    left: 0,
    borderTopWidth: 1.6,
    borderLeftWidth: 1.6,
  },
  focusTopRight: {
    top: 0,
    right: 0,
    borderTopWidth: 1.6,
    borderRightWidth: 1.6,
  },
  focusBottomLeft: {
    bottom: 0,
    left: 0,
    borderBottomWidth: 1.6,
    borderLeftWidth: 1.6,
  },
  focusBottomRight: {
    right: 0,
    bottom: 0,
    borderRightWidth: 1.6,
    borderBottomWidth: 1.6,
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

  /* Hero Camera Action Card (Initial Scan Page) */
  cameraHeroCard: {
    width: '100%',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 36,
    paddingHorizontal: 20,
    marginTop: 6,
    borderWidth: 2,
    borderColor: '#D8CFA7',
    borderRadius: 24,
    backgroundColor: '#FFFEFA',
    shadowColor: '#163B2C',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.1,
    shadowRadius: 16,
    elevation: 4,
  },
  heroIconCircle: {
    width: 96,
    height: 96,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 16,
    borderWidth: 2,
    borderColor: '#E8DEC3',
    borderRadius: 48,
    backgroundColor: '#F3F7F1',
    shadowColor: '#163B2C',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08,
    shadowRadius: 10,
    elevation: 2,
  },
  heroActionTitle: {
    color: '#1A3626',
    fontSize: 20,
    fontWeight: '700',
    textAlign: 'center',
    letterSpacing: 0.2,
  },
  heroBadge: {
    marginTop: 16,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 18,
    backgroundColor: '#1F5137',
  },
  heroBadgeText: {
    color: '#FFFEFA',
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.8,
  },
  heroCardPressed: {
    opacity: 0.92,
    transform: [{ scale: 0.99 }],
    borderColor: '#C7A45A',
  },
  heroGalleryButton: {
    width: '100%',
    minHeight: 48,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    marginTop: 14,
    borderWidth: 1,
    borderColor: '#D2DEC8',
    borderRadius: 16,
    backgroundColor: '#FFFEFA',
  },
  heroGalleryButtonText: {
    color: '#1F5137',
    fontSize: 13,
    fontWeight: '700',
  },

  /* Compact Voice Help Card */
  compactVoiceCard: {
    marginTop: 18,
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderWidth: 1,
    borderColor: '#D8E3D7',
    borderRadius: 18,
    backgroundColor: '#F3F6F1',
  },
  compactVoiceHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
    marginBottom: 12,
  },
  voiceSmallIcon: {
    width: 32,
    height: 32,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 2,
    borderWidth: 1,
    borderColor: '#D2DEC8',
    borderRadius: 10,
    backgroundColor: '#E6EFE3',
  },
  compactVoiceTextWrap: {
    flex: 1,
  },
  compactVoiceTitle: {
    color: '#1A3626',
    fontSize: 13,
    fontWeight: '700',
  },
  compactVoiceSpoken: {
    marginTop: 3,
    color: '#46604E',
    fontSize: 12,
    lineHeight: 17,
  },
  compactPlayButton: {
    minHeight: 42,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    borderWidth: 1,
    borderColor: '#D5BB79',
    borderRadius: 12,
    backgroundColor: '#1F5137',
    shadowColor: '#0E2B1E',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  compactPlayButtonActive: {
    backgroundColor: '#143825',
    borderColor: '#C7A45A',
  },
  compactPlayIconWrap: {
    width: 18,
    height: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  compactPlayText: {
    color: '#FFFEFA',
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 0.3,
  },
  compactPlayTextActive: {
    color: '#FFFEFA',
  },

  /* Full Camera Interface Controls */
  closeCameraButton: {
    width: '100%',
    minHeight: 44,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    marginTop: 10,
    borderWidth: 1,
    borderColor: '#DCE2D9',
    borderRadius: 14,
    backgroundColor: '#FFFEFA',
  },
  closeCameraButtonText: {
    color: '#5C6E61',
    fontSize: 12,
    fontWeight: '600',
  },

  /* Hero Camera Glyph */
  heroCameraGlyph: {
    width: 68,
    height: 54,
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
  },
  heroCameraTopBar: {
    position: 'absolute',
    top: 2,
    left: 14,
    width: 20,
    height: 6,
    borderTopLeftRadius: 3,
    borderTopRightRadius: 3,
  },
  heroCameraFlashDot: {
    position: 'absolute',
    top: 3,
    right: 14,
    width: 7,
    height: 7,
    borderRadius: 3.5,
    backgroundColor: '#D5BB79',
  },
  heroCameraBodyBox: {
    width: 64,
    height: 44,
    marginTop: 6,
    borderWidth: 2.8,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#F8FBF6',
  },
  heroCameraOuterLens: {
    width: 26,
    height: 26,
    borderWidth: 2.2,
    borderRadius: 13,
    alignItems: 'center',
    justifyContent: 'center',
  },
  heroCameraInnerLens: {
    width: 13,
    height: 13,
    borderRadius: 6.5,
    position: 'relative',
  },
  heroCameraGlint: {
    position: 'absolute',
    top: 2,
    right: 2,
    width: 3.5,
    height: 3.5,
    borderRadius: 2,
    backgroundColor: '#D5BB79',
  },
  uploadErrorText: {
    marginTop: 10,
    marginHorizontal: 4,
    color: '#B03030',
    fontSize: 13,
    lineHeight: 18,
    textAlign: 'center',
    fontWeight: '500',
  },

  /* Globe Glyph */
  globeGlyph: {
    width: 22,
    height: 22,
    alignItems: 'center',
    justifyContent: 'center',
  },
  globeCircle: {
    width: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 1.8,
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
  globeEquator: {
    position: 'absolute',
    width: 20,
    height: 1.5,
  },
  globeMeridian: {
    position: 'absolute',
    width: 10,
    height: 20,
    borderRadius: 5,
    borderWidth: 1.5,
  },

  /* Language Selection Popup Modal */
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(12, 33, 23, 0.48)',
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 24,
  },
  modalContent: {
    width: '100%',
    maxWidth: 360,
    backgroundColor: '#FFFFFF',
    borderRadius: 22,
    borderWidth: 1,
    borderColor: '#E6E4DC',
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 20,
    shadowColor: '#102B1F',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.14,
    shadowRadius: 20,
    elevation: 8,
  },
  modalHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 18,
  },
  modalTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    flex: 1,
    marginRight: 8,
  },
  modalHeaderIconBadge: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#EFF5F0',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#D7E5DB',
  },
  modalTitle: {
    fontSize: 17,
    fontWeight: '700',
    color: '#1F5137',
    letterSpacing: -0.2,
    flexShrink: 1,
  },
  modalCloseButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#F5F4EC',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#E3E2D9',
  },
  modalCloseText: {
    fontSize: 13,
    color: '#5B6B61',
    fontWeight: '600',
    lineHeight: 16,
    textAlign: 'center',
  },
  languageList: {
    gap: 11,
  },
  languageCard: {
    flexDirection: 'row',
    alignItems: 'center',
    minHeight: 58,
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderRadius: 16,
    borderWidth: 1.5,
  },
  languageCardSelected: {
    backgroundColor: '#F2F8F4',
    borderColor: '#1F5137',
    shadowColor: '#1F5137',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 1,
  },
  languageCardUnselected: {
    backgroundColor: '#FFFFFF',
    borderColor: '#E7E5DD',
  },
  languageCardPressed: {
    opacity: 0.88,
    transform: [{ scale: 0.99 }],
  },
  langBadge: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: '#F4F3EB',
    borderWidth: 1,
    borderColor: '#DFDCD3',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  langBadgeSelected: {
    backgroundColor: '#1F5137',
    borderColor: '#1F5137',
  },
  langBadgeText: {
    fontSize: 15,
    fontWeight: '700',
    color: '#1F5137',
  },
  langBadgeTextSelected: {
    color: '#FFFFFF',
  },
  langTextContainer: {
    flex: 1,
    justifyContent: 'center',
    marginRight: 8,
  },
  langNativeLabel: {
    fontSize: 15,
    fontWeight: '700',
    color: '#24382C',
    letterSpacing: -0.1,
  },
  langNativeLabelSelected: {
    color: '#1F5137',
  },
  langSubLabel: {
    fontSize: 12,
    color: '#6F7D74',
    marginTop: 1,
    fontWeight: '500',
  },
  langRadio: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 1.6,
    borderColor: '#CBC7BA',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#FFFFFF',
  },
  langRadioSelected: {
    backgroundColor: '#1F5137',
    borderColor: '#1F5137',
  },
  modalDivider: {
    height: 1,
    backgroundColor: '#ECEAE2',
    marginTop: 16,
    marginBottom: 14,
  },
  modalFooterActions: {
    width: '100%',
  },
  modalCloseFooterButton: {
    width: '100%',
    minHeight: 46,
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 14,
    backgroundColor: '#F5F4EC',
    borderWidth: 1,
    borderColor: '#E2DFD4',
    alignItems: 'center',
    justifyContent: 'center',
  },
  modalCloseFooterText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#34483C',
  },
});
