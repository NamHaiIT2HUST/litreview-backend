import React from 'react';
import { Search, Sparkles, Sun, Moon, Home, Settings, Library, Download, Languages } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

export default function Navbar({ activeTab, setActiveTab, darkMode, setDarkMode }) {
  const { language, setLanguage, t } = useLanguage();

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
        
        {/* Left Logo - VinDynamics Tech Style */}
        <div 
          onClick={() => setActiveTab('overview')}
          className="flex items-center gap-3 cursor-pointer group select-none"
        >
          <div className="w-10 h-10 rounded-xl bg-slate-900 dark:bg-slate-800 text-white font-display font-extrabold text-lg flex items-center justify-center border border-slate-800 dark:border-slate-700 shadow-sm group-hover:border-vindy-500 transition-colors">
            <span className="text-vindy-500 font-display">L</span>R
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-display font-bold text-base md:text-lg tracking-tight leading-none text-slate-900 dark:text-white">
                LITREVIEW
              </h1>
              <span className="px-1.5 py-0.5 rounded-md bg-vindy-500/10 text-vindy-600 dark:text-vindy-400 font-display font-bold text-[10px] tracking-wider uppercase border border-vindy-500/20">
                PRO
              </span>
            </div>
            <span className="text-[11px] font-medium text-slate-500 tracking-wide whitespace-nowrap">
              Academic Literature Intelligence
            </span>
          </div>
        </div>

        {/* Center Navigation Tabs */}
        <nav className={`hidden md:flex items-center gap-1 p-1 rounded-2xl border ${
          darkMode ? 'bg-slate-950 border-slate-800' : 'bg-slate-100/90 border-slate-200'
        }`}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center gap-2 px-3.5 py-2 text-xs font-display font-bold rounded-xl transition-all ${
                  isActive
                    ? 'bg-slate-900 dark:bg-white text-white dark:text-slate-900 shadow-sm border border-slate-800 dark:border-slate-100'
                    : darkMode
                      ? 'text-slate-400 hover:text-white hover:bg-slate-900/60'
                      : 'text-slate-600 hover:text-slate-950 hover:bg-white/80'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-vindy-500 dark:text-vindy-600' : ''}`} />
                <span>{item.label}</span>
                {item.count !== undefined && item.count > 0 && (
                  <span className="w-4 h-4 bg-vindy-500 text-white rounded-full text-[10px] flex items-center justify-center font-bold ml-1">
                    {item.count}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Right Controls */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setLanguage(language === 'vi' ? 'en' : 'vi')}
            className={`p-2.5 rounded-xl border text-sm font-bold transition-all flex items-center gap-2 ${
              darkMode 
                ? 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700' 
                : 'bg-slate-100 border-slate-200 text-slate-700 hover:bg-slate-200'
            }`}
            title={t('nav.toggle_language')}
          >
            <Languages className={`w-4 h-4 ${language === 'vi' ? 'text-green-600 dark:text-green-400' : 'text-blue-600 dark:text-blue-400'}`} />
            <span className="hidden lg:inline text-xs">{language === 'vi' ? 'VI' : 'EN'}</span>
          </button>

          <button
            onClick={() => setDarkMode(!darkMode)}
            className={`p-2.5 rounded-xl border text-sm font-bold transition-all flex items-center gap-2 ${
              darkMode 
                ? 'bg-slate-800 border-slate-700 text-amber-300 hover:bg-slate-700' 
                : 'bg-slate-100 border-slate-200 text-slate-700 hover:bg-slate-200'
            }`}
            title={t('nav.toggle_theme')}
          >
            {darkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-blue-600" />}
            <span className="hidden lg:inline text-xs">{darkMode ? t('nav.light') : t('nav.dark')}</span>
          </button>

          <div className="w-9 h-9 rounded-xl bg-slate-900 dark:bg-slate-700 text-white font-bold text-xs flex items-center justify-center shadow-sm">
            NH
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
