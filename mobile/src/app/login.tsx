import { useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter, type Href } from 'expo-router';
import { useLanguage } from '../i18n/LanguageContext';
import { Language } from '../i18n/translations';

import { loginUser } from '../config/api';
import { saveAuthToken } from '../config/tokenStore';
import GoogleIcon from '../components/GoogleIcon';

type FieldName = 'identity' | 'password';

const copy = {
  en: {
    subtitle: 'Tur Leaf Disease Detection & Smart Spray Guidance',
    welcome: 'Welcome back',
    intro: 'Sign in to continue caring for your Tur crop.',
    identity: 'Email or Mobile Number',
    password: 'Password',
    remember: 'Remember me',
    forgot: 'Forgot password?',
    login: 'Login',
    loading: 'Please wait...',
    or: 'OR',
    google: 'Continue with Google',
    registerPrompt: "Don't have an account?",
    register: 'Register',
    requiredIdentity: 'Enter your email address or mobile number.',
    requiredPassword: 'Enter your password.',
    unavailable: 'Login is not connected yet. Your details have not been submitted.',
    forgotInfo: 'Password recovery will be available once account services are connected.',
    googleInfo: 'Google sign-in is not set up yet. No account was created.',
  },
  mr: {
    subtitle: 'तूर पान रोग ओळख आणि योग्य फवारणी मार्गदर्शन',
    welcome: 'पुन्हा स्वागत आहे',
    intro: 'तुमच्या तूर पिकाची काळजी सुरू ठेवण्यासाठी लॉगिन करा.',
    identity: 'ईमेल किंवा मोबाइल नंबर',
    password: 'पासवर्ड',
    remember: 'मला लक्षात ठेवा',
    forgot: 'पासवर्ड विसरलात?',
    login: 'लॉगिन',
    loading: 'कृपया थांबा...',
    or: 'किंवा',
    google: 'Google सह सुरू ठेवा',
    registerPrompt: 'खाते नाही?',
    register: 'नोंदणी करा',
    requiredIdentity: 'ईमेल किंवा मोबाइल नंबर भरा.',
    requiredPassword: 'पासवर्ड भरा.',
    unavailable: 'लॉगिन सेवा अद्याप जोडलेली नाही. तुमची माहिती पाठवलेली नाही.',
    forgotInfo: 'खाते सेवा जोडल्यावर पासवर्ड पुनर्प्राप्ती उपलब्ध होईल.',
    googleInfo: 'Google लॉगिन अद्याप सेट केलेले नाही. खाते तयार झालेले नाही.',
  },
  hi: {
    subtitle: 'तूर पत्ती रोग पहचान और सही छिड़काव मार्गदर्शन',
    welcome: 'वापसी पर स्वागत है',
    intro: 'अपनी तूर फसल की देखभाल जारी रखने के लिए लॉगिन करें।',
    identity: 'ईमेल या मोबाइल नंबर',
    password: 'पासवर्ड',
    remember: 'मुझे याद रखें',
    forgot: 'पासवर्ड भूल गए?',
    login: 'लॉगिन',
    loading: 'कृपया प्रतीक्षा करें...',
    or: 'या',
    google: 'Google से जारी रखें',
    registerPrompt: 'खाता नहीं है?',
    register: 'रजिस्टर करें',
    requiredIdentity: 'ईमेल या मोबाइल नंबर दर्ज करें।',
    requiredPassword: 'पासवर्ड दर्ज करें।',
    unavailable: 'लॉगिन सेवा अभी उपलब्ध नहीं है। आपकी जानकारी जमा नहीं की गई।',
    forgotInfo: 'खाता सेवाएं जुड़ने के बाद पासवर्ड रिकवरी उपलब्ध होगी।',
    googleInfo: 'Google लॉगिन अभी सेट नहीं है। कोई खाता नहीं बनाया गया।',
  },
} satisfies Record<Language, Record<string, string>>;

export default function LoginScreen() {
  const router = useRouter();
  const { language } = useLanguage();
  const [identity, setIdentity] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState<Partial<Record<FieldName, string>>>({});
  const [message, setMessage] = useState('');
  const text = copy[language];

  const handleLogin = async () => {
    if (isLoading) return;
    const nextErrors: Partial<Record<FieldName, string>> = {};
    if (!identity.trim()) nextErrors.identity = text.requiredIdentity;
    if (!password.trim()) nextErrors.password = text.requiredPassword;
    setErrors(nextErrors);
    setMessage('');

    if (Object.keys(nextErrors).length > 0) return;

    setIsLoading(true);
    try {
      const authResult = await loginUser({
        identifier: identity.trim(),
        password: password,
      });
      if (authResult && authResult.access_token && authResult.user) {
        // Persist the JWT so the scan screen can use it for authenticated uploads
        await saveAuthToken(authResult.access_token);
        setIsLoading(false);
        router.replace('/scan' as Href);
      } else {
        throw new Error('Invalid authentication response from server.');
      }
    } catch (err: any) {
      setIsLoading(false);
      setMessage(err.message || 'Unable to connect to server. Please check your connection and try again.');
    }
  };

  const updateIdentity = (value: string) => {
    setIdentity(value);
    if (errors.identity) setErrors((current) => ({ ...current, identity: undefined }));
  };

  const updatePassword = (value: string) => {
    setPassword(value);
    if (errors.password) setErrors((current) => ({ ...current, password: undefined }));
  };

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
              <Text style={styles.heading}>{text.welcome}</Text>
              <Text style={styles.intro}>{text.intro}</Text>

              <Text style={styles.label}>{text.identity}</Text>
              <TextInput
                accessibilityLabel={text.identity}
                autoCapitalize="none"
                autoComplete="username"
                autoCorrect={false}
                keyboardType="email-address"
                onChangeText={updateIdentity}
                onSubmitEditing={handleLogin}
                placeholder={text.identity}
                placeholderTextColor="#89958A"
                returnKeyType="next"
                style={[styles.input, errors.identity ? styles.inputError : null]}
                value={identity}
              />
              {errors.identity ? <Text style={styles.errorText}>{errors.identity}</Text> : null}

              <Text style={[styles.label, styles.passwordLabel]}>{text.password}</Text>
              <View style={[styles.passwordInput, errors.password ? styles.inputError : null]}>
                <TextInput
                  accessibilityLabel={text.password}
                  autoCapitalize="none"
                  autoComplete="current-password"
                  onChangeText={updatePassword}
                  onSubmitEditing={handleLogin}
                  placeholder={text.password}
                  placeholderTextColor="#89958A"
                  returnKeyType="done"
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
              {errors.password ? <Text style={styles.errorText}>{errors.password}</Text> : null}

              <View style={styles.optionsRow}>
                <Pressable
                  accessibilityRole="checkbox"
                  accessibilityState={{ checked: remember }}
                  onPress={() => setRemember((checked) => !checked)}
                  style={styles.rememberButton}
                >
                  <View style={[styles.checkbox, remember ? styles.checkboxChecked : null]}>
                    {remember ? <View style={styles.checkboxTick} /> : null}
                  </View>
                  <Text style={styles.rememberText}>{text.remember}</Text>
                </Pressable>
                <Pressable
                  accessibilityRole="button"
                  onPress={() => setMessage(text.forgotInfo)}
                  hitSlop={8}
                >
                  <Text style={styles.textLink}>{text.forgot}</Text>
                </Pressable>
              </View>

              {message ? (
                <Text accessibilityRole="alert" style={styles.notice}>
                  {message}
                </Text>
              ) : null}

              <Pressable
                accessibilityRole="button"
                disabled={isLoading}
                onPress={handleLogin}
                style={({ pressed }) => [
                  styles.loginButton,
                  pressed && !isLoading ? styles.buttonPressed : null,
                  isLoading ? styles.buttonLoading : null,
                ]}
              >
                <Text style={styles.loginButtonText}>{isLoading ? text.loading : text.login}</Text>
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

              <View style={styles.registerRow}>
                <Text style={styles.registerPrompt}>{text.registerPrompt} </Text>
                <Pressable
                  accessibilityRole="link"
                  onPress={() => router.push('/register' as Href)}
                  hitSlop={8}
                >
                  <Text style={styles.registerLink}>{text.register}</Text>
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
  passwordLabel: {
    marginTop: 15,
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
  optionsRow: {
    minHeight: 48,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
  },
  rememberButton: {
    minHeight: 42,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
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
  rememberText: {
    color: '#526458',
    fontSize: 12,
  },
  textLink: {
    color: '#236C4C',
    fontSize: 12,
    fontWeight: '700',
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
  loginButton: {
    minHeight: 51,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
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
  loginButtonText: {
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
  registerRow: {
    minHeight: 43,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    flexWrap: 'wrap',
    marginTop: 7,
  },
  registerPrompt: {
    color: '#66746A',
    fontSize: 12,
  },
  registerLink: {
    color: '#236C4C',
    fontSize: 12,
    fontWeight: '700',
  },
});
