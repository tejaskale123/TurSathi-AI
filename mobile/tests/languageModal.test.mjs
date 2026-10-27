import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';

describe('Language Selection Upgrade & Accessibility Suite', () => {
  const translationsPath = path.resolve('mobile/src/i18n/translations.ts');
  const scanScreenPath = path.resolve('mobile/src/app/scan.tsx');
  const languageContextPath = path.resolve('mobile/src/i18n/LanguageContext.tsx');
  const languageSelectionScreenPath = path.resolve('mobile/src/app/language-selection.tsx');

  const translationsContent = fs.readFileSync(translationsPath, 'utf8');
  const scanContent = fs.readFileSync(scanScreenPath, 'utf8');
  const contextContent = fs.readFileSync(languageContextPath, 'utf8');
  const languageSelectionContent = fs.readFileSync(languageSelectionScreenPath, 'utf8');

  test('Required modal translation keys exist in en, mr, and hi', () => {
    const requiredKeys = [
      'language.selectLanguage',
      'language.marathi',
      'language.english',
      'language.hindi',
      'language.close',
    ];

    for (const key of requiredKeys) {
      assert.ok(
        translationsContent.includes(`'${key}':`),
        `Missing translation key ${key} in translations.ts`
      );
    }
  });

  test('Top-right button renders globe Glyph with accessibilityLabel and opens modal', () => {
    // Check that Glyph includes 'globe'
    assert.ok(
      scanContent.includes("name === 'globe'"),
      'Glyph component does not implement globe icon'
    );

    // Check that top-right header button uses globe glyph
    assert.ok(
      scanContent.includes('<Glyph name="globe" color="#1F5137" />'),
      'Header does not render dark green globe Glyph'
    );

    // Check accessible label on the language button
    assert.ok(
      scanContent.includes("accessibilityLabel={t('language.selectLanguage')}"),
      'Globe button is missing accessible label'
    );

    // Check modal open trigger
    assert.ok(
      scanContent.includes('setIsLanguageModalVisible(true)'),
      'Globe button does not open language modal'
    );
  });

  test('Language modal offers Marathi, English, and Hindi with checkmark styling and closes on selection', () => {
    // Check LANGUAGE_CHOICES array has mr, en, and hi
    assert.ok(
      scanContent.includes("code: 'mr'"),
      'LANGUAGE_CHOICES missing Marathi'
    );
    assert.ok(
      scanContent.includes("code: 'en'"),
      'LANGUAGE_CHOICES missing English'
    );
    assert.ok(
      scanContent.includes("code: 'hi'"),
      'LANGUAGE_CHOICES missing Hindi'
    );

    // Check that selected item renders checkmark
    assert.ok(
      scanContent.includes('<Glyph name="check" color="#FFFFFF" />'),
      'Language card does not render checkmark glyph when selected'
    );

    // Check that selecting language updates context and closes modal
    assert.ok(
      scanContent.includes('setLanguage(item.code);'),
      'Selecting a language option must call setLanguage'
    );
    assert.ok(
      scanContent.includes('setIsLanguageModalVisible(false);'),
      'Selecting a language option must close the modal'
    );
  });

  test('Logout is completely removed from language popup and placed as standalone header button', () => {
    // Extract modal JSX chunk
    const modalStart = scanContent.indexOf('{/* Language Selection Popup Modal */}');
    const modalEnd = scanContent.indexOf('</Modal>', modalStart);
    const modalSection = scanContent.slice(modalStart, modalEnd);

    // Logout MUST NOT appear inside the modal
    assert.ok(
      !modalSection.toLowerCase().includes('logout'),
      'Language popup must never contain a Logout option'
    );
    assert.ok(
      !modalSection.includes('modalLogoutButton'),
      'modalLogoutButton must not be present inside language modal'
    );

    // Header must contain standalone Logout button alongside language button
    const headerStart = scanContent.indexOf('{/* 1. TOP HEADER */}');
    const headerEnd = scanContent.indexOf('{/* 2. INSTRUCTION TITLE', headerStart);
    const headerSection = scanContent.slice(headerStart, headerEnd);

    assert.ok(
      headerSection.includes('logoutButton'),
      'Top header must contain a standalone logoutButton'
    );
    assert.ok(
      headerSection.includes("t('language.logout')"),
      'Standalone logout button must render localized Logout label'
    );
    assert.ok(
      headerSection.includes('promptLogout'),
      'Standalone logout button must trigger promptLogout'
    );

    // Confirm dialog texts and handlers
    assert.ok(
      scanContent.includes("t('language.logoutConfirmTitle')"),
      'Logout must show a localized confirmation title'
    );
    assert.ok(
      scanContent.includes("t('language.logoutConfirmMessage')"),
      'Logout must show a localized confirmation message'
    );
    assert.ok(
      scanContent.includes("t('language.cancel')"),
      'Logout confirm dialog must include a Cancel option'
    );
    assert.ok(
      scanContent.includes('handleLogout()'),
      'handleLogout must be invoked upon confirmation'
    );

    // Ensure handleLogout & clearAuthToken remain available in the file
    assert.ok(
      scanContent.includes('const handleLogout = async () => {'),
      'handleLogout function must be preserved in scan.tsx'
    );
    assert.ok(
      scanContent.includes('clearAuthToken()'),
      'clearAuthToken logic must remain intact'
    );
    assert.ok(
      scanContent.includes('logoutGuard.current'),
      'handleLogout must be guarded against duplicate calls'
    );
  });

  test('Close button is preserved at the bottom with proper accessibility', () => {
    const modalStart = scanContent.indexOf('{/* Language Selection Popup Modal */}');
    const modalEnd = scanContent.indexOf('</Modal>', modalStart);
    const modalSection = scanContent.slice(modalStart, modalEnd);

    assert.ok(
      modalSection.includes('modalCloseFooterButton'),
      'Modal footer must contain the Close button'
    );
    assert.ok(
      modalSection.includes("accessibilityLabel={t('language.close')}"),
      'Close button must have an accessibilityLabel'
    );
    assert.ok(
      modalSection.includes('setIsLanguageModalVisible(false)'),
      'Close button must dismiss the modal'
    );
  });

  test('Modal positioning is stable and centered with statusBarTranslucent', () => {
    assert.ok(
      scanContent.includes('statusBarTranslucent'),
      'Modal must have statusBarTranslucent for stable centering across status bars'
    );
    assert.ok(
      scanContent.includes('maxWidth: 360'),
      'Modal content must constrain maxWidth to 360 for responsive mobile sizing'
    );
    assert.ok(
      scanContent.includes("justifyContent: 'center'"),
      'Modal overlay must be centered'
    );
  });

  test('LanguageSelectionScreen uses safe-area-context without deprecation warning', () => {
    assert.ok(
      languageSelectionContent.includes("from 'react-native-safe-area-context'"),
      'language-selection.tsx must import SafeAreaView from react-native-safe-area-context'
    );
    assert.ok(
      !languageSelectionContent.includes("SafeAreaView,\n  ScrollView,\n  StyleSheet,\n  Text,\n  View,\n} from 'react-native'"),
      'language-selection.tsx must not import deprecated SafeAreaView from react-native'
    );
  });

  test('LanguageContext defaults to Marathi (mr) when no saved preference exists', () => {
    assert.ok(
      contextContent.includes("language: 'mr'"),
      'LanguageContext default createContext language is not Marathi (mr)'
    );
    assert.ok(
      contextContent.includes("useState<Language>('mr')"),
      'LanguageProvider initial state does not default to Marathi (mr)'
    );
  });

  test('Agricultural theme styling tokens are correctly applied', () => {
    assert.ok(
      scanContent.includes("backgroundColor: '#FFFFFF'"),
      'Modal does not use clean white card surface'
    );
    assert.ok(
      scanContent.includes("color: '#1F5137'"),
      'Modal does not use dark green primary text'
    );
    assert.ok(
      scanContent.includes('borderRadius: 22'),
      'Modal card does not have refined rounded corners'
    );
  });
});

describe('Tur Leaf Photo Capture Language Consistency & UI Presentation Suite', () => {
  const translationsPath = path.resolve('mobile/src/i18n/translations.ts');
  const scanScreenPath = path.resolve('mobile/src/app/scan.tsx');

  const translationsContent = fs.readFileSync(translationsPath, 'utf8');
  const scanContent = fs.readFileSync(scanScreenPath, 'utf8');

  test('Marathi capture screen strings exactly match the user screenshot and requirements', () => {
    // Screenshot 1 elements:
    // “तूर पानाचा फोटो काढा”
    // “कॅमेरा उघडण्यासाठी टॅप करा”
    // “गॅलरीतून निवडा”
    // “मदत हवी आहे?”
    assert.ok(
      translationsContent.includes("'scan.title': 'तूर पानाचा फोटो काढा'"),
      'Marathi scan title must match "तूर पानाचा फोटो काढा"'
    );
    assert.ok(
      translationsContent.includes("'scan.actionText': 'तूर पानाचा फोटो काढा'"),
      'Marathi scan action card title must match "तूर पानाचा फोटो काढा"'
    );
    assert.ok(
      translationsContent.includes("'scan.tapToOpen': 'कॅमेरा उघडण्यासाठी टॅप करा'"),
      'Marathi tap to open badge must match "कॅमेरा उघडण्यासाठी टॅप करा"'
    );
    assert.ok(
      translationsContent.includes("'scan.chooseFromGallery': 'गॅलरीतून निवडा'"),
      'Marathi choose gallery button must match "गॅलरीतून निवडा"'
    );
    assert.ok(
      translationsContent.includes("'scan.needHelp': 'मदत हवी आहे?'"),
      'Marathi voice help title must match "मदत हवी आहे?"'
    );
    assert.ok(
      translationsContent.includes("'scan.playVoiceHelp': 'आवाज मार्गदर्शन ऐका'"),
      'Marathi voice help button must match "आवाज मार्गदर्शन ऐका"'
    );
    assert.ok(
      translationsContent.includes("'scan.closeCamera': 'कॅमेरा बंद करा'"),
      'Marathi close camera button must match "कॅमेरा बंद करा"'
    );
  });

  test('English capture screen strings exactly match the user screenshot and requirements', () => {
    // Screenshot 2 elements:
    // “Capture Tur Leaf Photo”
    // “TAP TO OPEN CAMERA”
    // “Choose from Gallery”
    // “Need help?”
    assert.ok(
      translationsContent.includes("'scan.title': 'Capture Tur Leaf Photo'"),
      'English scan title must match "Capture Tur Leaf Photo"'
    );
    assert.ok(
      translationsContent.includes("'scan.actionText': 'Capture Tur Leaf Photo'"),
      'English scan action card title must match "Capture Tur Leaf Photo"'
    );
    assert.ok(
      translationsContent.includes("'scan.tapToOpen': 'TAP TO OPEN CAMERA'"),
      'English tap to open badge must match "TAP TO OPEN CAMERA"'
    );
    assert.ok(
      translationsContent.includes("'scan.chooseFromGallery': 'Choose from Gallery'"),
      'English choose gallery button must match "Choose from Gallery"'
    );
    assert.ok(
      translationsContent.includes("'scan.needHelp': 'Need help?'"),
      'English voice help title must match "Need help?"'
    );
    assert.ok(
      translationsContent.includes("'scan.playVoiceHelp': 'Play Voice Help'"),
      'English voice help button must match "Play Voice Help"'
    );
    assert.ok(
      translationsContent.includes("'scan.closeCamera': 'Close Camera'"),
      'English close camera button must match "Close Camera"'
    );
  });

  test('Hindi capture screen strings provide complete and consistent localization', () => {
    assert.ok(
      translationsContent.includes("'scan.title': 'तूर पत्ती का फोटो लें'"),
      'Hindi scan title must match "तूर पत्ती का फोटो लें"'
    );
    assert.ok(
      translationsContent.includes("'scan.actionText': 'तूर पत्ती का फोटो लें'"),
      'Hindi scan action card title must match "तूर पत्ती का फोटो लें"'
    );
    assert.ok(
      translationsContent.includes("'scan.tapToOpen': 'कैमरा खोलने के लिए टैप करें'"),
      'Hindi tap to open badge must match "कैमरा खोलने के लिए टैप करें"'
    );
    assert.ok(
      translationsContent.includes("'scan.chooseFromGallery': 'गैलरी से चुनें'"),
      'Hindi choose gallery button must match "गैलरी से चुनें"'
    );
    assert.ok(
      translationsContent.includes("'scan.needHelp': 'मदद चाहिए?'"),
      'Hindi voice help title must match "मदद चाहिए?"'
    );
    assert.ok(
      translationsContent.includes("'scan.playVoiceHelp': 'आवाज मार्गदर्शन सुनें'"),
      'Hindi voice help button must match "आवाज मार्गदर्शन सुनें"'
    );
  });

  test('Duplicate SCAN_STRINGS dictionary is removed from scan.tsx in favor of translations.ts', () => {
    assert.ok(
      !scanContent.includes('const SCAN_STRINGS'),
      'scan.tsx must not declare duplicate SCAN_STRINGS dictionary'
    );
  });

  test('scanText is derived strictly from centralized t(...) translation function', () => {
    assert.ok(
      scanContent.includes("title: t('scan.title')"),
      'scanText.title must use t("scan.title")'
    );
    assert.ok(
      scanContent.includes("subtitle: t('scan.subtitle')"),
      'scanText.subtitle must use t("scan.subtitle")'
    );
    assert.ok(
      scanContent.includes("actionText: t('scan.actionText')"),
      'scanText.actionText must use t("scan.actionText")'
    );
    assert.ok(
      scanContent.includes("tapToOpen: t('scan.tapToOpen')"),
      'scanText.tapToOpen must use t("scan.tapToOpen")'
    );
    assert.ok(
      scanContent.includes("voiceGuide: t('scan.voiceGuide')"),
      'scanText.voiceGuide must use t("scan.voiceGuide")'
    );
    assert.ok(
      scanContent.includes("needHelp: t('scan.needHelp')"),
      'scanText.needHelp must use t("scan.needHelp")'
    );
    assert.ok(
      scanContent.includes("playVoiceHelp: t('scan.playVoiceHelp')"),
      'scanText.playVoiceHelp must use t("scan.playVoiceHelp")'
    );
    assert.ok(
      scanContent.includes("closeCamera: t('scan.closeCamera')"),
      'scanText.closeCamera must use t("scan.closeCamera")'
    );
  });

  test('All alerts, errors, and accessibility hints in scan.tsx use localized keys', () => {
    // Check that hardcoded English alert titles/messages were replaced with t(...)
    assert.ok(
      !scanContent.includes("Alert.alert('Photo could not be prepared'"),
      'Hardcoded alert "Photo could not be prepared" must be replaced with t("scan.photoPrepErrorTitle")'
    );
    assert.ok(
      !scanContent.includes("Alert.alert('Photo unavailable'"),
      'Hardcoded alert "Photo unavailable" must be replaced with t("scan.photoUnavailableTitle")'
    );
    assert.ok(
      !scanContent.includes("setUploadError('Session expired. Please log in again.')"),
      'Hardcoded error "Session expired" must be replaced with t("scan.sessionExpired")'
    );
    assert.ok(
      !scanContent.includes("setUploadError('Upload failed. Please check your connection and try again.')"),
      'Hardcoded error "Upload failed" must be replaced with t("scan.uploadFailed")'
    );

    // Check accessibility hints and labels are localized
    assert.ok(
      scanContent.includes("accessibilityHint={t('scan.openCameraHint')}"),
      'Hero camera card must use localized openCameraHint'
    );
    assert.ok(
      scanContent.includes("accessibilityHint={t('scan.galleryHint')}"),
      'Gallery buttons must use localized galleryHint'
    );
    assert.ok(
      scanContent.includes("accessibilityHint={t('scan.playVoiceHint')}"),
      'Voice help button must use localized playVoiceHint'
    );
    assert.ok(
      scanContent.includes("accessibilityHint={t('scan.captureHint')}"),
      'Capture button must use localized captureHint'
    );
    assert.ok(
      scanContent.includes("accessibilityHint={t('scan.retakeHint')}"),
      'Retake button must use localized retakeHint'
    );
    assert.ok(
      scanContent.includes("accessibilityHint={t('scan.usePhotoHint')}"),
      'Use photo button must use localized usePhotoHint'
    );
  });
});
