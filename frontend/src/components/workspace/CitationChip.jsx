import React, { useState } from 'react';
import { Quote, FileText, ChevronRight, Calendar, BookOpen, ExternalLink } from 'lucide-react';

export default function CitationChip({ citeId, citeObj, onClick, darkMode, children }) {
  const [showTooltip, setShowTooltip] = useState(false);
  const [placement, setPlacement] = useState({ vertical: 'bottom', horizontal: 'center' });

  const handleMouseEnter = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const spaceAbove = rect.top;
    const spaceBelow = window.innerHeight - rect.bottom;
    const spaceRight = window.innerWidth - rect.right;

    // Prefer 'bottom' if space above is less than 300px, or if space below is larger
    const vertical = (spaceAbove > 320 && spaceBelow < 300) ? 'top' : 'bottom';

    // Prevent horizontal overflowing
    let horizontal = 'center';
    if (rect.left < 180) {
      horizontal = 'left';
    } else if (spaceRight < 180) {
      horizontal = 'right';
    }

    setPlacement({ vertical, horizontal });
    setShowTooltip(true);
  };

  // If we couldn't find the citation object, render a fallback badge
  if (!citeObj) {
    return (
      <button
        type="button"
        onClick={onClick}
        className="inline-flex items-center justify-center px-1.5 py-0.5 mx-0.5 rounded text-[11px] font-bold bg-blue-100/90 text-blue-700 hover:bg-blue-200 dark:bg-blue-900/60 dark:text-blue-300 dark:hover:bg-blue-800 transition-all shadow-xs"
      >
        {children || `[${citeId}]`}
      </button>
    );
  }

  const title = citeObj.paper_title || citeObj.title || 'Tài liệu nghiên cứu';
  const snippet = citeObj.snippet || citeObj.quoted_snippet || citeObj.quote || 'Đoạn trích dẫn được bóc tách từ bài báo.';
  const authors = citeObj.authors || citeObj.author || '';
  const year = citeObj.year || '';
  const venue = citeObj.journal || citeObj.venue || '';
  const page = citeObj.page_number || citeObj.page || '';

  // Position classes
  const vClass = placement.vertical === 'top' 
    ? 'bottom-full mb-2.5 slide-in-from-bottom-2' 
    : 'top-full mt-2.5 slide-in-from-top-2';

  const hClass = placement.horizontal === 'left'
    ? 'left-0 translate-x-0'
    : placement.horizontal === 'right'
    ? 'right-0 left-auto translate-x-0'
    : 'left-1/2 -translate-x-1/2';

  const arrowHClass = placement.horizontal === 'left'
    ? 'left-4 translate-x-0'
    : placement.horizontal === 'right'
    ? 'right-4 left-auto translate-x-0'
    : 'left-1/2 -translate-x-1/2';

  const arrowVClass = placement.vertical === 'top'
    ? '-bottom-1.5 border-b border-r'
    : '-top-1.5 border-t border-l';

  return (
    <span 
      className="inline-block relative group align-baseline"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <button
        type="button"
        onClick={onClick}
        className="inline-flex items-center justify-center px-1.5 py-0.5 mx-0.5 rounded-md text-[11px] font-semibold tracking-tight bg-blue-50 text-blue-700 hover:bg-blue-600 hover:text-white dark:bg-blue-950/80 dark:text-blue-300 dark:hover:bg-blue-600 dark:hover:text-white border border-blue-200/80 dark:border-blue-800/70 transition-all duration-150 shadow-2xs hover:shadow-xs active:scale-95 cursor-pointer align-baseline select-none"
        title={title}
      >
        <span className="opacity-70 font-mono text-[10px] mr-0.5">#</span>
        <span>{citeId}</span>
      </button>

      {/* Popover / Tooltip */}
      {showTooltip && (
        <div 
          className={`absolute z-50 w-[350px] max-w-[88vw] animate-in fade-in zoom-in-95 duration-150 ease-out cursor-default text-left whitespace-normal ${vClass} ${hClass}`}
          onClick={(e) => e.stopPropagation()}
        >
          <div className={`relative p-3.5 rounded-xl shadow-2xl overflow-hidden border backdrop-blur-md ${
            'bg-white/95 border-slate-200/90 shadow-slate-400/40 text-slate-800 dark:bg-slate-900/95 dark:border-slate-700/80 dark:shadow-black/80 dark:text-slate-100'
          }`}>
            {/* Header: Badge ID + Metadata */}
            <div className="flex items-center justify-between gap-2 mb-2">
              <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                'bg-blue-100 text-blue-800 border border-blue-200 dark:bg-blue-900/80 dark:text-blue-300 dark:border dark:border-blue-700/50'
              }`}>
                <Quote className="w-2.5 h-2.5" />
                Trích dẫn #{citeId}
              </span>
              {year && (
                <span className={`inline-flex items-center gap-1 text-[11px] font-medium ${
                  'text-slate-500 dark:text-slate-400'
                }`}>
                  <Calendar className="w-3 h-3" />
                  {year}
                </span>
              )}
            </div>

            {/* Paper Title */}
            <h4 className={`font-semibold text-[13px] leading-snug line-clamp-2 mb-1.5 ${
              'text-slate-900 dark:text-white'
            }`} title={title}>
              {title}
            </h4>

            {/* Authors & Venue */}
            {(authors || venue) && (
              <p className={`text-[11px] line-clamp-1 mb-2.5 ${
                'text-slate-500 dark:text-slate-400'
              }`}>
                {authors && <span>{authors}</span>}
                {authors && venue && <span> • </span>}
                {venue && <span className="italic">{venue}</span>}
              </p>
            )}
            
            {/* Verbatim Snippet Box */}
            <div className={`relative p-2.5 rounded-lg border text-[11.5px] leading-relaxed mb-3 ${
              'bg-amber-50/70 border-amber-200/80 text-slate-700 dark:bg-slate-800/80 dark:border-slate-700 dark:text-slate-300'
            }`}>
              <div className="flex items-start gap-1.5">
                <Quote className={`w-3 h-3 shrink-0 mt-0.5 ${
                  'text-amber-600 dark:text-amber-400'
                }`} />
                <p className="italic line-clamp-4 font-serif">
                  "{snippet}"
                </p>
              </div>
              {page && (
                <div className="text-right mt-1 text-[10px] opacity-75 font-mono">
                  Trang {page}
                </div>
              )}
            </div>
            
            {/* Action Button */}
            <button
              onClick={onClick}
              className={`w-full flex items-center justify-center gap-1.5 py-1.5 px-3 rounded-lg text-xs font-semibold transition-all duration-150 shadow-xs ${
                'bg-blue-600 hover:bg-blue-700 text-white dark:bg-blue-600 dark:hover:bg-blue-500 dark:text-white'
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Đối chiếu đoạn trích trong PDF</span>
              <ChevronRight className="w-3 h-3 ml-auto opacity-80" />
            </button>
          </div>
          
          {/* Tooltip Arrow */}
          <div className={`absolute w-3 h-3 rotate-45 transform -z-10 ${arrowHClass} ${arrowVClass}`}
             style={{
               backgroundColor: '#ffffff dark:#0f172a',
               borderColor: '#e2e8f0 dark:#334155'
             }}
          />
        </div>
      )}
    </span>
  );
}
