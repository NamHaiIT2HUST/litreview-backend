import React, { useEffect, useMemo, useState } from 'react';
import { 
  BookOpen, 
  FileCheck2, 
  Loader2, 
  Play, 
  RefreshCw, 
  ChevronDown, 
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
  Lightbulb
} from 'lucide-react';

import {
  DEFAULT_PROJECT_ID,
  buildComparisonRows,
  buildReviewSections,
  buildSynthesisRequest,
  enrichCitation,
  tokenizeReviewCitations,
} from '../../utils/synthesis';
import { reviewScrollClass, sectionEvidenceLabel } from '../../utils/reviewPresentation';
import { useLanguage } from '../../contexts/LanguageContext';
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

const getPerspectiveBadge = (title = '') => {
  const t = title.toLowerCase();
  if (t.includes('cơ sở') || t.includes('tổng quan') || t.includes('lý thuyết') || t.includes('bài toán')) {
    return {
      label: 'Cơ sở Lý thuyết & Bài toán',
      badgeClass: 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300 border-blue-200 dark:border-blue-800/60'
    };
  }
  if (t.includes('phương pháp') || t.includes('thuật toán') || t.includes('kỹ thuật') || t.includes('đột phá')) {
    return {
      label: 'Phương pháp luận & Kỹ thuật',
      badgeClass: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-950 dark:text-cyan-300 border-cyan-200 dark:border-cyan-800/60'
    };
  }
  if (t.includes('thực nghiệm') || t.includes('đánh giá') || t.includes('phát hiện') || t.includes('kết quả')) {
    return {
      label: 'Thực nghiệm & Phát hiện Cốt lõi',
      badgeClass: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800/60'
    };
  }
  if (t.includes('phê phán') || t.includes('khoảng trống') || t.includes('hạn chế') || t.includes('hướng mở')) {
    return {
      label: 'Khoảng trống Nghiên cứu & Hướng mở',
      badgeClass: 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300 border-amber-200 dark:border-amber-900/60'
    };
  }
  return {
    label: 'Phân tích Đa chiều',
    badgeClass: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300 border-indigo-200 dark:border-indigo-800/60'
  };
};

export default function SynthesisPanel({ workspacePapers, setActiveCitation, darkMode }) {
  const { t } = useLanguage();
  const [sessionId, setSessionId] = useState(null);
  const [status, setStatus] = useState('idle');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [history, setHistory] = useState([]);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  
  // Research Focus / Topic Input
  const [researchTopic, setResearchTopic] = useState('');
  const [copied, setCopied] = useState(false);
  const [bibtexCopied, setBibtexCopied] = useState(false);
  const [refViewMode, setRefViewMode] = useState('standard'); // 'standard' | 'bibtex'

  const canRun = workspacePapers.length > 0 && workspacePapers.length <= 25;

  const fetchHistory = async (autoSelect = false) => {
    try {
      const response = await safeFetch(`/projects/${DEFAULT_PROJECT_ID}/synthesis-sessions`);
      if (response.ok) {
        const data = await response.json();
        setHistory(data);
        if (autoSelect && data.length > 0) {
          const storedId = localStorage.getItem('litreview_active_synthesis_id');
          const sessionToLoad = data.find(s => s.id === storedId) || data.find(s => s.status === 'done') || data[0];
          if (sessionToLoad && sessionToLoad.status !== 'failed') {
            setSessionId(sessionToLoad.id);
            setStatus(sessionToLoad.status);
            localStorage.setItem('litreview_active_synthesis_id', sessionToLoad.id);
          } else {
            setSessionId(null);
            setStatus('idle');
            setError('');
            localStorage.removeItem('litreview_active_synthesis_id');
          }
        }
      }
    } catch (err) {
      console.error('Failed to fetch synthesis history:', err);
    }
  };

  useEffect(() => {
    fetchHistory(true);
  }, []);

  const startSynthesis = async () => {
    if (!canRun) return;
    setError('');
    setResult(null);
    setStatus('starting');
    setActiveCitation(null);

    try {
      const requestPayload = buildSynthesisRequest(workspacePapers, DEFAULT_PROJECT_ID, researchTopic);
      const response = await safeFetch('/synthesis-sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestPayload),
      });
      const data = await response.json();
      if (!response.ok) {
        const detailStr = typeof data.detail === 'string' 
          ? data.detail 
          : (Array.isArray(data.detail) ? data.detail.map(d => d.msg || JSON.stringify(d)).join(', ') : JSON.stringify(data.detail));
        throw new Error(detailStr || t('synthesis.create_failed'));
      }
      setSessionId(data.session_id);
      setStatus(data.status || 'processing');
      localStorage.setItem('litreview_active_synthesis_id', data.session_id);
      fetchHistory();
    } catch (err) {
      setStatus('failed');
      setError(err.message || t('synthesis.synthesis_failed'));
    }
  };

  const loadSession = (id) => {
    setSessionId(id);
    setStatus('processing');
    setResult(null);
    setError('');
    setIsHistoryOpen(false);
    localStorage.setItem('litreview_active_synthesis_id', id);
  };

  const createNewSession = () => {
    setSessionId(null);
    setStatus('idle');
    setResult(null);
    setError('');
    setResearchTopic('');
    localStorage.removeItem('litreview_active_synthesis_id');
  };

  const deleteSession = async (id) => {
    if (!window.confirm("Bạn có chắc chắn muốn xóa phiên báo cáo tổng quan này không?")) return;
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

  useEffect(() => {
    if (!sessionId || !['starting', 'processing'].includes(status)) return undefined;

    let cancelled = false;
    const poll = async () => {
      try {
        const response = await safeFetch(`/synthesis-sessions/${sessionId}`);
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || t('synthesis.read_failed'));
        }
        if (cancelled) return;
        setStatus(data.status);
        setResult(data);
        if (data.status === 'done' && data.research_question) {
          setResearchTopic(data.research_question);
        }
        if (data.status === 'failed') {
          setError(data.error_message || t('synthesis.synthesis_failed'));
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || t('synthesis.check_failed'));
        }
      }
    };

    poll();
    const timer = window.setInterval(poll, 2000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [sessionId, status]);

  const reviewTokens = useMemo(
    () => tokenizeReviewCitations(result?.review_markdown || '', result?.citations || []),
    [result],
  );
  const reviewSections = useMemo(
    () => buildReviewSections(result, workspacePapers),
    [result, workspacePapers],
  );
  const comparisonRows = useMemo(
    () => buildComparisonRows(result?.evidence_profile || [], workspacePapers),
    [result, workspacePapers],
  );

  // Generate clean BibTeX text
  const bibtexContent = useMemo(() => {
    if (!result?.citations || result.citations.length === 0) return '';
    return result.citations.map((cite, index) => {
      const paper = workspacePapers.find(p => p.id === cite.paper_id) || {};
      const authorStr = paper.authors || 'Unknown';
      const firstAuthor = authorStr.split(',')[0].trim().split(' ').pop().toLowerCase().replace(/[^a-z]/g, '') || `paper${index+1}`;
      const year = paper.year || new Date().getFullYear();
      const citeKey = `${firstAuthor}${year}`;
      const title = cite.title || paper.title || 'Untitled';
      const journal = paper.journal || paper.venue || '';

      let entry = `@article{${citeKey},\n`;
      entry += `  title = {${title}},\n`;
      entry += `  author = {${authorStr}},\n`;
      if (journal) entry += `  journal = {${journal}},\n`;
      entry += `  year = {${year}}\n`;
      entry += `}`;
      return entry;
    }).join('\n\n');
  }, [result, workspacePapers]);

  // Executive Takeaways: extract first key claims
  const executiveTakeaways = useMemo(() => {
    if (!reviewSections || reviewSections.length === 0) return [];
    const claims = [];
    for (const section of reviewSections) {
      for (const sent of section.sentences || []) {
        if (sent.sentence_type === 'claim' && sent.text.length > 25 && claims.length < 4) {
          claims.push({ text: sent.text, sectionTitle: section.title, citations: sent.citations });
        }
      }
    }
    return claims;
  }, [reviewSections]);

  const openCitation = (citation) => {
    setActiveCitation(enrichCitation(citation, workspacePapers));
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
    if (!result?.review_markdown) return;
    navigator.clipboard.writeText(result.review_markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleCopyBibtex = () => {
    if (!bibtexContent) return;
    navigator.clipboard.writeText(bibtexContent);
    setBibtexCopied(true);
    setTimeout(() => setBibtexCopied(false), 2000);
  };

  const handleDownloadMarkdown = () => {
    if (!result?.review_markdown) return;
    let fullDoc = result.review_markdown;
    if (bibtexContent) {
      fullDoc += `\n\n## Danh mục BibTeX\n\`\`\`bibtex\n${bibtexContent}\n\`\`\``;
    }
    const blob = new Blob([fullDoc], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Bao_cao_Tong_quan_${new Date().toISOString().slice(0, 10)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const isRunning = ['starting', 'processing'].includes(status);

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-5 custom-scrollbar bg-transparent">
      
      {/* Top Banner & Control Section */}
      <div className={`p-5 rounded-2xl border transition-all ${
        darkMode ? 'bg-slate-900/60 border-slate-800 shadow-lg' : 'bg-white border-slate-200/80 shadow-sm'
      }`}>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
          <div className="flex items-start gap-3">
            <div className="p-2.5 rounded-xl bg-blue-50 text-blue-600 dark:bg-blue-900/40 dark:text-blue-400 shrink-0">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-extrabold text-base text-slate-800 dark:text-slate-100">
                  Báo cáo Tổng quan Tài liệu
                </h3>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Tự động đối chiếu, tổng hợp đa chiều và lập luận dựa trên bằng chứng xác thực từ {workspacePapers.length} tài liệu đã tải lên.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {sessionId && (
              <button
                onClick={createNewSession}
                className={`inline-flex items-center gap-1.5 px-3 py-2.5 rounded-xl border transition-colors text-xs font-semibold ${
                  darkMode
                    ? 'border-slate-700 hover:bg-slate-800 text-slate-300'
                    : 'border-slate-200 hover:bg-slate-100 text-slate-700'
                }`}
                title="Tạo phiên báo cáo mới"
              >
                <Plus className="w-4 h-4" />
                <span>Báo cáo mới</span>
              </button>
            )}

            {history.length > 0 && (
              <div className="relative">
                <button
                  onClick={() => setIsHistoryOpen(!isHistoryOpen)}
                  className={`inline-flex items-center gap-2 px-3 py-2.5 rounded-xl border transition-colors text-xs font-semibold ${
                    darkMode
                      ? 'border-slate-700 hover:bg-slate-800 text-slate-300'
                      : 'border-slate-200 hover:bg-slate-100 text-slate-700'
                  }`}
                  title="Lịch sử các phiên tổng quan"
                >
                  <History className="w-4 h-4" />
                  <span className="hidden sm:inline">Lịch sử</span>
                  <ChevronDown className="w-3 h-3" />
                </button>
                
                {isHistoryOpen && (
                  <div className={`absolute right-0 top-full mt-2 w-80 max-h-80 overflow-y-auto rounded-2xl shadow-xl border z-50 p-2 space-y-1 ${
                    darkMode ? 'bg-slate-900 border-slate-700 shadow-black/80' : 'bg-white border-slate-200 shadow-slate-300/60'
                  }`}>
                    <div className="px-2 py-1 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                      Các báo cáo đã tạo ({history.length})
                    </div>
                    {history.map(session => (
                      <div
                        key={session.id}
                        onClick={() => loadSession(session.id)}
                        className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs transition-colors group cursor-pointer ${
                          sessionId === session.id
                            ? (darkMode ? 'bg-blue-900/40 text-blue-300 font-semibold' : 'bg-blue-50 text-blue-700 font-semibold')
                            : (darkMode ? 'hover:bg-slate-800 text-slate-300' : 'hover:bg-slate-100 text-slate-700')
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
                            {session.paper_count} tài liệu nguồn
                          </span>
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteSession(session.id);
                          }}
                          className="opacity-0 group-hover:opacity-100 ml-2 p-1 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 transition-all shrink-0"
                          title="Xóa phiên báo cáo này"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Focus Research Topic Input */}
        <div className="space-y-2 mt-4 pt-4 border-t dark:border-slate-800/80 border-slate-100">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
              <span>Chủ đề / Định hướng nghiên cứu trọng tâm (Tùy chọn)</span>
            </label>
            <span className="text-[11px] text-slate-400">
              {workspacePapers.length} bài báo đã chọn
            </span>
          </div>
          <div className="flex gap-2.5">
            <input
              type="text"
              value={researchTopic}
              onChange={(e) => setResearchTopic(e.target.value)}
              disabled={isRunning}
              placeholder="Ví dụ: Phân tích so sánh các thuật toán giải bài toán CFP, ưu nhược điểm... (để trống để tổng hợp toàn diện)"
              className={`flex-1 px-4 py-2.5 rounded-xl text-xs border transition-all focus:outline-none focus:ring-2 focus:ring-blue-500/20 ${
                darkMode 
                  ? 'bg-slate-950 border-slate-700 text-slate-200 placeholder-slate-500 focus:border-blue-500' 
                  : 'bg-slate-50 border-slate-200 text-slate-800 placeholder-slate-400 focus:border-blue-600'
              }`}
            />
            <button
              onClick={startSynthesis}
              disabled={!canRun || isRunning}
              className="inline-flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-bold shadow-md shadow-blue-600/20 active:scale-95 transition-all shrink-0 cursor-pointer"
            >
              {isRunning ? <Loader2 className="w-4 h-4 animate-spin" /> : result ? <RefreshCw className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              <span>{isRunning ? 'Đang viết báo cáo...' : result ? 'Tạo lại báo cáo' : 'Tạo Báo cáo Tổng quan'}</span>
            </button>
          </div>
        </div>
      </div>

      {!canRun && (
        <div className="text-xs p-4 rounded-xl bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-900/50 flex items-center gap-2">
          <HelpCircle className="w-4 h-4 shrink-0" />
          <span>Vui lòng chọn hoặc tải lên ít nhất 1 tài liệu ở cột "Nguồn" bên trái để tạo báo cáo tổng quan.</span>
        </div>
      )}

      {/* Progress & Status Indicator */}
      {isRunning && (
        <div className="p-8 rounded-2xl border border-blue-100 dark:border-blue-900/40 bg-blue-50/50 dark:bg-blue-950/20 flex flex-col items-center justify-center text-center space-y-3">
          <Loader2 className="w-8 h-8 text-blue-600 dark:text-blue-400 animate-spin" />
          <div>
            <h4 className="text-sm font-bold text-slate-800 dark:text-slate-200">
              Đang phân tích & tổng hợp tài liệu...
            </h4>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-md">
              Hệ thống đang trích xuất bằng chứng từ {workspacePapers.length} tài liệu, kiểm chứng các luận điểm và viết báo cáo học thuật hoàn chỉnh.
            </p>
          </div>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-300 text-xs border border-red-200 dark:border-red-900/40 whitespace-pre-wrap">
          {error}
        </div>
      )}

      {/* Complete Literature Report View */}
      {(result?.review_markdown || reviewSections.length > 0) && status === 'done' && (
        <div className={`rounded-2xl border p-6 space-y-6 ${reviewScrollClass} ${
          darkMode ? 'bg-slate-900/40 border-slate-800' : 'bg-white border-slate-200 shadow-sm'
        }`}>
          
          {/* Action Bar: Copy & Download */}
          <div className="flex items-center justify-between pb-4 border-b dark:border-slate-800 border-slate-100">
            <div className="flex items-center gap-2">
              <FileCheck2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
              <div>
                <h4 className="font-extrabold text-sm text-slate-800 dark:text-slate-100">
                  Báo cáo Tổng quan Tài liệu đã Hoàn thiện
                </h4>
                <p className="text-[11px] text-slate-400">
                  100% luận điểm được xác minh nguồn trích dẫn
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleCopyMarkdown}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer ${
                  copied
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800'
                    : darkMode
                    ? 'border-slate-700 hover:bg-slate-800 text-slate-300'
                    : 'border-slate-200 hover:bg-slate-100 text-slate-700'
                }`}
                title="Sao chép toàn văn Markdown"
              >
                {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Đã sao chép' : 'Sao chép Markdown'}</span>
              </button>

              <button
                onClick={handleDownloadMarkdown}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer ${
                  darkMode
                    ? 'border-slate-700 hover:bg-slate-800 text-slate-300'
                    : 'border-slate-200 hover:bg-slate-100 text-slate-700'
                }`}
                title="Tải về file .md"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Tải file .md</span>
              </button>
            </div>
          </div>

          {/* Executive Takeaways Card (Điểm nhấn Cốt lõi) */}
          {executiveTakeaways.length > 0 && (
            <div className={`p-4 rounded-xl border transition-all ${
              darkMode ? 'bg-blue-950/20 border-blue-900/40' : 'bg-blue-50/50 border-blue-100'
            }`}>
              <div className="flex items-center gap-2 mb-2 text-blue-700 dark:text-blue-300 font-bold text-xs">
                <Lightbulb className="w-4 h-4" />
                <span>Điểm nhấn Cốt lõi (Executive Takeaways)</span>
              </div>
              <ul className="space-y-1.5 text-xs text-slate-700 dark:text-slate-300 pl-4 list-disc marker:text-blue-500">
                {executiveTakeaways.map((takeaway, idx) => (
                  <li key={idx} className="leading-relaxed">
                    <span>{takeaway.text}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Section 1: Comparative Matrix Table */}
          {comparisonRows.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h5 className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                  Bảng Đối chiếu Tổng hợp Đa Nguồn
                </h5>
                <span className="text-[10px] text-slate-400 font-mono">
                  {comparisonRows.length} nghiên cứu
                </span>
              </div>
              <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700/80 shadow-xs">
                <table className="w-full min-w-[900px] text-xs text-left">
                  <thead className="bg-slate-100/80 dark:bg-slate-800/80 text-slate-700 dark:text-slate-200 border-b dark:border-slate-700">
                    <tr>
                      <th className="p-3 font-bold w-[22%]">Tài liệu & Tác giả</th>
                      <th className="p-3 font-bold w-[20%]">Phương pháp</th>
                      <th className="p-3 font-bold w-[18%]">Dữ liệu & Thực nghiệm</th>
                      <th className="p-3 font-bold w-[22%]">Phát hiện chính</th>
                      <th className="p-3 font-bold w-[18%]">Hạn chế</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200/80 dark:divide-slate-800">
                    {comparisonRows.map((row) => (
                      <tr key={row.paperId} className="align-top bg-white dark:bg-slate-900/40 hover:bg-slate-50/50 dark:hover:bg-slate-800/40 transition-colors">
                        <td className="p-3 font-bold text-slate-800 dark:text-slate-100">{row.title}</td>
                        {[row.method, row.dataset, row.findings, row.limitations].map((value, index) => (
                          <td key={index} className="p-3 leading-relaxed text-slate-600 dark:text-slate-300">
                            {value || <span className="italic text-slate-400 text-[11px]">—</span>}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Section 2: Narrative Literature Review Sections with Perspective Badges */}
          <div className="space-y-6 pt-2">
            <h5 className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
              Nội dung Tổng quan Học thuật & Luận điểm Chứng minh
            </h5>

            {reviewSections.length > 0 ? (
              reviewSections.map((section, sIdx) => {
                const perspective = getPerspectiveBadge(section.title);
                return (
                  <div 
                    key={section.id} 
                    className={`p-5 rounded-xl border transition-all ${
                      darkMode ? 'bg-slate-950/40 border-slate-800/80' : 'bg-slate-50/70 border-slate-200/80'
                    }`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-3 pb-2 border-b dark:border-slate-800 border-slate-200/60">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h4 className="font-bold text-[15px] text-slate-800 dark:text-slate-100 flex items-center gap-2">
                          <span className="w-5 h-5 rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900/60 dark:text-blue-300 text-xs flex items-center justify-center font-extrabold">
                            {sIdx + 1}
                          </span>
                          <span>{section.title}</span>
                        </h4>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${perspective.badgeClass}`}>
                          {perspective.label}
                        </span>
                      </div>
                      <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ${
                        section.coverage?.status === 'sufficient' 
                          ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300' 
                          : 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300'
                      }`}>
                        {sectionEvidenceLabel(section.coverage)}
                      </span>
                    </div>

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
                            title={sentence.sentence_type === 'claim' ? 'Nhấp để xem chứng cứ đối chiếu trên file PDF' : 'Nhấp để xem nguồn trích dẫn'}
                          >
                            {sentence.text}
                          </span>{' '}
                        </React.Fragment>
                      ))}
                    </div>

                    {section.coverage?.reasons?.length > 0 && section.coverage.status !== 'sufficient' && (
                      <p className="mt-3 text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/20 p-2.5 rounded-lg">
                        {section.coverage.reasons.join(' ')}
                      </p>
                    )}
                  </div>
                );
              })
            ) : (
              <div className="text-sm leading-relaxed whitespace-pre-wrap text-slate-700 dark:text-slate-300">
                {reviewTokens.map((token, index) => (
                  token.type === 'citation' ? (
                    <button
                      key={`${token.citation.id}-${index}`}
                      onClick={() => openCitation(token.citation)}
                      className="mx-0.5 text-blue-600 dark:text-blue-400 font-bold hover:underline align-baseline cursor-pointer"
                      title="Xem bằng chứng trên file PDF"
                    >
                      {token.text}
                    </button>
                  ) : (
                    <React.Fragment key={`text-${index}`}>{token.text}</React.Fragment>
                  )
                ))}
              </div>
            )}
          </div>

          {/* Section 3: Bibliography / Danh mục tham khảo & BibTeX */}
          {result?.citations?.length > 0 && (
            <div className="space-y-3 pt-4 border-t dark:border-slate-800 border-slate-200">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <h5 className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                  Danh mục Tài liệu Tham khảo & Trích dẫn
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
                    <span>Danh mục chuẩn</span>
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
                    <span>Mã BibTeX</span>
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
                        darkMode ? 'bg-slate-950/30 border-slate-800 hover:bg-slate-800/60' : 'bg-slate-50/50 border-slate-200/80 hover:bg-blue-50/50'
                      }`}
                    >
                      <span className="font-bold text-blue-600 dark:text-blue-400 shrink-0">
                        {cite.marker_display || `[${idx + 1}]`}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold text-slate-800 dark:text-slate-200 truncate">
                          {cite.title || cite.filename || 'Tài liệu không tên'}
                        </p>
                        {cite.quoted_snippet && (
                          <p className="text-slate-500 dark:text-slate-400 italic text-[11px] mt-0.5 line-clamp-1">
                            "{cite.quoted_snippet}"
                          </p>
                        )}
                      </div>
                      <span className="text-[10px] text-blue-600 dark:text-blue-400 shrink-0 flex items-center gap-1 font-semibold">
                        Xem PDF <ExternalLink className="w-3 h-3" />
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="relative">
                  <pre className="p-4 rounded-xl text-xs font-mono overflow-x-auto bg-slate-900 text-slate-200 dark:bg-slate-950 border border-slate-800">
                    {bibtexContent}
                  </pre>
                  <button
                    onClick={handleCopyBibtex}
                    className="absolute top-3 right-3 inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white shadow-sm transition-all"
                  >
                    {bibtexCopied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{bibtexCopied ? 'Đã chép BibTeX' : 'Sao chép BibTeX'}</span>
                  </button>
                </div>
              )}
            </div>
          )}

        </div>
      )}
    </div>
  );
}
