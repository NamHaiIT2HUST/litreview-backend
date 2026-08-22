import React, { useState } from 'react';
import { 
  ShieldCheck, 
  AlertTriangle, 
  XCircle, 
  CheckCircle2, 
  ChevronDown, 
  ChevronUp, 
  FileText, 
  Search,
  Sparkles,
  Info,
  ExternalLink
} from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';

/**
 * RAGVerificationBadge — ASTA-Bench & PaperQA2 Inspired Quality & Hallucination Auditor.
 * Renders an interactive verification pill on AI answers in Chat and Synthesis panels.
 */
export default function RAGVerificationBadge({ guardrail, citations = [], darkMode = false }) {
  const { t, language } = useLanguage();
  const isEn = language === 'en';
  const [isOpen, setIsOpen] = useState(false);

  if (!guardrail) return null;

  const {
    safety_verdict,
    faithfulness_score = 1.0,
    hallucination_rate = 0.0,
    citation_precision = 1.0,
    total_claims = 0,
    attributable_claims_count = 0,
    extrapolatory_claims_count = 0,
    contradictory_claims_count = 0,
    claims = [],
    summary_verdict,
  } = guardrail;

  const faithfulnessPct = Math.round((faithfulness_score || 0) * 100);
  const hallucinationPct = Math.round((hallucination_rate || 0) * 100);

  // Verdict style & colors
  const isSafe = safety_verdict === 'VERIFIED_HIGH_CONFIDENCE' || safety_verdict === 'REFUSAL_GROUNDED';
  const isWarning = safety_verdict === 'PARTIALLY_GROUNDED';
  const isDanger = safety_verdict === 'HIGH_HALLUCINATION_RISK' || safety_verdict === 'INPUT_GUARDRAIL_BLOCKED';

  const badgeBg = isSafe
    ? 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300'
    : isWarning
    ? 'bg-amber-50 dark:bg-amber-950/40 border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-300'
    : 'bg-rose-50 dark:bg-rose-950/40 border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300';

  const badgeIcon = isSafe ? (
    <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
  ) : isWarning ? (
    <AlertTriangle className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
  ) : (
    <XCircle className="w-3.5 h-3.5 text-rose-600 dark:text-rose-400" />
  );

  const getStatusBadge = (status) => {
    switch (status) {
      case 'Attributable':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300 flex items-center gap-1 shrink-0">
            <CheckCircle2 className="w-2.5 h-2.5" />
            {isEn ? 'Attributable' : 'Có căn cứ'}
          </span>
        );
      case 'Contradictory':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 dark:bg-rose-900/50 text-rose-700 dark:text-rose-300 flex items-center gap-1 shrink-0">
            <XCircle className="w-2.5 h-2.5" />
            {isEn ? 'Contradictory' : 'Mâu thuẫn'}
          </span>
        );
      case 'Extrapolatory':
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300 flex items-center gap-1 shrink-0">
            <AlertTriangle className="w-2.5 h-2.5" />
            {isEn ? 'Extrapolatory' : 'Suy diễn / Ảo giác'}
          </span>
        );
    }
  };

  return (
    <div className="mt-3 pt-2.5 border-t dark:border-slate-800/80 border-slate-100 text-xs">
      {/* Top Banner Badge */}
      <div 
        onClick={() => setIsOpen(!isOpen)}
        className={`flex flex-wrap items-center justify-between gap-2 px-3 py-2 rounded-xl border cursor-pointer select-none transition-all shadow-xs ${badgeBg}`}
      >
        <div className="flex items-center gap-2">
          {badgeIcon}
          <span className="font-bold text-[11.5px]">
            {isEn ? 'RAG Quality & Guardrail:' : 'Kiểm định RAG & Chống ảo giác:'}
          </span>
          <span className="font-semibold text-[11px] opacity-90 truncate max-w-[280px] sm:max-w-md">
            {summary_verdict}
          </span>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <div className="flex items-center gap-2 text-[10.5px] font-mono font-bold">
            <span className="px-1.5 py-0.5 rounded bg-black/5 dark:bg-white/5">
              Faithfulness: {faithfulnessPct}%
            </span>
            {hallucinationPct > 0 && (
              <span className="px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-600 dark:text-rose-400">
                Hallucination: {hallucinationPct}%
              </span>
            )}
          </div>
          <button 
            type="button"
            className="p-0.5 hover:bg-black/5 dark:hover:bg-white/10 rounded transition-colors"
          >
            {isOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Expandable Audit Drawer */}
      {isOpen && (
        <div className={`mt-2.5 p-4 rounded-2xl border transition-all animate-in fade-in-50 duration-200 ${
          darkMode ? 'bg-slate-900/95 border-slate-800 shadow-md' : 'bg-slate-50 border-slate-200 shadow-xs'
        }`}>
          {/* Header metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4">
            <div className={`p-2.5 rounded-xl border ${darkMode ? 'bg-slate-800/60 border-slate-700' : 'bg-white border-slate-200'}`}>
              <div className="text-[10px] text-slate-400 font-semibold">{isEn ? 'Total Claims' : 'Tổng số luận điểm'}</div>
              <div className="text-base font-extrabold text-slate-700 dark:text-slate-200 mt-0.5">{total_claims}</div>
            </div>
            <div className={`p-2.5 rounded-xl border ${darkMode ? 'bg-slate-800/60 border-slate-700' : 'bg-white border-slate-200'}`}>
              <div className="text-[10px] text-emerald-500 font-semibold">{isEn ? 'Attributable' : 'Có căn cứ xác thực'}</div>
              <div className="text-base font-extrabold text-emerald-600 dark:text-emerald-400 mt-0.5">{attributable_claims_count}</div>
            </div>
            <div className={`p-2.5 rounded-xl border ${darkMode ? 'bg-slate-800/60 border-slate-700' : 'bg-white border-slate-200'}`}>
              <div className="text-[10px] text-amber-500 font-semibold">{isEn ? 'Extrapolatory' : 'Suy diễn / Chưa rõ'}</div>
              <div className="text-base font-extrabold text-amber-600 dark:text-amber-400 mt-0.5">{extrapolatory_claims_count}</div>
            </div>
            <div className={`p-2.5 rounded-xl border ${darkMode ? 'bg-slate-800/60 border-slate-700' : 'bg-white border-slate-200'}`}>
              <div className="text-[10px] text-blue-500 font-semibold">{isEn ? 'Citation Precision' : 'Độ chính xác trích dẫn'}</div>
              <div className="text-base font-extrabold text-blue-600 dark:text-blue-400 mt-0.5">{Math.round(citation_precision * 100)}%</div>
            </div>
          </div>

          {/* Claim-by-claim breakdown */}
          <div className="space-y-3">
            <h5 className="text-[11px] font-extrabold text-slate-600 dark:text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-blue-500" />
              <span>{isEn ? 'Claim-level Attribution Audit' : 'Chi tiết kiểm định nguồn từng luận điểm'}</span>
            </h5>

            {claims.length === 0 ? (
              <p className="text-xs text-slate-400 italic">{isEn ? 'No claim breakdown available.' : 'Không có chi tiết luận điểm.'}</p>
            ) : (
              claims.map((claim, cIdx) => (
                <div 
                  key={cIdx} 
                  className={`p-3 rounded-xl border transition-all ${
                    darkMode ? 'bg-slate-800/40 border-slate-800' : 'bg-white border-slate-200/80 shadow-xs'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-[12.5px] font-medium leading-relaxed text-slate-800 dark:text-slate-200 flex-1">
                      {claim.sentence}
                    </p>
                    {getStatusBadge(claim.status)}
                  </div>

                  {claim.supporting_excerpt && (
                    <div className="mt-2 pl-2.5 border-l-2 border-blue-500/60 text-[11px] text-slate-500 dark:text-slate-400 leading-normal bg-blue-50/30 dark:bg-blue-950/20 py-1 pr-2 rounded-r">
                      <span className="font-bold text-blue-600 dark:text-blue-400 mr-1">
                        {isEn ? 'Supporting Excerpt:' : 'Trích đoạn nguồn:'}
                      </span>
                      "{claim.supporting_excerpt}"
                    </div>
                  )}

                  <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-[10.5px] text-slate-400">
                    <div className="flex items-center gap-2">
                      {claim.paper_title && (
                        <span className="truncate max-w-[240px] font-medium text-slate-600 dark:text-slate-300">
                          📄 {claim.paper_title} {claim.page ? `(Trang ${claim.page})` : ''}
                        </span>
                      )}
                      {claim.citation_keys && claim.citation_keys.length > 0 && (
                        <span className="font-mono text-blue-600 dark:text-blue-400 font-bold">
                          [{claim.citation_keys.join(', ')}]
                        </span>
                      )}
                    </div>
                    {claim.reasoning && (
                      <span className="italic text-slate-500">
                        {claim.reasoning}
                      </span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
