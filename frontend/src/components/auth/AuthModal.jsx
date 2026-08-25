import React, { useState } from 'react';
import { 
  X, BookOpen, User, Mail, Lock, Building, 
  ArrowRight, ArrowLeft, ShieldCheck, Check, Eye, EyeOff, 
  ChevronDown, AlertCircle, CheckCircle2
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { useLanguage } from '../../contexts/LanguageContext';

const AUTH_TEXT = {
  vi: {
    title: 'LitReview',
    subtitle: 'Nền tảng Nghiên cứu & Tổng quan Tài liệu',
    signInHeading: 'Đăng nhập vào tài khoản của bạn',
    registerHeading: 'Tạo tài khoản nghiên cứu mới',
    forgotHeading: 'Khôi phục mật khẩu',
    forgotDesc: 'Nhập email học thuật của bạn. Chúng tôi sẽ gửi liên kết để bạn thiết lập lại mật khẩu.',
    tabLogin: 'Đăng nhập',
    tabRegister: 'Tạo tài khoản',
    continueGoogle: 'Tiếp tục với Google',
    orEmail: 'hoặc tiếp tục với email',
    orDivider: 'hoặc',
    emailLabel: 'Email học thuật',
    emailPlaceholder: 'name@university.edu.vn',
    passwordLabel: 'Mật khẩu',
    passwordPlaceholder: '••••••••',
    passwordCreatePlaceholder: 'Tối thiểu 8 ký tự',
    confirmPasswordLabel: 'Xác nhận mật khẩu',
    confirmPasswordPlaceholder: 'Nhập lại mật khẩu',
    rememberMe: 'Ghi nhớ đăng nhập',
    forgotPassword: 'Quên mật khẩu?',
    btnSignIn: 'Đăng nhập',
    btnSigningIn: 'Đang xác thực...',
    btnCreateAccount: 'Tạo tài khoản',
    btnCreating: 'Đang tạo tài khoản...',
    btnSendReset: 'Gửi liên kết khôi phục',
    btnSending: 'Đang gửi...',
    resetSentSuccess: 'Đã gửi liên kết khôi phục! Vui lòng kiểm tra hộp thư của bạn.',
    backToSignIn: 'Quay lại đăng nhập',
    nameLabel: 'Họ và tên',
    namePlaceholder: 'Nhập họ và tên đầy đủ',
    instLabel: 'Trường hoặc Viện nghiên cứu',
    instPlaceholder: 'vd: Đại học Bách Khoa Hà Nội',
    roleLabel: 'Vai trò học thuật',
    newToPlatform: 'Chưa có tài khoản?',
    alreadyHaveAccount: 'Đã có tài khoản?',
    tryDemoBtn: 'Dùng thử tài khoản nghiên cứu mẫu →',
    demoTitle: 'Chọn tài khoản nghiên cứu mẫu',
    demoDesc: 'Trải nghiệm ngay toàn bộ quy trình tổng quan tài liệu, sàng lọc PRISMA và phân tích ma trận:',
    errEmail: 'Vui lòng nhập email học thuật.',
    errPassword: 'Vui lòng nhập mật khẩu.',
    errFields: 'Vui lòng điền đầy đủ họ tên và email.',
    errPasswordMatch: 'Mật khẩu xác nhận không khớp.',
    errPasswordLength: 'Mật khẩu phải có ít nhất 8 ký tự.',
  },
  en: {
    title: 'LitReview',
    subtitle: 'Academic Literature Review Platform',
    signInHeading: 'Sign in to your account',
    registerHeading: 'Create your academic account',
    forgotHeading: 'Reset your password',
    forgotDesc: 'Enter your academic email and we will send you a link to reset your password.',
    tabLogin: 'Sign In',
    tabRegister: 'Create Account',
    continueGoogle: 'Continue with Google',
    orEmail: 'or continue with email',
    orDivider: 'or',
    emailLabel: 'Academic email',
    emailPlaceholder: 'name@university.edu',
    passwordLabel: 'Password',
    passwordPlaceholder: '••••••••',
    passwordCreatePlaceholder: 'At least 8 characters',
    confirmPasswordLabel: 'Confirm password',
    confirmPasswordPlaceholder: 'Re-enter your password',
    rememberMe: 'Remember me',
    forgotPassword: 'Forgot password?',
    btnSignIn: 'Sign In',
    btnSigningIn: 'Signing in...',
    btnCreateAccount: 'Create Account',
    btnCreating: 'Creating account...',
    btnSendReset: 'Send Reset Link',
    btnSending: 'Sending link...',
    resetSentSuccess: 'Password reset link sent! Please check your inbox.',
    backToSignIn: 'Back to Sign In',
    nameLabel: 'Full name',
    namePlaceholder: 'Enter your full name',
    instLabel: 'University or institute',
    instPlaceholder: 'e.g. VinUniversity',
    roleLabel: 'Academic role',
    newToPlatform: 'New to LitReview?',
    alreadyHaveAccount: 'Already have an account?',
    tryDemoBtn: 'Try a demo workspace profile →',
    demoTitle: 'Choose a Demo Researcher Profile',
    demoDesc: 'Experience the full literature review, PRISMA screening, and methodology matrix pipeline:',
    errEmail: 'Please enter your academic email.',
    errPassword: 'Please enter your password.',
    errFields: 'Please fill in your name and email.',
    errPasswordMatch: 'Passwords do not match.',
    errPasswordLength: 'Password must be at least 8 characters.',
  }
};

function GoogleIcon({ className = 'w-4 h-4' }) {
  return (
    <svg className={className} viewBox="0 0 24 24">
      <path
        fill="#4285F4"
        d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17z"
      />
      <path
        fill="#34A853"
        d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.35 24 12 24z"
      />
      <path
        fill="#FBBC05"
        d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.18 0 9.99 0 12s.45 3.82 1.25 5.42l4.03-3.15z"
      />
      <path
        fill="#EA4335"
        d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.35 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98z"
      />
    </svg>
  );
}

export default function AuthModal({ isOpen, onClose, defaultMode = 'login' }) {
  const { login, loginWithGoogle, resetPassword, register } = useAuth();
  const { language } = useLanguage();
  const t = AUTH_TEXT[language] || AUTH_TEXT.vi;

  const [mode, setMode] = useState(defaultMode === 'demo' ? 'login' : defaultMode); // 'login' | 'register' | 'forgot'

  // Form Fields
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);

  // Register Fields
  const [name, setName] = useState('');
  const [institution, setInstitution] = useState('');
  const [role, setRole] = useState('Senior Researcher');

  // State Feedback
  const [error, setError] = useState('');
  const [resetSent, setResetSent] = useState(false);
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!email.trim()) {
      setError(t.errEmail);
      return;
    }
    if (!password) {
      setError(t.errPassword);
      return;
    }
    setLoading(true);
    try {
      await login(email, password);
      setLoading(false);
      onClose();
    } catch (err) {
      setError(err?.message || 'Đăng nhập không thành công. Vui lòng kiểm tra lại thông tin.');
      setLoading(false);
    }
  };

  const handleGoogleSignIn = async () => {
    setError('');
    setLoading(true);
    try {
      await loginWithGoogle();
      setLoading(false);
      onClose();
    } catch (err) {
      setError(err?.message || 'Google Sign-in failed. Please try again.');
      setLoading(false);
    }
  };

  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!name.trim() || !email.trim()) {
      setError(t.errFields);
      return;
    }
    if (password.length < 6) {
      setError(language === 'vi' ? 'Mật khẩu phải có ít nhất 6 ký tự.' : 'Password must be at least 6 characters.');
      return;
    }
    if (password !== confirmPassword) {
      setError(t.errPasswordMatch);
      return;
    }
    setLoading(true);
    try {
      await register({ name, email, password, institution, role });
      setLoading(false);
      onClose();
    } catch (err) {
      setError(err?.message || 'Đăng ký không thành công. Vui lòng thử lại.');
      setLoading(false);
    }
  };

  const handleForgotSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!email.trim()) {
      setError(t.errEmail);
      return;
    }
    setLoading(true);
    await resetPassword(email);
    setLoading(false);
    setResetSent(true);
  };

  const switchMode = (newMode) => {
    setMode(newMode);
    setError('');
    setResetSent(false);
    setShowDemoDrawer(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="card w-full max-w-md overflow-hidden shadow-2xl animate-slide-up bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 rounded-2xl">
        
        {/* ── 1. Clean Header ─────────────────────────────────────────── */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-xs">
              <BookOpen className="w-4 h-4" />
            </div>
            <div>
              <span className="font-display font-extrabold text-sm text-slate-900 dark:text-white leading-none block">
                {t.title}
              </span>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 leading-none font-medium">
                {t.subtitle}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* ── 2. Primary 2-Tab Navigation Switcher ───────────────────────── */}
        {mode !== 'forgot' && (
          <div className="flex border-b border-slate-100 dark:border-slate-800 p-1.5 bg-slate-50/80 dark:bg-slate-950/40">
            <button
              type="button"
              onClick={() => switchMode('login')}
              className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                mode === 'login'
                  ? 'bg-white dark:bg-slate-800 text-blue-600 dark:text-blue-400 shadow-xs'
                  : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-300'
              }`}
            >
              {t.tabLogin}
            </button>
            <button
              type="button"
              onClick={() => switchMode('register')}
              className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                mode === 'register'
                  ? 'bg-white dark:bg-slate-800 text-blue-600 dark:text-blue-400 shadow-xs'
                  : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-300'
              }`}
            >
              {t.tabRegister}
            </button>
          </div>
        )}

        {/* ── 3. Main Form Content Area ─────────────────────────────────── */}
        <div className="p-6 space-y-4">
          
          {/* Error Banner */}
          {error && (
            <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 text-xs font-medium border border-rose-200 dark:border-rose-800 flex items-center gap-2 animate-fade-in">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
              <span>{error}</span>
            </div>
          )}

          {mode === 'forgot' ? (
            /* ── FORGOT PASSWORD VIEW ── */
            <div className="space-y-4">
              <div className="space-y-1">
                <h3 className="font-display font-bold text-base text-slate-900 dark:text-white">
                  {t.forgotHeading}
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                  {t.forgotDesc}
                </p>
              </div>

              {resetSent ? (
                <div className="p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300 text-xs font-medium space-y-3">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                    <span>{t.resetSentSuccess}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => switchMode('login')}
                    className="btn btn-secondary btn-sm w-full cursor-pointer"
                  >
                    <span>{t.backToSignIn}</span>
                  </button>
                </div>
              ) : (
                <form onSubmit={handleForgotSubmit} className="space-y-3.5">
                  <div>
                    <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1.5">
                      {t.emailLabel}
                    </label>
                    <div className="relative">
                      <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                      <input
                        type="email"
                        value={email}
                        onChange={e => setEmail(e.target.value)}
                        placeholder={t.emailPlaceholder}
                        className="w-full !pl-10 !pr-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-all placeholder:text-slate-400"
                        autoFocus
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="btn btn-primary w-full py-2.5 shadow-primary-sm cursor-pointer font-bold"
                  >
                    <span>{loading ? t.btnSending : t.btnSendReset}</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>

                  <div className="text-center pt-1">
                    <button
                      type="button"
                      onClick={() => switchMode('login')}
                      className="text-xs text-slate-500 hover:text-blue-600 dark:hover:text-blue-400 transition-colors cursor-pointer inline-flex items-center gap-1 font-medium"
                    >
                      <ArrowLeft className="w-3 h-3" />
                      <span>{t.backToSignIn}</span>
                    </button>
                  </div>
                </form>
              )}
            </div>
          ) : mode === 'login' ? (
            /* ── SIGN IN VIEW ── */
            <div className="space-y-4">
              
              {/* Google Sign-in Button */}
              <button
                type="button"
                onClick={handleGoogleSignIn}
                disabled={loading}
                className="w-full py-2.5 px-4 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 text-xs font-semibold flex items-center justify-center gap-2.5 transition-all shadow-xs hover:bg-slate-50 dark:hover:bg-slate-750 cursor-pointer"
              >
                <GoogleIcon className="w-4 h-4 shrink-0" />
                <span>{t.continueGoogle}</span>
              </button>

              {/* Divider */}
              <div className="relative flex items-center justify-center">
                <div className="border-t border-slate-200 dark:border-slate-800 w-full" />
                <span className="bg-white dark:bg-slate-900 px-3 text-[11px] font-semibold text-slate-400 uppercase tracking-wider relative">
                  {t.orEmail}
                </span>
              </div>

              {/* Email & Password Form */}
              <form onSubmit={handleLoginSubmit} className="space-y-3.5">
                <div>
                  <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1.5">
                    {t.emailLabel}
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                    <input
                      type="email"
                      value={email}
                      onChange={e => setEmail(e.target.value)}
                      placeholder={t.emailPlaceholder}
                      className="w-full !pl-10 !pr-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-all placeholder:text-slate-400"
                      autoFocus
                    />
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                      {t.passwordLabel}
                    </label>
                    <button
                      type="button"
                      onClick={() => switchMode('forgot')}
                      className="text-[11px] font-semibold text-blue-600 dark:text-blue-400 hover:underline cursor-pointer"
                    >
                      {t.forgotPassword}
                    </button>
                  </div>
                  <div className="relative">
                    <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={e => setPassword(e.target.value)}
                      placeholder={t.passwordPlaceholder}
                      className="w-full !pl-10 !pr-10 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-all placeholder:text-slate-400"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors cursor-pointer"
                      title={showPassword ? 'Hide password' : 'Show password'}
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <div className="flex items-center text-xs text-slate-600 dark:text-slate-400 pt-0.5">
                  <label className="flex items-center gap-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={rememberMe}
                      onChange={e => setRememberMe(e.target.checked)}
                      className="accent-blue-600 rounded cursor-pointer"
                    />
                    <span className="font-medium">{t.rememberMe}</span>
                  </label>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="btn btn-primary w-full py-2.5 shadow-primary-sm cursor-pointer mt-2 font-bold"
                >
                  <span>{loading ? t.btnSigningIn : t.btnSignIn}</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </form>

              {/* Secondary Navigation & Demo Shortcut */}
              <div className="space-y-2.5 pt-3 text-center text-xs text-slate-500 dark:text-slate-400 border-t border-slate-100 dark:border-slate-800">
                <p>
                  <span>{t.newToPlatform} </span>
                  <button
                    type="button"
                    onClick={() => switchMode('register')}
                    className="font-bold text-blue-600 dark:text-blue-400 hover:underline cursor-pointer ml-1"
                  >
                    {t.tabRegister}
                  </button>
                </p>

                <div>
                  <button
                    type="button"
                    onClick={() => setShowDemoDrawer(true)}
                    className="inline-flex items-center gap-1.5 text-xs font-semibold text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 hover:underline cursor-pointer"
                  >
                    <span>{t.tryDemoBtn}</span>
                  </button>
                </div>
              </div>

            </div>
          ) : (
            /* ── CREATE ACCOUNT VIEW ── */
            <div className="space-y-4">
              
              {/* Google Sign-up Shortcut */}
              <button
                type="button"
                onClick={handleGoogleSignIn}
                disabled={loading}
                className="w-full py-2.5 px-4 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 text-xs font-semibold flex items-center justify-center gap-2.5 transition-all shadow-xs hover:bg-slate-50 dark:hover:bg-slate-750 cursor-pointer"
              >
                <GoogleIcon className="w-4 h-4 shrink-0" />
                <span>{t.continueGoogle}</span>
              </button>

              {/* Divider */}
              <div className="relative flex items-center justify-center">
                <div className="border-t border-slate-200 dark:border-slate-800 w-full" />
                <span className="bg-white dark:bg-slate-900 px-3 text-[11px] font-semibold text-slate-400 uppercase tracking-wider relative">
                  {t.orEmail}
                </span>
              </div>

              <form onSubmit={handleRegisterSubmit} className="space-y-3">
                {/* Full Name */}
                <div>
                  <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1.5">
                    {t.nameLabel}
                  </label>
                  <div className="relative">
                    <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                    <input
                      type="text"
                      value={name}
                      onChange={e => setName(e.target.value)}
                      placeholder={t.namePlaceholder}
                      className="w-full !pl-10 !pr-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-all placeholder:text-slate-400"
                      autoFocus
                    />
                  </div>
                </div>

                {/* Academic Email */}
                <div>
                  <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1.5">
                    {t.emailLabel}
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                    <input
                      type="email"
                      value={email}
                      onChange={e => setEmail(e.target.value)}
                      placeholder={t.emailPlaceholder}
                      className="w-full !pl-10 !pr-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-all placeholder:text-slate-400"
                    />
                  </div>
                </div>

                {/* Institution & Role */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  <div>
                    <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1.5">
                      {t.instLabel}
                    </label>
                    <div className="relative">
                      <Building className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                      <input
                        type="text"
                        value={institution}
                        onChange={e => setInstitution(e.target.value)}
                        placeholder={t.instPlaceholder}
                        className="w-full !pl-10 !pr-4 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-all placeholder:text-slate-400"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1.5">
                      {t.roleLabel}
                    </label>
                    <div className="relative">
                      <select
                        value={role}
                        onChange={e => setRole(e.target.value)}
                        className="w-full px-3 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-all pr-8 appearance-none cursor-pointer"
                      >
                        <option value="Student">Student</option>
                        <option value="Graduate Student">Graduate Student</option>
                        <option value="Researcher">Researcher</option>
                        <option value="Senior Researcher">Senior Researcher</option>
                        <option value="Faculty / Professor">Faculty / Professor</option>
                        <option value="Other">Other</option>
                      </select>
                      <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400 pointer-events-none" />
                    </div>
                  </div>
                </div>

                {/* Password & Confirm Password */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  <div>
                    <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1.5">
                      {t.passwordLabel}
                    </label>
                    <div className="relative">
                      <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                      <input
                        type={showPassword ? 'text' : 'password'}
                        value={password}
                        onChange={e => setPassword(e.target.value)}
                        placeholder={t.passwordCreatePlaceholder}
                        className="w-full !pl-10 !pr-9 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-all placeholder:text-slate-400"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors cursor-pointer"
                        title={showPassword ? 'Hide password' : 'Show password'}
                      >
                        {showPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1.5">
                      {t.confirmPasswordLabel}
                    </label>
                    <div className="relative">
                      <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                      <input
                        type={showConfirmPassword ? 'text' : 'password'}
                        value={confirmPassword}
                        onChange={e => setConfirmPassword(e.target.value)}
                        placeholder={t.confirmPasswordPlaceholder}
                        className="w-full !pl-10 !pr-9 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-all placeholder:text-slate-400"
                      />
                      <button
                        type="button"
                        onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                        className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors cursor-pointer"
                        title={showConfirmPassword ? 'Hide password' : 'Show password'}
                      >
                        {showConfirmPassword ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="btn btn-primary w-full py-2.5 shadow-primary-sm cursor-pointer mt-3 font-bold"
                >
                  <span>{loading ? t.btnCreating : t.btnCreateAccount}</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </form>

              {/* Already have an account link */}
              <div className="text-center pt-2 text-xs text-slate-500 dark:text-slate-400 border-t border-slate-100 dark:border-slate-800">
                <span>{t.alreadyHaveAccount} </span>
                <button
                  type="button"
                  onClick={() => switchMode('login')}
                  className="font-bold text-blue-600 dark:text-blue-400 hover:underline cursor-pointer ml-1"
                >
                  {t.tabLogin}
                </button>
              </div>

            </div>
          )}

        </div>

      </div>
    </div>
  );
}
