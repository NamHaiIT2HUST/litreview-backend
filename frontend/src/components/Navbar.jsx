import React, { useState, useEffect } from 'react';
import { Search, Sparkles, Sun, Moon, Home, Settings, Library, Download, Languages, GraduationCap, ShieldCheck, ChevronDown, Check } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

export default function Navbar({ activeTab, setActiveTab, darkMode, setDarkMode }) {
  const { language, setLanguage, t } = useLanguage();
  const isEn = language === 'en';

  const [userRole, setUserRole] = useState(() => {
    return localStorage.getItem('litreview_user_role') || 'researcher';
  });
  const [showRoleMenu, setShowRoleMenu] = useState(false);

  useEffect(() => {
    localStorage.setItem('litreview_user_role', userRole);
  }, [userRole]);

  const navItems = [
    { id: 'overview', label: t('nav.overview'), icon: Home },
    { id: 'setup', label: t('nav.setup'), icon: Settings },
    { id: 'search', label: t('nav.search'), icon: Search },
    { id: 'synthesis', label: t('nav.workspace'), icon: Library },
    { id: 'export', label: t('nav.export'), icon: Download },
  ];

  return (
    <header className={`sticky top-0 z-50 border-b transition-colors shadow-sm ${
      darkMode 
        ? 'bg-slate-900/95 border-slate-800 text-white backdrop-blur-md' 
        : 'bg-white/95 border-slate-200 text-slate-900 backdrop-blur-md'
    }`}>
      <div className="w-full px-4 md:px-8 lg:px-12 h-18 flex items-center justify-between py-3">
        
        {/* Left Logo - Modern Blue & White Tech Style */}
        <div 
          onClick={() => setActiveTab('overview')}
          className="flex items-center gap-3 cursor-pointer group select-none"
        >
          <div className="w-10 h-10 rounded-2xl bg-blue-600 text-white font-display font-black text-lg flex items-center justify-center shadow-md shadow-blue-500/20 group-hover:scale-105 transition-transform">
            LR
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-display font-black text-base md:text-lg tracking-tight leading-none text-slate-900 dark:text-white">
                LITREVIEW
              </h1>
              <span className="px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 dark:bg-blue-950/80 dark:text-sky-400 font-display font-bold text-[10px] tracking-wider uppercase border border-blue-200 dark:border-blue-800">
                AI WORKSPACE
              </span>
            </div>
            <span className="text-[11px] font-medium text-slate-500 tracking-tight whitespace-nowrap">
              Academic Systematic Review Intelligence
            </span>
          </div>
        </div>

        {/* Center Navigation Tabs */}
        <nav className={`hidden md:flex items-center gap-1 p-1 rounded-2xl border ${
          darkMode ? 'bg-slate-900 border-slate-800' : 'bg-slate-100/80 border-slate-200'
        }`}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center gap-2 px-4 py-2 text-xs font-display font-bold rounded-xl transition-all ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20'
                    : darkMode
                      ? 'text-slate-400 hover:text-white hover:bg-slate-800/80'
                      : 'text-slate-600 hover:text-slate-950 hover:bg-white/80'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-white' : ''}`} />
                <span>{item.label}</span>
                {item.count !== undefined && item.count > 0 && (
                  <span className="w-4 h-4 bg-amber-400 text-slate-950 rounded-full text-[10px] flex items-center justify-center font-bold ml-1">
                    {item.count}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Right Controls */}
        <div className="flex items-center gap-2.5">
          {/* User Role Switcher Dropdown */}
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
                  className={`w-full px-3 py-2 text-left flex items-center justify-between transition-colors ${
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
                  className={`w-full px-3 py-2 text-left flex items-center justify-between transition-colors ${
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

          <button
            onClick={() => setLanguage(language === 'vi' ? 'en' : 'vi')}
            className={`p-2 rounded-xl border text-xs font-bold transition-all flex items-center gap-1.5 ${
              darkMode 
                ? 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700' 
                : 'bg-slate-100 border-slate-200 text-slate-700 hover:bg-slate-200'
            }`}
            title={t('nav.toggle_language')}
          >
            <Languages className={`w-3.5 h-3.5 ${language === 'vi' ? 'text-green-600 dark:text-green-400' : 'text-blue-600 dark:text-blue-400'}`} />
            <span className="hidden lg:inline">{language === 'vi' ? 'VI' : 'EN'}</span>
          </button>

          <button
            onClick={() => setDarkMode(!darkMode)}
            className={`p-2 rounded-xl border text-xs font-bold transition-all flex items-center gap-1.5 ${
              darkMode 
                ? 'bg-slate-800 border-slate-700 text-amber-300 hover:bg-slate-700' 
                : 'bg-slate-100 border-slate-200 text-slate-700 hover:bg-slate-200'
            }`}
            title={t('nav.toggle_theme')}
          >
            {darkMode ? <Sun className="w-3.5 h-3.5 text-amber-400" /> : <Moon className="w-3.5 h-3.5 text-blue-600" />}
            <span className="hidden lg:inline">{darkMode ? t('nav.light') : t('nav.dark')}</span>
          </button>

          <div className="w-8 h-8 rounded-xl bg-slate-900 dark:bg-slate-700 text-white font-bold text-xs flex items-center justify-center shadow-sm">
            {userRole === 'reviewer' ? 'REV' : 'RES'}
          </div>
        </div>

      </div>

      {/* Mobile Navigation Bar */}
      <div className={`md:hidden border-t p-2 flex justify-around ${
        darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
      }`}>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          const mobileLabel = item.label.includes('.') ? item.label.split('.')[1] : item.label;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`p-2 rounded-xl text-xs font-bold flex flex-col items-center gap-1 ${
                isActive ? 'text-blue-600 dark:text-sky-400 font-extrabold' : 'text-slate-400'
              }`}
            >
              <Icon className="w-5 h-5" />
              <span className="text-[11px]">{mobileLabel}</span>
            </button>
          );
        })}
      </div>
    </header>
  );
}
