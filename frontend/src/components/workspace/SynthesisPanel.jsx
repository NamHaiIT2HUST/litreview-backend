import React, { useEffect, useMemo, useState } from 'react';
import { FileCheck2, Loader2, Play, RefreshCw, ShieldCheck } from 'lucide-react';

import {
  DEFAULT_PROJECT_ID,
  buildComparisonRows,
  buildReviewSections,
  buildSynthesisRequest,
  enrichCitation,
  tokenizeReviewCitations,
} from '../../utils/synthesis';
import { reviewScrollClass, sectionEvidenceLabel } from '../../utils/reviewPresentation';

const API_BASE = 'http://localhost:8000/api/v1';

export default function SynthesisPanel({ workspacePapers, setActiveCitation, darkMode }) {
  const [sessionId, setSessionId] = useState(null);
  const [status, setStatus] = useState('idle');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const canRun = workspacePapers.length > 0 && workspacePapers.length <= 15;

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
        throw new Error(data.detail || 'Không thể tạo synthesis session.');
      }
      setSessionId(data.session_id);
      setStatus(data.status || 'processing');
    } catch (err) {
      setStatus('failed');
      setError(err.message || 'Không thể bắt đầu synthesis.');
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
          throw new Error(data.detail || 'Không đọc được trạng thái synthesis.');
        }
        if (cancelled) return;
        setStatus(data.status);
        setResult(data);
        if (data.status === 'failed') {
          setError(data.error_message || 'Synthesis thất bại.');
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Lỗi khi kiểm tra synthesis session.');
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
    setActiveCitation({
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
    <div className={`p-6 rounded-3xl border shadow-sm space-y-5 ${darkMode ? 'bg-slate-900 border-slate-800 text-slate-100' : 'bg-white border-slate-200 text-slate-800'}`}>
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-600" />
            <h3 className="font-extrabold">Evidence-first Literature Synthesis</h3>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {workspacePapers.length} paper đã ingest • evidence → claim verification → outline → draft → citation resolver
          </p>
        </div>
        <button
          onClick={startSynthesis}
          disabled={!canRun || isRunning}
          className="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-bold"
        >
          {isRunning ? <Loader2 className="w-4 h-4 animate-spin" /> : result ? <RefreshCw className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          {isRunning ? 'Đang tổng hợp...' : result ? 'Chạy lại synthesis' : 'Tạo tổng quan nghiên cứu'}
        </button>
      </div>

      {!canRun && (
        <div className="text-xs p-3 rounded-xl bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-300">
          Synthesis yêu cầu 1–15 paper đã upload PDF và có provenance.
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
            Tổng quan đã kiểm chứng nguồn
          </div>
          {comparisonRows.length > 0 && (
            <div className="mb-7 overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-700">
              <table className="w-full min-w-[900px] text-xs text-left">
                <thead className="bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                  <tr>
                    <th className="p-3 font-bold">Tài liệu</th>
                    <th className="p-3 font-bold">Phương pháp</th>
                    <th className="p-3 font-bold">Dữ liệu</th>
                    <th className="p-3 font-bold">Kết quả chính</th>
                    <th className="p-3 font-bold">Hạn chế</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                  {comparisonRows.map((row) => (
                    <tr key={row.paperId} className="align-top bg-white dark:bg-slate-900/60">
                      <td className="p-3 font-bold min-w-[180px]">{row.title}</td>
                      {[row.method, row.dataset, row.findings, row.limitations].map((value, index) => (
                        <td key={index} className="p-3 leading-5 min-w-[170px] text-slate-600 dark:text-slate-300">
                          {value || <span className="italic text-amber-600 dark:text-amber-400">Chưa đủ bằng chứng</span>}
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
                <h4 className="font-extrabold text-base">{section.title}</h4>
                <span className={`text-[10px] font-bold px-2 py-1 rounded-full ${section.coverage?.status === 'sufficient' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
                  {sectionEvidenceLabel(section.coverage)}
                </span>
              </div>
              <p className="text-sm leading-8 text-justify">
                {section.sentences.map((sentence, index) => (
                  <React.Fragment key={`${section.id}-${index}`}>
                    <button
                      type="button"
                      onClick={(event) => openSentence(event, sentence)}
                      className={`inline text-left rounded px-0.5 transition-colors ${sentence.sentence_type === 'claim' ? 'hover:bg-blue-100 dark:hover:bg-blue-950/70 decoration-blue-400 underline decoration-dotted underline-offset-4' : 'hover:bg-violet-100 dark:hover:bg-violet-950/70'}`}
                      title={sentence.sentence_type === 'claim' ? 'Bấm để xác minh nguồn câu này' : 'Bấm để xem truy vết câu nối'}
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
                  title="Xem evidence gốc"
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
