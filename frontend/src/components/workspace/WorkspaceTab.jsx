import React, { useCallback, useRef, useState } from 'react';
import ChatPanel from './ChatPanel';
import VerificationPanel from './VerificationPanel';
import { persistedDirectUploadSources } from '../../utils/workspaceSources';
import SynthesisPanel from './SynthesisPanel';
import DataAnalysisPanel from './DataAnalysisPanel';
import RAGEvalHarnessModal from './RAGEvalHarnessModal';
import { reconcileSelectedPaperIds, selectedPapersFromIds } from '../../utils/workspaceScope';
import { useProject } from '../../contexts/ProjectContext';

import { useLanguage } from '../../contexts/LanguageContext';
import {
  Bot,
  UploadCloud,
  FileText,
  Sparkles,
  CheckCircle2,
  Check,
  AlertCircle,
  Loader2,
  Trash2,
  BookOpen,
  PanelLeftClose,
  PanelLeft,
  Plus,
  BarChart2,
  MessageSquare,
  ShieldCheck,
  Clock
} from 'lucide-react';

import { API_BASE, safeFetch } from '../../utils/apiConfig';
const MAX_FILE_SIZE_MB = 20;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

// ─── Source Card ──────────────────────────────────────────────────────────────
function SourceCard({ paper, isChecked, onToggle, onRemove, darkMode }) {
  const { t } = useLanguage();
  return (
    <button
      type="button"
      onClick={() => onToggle(paper.id)}
      className={`group relative w-full text-left py-2 px-3 flex items-center justify-between rounded-xl cursor-pointer transition-all select-none ${
        'hover:bg-slate-100 dark:hover:bg-slate-800/60'
      }`}
    >
      <div className="flex items-center gap-3 overflow-hidden">
        {/* PDF Badge */}
        <div className={`shrink-0 w-6 h-6 rounded flex items-center justify-center font-extrabold text-[8px] ${
          'bg-red-50 text-red-600 border border-red-200 dark:bg-red-950/40 dark:text-red-400 dark:border dark:border-red-900/50'
        }`}>
          PDF
        </div>

        {/* Content */}
        <p className={`text-[13px] font-medium leading-tight truncate pr-4 ${
          'text-slate-700 dark:text-slate-300'
        }`}>
          {paper.title || paper.filename}
        </p>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <button
          type="button"
          onClick={(e) => { 
            e.preventDefault();
            e.stopPropagation(); 
            onRemove(paper.id); 
          }}
          className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/50 transition-all cursor-pointer"
          title={t('workspace.delete_doc')}
        >
          <Trash2 className="w-3.5 h-3.5 pointer-events-none" />
        </button>

        {/* Checkbox */}
        <div
          className={`shrink-0 w-4 h-4 rounded-[4px] flex items-center justify-center transition-all ${
            isChecked
              ? ('bg-slate-700 text-white dark:bg-slate-300 dark:text-slate-900')
              : ('border border-slate-300 bg-transparent dark:border dark:border-slate-600 dark:bg-transparent')
          }`}
        >
          {isChecked && <Check className="w-3 h-3 stroke-[3]" />}
        </div>
      </div>
    </button>
  );
}

function AddSourceButton({ onFiles, isUploading, darkMode }) {
  const { t } = useLanguage();
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef(null);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files).filter((f) =>
      f.name.toLowerCase().endsWith('.pdf')
    );
    if (files.length > 0) onFiles(files);
  }, [onFiles]);

  return (
    <button
      type="button"
      onDrop={handleDrop}
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      onClick={() => !isUploading && inputRef.current?.click()}
      className={`relative w-full flex items-center justify-center gap-2 py-2.5 rounded-full border cursor-pointer transition-all ${
        isDragging
          ? 'border-blue-500 bg-blue-50'
          : isUploading
          ? 'border-blue-200 bg-blue-50/50 cursor-wait'
          : 'border-slate-300 bg-white hover:bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-200'
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf"
        multiple
        className="hidden"
        onChange={(e) => {
          const files = Array.from(e.target.files || []);
          if (files.length > 0) onFiles(files);
          e.target.value = null;
        }}
      />
      {isUploading ? (
        <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
      ) : (
        <Plus className="w-4 h-4" />
      )}
      <span className="text-[13px] font-semibold">
        {isUploading ? t('workspace.uploading') : isDragging ? t('workspace.drop_pdf') : t('workspace.add_source')}
      </span>
    </button>
  );
}

// ─── Upload Queue Item ────────────────────────────────────────────────────────
function UploadQueueItem({ item, onDismiss, darkMode }) {
  const statusIcon = {
    pending: <Loader2 className="w-3.5 h-3.5 text-blue-500 animate-spin shrink-0" />,
    done: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />,
    error: <AlertCircle className="w-3.5 h-3.5 text-red-500 shrink-0" />,
  }[item.status];

  return (
    <div className={`flex items-center gap-2 p-2 rounded-xl text-xs ${item.status === 'error' ? 'bg-red-50/80 dark:bg-red-950/40 border border-red-200 dark:border-red-900/50' : 'bg-slate-50 dark:bg-slate-800'}`}>
      {statusIcon}
      <div className="flex-1 min-w-0">
        <p className="truncate font-semibold dark:text-slate-300 text-slate-700">
          {item.filename}
        </p>
        {item.error && (
          <p className="text-[10px] text-red-500 truncate mt-0.5">{item.error}</p>
        )}
      </div>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="p-1 hover:bg-slate-200 dark:hover:bg-slate-700 rounded text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer shrink-0"
        >
          <X className="w-3 h-3" />
        </button>
      )}
    </div>
  );
}

// ─── Analysis History Sidebar ───────────────────────────────────────────────────
function AnalysisHistorySidebar({ 
  history, 
  onSelect, 
  onNew, 
  activeId, 
  onDelete, 
  onToggleCollapse, 
  darkMode 
}) {
  const { t, language } = useLanguage();
  const isVietnamese = language === 'vi';
  
  return (
    <>
      <div className="flex items-center justify-between px-4 h-14 border-b border-surface-100 dark:border-surface-800 shrink-0">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-primary-600 dark:text-primary-400" />
          <h3 className="section-label">
            {isVietnamese ? 'Lịch sử phân tích' : 'Analysis History'}
          </h3>
        </div>
        <button 
          onClick={onToggleCollapse}
          className="p-1.5 rounded-lg text-surface-400 hover:text-surface-600 dark:hover:text-surface-200 hover:bg-surface-100 dark:hover:bg-surface-800 transition-colors"
          title={isVietnamese ? 'Thu gọn lịch sử' : 'Collapse history'}
        >
          <PanelLeftClose className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-3 space-y-4 pb-4 pt-3 custom-scrollbar">
        <button
          onClick={onNew}
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-full border border-primary-300 bg-primary-50 hover:bg-primary-100 text-primary-700 dark:border-primary-700 dark:bg-primary-900/30 dark:hover:bg-primary-900/50 dark:text-primary-300 transition-all font-semibold text-[13px]"
        >
          <Plus className="w-4 h-4" />
          {isVietnamese ? 'Phân tích mới' : 'New Analysis'}
        </button>

        {history.length === 0 ? (
          <div className="text-center text-surface-400 text-sm mt-8 px-4 italic">
            {isVietnamese ? 'Chưa có lịch sử phân tích nào.' : 'No analysis history yet.'}
          </div>
        ) : (
          <div className="space-y-2">
            {history.map((item) => (
              <div 
                key={item.id}
                className={`group relative w-full text-left p-3 rounded-xl cursor-pointer transition-all border ${
                  activeId === item.id 
                    ? 'border-primary-500 bg-primary-50 dark:border-primary-700 dark:bg-primary-900/30' 
                    : 'border-transparent bg-surface-50 hover:bg-surface-100 dark:bg-surface-800/40 dark:hover:bg-surface-800'
                }`}
                onClick={() => onSelect(item.id)}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <p className={`text-[13px] font-medium leading-snug line-clamp-2 ${activeId === item.id ? 'text-primary-700 dark:text-primary-300' : 'text-surface-700 dark:text-surface-300'}`}>
                      {item.query}
                    </p>
                    <p className="text-[10px] text-surface-400 mt-1.5 font-mono">
                      {new Date(item.timestamp).toLocaleString()}
                    </p>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); onDelete(item.id); }}
                    className="p-1 rounded hover:bg-red-100 dark:hover:bg-red-900/40 text-surface-400 hover:text-red-600 dark:hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all shrink-0"
                    title={isVietnamese ? 'Xóa phân tích' : 'Delete analysis'}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}

// ─── Main Workspace Tab ───────────────────────────────────────────────────────
export default function WorkspaceTab({
  papers = [],
  setPapers,
  selectedPapers = [],
  setSelectedPapers,
  workspacePapers,
  setWorkspacePapers,
  chatMessages,
  setChatMessages,
  activeCitation,
  setActiveCitation,
  darkMode,
}) {
  const { t, language } = useLanguage();
  const isVietnamese = language === 'vi';
  const [uploadQueue, setUploadQueue] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedPaperIds, setSelectedPaperIds] = useState([]);
  const [deletedPaperIds, setDeletedPaperIds] = useState(new Set());
  const [activeWorkspaceTab, setActiveWorkspaceTab] = useState('chat');
  const [isSourcesOpen, setIsSourcesOpen] = useState(true);
  const [isHarnessOpen, setIsHarnessOpen] = useState(false);
  
  // Resizable Sidebar States
  const [sidebarWidth, setSidebarWidth] = useState(360);
  const [isResizing, setIsResizing] = useState(false);
  const sidebarRef = React.useRef(null);

  const [verificationWidth, setVerificationWidth] = useState(380);
  const [isVerifResizing, setIsVerifResizing] = useState(false);
  const verifRef = React.useRef(null);

  React.useEffect(() => {
    if (!isResizing) return;
    const handleMouseMove = (e) => {
      if (sidebarRef.current) {
        const newWidth = e.clientX - sidebarRef.current.getBoundingClientRect().left;
        if (newWidth >= 260 && newWidth <= 800) {
          setSidebarWidth(newWidth);
        }
      }
    };
    const handleMouseUp = () => {
      setIsResizing(false);
      document.body.style.cursor = 'default';
      document.body.style.userSelect = 'auto';
    };
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'default';
      document.body.style.userSelect = 'auto';
    };
  }, [isResizing]);

  React.useEffect(() => {
    if (!isVerifResizing) return;
    const handleMouseMove = (e) => {
      if (verifRef.current) {
        const rightEdge = verifRef.current.getBoundingClientRect().right;
        const newWidth = rightEdge - e.clientX;
        if (newWidth >= 300 && newWidth <= 1200) {
          setVerificationWidth(newWidth);
        }
      }
    };
    const handleMouseUp = () => {
      setIsVerifResizing(false);
      document.body.style.cursor = 'default';
      document.body.style.userSelect = 'auto';
    };
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'default';
      document.body.style.userSelect = 'auto';
    };
  }, [isVerifResizing]);

  const { activeProject } = useProject();
  const currentProjectId = activeProject?.id;

  const [analysisHistory, setAnalysisHistory] = useState([]);
  const [activeAnalysisSessionId, setActiveAnalysisSessionId] = useState(null);

  // Load history on project change
  React.useEffect(() => {
    if (!currentProjectId) {
      setAnalysisHistory([]);
      return;
    }
    try {
      const saved = localStorage.getItem(`analysisHistory_${currentProjectId}`);
      setAnalysisHistory(saved ? JSON.parse(saved) : []);
    } catch (e) {
      setAnalysisHistory([]);
    }
  }, [currentProjectId]);

  // Save history on change
  React.useEffect(() => {
    if (!currentProjectId) return;
    const key = `analysisHistory_${currentProjectId}`;
    
    const saveToLocal = (historyObj) => {
      try {
        localStorage.setItem(key, JSON.stringify(historyObj));
        return true;
      } catch (e) {
        return false;
      }
    };

    // Attempt 1: Save full history
    if (saveToLocal(analysisHistory)) return;

    console.warn("Storage quota exceeded. Slimming down older sessions...");
    // Attempt 2: Strip large base64 figures from older sessions
    const slimmedOlder = analysisHistory.map(session => {
      if (session.id === activeAnalysisSessionId) return session;
      return {
        ...session,
        messages: session.messages.map(msg => ({
          ...msg,
          figures: [],
          block_outputs: msg.block_outputs ? msg.block_outputs.map(bo => ({ ...bo, figures: [] })) : []
        }))
      };
    });
    
    if (saveToLocal(slimmedOlder)) return;

    console.warn("Storage quota still exceeded. Slimming down all sessions...");
    // Attempt 3: Strip figures from ALL sessions
    const strippedAll = analysisHistory.map(session => ({
      ...session,
      messages: session.messages.map(msg => ({
        ...msg,
        figures: [],
        block_outputs: msg.block_outputs ? msg.block_outputs.map(bo => ({ ...bo, figures: [] })) : []
      }))
    }));
    
    if (saveToLocal(strippedAll)) return;
    
    console.warn("Storage quota critical. Keeping only current active session.");
    // Attempt 4: Extreme fallback - keep only active session without figures
    saveToLocal(strippedAll.filter(s => s.id === activeAnalysisSessionId));
  }, [analysisHistory, currentProjectId, activeAnalysisSessionId]);

  React.useEffect(() => {
    let cancelled = false;
    const restoreUploads = async () => {
      if (!currentProjectId) {
        setWorkspacePapers?.([]);
        return;
      }
      try {
        const response = await safeFetch(`/projects/${currentProjectId}/papers?include_unverified=true`);
        if (!response.ok) return;
        const persisted = persistedDirectUploadSources(await response.json());
        if (cancelled) return;
        setWorkspacePapers?.(persisted);
      } catch (error) {
        console.error('Unable to restore uploaded workspace papers:', error);
      }
    };
    restoreUploads();
    return () => { cancelled = true; };
  }, [currentProjectId, setWorkspacePapers]);

  // Lọc và gộp danh sách nguồn tài liệu
  const allSources = React.useMemo(() => {
    const keepPapers = [...(papers || []), ...(selectedPapers || [])].filter((p) => {
      if (deletedPaperIds.has(String(p.id))) return false;
      const d = p.screening_decision || p.screeningDecision;
      return d === 'keep' || d === 'maybe' || (selectedPapers || []).some((sp) => String(sp.id) === String(p.id));
    });
    const keepIds = new Set(keepPapers.map((p) => String(p.id)));
    const wsPapers = (workspacePapers || []).filter((w) => !deletedPaperIds.has(String(w.id)) && (!keepIds.has(String(w.id)) || w.source === 'direct_upload'));

    const merged = new Map();
    keepPapers.forEach((p) => {
      const wp = (workspacePapers || []).find((w) => String(w.id) === String(p.id));
      merged.set(String(p.id), { ...p, ...(wp || {}), source: p.source || 'library' });
    });
    wsPapers.forEach((w) => {
      if (!merged.has(String(w.id))) merged.set(String(w.id), w);
    });

    return Array.from(merged.values());
  }, [papers, selectedPapers, workspacePapers, deletedPaperIds]);

  React.useEffect(() => {
    setSelectedPaperIds((current) => {
      if (!current || current.length === 0) {
        return allSources.map((p) => p.id);
      }
      return reconcileSelectedPaperIds(current, allSources, false);
    });
  }, [allSources]);

  const scopedPapers = React.useMemo(() => {
    if (!selectedPaperIds || selectedPaperIds.length === 0) {
      return allSources;
    }
    const selected = selectedPapersFromIds(allSources, selectedPaperIds);
    return selected.length > 0 ? selected : allSources;
  }, [allSources, selectedPaperIds]);

  // Upload Logic
  const uploadFiles = async (files) => {
    if (isUploading) return;
    setIsUploading(true);
    const items = files.map((f) => ({ filename: f.name, status: 'pending', file: f }));
    setUploadQueue(items);

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.file.size > MAX_FILE_SIZE_BYTES) {
        items[i] = { ...item, status: 'error', error: t('workspace.file_too_large') };
        setUploadQueue([...items]);
        continue;
      }
      const formData = new FormData();
      formData.append('file', item.file);
      formData.append('title', item.filename.replace(/\.pdf$/i, ''));
      if (currentProjectId) {
        formData.append('project_id', currentProjectId);
      }
      try {
        const res = await safeFetch('/workspace/direct-upload', { method: 'POST', body: formData });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || t('workspace.error'));
        items[i] = { ...item, status: 'done' };
        setUploadQueue([...items]);
        setWorkspacePapers((prev) => [
          {
            id: data.paper_id,
            title: data.title,
            filename: data.filename,
            uploadFilename: data.filename,
            totalPages: data.total_pages,
            totalChunks: data.total_chunks,
            source: 'direct_upload',
            screening_decision: 'keep',
          },
          ...(prev || []).filter((p) => String(p.id) !== String(data.paper_id)),
        ]);
        setSelectedPaperIds((prev) => (prev || []).includes(data.paper_id) ? prev : [...(prev || []), data.paper_id]);
      } catch (err) {
        items[i] = { ...item, status: 'error', error: err.message };
        setUploadQueue([...items]);
      }
    }
    setIsUploading(false);
    setTimeout(() => setUploadQueue([]), 3000); // Clear after 3s
  };

  const removeSource = async (id) => {
    const strId = String(id);
    setDeletedPaperIds((prev) => new Set([...prev, strId]));

    try {
      const wsKey = currentProjectId ? `litreview_workspace_papers_${currentProjectId}` : 'litreview_workspace_papers';
      const papersKey = currentProjectId ? `litreview_papers_${currentProjectId}` : 'litreview_papers';
      const savedWs = JSON.parse(localStorage.getItem(wsKey) || '[]');
      const filteredWs = savedWs.filter((p) => String(p.id) !== strId);
      localStorage.setItem(wsKey, JSON.stringify(filteredWs));

      const savedPapers = JSON.parse(localStorage.getItem(papersKey) || '[]');
      const filteredPapers = savedPapers.filter((p) => String(p.id) !== strId);
      localStorage.setItem(papersKey, JSON.stringify(filteredPapers));
    } catch (e) {
      console.error('LocalStorage sync error:', e);
    }

    try {
      await safeFetch(`/papers/${id}`, { method: 'DELETE' });
    } catch (err) {
      console.error('Failed to delete paper from backend:', err);
    }

    setWorkspacePapers((prev) => (prev || []).filter((p) => String(p.id) !== strId));
    if (setPapers) setPapers((prev) => (prev || []).filter((p) => String(p.id) !== strId));
    if (setSelectedPapers) setSelectedPapers((prev) => (prev || []).filter((p) => String(p.id) !== strId));
    setSelectedPaperIds((prev) => (prev || []).filter((paperId) => String(paperId) !== strId));
  };

  const handleRemoveSource = removeSource;

  const togglePaperSelection = (id) => {
    setSelectedPaperIds((prev) => {
      const current = prev || [];
      return current.includes(id)
        ? current.filter((item) => item !== id)
        : [...current, id];
    });
  };

  const handleSelectAll = () => {
    if (selectedPaperIds.length === allSources.length) {
      setSelectedPaperIds([]);
    } else {
      setSelectedPaperIds(allSources.map(p => p.id));
    }
  };

  const handleSendToChat = async (questionText) => {
    setActiveWorkspaceTab('chat');
    if (!questionText) return;
    const userMsg = { sender: 'user', text: questionText };
    setChatMessages((prev) => [...prev, userMsg]);
    
    try {
      const paperIds = scopedPapers.map((p) => p.id);
      const response = await safeFetch('/workspace/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: questionText, paper_ids: paperIds }),
      });
      if (response.ok) {
        const data = await response.json();
        setChatMessages((prev) => [
          ...prev,
          {
            sender: 'ai',
            text: data.reply || data.text,
            citations: data.citations || [],
          },
        ]);
      }
    } catch (err) {
      console.error('Failed to trigger chat response from synthesis prompt:', err);
    }
  };  return (
    <div className="flex flex-col gap-4 h-screen p-4 overflow-hidden font-sans text-surface-900 dark:text-surface-100">
      <div className="flex flex-col lg:flex-row gap-4 flex-1 min-h-0">
      
      {/* ── LEFT: Sources Panel ── */}
      <div 
        ref={sidebarRef}
        className={`relative shrink-0 ${isSourcesOpen ? 'w-full lg:w-[var(--sidebar-width,260px)]' : 'w-full lg:w-[64px]'} ${isResizing ? 'transition-none' : 'transition-all duration-300 ease-in-out'}`}
      >
        <div className="card h-full flex flex-col overflow-hidden">
        
        {isSourcesOpen ? (
          <>
            {activeWorkspaceTab === 'analyze' ? (
              <AnalysisHistorySidebar 
                history={analysisHistory}
                activeId={activeAnalysisSessionId}
                onSelect={(id) => setActiveAnalysisSessionId(id)}
                onNew={() => setActiveAnalysisSessionId(null)}
                onDelete={(id) => setAnalysisHistory(prev => prev.filter(h => h.id !== id))}
                onToggleCollapse={() => setIsSourcesOpen(false)}
                darkMode={darkMode}
              />
            ) : (
              <>
                {/* FULL HEADER */}
                <div className="flex items-center justify-between px-4 h-14 border-b border-surface-100 dark:border-surface-800 shrink-0">
                  <div className="flex items-center gap-2">
                    <BookOpen className="w-4 h-4 text-primary-600 dark:text-primary-400" />
                    <h3 className="section-label">
                      {t('workspace.source_title')}
                    </h3>
                  </div>
                  <button 
                    onClick={() => setIsSourcesOpen(false)}
                    className="p-1.5 rounded-lg text-surface-400 hover:text-surface-600 dark:hover:text-surface-200 hover:bg-surface-100 dark:hover:bg-surface-800 transition-colors"
                    title={isVietnamese ? 'Thu gọn' : 'Collapse sources'}
                  >
                    <PanelLeftClose className="w-4 h-4" />
                  </button>
                </div>

                {/* FULL CONTENT */}
                <div className="flex-1 overflow-y-auto px-3 space-y-4 pb-4 pt-3">
                  <div>
                    <AddSourceButton onFiles={uploadFiles} isUploading={isUploading} darkMode={darkMode} />
                  </div>
                  
                  {uploadQueue.length > 0 && (
                    <div className="space-y-1.5 shrink-0">
                      {uploadQueue.map((item, i) => (
                        <UploadQueueItem 
                          key={i} 
                          item={item} 
                          onDismiss={() => setUploadQueue(prev => prev.filter((_, idx) => idx !== i))}
                          darkMode={darkMode} 
                        />
                      ))}
                    </div>
                  )}

                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between px-2 py-1.5 bg-surface-50 dark:bg-surface-800/50 rounded-lg border border-surface-200 dark:border-surface-700">
                      <span className="text-[11px] font-semibold text-surface-500">
                        {scopedPapers.length}/{allSources.length} {t('workspace.using')}
                      </span>
                      <button 
                        type="button"
                        onClick={handleSelectAll}
                        className="flex items-center gap-1.5 text-[11px] font-medium text-surface-400 hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
                      >
                        <span>{t('workspace.select_all')}</span>
                        <div className={`w-3.5 h-3.5 rounded border flex items-center justify-center transition-all ${
                          selectedPaperIds.length === allSources.length && allSources.length > 0
                            ? 'bg-primary-600 text-white border-primary-600'
                            : 'border-surface-300 dark:border-surface-600'
                        }`}>
                          {selectedPaperIds.length === allSources.length && allSources.length > 0 && <Check className="w-2.5 h-2.5 stroke-[3]" />}
                        </div>
                      </button>
                    </div>
                    {allSources.length === 0 ? (
                      <p className="text-surface-400 text-[13px] text-center italic mt-6 px-4">
                        {t('workspace.no_sources')}
                      </p>
                    ) : (
                      allSources.map((paper) => (
                        <SourceCard
                          key={paper.id}
                          paper={paper}
                          isChecked={selectedPaperIds.includes(paper.id)}
                          onToggle={togglePaperSelection}
                          onRemove={handleRemoveSource}
                          darkMode={darkMode}
                        />
                      ))
                    )}
                  </div>
                </div>
              </>
            )}
          </>

        ) : (
          <div className="flex flex-col items-center py-4 h-full">
            <button 
              onClick={() => setIsSourcesOpen(true)}
              className="p-1.5 rounded-lg text-surface-400 hover:text-surface-600 dark:hover:text-surface-200 hover:bg-surface-100 dark:hover:bg-surface-800 transition-colors mb-6"
              title={isVietnamese ? 'Mở rộng' : 'Expand sources'}
            >
              <PanelLeft className="w-4 h-4" />
            </button>
            <div className="flex-1 overflow-y-auto custom-scrollbar flex flex-col items-center gap-2">
              {activeWorkspaceTab === 'analyze' ? (
                <div 
                  className="w-10 h-10 rounded-xl bg-primary-50 dark:bg-primary-900/30 border border-primary-200 dark:border-primary-800 flex flex-col items-center justify-center shrink-0 cursor-pointer hover:bg-primary-100 dark:hover:bg-primary-900/50 transition-colors"
                  title={isVietnamese ? 'Mở Lịch sử phân tích' : 'Open Analysis History'}
                  onClick={() => setIsSourcesOpen(true)}
                >
                  <Clock className="w-5 h-5 text-primary-500" />
                </div>
              ) : (
                allSources.map(paper => (
                  <div 
                    key={paper.id}
                    className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-[10px] shrink-0 border transition-colors cursor-pointer ${
                      selectedPaperIds.includes(paper.id)
                        ? 'bg-primary-50 border-primary-200 text-primary-700 dark:bg-primary-900/30 dark:border-primary-800 dark:text-primary-300'
                        : 'bg-surface-50 border-surface-200 text-surface-400 dark:bg-surface-800 dark:border-surface-700'
                    }`}
                    title={paper.title || paper.filename}
                    onClick={() => setIsSourcesOpen(true)}
                  >
                    PDF
                  </div>
                ))
              )}
            </div>
          </div>
        )}
        </div>

        {/* Resizer Handle */}
        {isSourcesOpen && (
          <div 
             className="hidden lg:flex absolute -right-2 top-0 bottom-0 w-4 cursor-col-resize z-10 items-center justify-center group"
             onMouseDown={(e) => { e.preventDefault(); setIsResizing(true); }}
          >
             <div className={`w-0.5 h-12 rounded-full opacity-0 group-hover:opacity-100 transition-opacity bg-surface-300 dark:bg-surface-600 ${isResizing ? 'opacity-100 bg-primary-500' : ''}`} />
          </div>
        )}
      </div>

      {/* ── RIGHT: Active Workspace Panel ── */}
      <div className="flex-1 flex gap-4 h-full min-h-0 overflow-hidden relative">
        {/* Main Content Area (Chat/Synthesis/Data) */}
        <div className="card flex-1 flex flex-col overflow-hidden">
            {/* ── Workspace Header ── */}
            <div className="flex items-center justify-between px-5 h-14 border-b border-surface-100 dark:border-surface-800 shrink-0 gap-3">
              
              {/* Left: Brand / Title */}
              <div className="flex items-center gap-2.5 shrink-0">
                <div className="w-8 h-8 rounded-xl overflow-hidden shrink-0 shadow-xs border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 flex items-center justify-center p-0.5">
                  <img src="/AI.png" alt="AI Assistant" className="w-full h-full object-cover rounded-[10px]" />
                </div>
                <div className="hidden sm:block">
                  <span className="font-display font-semibold text-xs text-surface-900 dark:text-white block leading-none">
                    {t('workspace.ai_assistant')}
                  </span>
                  <span className="section-label mt-0.5 block">
                    Workspace Mode
                  </span>
                </div>
              </div>

              {/* Center / Right: The 3 Main Workspace Navigation Tabs */}
              <div className="flex items-center gap-2">
                <div id="tour-workspace-tabs" className="flex items-center bg-surface-100 dark:bg-surface-800 p-1 rounded-xl border border-surface-200 dark:border-surface-700">
                  {[
                    { id: 'chat', label: t('workspace.tab_chat'), Icon: MessageSquare },
                    { id: 'synthesis', label: t('workspace.tab_synthesis'), Icon: FileText },
                    { id: 'analyze', label: t('workspace.tab_analyze'), Icon: BarChart2 },
                  ].map(({ id, label, Icon }) => {
                    const isActive = activeWorkspaceTab === id;
                    return (
                      <button
                        key={id}
                        type="button"
                        onClick={() => setActiveWorkspaceTab(id)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all select-none cursor-pointer ${
                          isActive
                            ? 'bg-white dark:bg-surface-700 text-primary-600 dark:text-primary-400 shadow-xs'
                            : 'text-surface-500 hover:text-surface-800 dark:hover:text-surface-200'
                        }`}
                      >
                        <Icon className="w-3.5 h-3.5" />
                        <span className="hidden lg:inline">{label}</span>
                      </button>
                    );
                  })}
                </div>

                {activeWorkspaceTab === 'chat' && chatMessages && chatMessages.length > 1 && (
                  <button
                    onClick={() => {
                      if (window.confirm(t('workspace.clear_chat_confirm'))) {
                        setChatMessages([
                          {
                            sender: 'ai',
                            isWelcome: true,
                            text: ""
                          }
                        ]);
                      }
                    }}
                    className="p-2 rounded-xl btn-ghost text-surface-400 hover:text-danger hover:bg-danger-light dark:hover:bg-danger-dark"
                    title={t('workspace.clear_chat')}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>
            
            <div className="flex-1 min-h-0 flex flex-col relative z-0">
              {activeWorkspaceTab === 'chat' && (
                <ChatPanel
                  workspacePapers={scopedPapers}
                  selectedSourceIds={selectedPaperIds}
                  chatMessages={chatMessages}
                  setChatMessages={setChatMessages}
                  activeCitation={activeCitation}
                  setActiveCitation={setActiveCitation}
                  darkMode={darkMode}
                />
              )}

              {activeWorkspaceTab === 'synthesis' && (
                <SynthesisPanel
                  workspacePapers={scopedPapers}
                  setActiveCitation={setActiveCitation}
                  darkMode={darkMode}
                  onSendToChat={handleSendToChat}
                />
              )}
              {activeWorkspaceTab === 'analyze' && (
                <DataAnalysisPanel 
                  workspacePapers={scopedPapers}
                  darkMode={darkMode}
                  onSendToChat={handleSendToChat}
                  activeProject={activeProject}
                  analysisHistory={analysisHistory}
                  setAnalysisHistory={setAnalysisHistory}
                  activeSessionId={activeAnalysisSessionId}
                  setActiveSessionId={setActiveAnalysisSessionId}
                />
              )}
            </div>
          </div>

        {/* Citation Verification Panel — slide-in overlay từ phải khi user click citation */}
        {activeCitation && (
          <div 
            ref={verifRef}
            className="shrink-0 h-full overflow-visible card border-primary-200 dark:border-primary-800 animate-slide-up relative flex"
            style={{ width: verificationWidth }}
          >
            {/* Left handle for verification panel */}
            <div 
              className="absolute -left-2 top-0 bottom-0 w-4 cursor-col-resize z-20 flex items-center justify-center group"
              onMouseDown={(e) => { e.preventDefault(); setIsVerifResizing(true); }}
            >
              <div className={`w-0.5 h-12 rounded-full opacity-0 group-hover:opacity-100 transition-opacity bg-surface-300 dark:bg-surface-600 ${isVerifResizing ? 'opacity-100 bg-primary-500' : ''}`} />
            </div>
            
            <div className="flex-1 w-full h-full overflow-hidden">
              <VerificationPanel
                activeCitation={activeCitation}
                darkMode={darkMode}
                onClose={() => setActiveCitation(null)}
              />
            </div>
          </div>
        )}
      </div>
      </div>

      {/* RAG Evaluation Benchmark Harness Modal */}
      <RAGEvalHarnessModal
        isOpen={isHarnessOpen}
        onClose={() => setIsHarnessOpen(false)}
        workspacePapers={allSources}
        darkMode={darkMode}
      />

      {/* Disclaimer Text */}
      <div className="shrink-0 text-center">
        <p className="text-[11px] text-surface-400">
          {t('workspace.disclaimer')}
        </p>
      </div>
    </div>
  );
}
