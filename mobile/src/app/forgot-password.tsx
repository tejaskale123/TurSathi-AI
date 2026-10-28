import { useEffect, useRef, useState } from 'react';
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
import { useRouter, useLocalSearchParams, type Href } from 'expo-router';
import { useLanguage } from '../i18n/LanguageContext';
import { Language } from '../i18n/translations';
import {
  requestPasswordReset,
  verifyPasswordResetOtp,
  submitPasswordReset,
} from '../config/api';

type Stage = 'email' | 'otp' | 'password';

const copy = {
  en: {
    subtitle: 'Tur Leaf Disease Detection & Smart Spray Guidance',
    title: 'Reset Password',
    introEmail: 'Enter your registered email address to receive a 6-digit verification code.',
    introOtp: 'Enter the 6-digit verification code sent to your email address.',
    introPassword: 'Enter and confirm your new secure password.',
    emailLabel: 'Registered Email Address',
    otpLabel: '6-Digit Verification Code',
    newPasswordLabel: 'New Password',
    confirmPasswordLabel: 'Confirm New Password',
    sendOtp: 'Send OTP',
    sendingOtp: 'Sending Code...',
    verifyOtp: 'Verify Code',
    verifyingOtp: 'Verifying...',
    resetPassword: 'Reset Password',
    resetting: 'Updating Password...',
    resendOtp: 'Resend Code',
    resendIn: 'Resend in',
    changeEmail: 'Change Email',
    backToLogin: 'Back to Login',
    requiredEmail: 'Enter your registered email address.',
    invalidEmail: 'Enter a valid email address.',
    requiredOtp: 'Enter the 6-digit code.',
    invalidOtpLength: 'Code must be exactly 6 digits.',
    requiredPassword: 'Password must be at least 8 characters.',
    mismatch: 'Passwords do not match.',
    codeSentNotice: 'If an account exists, a 6-digit code was sent to your email.',
    codeVerifiedNotice: 'Code verified! Please set your new password.',
    successNotice: 'Password reset successfully! Redirecting to login...',
  },
  mr: {
    subtitle: 'तूर पान रोग ओळख आणि योग्य फवारणी मार्गदर्शन',
    title: 'पासवर्ड रीसेट करा',
    introEmail: '६-अंकी पडताळणी कोड मिळवण्यासाठी तुमचा नोंदणीकृत ईमेल पत्ता भरा.',
    introOtp: 'तुमच्या ईमेलवर पाठवलेला ६-अंकी पडताळणी कोड भरा.',
    introPassword: 'तुमचा नवीन सुरक्षित पासवर्ड भरा आणि पुष्टी करा.',
    emailLabel: 'नोंदणीकृत ईमेल पत्ता',
    otpLabel: '६-अंकी पडताळणी कोड',
    newPasswordLabel: 'नवीन पासवर्ड',
    confirmPasswordLabel: 'नवीन पासवर्डची पुष्टी करा',
    sendOtp: 'ओटीपी पाठवा',
    sendingOtp: 'कोड पाठवत आहे...',
    verifyOtp: 'कोड पडताळा',
    verifyingOtp: 'पडताळणी करत आहे...',
    resetPassword: 'पासवर्ड रीसेट करा',
    resetting: 'बदलत आहे...',
    resendOtp: 'पुन्हा कोड पाठवा',
    resendIn: 'पुन्हा पाठवा',
    changeEmail: 'ईमेल बदला',
    backToLogin: 'लॉगिनवर परत जा',
    requiredEmail: 'नोंदणीकृत ईमेल पत्ता भरा.',
    invalidEmail: 'वैध ईमेल पत्ता भरा.',
    requiredOtp: '६-अंकी कोड भरा.',
    invalidOtpLength: 'कोड ६ अंकी असणे आवश्यक आहे.',
    requiredPassword: 'पासवर्ड किमान ८ अक्षरांचा असावा.',
    mismatch: 'दोन्ही पासवर्ड जुळत नाहीत.',
    codeSentNotice: 'खाते असल्यास तुमच्या ईमेलवर ६-अंकी कोड पाठवला गेला आहे.',
    codeVerifiedNotice: 'कोड पडताळला! कृपया नवीन पासवर्ड सेट करा.',
    successNotice: 'पासवर्ड यशस्वीरीत्या बदलला! लॉगिनकडे जात आहे...',
  },
  hi: {
    subtitle: 'तूर पत्ती रोग पहचान और सही छिड़काव मार्गदर्शन',
    title: 'पासवर्ड रीसेट करें',
    introEmail: '6-अंकीय सत्यापन कोड प्राप्त करने के लिए अपना पंजीकृत ईमेल पता दर्ज करें।',
    introOtp: 'अपने ईमेल पर भेजा गया 6-अंकीय सत्यापन कोड दर्ज करें।',
    introPassword: 'अपना नया सुरक्षित पासवर्ड दर्ज करें और पुष्टि करें।',
    emailLabel: 'पंजीकृत ईमेल पता',
    otpLabel: '6-अंकीय सत्यापन कोड',
    newPasswordLabel: 'नया पासवर्ड',
    confirmPasswordLabel: 'नए पासवर्ड की पुष्टि करें',
    sendOtp: 'ओटीपी भेजें',
    sendingOtp: 'कोड भेजा जा रहा है...',
    verifyOtp: 'कोड सत्यापित करें',
    verifyingOtp: 'सत्यापित हो रहा है...',
    resetPassword: 'पासवर्ड रीसेट करें',
    resetting: 'अपडेट हो रहा है...',
    resendOtp: 'पुनः कोड भेजें',
    resendIn: 'पुनः भेजें',
    changeEmail: 'ईमेल बदलें',
    backToLogin: 'लॉगिन पर वापस जाएं',
    requiredEmail: 'पंजीकृत ईमेल पता दर्ज करें।',
    invalidEmail: 'सही ईमेल पता दर्ज करें।',
    requiredOtp: '6-अंकीय कोड दर्ज करें।',
    invalidOtpLength: 'कोड ठीक 6 अंकों का होना चाहिए।',
    requiredPassword: 'पासवर्ड कम से कम 8 अक्षरों का होना चाहिए।',
    mismatch: 'दोनों पासवर्ड मेल नहीं खाते।',
    codeSentNotice: 'यदि खाता मौजूद है, तो आपके ईमेल पर 6 अंकों का कोड भेजा गया है।',
    codeVerifiedNotice: 'कोड सत्यापित हुआ! कृपया अपना नया पासवर्ड सेट करें।',
    successNotice: 'पासवर्ड सफलतापूर्वक बदल गया! लॉगिन पर भेजा जा रहा है...',
  },
} satisfies Record<Language, Record<string, string>>;

export default function ForgotPasswordScreen() {
  const router = useRouter();
  const { language } = useLanguage();
  const text = copy[language];
  const params = useLocalSearchParams();

  const [stage, setStage] = useState<Stage>('email');
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState('');
  const [resetToken, setResetToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [isLoading, setIsLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});

  // 60-second cooldown timer
  const [cooldown, setCooldown] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Auto-prefill email from navigation query if available
  useEffect(() => {
    if (params.email && typeof params.email === 'string') {
      setEmail(params.email.trim());
    }
  }, [params.email]);

  // Clean up interval timer on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const startCooldown = () => {
    setCooldown(60);
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      setCooldown((prev) => {
        if (prev <= 1) {
          if (timerRef.current) clearInterval(timerRef.current);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  // ---------------- Stage 1: Send OTP ----------------
  const handleSendOtp = async () => {
    const nextErrors: Record<string, string> = {};
    const trimmedEmail = email.trim().toLowerCase();

    if (!trimmedEmail) {
      nextErrors.email = text.requiredEmail;
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      nextErrors.email = text.invalidEmail;
    }

    setErrors(nextErrors);
    setErrorMessage('');
    if (Object.keys(nextErrors).length > 0) return;

    setIsLoading(true);
    setStatusMessage('');
    try {
      const res = await requestPasswordReset(trimmedEmail);
      setIsLoading(false);
      setStatusMessage(res.message || text.codeSentNotice);
      startCooldown();
      setStage('otp');
    } catch (err: any) {
      setIsLoading(false);
      setErrorMessage(err.message || 'Unable to send code. Please try again.');
    }
  };

  // ---------------- Stage 2: Verify OTP ----------------
  const handleVerifyOtp = async () => {
    const nextErrors: Record<string, string> = {};
    const cleanedOtp = otp.trim().replace(/\s+/g, '');

    if (!cleanedOtp) {
      nextErrors.otp = text.requiredOtp;
    } else if (!/^\d{6}$/.test(cleanedOtp)) {
      nextErrors.otp = text.invalidOtpLength;
    }

    setErrors(nextErrors);
    setErrorMessage('');
    if (Object.keys(nextErrors).length > 0) return;

    setIsLoading(true);
    try {
      const res = await verifyPasswordResetOtp(email.trim().toLowerCase(), cleanedOtp);
      setIsLoading(false);
      if (res?.reset_token) {
        setResetToken(res.reset_token);
        setStatusMessage(text.codeVerifiedNotice);
        setStage('password');
      } else {
        throw new Error('Invalid verification response from server.');
      }
    } catch (err: any) {
      setIsLoading(false);
      setErrorMessage(err.message || 'Invalid verification code.');
    }
  };

  // ---------------- Stage 3: Reset Password ----------------
  const handleResetPassword = async () => {
    const nextErrors: Record<string, string> = {};

    if (newPassword.length < 8) {
      nextErrors.newPassword = text.requiredPassword;
    }
    if (!confirmPassword) {
      nextErrors.confirmPassword = text.requiredPassword;
    } else if (newPassword !== confirmPassword) {
      nextErrors.confirmPassword = text.mismatch;
    }

    setErrors(nextErrors);
    setErrorMessage('');
    if (Object.keys(nextErrors).length > 0) return;

    setIsLoading(true);
    try {
      await submitPasswordReset({
        reset_token: resetToken,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      setIsLoading(false);
      setStatusMessage(text.successNotice);

      // Redirect user to login with success indicator
      setTimeout(() => {
        router.replace({
          pathname: '/login',
          params: { reset_success: '1', email: email.trim().toLowerCase() },
        } as any);
      }, 1200);
    } catch (err: any) {
      setIsLoading(false);
      setErrorMessage(err.message || 'Failed to reset password. Please try again.');
    }
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
            {/* Header / Brand */}
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

            {/* Form Panel */}
            <View style={styles.formPanel}>
              <Text style={styles.heading}>{text.title}</Text>
              <Text style={styles.intro}>
                {stage === 'email' && text.introEmail}
                {stage === 'otp' && text.introOtp}
                {stage === 'password' && text.introPassword}
              </Text>

              {/* Status Message */}
              {statusMessage ? (
                <View style={styles.noticeBox}>
                  <Text style={styles.noticeText}>{statusMessage}</Text>
                </View>
              ) : null}

              {/* Error Message */}
              {errorMessage ? (
                <View style={styles.errorBox}>
                  <Text style={styles.errorBoxText}>{errorMessage}</Text>
                </View>
              ) : null}

              {/* ================= STAGE 1: EMAIL ================= */}
              {stage === 'email' && (
                <View>
                  <Text style={styles.label}>{text.emailLabel}</Text>
                  <TextInput
                    accessibilityLabel={text.emailLabel}
                    autoCapitalize="none"
                    autoComplete="email"
                    autoCorrect={false}
                    keyboardType="email-address"
                    onChangeText={(val) => {
                      setEmail(val);
                      if (errors.email) setErrors((prev) => ({ ...prev, email: '' }));
                    }}
                    onSubmitEditing={handleSendOtp}
                    placeholder={text.emailLabel}
                    placeholderTextColor="#89958A"
                    returnKeyType="done"
                    style={[styles.input, errors.email ? styles.inputError : null]}
                    value={email}
                  />
                  {errors.email ? <Text style={styles.errorText}>{errors.email}</Text> : null}

                  <Pressable
                    accessibilityRole="button"
                    disabled={isLoading}
                    onPress={handleSendOtp}
                    style={({ pressed }) => [
                      styles.primaryButton,
                      pressed && !isLoading ? styles.buttonPressed : null,
                      isLoading ? styles.buttonLoading : null,
                    ]}
                  >
                    <Text style={styles.primaryButtonText}>
                      {isLoading ? text.sendingOtp : text.sendOtp}
                    </Text>
                    {!isLoading && <View style={styles.buttonArrow} />}
                  </Pressable>
                </View>
              )}

              {/* ================= STAGE 2: OTP ================= */}
              {stage === 'otp' && (
                <View>
                  <View style={styles.emailBadgeRow}>
                    <Text style={styles.emailBadgeText} numberOfLines={1}>
                      {email.trim().toLowerCase()}
                    </Text>
                    <Pressable
                      accessibilityRole="button"
                      onPress={() => {
                        setStage('email');
                        setErrorMessage('');
                      }}
                      hitSlop={6}
                    >
                      <Text style={styles.changeEmailText}>{text.changeEmail}</Text>
                    </Pressable>
                  </View>

                  <Text style={styles.label}>{text.otpLabel}</Text>
                  <TextInput
                    accessibilityLabel={text.otpLabel}
                    autoCapitalize="none"
                    autoCorrect={false}
                    keyboardType="number-pad"
                    maxLength={6}
                    onChangeText={(val) => {
                      setOtp(val.replace(/\D/g, ''));
                      if (errors.otp) setErrors((prev) => ({ ...prev, otp: '' }));
                    }}
                    onSubmitEditing={handleVerifyOtp}
                    placeholder="123456"
                    placeholderTextColor="#89958A"
                    returnKeyType="done"
                    style={[
                      styles.input,
                      styles.otpInput,
                      errors.otp ? styles.inputError : null,
                    ]}
                    value={otp}
                  />
                  {errors.otp ? <Text style={styles.errorText}>{errors.otp}</Text> : null}

                  <Pressable
                    accessibilityRole="button"
                    disabled={isLoading}
                    onPress={handleVerifyOtp}
                    style={({ pressed }) => [
                      styles.primaryButton,
                      pressed && !isLoading ? styles.buttonPressed : null,
                      isLoading ? styles.buttonLoading : null,
                    ]}
                  >
                    <Text style={styles.primaryButtonText}>
                      {isLoading ? text.verifyingOtp : text.verifyOtp}
                    </Text>
                    {!isLoading && <View style={styles.buttonArrow} />}
                  </Pressable>

                  {/* Resend OTP button with cooldown */}
                  <View style={styles.resendRow}>
                    {cooldown > 0 ? (
                      <Text style={styles.resendCooldownText}>
                        {text.resendIn} {cooldown}s
                      </Text>
                    ) : (
                      <Pressable
                        accessibilityRole="button"
                        disabled={isLoading}
                        onPress={handleSendOtp}
                        hitSlop={8}
                      >
                        <Text style={styles.resendActiveText}>{text.resendOtp}</Text>
                      </Pressable>
                    )}
                  </View>
                </View>
              )}

              {/* ================= STAGE 3: PASSWORD ================= */}
              {stage === 'password' && (
                <View>
                  <Text style={styles.label}>{text.newPasswordLabel}</Text>
                  <View style={[styles.passwordInput, errors.newPassword ? styles.inputError : null]}>
                    <TextInput
                      accessibilityLabel={text.newPasswordLabel}
                      autoCapitalize="none"
                      autoComplete="new-password"
                      onChangeText={(val) => {
                        setNewPassword(val);
                        if (errors.newPassword) setErrors((prev) => ({ ...prev, newPassword: '' }));
                      }}
                      placeholder={text.newPasswordLabel}
                      placeholderTextColor="#89958A"
                      returnKeyType="next"
                      secureTextEntry={!showNewPassword}
                      style={styles.passwordTextInput}
                      value={newPassword}
                    />
                    <Pressable
                      accessibilityRole="button"
                      hitSlop={10}
                      onPress={() => setShowNewPassword((v) => !v)}
                      style={styles.visibilityButton}
                    >
                      <Text style={styles.visibilityText}>
                        {showNewPassword ? 'HIDE' : 'SHOW'}
                      </Text>
                    </Pressable>
                  </View>
                  {errors.newPassword ? <Text style={styles.errorText}>{errors.newPassword}</Text> : null}

                  <Text style={[styles.label, styles.fieldSpacing]}>{text.confirmPasswordLabel}</Text>
                  <View style={[styles.passwordInput, errors.confirmPassword ? styles.inputError : null]}>
                    <TextInput
                      accessibilityLabel={text.confirmPasswordLabel}
                      autoCapitalize="none"
                      autoComplete="new-password"
                      onChangeText={(val) => {
                        setConfirmPassword(val);
                        if (errors.confirmPassword) setErrors((prev) => ({ ...prev, confirmPassword: '' }));
                      }}
                      onSubmitEditing={handleResetPassword}
                      placeholder={text.confirmPasswordLabel}
                      placeholderTextColor="#89958A"
                      returnKeyType="done"
                      secureTextEntry={!showConfirmPassword}
                      style={styles.passwordTextInput}
                      value={confirmPassword}
                    />
                    <Pressable
                      accessibilityRole="button"
                      hitSlop={10}
                      onPress={() => setShowConfirmPassword((v) => !v)}
                      style={styles.visibilityButton}
                    >
                      <Text style={styles.visibilityText}>
                        {showConfirmPassword ? 'HIDE' : 'SHOW'}
                      </Text>
                    </Pressable>
                  </View>
                  {errors.confirmPassword ? <Text style={styles.errorText}>{errors.confirmPassword}</Text> : null}

                  <Pressable
                    accessibilityRole="button"
                    disabled={isLoading}
                    onPress={handleResetPassword}
                    style={({ pressed }) => [
                      styles.primaryButton,
                      pressed && !isLoading ? styles.buttonPressed : null,
                      isLoading ? styles.buttonLoading : null,
                    ]}
                  >
                    <Text style={styles.primaryButtonText}>
                      {isLoading ? text.resetting : text.resetPassword}
                    </Text>
                    {!isLoading && <View style={styles.buttonArrow} />}
                  </Pressable>
                </View>
              )}

              {/* Back to Login Link */}
              <View style={styles.loginRow}>
                <Pressable
                  accessibilityRole="link"
                  onPress={() => router.replace('/login' as Href)}
                  hitSlop={8}
                >
                  <Text style={styles.loginLink}>← {text.backToLogin}</Text>
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
    paddingBottom: 24,
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
    paddingBottom: 22,
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
    fontSize: 24,
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
    marginTop: 14,
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
  otpInput: {
    fontSize: 22,
    fontWeight: '700',
    letterSpacing: 8,
    textAlign: 'center',
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
  noticeBox: {
    marginBottom: 14,
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 10,
    backgroundColor: '#E9EFE5',
  },
  noticeText: {
    color: '#315B43',
    fontSize: 13,
    lineHeight: 18,
    textAlign: 'center',
  },
  errorBox: {
    marginBottom: 14,
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 10,
    backgroundColor: '#FDEEEB',
    borderWidth: 1,
    borderColor: '#F5C2BA',
  },
  errorBoxText: {
    color: '#B34438',
    fontSize: 13,
    lineHeight: 18,
    textAlign: 'center',
  },
  primaryButton: {
    minHeight: 51,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 18,
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
  emailBadgeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 14,
    paddingVertical: 10,
    marginBottom: 16,
    borderRadius: 10,
    backgroundColor: '#EDF2E8',
    borderWidth: 1,
    borderColor: '#D8E2D2',
  },
  emailBadgeText: {
    flex: 1,
    color: '#264D37',
    fontSize: 13,
    fontWeight: '600',
    marginRight: 8,
  },
  changeEmailText: {
    color: '#236C4C',
    fontSize: 12,
    fontWeight: '700',
  },
  resendRow: {
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 16,
    minHeight: 32,
  },
  resendCooldownText: {
    color: '#859288',
    fontSize: 13,
  },
  resendActiveText: {
    color: '#236C4C',
    fontSize: 13,
    fontWeight: '700',
  },
  loginRow: {
    marginTop: 22,
    alignItems: 'center',
    justifyContent: 'center',
  },
  loginLink: {
    color: '#236C4C',
    fontSize: 13,
    fontWeight: '700',
  },
});
