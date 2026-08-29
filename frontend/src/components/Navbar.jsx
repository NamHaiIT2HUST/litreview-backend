import React, { useState, useEffect } from 'react';
import { 
  Search, Sun, Moon, Home, Settings, Library, Download, 
  Languages, Menu, X, GraduationCap, ShieldCheck, ChevronDown, Check,
  LayoutDashboard
} from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';
import { useDarkMode } from '../contexts/DarkModeContext';
import { useAuth } from '../contexts/AuthContext';
import BrandLogo from './common/BrandLogo';

export default function Navbar({ activeTab, setActiveTab }) {
  const { language, setLanguage, t } = useLanguage();
  const { darkMode, setDarkMode } = useDarkMode();
  const { user, logout } = useAuth();
  const [isScrolled, setIsScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const isEn = language === 'en';
  const [userRole, setUserRole] = useState(() => {
    return localStorage.getItem('litreview_user_role') || 'researcher';
  });
  const [showRoleMenu, setShowRoleMenu] = useState(false);

  useEffect(() => {
    localStorage.setItem('litreview_user_role', userRole);
  }, [userRole]);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 10);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const userNavItems = [
    { id: 'setup', label: t('nav.setup'), icon: Settings },
    { id: 'search', label: t('nav.search'), icon: Search },
    { id: 'synthesis', label: t('nav.workspace'), icon: Library },
    { id: 'export', label: t('nav.export'), icon: Download },
  ];

  const adminNavItems = [
    { id: 'admin', label: 'Quản Trị Hệ Thống', icon: LayoutDashboard },
    { id: 'overview', label: t('nav.overview'), icon: Home },
  ];

  const navItems = user?.role === 'admin' ? adminNavItems : userNavItems;

  return (
    <>
      <div className="h-16 md:h-20" />

      <header 
        className={`fixed top-0 inset-x-0 z-50 transition-all duration-300 ${
          isScrolled 
            ? 'bg-white/80 dark:bg-slate-950/80 backdrop-blur-xl border-b border-slate-200/50 dark:border-slate-800/50 shadow-sm' 
            : 'bg-white dark:bg-slate-950 border-b border-slate-100 dark:border-slate-900'
        }`}
      >
        <div className="max-w-[1920px] mx-auto px-4 md:px-6 lg:px-8 h-16 md:h-20 flex items-center justify-between">
          
          {/* Brand */}
          <div className="relative z-10">
            <BrandLogo
              size="md"
              withText
              withTagline
              isEn={isEn}
              badgeStyle
              onClick={() => setActiveTab('overview')}
            />
          </div>

          {/* Center Navigation */}
          <nav className="hidden lg:flex items-center absolute left-1/2 -translate-x-1/2 bg-slate-100/50 dark:bg-slate-900/50 p-1 rounded-2xl border border-slate-200/50 dark:border-slate-800/50 backdrop-blur-md">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`relative flex items-center gap-2 px-5 py-2.5 text-[13px] font-display font-bold rounded-xl transition-all duration-300 overflow-hidden cursor-pointer ${
                    isActive
                      ? 'text-white shadow-md shadow-blue-500/20'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-white/80 dark:text-slate-400 dark:hover:text-white dark:hover:bg-slate-800/80'
                  }`}
                >
                  {isActive && (
                    <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl" />
                  )}
                  <Icon className={`w-4 h-4 relative z-10 ${isActive ? 'text-white' : ''}`} />
                  <span className="relative z-10 tracking-wide">{item.label}</span>
                </button>
              );
            })}
          </nav>

          {/* Right Controls */}
          <div className="flex items-center gap-2 md:gap-3 relative z-10">
            {/* User Role Switcher */}
            <div className="relative">
              <button
                onClick={() => setShowRoleMenu(!showRoleMenu)}
                className={`px-3 py-2 rounded-xl border text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer shadow-sm ${
                  userRole === 'reviewer'
                    ? 'bg-amber-500/10 border-amber-500/30 text-amber-600 dark:text-amber-400 hover:bg-amber-500/20'
                    : 'bg-blue-500/10 border-blue-500/30 text-blue-600 dark:text-blue-400 hover:bg-blue-500/20'
                }`}
                title={isEn ? "Switch User Role" : "Chuyển đổi vai trò người dùng"}
              >
                {userRole === 'reviewer' ? (
                  <ShieldCheck className="w-4 h-4 text-amber-500" />
                ) : (
                  <GraduationCap className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                )}
                <span className="hidden sm:inline">
                  {userRole === 'reviewer' 
                    ? (isEn ? 'Role: Reviewer' : 'Vai trò: Reviewer') 
                    : (isEn ? 'Role: Researcher' : 'Vai trò: Nghiên cứu viên')}
                </span>
                <ChevronDown className="w-3 h-3 opacity-60" />
              </button>

              {showRoleMenu && (
                <div 
                  className="absolute right-0 mt-2 w-56 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xl py-1.5 z-50 text-xs"
                  onClick={() => setShowRoleMenu(false)}
                >
                  <div className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400 border-b border-slate-100 dark:border-slate-800">
                    {isEn ? "Select Active Role" : "Chọn vai trò làm việc"}
                  </div>
                  <button
                    onClick={() => setUserRole('researcher')}
                    className={`w-full px-3 py-2 text-left flex items-center justify-between transition-colors cursor-pointer ${
                      userRole === 'researcher' 
                        ? 'bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 font-bold' 
                        : 'text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <GraduationCap className="w-4 h-4 text-blue-500" />
                      <div>
                        <div>{isEn ? "Lead Researcher" : "Nghiên cứu viên"}</div>
                        <div className="text-[10px] text-slate-400 font-normal">{isEn ? "Search, Scope & Analysis" : "Tìm kiếm, PICO & Phân tích"}</div>
                      </div>
                    </div>
                    {userRole === 'researcher' && <Check className="w-3.5 h-3.5 text-blue-600" />}
                  </button>

                  <button
                    onClick={() => setUserRole('reviewer')}
                    className={`w-full px-3 py-2 text-left flex items-center justify-between transition-colors cursor-pointer ${
                      userRole === 'reviewer' 
                        ? 'bg-amber-50 dark:bg-amber-950/40 text-amber-600 dark:text-amber-400 font-bold' 
                        : 'text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-amber-500" />
                      <div>
                        <div>{isEn ? "Scientific Reviewer" : "Reviewer / Giám định"}</div>
                        <div className="text-[10px] text-slate-400 font-normal">{isEn ? "Screening, Audit & Approval" : "Sàng lọc, Thẩm định & Duyệt"}</div>
                      </div>
                    </div>
                    {userRole === 'reviewer' && <Check className="w-3.5 h-3.5 text-amber-500" />}
                  </button>
                </div>
              )}
            </div>

            {/* Language Toggle */}
            <button
              onClick={() => setLanguage(language === 'vi' ? 'en' : 'vi')}
              className="w-9 h-9 md:w-10 md:h-10 rounded-xl flex items-center justify-center transition-all bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-600 dark:bg-slate-900 dark:hover:bg-slate-800 dark:border-slate-800 dark:text-slate-300 group cursor-pointer"
              title={t('nav.toggle_language')}
            >
              <Languages className={`w-4 h-4 md:w-4.5 md:h-4.5 transition-transform group-hover:scale-110 ${language === 'vi' ? 'text-emerald-500' : 'text-blue-500'}`} />
            </button>

            {/* Dark Mode Toggle */}
            <button
              onClick={() => setDarkMode(!darkMode)}
              className="w-9 h-9 md:w-10 md:h-10 rounded-xl flex items-center justify-center transition-all bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-600 dark:bg-slate-900 dark:hover:bg-slate-800 dark:border-slate-800 dark:text-slate-300 group cursor-pointer"
              title={t('nav.toggle_theme')}
            >
              <div className="relative w-4 h-4 md:w-4.5 md:h-4.5 flex items-center justify-center overflow-hidden">
                <Sun className={`absolute w-full h-full text-amber-500 transition-all duration-500 ${darkMode ? 'translate-y-8 opacity-0' : 'translate-y-0 opacity-100 group-hover:rotate-45'}`} />
                <Moon className={`absolute w-full h-full text-indigo-400 transition-all duration-500 ${darkMode ? 'translate-y-0 opacity-100 group-hover:-rotate-12' : '-translate-y-8 opacity-0'}`} />
              </div>
            </button>

            {/* User Profile / Logout */}
            {user ? (
              <div className="flex items-center gap-2">
                <div className="w-9 h-9 md:w-10 md:h-10 rounded-xl bg-gradient-to-br from-slate-800 to-slate-950 dark:from-slate-700 dark:to-slate-800 text-white font-bold text-xs md:text-sm flex items-center justify-center shadow-inner border border-slate-700/50">
                  {user.name ? user.name.slice(0, 2).toUpperCase() : (userRole === 'reviewer' ? 'REV' : 'RES')}
                </div>
                <button
                  onClick={logout}
                  className="text-xs font-semibold text-slate-500 hover:text-red-500 transition-colors hidden sm:inline"
                >
                  {isEn ? 'Logout' : 'Đăng xuất'}
                </button>
              </div>
            ) : null}

            {/* Mobile Menu Toggle */}
            <button 
              className="lg:hidden ml-1 w-9 h-9 flex items-center justify-center rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300 cursor-pointer"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </header>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-40 bg-slate-900/20 backdrop-blur-sm lg:hidden animate-in fade-in duration-200">
          <div className="absolute right-0 top-16 md:top-20 bottom-0 w-64 bg-white dark:bg-slate-950 border-l border-slate-200 dark:border-slate-800 shadow-2xl animate-in slide-in-from-right duration-300 flex flex-col p-4 gap-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    setActiveTab(item.id);
                    setMobileMenuOpen(false);
                  }}
                  className={`flex items-center gap-3 px-4 py-3.5 text-sm font-display font-bold rounded-2xl transition-all cursor-pointer ${
                    isActive
                      ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-white dark:hover:bg-slate-800/80'
                  }`}
                >
                  <Icon className={`w-5 h-5 ${isActive ? 'text-white' : ''}`} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </>
  );
}
