import React, { useState, useEffect, useMemo } from 'react';
import {
  generateClientBibTeX,
  generateClientCSV,
  generateClientMarkdown,
  generateClientJSON,
  downloadFile
} from '../../utils/exportUtils';
import { useLanguage } from '../../contexts/LanguageContext';

import { API_BASE } from '../../utils/apiConfig';
const DEFAULT_PROJECT_ID = '00000000-0000-0000-0000-000000000001';

export default function ExportTab({ papers = [], selectedPapers = [], workspacePapers = [], darkMode = false }) {
  const { t } = useLanguage();
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

  // Setup history (REAL DATA from Setup tab)
  const [researchSetup, setResearchSetup] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('litreview_setup')) || null;
    } catch {
      return null;
    }
  });

  const projectInfo = {
    name: researchSetup?.name || 'Literature Review Project',
    research_question: researchSetup?.research_question || 'Not specified',
    research_field: researchSetup?.research_field || 'Not specified',
    criteria_include: researchSetup?.criteria_include?.join(', ') || 'Not specified',
    criteria_exclude: researchSetup?.criteria_exclude?.join(', ') || 'Not specified'
  };

  // Sync history to localStorage
  useEffect(() => {
    localStorage.setItem('litreview_export_history', JSON.stringify(exportHistory));
  }, [exportHistory]);

  // Fetch export history from backend on mount and merge
  useEffect(() => {
    const fetchExportHistory = async () => {
      try {
        const response = await fetch(`${API_BASE}/projects/${DEFAULT_PROJECT_ID}/export/history`);
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
  }, []);

  // Fetch the latest successful synthesis session draft on mount to pre-populate customDraft
  useEffect(() => {
    const fetchLatestSynthesisDraft = async () => {
      try {
        const response = await fetch(`${API_BASE}/projects/${DEFAULT_PROJECT_ID}/synthesis-sessions`);
        if (response.ok) {
          const sessions = await response.json();
          const latestDone = sessions.find(s => s.status === 'done');
          if (latestDone) {
            const resDetail = await fetch(`${API_BASE}/synthesis-sessions/${latestDone.id}`);
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
      return generateClientMarkdown(targetPapers, projectInfo, customDraft);
    }
    if (activeFormat === 'json') {
      return generateClientJSON(targetPapers, projectInfo, customDraft);
    }
    return '';
  }, [targetPapers, activeFormat, includeAbstract, customDraft]);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 3500);
  };

  // Trigger Download
  const handleDownload = async () => {
    setIsExporting(true);
    const now = new Date();
    const timestamp = now.toISOString().replace(/[-:]/g, '').replace('T', '_').slice(0, 15);
    const projSlug = projectInfo.name.replace(/[^a-zA-Z0-9]/g, '_').toLowerCase();

    let ext = 'bib';
    let mime = 'text/plain;charset=utf-8';

    if (activeFormat === 'bibtex') {
      ext = 'bib';
      mime = 'application/x-bibtex;charset=utf-8';
    } else if (activeFormat === 'csv') {
      ext = 'csv';
      mime = 'text/csv;charset=utf-8';
    } else if (activeFormat === 'markdown') {
      ext = 'md';
      mime = 'text/markdown;charset=utf-8';
    } else if (activeFormat === 'json') {
      ext = 'json';
      mime = 'application/json;charset=utf-8';
    }

    const filename = `${projSlug}_${activeFormat.toUpperCase()}_${timestamp}.${ext}`;

    try {
      // Attempt backend API call first
      const backendPayload = {
        format: activeFormat,
        scope: scope,
        include_abstract: includeAbstract,
        citation_key_style: citationStyle,
        draft_text: customDraft,
        custom_papers: targetPapers
      };

      const response = await fetch(`${API_BASE}/projects/${DEFAULT_PROJECT_ID}/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(backendPayload)
      }).catch(() => null);

      let finalContent = previewContent;
      let finalFilename = filename;

      if (response && response.ok) {
        const data = await response.json();
        if (data.content) finalContent = data.content;
        if (data.filename) finalFilename = data.filename;
      }

      downloadFile(finalContent, finalFilename, mime);

      // Add to session history
      const historyItem = {
        id: `exp_${Date.now()}`,
        format: activeFormat.toUpperCase(),
        filename: finalFilename,
        papers_count: targetPapers.length,
        timestamp: new Date().toLocaleTimeString(),
        content: finalContent
      };
      setExportHistory(prev => [historyItem, ...prev]);

      showToast(t('export.success_msg'));
    } catch (err) {
      console.error('Export download error:', err);
      // Fallback client download
      downloadFile(previewContent, filename, mime);
      showToast(`Exported ${filename} (Client Fallback)`);
    } finally {
      setIsExporting(false);
    }
  };

  // Copy Preview to Clipboard
  const handleCopy = () => {
    navigator.clipboard.writeText(previewContent).then(() => {
      setCopied(true);
      showToast(t('export.copied_msg'));
      setTimeout(() => setCopied(false), 2000);
    }).catch(err => {
      console.error('Failed to copy text: ', err);
    });
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center space-x-2 bg-emerald-600 text-white px-4 py-3 rounded-lg shadow-xl animate-bounce">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
          </svg>
          <span className="font-medium text-sm">{toastMessage}</span>
        </div>
      )}

      {/* Header Banner */}
      <div className="bg-gradient-to-r from-indigo-900 via-slate-900 to-sky-900 text-white p-6 md:p-8 rounded-2xl shadow-lg border border-indigo-800/40">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 text-indigo-300 text-sm font-semibold tracking-wide uppercase mb-1">
              <span>{t('export.module')}</span>
              <span>•</span>
              <span>{t('export.package')}</span>
            </div>
            <h1 className="text-2xl md:text-3xl font-extrabold text-white">{t('export.title')}</h1>
            <p className="text-slate-300 text-sm mt-1 max-w-2xl">
              {t('export.desc')}
            </p>
          </div>

          {/* Quick Metrics */}
          <div className="flex flex-wrap gap-2 md:gap-3 bg-slate-800/80 backdrop-blur-md p-3 rounded-xl border border-slate-700/60 text-xs">
            <div className="text-center px-3 py-1 bg-slate-700/50 rounded-lg">
              <div className="text-slate-400 font-medium">{t('export.total_papers')}</div>
              <div className="text-lg font-bold text-white">{stats.total}</div>
            </div>
            <div className="text-center px-3 py-1 bg-emerald-950/60 rounded-lg border border-emerald-800/50">
              <div className="text-emerald-400 font-medium">{t('export.keep_papers')}</div>
              <div className="text-lg font-bold text-emerald-300">{stats.keep}</div>
            </div>
            <div className="text-center px-3 py-1 bg-sky-950/60 rounded-lg border border-sky-800/50">
              <div className="text-sky-400 font-medium">{t('export.scopus_verified')}</div>
              <div className="text-lg font-bold text-sky-300">{stats.scopus}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Main 2-Column Responsive Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* LEFT COLUMN: Controls & Formats (5 cols) */}
        <div className="lg:col-span-5 space-y-6">

          {/* Step 1: Scope Selection */}
          <div className="bg-white dark:bg-slate-900 p-5 rounded-xl shadow-sm border border-slate-200 dark:border-slate-800">
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3">
              {t('export.step1')}
            </label>
            <div className="grid grid-cols-1 gap-2">
              <button
                type="button"
                onClick={() => setScope('keep')}
                className={`flex items-center justify-between p-3 rounded-lg border text-left transition-all ${
                  scope === 'keep'
                    ? 'border-indigo-600 bg-indigo-50/70 dark:bg-indigo-950/40 text-indigo-900 dark:text-indigo-200 font-semibold ring-2 ring-indigo-500/20'
                    : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 text-slate-700 dark:text-slate-300'
                }`}
              >
                <div>
                  <div className="text-sm font-medium">{t('export.keep_only')}</div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">{t('export.keep_desc')}</div>
                </div>
                <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 font-bold">
                  {stats.keep} {t('export.papers')}
                </span>
              </button>

              <button
                type="button"
                onClick={() => setScope('all')}
                className={`flex items-center justify-between p-3 rounded-lg border text-left transition-all ${
                  scope === 'all'
                    ? 'border-indigo-600 bg-indigo-50/70 dark:bg-indigo-950/40 text-indigo-900 dark:text-indigo-200 font-semibold ring-2 ring-indigo-500/20'
                    : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 text-slate-700 dark:text-slate-300'
                }`}
              >
                <div>
                  <div className="text-sm font-medium">{t('export.all_project')}</div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">{t('export.all_desc')}</div>
                </div>
                <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-bold">
                  {stats.total} {t('export.papers')}
                </span>
              </button>

              <button
                type="button"
                onClick={() => setScope('workspace')}
                className={`flex items-center justify-between p-3 rounded-lg border text-left transition-all ${
                  scope === 'workspace'
                    ? 'border-indigo-600 bg-indigo-50/70 dark:bg-indigo-950/40 text-indigo-900 dark:text-indigo-200 font-semibold ring-2 ring-indigo-500/20'
                    : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 text-slate-700 dark:text-slate-300'
                }`}
              >
                <div>
                  <div className="text-sm font-medium">{t('export.workspace_set')}</div>
                  <div className="text-xs text-slate-500 dark:text-slate-400">{t('export.workspace_desc')}</div>
                </div>
                <span className="text-xs px-2 py-0.5 rounded-full bg-sky-100 dark:bg-sky-950 text-sky-800 dark:text-sky-300 font-bold">
                  {workspacePapers.length || stats.total} {t('export.papers')}
                </span>
              </button>
            </div>
          </div>

          {/* Step 2: Choose Export Format */}
          <div className="bg-white dark:bg-slate-900 p-5 rounded-xl shadow-sm border border-slate-200 dark:border-slate-800">
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3">
              {t('export.step2')}
            </label>
            <div className="grid grid-cols-2 gap-3">
              
              {/* BibTeX */}
              <button
                type="button"
                onClick={() => setActiveFormat('bibtex')}
                className={`p-4 rounded-xl border text-left transition-all flex flex-col justify-between ${
                  activeFormat === 'bibtex'
                    ? 'border-indigo-600 bg-indigo-600 text-white shadow-md ring-2 ring-indigo-500/30'
                    : 'border-slate-200 dark:border-slate-800 hover:border-indigo-300 dark:hover:border-indigo-800 text-slate-800 dark:text-slate-200 bg-slate-50/50 dark:bg-slate-800/30'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-2xl">📜</span>
                  <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${
                    activeFormat === 'bibtex' ? 'bg-indigo-800 text-indigo-100' : 'bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300'
                  }`}>.bib</span>
                </div>
                <div>
                  <div className="font-bold text-sm">{t('export.bibtex_cit')}</div>
                  <div className={`text-xs mt-0.5 ${activeFormat === 'bibtex' ? 'text-indigo-100' : 'text-slate-500 dark:text-slate-400'}`}>{t('export.bibtex_desc')}</div>
                </div>
              </button>

              {/* CSV */}
              <button
                type="button"
                onClick={() => setActiveFormat('csv')}
                className={`p-4 rounded-xl border text-left transition-all flex flex-col justify-between ${
                  activeFormat === 'csv'
                    ? 'border-indigo-600 bg-indigo-600 text-white shadow-md ring-2 ring-indigo-500/30'
                    : 'border-slate-200 dark:border-slate-800 hover:border-indigo-300 dark:hover:border-indigo-800 text-slate-800 dark:text-slate-200 bg-slate-50/50 dark:bg-slate-800/30'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-2xl">📊</span>
                  <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${
                    activeFormat === 'csv' ? 'bg-indigo-800 text-indigo-100' : 'bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300'
                  }`}>.csv</span>
                </div>
                <div>
                  <div className="font-bold text-sm">{t('export.csv_meta')}</div>
                  <div className={`text-xs mt-0.5 ${activeFormat === 'csv' ? 'text-indigo-100' : 'text-slate-500 dark:text-slate-400'}`}>{t('export.csv_desc')}</div>
                </div>
              </button>

              {/* Markdown */}
              <button
                type="button"
                onClick={() => setActiveFormat('markdown')}
                className={`p-4 rounded-xl border text-left transition-all flex flex-col justify-between ${
                  activeFormat === 'markdown'
                    ? 'border-indigo-600 bg-indigo-600 text-white shadow-md ring-2 ring-indigo-500/30'
                    : 'border-slate-200 dark:border-slate-800 hover:border-indigo-300 dark:hover:border-indigo-800 text-slate-800 dark:text-slate-200 bg-slate-50/50 dark:bg-slate-800/30'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-2xl">📝</span>
                  <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${
                    activeFormat === 'markdown' ? 'bg-indigo-800 text-indigo-100' : 'bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300'
                  }`}>.md</span>
                </div>
                <div>
                  <div className="font-bold text-sm">{t('export.md_report')}</div>
                  <div className={`text-xs mt-0.5 ${activeFormat === 'markdown' ? 'text-indigo-100' : 'text-slate-500 dark:text-slate-400'}`}>{t('export.md_desc')}</div>
                </div>
              </button>

              {/* JSON Package */}
              <button
                type="button"
                onClick={() => setActiveFormat('json')}
                className={`p-4 rounded-xl border text-left transition-all flex flex-col justify-between ${
                  activeFormat === 'json'
                    ? 'border-indigo-600 bg-indigo-600 text-white shadow-md ring-2 ring-indigo-500/30'
                    : 'border-slate-200 dark:border-slate-800 hover:border-indigo-300 dark:hover:border-indigo-800 text-slate-800 dark:text-slate-200 bg-slate-50/50 dark:bg-slate-800/30'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-2xl">📦</span>
                  <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${
                    activeFormat === 'json' ? 'bg-indigo-800 text-indigo-100' : 'bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300'
                  }`}>.json</span>
                </div>
                <div>
                  <div className="font-bold text-sm">{t('export.json_pkg')}</div>
                  <div className={`text-xs mt-0.5 ${activeFormat === 'json' ? 'text-indigo-100' : 'text-slate-500 dark:text-slate-400'}`}>{t('export.json_desc')}</div>
                </div>
              </button>

            </div>
          </div>

          {/* Step 3: Customization Options */}
          <div className="bg-white dark:bg-slate-900 p-5 rounded-xl shadow-sm border border-slate-200 dark:border-slate-800 space-y-4">
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              {t('export.step3')}
            </label>

            <div className="flex items-center justify-between">
              <span className="text-sm text-slate-700 dark:text-slate-300 font-medium">{t('export.include_abs')}</span>
              <input
                type="checkbox"
                checked={includeAbstract}
                onChange={(e) => setIncludeAbstract(e.target.checked)}
                className="w-4 h-4 text-indigo-600 rounded focus:ring-indigo-500 border-slate-300 dark:border-slate-700"
              />
            </div>

            {activeFormat === 'bibtex' && (
              <div>
                <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">{t('export.cit_style')}</label>
                <select
                  value={citationStyle}
                  onChange={(e) => setCitationStyle(e.target.value)}
                  className="w-full text-xs p-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200"
                >
                  <option value="author_year_title">Author + Year + TitleWord (e.g. Smith2024AI)</option>
                  <option value="author_year">Author + Year (e.g. Smith2024)</option>
                </select>
              </div>
            )}

            {activeFormat === 'markdown' && (
              <div>
                <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">{t('export.custom_draft')}</label>
                <textarea
                  value={customDraft}
                  onChange={(e) => setCustomDraft(e.target.value)}
                  placeholder={t('export.custom_placeholder')}
                  rows="3"
                  className="w-full text-xs p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 placeholder-slate-400 focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={handleDownload}
              disabled={isExporting || stats.activeScopeCount === 0}
              className="flex-1 py-3.5 px-6 rounded-xl bg-gradient-to-r from-indigo-600 to-sky-600 hover:from-indigo-500 hover:to-sky-500 text-white font-bold text-sm shadow-md transition-all flex items-center justify-center space-x-2 disabled:opacity-50"
            >
              {isExporting ? (
                <>
                  <svg className="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span>{t('export.exporting')}</span>
                </>
              ) : (
                <>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  <span>{t('export.download')} {activeFormat.toUpperCase()} ({stats.activeScopeCount})</span>
                </>
              )}
            </button>

            <button
              type="button"
              onClick={handleCopy}
              disabled={stats.activeScopeCount === 0}
              className="py-3.5 px-4 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 font-semibold text-sm transition-all flex items-center justify-center space-x-1.5"
              title="Copy snippet to clipboard"
            >
              {copied ? (
                <>
                  <svg className="w-5 h-5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="text-emerald-600 dark:text-emerald-400">{t('export.copied')}</span>
                </>
              ) : (
                <>
                  <svg className="w-5 h-5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                  </svg>
                  <span>{t('export.copy')}</span>
                </>
              )}
            </button>
          </div>

        </div>

        {/* RIGHT COLUMN: Live Preview & Export History (7 cols) */}
        <div className="lg:col-span-7 bg-white dark:bg-slate-900 rounded-xl shadow-sm border border-slate-200 dark:border-slate-800 flex flex-col min-h-[580px]">
          
          {/* Right Column Header Tabs */}
          <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 rounded-t-xl">
            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={() => setRightTab('preview')}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  rightTab === 'preview'
                    ? 'bg-white dark:bg-slate-900 text-indigo-600 dark:text-indigo-400 shadow-sm border border-slate-200 dark:border-slate-800'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                👁️ {t('export.preview')}
              </button>
              <button
                type="button"
                onClick={() => setRightTab('history')}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center space-x-1 ${
                  rightTab === 'history'
                    ? 'bg-white dark:bg-slate-900 text-indigo-600 dark:text-indigo-400 shadow-sm border border-slate-200 dark:border-slate-800'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                <span>⏳ {t('export.history')}</span>
                {exportHistory.length > 0 && (
                  <span className="px-1.5 py-0.2 rounded-full bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 text-[10px]">
                    {exportHistory.length}
                  </span>
                )}
              </button>
            </div>

            {rightTab === 'preview' && (
              <div className="flex items-center space-x-2">
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 uppercase">
                  {activeFormat}
                </span>
                <button
                  type="button"
                  onClick={handleCopy}
                  className="text-xs text-indigo-600 dark:text-indigo-400 font-semibold hover:underline"
                >
                  {t('export.copy_snippet')}
                </button>
              </div>
            )}
          </div>

          {/* Right Column Body */}
          <div className="p-5 flex-1 flex flex-col">
            {rightTab === 'preview' ? (
              <div className="flex-1 flex flex-col">
                <div className="relative flex-1 bg-slate-950 text-slate-100 rounded-xl p-4 font-mono text-xs overflow-auto max-h-[500px] border border-slate-800 leading-relaxed">
                  <pre className="whitespace-pre-wrap break-words">{previewContent}</pre>
                </div>
                <div className="mt-3 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
                  <span>{t('export.target_subset')} <strong>{targetPapers.length} {t('export.papers')}</strong> ({scope})</span>
                  <span>{t('export.char_count')} <strong>{previewContent.length.toLocaleString()}</strong></span>
                </div>
              </div>
            ) : (
              <div className="flex-1 overflow-auto space-y-3">
                {exportHistory.length === 0 ? (
                  <div className="text-center py-16 text-slate-400 dark:text-slate-500">
                    <span className="text-3xl block mb-2">📁</span>
                    <p className="text-sm">{t('export.no_history')}</p>
                    <p className="text-xs mt-1">{t('export.no_history_desc')}</p>
                  </div>
                ) : (
                  exportHistory.map((item) => (
                    <div
                      key={item.id}
                      className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/20 flex items-center justify-between"
                    >
                      <div className="space-y-0.5">
                        <div className="flex items-center space-x-2">
                          <span className="text-xs font-bold px-2 py-0.5 rounded bg-indigo-100 dark:bg-indigo-950 text-indigo-800 dark:text-indigo-300">
                            {item.format}
                          </span>
                          <span className="text-xs font-mono font-semibold text-slate-800 dark:text-slate-200">
                            {item.filename}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-500 dark:text-slate-400">
                          {item.papers_count} papers • {item.timestamp}
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => downloadFile(item.content, item.filename)}
                        className="text-xs px-3 py-1.5 rounded-lg bg-slate-200 dark:bg-slate-700 hover:bg-indigo-100 dark:hover:bg-indigo-900/50 text-slate-700 dark:text-slate-200 font-semibold transition-all"
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
