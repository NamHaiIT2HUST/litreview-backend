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
