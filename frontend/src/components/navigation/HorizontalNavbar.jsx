import React, { useState, useRef, useEffect } from 'react';
import {
  Home, Settings, Search, Library, Download,
  Sun, Moon, Languages, Check, Plus, LogOut,
  FolderKanban, ChevronDown, LayoutList, PanelLeft,
  LayoutDashboard, User, ShieldCheck, ExternalLink,
  BookOpen, ArrowLeft, MessageSquare, FileText, BarChart2,
  Sparkles, HelpCircle
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { useProject } from '../../contexts/ProjectContext';
import { useLanguage } from '../../contexts/LanguageContext';
import { useDarkMode } from '../../contexts/DarkModeContext';
import BrandLogo from '../common/BrandLogo';

const NAV_ITEMS = [
  { id: 'setup',        labelVi: 'Khung đề tài',       shortLabelVi: 'Khung đề tài',  labelEn: 'Setup',             shortLabelEn: 'Setup',      icon: Settings },
  { id: 'search',       labelVi: 'Tìm kiếm',          shortLabelVi: 'Tìm kiếm',     labelEn: 'Search',            shortLabelEn: 'Search',     icon: Search },
  { id: 'chat',         labelVi: 'Chat với nguồn',     shortLabelVi: 'Chat nguồn',   labelEn: 'Chat with Sources', shortLabelEn: 'Chat',       icon: MessageSquare },
  { id: 'synthesis',    labelVi: 'Tổng quan tài liệu', shortLabelVi: 'Tổng quan',    labelEn: 'Literature Review', shortLabelEn: 'Review',     icon: FileText },
  { id: 'data_analysis',labelVi: 'Phân tích dữ liệu',  shortLabelVi: 'Phân tích',    labelEn: 'Data Analysis',     shortLabelEn: 'Analytics',  icon: BarChart2 },
];

export default function HorizontalNavbar({
  activeTab,
  setActiveTab,
  onOpenNewProject,
  onStartTour,
  layoutMode = 'horizontal',
  setLayoutMode,
}) {
  const { currentUser, logout } = useAuth();
  const { projects, activeProject, activeProjectId, switchProject } = useProject();
  const { language, setLanguage } = useLanguage();
  const { darkMode, setDarkMode } = useDarkMode();

  const isVi = language === 'vi';
  const [projectDropdownOpen, setProjectDropdownOpen] = useState(false);
  const [profileDropdownOpen, setProfileDropdownOpen] = useState(false);

  const projectDropdownRef = useRef(null);
  const profileDropdownRef = useRef(null);

  // Close dropdowns on outside click
  useEffect(() => {
    const handleOutside = (e) => {
      if (projectDropdownRef.current && !projectDropdownRef.current.contains(e.target)) {
        setProjectDropdownOpen(false);
      }
      if (profileDropdownRef.current && !profileDropdownRef.current.contains(e.target)) {
        setProfileDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutside);
    return () => document.removeEventListener('mousedown', handleOutside);
  }, []);

  const navItems = currentUser?.role === 'admin' 
    ? [
        { id: 'admin', labelVi: 'Quản trị', shortLabelVi: 'Quản trị', labelEn: 'Admin', shortLabelEn: 'Admin', icon: LayoutDashboard },
      ]
    : NAV_ITEMS;

  const userInitials = currentUser?.name 
    ? currentUser.name.split(' ').map(n => n[0]).join('').slice(-2).toUpperCase() 
    : 'NH';

  const handleExportFullProject = () => {
    try {
      const pId = activeProjectId || activeProject?.id;
      const cachedPapers = JSON.parse(localStorage.getItem(`litreview_search_papers_${pId}`) || '[]');
      const setupData = JSON.parse(localStorage.getItem(`research_setup_data_${pId}`) || '{}');
      const picoData = JSON.parse(localStorage.getItem(`slr_pico_data_${pId}`) || '{}');
      const chatHistory = JSON.parse(localStorage.getItem(`litreview_workspace_chat_${pId}`) || '[]');
      
      const payload = {
        app: 'T165 LitReview Agent',
        exported_at: new Date().toISOString(),
        project: activeProject || setupData,
        pico: picoData,
        papers: cachedPapers,
        chat_history: chatHistory
      };
      
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${(activeProject?.name || 'project').replace(/\s+/g, '_')}_full_package.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error('Failed to export full project package:', e);
    }
  };

  return (
    <header className="sticky top-0 z-50 w-full bg-white/95 dark:bg-slate-900/95 backdrop-blur-md border-b border-slate-200/80 dark:border-slate-800 transition-colors shadow-xs">
      <div className="w-full max-w-[1920px] mx-auto px-2 sm:px-4 lg:px-6 h-16 flex items-center justify-between gap-1.5 sm:gap-2.5 lg:gap-4">
        
        {/* ── 1. Left: Brand Logo & Unified Project Switcher Hub ─────── */}
        <div className="flex items-center gap-1.5 sm:gap-2.5 shrink-0 min-w-0">
          <BrandLogo
            size="md"
            withText
            withTagline
            taglineClassName="hidden 2xl:block"
            isEn={!isVi}
            badgeStyle
            onClick={() => setActiveTab('overview')}
          />
          <div className="h-5 w-px bg-slate-200 dark:bg-slate-800 hidden sm:block shrink-0" />

          {/* Unified Project Switcher & Back Hub Dropdown */}
          <div className="relative shrink min-w-0" ref={projectDropdownRef}>
            <button
              id="tour-project-switcher"
              onClick={() => setProjectDropdownOpen(!projectDropdownOpen)}
              className="inline-flex items-center gap-1.5 px-2 sm:px-2.5 py-1.5 rounded-xl text-xs font-bold text-slate-700 dark:text-slate-200 bg-slate-100/90 dark:bg-slate-800/90 hover:bg-slate-200/80 dark:hover:bg-slate-750 border border-slate-200/90 dark:border-slate-700/90 transition-all cursor-pointer shadow-2xs max-w-[120px] sm:max-w-[150px] md:max-w-[180px] xl:max-w-[230px] overflow-hidden"
              title={activeProject?.name || (isVi ? 'Đề tài hiện tại / Chuyển đề tài' : 'Current Project / Switch')}
            >
              <FolderKanban className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400 shrink-0" />
              <span className="truncate min-w-0 flex-1">{activeProject?.name || (isVi ? 'Tất cả Đề tài' : 'All Projects')}</span>
              <ChevronDown className="w-3 h-3 text-slate-400 shrink-0 ml-0.5" />
            </button>

            {projectDropdownOpen && (
              <div className="absolute left-0 mt-2 w-72 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xl py-2 z-50 animate-slide-up text-xs">
                
                {/* Back to All Projects Hub Option */}
                <div className="px-2 pb-1.5 border-b border-slate-100 dark:border-slate-800">
                  <button
                    onClick={() => {
                      setProjectDropdownOpen(false);
                      setActiveTab('overview');
                    }}
                    className="w-full px-2.5 py-1.5 rounded-xl text-left flex items-center gap-2 text-slate-700 dark:text-slate-300 hover:bg-blue-50 dark:hover:bg-blue-950/40 hover:text-blue-600 dark:hover:text-blue-400 transition-colors cursor-pointer font-bold"
                  >
                    <ArrowLeft className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400 shrink-0" />
                    <span>{isVi ? 'Quay lại Tất cả Đề tài' : 'Back to All Projects'}</span>
                  </button>
                </div>

                <div className="px-3.5 py-1.5 text-[10.5px] font-extrabold uppercase tracking-wider text-slate-400 flex items-center justify-between">
                  <span>{isVi ? 'Danh sách Đề tài' : 'Projects'}</span>
                  <span className="font-mono text-blue-600 dark:text-blue-400">{projects.length}</span>
                </div>

                <div className="max-h-56 overflow-y-auto p-1 space-y-1">
                  {projects.map((p) => {
                    const isCurrent = p.id === activeProjectId;
                    return (
                      <button
                        key={p.id}
                        onClick={() => {
                          switchProject(p.id);
                          setProjectDropdownOpen(false);
                        }}
                        className={`w-full px-3 py-2 rounded-xl text-left flex items-center justify-between transition-colors cursor-pointer ${
                          isCurrent
                            ? 'bg-blue-50 dark:bg-blue-950/50 text-blue-600 dark:text-blue-400 font-bold'
                            : 'text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'
                        }`}
                      >
                        <span className="truncate pr-2">{p.name}</span>
                        {isCurrent && <Check className="w-3.5 h-3.5 text-blue-600 shrink-0" />}
                      </button>
                    );
                  })}
                </div>

                <div className="pt-1.5 px-2 border-t border-slate-100 dark:border-slate-800 space-y-1">
                  <button
                    onClick={() => {
                      setProjectDropdownOpen(false);
                      onOpenNewProject();
                    }}
                    className="w-full py-1.5 px-2.5 rounded-xl bg-blue-50 hover:bg-blue-100 dark:bg-blue-950/40 dark:hover:bg-blue-900/50 text-blue-600 dark:text-blue-400 font-bold text-xs flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>{isVi ? 'Tạo Đề tài mới' : 'New Project'}</span>
                  </button>

                  <button
                    onClick={() => {
                      setProjectDropdownOpen(false);
                      handleExportFullProject();
                    }}
                    className="w-full py-1.5 px-2.5 rounded-xl text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 font-semibold text-xs flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                    title={isVi ? 'Tải trọn bộ dữ liệu đề tài (JSON)' : 'Export complete project package (JSON)'}
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>{isVi ? 'Xuất Gói Đề tài (.json)' : 'Export Full Package'}</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* ── 2. Center: Primary Horizontal Navigation Tabs (5 Core Flat Steps) ── */}
        <nav className="hidden md:flex items-center p-0.5 sm:p-1 rounded-2xl bg-slate-100/70 dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-700/60 backdrop-blur-sm shrink min-w-0 overflow-x-auto no-scrollbar">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`relative flex items-center gap-1 lg:gap-1.5 px-2 sm:px-2.5 lg:px-3 py-1.5 rounded-xl text-xs font-bold transition-all duration-200 cursor-pointer whitespace-nowrap shrink-0 ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-sm shadow-blue-500/30'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-white/80 dark:text-slate-300 dark:hover:text-white dark:hover:bg-slate-700/60'
                }`}
                title={isVi ? item.labelVi : item.labelEn}
              >
                <Icon className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-white' : 'text-slate-500 dark:text-slate-400'}`} />
                <span className="hidden xl:inline">{isVi ? item.labelVi : item.labelEn}</span>
                <span className="inline xl:hidden">{isVi ? (item.shortLabelVi || item.labelVi) : (item.shortLabelEn || item.labelEn)}</span>
              </button>
            );
          })}
        </nav>

        {/* ── 3. Right: Language, Theme, Profile ───────────────────────── */}
        <div className="flex items-center gap-1 sm:gap-1.5 shrink-0">

          {/* Language Switch */}
          <button
            onClick={() => setLanguage(language === 'vi' ? 'en' : 'vi')}
            className="px-2 sm:px-2.5 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition-all text-xs font-bold text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 flex items-center gap-1 cursor-pointer shadow-xs shrink-0"
            title={isVi ? 'Đổi ngôn ngữ' : 'Switch Language'}
          >
            <Languages className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
            <span className="font-mono uppercase text-[10.5px] sm:text-[11px]">{language}</span>
          </button>

          {/* Dark Mode Switch */}
          <button
            onClick={() => setDarkMode(!darkMode)}
            className="px-2 sm:px-2.5 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition-all text-xs font-bold text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 flex items-center gap-1 cursor-pointer shadow-xs shrink-0"
            title={isVi ? 'Giao diện Sáng/Tối' : 'Toggle Theme'}
          >
            {darkMode ? (
              <>
                <Sun className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                <span className="hidden 2xl:inline text-[11px]">{isVi ? 'Sáng' : 'Light'}</span>
              </>
            ) : (
              <>
                <Moon className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                <span className="hidden 2xl:inline text-[11px]">{isVi ? 'Tối' : 'Dark'}</span>
              </>
            )}
          </button>

          {/* User Profile Pill with Avatar Image, Full Name & Email */}
          <div className="relative shrink-0" ref={profileDropdownRef}>
            <button
              onClick={() => setProfileDropdownOpen(!profileDropdownOpen)}
              className="flex items-center gap-1.5 sm:gap-2 py-1 pl-1 pr-1.5 sm:pr-2.5 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-750 transition-all cursor-pointer shadow-xs ml-0.5 sm:ml-1 max-w-[140px] sm:max-w-[180px] xl:max-w-[240px]"
              title={currentUser?.name ? `${currentUser.name} · ${currentUser.email || ''}` : 'User Profile'}
            >
              {currentUser?.picture ? (
                <img
                  src={currentUser.picture}
                  alt={currentUser.name}
                  className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg object-cover ring-1 ring-blue-500/30 flex-shrink-0"
                />
              ) : (
                <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-700 text-white font-extrabold text-xs flex items-center justify-center flex-shrink-0 shadow-xs">
                  {userInitials}
                </div>
              )}
              <div className="hidden xl:block text-left min-w-0 flex-1">
                <p className="font-bold text-xs text-slate-800 dark:text-white truncate leading-tight">
                  {currentUser?.name || 'Researcher'}
                </p>
                <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate leading-tight lowercase">
                  {currentUser?.email || currentUser?.role || 'user@research.edu'}
                </p>
              </div>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400 shrink-0 hidden sm:block" />
            </button>

            {profileDropdownOpen && (
              <div className="absolute right-0 mt-2 w-64 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xl py-2 z-50 animate-slide-up text-xs">
                <div className="px-4 py-2.5 border-b border-slate-100 dark:border-slate-800 space-y-1.5">
                  <div className="flex items-center gap-2.5">
                    {currentUser?.picture ? (
                      <img
                        src={currentUser.picture}
                        alt={currentUser.name}
                        className="w-9 h-9 rounded-xl object-cover ring-1 ring-blue-500/30 flex-shrink-0"
                      />
                    ) : (
                      <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-700 text-white font-bold flex items-center justify-center text-xs flex-shrink-0">
                        {userInitials}
                      </div>
                    )}
                    <div className="min-w-0 flex-1">
                      <p className="font-bold text-slate-900 dark:text-white truncate">{currentUser?.name || 'Researcher'}</p>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate lowercase">{currentUser?.email || 'name@university.edu'}</p>
                    </div>
                  </div>
                  <div className="pt-1 flex items-center gap-1.5">
                    <span className="badge badge-primary text-[9.5px] uppercase">{currentUser?.role || 'Senior Researcher'}</span>
                    {currentUser?.institution && (
                      <span className="text-[10px] text-slate-400 truncate">{currentUser.institution}</span>
                    )}
                  </div>
                </div>

                <div className="p-1 space-y-0.5">
                  <button
                    onClick={() => {
                      setProfileDropdownOpen(false);
                      if (onStartTour) onStartTour();
                    }}
                    className="w-full px-3 py-2 rounded-xl text-left text-slate-700 dark:text-slate-200 hover:bg-blue-50 dark:hover:bg-blue-950/40 hover:text-blue-600 dark:hover:text-blue-400 font-semibold flex items-center gap-2 transition-colors cursor-pointer"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-blue-500" />
                    <span>{isVi ? 'Hướng dẫn sử dụng (Tour)' : 'Onboarding Tour'}</span>
                  </button>

                  <div className="h-px bg-slate-100 dark:bg-slate-800 my-1" />

                  <button
                    onClick={() => {
                      setProfileDropdownOpen(false);
                      logout();
                    }}
                    className="w-full px-3 py-2 rounded-xl text-left text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 font-bold flex items-center gap-2 transition-colors cursor-pointer"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                    <span>{isVi ? 'Đăng xuất' : 'Sign Out'}</span>
                  </button>
                </div>
              </div>
            )}
          </div>

        </div>

      </div>

      {/* ── 4. Mobile Horizontal Navigation Bar (< md) ────────────────── */}
      <div className="md:hidden w-full overflow-x-auto no-scrollbar px-2.5 py-1.5 border-t border-slate-200/60 dark:border-slate-800 bg-slate-50/95 dark:bg-slate-900/95 backdrop-blur-sm">
        <div className="flex items-center gap-1 min-w-max">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all shrink-0 cursor-pointer ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-xs'
                    : 'text-slate-600 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-800'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-white' : 'text-slate-500 dark:text-slate-400'}`} />
                <span>{isVi ? (item.shortLabelVi || item.labelVi) : (item.shortLabelEn || item.labelEn)}</span>
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
}
