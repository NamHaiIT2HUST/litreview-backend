import React, { useState, useEffect } from 'react';
import {
  BookOpen, Sparkles, Search, Layers, ShieldCheck, ArrowRight,
  CheckCircle2, Bot, Database, Zap, FileText, Check, ChevronRight,
  Plus, Target, BarChart2, TrendingUp, Clock, Copy, Trash2,
  ExternalLink, ArrowUpRight, Filter, AlertCircle, RefreshCw,
  FolderKanban, Award, Compass, PieChart, FolderPlus, HelpCircle,
  Pin, PinOff, Pencil, Share2, AlertTriangle, X, MoreVertical
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { useProject } from '../../contexts/ProjectContext';
import { useLanguage } from '../../contexts/LanguageContext';

export default function PersonalizedDashboard({ setActiveTab, onOpenNewProject, onStartTour }) {
  const { currentUser } = useAuth();
  const { 
    projects, activeProject, activeProjectId, 
    switchProject, togglePinProject, renameProject, 
    deleteProject, duplicateProject, shareProject 
  } = useProject();
  const { t, language } = useLanguage();

  const [copiedGap, setCopiedGap] = useState(null);
  const [activeMenuProjectId, setActiveMenuProjectId] = useState(null);
  const [editingProjectId, setEditingProjectId] = useState(null);
  const [editingName, setEditingName] = useState('');
  const [deleteConfirmId, setDeleteConfirmId] = useState(null);
  const [dashboardToast, setDashboardToast] = useState(null);

  const isVietnamese = language === 'vi';

  // Close menus on outside click
  useEffect(() => {
    const handleOutside = () => {
      setActiveMenuProjectId(null);
    };
    document.addEventListener('click', handleOutside);
    return () => document.removeEventListener('click', handleOutside);
  }, []);

  const showToast = (msg) => {
    setDashboardToast(msg);
    setTimeout(() => setDashboardToast(null), 2500);
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

  const handleDelete = (e, projId) => {
    e.stopPropagation();
    setActiveMenuProjectId(null);
    deleteProject(projId);
    setDeleteConfirmId(null);
    showToast(isVietnamese ? 'Đã xóa đề tài thành công.' : 'Project deleted successfully.');
  };

  // Compute aggregated real-time stats
  const totalProjects = projects.length;
  const totalPapers = projects.reduce((acc, p) => acc + (p.paper_count || 0), 0);
  const totalScreened = projects.reduce((acc, p) => acc + (p.screened_count || 0), 0);
  const totalGaps = projects.reduce((acc, p) => acc + (p.gaps_count || 0), 0);

  const handleCopyGap = (gapText, i) => {
    navigator.clipboard.writeText(gapText);
    setCopiedGap(i);
    setTimeout(() => setCopiedGap(null), 2000);
  };

  const greeting = isVietnamese ? 'Xin chào' : 'Welcome';
  const userName = currentUser?.name?.trim() || currentUser?.email?.split('@')[0] || (isVietnamese ? 'Nhà Nghiên cứu' : 'Researcher');

  // Dynamic gaps from active project if available
  const activeGaps = activeProject?.research_gaps && activeProject.research_gaps.length > 0
    ? activeProject.research_gaps
    : [];

  return (
    <div className="space-y-8 pb-16 relative">
      
      {/* Toast Notification */}
      {dashboardToast && (
        <div className="fixed bottom-6 right-6 z-50 p-3 px-4 rounded-xl bg-surface-900/95 dark:bg-white text-white dark:text-surface-900 text-xs font-semibold shadow-2xl flex items-center gap-2 animate-slide-up border border-white/10">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 dark:text-emerald-600 shrink-0" />
          <span>{dashboardToast}</span>
        </div>
      )}

      {/* ── 1. Welcome & Active Project Header (Crisp Contrast in both Light & Dark Mode) ── */}
      <div id="tour-dashboard-hero" className="p-6 md:p-8 bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-950 text-white relative overflow-hidden shadow-2xl border border-indigo-900/60 dark:border-indigo-800/40 rounded-2xl">
        <div className="absolute -top-24 -right-24 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        
        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          
          {/* User Info */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs text-indigo-300 font-semibold uppercase tracking-wider">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span>{currentUser?.institution || 'Academic SLR Platform'}</span>
              <span>•</span>
              <span className="text-indigo-200">{currentUser?.role || 'Senior Researcher'}</span>
            </div>
            
            <h1 className="font-display font-bold text-2xl sm:text-3xl text-white tracking-tight">
              {greeting}, {userName}! 👋
            </h1>
            
            {totalProjects > 0 && activeProject ? (
              <p className="text-xs sm:text-sm text-slate-300 max-w-2xl leading-relaxed">
                {isVietnamese ? 'Bạn đang làm việc trên đề tài:' : 'Active research topic:'}{' '}
                <strong className="text-white font-bold">{activeProject.name}</strong>.
              </p>
            ) : (
              <p className="text-xs sm:text-sm text-slate-300 max-w-2xl leading-relaxed">
                {isVietnamese
                  ? 'Chào mừng bạn đến với LitReview AI. Bạn chưa có đề tài nghiên cứu nào. Hãy khởi tạo đề tài đầu tiên để bắt đầu quy trình Tổng quan tài liệu có hệ thống (SLR) chuẩn PRISMA.'
                  : 'Welcome to LitReview AI. You have no active research projects yet. Create your first project to begin the PRISMA-compliant SLR workflow.'}
              </p>
            )}
          </div>

          {/* Quick Actions in Header */}
          <div className="flex flex-wrap items-center gap-2.5">
            {onStartTour && (
              <button
                onClick={onStartTour}
                className="btn btn-sm bg-indigo-900/80 hover:bg-indigo-800 text-indigo-100 border border-indigo-700/60 font-semibold flex items-center gap-1.5 cursor-pointer shadow-xs"
                title={t('tour.btn_restart')}
              >
                <Sparkles className="w-3.5 h-3.5 text-indigo-300 animate-pulse" />
                <span>{t('tour.btn_restart')}</span>
              </button>
            )}
            <button
              onClick={onOpenNewProject}
              className="btn btn-sm bg-white text-slate-900 hover:bg-slate-100 font-bold shadow-sm cursor-pointer flex items-center gap-1.5"
            >
              <Plus className="w-4 h-4 text-indigo-600" />
              <span>{isVietnamese ? 'Đề tài mới' : 'New Project'}</span>
            </button>
            {totalProjects > 0 && (
              <button
                onClick={() => setActiveTab('synthesis')}
                className="btn btn-sm bg-indigo-600 hover:bg-indigo-500 text-white font-bold shadow-primary-sm cursor-pointer flex items-center gap-1.5"
              >
                <Bot className="w-4 h-4" />
                <span>{isVietnamese ? 'Mở AI Workspace' : 'Open Workspace'}</span>
              </button>
            )}
          </div>

        </div>

        {/* Active Project Meta & Status Bar (Only if project exists) */}
        {totalProjects > 0 && activeProject && (
          <div className="mt-6 pt-6 border-t border-white/10 flex flex-wrap items-center justify-between gap-4 text-xs">
            <div className="flex flex-wrap items-center gap-2">
              <span className="px-3 py-1.5 rounded-lg bg-white/10 backdrop-blur-md text-indigo-200 font-bold text-[11px] flex items-center gap-1.5 border border-white/10">
                <FolderKanban className="w-3.5 h-3.5 text-indigo-300" />
                <span>{activeProject?.research_field || (isVietnamese ? 'Lĩnh vực học thuật' : 'Academic Field')}</span>
              </span>
              <span className="px-3 py-1.5 rounded-lg bg-white/10 backdrop-blur-md text-slate-200 font-mono text-[11px] border border-white/10">
                {isVietnamese ? 'Năm' : 'Years'}: {activeProject?.year_from || 2020} – {activeProject?.year_to || 2026}
              </span>
              <span className="px-3 py-1.5 rounded-lg bg-emerald-500/20 backdrop-blur-md text-emerald-300 font-bold text-[11px] flex items-center gap-1 border border-emerald-500/30">
                <Check className="w-3.5 h-3.5 text-emerald-400" />
                <span>{activeProject?.paper_count > 0 ? `${activeProject.paper_count} ${isVietnamese ? 'bài báo đã nạp' : 'papers loaded'}` : (isVietnamese ? 'Chưa nạp bài báo' : 'No papers loaded')}</span>
              </span>
            </div>

            <div className="flex items-center gap-2 text-slate-300 text-xs">
              <Clock className="w-3.5 h-3.5 text-indigo-400" />
              <span>{isVietnamese ? 'Cập nhật gần nhất:' : 'Last updated:'} <strong className="text-white">{isVietnamese ? 'Hôm nay' : 'Today'}</strong></span>
            </div>
          </div>
        )}
      </div>

      {/* ── 2. Real-time KPI Analytics Grid (Modernize Style) ── */}
      <div id="tour-quick-stats" className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        
        <div className="card p-5 space-y-3 bg-white dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800 shadow-xs hover:shadow-sm transition-all rounded-2xl">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">{isVietnamese ? 'Đề tài Nghiên cứu' : 'Research Projects'}</span>
            <div className="w-10 h-10 rounded-xl bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 flex items-center justify-center">
              <FolderKanban className="w-5 h-5" />
            </div>
          </div>
          <div>
            <p className="text-2xl sm:text-3xl font-extrabold font-display text-slate-800 dark:text-white leading-none">{totalProjects}</p>
            <div className="mt-2 flex items-center gap-1.5">
              <span className="badge badge-primary text-[10px]">{isVietnamese ? 'Độc lập' : 'Active'}</span>
              <span className="text-[11px] text-slate-400">{isVietnamese ? 'Đang quản lý' : 'Managed'}</span>
            </div>
          </div>
        </div>

        <div className="card p-5 space-y-3 bg-white dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800 shadow-xs hover:shadow-sm transition-all rounded-2xl">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">{isVietnamese ? 'Bài báo Scopus' : 'Scopus Papers'}</span>
            <div className="w-10 h-10 rounded-xl bg-cyan-50 dark:bg-cyan-950/60 text-cyan-600 dark:text-cyan-400 flex items-center justify-center">
              <Database className="w-5 h-5" />
            </div>
          </div>
          <div>
            <p className="text-2xl sm:text-3xl font-extrabold font-display text-slate-800 dark:text-white leading-none">{totalPapers}</p>
            <div className="mt-2 flex items-center gap-1.5">
              <span className="badge badge-success text-[10px]">{totalPapers > 0 ? 'Verified' : '0'}</span>
              <span className="text-[11px] text-emerald-600 dark:text-emerald-400 font-semibold">
                {totalPapers > 0 ? (isVietnamese ? '100% Đã xác minh' : '100% Verified') : (isVietnamese ? 'Chưa nạp bài' : 'No papers')}
              </span>
            </div>
          </div>
        </div>

        <div className="card p-5 space-y-3 bg-white dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800 shadow-xs hover:shadow-sm transition-all rounded-2xl">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">{isVietnamese ? 'Đã Sàng lọc PRISMA' : 'PRISMA Screened'}</span>
            <div className="w-10 h-10 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </div>
          <div>
            <p className="text-2xl sm:text-3xl font-extrabold font-display text-slate-800 dark:text-white leading-none">{totalScreened}</p>
            <div className="mt-2 flex items-center gap-1.5">
              <span className="badge badge-success text-[10px]">{totalScreened > 0 ? 'Included' : '0'}</span>
              <span className="text-[11px] text-slate-400">
                {totalScreened > 0 ? (isVietnamese ? 'Đạt tiêu chuẩn' : 'Met criteria') : (isVietnamese ? 'Chưa sàng lọc' : 'Not screened')}
              </span>
            </div>
          </div>
        </div>

        <div className="card p-5 space-y-3 bg-white dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800 shadow-xs hover:shadow-sm transition-all rounded-2xl">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">{isVietnamese ? 'Khoảng trống Đề tài' : 'Research Gaps'}</span>
            <div className="w-10 h-10 rounded-xl bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 flex items-center justify-center">
              <Target className="w-5 h-5" />
            </div>
          </div>
          <div>
            <p className="text-2xl sm:text-3xl font-extrabold font-display text-slate-800 dark:text-white leading-none">{totalGaps}</p>
            <div className="mt-2 flex items-center gap-1.5">
              <span className="badge badge-warning text-[10px]">{totalGaps > 0 ? 'Extracted' : '0'}</span>
              <span className="text-[11px] text-amber-600 dark:text-amber-400 font-semibold">
                {totalGaps > 0 ? (isVietnamese ? 'Cơ hội mới' : 'New angles') : (isVietnamese ? 'Chưa bóc tách' : 'Pending')}
              </span>
            </div>
          </div>
        </div>

      </div>

      {/* ── 3. IF NO PROJECTS: Show Empty State Onboarding Guide ───────── */}
      {totalProjects === 0 ? (
        <div className="card p-8 md:p-12 text-center space-y-6 bg-surface-50/50 dark:bg-surface-900/40 border-dashed border-2 border-surface-200 dark:border-surface-800 rounded-2xl">
          <div className="w-16 h-16 rounded-2xl bg-primary-100 dark:bg-primary-950/60 text-primary-600 dark:text-primary-400 flex items-center justify-center mx-auto shadow-sm">
            <FolderPlus className="w-8 h-8" />
          </div>

          <div className="max-w-md mx-auto space-y-2">
            <h2 className="font-display font-bold text-lg text-surface-900 dark:text-white">
              {isVietnamese ? 'Bắt đầu đề tài nghiên cứu đầu tiên của bạn' : 'Start Your First Literature Review Project'}
            </h2>
            <p className="text-xs text-surface-500 dark:text-surface-400 leading-relaxed">
              {isVietnamese
                ? 'Hệ thống hỗ trợ toàn bộ quy trình SLR khép kín: từ phân tích khung PICO, tra cứu Scopus Q1–Q4, sàng lọc PRISMA đến bóc tách ma trận so sánh phương pháp.'
                : 'Automate the end-to-end SLR pipeline: PICO scoping, Scopus Q1–Q4 discovery, PRISMA screening, and cross-paper matrix synthesis.'}
            </p>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            <button
              onClick={onOpenNewProject}
              className="btn btn-primary px-6 py-2.5 font-bold shadow-primary-sm cursor-pointer flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              <span>{isVietnamese ? 'Tạo đề tài nghiên cứu đầu tiên' : 'Create First Project'}</span>
            </button>
            <button
              onClick={() => setActiveTab('setup')}
              className="btn btn-secondary px-5 py-2.5 font-semibold cursor-pointer flex items-center gap-2"
            >
              <span>{isVietnamese ? 'Khám phá Cấu hình PICO' : 'Explore PICO Setup'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>

          {/* 3 Steps Guide */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-8 text-left border-t border-surface-200 dark:border-surface-800">
            <div className="p-4 rounded-xl bg-white dark:bg-surface-800 border border-surface-100 dark:border-surface-700 space-y-2">
              <div className="w-7 h-7 rounded-lg bg-primary-100 dark:bg-primary-950 text-primary-600 dark:text-primary-400 font-bold text-xs flex items-center justify-center">
                1
              </div>
              <p className="font-bold text-xs text-surface-900 dark:text-white">
                {isVietnamese ? 'Thiết lập PICO & Tiêu chí' : 'PICO & Protocol Setup'}
              </p>
              <p className="text-[11px] text-surface-500 dark:text-surface-400">
                {isVietnamese
                  ? 'Nhập câu hỏi nghiên cứu, AI tự động gợi ý tiêu chí Chọn / Loại chuẩn PRISMA.'
                  : 'Define research questions; AI suggests PRISMA Inclusion/Exclusion criteria.'}
              </p>
            </div>

            <div className="p-4 rounded-xl bg-white dark:bg-surface-800 border border-surface-100 dark:border-surface-700 space-y-2">
              <div className="w-7 h-7 rounded-lg bg-sky-100 dark:bg-sky-950 text-sky-600 dark:text-sky-400 font-bold text-xs flex items-center justify-center">
                2
              </div>
              <p className="font-bold text-xs text-surface-900 dark:text-white">
                {isVietnamese ? 'Tra cứu & Xác minh Scopus' : 'Search & Scopus Validation'}
              </p>
              <p className="text-[11px] text-surface-500 dark:text-surface-400">
                {isVietnamese
                  ? 'Tra cứu hàng trăm bài báo Google Scholar, kiểm tra chỉ số Q1–Q4 và phát hiện bài trùng.'
                  : 'Search Google Scholar, verify Scopus quartiles, and filter duplicates.'}
              </p>
            </div>

            <div className="p-4 rounded-xl bg-white dark:bg-surface-800 border border-surface-100 dark:border-surface-700 space-y-2">
              <div className="w-7 h-7 rounded-lg bg-emerald-100 dark:bg-emerald-950 text-emerald-600 dark:text-emerald-400 font-bold text-xs flex items-center justify-center">
                3
              </div>
              <p className="font-bold text-xs text-surface-900 dark:text-white">
                {isVietnamese ? 'Bóc tách Ma trận & Xuất bản' : 'Matrix Synthesis & Export'}
              </p>
              <p className="text-[11px] text-surface-500 dark:text-surface-400">
                {isVietnamese
                  ? 'Tự động trích xuất bảng so sánh phương pháp, phát hiện Research Gaps và xuất BibTeX.'
                  : 'Extract methodology matrix, identify research gaps, and export BibTeX.'}
              </p>
            </div>
          </div>
        </div>
      ) : (
        /* ── 4. IF USER HAS PROJECTS: Real PRISMA Funnel & Gaps ─────────── */
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* Left (7 cols): Real PRISMA 2020 Funnel */}
          <div className="lg:col-span-7 card p-6 space-y-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-primary-600 dark:text-primary-400" />
                <h3 className="font-display font-bold text-sm text-surface-900 dark:text-white">
                  {isVietnamese ? 'Sơ đồ Phễu Sàng lọc PRISMA (Dự án Hiện tại)' : 'PRISMA Screening Funnel (Active Project)'}
                </h3>
              </div>
              <span className="badge badge-primary text-[10px]">
                {activeProject?.name?.slice(0, 20)}...
              </span>
            </div>

            <div className="space-y-3">
              
              {/* Step 1: Identification */}
              <div className="p-3.5 rounded-xl bg-surface-50 dark:bg-surface-800/60 border border-surface-200 dark:border-surface-700 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="w-7 h-7 rounded-lg bg-primary-100 dark:bg-primary-950 text-primary-700 dark:text-primary-300 font-bold text-xs flex items-center justify-center">
                    1
                  </span>
                  <div>
                    <p className="text-xs font-bold text-surface-900 dark:text-white">
                      {isVietnamese ? 'Giai đoạn Nhận diện (Identification)' : 'Identification Phase'}
                    </p>
                    <p className="text-[11px] text-surface-400">
                      {isVietnamese ? 'Tra cứu Google Scholar & Scopus API' : 'Google Scholar & Scopus Search'}
                    </p>
                  </div>
                </div>
                <span className="font-mono font-bold text-sm text-surface-900 dark:text-white">
                  {activeProject?.paper_count || 0} records
                </span>
              </div>

              {/* Step 2: Screening */}
              <div className="p-3.5 rounded-xl bg-surface-50 dark:bg-surface-800/60 border border-surface-200 dark:border-surface-700 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="w-7 h-7 rounded-lg bg-sky-100 dark:bg-sky-950 text-sky-700 dark:text-sky-300 font-bold text-xs flex items-center justify-center">
                    2
                  </span>
                  <div>
                    <p className="text-xs font-bold text-surface-900 dark:text-white">
                      {isVietnamese ? 'Lọc Trùng lặp & Xác minh Scopus' : 'Deduplication & Scopus Verification'}
                    </p>
                    <p className="text-[11px] text-surface-400">
                      {isVietnamese ? 'Kiểm tra xếp hạng Q1–Q4' : 'Verified Scopus rankings'}
                    </p>
                  </div>
                </div>
                <span className="font-mono font-bold text-sm text-emerald-600 dark:text-emerald-400">
                  {activeProject?.paper_count || 0} verified
                </span>
              </div>

              {/* Step 3: Eligibility */}
              <div className="p-3.5 rounded-xl bg-surface-50 dark:bg-surface-800/60 border border-surface-200 dark:border-surface-700 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="w-7 h-7 rounded-lg bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 font-bold text-xs flex items-center justify-center">
                    3
                  </span>
                  <div>
                    <p className="text-xs font-bold text-surface-900 dark:text-white">
                      {isVietnamese ? 'Sàng lọc Tiêu chí Đạt yêu cầu (Inclusion)' : 'Eligibility & Inclusion Screening'}
                    </p>
                    <p className="text-[11px] text-surface-400">
                      {isVietnamese ? 'Đối chiếu bộ tiêu chuẩn PICO đã định hình' : 'Filtered against PICO criteria'}
                    </p>
                  </div>
                </div>
                <span className="font-mono font-bold text-sm text-surface-900 dark:text-white">
                  {activeProject?.screened_count || 0} passed
                </span>
              </div>

              {/* Step 4: Included */}
              <div className="p-3.5 rounded-xl bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800/60 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="w-7 h-7 rounded-lg bg-emerald-600 text-white font-bold text-xs flex items-center justify-center shadow-xs">
                    4
                  </span>
                  <div>
                    <p className="text-xs font-bold text-emerald-900 dark:text-emerald-200">
                      {isVietnamese ? 'Đưa vào Tổng hợp SLR & Bóc tách Ma trận' : 'Included for SLR Synthesis'}
                    </p>
                    <p className="text-[11px] text-emerald-700/80 dark:text-emerald-400">
                      {isVietnamese ? 'Nạp vào Không gian làm việc AI RAG' : 'Loaded into AI Workspace'}
                    </p>
                  </div>
                </div>
                <span className="font-mono font-bold text-sm text-emerald-700 dark:text-emerald-300">
                  {activeProject?.screened_count || 0} studies
                </span>
              </div>

            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setActiveTab('search')}
                className="btn btn-secondary btn-sm flex items-center gap-1.5 cursor-pointer font-semibold"
              >
                <span>{isVietnamese ? 'Tiếp tục tìm kiếm bài báo' : 'Continue Paper Search'}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Right (5 cols): Research Gaps Discovered */}
          <div className="lg:col-span-5 card p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Target className="w-5 h-5 text-violet-600 dark:text-violet-400" />
                <h3 className="font-display font-bold text-sm text-surface-900 dark:text-white">
                  {isVietnamese ? 'Khoảng trống Nghiên cứu' : 'Research Gaps'}
                </h3>
              </div>
              <span className="badge badge-warning text-[10px]">
                {activeGaps.length > 0 ? 'AI Discovered' : 'Pending'}
              </span>
            </div>

            {activeGaps.length > 0 ? (
              <div className="space-y-3">
                {activeGaps.map((gap, i) => (
                  <div
                    key={i}
                    className="p-3.5 rounded-xl border border-surface-200 dark:border-surface-700 bg-surface-50/50 dark:bg-surface-800/40 hover:border-violet-400 transition-all space-y-1.5 relative group"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="badge badge-secondary text-[9px] font-mono">
                        {gap.tag || 'Gap'}
                      </span>
                      <span className="text-[10px] text-amber-600 dark:text-amber-400 font-semibold">
                        {gap.impact || 'High Priority'}
                      </span>
                    </div>
                    <p className="font-bold text-xs text-surface-900 dark:text-white leading-snug">
                      {gap.title}
                    </p>
                    <p className="text-[11px] text-surface-500 dark:text-surface-400 leading-relaxed line-clamp-2">
                      {gap.desc}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-6 rounded-xl bg-surface-50 dark:bg-surface-800/40 border border-surface-200 dark:border-surface-700 text-center space-y-3 my-auto">
                <Target className="w-8 h-8 text-surface-400 mx-auto" />
                <p className="text-xs text-surface-500 dark:text-surface-400">
                  {isVietnamese
                    ? 'Chưa phát hiện khoảng trống nghiên cứu cho đề tài này. Hãy nạp thêm bài báo và mở AI Workspace để hệ thống bóc tách.'
                    : 'No research gaps extracted yet for this project. Load papers and open AI Workspace to run synthesis.'}
                </p>
                <button
                  onClick={() => setActiveTab('synthesis')}
                  className="btn btn-secondary btn-xs mx-auto cursor-pointer flex items-center gap-1 font-semibold"
                >
                  <Bot className="w-3.5 h-3.5 text-primary-500" />
                  <span>{isVietnamese ? 'Mở AI Workspace' : 'Open Workspace'}</span>
                </button>
              </div>
            )}
          </div>

        </div>
      )}

      {/* ── 5. Project Management List (With Clean "..." 3-Dot Menu) ─────── */}
      {totalProjects > 0 && (
        <div className="card p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-display font-bold text-base text-surface-900 dark:text-white">
                {isVietnamese ? 'Danh sách Đề tài Nghiên cứu Đang Quản lý' : 'Managed Research Projects'}
              </h3>
              <p className="text-xs text-surface-400">
                {isVietnamese ? 'Ghim lên đầu, chỉnh sửa tên, chia sẻ liên kết hoặc xóa đề tài độc lập' : 'Pin to top, rename, share links, or delete projects'}
              </p>
            </div>
            <button
              onClick={onOpenNewProject}
              className="btn btn-primary btn-sm flex items-center gap-1.5 cursor-pointer font-bold"
            >
              <Plus className="w-4 h-4" />
              <span>{isVietnamese ? 'Tạo đề tài mới' : 'New Project'}</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pt-2">
            {projects.map((proj) => {
              const isActive = proj.id === activeProjectId;
              const isEditing = editingProjectId === proj.id;
              const isConfirmingDelete = deleteConfirmId === proj.id;
              const isMenuOpen = activeMenuProjectId === proj.id;

              return (
                <div
                  key={proj.id}
                  onClick={() => !isEditing && !isConfirmingDelete && switchProject(proj.id)}
                  className={`p-4 rounded-xl border transition-all space-y-3 relative group ${
                    isActive
                      ? 'bg-primary-50/40 dark:bg-primary-950/30 border-primary-500 shadow-xs'
                      : 'bg-white dark:bg-surface-800/60 border-surface-200 dark:border-surface-700 hover:border-primary-400 cursor-pointer'
                  }`}
                >
                  {/* Top Bar on Card */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-1.5">
                      {proj.is_pinned && (
                        <span className="badge bg-primary-100 dark:bg-primary-950 text-primary-700 dark:text-primary-300 text-[10px] flex items-center gap-1">
                          <Pin className="w-3 h-3 fill-primary-600" />
                          <span>{isVietnamese ? 'Đã ghim' : 'Pinned'}</span>
                        </span>
                      )}
                      <span className="badge badge-primary text-[10px]">
                        {proj.research_field || (isVietnamese ? 'Nghiên cứu' : 'Research')}
                      </span>
                    </div>

                    {/* Single Clean "..." Action Button */}
                    <div className="relative" onClick={e => e.stopPropagation()}>
                      <button
                        type="button"
                        onClick={e => {
                          e.stopPropagation();
                          setActiveMenuProjectId(isMenuOpen ? null : proj.id);
                        }}
                        className={`p-1.5 rounded-lg text-surface-400 hover:text-surface-700 dark:hover:text-surface-200 hover:bg-surface-100 dark:hover:bg-surface-700 transition-colors cursor-pointer ${
                          isMenuOpen ? 'bg-surface-100 dark:bg-surface-700 text-surface-800 dark:text-white' : ''
                        }`}
                        title={isVietnamese ? 'Tùy chọn đề tài' : 'Project options'}
                      >
                        <MoreVertical className="w-4 h-4" />
                      </button>

                      {/* Floating Action Menu for Card */}
                      {isMenuOpen && (
                        <div
                          className="absolute right-0 top-full mt-1 z-50 w-44 rounded-xl shadow-2xl bg-white dark:bg-surface-800 border border-surface-200 dark:border-surface-700 py-1 space-y-0.5 animate-slide-up text-left"
                        >
                          {/* 1. Pin / Unpin */}
                          <button
                            type="button"
                            onClick={e => handleTogglePin(e, proj.id, proj.is_pinned)}
                            className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-surface-700 dark:text-surface-200 hover:bg-primary-50 dark:hover:bg-primary-950/50 hover:text-primary-600 dark:hover:text-primary-400 cursor-pointer transition-colors"
                          >
                            {proj.is_pinned ? <PinOff className="w-3.5 h-3.5 text-primary-500" /> : <Pin className="w-3.5 h-3.5" />}
                            <span>{proj.is_pinned ? (isVietnamese ? 'Bỏ ghim đề tài' : 'Unpin project') : (isVietnamese ? 'Ghim lên đầu' : 'Pin to top')}</span>
                          </button>

                          {/* 2. Rename */}
                          <button
                            type="button"
                            onClick={e => handleStartRename(e, proj)}
                            className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-surface-700 dark:text-surface-200 hover:bg-primary-50 dark:hover:bg-primary-950/50 hover:text-primary-600 dark:hover:text-primary-400 cursor-pointer transition-colors"
                          >
                            <Pencil className="w-3.5 h-3.5" />
                            <span>{isVietnamese ? 'Đổi tên đề tài' : 'Rename project'}</span>
                          </button>

                          {/* 3. Share */}
                          <button
                            type="button"
                            onClick={e => handleShare(e, proj)}
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
                              setDeleteConfirmId(proj.id);
                            }}
                            className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/40 cursor-pointer transition-colors"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                            <span>{isVietnamese ? 'Xóa đề tài' : 'Delete project'}</span>
                          </button>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Project Name or Inline Edit */}
                  {isEditing ? (
                    <div className="space-y-2 pt-1" onClick={e => e.stopPropagation()}>
                      <input
                        type="text"
                        value={editingName}
                        onChange={e => setEditingName(e.target.value)}
                        onKeyDown={e => {
                          if (e.key === 'Enter') handleSaveRename(e, proj.id);
                          if (e.key === 'Escape') handleCancelRename(e);
                        }}
                        className="input input-sm w-full text-xs font-semibold"
                        autoFocus
                      />
                      <div className="flex items-center justify-end gap-2">
                        <button
                          type="button"
                          onClick={handleCancelRename}
                          className="btn btn-secondary btn-xs cursor-pointer"
                        >
                          {isVietnamese ? 'Hủy' : 'Cancel'}
                        </button>
                        <button
                          type="button"
                          onClick={e => handleSaveRename(e, proj.id)}
                          className="btn btn-primary btn-xs cursor-pointer"
                        >
                          {isVietnamese ? 'Lưu' : 'Save'}
                        </button>
                      </div>
                    </div>
                  ) : isConfirmingDelete ? (
                    <div className="p-2.5 space-y-2 bg-red-50 dark:bg-red-950/40 rounded-xl border border-red-200 dark:border-red-800" onClick={e => e.stopPropagation()}>
                      <p className="text-xs font-semibold text-red-700 dark:text-red-300 flex items-center gap-1.5">
                        <AlertTriangle className="w-4 h-4 text-red-500 shrink-0" />
                        <span>{isVietnamese ? 'Bạn có chắc chắn muốn xóa đề tài này không?' : 'Are you sure you want to delete this project?'}</span>
                      </p>
                      <div className="flex items-center justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => setDeleteConfirmId(null)}
                          className="px-2.5 py-1 text-xs rounded-lg bg-surface-200 dark:bg-surface-700 text-surface-700 dark:text-surface-300 cursor-pointer"
                        >
                          {isVietnamese ? 'Hủy' : 'Cancel'}
                        </button>
                        <button
                          type="button"
                          onClick={e => handleDelete(e, proj.id)}
                          className="px-2.5 py-1 text-xs rounded-lg bg-red-600 text-white font-bold hover:bg-red-700 cursor-pointer"
                        >
                          {isVietnamese ? 'Xóa vĩnh viễn' : 'Delete'}
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div>
                      <h4 className="font-bold text-xs text-surface-900 dark:text-white line-clamp-2 leading-snug">
                        {proj.name}
                      </h4>
                      {isActive && (
                        <p className="text-[10px] font-bold text-primary-600 dark:text-primary-400 flex items-center gap-1 mt-1">
                          <Check className="w-3 h-3" />
                          <span>{isVietnamese ? 'Đang chọn làm việc' : 'Currently Active'}</span>
                        </p>
                      )}
                    </div>
                  )}

                  <div className="flex items-center justify-between text-[11px] text-surface-400 pt-2 border-t border-surface-100 dark:border-surface-700/60">
                    <span>{proj.paper_count || 0} {isVietnamese ? 'bài báo' : 'papers'}</span>
                    <span>{proj.year_from || 2020} – {proj.year_to || 2026}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

    </div>
  );
}
