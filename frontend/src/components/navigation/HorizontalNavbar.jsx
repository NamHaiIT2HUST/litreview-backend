import React, { useState, useRef, useEffect } from 'react';
import {
  Home, Settings, Search, Library, Download,
  Sun, Moon, Languages, Check, Plus, LogOut,
  FolderKanban, ChevronDown, LayoutList, PanelLeft,
  LayoutDashboard, User, ShieldCheck, ExternalLink,
  BookOpen
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { useProject } from '../../contexts/ProjectContext';
import { useLanguage } from '../../contexts/LanguageContext';
import { useDarkMode } from '../../contexts/DarkModeContext';

const NAV_ITEMS = [
  { id: 'overview',   labelVi: 'Tổng quan',   labelEn: 'Overview',  icon: Home },
  { id: 'setup',      labelVi: 'Cấu hình',    labelEn: 'Setup',     icon: Settings },
  { id: 'search',     labelVi: 'Tìm kiếm',    labelEn: 'Search',    icon: Search },
  { id: 'synthesis',  labelVi: 'Phân tích',   labelEn: 'Analysis',  icon: Library },
  { id: 'export',     labelVi: 'Xuất dữ liệu', labelEn: 'Export',   icon: Download },
];

export default function HorizontalNavbar({
  activeTab,
  setActiveTab,
  onOpenNewProject,
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
        { id: 'admin', labelVi: 'Quản trị', labelEn: 'Admin', icon: LayoutDashboard },
        { id: 'overview', labelVi: 'Tổng quan', labelEn: 'Overview', icon: Home },
      ]
    : NAV_ITEMS;

  const userInitials = currentUser?.name 
    ? currentUser.name.split(' ').map(n => n[0]).join('').slice(-2).toUpperCase() 
    : 'NH';

  return (
    <header className="sticky top-0 z-40 w-full bg-white/95 dark:bg-slate-900/95 backdrop-blur-md border-b border-slate-200/80 dark:border-slate-800 transition-colors shadow-xs">
      <div className="max-w-[1680px] mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        
        {/* ── 1. Left: Brand Logo & Title ──────────────────────────────── */}
        <div className="flex items-center gap-3 shrink-0">
          <div 
            onClick={() => setActiveTab('overview')}
            className="flex items-center gap-3 cursor-pointer group select-none"
          >
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-600 text-white font-display font-extrabold text-base flex items-center justify-center shadow-md shadow-blue-500/20 group-hover:scale-105 transition-all">
              LR
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-display font-extrabold text-base text-slate-900 dark:text-white tracking-tight leading-none">
                  LitReview Agent
                </span>
              </div>
              <p className="text-[10.5px] font-semibold text-blue-600 dark:text-blue-400 mt-1 leading-none">
                {isVi ? 'Nền tảng Nghiên cứu & Tổng quan Tài liệu' : 'Closed-Domain RAG System'}
              </p>
            </div>
          </div>
        </div>

        {/* ── 2. Center: Primary Horizontal Navigation Tabs ─────────────── */}
        <nav className="hidden md:flex items-center p-1 rounded-2xl bg-slate-100/70 dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-700/60 backdrop-blur-sm">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`relative flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all duration-200 cursor-pointer ${
                  isActive
                    ? 'bg-blue-600 text-white shadow-sm shadow-blue-500/30'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-white/80 dark:text-slate-300 dark:hover:text-white dark:hover:bg-slate-700/60'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-white' : 'text-slate-500 dark:text-slate-400'}`} />
                <span>{isVi ? item.labelVi : item.labelEn}</span>
              </button>
            );
          })}
        </nav>

        {/* ── 3. Right: Project Switcher, Layout Toggle, Theme, Profile ─── */}
        <div className="flex items-center gap-2 sm:gap-2.5">
          
          {/* Project Switcher Dropdown */}
          <div className="relative" ref={projectDropdownRef}>
            <button
              onClick={() => setProjectDropdownOpen(!projectDropdownOpen)}
              className="px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/80 dark:bg-slate-800/80 hover:bg-slate-100 dark:hover:bg-slate-750 text-xs font-bold text-slate-700 dark:text-slate-200 flex items-center gap-2 transition-all cursor-pointer shadow-xs max-w-[200px]"
              title={isVi ? 'Đổi đề tài nghiên cứu' : 'Switch Project'}
            >
              <FolderKanban className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400 shrink-0" />
              <span className="truncate">{activeProject?.name || (isVi ? 'Chọn đề tài' : 'Select project')}</span>
              <ChevronDown className="w-3 h-3 text-slate-400 shrink-0" />
            </button>

            {projectDropdownOpen && (
              <div className="absolute right-0 mt-2 w-64 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xl py-2 z-50 animate-slide-up text-xs">
                <div className="px-3.5 py-1.5 text-[10.5px] font-extrabold uppercase tracking-wider text-slate-400 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
                  <span>{isVi ? 'Đề tài Nghiên cứu' : 'Projects'}</span>
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

                <div className="pt-1.5 px-2 border-t border-slate-100 dark:border-slate-800">
                  <button
                    onClick={() => {
                      setProjectDropdownOpen(false);
                      onOpenNewProject();
                    }}
                    className="w-full py-1.5 px-2.5 rounded-xl bg-blue-50 hover:bg-blue-100 dark:bg-blue-950/40 dark:hover:bg-blue-900/50 text-blue-600 dark:text-blue-400 font-bold text-xs flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>{isVi ? 'Tạo đề tài mới' : 'New Project'}</span>
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Layout Mode Toggle (Ngang / Dọc) */}
          <button
            onClick={() => {
              const nextMode = layoutMode === 'horizontal' ? 'vertical' : 'horizontal';
              if (setLayoutMode) setLayoutMode(nextMode);
              localStorage.setItem('litreview_layout_mode', nextMode);
            }}
            className="p-2 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 transition-all text-xs font-bold border border-slate-200 dark:border-slate-700 cursor-pointer hidden sm:flex items-center gap-1.5"
            title={isVi ? (layoutMode === 'horizontal' ? 'Chuyển sang Thanh dọc (Sidebar)' : 'Chuyển sang Thanh ngang (Navbar)') : 'Toggle Layout Mode'}
          >
            {layoutMode === 'horizontal' ? (
              <>
                <PanelLeft className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400" />
                <span className="text-[11px] font-semibold">{isVi ? 'Thanh dọc' : 'Vertical'}</span>
              </>
            ) : (
              <>
                <LayoutList className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
                <span className="text-[11px] font-semibold">{isVi ? 'Thanh ngang' : 'Horizontal'}</span>
              </>
            )}
          </button>

          {/* Language Switch */}
          <button
            onClick={() => setLanguage(language === 'vi' ? 'en' : 'vi')}
            className="px-2.5 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition-all text-xs font-bold text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 flex items-center gap-1.5 cursor-pointer shadow-xs"
            title={isVi ? 'Đổi ngôn ngữ' : 'Switch Language'}
          >
            <Languages className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
            <span className="font-mono uppercase text-[11px]">{language}</span>
          </button>

          {/* Dark Mode Switch */}
          <button
            onClick={() => setDarkMode(!darkMode)}
            className="px-2.5 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition-all text-xs font-bold text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 flex items-center gap-1.5 cursor-pointer shadow-xs"
            title={isVi ? 'Giao diện Sáng/Tối' : 'Toggle Theme'}
          >
            {darkMode ? (
              <>
                <Sun className="w-3.5 h-3.5 text-amber-500" />
                <span className="hidden sm:inline text-[11px]">{isVi ? 'Sáng' : 'Light'}</span>
              </>
            ) : (
              <>
                <Moon className="w-3.5 h-3.5 text-blue-600" />
                <span className="hidden sm:inline text-[11px]">{isVi ? 'Tối' : 'Dark'}</span>
              </>
            )}
          </button>

          {/* User Profile Pill with Avatar Image, Full Name & Email */}
          <div className="relative" ref={profileDropdownRef}>
            <button
              onClick={() => setProfileDropdownOpen(!profileDropdownOpen)}
              className="flex items-center gap-2 py-1 pl-1 pr-2 sm:pr-2.5 rounded-xl border border-slate-200 dark:border-slate-700/80 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-750 transition-all cursor-pointer shadow-xs ml-1 max-w-[220px]"
              title={currentUser?.name || 'User Profile'}
            >
              {currentUser?.picture ? (
                <img
                  src={currentUser.picture}
                  alt={currentUser.name}
                  className="w-8 h-8 rounded-lg object-cover ring-1 ring-blue-500/30 flex-shrink-0"
                />
              ) : (
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-indigo-700 text-white font-extrabold text-xs flex items-center justify-center flex-shrink-0 shadow-xs">
                  {userInitials}
                </div>
              )}
              <div className="hidden lg:block text-left min-w-0 flex-1">
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
    </header>
  );
}
