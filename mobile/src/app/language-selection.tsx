import { useState } from 'react';
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useLanguage } from '../i18n/LanguageContext';
import { Language } from '../i18n/translations';

interface LanguageOption {
  code: Language;
  label: string;
  sublabel: string;
}

const LANGUAGE_OPTIONS: LanguageOption[] = [
  { code: 'en', label: 'English', sublabel: 'English' },
  { code: 'mr', label: 'मराठी', sublabel: 'Marathi' },
  { code: 'hi', label: 'हिंदी', sublabel: 'Hindi' },
];

export default function LanguageSelectionScreen() {
  const router = useRouter();
  const { language, setLanguage } = useLanguage();
  const [selectedLanguage, setSelectedLanguage] = useState<Language>(language || 'en');
  const [hasSelected, setHasSelected] = useState<boolean>(false);

  const handleSelect = (code: Language) => {
    setSelectedLanguage(code);
    setLanguage(code);
    setHasSelected(true);
    // Navigation does NOT happen here — user must tap Next
  };

  const handleNext = () => {
    if (hasSelected) {
      router.replace('/login');
    }
  };

  return (
    <SafeAreaView edges={['top', 'bottom']} style={styles.safeArea}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.page}>
          {/* Header Brand Area */}
          <View style={styles.header}>
            <View style={styles.brandMark} accessibilityLabel="TurSathi AI logo">
              <View style={styles.markLeafLeft} />
              <View style={styles.markLeafRight} />
              <View style={styles.markLeafTop} />
              <View style={styles.markStem} />
            </View>
            <Text style={styles.brandName}>
              <Text style={styles.brandTur}>Tur</Text>
              <Text style={styles.brandSathi}>Sathi</Text>
              <Text style={styles.brandAi}> AI</Text>
            </Text>
            <View style={styles.goldRule} />
          </View>

          {/* Language Selection Card */}
          <View style={styles.card}>
            <Text style={styles.heading}>Please Select Your Language</Text>
            <Text style={styles.supportingText}>
              Choose your preferred language to continue.
            </Text>

            <View style={styles.optionsContainer}>
              {LANGUAGE_OPTIONS.map((option) => {
                const isSelected = selectedLanguage === option.code;
                return (
                  <Pressable
                    key={option.code}
                    accessibilityHint={`Select ${option.label} as your app language`}
                    accessibilityLabel={option.label}
                    accessibilityRole="button"
                    accessibilityState={{ selected: isSelected }}
                    onPress={() => handleSelect(option.code)}
                    style={({ pressed }) => [
                      styles.optionCard,
                      isSelected && styles.optionCardSelected,
                      pressed && styles.buttonPressed,
                    ]}
                  >
                    <View style={styles.optionContent}>
                      <View style={styles.radioOutline}>
                        {isSelected && <View style={styles.radioInner} />}
                      </View>

                      <View style={styles.labelGroup}>
                        <Text
                          style={[
                            styles.optionLabel,
                            isSelected && styles.optionLabelSelected,
                          ]}
                        >
                          {option.label}
                        </Text>
                        <Text style={styles.optionSublabel}>{option.sublabel}</Text>
                      </View>
                    </View>

                    <View style={[styles.arrowGlyph, isSelected && styles.arrowGlyphSelected]} />
                  </Pressable>
                );
              })}
            </View>
          </View>

          {/* Next Button */}
          <Pressable
            accessibilityLabel="Continue to login"
            accessibilityRole="button"
            accessibilityState={{ disabled: !hasSelected }}
            disabled={!hasSelected}
            onPress={handleNext}
            style={({ pressed }) => [
              styles.nextButton,
              !hasSelected && styles.nextButtonDisabled,
              pressed && hasSelected && styles.nextButtonPressed,
            ]}
          >
            <Text
              style={[
                styles.nextButtonText,
                !hasSelected && styles.nextButtonTextDisabled,
              ]}
            >
              Next  →
            </Text>
          </Pressable>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#103B2D',
  },
  scrollContent: {
    flexGrow: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 24,
  },
  page: {
    width: '100%',
    maxWidth: 480,
    paddingHorizontal: 22,
    alignItems: 'center',
  },

  // Header Brand Mark
  header: {
    alignItems: 'center',
    marginBottom: 20,
  },
  brandMark: {
    width: 55,
    height: 50,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 7,
  },
  markLeafLeft: {
    position: 'absolute',
    width: 18,
    height: 29,
    left: 7,
    top: 14,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 2,
    borderBottomLeftRadius: 2,
    borderBottomRightRadius: 20,
    backgroundColor: '#90AE7D',
    transform: [{ rotate: '-38deg' }],
  },
  markLeafRight: {
    position: 'absolute',
    width: 18,
    height: 29,
    right: 7,
    top: 14,
    borderTopLeftRadius: 2,
    borderTopRightRadius: 20,
    borderBottomLeftRadius: 20,
    borderBottomRightRadius: 2,
    backgroundColor: '#C5A45C',
    transform: [{ rotate: '38deg' }],
  },
  markLeafTop: {
    position: 'absolute',
    width: 16,
    height: 26,
    top: 0,
    borderTopLeftRadius: 18,
    borderTopRightRadius: 2,
    borderBottomLeftRadius: 2,
    borderBottomRightRadius: 18,
    backgroundColor: '#BACBA6',
  },
  markStem: {
    position: 'absolute',
    width: 2,
    height: 29,
    bottom: 2,
    borderRadius: 2,
    backgroundColor: '#E1CF9B',
  },
  brandName: {
    color: '#F6F1E5',
    fontSize: 28,
    fontWeight: '700',
  },
  brandTur: {
    color: '#F6F1E5',
  },
  brandSathi: {
    color: '#D8BD79',
  },
  brandAi: {
    color: '#F6F1E5',
    fontSize: 19,
    fontWeight: '500',
  },
  goldRule: {
    width: 36,
    height: 2,
    marginTop: 10,
    borderRadius: 2,
    backgroundColor: '#C7A65A',
  },

  // Main Card
  card: {
    width: '100%',
    paddingHorizontal: 22,
    paddingTop: 24,
    paddingBottom: 24,
    borderRadius: 22,
    backgroundColor: '#F7F5ED',
    shadowColor: '#071E17',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.16,
    shadowRadius: 20,
    elevation: 7,
  },
  heading: {
    color: '#1D3328',
    fontSize: 22,
    fontWeight: '700',
    textAlign: 'center',
    marginBottom: 6,
  },
  supportingText: {
    color: '#647369',
    fontSize: 13,
    lineHeight: 18,
    textAlign: 'center',
    marginBottom: 22,
  },

  // Option Cards
  optionsContainer: {
    gap: 12,
  },
  optionCard: {
    minHeight: 60,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 16,
    backgroundColor: '#FFFEFA',
    borderWidth: 1.5,
    borderColor: '#E2E6DD',
    elevation: 2,
    shadowColor: '#1A4D33',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 6,
  },
  optionCardSelected: {
    borderColor: '#267451',
    backgroundColor: '#F2F8F4',
  },
  optionContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
  },
  radioOutline: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 2,
    borderColor: '#9AA89B',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#FFFFFF',
  },
  radioInner: {
    width: 11,
    height: 11,
    borderRadius: 5.5,
    backgroundColor: '#267451',
  },
  labelGroup: {
    justifyContent: 'center',
  },
  optionLabel: {
    fontSize: 17,
    fontWeight: '700',
    color: '#1D3328',
  },
  optionLabelSelected: {
    color: '#145236',
  },
  optionSublabel: {
    fontSize: 11,
    color: '#708375',
    marginTop: 1,
  },

  arrowGlyph: {
    width: 8,
    height: 8,
    borderTopWidth: 2,
    borderRightWidth: 2,
    borderColor: '#9AA89B',
    transform: [{ rotate: '45deg' }],
  },
  arrowGlyphSelected: {
    borderColor: '#267451',
  },

  buttonPressed: {
    opacity: 0.9,
    transform: [{ scale: 0.99 }],
  },

  // Next Button
  nextButton: {
    width: '100%',
    marginTop: 20,
    paddingVertical: 16,
    borderRadius: 16,
    backgroundColor: '#1B5E40',
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#071E17',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.22,
    shadowRadius: 10,
    elevation: 5,
  },
  nextButtonDisabled: {
    backgroundColor: '#9EB5A8',
    shadowOpacity: 0,
    elevation: 0,
  },
  nextButtonPressed: {
    opacity: 0.88,
    transform: [{ scale: 0.98 }],
  },
  nextButtonText: {
    color: '#F6F1E5',
    fontSize: 17,
    fontWeight: '700',
    letterSpacing: 0.4,
  },
  nextButtonTextDisabled: {
    color: '#D6E2DD',
  },
});
