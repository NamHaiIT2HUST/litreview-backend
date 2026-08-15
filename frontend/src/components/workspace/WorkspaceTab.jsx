import React, { useCallback, useRef, useState } from 'react';
import ChatPanel from './ChatPanel';
import VerificationPanel from './VerificationPanel';
import SynthesisPanel from './SynthesisPanel';
import { persistedDirectUploadSources } from '../../utils/workspaceSources';
import {
  Bot,
  UploadCloud,
  FileText,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Trash2,
  Plus,
  Info,
  BookOpen,
  Layers,
  Hash,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

const API_BASE = 'http://localhost:8000/api/v1';
const MAX_FILE_SIZE_MB = 20;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

// ─── Source Card ──────────────────────────────────────────────────────────────
function SourceCard({ paper, isSelected, onSelect, onRemove, darkMode }) {
  const isDirectUpload = paper.source === 'direct_upload';
  return (
    <div
      onClick={() => onSelect(paper.id)}
      className={`group relative p-3 rounded-2xl border cursor-pointer transition-all select-none ${
        isSelected
          ? 'border-blue-500 ring-2 ring-blue-200 dark:ring-blue-800 bg-blue-50 dark:bg-blue-950/40'
          : darkMode
          ? 'bg-slate-800/70 border-slate-700 hover:border-slate-500'
          : 'bg-white border-slate-200 hover:border-slate-300 hover:shadow-md'
      }`}
    >
      <button
        onClick={(e) => { e.stopPropagation(); onRemove(paper.id); }}
        className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 p-1 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950 transition-all"
      >
        <Trash2 className="w-3.5 h-3.5" />
      </button>

      <div className="flex items-start gap-3">
        <div className={`shrink-0 w-8 h-8 rounded-xl flex items-center justify-center ${
          isDirectUpload
            ? 'bg-purple-100 dark:bg-purple-950 text-purple-600 dark:text-purple-400'
            : 'bg-blue-100 dark:bg-blue-950 text-blue-600 dark:text-blue-400'
        }`}>
          <FileText className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <p className={`text-xs font-bold leading-snug truncate ${darkMode ? 'text-slate-100' : 'text-slate-900'}`}>
            {paper.title}
          </p>
          <div className="flex items-center gap-2 mt-1">
            {paper.totalPages && (
              <span className={`text-[9px] font-semibold ${darkMode ? 'text-slate-500' : 'text-slate-400'}`}>
                {paper.totalPages} trang
              </span>
            )}
            {isDirectUpload ? (
              <span className="px-1.5 py-0.5 text-[8px] font-bold rounded-full bg-purple-100 text-purple-600 dark:bg-purple-950 dark:text-purple-400">
                Direct
              </span>
            ) : (
              <span className="px-1.5 py-0.5 text-[8px] font-bold rounded-full bg-blue-100 text-blue-600 dark:bg-blue-950 dark:text-blue-400">
                Library
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Drop Zone ────────────────────────────────────────────────────────────────
function DropZone({ onFiles, isUploading, darkMode }) {
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
      className={`relative flex flex-col items-center justify-center gap-2 py-6 px-4 rounded-3xl border-2 border-dashed cursor-pointer transition-all ${
        isDragging
          ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/30'
          : isUploading
          ? 'border-blue-300 bg-blue-50/50 dark:bg-blue-950/20 cursor-wait'
          : darkMode
          ? 'border-slate-700 bg-slate-800/40 hover:border-blue-500'
          : 'border-slate-300 bg-slate-50 hover:border-blue-400'
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
        <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />
      ) : (
        <UploadCloud className={`w-6 h-6 ${isDragging ? 'text-blue-600' : 'text-blue-400'}`} />
      )}
      <p className={`text-xs text-center font-bold ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
        {isUploading ? 'Đang xử lý...' : isDragging ? 'Thả PDF vào đây' : 'Tải lên PDF (+)'}
      </p>
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
  setSelectedPaperIds,
  workspacePapers,
  setWorkspacePapers,
  chatMessages,
  setChatMessages,
  activeCitation,
  setActiveCitation,
  darkMode,
}) {
  const [uploadQueue, setUploadQueue] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedSourceIds, setSelectedSourceIds] = useState([]);
  const [activeWorkspaceTab, setActiveWorkspaceTab] = useState('chat');
  const [isRestoring, setIsRestoring] = useState(false);

  // ── Restore persisted uploaded papers on mount ──
  React.useEffect(() => {
    let cancelled = false;
    const restoreUploads = async () => {
      setIsRestoring(true);
      try {
        const response = await fetch(`${API_BASE}/projects/00000000-0000-0000-0000-000000000001/papers?include_unverified=true`);
        if (!response.ok) return;
        const persisted = persistedDirectUploadSources(await response.json());
        if (cancelled) return;
        setWorkspacePapers((current) => {
          return (current || []).map((paper) => {
            const match = persisted.find(
              (p) => p.id === paper.id || (p.title === paper.title && p.source === paper.source)
            );
            if (match) {
              return {
                ...paper,
                id: match.id,
                totalPages: match.totalPages || paper.totalPages,
                totalChunks: match.totalChunks || paper.totalChunks,
              };
            }
            return paper;
          });
        });
      } catch (error) {
        console.error('Unable to restore uploaded workspace papers:', error);
      } finally {
        if (!cancelled) setIsRestoring(false);
      }
    };
    restoreUploads();
    return () => {
      cancelled = true;
    };
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

  // Upload Logic
  const uploadFiles = async (files) => {
    if (isUploading) return;
    setIsUploading(true);
    const items = files.map((f) => ({ filename: f.name, status: 'pending', file: f }));
    setUploadQueue(items);

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.file.size > MAX_FILE_SIZE_BYTES) {
        items[i] = { ...item, status: 'error', error: 'File quá lớn' };
        setUploadQueue([...items]);
        continue;
      }
      const formData = new FormData();
      formData.append('file', item.file);
      formData.append('title', item.filename.replace(/\.pdf$/i, ''));
      try {
        const res = await fetch(`${API_BASE}/workspace/direct-upload`, { method: 'POST', body: formData });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Lỗi');
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
      } catch (err) {
        items[i] = { ...item, status: 'error', error: err.message };
        setUploadQueue([...items]);
      }
    }
    setIsUploading(false);
    setTimeout(() => setUploadQueue([]), 3000); // Clear after 3s
  };

  const removeSource = (id) => {
    setWorkspacePapers((prev) => prev.filter((p) => p.id !== id));
    if (setPapers) setPapers((prev) => prev.filter((p) => p.id !== id));
    if (setSelectedPaperIds) setSelectedPaperIds((prev) => prev.filter((pId) => pId !== id));
    setSelectedSourceIds((prev) => prev.filter((x) => x !== id));
  };

  return (
    <div className={`grid grid-cols-1 lg:grid-cols-12 gap-5 h-[calc(100vh-140px)] ${darkMode ? 'text-slate-100' : 'text-slate-900'}`}>
      
      {/* ── LEFT: Sources Panel ── */}
      <div className={`lg:col-span-3 flex flex-col gap-4 rounded-3xl border p-4 ${
        darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
      }`}>
        <div className="flex items-center justify-between">
          <h3 className="font-extrabold text-lg">Nguồn tài liệu</h3>
          <span className="text-xs font-bold px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300 rounded-lg">
            {allSources.length} files
          </span>
        </div>

        <DropZone onFiles={uploadFiles} isUploading={isUploading} darkMode={darkMode} />
        
        {uploadQueue.length > 0 && (
          <div className="space-y-1.5 shrink-0">
            {uploadQueue.map((item, i) => (
              <UploadQueueItem key={i} item={item} darkMode={darkMode} />
            ))}
          </div>
        )}

        <div className="flex-1 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
          {allSources.map((paper) => (
            <SourceCard
              key={paper.id}
              paper={paper}
              isSelected={selectedSourceIds.includes(paper.id)}
              onSelect={(id) => setSelectedSourceIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])}
              onRemove={removeSource}
              darkMode={darkMode}
            />
          ))}
          {allSources.length === 0 && !isUploading && (
            <div className={`text-center p-6 rounded-2xl border border-dashed ${darkMode ? 'border-slate-700 text-slate-500' : 'border-slate-300 text-slate-400'}`}>
              <BookOpen className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm font-semibold">Chưa có nguồn nào</p>
              <p className="text-xs mt-1 opacity-75">Tải PDF lên hoặc chọn từ thư viện</p>
            </div>
          )}
        </div>
      </div>

      {/* ── RIGHT: Chat & Synthesis Panel ── */}
      <div className="lg:col-span-9 flex flex-col gap-5 h-full min-h-0 overflow-hidden">
        
        {/* Tab bar */}
        <div className={`flex items-center justify-between px-4 py-3 rounded-3xl border shrink-0 ${
          darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
        }`}>
          <div className={`flex gap-1 p-1 rounded-xl ${darkMode ? 'bg-slate-800' : 'bg-slate-100'}`}>
            {[
              ['chat', 'Chat', Bot, 'Chat với tài liệu'],
              ['synthesis', 'Synthesis', Sparkles, 'Tổng hợp nghiên cứu'],
            ].map(([id, label, Icon, title]) => (
              <button
                key={id}
                type="button"
                title={title}
                onClick={() => setActiveWorkspaceTab(id)}
                className={`px-4 py-2 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all ${
                  activeWorkspaceTab === id
                    ? 'bg-white text-blue-600 shadow-sm dark:bg-slate-700 dark:text-blue-400'
                    : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-3">
             {activeCitation && activeWorkspaceTab === 'chat' && (
                <span className="text-xs font-bold bg-blue-100 text-blue-600 px-3 py-1 rounded-lg">
                  Đang mở Xác minh
                </span>
             )}
          </div>
        </div>

        {/* Content Area */}
        {activeWorkspaceTab === 'synthesis' ? (
          <div className="flex-1 overflow-y-auto min-h-0 pb-4 custom-scrollbar">
            <SynthesisPanel
              workspacePapers={workspacePapers}
              setActiveCitation={setActiveCitation}
              darkMode={darkMode}
            />
          </div>
        ) : (
          /* Chat / Verification Split */
          <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-5 min-h-0 pb-4">
            <div className={`${activeCitation ? 'lg:col-span-7' : 'lg:col-span-12'} h-full rounded-3xl border flex flex-col overflow-hidden ${
              darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
            }`}>
              <ChatPanel
                workspacePapers={workspacePapers}
                selectedSourceIds={selectedSourceIds}
                chatMessages={chatMessages}
                setChatMessages={setChatMessages}
                activeCitation={activeCitation}
                setActiveCitation={setActiveCitation}
                darkMode={darkMode}
              />
            </div>

            {activeCitation && (
              <div className="lg:col-span-5 h-full overflow-y-auto custom-scrollbar">
                <VerificationPanel activeCitation={activeCitation} darkMode={darkMode} />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
