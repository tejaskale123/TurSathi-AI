import { useEffect, useRef, useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useLanguage } from '../i18n/LanguageContext';
import { Language } from '../i18n/translations';
import { registerUser } from '../config/api';
import { saveAuthToken } from '../config/tokenStore';
import GoogleIcon from '../components/GoogleIcon';

type FieldName = 'name' | 'mobile' | 'email' | 'password' | 'confirmPassword' | 'terms';
type PrototypeRegistration = {
  name: string;
  mobile: string;
  email: string;
  password: string;
};

const copy = {
  en: {
    subtitle: 'Tur Leaf Disease Detection & Smart Spray Guidance',
    heading: 'Create your account',
    intro: 'A healthier Tur crop starts with the right guidance.',
    name: 'Full Name',
    mobile: 'Mobile Number',
    email: 'Email Address (optional)',
    password: 'Password',
    confirmPassword: 'Confirm Password',
    terms: 'I agree to the Terms of Service and Privacy Policy.',
    create: 'Create Account',
    loading: 'Checking details...',
    or: 'OR',
    google: 'Continue with Google',
    accountPrompt: 'Already have an account?',
    login: 'Login',
    requiredName: 'Enter your full name.',
    requiredMobile: 'Enter your mobile number.',
    invalidMobile: 'Enter a valid 10-digit mobile number.',
    invalidEmail: 'Enter a valid email address or leave it blank.',
    requiredPassword: 'Enter a password with at least 8 characters.',
    mismatch: 'The passwords do not match.',
    requiredTerms: 'Please accept the Terms of Service and Privacy Policy.',
    googleInfo: 'Google sign-in is not connected yet. No account has been created.',
  },
  mr: {
    subtitle: 'तूर पान रोग ओळख आणि योग्य फवारणी मार्गदर्शन',
    heading: 'तुमचे खाते तयार करा',
    intro: 'योग्य मार्गदर्शनाने तूर पीक अधिक निरोगी राहील.',
    name: 'पूर्ण नाव',
    mobile: 'मोबाइल नंबर',
    email: 'ईमेल पत्ता (ऐच्छिक)',
    password: 'पासवर्ड',
    confirmPassword: 'पासवर्डची पुष्टी करा',
    terms: 'मी सेवा अटी आणि गोपनीयता धोरणाशी सहमत आहे.',
    create: 'खाते तयार करा',
    loading: 'तपशील तपासत आहे...',
    or: 'किंवा',
    google: 'Google सह सुरू ठेवा',
    accountPrompt: 'आधीपासून खाते आहे?',
    login: 'लॉगिन',
    requiredName: 'तुमचे पूर्ण नाव भरा.',
    requiredMobile: 'मोबाइल नंबर भरा.',
    invalidMobile: 'वैध १० अंकी मोबाइल नंबर भरा.',
    invalidEmail: 'वैध ईमेल पत्ता भरा किंवा रिक्त ठेवा.',
    requiredPassword: 'किमान ८ अक्षरांचा पासवर्ड भरा.',
    mismatch: 'दोन्ही पासवर्ड जुळत नाहीत.',
    requiredTerms: 'कृपया सेवा अटी आणि गोपनीयता धोरण मान्य करा.',
    googleInfo: 'Google लॉगिन अद्याप जोडलेले नाही. खाते तयार केलेले नाही.',
  },
  hi: {
    subtitle: 'तूर पत्ती रोग पहचान और सही छिड़काव मार्गदर्शन',
    heading: 'अपना खाता बनाएं',
    intro: 'सही मार्गदर्शन से तूर की फसल स्वस्थ रखें।',
    name: 'पूरा नाम',
    mobile: 'मोबाइल नंबर',
    email: 'ईमेल पता (वैकल्पिक)',
    password: 'पासवर्ड',
    confirmPassword: 'पासवर्ड की पुष्टि करें',
    terms: 'मैं सेवा की शर्तों और गोपनीयता नीति से सहमत हूं।',
    create: 'खाता बनाएं',
    loading: 'जानकारी जांच रहे हैं...',
    or: 'या',
    google: 'Google से जारी रखें',
    accountPrompt: 'पहले से खाता है?',
    login: 'लॉगिन',
    requiredName: 'अपना पूरा नाम दर्ज करें।',
    requiredMobile: 'अपना मोबाइल नंबर दर्ज करें।',
    invalidMobile: '10 अंकों का सही मोबाइल नंबर दर्ज करें।',
    invalidEmail: 'सही ईमेल पता दर्ज करें या इसे खाली छोड़ें।',
    requiredPassword: 'कम से कम 8 अक्षरों का पासवर्ड दर्ज करें।',
    mismatch: 'दोनों पासवर्ड मेल नहीं खाते।',
    requiredTerms: 'कृपया सेवा की शर्तें और गोपनीयता नीति स्वीकार करें।',
    googleInfo: 'Google लॉगिन अभी जुड़ा नहीं है। खाता नहीं बनाया गया है।',
  },
} satisfies Record<Language, Record<string, string>>;

export default function RegisterScreen() {
  const router = useRouter();
  const { language } = useLanguage();
  const [name, setName] = useState('');
  const [mobile, setMobile] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState<Partial<Record<FieldName, string>>>({});
  const [message, setMessage] = useState('');
  const loadingTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const text = copy[language];

  useEffect(() => () => {
    if (loadingTimer.current) clearTimeout(loadingTimer.current);
  }, []);

  const clearError = (field: FieldName) => {
    if (errors[field]) setErrors((current) => ({ ...current, [field]: undefined }));
  };

  const handleCreateAccount = async () => {
    const nextErrors: Partial<Record<FieldName, string>> = {};
    const normalizedMobile = mobile.replace(/[\s()-]/g, '').replace(/^\+91/, '');

    if (!name.trim()) nextErrors.name = text.requiredName;
    if (!mobile.trim()) {
      nextErrors.mobile = text.requiredMobile;
    } else if (!/^[6-9]\d{9}$/.test(normalizedMobile)) {
      nextErrors.mobile = text.invalidMobile;
    }
    if (email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      nextErrors.email = text.invalidEmail;
    }
    if (password.length < 8) nextErrors.password = text.requiredPassword;
    if (!confirmPassword) {
      nextErrors.confirmPassword = text.requiredPassword;
    } else if (password !== confirmPassword) {
      nextErrors.confirmPassword = text.mismatch;
    }
    if (!acceptedTerms) nextErrors.terms = text.requiredTerms;

    setErrors(nextErrors);
    setMessage('');
    if (Object.keys(nextErrors).length > 0) return;

    setIsLoading(true);
    try {
      const regResult = await registerUser({
        full_name: name.trim(),
        mobile_number: normalizedMobile,
        email: email.trim() || undefined,
        password: password,
        confirm_password: confirmPassword,
      });
      // Backend returns Token { access_token, user } — save it for scan uploads
      if (regResult?.access_token) {
        await saveAuthToken(regResult.access_token);
      }
      setIsLoading(false);
      router.replace('/scan');
    } catch (err: any) {
      setIsLoading(false);
      setMessage(err.message || 'Registration failed. Please try again.');
    }
  };

  const fieldError = (field: FieldName) =>
    errors[field] ? <Text style={styles.errorText}>{errors[field]}</Text> : null;

  return (
    <SafeAreaView style={styles.safeArea}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.page}>
            <View style={styles.header}>
              <View style={styles.brandMark} accessibilityLabel="Tur leaf mark">
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
              <Text style={styles.brandSubtitle}>{text.subtitle}</Text>
            </View>

            <View style={styles.formPanel}>
              <Text style={styles.heading}>{text.heading}</Text>
              <Text style={styles.intro}>{text.intro}</Text>

              <Text style={styles.label}>{text.name}</Text>
              <TextInput
                accessibilityLabel={text.name}
                autoCapitalize="words"
                autoComplete="name"
                onChangeText={(value) => {
                  setName(value);
                  clearError('name');
                }}
                placeholder={text.name}
                placeholderTextColor="#89958A"
                returnKeyType="next"
                style={[styles.input, errors.name ? styles.inputError : null]}
                value={name}
              />
              {fieldError('name')}

              <Text style={[styles.label, styles.fieldSpacing]}>{text.mobile}</Text>
              <TextInput
                accessibilityLabel={text.mobile}
                autoComplete="tel"
                keyboardType="phone-pad"
                onChangeText={(value) => {
                  setMobile(value);
                  clearError('mobile');
                }}
                placeholder={text.mobile}
                placeholderTextColor="#89958A"
                returnKeyType="next"
                style={[styles.input, errors.mobile ? styles.inputError : null]}
                value={mobile}
              />
              {fieldError('mobile')}

              <Text style={[styles.label, styles.fieldSpacing]}>{text.email}</Text>
              <TextInput
                accessibilityLabel={text.email}
                autoCapitalize="none"
                autoComplete="email"
                autoCorrect={false}
                keyboardType="email-address"
                onChangeText={(value) => {
                  setEmail(value);
                  clearError('email');
                }}
                placeholder={text.email}
                placeholderTextColor="#89958A"
                returnKeyType="next"
                style={[styles.input, errors.email ? styles.inputError : null]}
                value={email}
              />
              {fieldError('email')}

              <Text style={[styles.label, styles.fieldSpacing]}>{text.password}</Text>
              <View style={[styles.passwordInput, errors.password ? styles.inputError : null]}>
                <TextInput
                  accessibilityLabel={text.password}
                  autoCapitalize="none"
                  autoComplete="new-password"
                  onChangeText={(value) => {
                    setPassword(value);
                    clearError('password');
                  }}
                  placeholder={text.password}
                  placeholderTextColor="#89958A"
                  returnKeyType="next"
                  secureTextEntry={!showPassword}
                  style={styles.passwordTextInput}
                  value={password}
                />
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel={showPassword ? 'Hide password' : 'Show password'}
                  hitSlop={10}
                  onPress={() => setShowPassword((visible) => !visible)}
                  style={styles.visibilityButton}
                >
                  <Text style={styles.visibilityText}>{showPassword ? 'HIDE' : 'SHOW'}</Text>
                </Pressable>
              </View>
              {fieldError('password')}

              <Text style={[styles.label, styles.fieldSpacing]}>{text.confirmPassword}</Text>
              <View style={[styles.passwordInput, errors.confirmPassword ? styles.inputError : null]}>
                <TextInput
                  accessibilityLabel={text.confirmPassword}
                  autoCapitalize="none"
                  autoComplete="new-password"
                  onChangeText={(value) => {
                    setConfirmPassword(value);
                    clearError('confirmPassword');
                  }}
                  placeholder={text.confirmPassword}
                  placeholderTextColor="#89958A"
                  returnKeyType="done"
                  secureTextEntry={!showConfirmPassword}
                  style={styles.passwordTextInput}
                  value={confirmPassword}
                />
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel={showConfirmPassword ? 'Hide password' : 'Show password'}
                  hitSlop={10}
                  onPress={() => setShowConfirmPassword((visible) => !visible)}
                  style={styles.visibilityButton}
                >
                  <Text style={styles.visibilityText}>{showConfirmPassword ? 'HIDE' : 'SHOW'}</Text>
                </Pressable>
              </View>
              {fieldError('confirmPassword')}

              <Pressable
                accessibilityRole="checkbox"
                accessibilityState={{ checked: acceptedTerms }}
                onPress={() => {
                  setAcceptedTerms((accepted) => !accepted);
                  clearError('terms');
                }}
                style={styles.termsRow}
              >
                <View style={[styles.checkbox, acceptedTerms ? styles.checkboxChecked : null]}>
                  {acceptedTerms ? <View style={styles.checkboxTick} /> : null}
                </View>
                <Text style={styles.termsText}>{text.terms}</Text>
              </Pressable>
              {fieldError('terms')}

              {message ? (
                <Text accessibilityRole="alert" style={styles.notice}>
                  {message}
                </Text>
              ) : null}

              <Pressable
                accessibilityRole="button"
                disabled={isLoading}
                onPress={handleCreateAccount}
                style={({ pressed }) => [
                  styles.primaryButton,
                  pressed && !isLoading ? styles.buttonPressed : null,
                  isLoading ? styles.buttonLoading : null,
                ]}
              >
                <Text style={styles.primaryButtonText}>{isLoading ? text.loading : text.create}</Text>
                {!isLoading ? <View style={styles.buttonArrow} /> : null}
              </Pressable>

              <View style={styles.divider}>
                <View style={styles.dividerLine} />
                <Text style={styles.dividerText}>{text.or}</Text>
                <View style={styles.dividerLine} />
              </View>

              <Pressable
                accessibilityRole="button"
                onPress={() => setMessage(text.googleInfo)}
                style={({ pressed }) => [styles.googleButton, pressed ? styles.googlePressed : null]}
              >
                <GoogleIcon size={20} />
                <Text style={styles.googleButtonText}>{text.google}</Text>
              </Pressable>

              <View style={styles.loginRow}>
                <Text style={styles.loginPrompt}>{text.accountPrompt} </Text>
                <Pressable
                  accessibilityRole="link"
                  onPress={() => router.push('/login')}
                  hitSlop={8}
                >
                  <Text style={styles.loginLink}>{text.login}</Text>
                </Pressable>
              </View>
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  flex: {
    flex: 1,
  },
  safeArea: {
    flex: 1,
    backgroundColor: '#103B2D',
  },
  scrollContent: {
    flexGrow: 1,
    alignItems: 'center',
  },
  page: {
    width: '100%',
    maxWidth: 480,
    paddingHorizontal: 22,
    paddingTop: 25,
    paddingBottom: 18,
  },
  header: {
    alignItems: 'center',
    paddingBottom: 21,
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
  brandSubtitle: {
    maxWidth: 290,
    marginTop: 7,
    color: '#D3DDCF',
    fontSize: 12,
    fontWeight: '400',
    lineHeight: 17,
    textAlign: 'center',
  },
  formPanel: {
    width: '100%',
    paddingHorizontal: 21,
    paddingTop: 22,
    paddingBottom: 20,
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
    fontSize: 25,
    fontWeight: '700',
    textAlign: 'center',
  },
  intro: {
    marginTop: 6,
    marginBottom: 18,
    color: '#647369',
    fontSize: 13,
    lineHeight: 19,
    textAlign: 'center',
  },
  label: {
    marginBottom: 7,
    color: '#263C30',
    fontSize: 13,
    fontWeight: '600',
  },
  fieldSpacing: {
    marginTop: 13,
  },
  input: {
    height: 51,
    paddingHorizontal: 15,
    borderWidth: 1,
    borderColor: '#D9DED4',
    borderRadius: 13,
    backgroundColor: '#FFFEFA',
    color: '#1D3328',
    fontSize: 15,
  },
  inputError: {
    borderColor: '#C75A4A',
  },
  errorText: {
    marginTop: 5,
    color: '#B34438',
    fontSize: 12,
    lineHeight: 16,
  },
  passwordInput: {
    minHeight: 51,
    flexDirection: 'row',
    alignItems: 'center',
    paddingLeft: 15,
    paddingRight: 8,
    borderWidth: 1,
    borderColor: '#D9DED4',
    borderRadius: 13,
    backgroundColor: '#FFFEFA',
  },
  passwordTextInput: {
    flex: 1,
    minHeight: 49,
    paddingVertical: 0,
    color: '#1D3328',
    fontSize: 15,
  },
  visibilityButton: {
    minWidth: 48,
    minHeight: 42,
    alignItems: 'center',
    justifyContent: 'center',
  },
  visibilityText: {
    color: '#55745F',
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.6,
  },
  termsRow: {
    minHeight: 44,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 9,
    marginTop: 10,
  },
  checkbox: {
    width: 18,
    height: 18,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#9AA89B',
    borderRadius: 5,
    backgroundColor: '#FFFEFA',
  },
  checkboxChecked: {
    borderColor: '#267451',
    backgroundColor: '#267451',
  },
  checkboxTick: {
    width: 6,
    height: 9,
    borderRightWidth: 1.5,
    borderBottomWidth: 1.5,
    borderColor: '#FFFFFF',
    transform: [{ rotate: '45deg' }, { translateY: -1 }],
  },
  termsText: {
    flex: 1,
    color: '#526458',
    fontSize: 12,
    lineHeight: 18,
  },
  notice: {
    marginBottom: 11,
    paddingHorizontal: 11,
    paddingVertical: 9,
    borderRadius: 9,
    overflow: 'hidden',
    backgroundColor: '#E9EFE5',
    color: '#315B43',
    fontSize: 12,
    lineHeight: 17,
  },
  primaryButton: {
    minHeight: 51,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 13,
    borderRadius: 13,
    backgroundColor: '#267451',
    shadowColor: '#1C5F40',
    shadowOffset: { width: 0, height: 5 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 3,
  },
  buttonPressed: {
    opacity: 0.9,
    transform: [{ scale: 0.99 }],
  },
  buttonLoading: {
    opacity: 0.72,
  },
  primaryButtonText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '700',
  },
  buttonArrow: {
    position: 'absolute',
    right: 19,
    width: 8,
    height: 8,
    borderTopWidth: 1.5,
    borderRightWidth: 1.5,
    borderColor: '#F2D98F',
    transform: [{ rotate: '45deg' }],
  },
  divider: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginVertical: 17,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: '#DFE2D9',
  },
  dividerText: {
    color: '#879187',
    fontSize: 10,
    fontWeight: '600',
    letterSpacing: 1,
  },
  googleButton: {
    minHeight: 49,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    borderWidth: 1,
    borderColor: '#D6DBD2',
    borderRadius: 13,
    backgroundColor: '#FFFEFA',
  },
  googlePressed: {
    backgroundColor: '#F0F2EB',
  },

  googleButtonText: {
    color: '#34493B',
    fontSize: 13,
    fontWeight: '600',
  },
  loginRow: {
    minHeight: 43,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    flexWrap: 'wrap',
    marginTop: 7,
  },
  loginPrompt: {
    color: '#66746A',
    fontSize: 12,
  },
  loginLink: {
    color: '#236C4C',
    fontSize: 12,
    fontWeight: '700',
  },
});
