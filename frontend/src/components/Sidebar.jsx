import React, { useState, useRef, useEffect } from 'react';
import {
  Home, Settings, Search, Library, Download,
  Sun, Moon, Languages, Menu, X, Sparkles,
  ChevronRight, BookOpen, CheckCircle2, CircleDot,
  PanelLeftClose, PanelLeft, ChevronLeft, ChevronDown,
  Plus, LogOut, Check, FolderKanban,
  Pin, PinOff, Pencil, Share2, Trash2, Copy, AlertTriangle,
  MoreHorizontal, MoreVertical, LayoutList
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useProject } from '../contexts/ProjectContext';
import { useLanguage } from '../contexts/LanguageContext';
import { useDarkMode } from '../contexts/DarkModeContext';
import BrandLogo from './common/BrandLogo';

const WORKFLOW_STEPS = [
  { id: 'overview',   labelKey: 'nav.overview',   icon: Home,     step: null },
  { id: 'setup',      labelKey: 'nav.setup',       icon: Settings, step: 1 },
  { id: 'search',     labelKey: 'nav.search',      icon: Search,   step: 2 },
  { id: 'synthesis',  labelKey: 'nav.workspace',   icon: Library,  step: 3 },
  { id: 'export',     labelKey: 'nav.export',      icon: Download, step: 4 },
];

export default function Sidebar({
  activeTab, setActiveTab,
  mobileOpen, setMobileOpen,
  isCollapsed = false, setIsCollapsed,
  onOpenNewProject,
  onStartTour,
  paperCount = 0, selectedCount = 0,
  layoutMode = 'vertical', setLayoutMode,
}) {
  const { currentUser, logout } = useAuth();
  const { 
    projects, activeProject, activeProjectId, 
    switchProject, togglePinProject, renameProject, 
    deleteProject, shareProject 
  } = useProject();
  const { language, setLanguage, t } = useLanguage();
  const { darkMode, setDarkMode } = useDarkMode();

  const [projectDropdownOpen, setProjectDropdownOpen] = useState(false);
  const [activeMenuProjectId, setActiveMenuProjectId] = useState(null);
  const [editingProjectId, setEditingProjectId] = useState(null);
  const [editingName, setEditingName] = useState('');
  const [deleteConfirmId, setDeleteConfirmId] = useState(null);
  const [toastMessage, setToastMessage] = useState(null);
  const dropdownRef = useRef(null);

  const isVietnamese = language === 'vi';

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 2500);
  };

  const handleStartRename = (e, proj) => {
    e.stopPropagation();
    setActiveMenuProjectId(null);
    setEditingProjectId(proj.id);
    setEditingName(proj.name);
  };

  const handleSaveRename = (e, projId) => {
    e.stopPropagation();
    if (editingName.trim()) {
      renameProject(projId, editingName.trim());
      showToast(isVietnamese ? 'Đã đổi tên đề tài thành công!' : 'Project renamed successfully!');
    }
    setEditingProjectId(null);
  };

  const handleCancelRename = (e) => {
    e.stopPropagation();
    setEditingProjectId(null);
  };

  const handleTogglePin = (e, projId, isPinned) => {
    e.stopPropagation();
    setActiveMenuProjectId(null);
    togglePinProject(projId);
    showToast(
      isPinned 
        ? (isVietnamese ? 'Đã bỏ ghim đề tài.' : 'Project unpinned.') 
        : (isVietnamese ? 'Đã ghim đề tài lên đầu!' : 'Project pinned to top!')
    );
  };

  const handleShare = async (e, proj) => {
    e.stopPropagation();
    setActiveMenuProjectId(null);
    await shareProject(proj.id);
    showToast(isVietnamese ? 'Đã sao chép liên kết đề tài vào bộ nhớ tạm!' : 'Project link copied to clipboard!');
  };

  const handleDelete = async (e, projId) => {
    e.stopPropagation();
    setActiveMenuProjectId(null);
    setDeleteConfirmId(null);
    const result = await deleteProject(projId);
    showToast(
      result.success
        ? (isVietnamese ? 'Đã xóa đề tài thành công.' : 'Project deleted successfully.')
        : (isVietnamese ? 'Không thể xóa đề tài, vui lòng thử lại.' : 'Failed to delete project, please try again.')
    );
  };

  // Close dropdown on outside click
  useEffect(() => {
    const handleOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setProjectDropdownOpen(false);
        setActiveMenuProjectId(null);
        setEditingProjectId(null);
        setDeleteConfirmId(null);
      }
    };
    document.addEventListener('mousedown', handleOutside);
    return () => document.removeEventListener('mousedown', handleOutside);
  }, []);

  const getStepStatus = (item) => {
    if (!item.step) return 'none';
    const stepOrder = { setup: 1, search: 2, synthesis: 3, export: 4 };
    const currentOrder = stepOrder[activeTab] || 0;
    if (activeTab === item.id) return 'active';
    if (currentOrder > (item.step || 0)) return 'done';
    return 'pending';
  };

  return (
    <>
      {/* ── Toast Notification ────────────────────────────────────────── */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 p-3 px-4 rounded-xl bg-surface-900/95 dark:bg-white text-white dark:text-surface-900 text-xs font-semibold shadow-2xl flex items-center gap-2 animate-slide-up border border-white/10">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 dark:text-emerald-600 shrink-0" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* ── Mobile Top Bar ──────────────────────────────────────────────── */}
      <div className="lg:hidden fixed top-0 inset-x-0 z-50 h-14 flex items-center justify-between px-4 bg-white dark:bg-surface-900 border-b border-surface-200 dark:border-surface-800">
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="p-2 rounded-lg text-surface-600 dark:text-surface-400 hover:bg-surface-100 dark:hover:bg-surface-800 transition-colors cursor-pointer"
          aria-label="Toggle menu"
        >
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>

        {/* Mobile Brand */}
        <BrandLogo
          size="sm"
          withText
          badgeStyle
          onClick={() => setActiveTab('overview')}
        />

        <div className="flex items-center gap-1">
          <button
            onClick={() => setLanguage(language === 'vi' ? 'en' : 'vi')}
            className="p-2 rounded-lg text-surface-500 hover:bg-surface-100 dark:hover:bg-surface-800 transition-colors cursor-pointer"
            title={t('nav.toggle_language')}
          >
            <Languages className="w-4 h-4" />
          </button>
          <button
            onClick={() => setDarkMode(!darkMode)}
            className="p-2 rounded-lg text-surface-500 hover:bg-surface-100 dark:hover:bg-surface-800 transition-colors cursor-pointer"
            title={t('nav.toggle_theme')}
          >
            {darkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-indigo-400" />}
          </button>
        </div>
      </div>

      {/* ── Spacer for mobile top bar ─────────────────────────────────────── */}
      <div className="lg:hidden h-14" />

      {/* ── Desktop Sidebar / Mobile Drawer ─────────────────────────────── */}
      <aside className={`app-sidebar ${isCollapsed ? 'collapsed' : ''} ${mobileOpen ? 'mobile-open' : ''}`}>

        {/* ── Brand & Collapse Header ────────────────────────────────────── */}
        <div className={`flex items-center h-16 border-b border-surface-100 dark:border-surface-800 flex-shrink-0 transition-all ${
          isCollapsed ? 'justify-center px-2' : 'justify-between px-4'
        }`}>
          {!isCollapsed ? (
            <>
              <BrandLogo
                size="md"
                withText
                withTagline
                isEn={!isVietnamese}
                badgeStyle
                onClick={() => setActiveTab('overview')}
              />

              <button
                type="button"
                onClick={() => setIsCollapsed(true)}
                className="hidden lg:flex p-1.5 rounded-lg text-surface-400 hover:text-surface-700 dark:hover:text-surface-200 hover:bg-surface-100 dark:hover:bg-surface-800 transition-colors cursor-pointer"
                title="Thu gọn sidebar"
              >
                <PanelLeftClose className="w-4 h-4" />
              </button>
            </>
          ) : (
            /* Collapsed Mode Brand & Expand Toggle */
            <button
              type="button"
              onClick={() => setIsCollapsed(false)}
              className="p-1 rounded-xl hover:bg-surface-100 dark:hover:bg-surface-800 transition-all group relative cursor-pointer"
              title="Mở rộng sidebar"
            >
              <BrandLogo size="sm" />
              <span className="tooltip left-full ml-3 opacity-0 group-hover:opacity-100 transition-opacity">
                Mở rộng Sidebar
              </span>
            </button>
          )}
        </div>

        {/* ── Project Switcher Section with 3-dot "..." Action Menu ───────── */}
        {!isCollapsed ? (
          <div className="p-3 border-b border-surface-100 dark:border-surface-800 relative" ref={dropdownRef}>
            <p className="section-label px-1 mb-1.5 flex items-center justify-between">
              <span>{isVietnamese ? 'Đề tài nghiên cứu' : 'Research Projects'}</span>
              <span className="text-[10px] font-mono font-bold text-primary-600 dark:text-primary-400">
                {projects.length} {isVietnamese ? 'đề tài' : 'projects'}
              </span>
            </p>

            <button
              type="button"
              onClick={() => setProjectDropdownOpen(!projectDropdownOpen)}
              className="w-full flex items-center justify-between gap-2 p-2 rounded-xl bg-surface-50 dark:bg-surface-800/60 hover:bg-surface-100 dark:hover:bg-surface-800 border border-surface-200 dark:border-surface-700 text-left transition-colors cursor-pointer"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  {activeProject?.is_pinned && (
                    <Pin className="w-3 h-3 text-primary-500 fill-primary-500 shrink-0" />
                  )}
                  <p className="text-xs font-bold text-surface-900 dark:text-white truncate">
                    {activeProject?.name || (isVietnamese ? 'Chưa có đề tài...' : 'No project yet...')}
                  </p>
                </div>
                <p className="text-[10px] text-surface-400 truncate mt-0.5">
                  {activeProject?.research_field || (isVietnamese ? 'Bấm để tạo đề tài mới' : 'Click to create project')}
                </p>
              </div>
              <ChevronDown className={`w-3.5 h-3.5 text-surface-400 shrink-0 transition-transform ${projectDropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            {/* Dropdown Menu */}
            {projectDropdownOpen && (
              <div className="absolute left-3 right-3 top-full mt-1.5 z-50 card p-1.5 shadow-2xl bg-white dark:bg-surface-850 border-surface-200 dark:border-surface-700 space-y-1 animate-slide-up max-h-72 overflow-y-auto rounded-xl">
                {projects.length === 0 ? (
                  <p className="text-[11px] text-surface-400 p-2.5 text-center italic">
                    {isVietnamese ? 'Chưa có đề tài nào.' : 'No projects yet.'}
                  </p>
                ) : (
                  projects.map(p => {
                    const isSelected = p.id === activeProjectId;
                    const isEditing = editingProjectId === p.id;
                    const isConfirmingDelete = deleteConfirmId === p.id;
                    const isMenuOpen = activeMenuProjectId === p.id;

                    return (
                      <div
                        key={p.id}
                        className={`p-2 rounded-lg text-xs transition-colors group relative ${
                          isSelected
                            ? 'bg-primary-50 dark:bg-primary-950/60 border border-primary-200 dark:border-primary-800'
                            : 'hover:bg-surface-50 dark:hover:bg-surface-800 border border-transparent'
                        }`}
                      >
                        {/* Inline Rename Form */}
                        {isEditing ? (
                          <div className="flex items-center gap-1.5" onClick={e => e.stopPropagation()}>
                            <input
                              type="text"
                              value={editingName}
                              onChange={e => setEditingName(e.target.value)}
                              onKeyDown={e => {
                                if (e.key === 'Enter') handleSaveRename(e, p.id);
                                if (e.key === 'Escape') handleCancelRename(e);
                              }}
                              className="input input-xs flex-1 text-xs py-1"
                              autoFocus
                            />
                            <button
                              type="button"
                              onClick={e => handleSaveRename(e, p.id)}
                              className="p-1 rounded bg-emerald-600 text-white hover:bg-emerald-700 cursor-pointer"
                              title="Lưu"
                            >
                              <Check className="w-3 h-3" />
                            </button>
                            <button
                              type="button"
                              onClick={handleCancelRename}
                              className="p-1 rounded bg-surface-200 dark:bg-surface-700 text-surface-600 hover:bg-surface-300 cursor-pointer"
                              title="Hủy"
                            >
                              <X className="w-3 h-3" />
                            </button>
                          </div>
                        ) : isConfirmingDelete ? (
                          /* Delete Confirmation Box */
                          <div className="p-1.5 space-y-1.5 bg-red-50 dark:bg-red-950/40 rounded border border-red-200 dark:border-red-800" onClick={e => e.stopPropagation()}>
                            <p className="text-[11px] font-semibold text-red-700 dark:text-red-300 flex items-center gap-1">
                              <AlertTriangle className="w-3 h-3 text-red-500" />
                              <span>{isVietnamese ? 'Xác nhận xóa đề tài này?' : 'Delete this project?'}</span>
                            </p>
                            <div className="flex items-center gap-2 justify-end">
                              <button
                                type="button"
                                onClick={() => setDeleteConfirmId(null)}
                                className="px-2 py-0.5 text-[10px] rounded bg-surface-200 dark:bg-surface-700 text-surface-700 dark:text-surface-300 hover:bg-surface-300 cursor-pointer"
                              >
                                {isVietnamese ? 'Hủy' : 'Cancel'}
                              </button>
                              <button
                                type="button"
                                onClick={e => handleDelete(e, p.id)}
                                className="px-2 py-0.5 text-[10px] rounded bg-red-600 text-white font-bold hover:bg-red-700 cursor-pointer"
                              >
                                {isVietnamese ? 'Xóa' : 'Delete'}
                              </button>
                            </div>
                          </div>
                        ) : (
                          /* Standard Project Row with Clean "..." Button */
                          <div className="flex items-center justify-between gap-1.5">
                            <button
                              type="button"
                              onClick={() => {
                                switchProject(p.id);
                                setProjectDropdownOpen(false);
                              }}
                              className="flex items-center gap-1.5 min-w-0 flex-1 text-left cursor-pointer"
                            >
                              {p.is_pinned && (
                                <Pin className="w-3 h-3 text-primary-500 fill-primary-500 shrink-0" />
                              )}
                              <span className={`truncate ${isSelected ? 'font-bold text-primary-700 dark:text-primary-300' : 'text-surface-800 dark:text-surface-200'}`}>
                                {p.name}
                              </span>
                            </button>

                            {/* 3-Dot "..." Trigger Button */}
                            <button
                              type="button"
                              onClick={e => {
                                e.stopPropagation();
                                setActiveMenuProjectId(isMenuOpen ? null : p.id);
                              }}
                              className={`p-1 rounded text-surface-400 hover:text-surface-700 dark:hover:text-surface-200 hover:bg-surface-200 dark:hover:bg-surface-700 cursor-pointer transition-colors shrink-0 ${
                                isMenuOpen ? 'bg-surface-200 dark:bg-surface-700 text-surface-800 dark:text-white' : ''
                              }`}
                              title={isVietnamese ? 'Tùy chọn đề tài' : 'Project options'}
                            >
                              <MoreVertical className="w-3.5 h-3.5" />
                            </button>

                            {/* Floating "..." Action Menu */}
                            {isMenuOpen && (
                              <div
                                className="absolute right-2 top-full mt-1 z-50 w-44 rounded-xl shadow-2xl bg-white dark:bg-surface-800 border border-surface-200 dark:border-surface-700 py-1 space-y-0.5 animate-slide-up text-left"
                                onClick={e => e.stopPropagation()}
                              >
                                {/* 1. Pin / Unpin */}
                                <button
                                  type="button"
                                  onClick={e => handleTogglePin(e, p.id, p.is_pinned)}
                                  className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-surface-700 dark:text-surface-200 hover:bg-primary-50 dark:hover:bg-primary-950/50 hover:text-primary-600 dark:hover:text-primary-400 cursor-pointer transition-colors"
                                >
                                  {p.is_pinned ? <PinOff className="w-3.5 h-3.5 text-primary-500" /> : <Pin className="w-3.5 h-3.5" />}
                                  <span>{p.is_pinned ? (isVietnamese ? 'Bỏ ghim đề tài' : 'Unpin project') : (isVietnamese ? 'Ghim lên đầu' : 'Pin to top')}</span>
                                </button>

                                {/* 2. Rename */}
                                <button
                                  type="button"
                                  onClick={e => handleStartRename(e, p)}
                                  className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-surface-700 dark:text-surface-200 hover:bg-primary-50 dark:hover:bg-primary-950/50 hover:text-primary-600 dark:hover:text-primary-400 cursor-pointer transition-colors"
                                >
                                  <Pencil className="w-3.5 h-3.5" />
                                  <span>{isVietnamese ? 'Đổi tên đề tài' : 'Rename project'}</span>
                                </button>

                                {/* 3. Share */}
                                <button
                                  type="button"
                                  onClick={e => handleShare(e, p)}
                                  className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-surface-700 dark:text-surface-200 hover:bg-primary-50 dark:hover:bg-primary-950/50 hover:text-primary-600 dark:hover:text-primary-400 cursor-pointer transition-colors"
                                >
                                  <Share2 className="w-3.5 h-3.5" />
                                  <span>{isVietnamese ? 'Chia sẻ liên kết' : 'Share link'}</span>
                                </button>

                                <div className="border-t border-surface-100 dark:border-surface-700 my-0.5" />

                                {/* 4. Delete */}
                                <button
                                  type="button"
                                  onClick={e => {
                                    e.stopPropagation();
                                    setActiveMenuProjectId(null);
                                    setDeleteConfirmId(p.id);
                                  }}
                                  className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/40 cursor-pointer transition-colors"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                  <span>{isVietnamese ? 'Xóa đề tài' : 'Delete project'}</span>
                                </button>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })
                )}

                {/* Create Project Option */}
                <button
                  type="button"
                  onClick={() => {
                    setProjectDropdownOpen(false);
                    onOpenNewProject();
                  }}
                  className="w-full flex items-center gap-2 p-2 rounded-lg text-xs font-bold text-primary-600 dark:text-primary-400 hover:bg-primary-50 dark:hover:bg-primary-950/40 border-t border-surface-100 dark:border-surface-700 mt-1 pt-2 transition-colors cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>+ {isVietnamese ? 'Khởi tạo đề tài mới' : 'Create New Project'}</span>
                </button>
              </div>
            )}
          </div>
        ) : (
          /* Collapsed Project Button */
          <div className="py-2 border-b border-surface-100 dark:border-surface-800 flex justify-center">
            <button
              onClick={() => setIsCollapsed(false)}
              className="w-10 h-10 rounded-xl bg-surface-100 dark:bg-surface-800 text-surface-600 dark:text-surface-300 flex items-center justify-center hover:bg-primary-50 hover:text-primary-600 dark:hover:bg-primary-950 transition-colors group relative cursor-pointer"
              title={activeProject?.name}
            >
              <FolderKanban className="w-4 h-4" />
              <span className="tooltip left-full ml-3 opacity-0 group-hover:opacity-100 transition-opacity">
                Đề tài: {activeProject?.name}
              </span>
            </button>
          </div>
        )}

        {/* ── Navigation Items ─────────────────────────────────────────── */}
        <nav className={`flex-1 overflow-y-auto py-3 space-y-1.5 ${isCollapsed ? 'px-2 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]' : 'px-3'}`}>

          {/* Section: Overview Dashboard */}
          <NavItem
            item={WORKFLOW_STEPS[0]}
            isActive={activeTab === 'overview'}
            status="none"
            isCollapsed={isCollapsed}
            onClick={() => setActiveTab('overview')}
            t={t}
          />

          {/* Section: Workflow */}
          <div className="pt-3 pb-1">
            {!isCollapsed && (
              <p className="section-label px-3 mb-2 animate-fade-in">
                {isVietnamese ? 'Quy trình nghiên cứu' : 'Research Workflow'}
              </p>
            )}
            <div id="tour-sidebar-workflow" className="flex flex-col space-y-1">
              {WORKFLOW_STEPS.slice(1).map((item) => {
                const status = getStepStatus(item);
                return (
                  <NavItem
                    key={item.id}
                    item={item}
                    isActive={activeTab === item.id}
                    status={status}
                    isCollapsed={isCollapsed}
                    onClick={() => setActiveTab(item.id)}
                    t={t}
                  />
                );
              })}
            </div>
          </div>

          {/* Session Stats */}
          {paperCount > 0 && (
            <div className="pt-2 mt-1 border-t border-surface-100 dark:border-surface-800">
              {!isCollapsed ? (
                <div className="px-3 space-y-2 animate-fade-in">
                  <p className="section-label mb-2">{isVietnamese ? 'Phiên làm việc' : 'Session Stats'}</p>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-surface-500">{isVietnamese ? 'Bài báo đã lưu' : 'Saved Papers'}</span>
                    <span className="font-bold text-surface-700 dark:text-surface-300 font-mono">{paperCount}</span>
                  </div>
                  {selectedCount > 0 && (
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-surface-500">{isVietnamese ? 'Đã chọn' : 'Selected'}</span>
                      <span className="font-bold text-primary-600 dark:text-primary-400 font-mono">{selectedCount}</span>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex flex-col items-center py-1">
                  <div className="group relative">
                    <span className="w-10 h-10 mx-auto rounded-xl bg-surface-100 dark:bg-surface-800 flex items-center justify-center text-[11px] font-bold text-surface-700 dark:text-surface-300 font-mono">
                      {paperCount}
                    </span>
                    <span className="tooltip left-full ml-3 opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                      {paperCount} {isVietnamese ? 'bài báo' : 'papers'} ({selectedCount} {isVietnamese ? 'đã chọn' : 'selected'})
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}
        </nav>

        {/* ── Bottom Controls & User Profile ────────────────────────────── */}
        <div className={`border-t border-surface-100 dark:border-surface-800 p-2 space-y-1 flex-shrink-0 ${isCollapsed ? 'items-center' : ''}`}>

          {/* Product Tour Restart Button */}
          {onStartTour && (
            <button
              id="tour-restart-btn"
              onClick={onStartTour}
              className={`group relative flex items-center rounded-xl text-primary-700 dark:text-primary-300 bg-primary-50/80 dark:bg-primary-950/60 hover:bg-primary-100 dark:hover:bg-primary-900/80 transition-colors text-sm font-medium cursor-pointer ${
                isCollapsed ? 'w-full justify-center h-9 p-0' : 'w-full gap-3 px-3 py-2'
              }`}
              title={t('tour.btn_restart')}
            >
              <Sparkles className="w-4 h-4 text-primary-600 dark:text-primary-400 animate-pulse flex-shrink-0" />
              {!isCollapsed && (
                <span className="truncate text-xs font-semibold">
                  {t('tour.btn_restart')}
                </span>
              )}
              {isCollapsed && (
                <span className="tooltip left-full ml-3 opacity-0 group-hover:opacity-100 transition-opacity">
                  {t('tour.btn_restart')}
                </span>
              )}
            </button>
          )}

          {/* Language Toggle */}
          <button
            onClick={() => setLanguage(language === 'vi' ? 'en' : 'vi')}
            className={`group relative flex items-center rounded-xl text-surface-600 dark:text-surface-400 hover:bg-surface-100 dark:hover:bg-surface-800 hover:text-surface-900 dark:hover:text-white transition-colors text-sm font-medium cursor-pointer ${
              isCollapsed ? 'w-full justify-center h-9 p-0' : 'w-full gap-3 px-3 py-2'
            }`}
            title={t('nav.toggle_language')}
          >
            <Languages className="w-4 h-4 flex-shrink-0" />
            {!isCollapsed && (
              <div className="flex items-center justify-between w-full min-w-0">
                <span className="truncate text-xs">
                  {language === 'vi' ? 'Tiếng Việt' : 'English'}
                </span>
                <span className="badge badge-secondary text-[9px] px-1.5 py-0 font-mono">
                  {language.toUpperCase()}
                </span>
              </div>
            )}
            {isCollapsed && (
              <span className="tooltip left-full ml-3 opacity-0 group-hover:opacity-100 transition-opacity">
                {language === 'vi' ? 'Tiếng Việt (VI)' : 'English (EN)'}
              </span>
            )}
          </button>

          {/* Layout Mode Toggle (Switch to Horizontal Navbar) */}
          <button
            type="button"
            onClick={() => {
              const next = layoutMode === 'horizontal' ? 'vertical' : 'horizontal';
              if (setLayoutMode) setLayoutMode(next);
              localStorage.setItem('litreview_layout_mode', next);
            }}
            className={`group relative flex items-center rounded-xl text-surface-600 dark:text-surface-400 hover:bg-surface-100 dark:hover:bg-surface-800 hover:text-surface-900 dark:hover:text-white transition-colors text-sm font-medium cursor-pointer ${
              isCollapsed ? 'w-full justify-center h-9 p-0' : 'w-full gap-3 px-3 py-2'
            }`}
          >
            {layoutMode === 'horizontal' ? (
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="flex-shrink-0">
                <rect width="18" height="18" x="3" y="3" rx="2" ry="2" />
                <path d="M9 3v18" />
                <path d="M3 5a2 2 0 0 1 2-2h4v18H5a2 2 0 0 1-2-2V5z" fill="currentColor" stroke="none" />
              </svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="flex-shrink-0">
                <rect width="18" height="18" x="3" y="3" rx="2" ry="2" />
                <path d="M3 9h18" />
                <path d="M3 5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v4H3V5z" fill="currentColor" stroke="none" />
              </svg>
            )}
            {!isCollapsed && (
              <span className="truncate text-xs font-semibold">
                {isVietnamese ? 'Đổi giao diện' : 'Switch Layout'}
              </span>
            )}
            {isCollapsed && (
              <span className="tooltip left-full ml-3 opacity-0 group-hover:opacity-100 transition-opacity">
                {isVietnamese ? 'Đổi giao diện' : 'Switch Layout'}
              </span>
            )}
          </button>

          {/* Language Switcher */}
          <button
            onClick={() => setLanguage(language === 'vi' ? 'en' : 'vi')}
            className={`group relative flex items-center rounded-xl text-surface-600 dark:text-surface-400 hover:bg-surface-100 dark:hover:bg-surface-800 hover:text-surface-900 dark:hover:text-white transition-colors text-sm font-medium cursor-pointer ${
              isCollapsed ? 'w-full justify-center h-9 p-0' : 'w-full gap-3 px-3 py-2'
            }`}
            title={isVietnamese ? 'Chuyển sang tiếng Anh' : 'Switch to Vietnamese'}
          >
            <Languages className="w-4 h-4 text-blue-500 flex-shrink-0" />
            {!isCollapsed && (
              <span className="truncate text-xs font-bold text-slate-700 dark:text-slate-200">
                {language === 'vi' ? 'Tiếng Việt (VI)' : 'English (EN)'}
              </span>
            )}
            {isCollapsed && (
              <span className="tooltip left-full ml-3 opacity-0 group-hover:opacity-100 transition-opacity">
                {language === 'vi' ? 'VI' : 'EN'}
              </span>
            )}
          </button>

          {/* Theme Toggle */}
          <button
            onClick={() => setDarkMode(!darkMode)}
            className={`group relative flex items-center rounded-xl text-surface-600 dark:text-surface-400 hover:bg-surface-100 dark:hover:bg-surface-800 hover:text-surface-900 dark:hover:text-white transition-colors text-sm font-medium cursor-pointer ${
              isCollapsed ? 'w-full justify-center h-9 p-0' : 'w-full gap-3 px-3 py-2'
            }`}
            title={t('nav.toggle_theme')}
          >
            {darkMode ? (
              <Sun className="w-4 h-4 text-amber-400 flex-shrink-0" />
            ) : (
              <Moon className="w-4 h-4 text-indigo-400 flex-shrink-0" />
            )}
            {!isCollapsed && (
              <span className="truncate text-xs">
                {darkMode ? (isVietnamese ? 'Chế độ tối' : 'Dark Mode') : (isVietnamese ? 'Chế độ sáng' : 'Light Mode')}
              </span>
            )}
            {isCollapsed && (
              <span className="tooltip left-full ml-3 opacity-0 group-hover:opacity-100 transition-opacity">
                {darkMode ? (isVietnamese ? 'Chế độ tối' : 'Dark Mode') : (isVietnamese ? 'Chế độ sáng' : 'Light Mode')}
              </span>
            )}
          </button>

          {/* User Account / Profile Info */}
          {currentUser && (
            <div className={`pt-2 border-t border-surface-100 dark:border-surface-800 ${isCollapsed ? 'flex justify-center' : ''}`}>
              {!isCollapsed ? (
                <div className="p-2 rounded-xl bg-surface-50 dark:bg-surface-800/60 border border-surface-200 dark:border-surface-700/60 space-y-2">
                  <div className="flex items-center gap-2.5 min-w-0">
                    {currentUser.picture ? (
                      <img
                        src={currentUser.picture}
                        alt={currentUser.name}
                        className="w-8 h-8 rounded-lg object-cover ring-1 ring-primary-500/30 flex-shrink-0"
                      />
                    ) : (
                      <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-600 to-indigo-700 text-white font-bold flex items-center justify-center text-xs flex-shrink-0 shadow-xs">
                        {currentUser.avatar || 'US'}
                      </div>
                    )}
                    <div className="min-w-0 flex-1">
                      <p className="font-bold text-xs text-slate-900 dark:text-white truncate" title={currentUser.name}>
                        {currentUser.name}
                      </p>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate font-normal leading-tight lowercase" title={currentUser.email}>
                        {currentUser.email || currentUser.role}
                      </p>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={logout}
                    className="w-full flex items-center justify-center gap-1.5 py-1 text-[11px] font-medium text-surface-500 hover:text-danger dark:hover:text-danger-light hover:bg-danger-light/30 dark:hover:bg-danger-dark/30 rounded-lg transition-colors cursor-pointer"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                    <span>{isVietnamese ? 'Đăng xuất' : 'Sign out'}</span>
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={logout}
                  className="w-9 h-9 rounded-xl bg-surface-100 dark:bg-surface-800 text-surface-600 dark:text-surface-400 hover:text-danger flex items-center justify-center transition-colors group relative cursor-pointer"
                  title="Đăng xuất"
                >
                  <LogOut className="w-4 h-4" />
                  <span className="tooltip left-full ml-3 opacity-0 group-hover:opacity-100 transition-opacity">
                    {isVietnamese ? 'Đăng xuất' : 'Sign out'} ({currentUser.name})
                  </span>
                </button>
              )}
            </div>
          )}

        </div>
      </aside>
    </>
  );
}

function NavItem({ item, isActive, status, isCollapsed, onClick, t }) {
  const Icon = item.icon;
  const label = t(item.labelKey);

  return (
    <button
      type="button"
      onClick={onClick}
      className={`group relative flex items-center transition-all cursor-pointer text-xs font-semibold ${
        isCollapsed 
          ? 'justify-center w-10 h-10 mx-auto rounded-xl px-0' 
          : 'justify-between w-full px-3 py-2.5 rounded-xl'
      } ${
        isActive
          ? 'bg-primary-50 text-primary-700 dark:bg-primary-950/80 dark:text-primary-300 font-bold shadow-xs border border-primary-200 dark:border-primary-800'
          : 'text-surface-600 dark:text-surface-300 hover:bg-surface-100 dark:hover:bg-surface-800 hover:text-surface-900 dark:hover:text-white border border-transparent'
      }`}
      title={isCollapsed ? label : undefined}
    >
      <div className={`flex items-center gap-2.5 min-w-0 ${isCollapsed ? 'justify-center' : ''}`}>
        <Icon className={`w-4 h-4 shrink-0 transition-colors ${
          isActive ? 'text-primary-600 dark:text-primary-400' : 'text-surface-400 group-hover:text-surface-600 dark:group-hover:text-surface-300'
        }`} />
        {!isCollapsed && (
          <span className="truncate text-left">{label}</span>
        )}
      </div>

      {!isCollapsed && item.step && (
        <span className={`w-4 h-4 rounded-full border flex items-center justify-center shrink-0 text-[9px] font-mono ${
          status === 'done'
            ? 'border-emerald-500 bg-emerald-50 text-emerald-600 dark:bg-emerald-950 dark:text-emerald-400'
            : status === 'active'
            ? 'border-primary-500 bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-300 font-bold'
            : 'border-surface-300 dark:border-surface-700 text-surface-400'
        }`}>
          {status === 'done' ? '✓' : item.step}
        </span>
      )}

      {isCollapsed && (
        <span className="tooltip left-full ml-3 opacity-0 group-hover:opacity-100 transition-opacity">
          {label}
        </span>
      )}
    </button>
  );
}
