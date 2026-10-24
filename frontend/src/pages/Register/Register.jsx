import { useMemo, useState } from 'react';
import { ArrowRight, Check, Eye, EyeOff, Globe2, Lock, Mail, UserRound, ShieldCheck } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { authService } from '../../services/authService';
import './Register.css';

const translations = {
  en: {
    brand: 'TurSathi AI',
    tagline: 'Healthy Tur, Prosperous Farmers',
    heading: 'Create Your Account',
    subheading: 'Join thousands of farmers using AI for better Tur crop health',
    fullName: 'Full Name',
    mobile: 'Mobile Number',
    email: 'Email (Optional)',
    password: 'Password',
    confirmPassword: 'Confirm Password',
    terms: 'I agree to the Terms & Conditions and Privacy Policy',
    button: 'Create Account',
    or: 'OR',
    google: 'Continue with Google',
    loginPrompt: 'Already have an account?',
    login: 'Login',
    language: 'Language',
    requiredName: 'Please enter your full name.',
    requiredMobile: 'Please enter your mobile number.',
    invalidMobile: 'Please enter a valid 10-digit mobile number.',
    requiredPassword: 'Password is required.',
    passwordMinLength: 'Password must be at least 8 characters.',
    mismatch: 'Passwords do not match.',
    requiredTerms: 'Please accept the Terms & Conditions.',
    googleInfo: 'Google sign-in is not configured yet.',
    success: 'Registration successful! Redirecting to login...',
  },
  hi: {
    brand: 'TurSathi AI',
    tagline: 'स्वस्थ тур, समृद्ध किसान',
    heading: 'अपना खाता बनाएं',
    subheading: 'बेहतर Tur फसल स्वास्थ्य के लिए AI का उपयोग करने वाले किसानों में शामिल हों',
    fullName: 'पूरा नाम',
    mobile: 'मोबाइल नंबर',
    email: 'ईमेल (वैकल्पिक)',
    password: 'पासवर्ड',
    confirmPassword: 'पासवर्ड की पुष्टि करें',
    terms: 'मैं नियमों और गोपनीयता नीति से सहमत हूं',
    button: 'खाता बनाएं',
    or: 'या',
    google: 'Google से जारी रखें',
    loginPrompt: 'पहले से खाता है?',
    login: 'लॉगिन',
    language: 'भाषा',
    requiredName: 'कृपया अपना पूरा नाम दर्ज करें।',
    requiredMobile: 'कृपया अपना मोबाइल नंबर दर्ज करें।',
    invalidMobile: 'कृपया एक मान्य 10-अंकों का मोबाइल नंबर दर्ज करें।',
    requiredPassword: 'पासवर्ड आवश्यक है।',
    passwordMinLength: 'पासवर्ड कम से कम 8 वर्णों का होना चाहिए।',
    mismatch: 'पासवर्ड मेल नहीं खाते।',
    requiredTerms: 'कृपया नियमों और गोपनीयता नीति से सहमत हों।',
    googleInfo: 'Google साइन-इन अभी कॉन्फ़िगर नहीं है।',
    success: 'पंजीकरण सफल! लॉगिन पर रीडायरेक्ट हो रहा है...',
  },
  mr: {
    brand: 'TurSathi AI',
    tagline: 'आरोग्यदायी तूर, समृद्ध शेतकरी',
    heading: 'तुमचे खाते तयार करा',
    subheading: 'चांगल्या तूर फसल आरोग्यासाठी AI वापरणाऱ्या शेतकऱ्यांमध्ये सहभागी व्हा',
    fullName: 'पूर्ण नाव',
    mobile: 'मोबाइल नंबर',
    email: 'ईमेल (पर्यायी)',
    password: 'पासवर्ड',
    confirmPassword: 'पासवर्डची पुष्टी करा',
    terms: 'मी नियम व गोपनीयता धोरणाशी सहमत आहे',
    button: 'खाते तयार करा',
    or: 'किंवा',
    google: 'Google सह सुरू ठेवा',
    loginPrompt: 'आधीपासून खाते आहे का?',
    login: 'लॉगिन',
    language: 'भाषा',
    requiredName: 'कृपया आपले पूर्ण नाव भरा.',
    requiredMobile: 'कृपया आपला मोबाइल नंबर भरा.',
    invalidMobile: 'कृपया वैध 10-अंकी मोबाइल नंबर प्रविष्ट करा.',
    requiredPassword: 'पासवर्ड आवश्यक आहे.',
    passwordMinLength: 'पासवर्ड किमान 8 अक्षरांचा असणे आवश्यक आहे.',
    mismatch: 'पासवर्ड जुळत नाहीत.',
    requiredTerms: 'कृपया नियम व गोपनीयता धोरणाशी सहमत व्हा.',
    googleInfo: 'Google साइन-इन अद्याप कॉन्फिगर केलेले नाही.',
    success: 'नोंदणी यशस्वी! लॉगिनवर रीडायरेक्ट होत आहे...',
  },
};

function Register() {
  const navigate = useNavigate();
  const [language, setLanguage] = useState('en');
  const [form, setForm] = useState({
    name: '',
    mobile: '',
    email: '',
    password: '',
    confirmPassword: '',
    terms: false,
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState({});
  const [notice, setNotice] = useState('');
  const [noticeType, setNoticeType] = useState('info');

  const text = useMemo(() => translations[language], [language]);

  const handleChange = (event) => {
    const { name, value, type, checked } = event.target;
    setForm((current) => ({
      ...current,
      [name]: type === 'checkbox' ? checked : value,
    }));

    if (errors[name]) {
      setErrors((current) => ({ ...current, [name]: '' }));
    }
  };

  const validateForm = () => {
    const validationErrors = {};

    if (!form.name.trim()) {
      validationErrors.name = text.requiredName;
    } else if (form.name.trim().length < 2) {
      validationErrors.name = text.requiredName;
    }

    const normalizedMobile = authService.normalizeMobileNumber(form.mobile);
    if (!form.mobile.trim()) {
      validationErrors.mobile = text.requiredMobile;
    } else if (!/^[6-9]\d{9}$/.test(normalizedMobile)) {
      validationErrors.mobile = text.invalidMobile;
    }

    if (!form.password.trim()) {
      validationErrors.password = text.requiredPassword;
    } else if (form.password.length < 8) {
      validationErrors.password = text.passwordMinLength;
    }

    if (!form.confirmPassword.trim()) {
      validationErrors.confirmPassword = text.requiredPassword;
    } else if (form.confirmPassword !== form.password) {
      validationErrors.confirmPassword = text.mismatch;
    }

    if (!form.terms) {
      validationErrors.terms = text.requiredTerms;
    }

    setErrors(validationErrors);
    return Object.keys(validationErrors).length === 0;
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setNotice('');
    setNoticeType('info');

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      await authService.register({
        fullName: form.name.trim(),
        mobileNumber: form.mobile.trim(),
        email: form.email.trim() || null,
        password: form.password,
        confirmPassword: form.confirmPassword,
      });

      setNotice(text.success);
      setNoticeType('info');

      window.setTimeout(() => {
        navigate('/login', {
          state: {
            message: 'Registration successful! Please login with your password.',
          },
        });
      }, 700);
    } catch (err) {
      setNotice(err.detail || err.message || 'Registration failed.');
      setNoticeType('error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGoogle = () => {
    setNotice(text.googleInfo);
    setNoticeType('warning');
  };

  return (
    <div className="register-page">
      <div className="register-scene">
        <div className="register-card">
          <div className="brand-row" aria-label="TurSathi AI brand">
            <div className="mini-mark" aria-hidden="true">
              <span className="mini-leaf mini-leaf-a" />
              <span className="mini-leaf mini-leaf-b" />
              <span className="mini-leaf mini-leaf-c" />
              <span className="mini-stem" />
            </div>
            <div className="brand-copy">
              <h1>
                <span className="brand-green">Tur</span>
                <span className="brand-gold">Sathi</span>
                <span className="brand-green brand-ai">AI</span>
              </h1>
              <p>{text.tagline}</p>
            </div>
          </div>

          <div className="page-header">
            <h2>{text.heading}</h2>
            <p>{text.subheading}</p>
          </div>

          <form className="auth-form" onSubmit={handleSubmit} noValidate>
            <label className="field-label" htmlFor="register-name">{text.fullName}</label>
            <div className={`input-wrap ${errors.name ? 'has-error' : ''}`}>
              <UserRound size={18} className="input-icon" />
              <input
                id="register-name"
                name="name"
                type="text"
                value={form.name}
                onChange={handleChange}
                placeholder={text.fullName}
                autoComplete="name"
                aria-invalid={Boolean(errors.name)}
              />
            </div>
            {errors.name && <span className="field-error">{errors.name}</span>}

            <label className="field-label" htmlFor="register-mobile">{text.mobile}</label>
            <div className={`input-wrap ${errors.mobile ? 'has-error' : ''}`}>
              <ShieldCheck size={18} className="input-icon" />
              <input
                id="register-mobile"
                name="mobile"
                type="tel"
                value={form.mobile}
                onChange={handleChange}
                placeholder={text.mobile}
                autoComplete="tel"
                aria-invalid={Boolean(errors.mobile)}
              />
            </div>
            {errors.mobile && <span className="field-error">{errors.mobile}</span>}

            <label className="field-label" htmlFor="register-email">{text.email}</label>
            <div className="input-wrap">
              <Mail size={18} className="input-icon" />
              <input
                id="register-email"
                name="email"
                type="email"
                value={form.email}
                onChange={handleChange}
                placeholder={text.email}
                autoComplete="email"
              />
            </div>

            <label className="field-label" htmlFor="register-password">{text.password}</label>
            <div className={`input-wrap ${errors.password ? 'has-error' : ''}`}>
              <Lock size={18} className="input-icon" />
              <input
                id="register-password"
                name="password"
                type={showPassword ? 'text' : 'password'}
                value={form.password}
                onChange={handleChange}
                placeholder={text.password}
                autoComplete="new-password"
                aria-invalid={Boolean(errors.password)}
              />
              <button
                type="button"
                className="visibility-button"
                onClick={() => setShowPassword((current) => !current)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
            {errors.password && <span className="field-error">{errors.password}</span>}

            <label className="field-label" htmlFor="register-confirm-password">{text.confirmPassword}</label>
            <div className={`input-wrap ${errors.confirmPassword ? 'has-error' : ''}`}>
              <Lock size={18} className="input-icon" />
              <input
                id="register-confirm-password"
                name="confirmPassword"
                type={showConfirmPassword ? 'text' : 'password'}
                value={form.confirmPassword}
                onChange={handleChange}
                placeholder={text.confirmPassword}
                autoComplete="new-password"
                aria-invalid={Boolean(errors.confirmPassword)}
              />
              <button
                type="button"
                className="visibility-button"
                onClick={() => setShowConfirmPassword((current) => !current)}
                aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
              >
                {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
            {errors.confirmPassword && <span className="field-error">{errors.confirmPassword}</span>}

            <label className="checkbox-row terms-row" htmlFor="register-terms">
              <input
                id="register-terms"
                name="terms"
                type="checkbox"
                checked={form.terms}
                onChange={handleChange}
              />
              <span>{text.terms}</span>
            </label>
            {errors.terms && <span className="field-error">{errors.terms}</span>}

            {notice && (
              <div className={`status-message ${noticeType || 'info'}`} role="alert">
                {notice}
              </div>
            )}

            <button type="submit" className="primary-button" disabled={isSubmitting}>
              <span>{isSubmitting ? 'Creating...' : text.button}</span>
              <ArrowRight size={18} />
            </button>

            <div className="divider-row" aria-label="Continue with alternative sign-in">
              <span />
              <small>{text.or}</small>
              <span />
            </div>

            <button type="button" className="secondary-button" onClick={handleGoogle}>
              <span className="google-mark" aria-hidden="true">G</span>
              <span>{text.google}</span>
            </button>

            <div className="login-prompt">
              <span>{text.loginPrompt}</span>
              <Link to="/login" className="inline-link">
                {text.login}
              </Link>
            </div>
          </form>

          <div className="language-switcher" aria-label="Select language">
            <button
              type="button"
              className={language === 'mr' ? 'active' : ''}
              onClick={() => setLanguage('mr')}
            >
              मराठी
            </button>
            <button
              type="button"
              className={language === 'hi' ? 'active' : ''}
              onClick={() => setLanguage('hi')}
            >
              हिंदी
            </button>
            <button
              type="button"
              className={language === 'en' ? 'active' : ''}
              onClick={() => setLanguage('en')}
            >
              English
            </button>
          </div>
        </div>

        <div className="scene-ornament scene-ornament-left" aria-hidden="true">
          <span className="ornament leaf leaf-one" />
          <span className="ornament leaf leaf-two" />
          <span className="ornament leaf leaf-three" />
        </div>

        <div className="scene-ornament scene-ornament-right" aria-hidden="true">
          <span className="ornament leaf leaf-one" />
          <span className="ornament leaf leaf-two" />
          <span className="ornament leaf leaf-three" />
        </div>
      </div>
    </div>
  );
}

export default Register;
