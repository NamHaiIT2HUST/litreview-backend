import React, { useState } from 'react';
import { useLanguage } from '../../contexts/LanguageContext';
import {
  ExternalLink, FileText, Copy, Check, Quote, PlusCircle,
  CheckCircle2, Sparkles, GitFork, BookOpen, Award,
  ChevronDown, ChevronUp, Users, CalendarDays
} from 'lucide-react';

// ─── Scopus Status Badge ──────────────────────────────────────────────────────
function ScopusBadge({ status, quartile }) {
  if (!status || status === 'undetermined') return null;
  if (status === 'indexed') {
    return (
      <span className="badge badge-success gap-1">
        <CheckCircle2 className="w-2.5 h-2.5" />
        {quartile ? `Q${quartile}` : 'Scopus'}
      </span>
    );
  }
  if (status === 'not_indexed') {
    return <span className="badge badge-neutral">Not indexed</span>;
  }
  return null;
}

// ─── Open Access Badge ────────────────────────────────────────────────────────
function OABadge({ oaStatus }) {
  if (!oaStatus || oaStatus === 'undetermined') return null;
  if (oaStatus === 'open') {
    return <span className="badge badge-success">Open Access</span>;
  }
  return null;
}

// ─── Paper Card ───────────────────────────────────────────────────────────────
function PaperCard({ paper, isSelected, onToggle, onOpenAiScreening, onOpenGenealogy, copiedDoi, onCopyDoi }) {
  const { t } = useLanguage();
  const [expanded, setExpanded] = useState(false);

  const scopusStatus = paper.scopus_status || paper.scopusStatus;
  const quartile = paper.scopus_quartile;
  const oaStatus = paper.oa_status;
  const hasTldr = Boolean(paper.tldr);

  return (
    <div
      className={`card relative transition-all duration-200 overflow-hidden ${
        isSelected
          ? 'border-primary-300 dark:border-primary-700 bg-primary-50/50 dark:bg-primary-950/20'
          : 'hover:border-surface-300 dark:hover:border-surface-600'
      }`}
    >
      {/* Selection indicator bar */}
      {isSelected && (
        <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-primary-500 rounded-r" />
      )}

      <div className="p-5">
        {/* ── Header Row ───────────────────────────────────────────────── */}
        <div className="flex items-start gap-3">
          {/* Checkbox */}
          <button
            type="button"
            onClick={() => onToggle(paper.id)}
            className={`flex-shrink-0 mt-0.5 w-4.5 h-4.5 rounded border-2 flex items-center justify-center transition-all ${
              isSelected
                ? 'bg-primary-600 border-primary-600'
                : 'border-surface-300 dark:border-surface-600 hover:border-primary-400'
            }`}
          >
            {isSelected && <Check className="w-3 h-3 text-white stroke-[3]" />}
          </button>

          {/* Content */}
          <div className="flex-1 min-w-0">
            {/* Title + Link */}
            <div className="flex items-start gap-2 mb-2">
              <h3 className="font-semibold text-sm text-surface-900 dark:text-white leading-snug flex-1">
                {paper.title || 'Untitled Paper'}
              </h3>
              {paper.url && paper.url !== '#' && (
                <a
                  href={paper.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-shrink-0 p-1 rounded text-surface-400 hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
                  onClick={e => e.stopPropagation()}
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              )}
            </div>

            {/* Meta row */}
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-surface-500 dark:text-surface-400 mb-3">
              {paper.authors && (
                <span className="flex items-center gap-1">
                  <Users className="w-3 h-3" />
                  <span className="truncate max-w-[200px]">{paper.authors}</span>
                </span>
              )}
              {paper.year && (
                <span className="flex items-center gap-1">
                  <CalendarDays className="w-3 h-3" />
                  {paper.year}
                </span>
              )}
              {paper.journal && (
                <span className="flex items-center gap-1 italic truncate max-w-[180px]">
                  <BookOpen className="w-3 h-3 flex-shrink-0" />
                  {paper.journal}
                </span>
              )}
            </div>

            {/* Badges */}
            <div className="flex flex-wrap items-center gap-1.5 mb-3">
              {paper.citations != null && paper.citations > 0 && (
                <span className="badge badge-neutral">
                  <Quote className="w-2.5 h-2.5" />
                  {paper.citations.toLocaleString()}
                </span>
              )}
              <ScopusBadge status={scopusStatus} quartile={quartile} />
              <OABadge oaStatus={oaStatus} />
              {hasTldr && (
                <span className="badge" style={{ background: '#EEF2FF', color: '#4338CA' }}>
                  <Sparkles className="w-2.5 h-2.5" />
                  AI Summary
                </span>
              )}
            </div>

            {/* Abstract / TL;DR */}
            {(paper.abstract || hasTldr) && (
              <div>
                {/* TL;DR */}
                {hasTldr && (
                  <div className="mb-2 p-2.5 rounded-lg bg-primary-50 dark:bg-primary-950/30 border border-primary-100 dark:border-primary-900">
                    <p className="text-xs text-primary-800 dark:text-primary-200 leading-relaxed">
                      <span className="font-bold text-primary-600 dark:text-primary-400 mr-1">TL;DR</span>
                      {paper.tldr}
                    </p>
                  </div>
                )}

                {/* Abstract expandable */}
                {paper.abstract && (
                  <div>
                    <p className={`text-xs text-surface-500 dark:text-surface-400 leading-relaxed ${!expanded ? 'line-clamp-2' : ''}`}>
                      {paper.abstract}
                    </p>
                    <button
                      type="button"
                      onClick={() => setExpanded(!expanded)}
                      className="mt-1 flex items-center gap-1 text-[11px] font-semibold text-primary-600 dark:text-primary-400 hover:underline"
                    >
                      {expanded ? (
                        <><ChevronUp className="w-3 h-3" />{t('search.see_less') || 'See less'}</>
                      ) : (
                        <><ChevronDown className="w-3 h-3" />{t('search.see_more') || 'See more'}</>
                      )}
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* ── Footer Actions ────────────────────────────────────────────── */}
        <div className="flex flex-wrap items-center justify-between gap-2 mt-3 pt-3 border-t border-surface-100 dark:border-surface-800">
          {/* DOI */}
          <div className="flex items-center gap-1.5 text-[11px] text-surface-400 font-mono">
            {paper.doi && paper.doi !== 'N/A' ? (
              <button
                type="button"
                onClick={() => onCopyDoi(paper.doi)}
                className="flex items-center gap-1 hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
              >
                {copiedDoi === paper.doi ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
                <span className="max-w-[140px] xs:max-w-[180px] sm:max-w-[220px] truncate">{paper.doi}</span>
              </button>
            ) : (
              <span>No DOI</span>
            )}
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-1.5">
            {onOpenGenealogy && (
              <button
                type="button"
                onClick={() => onOpenGenealogy(paper)}
                className="btn btn-sm btn-ghost text-xs py-1 px-2"
                title="Citation genealogy"
              >
                <GitFork className="w-3 h-3" />
              </button>
            )}
            {onOpenAiScreening && (
              <button
                type="button"
                onClick={() => onOpenAiScreening(paper)}
                className="btn btn-sm btn-ghost text-xs py-1 px-2 text-primary-600 dark:text-primary-400"
                title="AI screening"
              >
                <Sparkles className="w-3 h-3" />
              </button>
            )}
            <button
              type="button"
              onClick={() => onToggle(paper.id)}
              className={`btn btn-sm text-xs py-1 px-3 ${
                isSelected
                  ? 'bg-primary-600 text-white'
                  : 'btn-secondary'
              }`}
            >
              {isSelected ? (
                <><Check className="w-3 h-3" /> {t('search.btn_selected') || 'Selected'}</>
              ) : (
                <><PlusCircle className="w-3 h-3" /> {t('search.btn_select') || 'Select'}</>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Table Row (compact list view) ───────────────────────────────────────────
function PaperRow({ paper, isSelected, onToggle, copiedDoi, onCopyDoi, onOpenAiScreening }) {
  const scopusStatus = paper.scopus_status || paper.scopusStatus;
  const quartile = paper.scopus_quartile;

  return (
    <tr
      className={`border-b border-surface-100 dark:border-surface-800 hover:bg-surface-50 dark:hover:bg-surface-800/50 transition-colors ${
        isSelected ? 'bg-primary-50/50 dark:bg-primary-950/20' : ''
      }`}
    >
      <td className="pl-4 pr-2 py-3 w-10">
        <button
          type="button"
          onClick={() => onToggle(paper.id)}
          className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-all ${
            isSelected
              ? 'bg-primary-600 border-primary-600'
              : 'border-surface-300 dark:border-surface-600 hover:border-primary-400'
          }`}
        >
          {isSelected && <Check className="w-2.5 h-2.5 text-white stroke-[3]" />}
        </button>
      </td>
      <td className="px-3 py-3">
        <div className="flex flex-col gap-0.5">
          <span className="text-sm font-medium text-surface-900 dark:text-white line-clamp-1">
            {paper.title}
          </span>
          <span className="text-xs text-surface-400 line-clamp-1">{paper.authors}</span>
        </div>
      </td>
      <td className="px-3 py-3 text-xs text-surface-500 whitespace-nowrap">{paper.year}</td>
      <td className="px-3 py-3">
        <div className="flex items-center gap-1">
          <ScopusBadge status={scopusStatus} quartile={quartile} />
        </div>
      </td>
      <td className="px-3 py-3 text-xs text-surface-500 text-right font-mono">{paper.citations ?? '—'}</td>
      <td className="px-3 py-3 text-right">
        <div className="flex items-center justify-end gap-1">
          {paper.url && paper.url !== '#' && (
            <a href={paper.url} target="_blank" rel="noopener noreferrer"
              className="p-1 rounded text-surface-400 hover:text-primary-600 dark:hover:text-primary-400">
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}
          {onOpenAiScreening && (
            <button type="button" onClick={() => onOpenAiScreening(paper)}
              className="p-1 rounded text-surface-400 hover:text-primary-600 dark:hover:text-primary-400">
              <Sparkles className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </td>
    </tr>
  );
}

// ─── Main PaperTable Component ────────────────────────────────────────────────
export default function PaperTable({ papers, selectedPaperIds, toggleSelectPaper, onOpenAiScreening, onOpenGenealogy, viewMode = 'grid' }) {
  const { t } = useLanguage();
  const [copiedDoi, setCopiedDoi] = useState(null);

  const handleCopyDoi = (doi) => {
    if (!doi || doi === 'N/A') return;
    navigator.clipboard.writeText(doi);
    setCopiedDoi(doi);
    setTimeout(() => setCopiedDoi(null), 2000);
  };

  const allSelected = papers.length > 0 && papers.every(p => selectedPaperIds.includes(p.id));
  const handleToggleAll = () => {
    if (allSelected) {
      papers.forEach(p => { if (selectedPaperIds.includes(p.id)) toggleSelectPaper(p.id); });
    } else {
      papers.forEach(p => { if (!selectedPaperIds.includes(p.id)) toggleSelectPaper(p.id); });
    }
  };

  if (papers.length === 0) {
    return (
      <div className="card flex flex-col items-center justify-center py-20 px-6 text-center">
        <div className="w-16 h-16 rounded-2xl bg-surface-100 dark:bg-surface-800 flex items-center justify-center mb-4">
          <FileText className="w-8 h-8 text-surface-400" />
        </div>
        <p className="font-display font-semibold text-surface-700 dark:text-surface-300 mb-1">
          {t('search.table_no_papers') || 'No papers found'}
        </p>
        <p className="text-sm text-surface-400">
          {t('search.table_no_papers_hint') || 'Try searching with different keywords.'}
        </p>
      </div>
    );
  }

  if (viewMode === 'table') {
    return (
      <div className="card overflow-hidden">
        <div className="overflow-x-auto touch-pan-x custom-scrollbar">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-surface-50 dark:bg-surface-800 border-b border-surface-200 dark:border-surface-700">
                <th className="pl-4 pr-2 py-3 w-10">
                  <button
                    type="button"
                    onClick={handleToggleAll}
                    className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-all ${
                      allSelected ? 'bg-primary-600 border-primary-600' : 'border-surface-300 dark:border-surface-600'
                    }`}
                  >
                    {allSelected && <Check className="w-2.5 h-2.5 text-white stroke-[3]" />}
                  </button>
                </th>
                <th className="px-3 py-3 text-left section-label">{t('search.table_th_title') || 'Title'}</th>
                <th className="px-3 py-3 text-left section-label">Year</th>
                <th className="px-3 py-3 text-left section-label">Status</th>
                <th className="px-3 py-3 text-right section-label">{t('search.table_th_citations') || 'Cites'}</th>
                <th className="px-3 py-3 text-right section-label w-20">{t('search.table_th_actions') || 'Actions'}</th>
              </tr>
            </thead>
            <tbody>
              {papers.map(paper => (
                <PaperRow
                  key={paper.id}
                  paper={paper}
                  isSelected={selectedPaperIds.includes(paper.id)}
                  onToggle={toggleSelectPaper}
                  copiedDoi={copiedDoi}
                  onCopyDoi={handleCopyDoi}
                  onOpenAiScreening={onOpenAiScreening}
                />
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  // Grid view (default)
  return (
    <div className="space-y-3">
      {/* Select all bar */}
      <div className="flex items-center justify-between text-sm">
        <label className="flex items-center gap-2 cursor-pointer text-surface-600 dark:text-surface-400 font-medium select-none">
          <button
            type="button"
            onClick={handleToggleAll}
            className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-all ${
              allSelected ? 'bg-primary-600 border-primary-600' : 'border-surface-300 dark:border-surface-600 hover:border-primary-400'
            }`}
          >
            {allSelected && <Check className="w-2.5 h-2.5 text-white stroke-[3]" />}
          </button>
          {allSelected ? 'Deselect all' : 'Select all'}
        </label>
        {selectedPaperIds.length > 0 && (
          <span className="badge badge-primary">
            {selectedPaperIds.length} selected
          </span>
        )}
      </div>

      {/* Cards */}
      <div className="grid grid-cols-1 gap-3">
        {papers.map(paper => (
          <PaperCard
            key={paper.id}
            paper={paper}
            isSelected={selectedPaperIds.includes(paper.id)}
            onToggle={toggleSelectPaper}
            onOpenAiScreening={onOpenAiScreening}
            onOpenGenealogy={onOpenGenealogy}
            copiedDoi={copiedDoi}
            onCopyDoi={handleCopyDoi}
          />
        ))}
      </div>
    </div>
  );
}
