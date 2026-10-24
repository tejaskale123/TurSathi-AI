import { useEffect, useMemo, useState } from 'react';
import { ArrowRight, Check, Eye, EyeOff, Globe2, Lock, Mail, ShieldCheck } from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { authService } from '../../services/authService';
import './Login.css';

const translations = {
  en: {
    brand: 'TurSathi AI',
    tagline: 'Healthy Tur, Prosperous Farmers',
    heading: 'Welcome Back',
    subheading: 'Continue your Tur health journey with AI guidance',
    emailLabel: 'Email or Mobile Number',
    passwordLabel: 'Password',
    remember: 'Remember me',
    forgot: 'Forgot Password?',
    login: 'Login',
    or: 'OR',
    google: 'Continue with Google',
    noAccount: "Don't have an account?",
    register: 'Register',
    language: 'Language',
    langOptions: ['मराठी', 'हिंदी', 'English'],
    requiredEmail: 'Please enter your email or mobile number.',
    requiredPassword: 'Password is required.',
    googleInfo: 'Google sign-in is not configured yet.',
    forgotInfo: 'Password reset is not configured yet. Please contact support.',
    submitSuccess: 'Demo login successful. Redirecting...',
    successMessage: 'Login successful',
  },
  hi: {
    brand: 'TurSathi AI',
    tagline: 'स्वस्थ тур, समृद्ध किसान',
    heading: 'वापसी पर स्वागत है',
    subheading: 'AI गाइडेंस के साथ अपनी Tur स्वास्थ्य यात्रा जारी रखें',
    emailLabel: 'ईमेल या मोबाइल नंबर',
    passwordLabel: 'पासवर्ड',
    remember: 'याद रखें',
    forgot: 'पासवर्ड भूल गए?',
    login: 'लॉगिन',
    or: 'या',
    google: 'Google से जारी रखें',
    noAccount: 'खाता नहीं है?',
    register: 'रजिस्टर करें',
    language: 'भाषा',
    langOptions: ['मराठी', 'हिंदी', 'English'],
    requiredEmail: 'कृपया अपना ईमेल या मोबाइल नंबर दर्ज करें।',
    requiredPassword: 'पासवर्ड आवश्यक है।',
    googleInfo: 'Google साइन-इन अभी कॉन्फ़िगर नहीं है।',
    forgotInfo: 'पासवर्ड रीसेट अभी कॉन्फ़िगर नहीं है। कृपया सहायता से संपर्क करें।',
    submitSuccess: 'डेमो लॉगिन सफल। रीडायरेक्ट हो रहा है...',
    successMessage: 'लॉगिन सफल',
  },
  mr: {
    brand: 'TurSathi AI',
    tagline: 'आरोग्यदायी तूर, समृद्ध शेतकरी',
    heading: 'परत स्वागत आहे',
    subheading: 'AI मार्गदर्शनासह तुमची तूर आरोग्य यात्रा सुरू ठेवा',
    emailLabel: 'ईमेल किंवा मोबाइल नंबर',
    passwordLabel: 'पासवर्ड',
    remember: 'लक्षात ठेवा',
    forgot: 'पासवर्ड विसरलात?',
    login: 'लॉगिन',
    or: 'किंवा',
    google: 'Google सह सुरू ठेवा',
    noAccount: 'खाते नाही का?',
    register: 'नोंदणी करा',
    language: 'भाषा',
    langOptions: ['मराठी', 'हिंदी', 'English'],
    requiredEmail: 'कृपया तुमचा ईमेल किंवा मोबाइल नंबर भरा.',
    requiredPassword: 'पासवर्ड आवश्यक आहे.',
    googleInfo: 'Google साइन-इन अद्याप कॉन्फिगर केलेले नाही.',
    forgotInfo: 'पासवर्ड रीसेट अद्याप कॉन्फिगर केलेले नाही. कृपया सपोर्टशी संपर्क करा.',
    submitSuccess: 'डेमो लॉगिन यशस्वी. रीडायरेक्ट होत आहे...',
    successMessage: 'लॉगिन यशस्वी',
  },
};

function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const [language, setLanguage] = useState('en');
  const [form, setForm] = useState({ email: '', password: '', remember: true });
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState({});
  const [notice, setNotice] = useState('');
  const [noticeType, setNoticeType] = useState('info');

  const text = useMemo(() => translations[language], [language]);

  useEffect(() => {
    if (location.state?.message) {
      setNotice(location.state.message);
      setNoticeType('info');
    }
  }, [location.state]);

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

    if (!form.email.trim()) {
      validationErrors.email = text.requiredEmail;
    }

    if (!form.password.trim()) {
      validationErrors.password = text.requiredPassword;
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
      await authService.login({
        identifier: form.email.trim(),
        password: form.password,
      });
      setNotice(text.successMessage);
      setNoticeType('info');
      const destination = location.state?.from?.pathname || '/home';
      navigate(destination);
    } catch (err) {
      setNotice(err.detail || err.message || 'Login failed. Please check your credentials.');
      setNoticeType('error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGoogle = () => {
    setNotice(text.googleInfo);
    setNoticeType('warning');
  };

  const handleForgot = () => {
    setNotice(text.forgotInfo);
    setNoticeType('warning');
  };

  return (
    <div className="login-page">
      <div className="login-scene">
        <div className="login-card">
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
            <label className="field-label" htmlFor="login-email">{text.emailLabel}</label>
            <div className={`input-wrap ${errors.email ? 'has-error' : ''}`}>
              <Mail size={18} className="input-icon" />
              <input
                id="login-email"
                name="email"
                type="text"
                value={form.email}
                onChange={handleChange}
                placeholder={text.emailLabel}
                autoComplete="username"
                aria-invalid={Boolean(errors.email)}
              />
            </div>
            {errors.email && <span className="field-error">{errors.email}</span>}

            <label className="field-label" htmlFor="login-password">{text.passwordLabel}</label>
            <div className={`input-wrap ${errors.password ? 'has-error' : ''}`}>
              <Lock size={18} className="input-icon" />
              <input
                id="login-password"
                name="password"
                type={showPassword ? 'text' : 'password'}
                value={form.password}
                onChange={handleChange}
                placeholder={text.passwordLabel}
                autoComplete="current-password"
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

            <div className="options-row">
              <label className="checkbox-row" htmlFor="login-remember">
                <input
                  id="login-remember"
                  name="remember"
                  type="checkbox"
                  checked={form.remember}
                  onChange={handleChange}
                />
                <span>{text.remember}</span>
              </label>

              <button type="button" className="link-button" onClick={handleForgot}>
                {text.forgot}
              </button>
            </div>

            {notice && (
              <div className={`status-message ${noticeType || 'info'}`} role="alert">
                {notice}
              </div>
            )}

            <button type="submit" className="primary-button" disabled={isSubmitting}>
              <span>{isSubmitting ? 'Processing...' : text.login}</span>
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

            <div className="register-prompt">
              <span>{text.noAccount}</span>
              <Link to="/register" className="inline-link">
                {text.register}
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

export default Login;
