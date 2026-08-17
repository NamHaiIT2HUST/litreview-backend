import React, { useEffect, useMemo, useState } from 'react';
import { FileCheck2, Loader2, Play, RefreshCw, ShieldCheck, ChevronDown, History, Trash2, Plus } from 'lucide-react';

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

import { API_BASE } from '../../utils/apiConfig';

const formatSessionTime = (isoString) => {
  if (!isoString) return '';
  let clean = isoString;
  if (!clean.endsWith('Z') && !clean.includes('+') && !clean.includes('-')) {
    clean += 'Z';
  }
  const d = new Date(clean);
  return d.toLocaleString('vi-VN', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
};

export default function SynthesisPanel({ workspacePapers, setActiveCitation, darkMode }) {
  const { t } = useLanguage();
  const [sessionId, setSessionId] = useState(null);
  const [status, setStatus] = useState('idle');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [history, setHistory] = useState([]);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  const canRun = workspacePapers.length > 0 && workspacePapers.length <= 15;

  const fetchHistory = async (autoSelect = false) => {
    try {
      const response = await fetch(`${API_BASE}/projects/${DEFAULT_PROJECT_ID}/synthesis-sessions`);
      if (response.ok) {
        const data = await response.json();
        setHistory(data);
        if (autoSelect && data.length > 0) {
          const storedId = localStorage.getItem('litreview_active_synthesis_id');
          const sessionToLoad = data.find(s => s.id === storedId) || data[0];
          setSessionId(sessionToLoad.id);
          setStatus(sessionToLoad.status);
          localStorage.setItem('litreview_active_synthesis_id', sessionToLoad.id);
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
      const response = await fetch(`${API_BASE}/synthesis-sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildSynthesisRequest(workspacePapers, DEFAULT_PROJECT_ID)),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || t('synthesis.create_failed'));
      }
      setSessionId(data.session_id);
      setStatus(data.status || 'processing');
      localStorage.setItem('litreview_active_synthesis_id', data.session_id);
      fetchHistory(); // Refresh history
    } catch (err) {
      setStatus('failed');
      setError(err.message || t('synthesis.synthesis_failed'));
    }
  };

  const loadSession = (id) => {
    setSessionId(id);
    setStatus('processing'); // trigger the polling/fetching
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
    localStorage.removeItem('litreview_active_synthesis_id');
  };

  const deleteSession = async (id) => {
    if (!window.confirm("Bạn có chắc chắn muốn xóa phiên tổng hợp này không?")) return;
    try {
      const res = await fetch(`${API_BASE}/synthesis-sessions/${id}`, { method: 'DELETE' });
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
        const response = await fetch(`${API_BASE}/synthesis-sessions/${sessionId}`);
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || t('synthesis.read_failed'));
        }
        if (cancelled) return;
        setStatus(data.status);
        setResult(data);
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

  const isRunning = ['starting', 'processing'].includes(status);

  return (
    <div className={`flex-1 overflow-y-auto p-6 space-y-5 custom-scrollbar bg-transparent`}>
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-600" />
            <h3 className="font-extrabold">{t('synthesis.title')}</h3>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {workspacePapers.length} {t('synthesis.desc_pt1')}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {sessionId && (
            <button
              onClick={createNewSession}
              className={`inline-flex items-center gap-1.5 px-3 py-3 rounded-xl border transition-colors text-xs font-semibold ${
                darkMode
                  ? 'border-slate-700 hover:bg-slate-800 text-slate-300'
                  : 'border-slate-200 hover:bg-slate-100 text-slate-700'
              }`}
              title="Tạo phiên tổng hợp mới"
            >
              <Plus className="w-4 h-4" />
              <span>Phiên mới</span>
            </button>
          )}

          {history.length > 0 && (
            <div className="relative">
              <button
                onClick={() => setIsHistoryOpen(!isHistoryOpen)}
                className={`inline-flex items-center gap-2 px-3 py-3 rounded-xl border transition-colors text-xs font-semibold ${
                  darkMode
                    ? 'border-slate-700 hover:bg-slate-800 text-slate-300'
                    : 'border-slate-200 hover:bg-slate-100 text-slate-700'
                }`}
                title={t('synthesis.history_title') || 'Lịch sử phiên'}
              >
                <History className="w-4 h-4" />
                <ChevronDown className="w-3 h-3" />
              </button>
              
              {isHistoryOpen && (
                <div className={`absolute right-0 top-full mt-2 w-72 max-h-80 overflow-y-auto rounded-xl shadow-lg border z-50 ${
                  darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-slate-200'
                }`}>
                  <div className="p-2 space-y-1">
                    {history.map(session => (
                      <div
                        key={session.id}
                        onClick={() => loadSession(session.id)}
                        className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs transition-colors group cursor-pointer ${
                          sessionId === session.id
                            ? (darkMode ? 'bg-blue-900/40 text-blue-300' : 'bg-blue-50 text-blue-700')
                            : (darkMode ? 'hover:bg-slate-700/60 text-slate-300' : 'hover:bg-slate-100 text-slate-700')
                        }`}
                      >
                        <div className="flex-1 min-w-0 flex flex-col gap-1">
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-[11px] opacity-80">
                              {formatSessionTime(session.created_at)}
                            </span>
                            <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-bold uppercase shrink-0 ${
                              session.status === 'done' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-400' : 
                              session.status === 'failed' ? 'bg-red-100 text-red-700 dark:bg-red-950/60 dark:text-red-400' : 'bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-400'
                            }`}>
                              {session.status}
                            </span>
                          </div>
                          <span className="font-medium opacity-90 truncate">
                            {session.paper_count} tài liệu
                          </span>
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteSession(session.id);
                          }}
                          className="opacity-0 group-hover:opacity-100 ml-2 p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 transition-all shrink-0"
                          title="Xóa phiên tổng hợp này"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
          
          <button
            onClick={startSynthesis}
            disabled={!canRun || isRunning}
            className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-bold"
          >
            {isRunning ? <Loader2 className="w-4 h-4 animate-spin" /> : result ? <RefreshCw className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            {isRunning ? t('synthesis.btn_running') : result ? t('synthesis.btn_rerun') : t('synthesis.btn_start')}
          </button>
        </div>
      </div>

      {!canRun && (
        <div className="text-xs p-3 rounded-xl bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-300">
          {t('synthesis.req_msg')}
        </div>
      )}

      {sessionId && (
        <div className="text-xs font-mono text-slate-400">
          session: {sessionId} • status: {status}
        </div>
      )}

      {error && (
        <div className="p-3 rounded-xl bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-300 text-xs whitespace-pre-wrap">
          {error}
        </div>
      )}

      {(result?.review_markdown || reviewSections.length > 0) && status === 'done' && (
        <div className={`rounded-2xl border p-5 ${reviewScrollClass} ${darkMode ? 'bg-slate-950/40 border-slate-800' : 'bg-slate-50 border-slate-200'}`}>
          <div className="flex items-center gap-2 mb-4 text-sm font-bold">
            <FileCheck2 className="w-4 h-4 text-blue-600" />
            {t('synthesis.verified_overview')}
          </div>
          {comparisonRows.length > 0 && (
            <div className="mb-7 overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700">
              <table className="w-full min-w-[900px] text-xs text-left">
                <thead className="bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                  <tr>
                    <th className="p-3 font-bold">{t('synthesis.th_doc')}</th>
                    <th className="p-3 font-bold">{t('synthesis.th_method')}</th>
                    <th className="p-3 font-bold">{t('synthesis.th_data')}</th>
                    <th className="p-3 font-bold">{t('synthesis.th_findings')}</th>
                    <th className="p-3 font-bold">{t('synthesis.th_limits')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                  {comparisonRows.map((row) => (
                    <tr key={row.paperId} className="align-top bg-white dark:bg-slate-900/60">
                      <td className="p-3 font-bold min-w-[180px]">{row.title}</td>
                      {[row.method, row.dataset, row.findings, row.limitations].map((value, index) => (
                        <td key={index} className="p-3 leading-5 min-w-[170px] text-slate-600 dark:text-slate-300">
                          {value || <span className="italic text-amber-600 dark:text-amber-400">{t('synthesis.insufficient_evidence')}</span>}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {reviewSections.length > 0 ? reviewSections.map((section) => (
            <section key={section.id} className="mb-7 last:mb-0">
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <h4 className="font-bold text-[14px]">{section.title}</h4>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${section.coverage?.status === 'sufficient' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
                  {sectionEvidenceLabel(section.coverage)}
                </span>
              </div>
              <p className="text-[14px] leading-8 text-justify">
                {section.sentences.map((sentence, index) => (
                  <React.Fragment key={`${section.id}-${index}`}>
                    <button
                      type="button"
                      onClick={(event) => openSentence(event, sentence)}
                      className={`inline text-left rounded px-0.5 transition-colors ${sentence.sentence_type === 'claim' ? 'hover:bg-blue-100 dark:hover:bg-blue-950/70 decoration-blue-400 underline decoration-dotted underline-offset-4' : 'hover:bg-violet-100 dark:hover:bg-violet-950/70'}`}
                      title={sentence.sentence_type === 'claim' ? t('synthesis.click_verify') : t('synthesis.click_trace')}
                    >
                      {sentence.text}
                    </button>{' '}
                  </React.Fragment>
                ))}
              </p>
              {section.coverage?.reasons?.length > 0 && section.coverage.status !== 'sufficient' && (
                <p className="mt-2 text-xs text-amber-600">{section.coverage.reasons.join(' ')}</p>
              )}
            </section>
          )) : (
          <div className="text-sm leading-7 whitespace-pre-wrap">
            {reviewTokens.map((token, index) => (
              token.type === 'citation' ? (
                <button
                  key={`${token.citation.id}-${index}`}
                  onClick={() => openCitation(token.citation)}
                  className="mx-0.5 text-blue-600 dark:text-sky-400 font-extrabold hover:underline align-baseline"
                  title={t('synthesis.view_evidence')}
                >
                  {token.text}
                </button>
              ) : (
                <React.Fragment key={`text-${index}`}>{token.text}</React.Fragment>
              )
            ))}
          </div>)}
        </div>
      )}
    </div>
  );
}
