import React, { useCallback, useRef, useState } from 'react';
import ChatPanel from './ChatPanel';
import VerificationPanel from './VerificationPanel';
import { persistedDirectUploadSources } from '../../utils/workspaceSources';
import SynthesisPanel from './SynthesisPanel';
import { reconcileSelectedPaperIds, selectedPapersFromIds } from '../../utils/workspaceScope';
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
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/v1';
const MAX_FILE_SIZE_MB = 20;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

// ─── Source Card ──────────────────────────────────────────────────────────────
function SourceCard({ paper, isChecked, onToggle, onRemove, darkMode }) {
  const { t } = useLanguage();
  return (
    <div
      onClick={() => onToggle(paper.id)}
      className={`group relative py-2 px-3 flex items-center justify-between rounded-xl cursor-pointer transition-all select-none ${
        darkMode ? 'hover:bg-slate-800/60' : 'hover:bg-slate-100'
      }`}
    >
      <div className="flex items-center gap-3 overflow-hidden">
        {/* PDF Badge */}
        <div className={`shrink-0 w-6 h-6 rounded flex items-center justify-center font-extrabold text-[8px] ${
          darkMode ? 'bg-red-950/40 text-red-400 border border-red-900/50' : 'bg-red-50 text-red-600 border border-red-200'
        }`}>
          PDF
        </div>

        {/* Content */}
        <p className={`text-[13px] font-medium leading-tight truncate pr-4 ${
          darkMode ? 'text-slate-300' : 'text-slate-700'
        }`}>
          {paper.title || paper.filename}
        </p>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <button
          onClick={(e) => { e.stopPropagation(); onRemove(paper.id); }}
          className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/50 transition-all"
          title={t('workspace.delete_doc')}
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>

        {/* Checkbox */}
        <div
          className={`shrink-0 w-4 h-4 rounded-[4px] flex items-center justify-center transition-all ${
            isChecked
              ? (darkMode ? 'bg-slate-300 text-slate-900' : 'bg-slate-700 text-white')
              : (darkMode ? 'border border-slate-600 bg-transparent' : 'border border-slate-300 bg-transparent')
          }`}
        >
          {isChecked && <Check className="w-3 h-3 stroke-[3]" />}
        </div>
      </div>
    </div>
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
    <div
      onDrop={handleDrop}
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      onClick={() => !isUploading && inputRef.current?.click()}
      className={`relative w-full flex items-center justify-center gap-2 py-2.5 rounded-full border cursor-pointer transition-all ${
        isDragging
          ? 'border-blue-500 bg-blue-50'
          : isUploading
          ? 'border-blue-200 bg-blue-50/50 cursor-wait'
          : darkMode
          ? 'border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-200'
          : 'border-slate-300 bg-white hover:bg-slate-50 text-slate-700'
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
    </div>
  );
}

// ─── Upload Queue Item ────────────────────────────────────────────────────────
function UploadQueueItem({ item, darkMode }) {
  const statusIcon = {
    pending: <Loader2 className="w-3.5 h-3.5 text-blue-500 animate-spin" />,
    done: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />,
    error: <AlertCircle className="w-3.5 h-3.5 text-red-500" />,
  }[item.status];

  return (
    <div className={`flex items-center gap-2 p-2 rounded-xl text-xs ${darkMode ? 'bg-slate-800' : 'bg-slate-50'}`}>
      {statusIcon}
      <div className="flex-1 min-w-0 truncate font-semibold dark:text-slate-300 text-slate-700">
        {item.filename}
      </div>
    </div>
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
  const { t } = useLanguage();
  const [uploadQueue, setUploadQueue] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedPaperIds, setSelectedPaperIds] = useState([]);
  const [activeWorkspaceTab, setActiveWorkspaceTab] = useState('chat');
  const [isSourcesOpen, setIsSourcesOpen] = useState(true);
  
  // Resizable Sidebar States
  const [sidebarWidth, setSidebarWidth] = useState(360);
  const [isResizing, setIsResizing] = useState(false);
  const sidebarRef = React.useRef(null);

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
    let cancelled = false;
    const restoreUploads = async () => {
      try {
        const response = await fetch(`${API_BASE}/projects/00000000-0000-0000-0000-000000000001/papers?include_unverified=true`);
        if (!response.ok) return;
        const persisted = persistedDirectUploadSources(await response.json());
        if (cancelled) return;
        setWorkspacePapers((current) => {
          const merged = new Map(current.map((paper) => [paper.id, paper]));
          persisted.forEach((paper) => merged.set(paper.id, { ...paper, ...(merged.get(paper.id) || {}) }));
          return Array.from(merged.values());
        });
      } catch (error) {
        console.error('Unable to restore uploaded workspace papers:', error);
      }
    };
    restoreUploads();
    return () => { cancelled = true; };
  }, [setWorkspacePapers]);

  // Lọc và gộp danh sách nguồn tài liệu
  const allSources = React.useMemo(() => {
    const keepPapers = [...papers, ...selectedPapers].filter((p) => {
      const d = p.screening_decision || p.screeningDecision;
      return d === 'keep' || d === 'maybe' || selectedPapers.some((sp) => sp.id === p.id);
    });
    const keepIds = new Set(keepPapers.map((p) => p.id));
    const wsPapers = workspacePapers.filter((w) => !keepIds.has(w.id) || w.source === 'direct_upload');

    const merged = new Map();
    keepPapers.forEach((p) => {
      const wp = workspacePapers.find((w) => w.id === p.id);
      merged.set(p.id, { ...p, ...(wp || {}), source: p.source || 'library' });
    });
    wsPapers.forEach((w) => {
      if (!merged.has(w.id)) merged.set(w.id, w);
    });

    return Array.from(merged.values());
  }, [papers, selectedPapers, workspacePapers]);

  React.useEffect(() => {
    setSelectedPaperIds((current) => reconcileSelectedPaperIds(current, allSources));
  }, [allSources]);

  const scopedPapers = React.useMemo(
    () => selectedPapersFromIds(allSources, selectedPaperIds),
    [allSources, selectedPaperIds],
  );

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
      try {
        const res = await fetch(`${API_BASE}/workspace/direct-upload`, { method: 'POST', body: formData });
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
          ...prev.filter((p) => p.id !== data.paper_id),
        ]);
        setSelectedPaperIds((prev) => prev.includes(data.paper_id) ? prev : [...prev, data.paper_id]);
      } catch (err) {
        items[i] = { ...item, status: 'error', error: err.message };
        setUploadQueue([...items]);
      }
    }
    setIsUploading(false);
    setTimeout(() => setUploadQueue([]), 3000); // Clear after 3s
  };

  const removeSource = async (id) => {
    try {
      await fetch(`${API_BASE}/papers/${id}`, { method: 'DELETE' });
    } catch (err) {
      console.error('Failed to delete paper from backend:', err);
    }
    setWorkspacePapers((prev) => prev.filter((p) => p.id !== id));
    if (setPapers) setPapers((prev) => prev.filter((p) => p.id !== id));
    if (setSelectedPapers) setSelectedPapers((prev) => prev.filter((p) => p.id !== id));
    setSelectedPaperIds((prev) => prev.filter((paperId) => paperId !== id));
  };
  const handleSelectAll = () => {
    if (selectedPaperIds.length === allSources.length) {
      setSelectedPaperIds([]);
    } else {
      setSelectedPaperIds(allSources.map(p => p.id));
    }
  };

  return (
    <div 
      className={`flex flex-col gap-4 h-[calc(100vh-75px)] p-4 lg:p-5 ${darkMode ? 'text-slate-100' : 'text-slate-900'}`}
      style={{ '--sidebar-width': `${isSourcesOpen ? sidebarWidth : 72}px` }}
    >
      <div className="flex flex-col lg:flex-row gap-5 flex-1 min-h-0">
      
      {/* ── LEFT: Sources Panel ── */}
      <div 
        ref={sidebarRef}
        className={`relative shrink-0 ${isSourcesOpen ? 'w-full lg:w-[var(--sidebar-width)]' : 'w-full lg:w-[72px]'} ${isResizing ? 'transition-none' : 'transition-all duration-300'}`}
      >
        <div className={`h-full flex flex-col rounded-3xl border overflow-hidden shadow-sm ${darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'}`}>
        
        {isSourcesOpen ? (
          <>
            {/* FULL HEADER */}
            <div className={`flex items-center justify-between px-5 h-[56px] border-b shrink-0 ${darkMode ? 'border-slate-800' : 'border-slate-100'}`}>
              <h3 className={`font-bold text-[14px] ${darkMode ? 'text-slate-100' : 'text-slate-800'}`}>
                {t('workspace.source_title')}
              </h3>
              <button 
                onClick={() => setIsSourcesOpen(false)}
                className={`p-1 rounded-lg transition-colors ${darkMode ? 'hover:bg-slate-800 text-slate-400' : 'hover:bg-slate-100 text-slate-500'}`}
                title="Thu gọn nguồn tài liệu"
              >
                <PanelLeftClose className="w-[18px] h-[18px]" />
              </button>
            </div>

            {/* FULL CONTENT */}
            <div className="flex-1 overflow-y-auto px-3 space-y-4 custom-scrollbar pb-4 pt-4">
              <div className="px-1">
                <AddSourceButton onFiles={uploadFiles} isUploading={isUploading} darkMode={darkMode} />
              </div>
              
              {uploadQueue.length > 0 && (
                <div className="space-y-1.5 shrink-0 px-1">
                  {uploadQueue.map((item, i) => (
                    <UploadQueueItem key={i} item={item} darkMode={darkMode} />
                  ))}
                </div>
              )}

              <div className="flex flex-col gap-1">
                <div className="flex items-center justify-between px-3 py-2">
                  <span className={`text-[12px] font-medium ${darkMode ? 'text-slate-500' : 'text-slate-400'}`}>
                    {scopedPapers.length}/{allSources.length} {t('workspace.using')}
                  </span>
                  <div 
                    onClick={handleSelectAll}
                    className="flex items-center gap-2 cursor-pointer group"
                  >
                    <span className={`text-[12px] font-medium transition-colors ${darkMode ? 'text-slate-400 group-hover:text-slate-200' : 'text-slate-500 group-hover:text-slate-800'}`}>
                      Chọn tất cả
                    </span>
                    <div className={`shrink-0 w-4 h-4 rounded-[4px] flex items-center justify-center transition-all ${
                      selectedPaperIds.length === allSources.length && allSources.length > 0
                        ? (darkMode ? 'bg-slate-300 text-slate-900' : 'bg-slate-700 text-white')
                        : (darkMode ? 'border border-slate-600 bg-transparent group-hover:border-slate-500' : 'border border-slate-300 bg-transparent group-hover:border-slate-400')
                    }`}>
                      {selectedPaperIds.length === allSources.length && allSources.length > 0 && <Check className="w-3 h-3 stroke-[3]" />}
                    </div>
                  </div>
                </div>

                <div className="flex flex-col gap-0.5">
                {allSources.map((paper) => (
                  <SourceCard
                    key={paper.id}
                    paper={paper}
                    isChecked={selectedPaperIds.includes(paper.id)}
                    onToggle={(id) => setSelectedPaperIds((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id])}
                    onRemove={removeSource}
                    darkMode={darkMode}
                  />
                ))}
                {allSources.length === 0 && !isUploading && (
                  <div className={`text-center p-6 rounded-2xl border border-dashed ${darkMode ? 'border-slate-700 text-slate-500' : 'border-slate-300 text-slate-400'}`}>
                    <BookOpen className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm font-semibold">{t('workspace.no_source_title')}</p>
                    <p className="text-xs mt-1 opacity-75">{t('workspace.no_source_desc')}</p>
                  </div>
                )}
                </div>
              </div>
            </div>
          </>
        ) : (
          <>
            {/* MINI HEADER */}
            <div className={`flex items-center justify-center h-[56px] border-b shrink-0 ${darkMode ? 'border-slate-800' : 'border-slate-100'}`}>
              <button 
                onClick={() => setIsSourcesOpen(true)}
                className={`p-1 rounded-lg transition-colors ${darkMode ? 'hover:bg-slate-800 text-slate-400' : 'hover:bg-slate-100 text-slate-500'}`}
                title={t('workspace.expand_source')}
              >
                <PanelLeft className="w-[18px] h-[18px]" />
              </button>
            </div>

            {/* MINI CONTENT */}
            <div className="flex-1 overflow-y-auto py-4 flex flex-col items-center gap-5 custom-scrollbar">
              <button 
                onClick={() => !isUploading && document.querySelector('input[type="file"]')?.click()}
                className={`w-9 h-9 flex items-center justify-center rounded-xl transition-all ${
                  darkMode ? 'hover:bg-slate-800 text-slate-300' : 'hover:bg-slate-100 text-slate-600'
                }`}
                title="Tải lên tài liệu PDF"
              >
                {isUploading ? <Loader2 className="w-5 h-5 animate-spin text-blue-500" /> : <Plus className="w-6 h-6" />}
              </button>

              <div className="flex flex-col items-center gap-3">
                {allSources.map((paper) => (
                  <div 
                    key={paper.id} 
                    onClick={() => setIsSourcesOpen(true)}
                    className={`w-8 h-8 rounded-lg border-2 flex items-center justify-center font-extrabold text-[9px] cursor-pointer transition-all ${
                      darkMode 
                        ? 'border-red-900/50 bg-red-950/20 text-red-400 hover:border-red-800' 
                        : 'border-red-600 bg-white text-red-600 hover:shadow-md hover:border-red-500'
                    }`}
                    title={paper.title}
                  >
                    PDF
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
        </div>

        {/* Resizer Handle */}
        {isSourcesOpen && (
          <div 
             className="hidden lg:flex absolute -right-[12.5px] top-0 bottom-0 w-[25px] cursor-col-resize z-10 items-center justify-center group"
             onMouseDown={(e) => { e.preventDefault(); setIsResizing(true); }}
          >
             <div className={`w-1 h-12 rounded-full opacity-0 group-hover:opacity-100 transition-opacity ${darkMode ? 'bg-slate-600' : 'bg-slate-300'} ${isResizing ? 'opacity-100 bg-blue-500' : ''}`} />
          </div>
        )}
      </div>

      {/* ── RIGHT: Active Workspace Panel ── */}
      <div className={`flex-1 flex gap-5 h-full min-h-0 overflow-hidden`}>
        {/* Main Content Area (Chat/Synthesis) */}
        <div className={`flex-1 rounded-3xl border flex flex-col overflow-hidden shadow-sm transition-all ${
            darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
          }`}>
            <div className={`flex items-center justify-between px-5 h-[56px] border-b shrink-0 ${darkMode ? 'border-slate-800' : 'border-slate-100'}`}>
              <div className="flex items-center gap-3">
                <span className="text-[14px] font-bold text-slate-700 dark:text-slate-200 flex items-center gap-1.5">
                  <Sparkles className="w-4 h-4 text-blue-500" />
                  {t('workspace.ai_assistant')}
                </span>
                {activeWorkspaceTab === 'chat' && chatMessages && chatMessages.length > 1 && (
                  <button
                    onClick={() => {
                      if (window.confirm("Bạn có chắc chắn muốn xóa lịch sử trò chuyện này không?")) {
                        setChatMessages([
                          {
                            sender: 'ai',
                            text: `Chào mừng bạn đến với **LitReview Agent**! Hãy tìm kiếm trên Google Scholar, hệ thống sẽ tự động đối chiếu Scopus và chỉ giữ các bài đã xác minh.`
                          }
                        ]);
                      }
                    }}
                    className={`px-2.5 py-1 rounded-lg text-xs font-semibold border transition-colors flex items-center gap-1 ${
                      darkMode
                        ? 'border-slate-800 text-slate-400 hover:text-red-400 hover:bg-red-950/20'
                        : 'border-slate-200 text-slate-500 hover:text-red-600 hover:bg-red-50'
                    }`}
                  >
                    <Trash2 className="w-3 h-3" />
                    <span>Xóa lịch sử</span>
                  </button>
                )}
              </div>
              <div className={`flex rounded-xl p-1 shadow-inner ${darkMode ? 'bg-slate-950' : 'bg-slate-100'}`}>
                {[
                  ['chat', t('workspace.chat_title'), Bot, t('workspace.chat_desc')],
                  ['synthesis', t('workspace.synthesis_title'), Sparkles, t('workspace.synthesis_desc')],
                ].map(([id, label, Icon, title]) => (
                  <button key={id} type="button" title={title} onClick={() => setActiveWorkspaceTab(id)} className={`px-4 py-1.5 rounded-lg text-[13px] font-bold flex items-center gap-2 transition-all ${activeWorkspaceTab === id ? 'bg-white text-blue-600 shadow dark:bg-slate-800 dark:text-blue-400' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}>
                    <Icon className="w-4 h-4" />{label}
                  </button>
                ))}
              </div>
            </div>
            
            <div className="flex-1 min-h-0 flex flex-col">
              {activeWorkspaceTab === 'chat' ? (
                <ChatPanel
                  workspacePapers={scopedPapers}
                  chatMessages={chatMessages}
                  setChatMessages={setChatMessages}
                  activeCitation={activeCitation}
                  setActiveCitation={setActiveCitation}
                  darkMode={darkMode}
                />
              ) : (
                <SynthesisPanel
                  workspacePapers={scopedPapers}
                  setActiveCitation={setActiveCitation}
                  darkMode={darkMode}
                />
              )}
            </div>
          </div>

        {/* Verification Sidebar */}
        {activeCitation && (
          <div className="w-[380px] shrink-0 h-full overflow-hidden rounded-3xl border shadow-sm bg-white dark:bg-slate-900 dark:border-slate-800 border-slate-200 transition-all">
            <VerificationPanel
              activeCitation={activeCitation}
              darkMode={darkMode}
              onClose={() => setActiveCitation(null)}
            />
          </div>
        )}
      </div>
      </div>

      {/* Disclaimer Text (Centered at the very bottom of the entire layout) */}
      <div className="shrink-0 pb-1 text-center -mt-2">
        <p className={`text-[12px] font-medium ${darkMode ? 'text-slate-500' : 'text-slate-400'}`}>
          {t('workspace.disclaimer')}
        </p>
      </div>
    </div>
  );
}
