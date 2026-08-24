import React, { useEffect, useMemo, useState } from 'react';
import { 
  BookOpen, 
  FileCheck2, 
  Loader2, 
  Play, 
  RefreshCw, 
  ChevronDown, 
  ChevronUp,
  History, 
  Trash2, 
  Plus, 
  Copy, 
  Check, 
  Download, 
  Sparkles, 
  HelpCircle, 
  ExternalLink,
  Code2,
  ListOrdered,
  Lightbulb,
  Search,
  FileSpreadsheet,
  Table,
  MessageSquare,
  ShieldCheck,
  Scale,
  Compass,
  AlertTriangle,
  ArrowRight,
  Layers,
  Quote
} from 'lucide-react';

import CitationChip from './CitationChip';
import {
  DEFAULT_PROJECT_ID,
  buildComparisonRows,
  buildReviewSections,
  buildSynthesisRequest,
  enrichCitation,
  generateFullBibTeX,
  generateAPAReferences,
  generateIEEEReferences,
  generateCSVContent,
  generateAcademicMarkdown,
  extractNoveltyAndGaps,
  generateFollowUpQuestions,
  tokenizeReviewCitations,
} from '../../utils/synthesis';
import { reviewScrollClass, sectionEvidenceLabel } from '../../utils/reviewPresentation';
import { useLanguage } from '../../contexts/LanguageContext';
import { useProject } from '../../contexts/ProjectContext';
import { safeFetch } from '../../utils/apiConfig';

const formatSessionTime = (isoString) => {
  if (!isoString) return '';
  let clean = isoString;
  if (!clean.endsWith('Z') && !clean.includes('+') && !clean.includes('-')) {
    clean += 'Z';
  }
  const date = new Date(clean);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' ' + date.toLocaleDateString();
};

const getPerspectiveBadge = (title = '', isEn = false) => {
  const t = title.toLowerCase();
  if (t.includes('cơ sở') || t.includes('tổng quan') || t.includes('lý thuyết') || t.includes('bài toán') || t.includes('theory') || t.includes('foundation')) {
    return {
      label: isEn ? 'Theoretical Foundations' : 'Cơ sở Lý thuyết & Bài toán',
      badgeClass: 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300 border-blue-200 dark:border-blue-800/60'
    };
  }
  if (t.includes('phương pháp') || t.includes('thuật toán') || t.includes('kỹ thuật') || t.includes('đột phá') || t.includes('method') || t.includes('algorithm')) {
    return {
      label: isEn ? 'Methodology & Techniques' : 'Phương pháp luận & Kỹ thuật',
      badgeClass: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-950 dark:text-cyan-300 border-cyan-200 dark:border-cyan-800/60'
    };
  }
  if (t.includes('thực nghiệm') || t.includes('đánh giá') || t.includes('phát hiện') || t.includes('kết quả') || t.includes('experiment') || t.includes('finding') || t.includes('result')) {
    return {
      label: isEn ? 'Empirical Findings' : 'Thực nghiệm & Phát hiện Cốt lõi',
      badgeClass: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800/60'
    };
  }
  if (t.includes('phê phán') || t.includes('khoảng trống') || t.includes('hạn chế') || t.includes('hướng mở') || t.includes('gap') || t.includes('limitation') || t.includes('future')) {
    return {
      label: isEn ? 'Research Gaps & Future Directions' : 'Khoảng trống Nghiên cứu & Hướng mở',
      badgeClass: 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300 border-amber-200 dark:border-amber-900/60'
    };
  }
  return {
    label: isEn ? 'Multi-perspective Analysis' : 'Phân tích Đa chiều',
    badgeClass: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300 border-indigo-200 dark:border-indigo-800/60'
  };
};

export default function SynthesisPanel({ 
  workspacePapers = [], 
  setActiveCitation, 
  darkMode,
  onSendToChat
}) {
  const { t, language } = useLanguage();
  const { activeProject, activeProjectId } = useProject();
  const currentProjectId = activeProjectId || DEFAULT_PROJECT_ID;
  const isEn = language === 'en';

  const [sessionId, setSessionId] = useState(null);
  const [status, setStatus] = useState('idle');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [history, setHistory] = useState([]);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  
  // Research Focus / Topic Input
  const [researchTopic, setResearchTopic] = useState(() => activeProject?.research_question || '');
  const [copied, setCopied] = useState(false);
  const [bibtexCopied, setBibtexCopied] = useState(false);
  const [apaCopied, setApaCopied] = useState(false);
  const [refViewMode, setRefViewMode] = useState('standard'); // 'standard' | 'bibtex' | 'apa'
  
  // Update topic when activeProject changes
  useEffect(() => {
    if (activeProject?.research_question) {
      setResearchTopic(activeProject.research_question);
    }
  }, [activeProject]);
  
  // Table search filter
  const [matrixSearchQuery, setMatrixSearchQuery] = useState('');
  
  // Claim perspective filter (all, debates, gaps)
  const [activeClaimFilter, setActiveClaimFilter] = useState('all');

  // Collapsed sections set for Accordion UI
  const [collapsedSections, setCollapsedSections] = useState(new Set());

  const toggleSection = (sId) => {
    setCollapsedSections((prev) => {
      const next = new Set(prev);
      if (next.has(sId)) next.delete(sId);
      else next.add(sId);
      return next;
    });
  };

  const canRun = workspacePapers.length > 0 && workspacePapers.length <= 25;

  const fetchHistory = async (autoSelect = false) => {
    try {
      const response = await safeFetch(`/projects/${currentProjectId}/synthesis-sessions`);
      if (response.ok) {
        const data = await response.json();
        setHistory(data);
        if (autoSelect && data.length > 0) {
          const storedId = localStorage.getItem(`litreview_active_synthesis_id_${currentProjectId}`);
          const sessionToLoad = data.find(s => s.id === storedId) || data.find(s => s.status === 'done') || data[0];
          if (sessionToLoad && sessionToLoad.status !== 'failed') {
            setSessionId(sessionToLoad.id);
            setStatus(sessionToLoad.status);
            localStorage.setItem(`litreview_active_synthesis_id_${currentProjectId}`, sessionToLoad.id);
          } else {
            setSessionId(null);
            setStatus('idle');
          }
        }
      }
    } catch (e) {
      console.error('Failed to fetch synthesis history', e);
    }
  };

  useEffect(() => {
    fetchHistory(true);
  }, [currentProjectId]);

  useEffect(() => {
    if (!sessionId) return;
    let timer;

    const checkStatus = async () => {
      try {
        const response = await safeFetch(`/synthesis-sessions/${sessionId}`);
        if (!response.ok) {
          if (response.status === 404) {
            setError(t('synthesis.session_not_found'));
            setStatus('failed');
            return;
          }
          throw new Error(`Failed to fetch status: ${response.status}`);
        }
        const data = await response.json();
        setStatus(data.status);
        if (data.status === 'done') {
          setResult(data);
          fetchHistory(false);
        } else if (data.status === 'failed') {
          setError(data.error_message || t('synthesis.failed_generic'));
          fetchHistory(false);
        } else {
          timer = setTimeout(checkStatus, 2000);
        }
      } catch (err) {
        console.error('Error polling synthesis status:', err);
        timer = setTimeout(checkStatus, 3000);
      }
    };

    checkStatus();
    return () => clearTimeout(timer);
  }, [sessionId, t]);

  const handleStartSynthesis = async () => {
    if (!canRun) return;
    setStatus('starting');
    setError('');
    setResult(null);

    try {
      const payload = buildSynthesisRequest(workspacePapers, currentProjectId, researchTopic || activeProject?.research_question || '');
      const response = await safeFetch('/synthesis-sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || t('synthesis.start_failed'));
      }

      const data = await response.json();
      setSessionId(data.session_id);
      localStorage.setItem(`litreview_active_synthesis_id_${currentProjectId}`, data.session_id);
      setStatus('queued');
      fetchHistory(false);
    } catch (err) {
      console.error(err);
      setError(err.message || t('synthesis.start_failed'));
      setStatus('idle');
    }
  };

  const startSynthesis = handleStartSynthesis;

  const handleReset = () => {
    setSessionId(null);
    setStatus('idle');
    setResult(null);
    setError('');
    localStorage.removeItem('litreview_active_synthesis_id');
  };

  const handleSelectHistory = (item) => {
    setSessionId(item.id);
    setStatus(item.status);
    localStorage.setItem('litreview_active_synthesis_id', item.id);
    setIsHistoryOpen(false);
  };

  const handleDeleteHistory = async (e, idToDelete) => {
    e.stopPropagation();
    try {
      const response = await safeFetch(`/synthesis-sessions/${idToDelete}`, {
        method: 'DELETE',
      });
      if (response.ok) {
        setHistory(prev => prev.filter(item => item.id !== idToDelete));
        if (sessionId === idToDelete) {
          handleReset();
        }
      }
    } catch (err) {
      console.error('Failed to delete synthesis history item', err);
    }
  };

  const reviewSections = useMemo(
    () => buildReviewSections(result, workspacePapers),
    [result, workspacePapers],
  );

  const comparisonRows = useMemo(
    () => buildComparisonRows(result?.evidence_profile || [], workspacePapers, result?.citations || []),
    [result, workspacePapers],
  );

  const bibtexContent = useMemo(() => {
    return generateFullBibTeX(result?.citations || [], workspacePapers);
  }, [result, workspacePapers]);

  // Novelty and Gaps assessment
  const { consensus, debates, gaps } = useMemo(() => {
    return extractNoveltyAndGaps(reviewSections, comparisonRows);
  }, [reviewSections, comparisonRows]);

  // Smart follow-up research questions
  const followUpQuestions = useMemo(() => {
    return generateFollowUpQuestions(result, researchTopic);
  }, [result, researchTopic]);

  const loadSession = (id) => {
    setSessionId(id);
    setStatus('processing');
    setResult(null);
    setError('');
    setIsHistoryOpen(false);
    localStorage.setItem('litreview_active_synthesis_id', id);
  };

  const createNewSession = () => {
    handleReset();
  };

  const deleteSession = async (id) => {
    if (!window.confirm(t('synthesis.delete_session_confirm'))) return;
    try {
      const res = await safeFetch(`/synthesis-sessions/${id}`, { method: 'DELETE' });
      if (res.ok) {
        if (sessionId === id) {
          createNewSession();
        }
        fetchHistory(false);
      }
    } catch (err) {
      console.error('Failed to delete synthesis session:', err);
    }
  };

  const reviewTokens = useMemo(
    () => tokenizeReviewCitations(result?.review_markdown || '', result?.citations || []),
    [result],
  );

  const filteredComparisonRows = useMemo(() => {
    if (!matrixSearchQuery.trim()) return comparisonRows;
    const q = matrixSearchQuery.toLowerCase();
    return comparisonRows.filter(row => 
      (row.title && row.title.toLowerCase().includes(q)) ||
      (row.method && row.method.toLowerCase().includes(q)) ||
      (row.dataset && row.dataset.toLowerCase().includes(q)) ||
      (row.findings && row.findings.toLowerCase().includes(q)) ||
      (row.limitations && row.limitations.toLowerCase().includes(q))
    );
  }, [comparisonRows, matrixSearchQuery]);

  const openCitation = (citation) => {
    setActiveCitation(enrichCitation(citation, workspacePapers));
  };

  const openCellEvidence = (cellObj, fallbackTitle, fallbackFilename) => {
    if (!cellObj) return;
    if (cellObj.citation) {
      setActiveCitation(cellObj.citation);
    } else {
      setActiveCitation({
        title: fallbackTitle || (isEn ? 'Research Document' : 'Tài liệu nghiên cứu'),
        filename: fallbackFilename || null,
        quoted_snippet: cellObj.quote || cellObj.value || '',
        source_page_display: 1,
        marker_display: '[PDF]',
      });
    }
  };

  const openSentence = (event, sentence) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const citation = sentence.citations?.[0];
    setActiveCitation({
      ...(citation || {}),
      kind: 'sentence',
      sentence: sentence.text,
      sentence_type: sentence.sentence_type,
      claim_ids: sentence.claim_ids || [],
      citations: sentence.citations || [],
      anchor: { left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom },
    });
  };

  const handleCopyMarkdown = () => {
    if (!result) return;
    const fullDoc = generateAcademicMarkdown(result, workspacePapers, researchTopic, comparisonRows);
    navigator.clipboard.writeText(fullDoc);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleCopyBibtex = () => {
    if (!bibtexContent) return;
    navigator.clipboard.writeText(bibtexContent);
    setBibtexCopied(true);
    setTimeout(() => setBibtexCopied(false), 2000);
  };

  const handleCopyAPA = () => {
    const refs = generateAPAReferences(result?.citations || [], workspacePapers);
    if (refs.length === 0) return;
    navigator.clipboard.writeText(refs.join('\n\n'));
    setApaCopied(true);
    setTimeout(() => setApaCopied(false), 2000);
  };

  const handleDownloadBibtex = () => {
    if (!bibtexContent) return;
    const blob = new Blob([bibtexContent], { type: 'text/plain;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `references_${new Date().toISOString().slice(0, 10)}.bib`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleDownloadMarkdown = () => {
    if (!result) return;
    const fullDoc = generateAcademicMarkdown(result, workspacePapers, researchTopic, comparisonRows);
    const blob = new Blob([fullDoc], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Academic_Review_${new Date().toISOString().slice(0, 10)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportCSV = () => {
    if (comparisonRows.length === 0) return;
    const csvContent = generateCSVContent(comparisonRows);
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Comparative_Evidence_Matrix_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const isRunning = ['starting', 'processing'].includes(status);

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar bg-transparent">
      
      {/* Top Banner & Control Section */}
      <div className={`p-5 rounded-2xl border transition-all ${
        'bg-white border-slate-200/80 shadow-sm dark:bg-slate-900/60 dark:border-slate-800 dark:shadow-lg'
      }`}>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
          <div className="flex items-start gap-3">
            <div className="p-2.5 rounded-xl bg-blue-50 text-blue-600 dark:bg-blue-900/40 dark:text-blue-400 shrink-0 shadow-xs">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-extrabold text-base text-slate-800 dark:text-slate-100">
                  {t('synthesis.title')}
                </h3>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                  {t('synthesis.engine_badge')}
                </span>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                {t('synthesis.subtitle', { count: workspacePapers.length })}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {sessionId && (
              <button
                onClick={createNewSession}
                className={`inline-flex items-center gap-1.5 px-3 py-2.5 rounded-xl border transition-colors text-xs font-semibold ${
                  'border-slate-200 hover:bg-slate-100 text-slate-700 dark:border-slate-700 dark:hover:bg-slate-800 dark:text-slate-300'
                }`}
                title={t('synthesis.new_report')}
              >
                <Plus className="w-4 h-4" />
                <span>{t('synthesis.new_report')}</span>
              </button>
            )}

            <div className="relative">
              <button
                onClick={() => setIsHistoryOpen(!isHistoryOpen)}
                className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-xl border transition-all text-xs font-semibold cursor-pointer select-none ${
                  isHistoryOpen
                    ? ('bg-blue-50 border-blue-300 text-blue-700 dark:bg-slate-800 dark:border-blue-500 dark:text-blue-400')
                    : ('border-slate-200 hover:bg-slate-100 text-slate-700 dark:border-slate-700 dark:hover:bg-slate-800 dark:text-slate-300')
                }`}
                title={t('synthesis.history_title')}
              >
                <History className="w-4 h-4 text-blue-500" />
                <span>{isEn ? 'History' : 'Lịch sử'} ({history.length})</span>
                <ChevronDown className={`w-3.5 h-3.5 transition-transform ${isHistoryOpen ? 'rotate-180' : ''}`} />
              </button>
              
              {isHistoryOpen && (
                <>
                  <div 
                    className="fixed inset-0 z-40" 
                    onClick={() => setIsHistoryOpen(false)} 
                  />
                  <div className={`absolute right-0 top-full mt-2 w-80 max-h-80 overflow-y-auto rounded-2xl shadow-xl border z-50 p-2 space-y-1.5 custom-scrollbar ${
                    'bg-white border-slate-200 shadow-slate-300/60 dark:bg-slate-900 dark:border-slate-700 dark:shadow-black/80'
                  }`}>
                    <div className="px-2 py-1 text-[11px] font-bold text-slate-400 uppercase tracking-wider flex items-center justify-between border-b pb-1.5 dark:border-slate-800 border-slate-100">
                      <span>{t('synthesis.history_title')} ({history.length})</span>
                      {history.length > 0 && (
                        <button 
                          onClick={() => fetchHistory(false)}
                          className="text-blue-500 hover:underline flex items-center gap-1 font-normal lowercase text-[10px]"
                        >
                          <RefreshCw className="w-2.5 h-2.5" /> {isEn ? 'refresh' : 'làm mới'}
                        </button>
                      )}
                    </div>

                    {history.length === 0 ? (
                      <div className="p-4 text-center text-xs text-slate-400">
                        {isEn ? 'No synthesis history yet.' : 'Chưa có phiên tổng quan nào trong lịch sử.'}
                      </div>
                    ) : (
                      history.map(session => (
                        <div
                          key={session.id}
                          onClick={() => {
                            loadSession(session.id);
                            setIsHistoryOpen(false);
                          }}
                          className={`w-full flex items-center justify-between p-2.5 rounded-xl text-xs transition-all group cursor-pointer border ${
                            sessionId === session.id
                              ? ('bg-blue-50 border-blue-200 text-blue-700 font-semibold dark:bg-blue-900/40 dark:border-blue-700 dark:text-blue-300 dark:font-semibold')
                              : ('border-transparent hover:bg-slate-100 text-slate-700 dark:border-transparent dark:hover:bg-slate-800/80 dark:text-slate-300')
                          }`}
                        >
                          <div className="flex-1 min-w-0 flex flex-col gap-0.5">
                            <div className="flex items-center justify-between">
                              <span className="font-semibold text-[11px] opacity-80">
                                {formatSessionTime(session.created_at)}
                              </span>
                              <span className={`text-[9px] px-1.5 py-0.2 rounded-full font-bold uppercase shrink-0 ${
                                session.status === 'done' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-400' : 
                                session.status === 'failed' ? 'bg-red-100 text-red-700 dark:bg-red-950/60 dark:text-red-400' : 'bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-400'
                              }`}>
                                {session.status}
                              </span>
                            </div>
                            <span className="font-medium opacity-90 truncate text-[11px]">
                              {session.paper_count} {t('synthesis.papers_selected')}
                            </span>
                          </div>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteSession(session.id);
                            }}
                            className="opacity-0 group-hover:opacity-100 ml-2 p-1 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 transition-all shrink-0"
                            title={!isEn ? 'Xóa phiên báo cáo này' : 'Delete this report session'}
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Focus Research Topic Input */}
        <div className="space-y-2 mt-4 pt-4 border-t dark:border-slate-800/80 border-slate-100">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
              <span>{t('synthesis.focus_topic_label')}</span>
            </label>
            <span className="text-[11px] text-slate-400 font-mono">
              {workspacePapers.length} {t('synthesis.papers_selected')}
            </span>
          </div>
          <div className="flex flex-col sm:flex-row gap-2.5">
            <input
              type="text"
              value={researchTopic}
              onChange={(e) => setResearchTopic(e.target.value)}
              disabled={isRunning}
              placeholder={t('synthesis.focus_topic_placeholder')}
              className={`flex-1 px-4 py-2.5 rounded-xl text-xs border transition-all focus:outline-none focus:ring-2 focus:ring-blue-500/20 ${
                'bg-slate-50 border-slate-200 text-slate-800 placeholder-slate-400 focus:border-blue-600 dark:bg-slate-950 dark:border-slate-700 dark:text-slate-200 dark:placeholder-slate-500 dark:focus:border-blue-500'
              }`}
            />
            <button
              onClick={startSynthesis}
              disabled={!canRun || isRunning}
              className="inline-flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-bold shadow-md shadow-blue-600/20 active:scale-95 transition-all shrink-0 cursor-pointer"
            >
              {isRunning ? <Loader2 className="w-4 h-4 animate-spin" /> : result ? <RefreshCw className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              <span>{isRunning ? t('synthesis.btn_running') : result ? t('synthesis.btn_rerun') : t('synthesis.btn_start')}</span>
            </button>
          </div>
        </div>
      </div>

      {!canRun && (
        <div className="text-xs p-4 rounded-xl bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-900/50 flex items-center gap-2">
          <HelpCircle className="w-4 h-4 shrink-0" />
          <span>{t('synthesis.req_msg')}</span>
        </div>
      )}

      {/* Progress & Status Indicator */}
      {isRunning && (
        <div className="p-8 rounded-2xl border border-blue-100 dark:border-blue-900/40 bg-blue-50/50 dark:bg-blue-950/20 flex flex-col items-center justify-center text-center space-y-3 shadow-sm">
          <Loader2 className="w-8 h-8 text-blue-600 dark:text-blue-400 animate-spin" />
          <div>
            <h4 className="text-sm font-bold text-slate-800 dark:text-slate-200">
              {t('synthesis.status_running_title')}
            </h4>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-md">
              {t('synthesis.status_running_desc', { count: workspacePapers.length })}
            </p>
          </div>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-300 text-xs border border-red-200 dark:border-red-900/40 whitespace-pre-wrap flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {/* Complete Literature Report View */}
      {(result?.review_markdown || reviewSections.length > 0) && status === 'done' && (
        <div className={`rounded-2xl border p-6 space-y-6 ${reviewScrollClass} ${
          'bg-white border-slate-200 shadow-sm dark:bg-slate-900/40 dark:border-slate-800'
        }`}>
          
          {/* Action Bar: Copy, Download MD, Download BibTeX, Export CSV */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b dark:border-slate-800 border-slate-100">
            <div className="flex items-center gap-2">
              <FileCheck2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
              <div>
                <h4 className="font-extrabold text-sm text-slate-800 dark:text-slate-100">
                  {t('synthesis.completed_title')}
                </h4>
                <p className="text-[11px] text-slate-400">
                  {t('synthesis.completed_desc')}
                </p>
              </div>
            </div>

            <div className="flex items-center flex-wrap gap-2">
              <button
                onClick={handleCopyMarkdown}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer ${
                  copied
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800'
                    : 'border-slate-200 hover:bg-slate-100 text-slate-700 dark:border-slate-700 dark:hover:bg-slate-800 dark:text-slate-300'
                }`}
                title={t('synthesis.copy_md')}
              >
                {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? t('synthesis.copied') : t('synthesis.copy_md')}</span>
              </button>

              <button
                onClick={handleCopyAPA}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer ${
                  apaCopied
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800'
                    : 'border-slate-200 hover:bg-slate-100 text-slate-700 dark:border-slate-700 dark:hover:bg-slate-800 dark:text-slate-300'
                }`}
                title={!isEn ? 'Sao chép trích dẫn (APA 7th)' : 'Copy citations (APA 7th)'}
              >
                {apaCopied ? <Check className="w-3.5 h-3.5" /> : <Quote className="w-3.5 h-3.5 text-amber-500" />}
                <span>{apaCopied ? (isEn ? 'Copied APA' : 'Đã chép APA') : 'APA 7th'}</span>
              </button>

              <button
                onClick={handleDownloadMarkdown}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer ${
                  'border-slate-200 hover:bg-slate-100 text-slate-700 dark:border-slate-700 dark:hover:bg-slate-800 dark:text-slate-300'
                }`}
                title={!isEn ? 'Tải báo cáo (.md)' : 'Download report (.md)'}
              >
                <Download className="w-3.5 h-3.5" />
                <span>{isEn ? 'Academic Report (.md)' : 'Báo cáo Học thuật (.md)'}</span>
              </button>

              <button
                onClick={handleDownloadBibtex}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer ${
                  'border-slate-200 hover:bg-slate-100 text-slate-700 dark:border-slate-700 dark:hover:bg-slate-800 dark:text-slate-300'
                }`}
                title={t('synthesis.download_bib')}
              >
                <Code2 className="w-3.5 h-3.5 text-blue-500" />
                <span>{t('synthesis.download_bib')}</span>
              </button>

              {comparisonRows.length > 0 && (
                <button
                  onClick={handleExportCSV}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer ${
                    'border-slate-200 hover:bg-slate-100 text-slate-700 dark:border-slate-700 dark:hover:bg-slate-800 dark:text-slate-300'
                  }`}
                  title={!isEn ? 'Xuất ma trận (CSV)' : 'Export matrix (CSV)'}
                >
                  <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-500" />
                  <span>{t('synthesis.export_csv')}</span>
                </button>
              )}
            </div>
          </div>

          {/* Executive Takeaways Card (Điểm nhấn Cốt lõi) */}
          {consensus.length > 0 && (
            <div className={`p-4 rounded-xl border transition-all ${
              'bg-blue-50/50 border-blue-100 dark:bg-blue-950/20 dark:border-blue-900/40'
            }`}>
              <div className="flex items-center gap-2 mb-2 text-blue-700 dark:text-blue-300 font-bold text-xs">
                <Lightbulb className="w-4 h-4" />
                <span>{t('synthesis.takeaways_title')}</span>
              </div>
              <ul className="space-y-1.5 text-xs text-slate-700 dark:text-slate-300 pl-4 list-disc marker:text-blue-500">
                {consensus.slice(0, 4).map((takeaway, idx) => (
                  <li key={idx} className="leading-relaxed">
                    <span>{takeaway.text}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Section 1: Interactive Comparative Matrix Table */}
          {comparisonRows.length > 0 && (
            <div className="space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Table className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                  <h5 className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                    {t('synthesis.matrix_title')}
                  </h5>
                  <span className="text-[10px] bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300 px-2 py-0.5 rounded-full font-bold">
                    {t('synthesis.matrix_hint')}
                  </span>
                </div>

                {/* Table Search Filter */}
                <div className="relative w-full sm:w-64">
                  <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
                  <input
                    type="text"
                    value={matrixSearchQuery}
                    onChange={(e) => setMatrixSearchQuery(e.target.value)}
                    placeholder={t('synthesis.matrix_search_placeholder')}
                    className={`w-full pl-8 pr-3 py-1.5 text-xs rounded-lg border focus:outline-none focus:ring-1 focus:ring-blue-500 ${
                      'bg-slate-50 border-slate-200 text-slate-800 dark:bg-slate-950 dark:border-slate-700 dark:text-slate-200'
                    }`}
                  />
                </div>
              </div>

              <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700/80 shadow-xs">
                <table className="w-full min-w-[950px] text-xs text-left">
                  <thead className="bg-slate-100/90 dark:bg-slate-800/90 text-slate-700 dark:text-slate-200 border-b dark:border-slate-700">
                    <tr>
                      <th className="p-3 font-bold w-[22%]">{t('synthesis.th_paper_author')}</th>
                      <th className="p-3 font-bold w-[20%]">{t('synthesis.th_method')}</th>
                      <th className="p-3 font-bold w-[18%]">{t('synthesis.th_dataset')}</th>
                      <th className="p-3 font-bold w-[22%]">{t('synthesis.th_findings')}</th>
                      <th className="p-3 font-bold w-[18%]">{t('synthesis.th_limitations')}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200/80 dark:divide-slate-800">
                    {filteredComparisonRows.map((row) => (
                      <tr key={row.paperId} className="align-top bg-white dark:bg-slate-900/40 hover:bg-slate-50/50 dark:hover:bg-slate-800/40 transition-colors">
                        <td className="p-3 font-bold text-slate-800 dark:text-slate-100">
                          <div>{row.title}</div>
                          {row.authors && <div className="text-[11px] font-normal text-slate-400 mt-0.5 truncate">{row.authors} ({row.year})</div>}
                        </td>
                        {['method', 'dataset', 'findings', 'limitations'].map((colKey) => {
                          const cell = row.cells?.[colKey];
                          const hasContent = cell && cell.value;
                          return (
                            <td 
                              key={colKey}
                              onClick={() => hasContent && openCellEvidence(cell, row.title, row.filename)}
                              className={`p-3 leading-relaxed transition-all ${
                                hasContent 
                                  ? 'cursor-pointer hover:bg-blue-50/80 dark:hover:bg-blue-950/60 hover:text-blue-700 dark:hover:text-blue-300 text-slate-600 dark:text-slate-300' 
                                  : 'text-slate-400 italic'
                              }`}
                              title={hasContent ? (isEn ? 'Click to inspect grounded snippet in PDF' : 'Nhấp để xem đoạn chứng cứ bôi vàng trên file PDF') : ''}
                            >
                              {hasContent ? (
                                <div className="relative group">
                                  <span>{cell.value}</span>
                                  <span className="opacity-0 group-hover:opacity-100 ml-1 text-[10px] text-blue-500 font-bold underline inline-block">
                                    [PDF]
                                  </span>
                                </div>
                              ) : (
                                <span className="text-[11px]">—</span>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                    {filteredComparisonRows.length === 0 && (
                      <tr>
                        <td colSpan={5} className="p-6 text-center text-slate-400 italic">
                          {t('synthesis.no_matrix_match')} "{matrixSearchQuery}"
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Section 2: Novelty & Research Gaps Evaluation (Đánh giá Tính mới & Khoảng trống Nghiên cứu) */}
          {(consensus.length > 0 || debates.length > 0 || gaps.length > 0) && (
            <div className={`p-5 rounded-xl border space-y-3 transition-all ${
              'bg-slate-50/80 border-slate-200 dark:bg-slate-950/50 dark:border-slate-800'
            }`}>
              <div className="flex items-center gap-2 text-slate-800 dark:text-slate-200 font-bold text-xs uppercase tracking-wider">
                <Compass className="w-4 h-4 text-amber-500" />
                <span>{t('synthesis.novelty_gaps_title')}</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-1">
                {/* 1. Đồng thuận Vững chắc */}
                <div className="p-4 rounded-xl bg-emerald-50/70 dark:bg-emerald-950/30 border border-emerald-200/80 dark:border-emerald-900/50 space-y-2.5 shadow-2xs">
                  <div className="flex items-center gap-1.5 text-emerald-800 dark:text-emerald-300 font-bold text-xs">
                    <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                    <span>{t('synthesis.novelty_consensus')} ({consensus.length})</span>
                  </div>
                  <ul className="space-y-2 text-[12px] text-slate-700 dark:text-slate-300 pl-3 list-disc marker:text-emerald-500">
                    {consensus.slice(0, 4).map((item, i) => (
                      <li key={i} className="leading-relaxed">
                        <span>{item.text}</span>
                        {item.citations?.map((c, cIdx) => (
                          <CitationChip
                            key={c.id || cIdx}
                            citeId={c.marker_display || cIdx + 1}
                            citeObj={c}
                            onClick={() => openCitation(c)}
                            darkMode={darkMode}
                          />
                        ))}
                      </li>
                    ))}
                    {consensus.length === 0 && <li className="italic text-slate-400">{t('synthesis.updating')}</li>}
                  </ul>
                </div>

                {/* 2. Tranh luận & Bất đồng (Contradictions & Trade-offs) */}
                <div className="p-4 rounded-xl bg-rose-50/70 dark:bg-rose-950/30 border border-rose-200/80 dark:border-rose-900/50 space-y-2.5 shadow-2xs">
                  <div className="flex items-center gap-1.5 text-rose-800 dark:text-rose-300 font-bold text-xs">
                    <Scale className="w-4 h-4 text-rose-600 dark:text-rose-400" />
                    <span>{t('synthesis.novelty_debates')} ({debates.length})</span>
                  </div>
                  <ul className="space-y-2 text-[12px] text-slate-700 dark:text-slate-300 pl-3 list-disc marker:text-rose-500">
                    {debates.slice(0, 4).map((item, i) => (
                      <li key={i} className="leading-relaxed">
                        <span>{item.text}</span>
                        {item.citations?.map((c, cIdx) => (
                          <CitationChip
                            key={c.id || cIdx}
                            citeId={c.marker_display || cIdx + 1}
                            citeObj={c}
                            onClick={() => openCitation(c)}
                            darkMode={darkMode}
                          />
                        ))}
                      </li>
                    ))}
                    {debates.length === 0 && <li className="italic text-slate-400">{t('synthesis.high_consensus')}</li>}
                  </ul>
                </div>

                {/* 3. Khoảng trống Nghiên cứu & Hướng mở */}
                <div className="p-4 rounded-xl bg-amber-50/70 dark:bg-amber-950/30 border border-amber-200/80 dark:border-amber-900/50 space-y-2.5 shadow-2xs">
                  <div className="flex items-center gap-1.5 text-amber-800 dark:text-amber-300 font-bold text-xs">
                    <Compass className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                    <span>{t('synthesis.novelty_gaps')} ({gaps.length})</span>
                  </div>
                  <ul className="space-y-2 text-[12px] text-slate-700 dark:text-slate-300 pl-3 list-disc marker:text-amber-500">
                    {gaps.slice(0, 4).map((item, i) => (
                      <li key={i} className="leading-relaxed">
                        <span>{item.text}</span>
                        {item.citations?.map((c, cIdx) => (
                          <CitationChip
                            key={c.id || cIdx}
                            citeId={c.marker_display || cIdx + 1}
                            citeObj={c}
                            onClick={() => openCitation(c)}
                            darkMode={darkMode}
                          />
                        ))}
                      </li>
                    ))}
                    {gaps.length === 0 && <li className="italic text-slate-400">{t('synthesis.no_major_gaps')}</li>}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* Section 3: Narrative Literature Review Sections with Perspective Badges */}
          <div className="space-y-4 pt-2">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <h5 className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                {t('synthesis.narrative_title')}
              </h5>

              {/* Filter Pills for Perspectives */}
              <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800/80 p-0.5 rounded-lg text-xs font-semibold">
                <button
                  onClick={() => setActiveClaimFilter('all')}
                  className={`px-2.5 py-1 rounded-md transition-all ${
                    activeClaimFilter === 'all'
                      ? 'bg-white dark:bg-slate-700 text-blue-600 dark:text-blue-400 shadow-xs'
                      : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                  }`}
                >
                  {t('synthesis.filter_all')} ({reviewSections.length} {t('synthesis.sections_count')})
                </button>
                <button
                  onClick={() => setActiveClaimFilter('debates')}
                  className={`px-2.5 py-1 rounded-md transition-all ${
                    activeClaimFilter === 'debates'
                      ? 'bg-white dark:bg-slate-700 text-rose-600 dark:text-rose-400 shadow-xs'
                      : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                  }`}
                >
                  {t('synthesis.filter_debates')} ({debates.length})
                </button>
                <button
                  onClick={() => setActiveClaimFilter('gaps')}
                  className={`px-2.5 py-1 rounded-md transition-all ${
                    activeClaimFilter === 'gaps'
                      ? 'bg-white dark:bg-slate-700 text-amber-600 dark:text-amber-400 shadow-xs'
                      : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                  }`}
                >
                  {t('synthesis.filter_gaps')} ({gaps.length})
                </button>
              </div>
            </div>

            {reviewSections.length > 0 ? (
              reviewSections.map((section, sIdx) => {
                const perspective = getPerspectiveBadge(section.title, isEn);
                const isCollapsed = collapsedSections.has(section.id);
                return (
                  <div 
                    key={section.id} 
                    className={`rounded-2xl border transition-all duration-200 shadow-xs overflow-hidden ${
                      'bg-white border-slate-200/90 hover:border-slate-300 dark:bg-slate-900/60 dark:border-slate-800 dark:hover:border-slate-700'
                    }`}
                  >
                    {/* Collapsible Section Header (Accordion) */}
                    <div 
                      onClick={() => toggleSection(section.id)}
                      className={`p-4 flex flex-wrap items-center justify-between gap-3 cursor-pointer select-none transition-colors ${
                        'hover:bg-slate-50 dark:hover:bg-slate-800/50'
                      } ${!isCollapsed ? ('border-b border-slate-100 bg-slate-50/40 dark:border-b dark:border-slate-800/80 dark:bg-slate-800/20') : ''}`}
                    >
                      <div className="flex items-center gap-2.5 flex-wrap">
                        <span className="w-6 h-6 rounded-lg bg-blue-600 text-white text-xs flex items-center justify-center font-bold shadow-xs">
                          {sIdx + 1}
                        </span>
                        <h4 className="font-bold text-[15px] text-slate-800 dark:text-slate-100">
                          {section.title}
                        </h4>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${perspective.badgeClass}`}>
                          {perspective.label}
                        </span>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ${
                          section.coverage?.status === 'sufficient' 
                            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300' 
                            : 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300'
                        }`}>
                          {sectionEvidenceLabel(section.coverage)}
                        </span>
                        <button
                          type="button"
                          className="p-1 rounded-md text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                        >
                          {isCollapsed ? <ChevronDown className="w-4 h-4" /> : <ChevronUp className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>

                    {/* Section Body */}
                    {!isCollapsed && (
                      <div className="p-5 space-y-4">
                        <div className="text-[14px] leading-8 text-justify text-slate-700 dark:text-slate-300">
                          {section.sentences.map((sentence, index) => (
                            <React.Fragment key={`${section.id}-${index}`}>
                              <span
                                onClick={(event) => openSentence(event, sentence)}
                                className={`inline rounded px-1 transition-all cursor-pointer ${
                                  sentence.sentence_type === 'claim' 
                                    ? 'hover:bg-blue-100 dark:hover:bg-blue-950/80 decoration-blue-400 underline decoration-dotted underline-offset-4' 
                                    : 'hover:bg-violet-100 dark:hover:bg-violet-950/80'
                                }`}
                                title={sentence.sentence_type === 'claim' ? t('synthesis.click_view_claim_pdf') : t('synthesis.click_view_cite_pdf')}
                              >
                                {sentence.text}
                              </span>
                              {sentence.citations?.map((c, cIdx) => (
                                <CitationChip
                                  key={c.id || cIdx}
                                  citeId={c.marker_display || cIdx + 1}
                                  citeObj={c}
                                  onClick={() => openCitation(c)}
                                  darkMode={darkMode}
                                />
                              ))}{' '}
                            </React.Fragment>
                          ))}
                        </div>

                        {section.coverage?.reasons?.length > 0 && section.coverage.status !== 'sufficient' && (
                          <p className="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/20 p-2.5 rounded-lg border border-amber-200/50">
                            {section.coverage.reasons.join(' ')}
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                );
              })
            ) : (
              <div className="text-sm leading-relaxed whitespace-pre-wrap text-slate-700 dark:text-slate-300 p-5 rounded-2xl border border-slate-200 dark:border-slate-800">
                {reviewTokens.map((token, index) => (
                  token.type === 'citation' ? (
                    <CitationChip
                      key={`${token.citation.id}-${index}`}
                      citeId={token.citation.marker_display || token.citation.id}
                      citeObj={token.citation}
                      onClick={() => openCitation(token.citation)}
                      darkMode={darkMode}
                    />
                  ) : (
                    <React.Fragment key={`text-${index}`}>{token.text}</React.Fragment>
                  )
                ))}
              </div>
            )}
          </div>

          {/* Section 4: Interactive Follow-up Research Prompts */}
          {followUpQuestions.length > 0 && (
            <div className={`p-5 rounded-xl border space-y-3 transition-all ${
              'bg-blue-50/40 border-blue-100 dark:bg-blue-950/20 dark:border-blue-900/40'
            }`}>
              <div className="flex items-center gap-2 text-blue-700 dark:text-blue-300 font-bold text-xs uppercase tracking-wider">
                <Sparkles className="w-4 h-4" />
                <span>{t('synthesis.followup_title')}</span>
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                {t('synthesis.followup_desc')}
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                {followUpQuestions.map((q, idx) => (
                  <div
                    key={idx}
                    className={`p-3 rounded-xl border flex flex-col justify-between gap-2 text-xs transition-all ${
                      'bg-white border-slate-200 hover:border-blue-400 shadow-xs dark:bg-slate-900/80 dark:border-slate-800 dark:hover:border-blue-700'
                    }`}
                  >
                    <p className="font-medium text-slate-700 dark:text-slate-300 leading-relaxed">
                      {q}
                    </p>
                    <div className="flex items-center justify-end gap-2 pt-1 border-t dark:border-slate-800/60 border-slate-100">
                      <button
                        onClick={() => {
                          setResearchTopic(q);
                          window.scrollTo({ top: 0, behavior: 'smooth' });
                        }}
                        className="text-[11px] text-slate-500 hover:text-blue-600 dark:hover:text-blue-400 font-semibold flex items-center gap-1 transition-colors"
                      >
                        {t('synthesis.set_focus')} <ArrowRight className="w-3 h-3" />
                      </button>
                      {onSendToChat && (
                        <button
                          onClick={() => onSendToChat(q)}
                          className="text-[11px] px-2 py-0.5 rounded-md bg-blue-600 hover:bg-blue-700 text-white font-bold flex items-center gap-1 transition-all cursor-pointer"
                        >
                          <MessageSquare className="w-3 h-3" />
                          {t('synthesis.ask_chat')}
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Section 5: Bibliography / Danh mục tham khảo & BibTeX */}
          {result?.citations?.length > 0 && (
            <div className="space-y-3 pt-4 border-t dark:border-slate-800 border-slate-200">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <h5 className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                  {t('synthesis.references_title')}
                </h5>
                <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800 p-0.5 rounded-lg">
                  <button
                    onClick={() => setRefViewMode('standard')}
                    className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-all flex items-center gap-1 ${
                      refViewMode === 'standard'
                        ? 'bg-white dark:bg-slate-700 text-blue-600 dark:text-blue-400 shadow-xs'
                        : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                    }`}
                  >
                    <ListOrdered className="w-3.5 h-3.5" />
                    <span>{t('synthesis.ref_mode_standard')}</span>
                  </button>
                  <button
                    onClick={() => setRefViewMode('bibtex')}
                    className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-all flex items-center gap-1 ${
                      refViewMode === 'bibtex'
                        ? 'bg-white dark:bg-slate-700 text-blue-600 dark:text-blue-400 shadow-xs'
                        : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                    }`}
                  >
                    <Code2 className="w-3.5 h-3.5" />
                    <span>{t('synthesis.ref_mode_bibtex')}</span>
                  </button>
                </div>
              </div>

              {refViewMode === 'standard' ? (
                <div className="space-y-2">
                  {result.citations.map((cite, idx) => (
                    <div 
                      key={cite.id || idx}
                      onClick={() => openCitation(cite)}
                      className={`flex items-start gap-3 p-3 rounded-xl border text-xs cursor-pointer transition-colors ${
                        'bg-slate-50/50 border-slate-200/80 hover:bg-blue-50/50 dark:bg-slate-950/30 dark:border-slate-800 dark:hover:bg-slate-800/60'
                      }`}
                    >
                      <span className="font-bold text-blue-600 dark:text-blue-400 shrink-0">
                        {cite.marker_display || `[${idx + 1}]`}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold text-slate-800 dark:text-slate-200 truncate">
                          {cite.title || cite.filename || (isEn ? 'Untitled Document' : 'Tài liệu không tên')}
                        </p>
                        {cite.quoted_snippet && (
                          <p className="text-slate-500 dark:text-slate-400 italic text-[11px] mt-0.5 line-clamp-1">
                            "{cite.quoted_snippet}"
                          </p>
                        )}
                      </div>
                      <span className="text-[10px] text-blue-600 dark:text-blue-400 shrink-0 flex items-center gap-1 font-semibold">
                        {t('synthesis.view_pdf')} <ExternalLink className="w-3 h-3" />
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="relative">
                  <pre className="p-4 rounded-xl text-xs font-mono overflow-x-auto bg-slate-900 text-slate-200 dark:bg-slate-950 border border-slate-800">
                    {bibtexContent}
                  </pre>
                  <div className="absolute top-3 right-3 flex items-center gap-2">
                    <button
                      onClick={handleCopyBibtex}
                      className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white shadow-sm transition-all cursor-pointer"
                    >
                      {bibtexCopied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{bibtexCopied ? t('synthesis.copied_bibtex') : t('synthesis.copy_bibtex')}</span>
                    </button>
                    <button
                      onClick={handleDownloadBibtex}
                      className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold bg-slate-700 hover:bg-slate-600 text-white shadow-sm transition-all cursor-pointer"
                      title={t('synthesis.download_bib')}
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>{t('synthesis.download_bib')}</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

        </div>
      )}
    </div>
  );
}
