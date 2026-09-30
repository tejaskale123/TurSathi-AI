import { useEffect } from 'react';
import { useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';
import { useLanguage } from '../i18n/LanguageContext';

export default function HomeScreen() {
  const router = useRouter();
  const { t } = useLanguage();

  useEffect(() => {
    const timer = setTimeout(() => {
      router.replace('/login');
    }, 2500);

    return () => clearTimeout(timer);
  }, [router]);

  return (
    <View style={styles.screen}>
      <View style={styles.centerContent}>
        <View style={styles.logo} accessibilityLabel={t('splash.logoAccessibility')}>
          <View style={styles.leafLeft} />
          <View style={styles.leafRight} />
          <View style={styles.leafTop} />
          <View style={styles.stem} />
          <View style={styles.logoGround} />
        </View>

        <View style={styles.brandBlock}>
          <Text style={styles.brandName}>
            <Text style={styles.brandTur}>Tur</Text>
            <Text style={styles.brandSathi}>Sathi</Text>
            <Text style={styles.brandAi}> AI</Text>
          </Text>
          <View style={styles.goldRule} />
          <Text style={styles.subtitle}>{t('splash.subtitle')}</Text>
          <Text style={styles.tagline}>{t('splash.tagline')}</Text>
        </View>
      </View>

      <View style={styles.loadingArea} accessibilityLabel={t('splash.loadingAccessibility')}>
        <View style={styles.loadingTrack}>
          <View style={styles.loadingSegment} />
          <View style={[styles.loadingSegment, styles.loadingSegmentMiddle]} />
          <View style={[styles.loadingSegment, styles.loadingSegmentLast]} />
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: '#103B2D',
    paddingHorizontal: 28,
    paddingTop: 32,
    paddingBottom: 30,
  },
  centerContent: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    width: '100%',
  },
  logo: {
    width: 92,
    height: 94,
    marginBottom: 28,
    alignItems: 'center',
    justifyContent: 'center',
  },
  leafLeft: {
    position: 'absolute',
    width: 31,
    height: 49,
    left: 12,
    top: 24,
    borderTopLeftRadius: 30,
    borderTopRightRadius: 4,
    borderBottomLeftRadius: 4,
    borderBottomRightRadius: 30,
    backgroundColor: '#8BAE77',
    transform: [{ rotate: '-38deg' }],
  },
  leafRight: {
    position: 'absolute',
    width: 31,
    height: 49,
    right: 12,
    top: 24,
    borderTopLeftRadius: 4,
    borderTopRightRadius: 30,
    borderBottomLeftRadius: 30,
    borderBottomRightRadius: 4,
    backgroundColor: '#C7A65A',
    transform: [{ rotate: '38deg' }],
  },
  leafTop: {
    position: 'absolute',
    width: 27,
    height: 41,
    top: 3,
    borderTopLeftRadius: 27,
    borderTopRightRadius: 4,
    borderBottomLeftRadius: 4,
    borderBottomRightRadius: 27,
    backgroundColor: '#B7C99B',
    transform: [{ rotate: '1deg' }],
  },
  stem: {
    position: 'absolute',
    width: 3,
    height: 52,
    bottom: 7,
    borderRadius: 3,
    backgroundColor: '#D8C58B',
  },
  logoGround: {
    position: 'absolute',
    width: 48,
    height: 2,
    bottom: 5,
    borderRadius: 2,
    backgroundColor: '#C7A65A',
    opacity: 0.82,
  },
  brandBlock: {
    alignItems: 'center',
    width: '100%',
    maxWidth: 380,
  },
  brandName: {
    color: '#F5F0E3',
    fontSize: 38,
    fontWeight: '700',
    letterSpacing: 0.2,
    textAlign: 'center',
  },
  brandTur: {
    color: '#F5F0E3',
  },
  brandSathi: {
    color: '#D8BD79',
  },
  brandAi: {
    color: '#F5F0E3',
    fontSize: 25,
    fontWeight: '500',
  },
  goldRule: {
    width: 42,
    height: 2,
    marginTop: 17,
    marginBottom: 17,
    borderRadius: 2,
    backgroundColor: '#C7A65A',
  },
  subtitle: {
    color: '#F2EDDF',
    fontSize: 16,
    fontWeight: '500',
    lineHeight: 24,
    textAlign: 'center',
  },
  tagline: {
    marginTop: 14,
    color: '#C4D0BD',
    fontSize: 13,
    fontWeight: '400',
    letterSpacing: 0.35,
    textAlign: 'center',
  },
  loadingArea: {
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 20,
  },
  loadingTrack: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    height: 4,
  },
  loadingSegment: {
    width: 5,
    height: 3,
    borderRadius: 2,
    backgroundColor: '#D8BD79',
    opacity: 0.9,
  },
  loadingSegmentMiddle: {
    width: 16,
    opacity: 0.55,
  },
  loadingSegmentLast: {
    opacity: 0.28,
  },
});
