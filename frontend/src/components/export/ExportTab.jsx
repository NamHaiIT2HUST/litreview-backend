import React, { useState, useEffect, useMemo } from 'react';
import {
  generateClientBibTeX,
  generateClientCSV,
  generateClientMarkdown,
  generateClientJSON,
  downloadFile
} from '../../utils/exportUtils';
import { useLanguage } from '../../contexts/LanguageContext';
import { useProject } from '../../contexts/ProjectContext';
import { 
  Download, Copy, Check, FileText, Database, 
  Code, BookOpen, Layers, History, CheckCircle2
} from 'lucide-react';
import { API_BASE, safeFetch } from '../../utils/apiConfig';

const DEFAULT_PROJECT_ID = '00000000-0000-0000-0000-000000000001';

export default function ExportTab({ papers = [], selectedPapers = [], workspacePapers = [], darkMode = false }) {
  const { t } = useLanguage();
  const { activeProjectId } = useProject();
  const currentProjectId = activeProjectId || DEFAULT_PROJECT_ID;
  // Scope selection: 'keep' | 'all' | 'workspace'
  const [scope, setScope] = useState('keep');
  
  // Format selection: 'bibtex' | 'csv' | 'markdown' | 'json'
  const [activeFormat, setActiveFormat] = useState('bibtex');
  
  // Customization options
  const [includeAbstract, setIncludeAbstract] = useState(true);
  const [citationStyle, setCitationStyle] = useState('author_year_title');
  const [customDraft, setCustomDraft] = useState('');

  // Status & Feedback UI state
  const [isExporting, setIsExporting] = useState(false);
  const [copied, setCopied] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);
  
  // Export Session History Log
  const [exportHistory, setExportHistory] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('litreview_export_history')) || [];
    } catch {
      return [];
    }
  });

  // Active right column view: 'preview' | 'history'
  const [rightTab, setRightTab] = useState('preview');

  // Compute paper subset based on selected scope
  const targetPapers = useMemo(() => {
    if (scope === 'keep') {
      return selectedPapers.length > 0 ? selectedPapers : papers;
    }
    if (scope === 'workspace') {
      return workspacePapers.length > 0 ? workspacePapers : papers;
    }
    return papers;
  }, [papers, selectedPapers, workspacePapers, scope]);

  // Statistics
  const stats = useMemo(() => {
    const keepCount = selectedPapers.length;
    const scopusCount = papers.filter(p => (p.scopus_status || p.scopusStatus) === 'indexed').length;
    return {
      total: papers.length,
      keep: keepCount,
      scopus: scopusCount,
      activeScopeCount: targetPapers.length
    };
  }, [papers, selectedPapers, targetPapers]);

  // Sync history to localStorage
  useEffect(() => {
    localStorage.setItem('litreview_export_history', JSON.stringify(exportHistory));
  }, [exportHistory]);

  // Fetch export history from backend on mount and merge
  useEffect(() => {
    const fetchExportHistory = async () => {
      try {
        const response = await safeFetch(`${API_BASE}/projects/${currentProjectId}/export/history`);
        if (response.ok) {
          const data = await response.json();
          setExportHistory(prev => {
            const merged = new Map(prev.map(item => [item.id, item]));
            data.forEach(item => {
              merged.set(item.id, {
                id: item.id,
                format: item.format,
                filename: item.filename,
                papers_count: item.papers_count,
                timestamp: new Date(item.exported_at).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
                content: item.content || ''
              });
            });
            return Array.from(merged.values()).sort((a, b) => b.id.localeCompare(a.id));
          });
        }
      } catch (err) {
        console.error('Failed to fetch backend export history:', err);
      }
    };
    fetchExportHistory();
  }, [currentProjectId]);

  // Fetch the latest successful synthesis session draft on mount to pre-populate customDraft
  useEffect(() => {
    const fetchLatestSynthesisDraft = async () => {
      try {
        const response = await safeFetch(`${API_BASE}/projects/${currentProjectId}/synthesis-sessions`);
        if (response.ok) {
          const sessions = await response.json();
          const latestDone = sessions.find(s => s.status === 'done');
          if (latestDone) {
            const resDetail = await safeFetch(`${API_BASE}/synthesis-sessions/${latestDone.id}`);
            if (resDetail.ok) {
              const detail = await resDetail.json();
              if (detail.review_markdown) {
                setCustomDraft(detail.review_markdown);
              }
            }
          }
        }
      } catch (err) {
        console.error('Failed to load latest synthesis draft:', err);
      }
    };
    fetchLatestSynthesisDraft();
  }, []);

  // Generate content dynamically for Live Preview
  const previewContent = useMemo(() => {
    if (activeFormat === 'bibtex') {
      return generateClientBibTeX(targetPapers);
    }
    if (activeFormat === 'csv') {
      return generateClientCSV(targetPapers, includeAbstract);
    }
    if (activeFormat === 'markdown') {
      return generateClientMarkdown(targetPapers, customDraft);
    }
    if (activeFormat === 'json') {
      return generateClientJSON(targetPapers);
    }
    return '';
  }, [activeFormat, targetPapers, includeAbstract, customDraft]);

  const handleDownload = async () => {
    setIsExporting(true);
    try {
      const filename = `litreview_export_${activeFormat}_${new Date().toISOString().slice(0, 10)}.${activeFormat === 'bibtex' ? 'bib' : activeFormat === 'markdown' ? 'md' : activeFormat}`;
      downloadFile(previewContent, filename);
      
      const newHistoryItem = {
        id: `export_${Date.now()}`,
        format: activeFormat.toUpperCase(),
        filename,
        papers_count: targetPapers.length,
        timestamp: new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' }),
        content: previewContent
      };
      setExportHistory(prev => [newHistoryItem, ...prev]);

      setToastMessage(t('export.exported_toast', { format: activeFormat.toUpperCase(), count: targetPapers.length }) || `Exported ${activeFormat.toUpperCase()} successfully!`);
      setTimeout(() => setToastMessage(null), 3000);
    } catch (err) {
      console.error('Export download error:', err);
    } finally {
      setIsExporting(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(previewContent).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const FORMATS = [
    { id: 'bibtex',   label: 'BibTeX (.bib)',      desc: 'LaTeX / Overleaf citation package', icon: BookOpen, ext: '.bib' },
    { id: 'csv',      label: 'Excel / CSV',        desc: 'Tabular data for spreadsheet review', icon: Database, ext: '.csv' },
    { id: 'markdown', label: 'Markdown (.md)',     desc: 'Formatted academic review draft', icon: FileText, ext: '.md' },
    { id: 'json',     label: 'JSON Data',          desc: 'Raw structured JSON schema', icon: Code, ext: '.json' },
  ];

  return (
    <div className="space-y-6 pb-16">
      
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2 bg-surface-900 dark:bg-white text-white dark:text-surface-900 px-4 py-3 rounded-xl shadow-lg animate-slide-up text-xs font-semibold">
          <Check className="w-4 h-4 text-emerald-400 dark:text-emerald-600" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">{t('export.title')}</h1>
          <p className="text-sm text-surface-500 dark:text-surface-400">
            {t('export.desc')}
          </p>
        </div>

        {/* Quick Stats Pills */}
        <div className="flex items-center gap-2">
          <span className="badge badge-neutral text-xs">
            Total: <strong className="ml-1 font-mono">{stats.total}</strong>
          </span>
          <span className="badge badge-primary text-xs">
            Selected: <strong className="ml-1 font-mono">{stats.keep}</strong>
          </span>
          <span className="badge badge-success text-xs">
            Scopus: <strong className="ml-1 font-mono">{stats.scopus}</strong>
          </span>
        </div>
      </div>

      {/* Main Grid: Controls + Preview */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column: Configuration (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          
          {/* Step 1: Scope */}
          <div className="card p-5 space-y-3">
            <div className="flex items-center gap-2">
              <span className="w-5 h-5 rounded-md bg-primary-50 dark:bg-primary-950 text-primary-700 dark:text-primary-300 flex items-center justify-center text-[11px] font-bold">1</span>
              <h3 className="section-label">{t('export.step1')}</h3>
            </div>
            
            <div className="grid grid-cols-3 gap-2">
              {[
                { id: 'keep', label: t('export.scope_keep'), count: stats.keep },
                { id: 'workspace', label: t('export.scope_workspace'), count: workspacePapers.length },
                { id: 'all', label: t('export.scope_all'), count: stats.total },
              ].map(opt => (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => setScope(opt.id)}
                  className={`p-3 rounded-xl border text-left flex flex-col justify-between transition-all ${
                    scope === opt.id
                      ? 'border-primary-500 bg-primary-50/50 dark:bg-primary-950/30'
                      : 'border-surface-200 dark:border-surface-700 hover:border-surface-300'
                  }`}
                >
                  <span className="text-xs font-semibold text-surface-800 dark:text-surface-200 truncate">{opt.label}</span>
                  <span className="text-lg font-bold text-primary-600 dark:text-primary-400 font-mono mt-1">{opt.count}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Step 2: Format Selection */}
          <div id="tour-export-formats" className="card p-5 space-y-3">
            <div className="flex items-center gap-2">
              <span className="w-5 h-5 rounded-md bg-primary-50 dark:bg-primary-950 text-primary-700 dark:text-primary-300 flex items-center justify-center text-[11px] font-bold">2</span>
              <h3 className="section-label">{t('export.step2')}</h3>
            </div>
            
            <div className="grid grid-cols-2 gap-2.5">
              {FORMATS.map(fmt => {
                const Icon = fmt.icon;
                const isActive = activeFormat === fmt.id;
                return (
                  <button
                    key={fmt.id}
                    type="button"
                    onClick={() => setActiveFormat(fmt.id)}
                    className={`p-3 rounded-xl border text-left flex flex-col justify-between transition-all ${
                      isActive
                        ? 'border-primary-500 bg-primary-50/50 dark:bg-primary-950/30'
                        : 'border-surface-200 dark:border-surface-700 hover:border-surface-300'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <Icon className={`w-4 h-4 ${isActive ? 'text-primary-600 dark:text-primary-400' : 'text-surface-400'}`} />
                      <span className="badge badge-neutral text-[10px]">{fmt.ext}</span>
                    </div>
                    <div>
                      <p className="text-xs font-bold text-surface-900 dark:text-white leading-tight">{fmt.label}</p>
                      <p className="text-[10px] text-surface-400 mt-0.5 leading-snug line-clamp-1">{fmt.desc}</p>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Step 3: Options */}
          <div className="card p-5 space-y-3">
            <div className="flex items-center gap-2">
              <span className="w-5 h-5 rounded-md bg-primary-50 dark:bg-primary-950 text-primary-700 dark:text-primary-300 flex items-center justify-center text-[11px] font-bold">3</span>
              <h3 className="section-label">{t('export.step3')}</h3>
            </div>

            <label className="flex items-center justify-between p-3 rounded-xl bg-surface-50 dark:bg-surface-800/50 border border-surface-200 dark:border-surface-700 cursor-pointer">
              <span className="text-xs font-medium text-surface-700 dark:text-surface-300">{t('export.include_abs')}</span>
              <input
                type="checkbox"
                checked={includeAbstract}
                onChange={e => setIncludeAbstract(e.target.checked)}
                className="accent-primary-600 w-4 h-4 rounded"
              />
            </label>

            {activeFormat === 'bibtex' && (
              <div className="space-y-1">
                <label className="section-label block">{t('export.cit_style')}</label>
                <select
                  value={citationStyle}
                  onChange={e => setCitationStyle(e.target.value)}
                  className="input input-sm appearance-none cursor-pointer"
                >
                  <option value="author_year_title">Author + Year + TitleWord (e.g. Smith2024AI)</option>
                  <option value="author_year">Author + Year (e.g. Smith2024)</option>
                </select>
              </div>
            )}

            {activeFormat === 'markdown' && (
              <div className="space-y-1">
                <label className="section-label block">{t('export.custom_draft')}</label>
                <textarea
                  value={customDraft}
                  onChange={e => setCustomDraft(e.target.value)}
                  placeholder={t('export.custom_placeholder')}
                  rows="3"
                  className="input input-sm resize-none text-xs"
                />
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2 pt-1">
            <button
              type="button"
              onClick={handleDownload}
              disabled={isExporting || stats.activeScopeCount === 0}
              className="btn btn-primary flex-1 btn-lg shadow-sm"
            >
              <Download className="w-4 h-4" />
              <span>{t('export.download')} {activeFormat.toUpperCase()} ({stats.activeScopeCount})</span>
            </button>

            <button
              type="button"
              onClick={handleCopy}
              disabled={stats.activeScopeCount === 0}
              className="btn btn-secondary btn-lg"
              title="Copy to clipboard"
            >
              {copied ? <Check className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4" />}
              <span>{copied ? t('export.copied') : t('export.copy')}</span>
            </button>
          </div>
        </div>

        {/* Right Column: Live Preview / History (7 cols) */}
        <div className="lg:col-span-7 card overflow-hidden flex flex-col min-h-[500px]">
          
          {/* Header Bar */}
          <div className="flex items-center justify-between px-5 h-14 border-b border-surface-100 dark:border-surface-800 shrink-0">
            <div className="flex items-center gap-1 p-1 rounded-xl bg-surface-100 dark:bg-surface-800 border border-surface-200 dark:border-surface-700">
              <button
                type="button"
                onClick={() => setRightTab('preview')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  rightTab === 'preview'
                    ? 'bg-white dark:bg-surface-700 text-primary-600 dark:text-primary-400 shadow-xs'
                    : 'text-surface-500 hover:text-surface-800 dark:hover:text-surface-200'
                }`}
              >
                {t('export.preview')}
              </button>
              <button
                type="button"
                onClick={() => setRightTab('history')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
                  rightTab === 'history'
                    ? 'bg-white dark:bg-surface-700 text-primary-600 dark:text-primary-400 shadow-xs'
                    : 'text-surface-500 hover:text-surface-800 dark:hover:text-surface-200'
                }`}
              >
                <span>{t('export.history')}</span>
                {exportHistory.length > 0 && (
                  <span className="badge badge-neutral text-[9px] py-0 px-1">
                    {exportHistory.length}
                  </span>
                )}
              </button>
            </div>

            {rightTab === 'preview' && (
              <span className="badge badge-primary text-[10px] uppercase font-mono">
                {activeFormat}
              </span>
            )}
          </div>

          {/* Body */}
          <div className="flex-1 p-5 flex flex-col min-h-0 bg-surface-50/50 dark:bg-surface-950/30">
            {rightTab === 'preview' ? (
              <div className="flex-1 flex flex-col min-h-0">
                <div className="flex-1 rounded-xl bg-surface-900 dark:bg-surface-950 text-surface-200 p-4 font-mono text-xs overflow-auto border border-surface-800 leading-relaxed custom-scrollbar">
                  <pre className="whitespace-pre-wrap break-words">{previewContent}</pre>
                </div>
                <div className="mt-3 flex items-center justify-between text-xs text-surface-400 px-1">
                  <span>Subset: <strong className="text-surface-700 dark:text-surface-200">{targetPapers.length}</strong> papers ({scope})</span>
                  <span>Chars: <strong className="text-surface-700 dark:text-surface-200 font-mono">{previewContent.length.toLocaleString()}</strong></span>
                </div>
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto space-y-2.5 custom-scrollbar">
                {exportHistory.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-center py-16">
                    <History className="w-8 h-8 text-surface-400 mb-2 opacity-50" />
                    <p className="text-sm font-semibold text-surface-700 dark:text-surface-300">{t('export.no_history')}</p>
                    <p className="text-xs text-surface-400 mt-0.5">{t('export.no_history_desc')}</p>
                  </div>
                ) : (
                  exportHistory.map(item => (
                    <div
                      key={item.id}
                      className="p-3.5 rounded-xl border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 flex items-center justify-between gap-3 hover:border-primary-300 transition-colors"
                    >
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="badge badge-neutral text-[10px] font-mono">{item.format}</span>
                          <span className="text-xs font-mono font-medium text-surface-800 dark:text-surface-200 truncate" title={item.filename}>
                            {item.filename}
                          </span>
                        </div>
                        <p className="text-[11px] text-surface-400 mt-1">
                          {item.papers_count} papers • {item.timestamp}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => downloadFile(item.content, item.filename)}
                        className="btn btn-sm btn-ghost text-xs text-primary-600 dark:text-primary-400 flex-shrink-0"
                      >
                        {t('export.redownload')}
                      </button>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>

        </div>

      </div>
    </div>
  );
}
