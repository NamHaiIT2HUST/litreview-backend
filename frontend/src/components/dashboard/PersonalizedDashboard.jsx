import React, { useState, useEffect } from 'react';
import {
  BookOpen, Sparkles, Search, Layers, ShieldCheck, ArrowRight,
  CheckCircle2, Bot, Database, Zap, FileText, Check, ChevronRight,
  Plus, Target, BarChart2, TrendingUp, Clock, Copy, Trash2,
  ExternalLink, ArrowUpRight, Filter, AlertCircle, RefreshCw,
  FolderKanban, Award, Compass, PieChart, FolderPlus, HelpCircle,
  Pin, PinOff, Pencil, Share2, AlertTriangle, X, MoreVertical,
  LayoutGrid, List, Settings, Globe, Cpu, Mic, Heart, Lightbulb,
  Laptop, Activity, SlidersHorizontal
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { useProject } from '../../contexts/ProjectContext';
import { useLanguage } from '../../contexts/LanguageContext';

// Curated Featured Notebooks inspired by Google NotebookLM
const FEATURED_NOTEBOOKS = [
  {
    id: 'feat_medical_ai',
    title: 'Đôi mắt có thể tiết lộ sức khỏe tổng quát: AI trong Chẩn đoán Y sinh',
    source: 'Google Research',
    date: '3 thg 7, 2026',
    sourcesCount: 14,
    image: 'https://images.unsplash.com/photo-1579684385127-1ef15d508118?w=800&auto=format&fit=crop&q=80',
    field: 'Y sinh & Chẩn đoán Y tế',
    question: 'Ứng dụng các kiến trúc Vision-Language Models và Deep Learning trong phân tích hình ảnh và chẩn đoán y sinh học.'
  },
  {
    id: 'feat_llm_reasoning',
    title: 'Chuỗi Tư duy (Chain-of-Thought) & Multi-Agent Reasoning trên LLM',
    source: 'OpenStax & Stanford',
    date: '31 thg 1, 2026',
    sourcesCount: 13,
    image: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800&auto=format&fit=crop&q=80',
    field: 'Xử lý Ngôn ngữ Tự nhiên & LLM',
    question: 'Cơ chế kích hoạt tư duy (Chain-of-Thought) và multi-agent reasoning trong giải quyết bài toán phức tạp trên mô hình ngôn ngữ lớn.'
  },
  {
    id: 'feat_robotics',
    title: 'SLAM & Deep Reinforcement Learning cho Robot Tự hành',
    source: 'U.S. National Archives with Google',
    date: '18 thg 2, 2026',
    sourcesCount: 39,
    image: 'https://images.unsplash.com/photo-1485827404703-89b55fcc595e?w=800&auto=format&fit=crop&q=80',
    field: 'Robotics & Hệ thống Tự hành',
    question: 'Thuật toán học tăng cường sâu (Deep RL) và SLAM trong điều hướng tự chủ và thao tác robot trong môi trường không xác định.'
  },
  {
    id: 'feat_climate_energy',
    title: 'Mô hình Học máy Tối ưu hóa Lưới điện & Năng lượng Tái tạo',
    source: 'The Atlantic',
    date: '11 thg 4, 2026',
    sourcesCount: 71,
    image: 'https://images.unsplash.com/photo-1473341304170-971dccb5ac1e?w=800&auto=format&fit=crop&q=80',
    field: 'Khoa học Môi trường & Năng lượng',
    question: 'Ứng dụng học máy và mô hình dự báo chuỗi thời gian trong tối ưu hóa lưới điện thông minh và năng lượng tái tạo.'
  },
  {
    id: 'feat_multimodal_vision',
    title: 'Bản Thiết Kế Multimodal RAG & Zero-shot Object Detection 3D',
    source: 'Founders & MIT AI',
    date: '17 thg 4, 2026',
    sourcesCount: 44,
    image: 'https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=800&auto=format&fit=crop&q=80',
    field: 'Khoa học Máy tính & Trí tuệ Nhân tạo',
    question: 'Kiến trúc Multimodal RAG và Zero-shot Object Detection trong giám sát không gian 3D và xử lý video tốc độ cao.'
  }
];

// Helper to get nice Notebook icons matching NotebookLM
const getNotebookIcon = (title = '', field = '') => {
  const text = (title + ' ' + field).toLowerCase();
  if (text.includes('robot') || text.includes('tự hành')) {
    return <Bot className="w-5 h-5 text-indigo-400" />;
  }
  if (text.includes('y tế') || text.includes('sức khỏe') || text.includes('tim') || text.includes('med')) {
    return <Heart className="w-5 h-5 text-rose-400" />;
  }
  if (text.includes('mạng') || text.includes('chip') || text.includes('embedded') || text.includes('nhúng')) {
    return <Cpu className="w-5 h-5 text-emerald-400" />;
  }
  if (text.includes('interview') || text.includes('audio') || text.includes('tiếng') || text.includes('thoại')) {
    return <Mic className="w-5 h-5 text-purple-400" />;
  }
  if (text.includes('toán') || text.includes('lý thuyết') || text.includes('suy luận') || text.includes('llm')) {
    return <Lightbulb className="w-5 h-5 text-amber-400" />;
  }
  if (text.includes('dữ liệu') || text.includes('data') || text.includes('cấu trúc')) {
    return <Laptop className="w-5 h-5 text-cyan-400" />;
  }
  return <BookOpen className="w-5 h-5 text-blue-400" />;
};

export default function PersonalizedDashboard({ setActiveTab, onOpenNewProject, onStartTour }) {
  const { currentUser } = useAuth();
  const { 
    projects, activeProject, activeProjectId, 
    switchProject, togglePinProject, renameProject, 
    deleteProject, duplicateProject, shareProject,
    createProject
  } = useProject();
  const { t, language } = useLanguage();

  const isVietnamese = language === 'vi';

  const [activeFilter, setActiveFilter] = useState('all'); // 'all' | 'mine' | 'featured' | 'shared' | 'collections'
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState('grid'); // 'grid' | 'list'
  const [sortBy, setSortBy] = useState('recent'); // 'recent' | 'name' | 'sources'

  const [activeMenuProjectId, setActiveMenuProjectId] = useState(null);
  const [editingProjectId, setEditingProjectId] = useState(null);
  const [editingName, setEditingName] = useState('');
  const [dashboardToast, setDashboardToast] = useState(null);

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

  const handleOpenNotebook = (proj) => {
    switchProject(proj.id);
    setActiveTab('synthesis'); // Open workspace
  };

  const handleOpenFeatured = async (feat) => {
    const existing = projects.find(p => p.name.toLowerCase().includes(feat.field.toLowerCase()) || p.name === feat.title);
    if (existing) {
      switchProject(existing.id);
      setActiveTab('synthesis');
      return;
    }

    const newProj = await createProject({
      name: feat.title,
      research_question: feat.question,
      research_field: feat.field,
      year_from: 2020,
      year_to: 2026,
      paper_count: feat.sourcesCount,
    });
    switchProject(newProj.id);
    setActiveTab('synthesis');
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
      showToast(isVietnamese ? 'Đã đổi tên sổ ghi chú thành công!' : 'Notebook renamed successfully!');
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
    showToast(isPinned ? (isVietnamese ? 'Đã bỏ ghim sổ ghi chú.' : 'Unpinned.') : (isVietnamese ? 'Đã ghim lên đầu!' : 'Pinned to top!'));
  };

  const handleShare = async (e, proj) => {
    e.stopPropagation();
    setActiveMenuProjectId(null);
    await shareProject(proj.id);
    showToast(isVietnamese ? 'Đã sao chép liên kết vào bộ nhớ tạm!' : 'Link copied to clipboard!');
  };

  const handleDelete = (e, projId) => {
    e.stopPropagation();
    setActiveMenuProjectId(null);
    deleteProject(projId);
    showToast(isVietnamese ? 'Đã xóa sổ ghi chú.' : 'Notebook deleted.');
  };

  // Filter and Sort user projects
  const filteredProjects = projects.filter(p => {
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return p.name.toLowerCase().includes(q) || (p.research_field || '').toLowerCase().includes(q);
    }
    return true;
  }).sort((a, b) => {
    if (a.is_pinned && !b.is_pinned) return -1;
    if (!a.is_pinned && b.is_pinned) return 1;
    if (sortBy === 'name') return a.name.localeCompare(b.name);
    if (sortBy === 'sources') return (b.paper_count || 0) - (a.paper_count || 0);
    return new Date(b.updated_at || 0) - new Date(a.updated_at || 0);
  });

  const userInitials = currentUser?.name 
    ? currentUser.name.split(' ').map(n => n[0]).join('').slice(-2).toUpperCase() 
    : 'NH';

  return (
    <div className="min-h-screen bg-[#171A21] text-slate-100 font-sans selection:bg-blue-600 selection:text-white flex flex-col">
      
      {/* ── Toast Notification (NotebookLM style bottom pill) ── */}
      {dashboardToast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 px-5 py-3 rounded-2xl bg-slate-900 text-white text-xs font-semibold shadow-2xl flex items-center gap-3 border border-slate-700/80 animate-slide-up">
          <CheckCircle2 className="w-4 h-4 text-blue-400 shrink-0" />
          <span>{dashboardToast}</span>
        </div>
      )}
      
      {/* ── 1. Top NotebookLM Header Bar ── */}
      <header className="sticky top-0 z-40 w-full bg-[#171A21]/95 backdrop-blur-md border-b border-slate-800/80 px-4 sm:px-8 py-3.5 flex items-center justify-between gap-4">
        
        {/* Left: Brand Logo & Notebook Title */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
            <BookOpen className="w-5 h-5" />
          </div>
          <span className="font-display font-bold text-lg text-white tracking-tight">
            LitReview Notebook
          </span>
        </div>

        {/* Right: Controls, Search, View Mode, + Tạo mới, Profile */}
        <div className="flex items-center gap-3">
          
          {/* Search Input */}
          <div className="relative hidden md:block w-48 lg:w-64">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder={isVietnamese ? 'Tìm kiếm sổ ghi chú...' : 'Search notebooks...'}
              className="w-full pl-9 pr-3 py-1.5 rounded-full bg-[#232834] border border-slate-700/70 text-xs text-white placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
            />
          </div>

          {/* Grid / List Toggle */}
          <div className="flex items-center bg-[#232834] p-0.5 rounded-full border border-slate-700/70">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-1.5 rounded-full transition-all cursor-pointer ${viewMode === 'grid' ? 'bg-[#313848] text-white shadow-xs' : 'text-slate-400 hover:text-slate-200'}`}
              title="Chế độ Lưới"
            >
              <LayoutGrid className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-1.5 rounded-full transition-all cursor-pointer ${viewMode === 'list' ? 'bg-[#313848] text-white shadow-xs' : 'text-slate-400 hover:text-slate-200'}`}
              title="Chế độ Danh sách"
            >
              <List className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Sort Dropdown */}
          <select
            value={sortBy}
            onChange={e => setSortBy(e.target.value)}
            className="hidden sm:block px-3 py-1.5 rounded-full bg-[#232834] border border-slate-700/70 text-xs text-slate-200 focus:outline-none cursor-pointer"
          >
            <option value="recent">{isVietnamese ? 'Gần đây nhất' : 'Most recent'}</option>
            <option value="name">{isVietnamese ? 'Tên A - Z' : 'Name A - Z'}</option>
            <option value="sources">{isVietnamese ? 'Số lượng nguồn' : 'Most sources'}</option>
          </select>

          {/* + Tạo mới Button */}
          <button
            onClick={onOpenNewProject}
            className="px-4 py-1.5 rounded-full bg-white hover:bg-slate-100 text-slate-900 font-bold text-xs flex items-center gap-1.5 shadow-md hover:scale-105 transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4 text-slate-900 stroke-[2.5]" />
            <span>{isVietnamese ? 'Tạo mới' : 'New Notebook'}</span>
          </button>

          {/* Tour / Settings / Pro */}
          {onStartTour && (
            <button
              onClick={onStartTour}
              className="p-2 rounded-full text-slate-400 hover:text-white hover:bg-[#232834] transition-colors cursor-pointer"
              title="Hướng dẫn sử dụng"
            >
              <Compass className="w-4 h-4" />
            </button>
          )}

          <div className="px-2 py-0.5 rounded-md bg-blue-500/20 text-blue-400 text-[10px] font-mono font-bold tracking-wider uppercase border border-blue-500/30">
            PRO
          </div>

          {/* User Profile Avatar */}
          {currentUser?.picture ? (
            <img
              src={currentUser.picture}
              alt={currentUser.name}
              className="w-8 h-8 rounded-full object-cover ring-2 ring-blue-500/40 shrink-0"
            />
          ) : (
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-600 to-indigo-600 text-white font-bold text-xs flex items-center justify-center shrink-0">
              {userInitials}
            </div>
          )}

        </div>
      </header>

      {/* ── Main Hub Content Area ── */}
      <main className="flex-1 w-full max-w-7xl mx-auto px-4 sm:px-8 py-6 space-y-8">
        
        {/* ── 2. Filter Category Pills (All, Mine, Featured, Shared, Collections) ── */}
        <div className="flex items-center gap-2 overflow-x-auto custom-scrollbar pb-1 text-xs font-semibold">
          {[
            { id: 'all', label: isVietnamese ? 'Tất cả' : 'All' },
            { id: 'mine', label: isVietnamese ? 'Sổ ghi chú của tôi' : 'My notebooks' },
            { id: 'featured', label: isVietnamese ? 'Sổ ghi chú nổi bật' : 'Featured' },
            { id: 'shared', label: isVietnamese ? 'Được chia sẻ với tôi' : 'Shared with me' },
            { id: 'collections', label: isVietnamese ? 'Tuyển tập' : 'Collections' },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveFilter(tab.id)}
              className={`px-4 py-1.5 rounded-full transition-all whitespace-nowrap cursor-pointer ${
                activeFilter === tab.id
                  ? 'bg-white text-slate-900 font-bold shadow-sm'
                  : 'bg-[#232834] text-slate-300 hover:bg-[#2e3444] hover:text-white border border-slate-700/60'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* ── 3. Section: Sổ ghi chú nổi bật (Featured Notebooks) ── */}
        {(activeFilter === 'all' || activeFilter === 'featured') && (
          <section className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base sm:text-lg font-bold text-white tracking-tight">
                {isVietnamese ? 'Sổ ghi chú nổi bật' : 'Featured Notebooks'}
              </h2>
              <button
                onClick={() => setActiveFilter('featured')}
                className="text-xs font-semibold text-slate-400 hover:text-blue-400 flex items-center gap-1 transition-colors cursor-pointer"
              >
                <span>{isVietnamese ? 'Xem tất cả' : 'View all'}</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3.5">
              {FEATURED_NOTEBOOKS.map(feat => (
                <div
                  key={feat.id}
                  onClick={() => handleOpenFeatured(feat)}
                  className="group relative rounded-2xl overflow-hidden bg-[#202531] border border-slate-800 hover:border-blue-500/80 shadow-md hover:shadow-xl hover:shadow-blue-500/10 transition-all duration-300 cursor-pointer flex flex-col h-56"
                >
                  {/* Cover Image */}
                  <div className="h-28 w-full relative overflow-hidden bg-slate-800 shrink-0">
                    <img
                      src={feat.image}
                      alt={feat.title}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500 filter brightness-90 contrast-110"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-[#202531] via-transparent to-transparent" />
                  </div>

                  {/* Body Content */}
                  <div className="p-3.5 flex flex-col justify-between flex-1 min-w-0">
                    <div>
                      <div className="flex items-center gap-1 text-[10px] font-semibold text-blue-400 truncate">
                        <span className="w-1.5 h-1.5 rounded-full bg-blue-400 shrink-0" />
                        <span className="truncate">{feat.source}</span>
                      </div>
                      <h3 className="font-bold text-xs text-white group-hover:text-blue-300 transition-colors line-clamp-2 mt-1 leading-snug">
                        {feat.title}
                      </h3>
                    </div>

                    {/* Footer Meta */}
                    <div className="flex items-center justify-between text-[10.5px] text-slate-400 pt-1 border-t border-slate-800/60 mt-auto">
                      <span className="truncate">{feat.date}</span>
                      <span className="flex items-center gap-1 text-slate-300 font-medium shrink-0">
                        {feat.sourcesCount} nguồn <Globe className="w-3 h-3 text-slate-400" />
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* ── 4. Section: Sổ ghi chú gần đây (Recent User Notebooks) ── */}
        {(activeFilter === 'all' || activeFilter === 'mine') && (
          <section className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base sm:text-lg font-bold text-white tracking-tight">
                {isVietnamese ? 'Sổ ghi chú gần đây' : 'Recent Notebooks'}
              </h2>
              <span className="text-xs text-slate-400">
                {filteredProjects.length} {isVietnamese ? 'sổ ghi chú' : 'notebooks'}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              
              {/* Card 1: + Tạo sổ ghi chú mới */}
              <button
                onClick={onOpenNewProject}
                className="h-44 rounded-2xl bg-[#202531]/60 hover:bg-[#202531] border border-dashed border-slate-700/80 hover:border-blue-500 flex flex-col items-center justify-center p-6 text-center transition-all group cursor-pointer shadow-sm hover:shadow-md"
              >
                <div className="w-12 h-12 rounded-full bg-[#29303F] group-hover:bg-blue-600 text-slate-300 group-hover:text-white flex items-center justify-center mb-3 transition-all group-hover:scale-110 shadow-inner">
                  <Plus className="w-6 h-6 stroke-[2.5]" />
                </div>
                <span className="font-bold text-xs sm:text-sm text-slate-200 group-hover:text-white transition-colors">
                  {isVietnamese ? 'Tạo sổ ghi chú mới' : 'Create new notebook'}
                </span>
                <span className="text-[11px] text-slate-400 mt-0.5">
                  {isVietnamese ? 'Chuẩn PRISMA & RAG' : 'PRISMA & RAG-ready'}
                </span>
              </button>

              {/* User Projects Cards */}
              {filteredProjects.map((proj) => {
                const isEditing = editingProjectId === proj.id;
                const isMenuOpen = activeMenuProjectId === proj.id;
                const updatedDate = proj.updated_at 
                  ? new Date(proj.updated_at).toLocaleDateString('vi-VN', { day: 'numeric', month: 'short', year: 'numeric' })
                  : (isVietnamese ? 'Hôm nay' : 'Today');

                return (
                  <div
                    key={proj.id}
                    onClick={() => handleOpenNotebook(proj)}
                    className={`group relative h-44 rounded-2xl bg-[#202531] border transition-all duration-200 cursor-pointer p-4 flex flex-col justify-between shadow-sm hover:shadow-lg ${
                      proj.is_pinned
                        ? 'border-blue-500/70 hover:border-blue-400 bg-gradient-to-b from-[#202531] to-[#1c2438]'
                        : 'border-slate-800/90 hover:border-slate-700'
                    }`}
                  >
                    {/* Card Top: Icon & 3-Dot Action Menu */}
                    <div className="flex items-center justify-between shrink-0">
                      <div className="w-9 h-9 rounded-xl bg-[#29303F] border border-slate-700/60 flex items-center justify-center">
                        {getNotebookIcon(proj.name, proj.research_field)}
                      </div>

                      <div className="flex items-center gap-1">
                        {proj.is_pinned && (
                          <Pin className="w-3.5 h-3.5 text-blue-400 fill-blue-400/40" />
                        )}
                        
                        {/* 3-Dot Button */}
                        <div className="relative">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setActiveMenuProjectId(isMenuOpen ? null : proj.id);
                            }}
                            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-[#2E3647] transition-colors cursor-pointer opacity-80 group-hover:opacity-100"
                            title="Tùy chọn sổ ghi chú"
                          >
                            <MoreVertical className="w-4 h-4" />
                          </button>

                          {/* Action Dropdown Menu */}
                          {isMenuOpen && (
                            <div
                              onClick={(e) => e.stopPropagation()}
                              className="absolute right-0 top-full mt-1.5 w-44 rounded-xl bg-[#1E2330] border border-slate-700/80 shadow-2xl p-1 z-50 animate-slide-up text-xs font-semibold text-slate-200"
                            >
                              <button
                                onClick={(e) => handleStartRename(e, proj)}
                                className="w-full px-3 py-2 rounded-lg text-left hover:bg-[#2A3142] flex items-center gap-2 transition-colors cursor-pointer"
                              >
                                <Pencil className="w-3.5 h-3.5 text-slate-400" />
                                <span>{isVietnamese ? 'Đổi tên' : 'Rename'}</span>
                              </button>

                              <button
                                onClick={(e) => handleTogglePin(e, proj.id, proj.is_pinned)}
                                className="w-full px-3 py-2 rounded-lg text-left hover:bg-[#2A3142] flex items-center gap-2 transition-colors cursor-pointer"
                              >
                                {proj.is_pinned ? <PinOff className="w-3.5 h-3.5 text-slate-400" /> : <Pin className="w-3.5 h-3.5 text-slate-400" />}
                                <span>{proj.is_pinned ? (isVietnamese ? 'Bỏ ghim' : 'Unpin') : (isVietnamese ? 'Ghim lên đầu' : 'Pin to top')}</span>
                              </button>

                              <button
                                onClick={(e) => handleShare(e, proj)}
                                className="w-full px-3 py-2 rounded-lg text-left hover:bg-[#2A3142] flex items-center gap-2 transition-colors cursor-pointer"
                              >
                                <Share2 className="w-3.5 h-3.5 text-slate-400" />
                                <span>{isVietnamese ? 'Sao chép liên kết' : 'Copy link'}</span>
                              </button>

                              <div className="my-1 border-t border-slate-700/60" />

                              <button
                                onClick={(e) => handleDelete(e, proj.id)}
                                className="w-full px-3 py-2 rounded-lg text-left hover:bg-rose-950/50 text-rose-400 font-bold flex items-center gap-2 transition-colors cursor-pointer"
                              >
                                <Trash2 className="w-3.5 h-3.5 text-rose-400" />
                                <span>{isVietnamese ? 'Xóa sổ ghi chú' : 'Delete'}</span>
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Card Body: Title (or Inline Editing Input) */}
                    <div className="my-auto min-w-0">
                      {isEditing ? (
                        <div onClick={e => e.stopPropagation()} className="space-y-1.5">
                          <input
                            type="text"
                            autoFocus
                            value={editingName}
                            onChange={e => setEditingName(e.target.value)}
                            onKeyDown={e => {
                              if (e.key === 'Enter') handleSaveRename(e, proj.id);
                              if (e.key === 'Escape') handleCancelRename(e);
                            }}
                            className="w-full px-2.5 py-1 text-xs rounded-lg bg-[#2E3647] border border-blue-500 text-white font-bold focus:outline-none"
                          />
                          <div className="flex items-center gap-1 justify-end">
                            <button
                              onClick={(e) => handleSaveRename(e, proj.id)}
                              className="px-2 py-0.5 rounded bg-blue-600 hover:bg-blue-500 text-[10px] font-bold text-white"
                            >
                              Lưu
                            </button>
                            <button
                              onClick={handleCancelRename}
                              className="px-2 py-0.5 rounded bg-slate-700 hover:bg-slate-600 text-[10px] text-slate-300"
                            >
                              Hủy
                            </button>
                          </div>
                        </div>
                      ) : (
                        <h3 className="font-bold text-xs sm:text-sm text-white group-hover:text-blue-300 transition-colors line-clamp-2 leading-snug">
                          {proj.name}
                        </h3>
                      )}
                    </div>

                    {/* Card Footer: Date & Source Count */}
                    <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400 shrink-0">
                      <span className="truncate">{updatedDate}</span>
                      <span className="font-medium text-slate-300 shrink-0">
                        {proj.paper_count || 0} {isVietnamese ? 'nguồn' : 'sources'}
                      </span>
                    </div>
                  </div>
                );
              })}

            </div>
          </section>
        )}

      </main>

    </div>
  );
}
