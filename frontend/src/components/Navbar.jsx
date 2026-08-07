import React from 'react';
import { Search, Upload, Sparkles, PieChart, Sun, Moon, Home, Settings, Filter, ShieldCheck, Library, Download } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, darkMode, setDarkMode, uploadedCount }) {
  const navItems = [
    { id: 'overview', label: 'Overview', icon: Home },
    { id: 'setup', label: 'Research Setup', icon: Settings },
    { id: 'search', label: 'Search Papers', icon: Search },
    { id: 'screening', label: 'Screening', icon: Filter },
    { id: 'quality', label: 'Quality Check', icon: ShieldCheck },
    { id: 'library', label: 'Library', icon: Library, count: uploadedCount },
    { id: 'synthesis', label: 'Synthesis', icon: Sparkles },
    { id: 'export', label: 'Export', icon: Download },
  ];

  return (
    <header className={`sticky top-0 z-50 border-b transition-colors shadow-sm ${
      darkMode 
        ? 'bg-slate-900/95 border-slate-800 text-white backdrop-blur-md' 
        : 'bg-white/95 border-slate-200 text-slate-900 backdrop-blur-md'
    }`}>
      <div className="max-w-7xl mx-auto px-4 md:px-8 h-18 flex items-center justify-between py-3">
        
        {/* Left Logo */}
        <div 
          onClick={() => setActiveTab('home')}
          className="flex items-center gap-3 cursor-pointer group"
        >
          <div className="w-10 h-10 rounded-xl bg-blue-600 text-white font-black text-xl flex items-center justify-center shadow-md group-hover:scale-105 transition-transform">
            LR
          </div>
          <div>
            <h1 className="font-extrabold text-base md:text-lg tracking-tight leading-none">
              LitReview Agent
            </h1>
            <span className="text-[11px] font-semibold text-blue-600 dark:text-sky-400 whitespace-nowrap">
              Closed-Domain RAG System
            </span>
          </div>
        </div>

        {/* Center Navigation Tabs (Spacious, Large Text) */}
        <nav className={`hidden md:flex items-center gap-1.5 p-1.5 rounded-2xl border ${
          darkMode ? 'bg-slate-800/80 border-slate-700' : 'bg-slate-100 border-slate-200'
        }`}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center gap-2 px-3 py-2 text-sm font-bold rounded-xl transition-all ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-md'
                    : darkMode
                      ? 'text-slate-300 hover:text-white hover:bg-slate-700/60'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-white/60'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{item.label}</span>
                {item.count !== undefined && item.count > 0 && (
                  <span className="w-5 h-5 bg-amber-400 text-slate-950 rounded-full text-xs flex items-center justify-center font-extrabold ml-1">
                    {item.count}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Right Controls */}
        <div className="flex items-center gap-3">
          {/* Light / Dark Mode Toggle */}
          <button
            onClick={() => setDarkMode(!darkMode)}
            className={`p-2.5 rounded-xl border text-sm font-bold transition-all flex items-center gap-2 ${
              darkMode 
                ? 'bg-slate-800 border-slate-700 text-amber-300 hover:bg-slate-700' 
                : 'bg-slate-100 border-slate-200 text-slate-700 hover:bg-slate-200'
            }`}
            title="Đổi giao diện Sáng / Tối"
          >
            {darkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-blue-600" />}
            <span className="hidden lg:inline text-xs">{darkMode ? 'Sáng' : 'Tối'}</span>
          </button>

          {/* User Avatar */}
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
