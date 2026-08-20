import React, { useState } from 'react';
import { Quote, FileText, ChevronRight } from 'lucide-react';

export default function CitationChip({ citeId, citeObj, onClick, darkMode, children }) {
  const [showTooltip, setShowTooltip] = useState(false);
  const [placement, setPlacement] = useState({ vertical: 'bottom', horizontal: 'center' });

  const handleMouseEnter = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const spaceAbove = rect.top;
    const spaceBelow = window.innerHeight - rect.bottom;
    const spaceRight = window.innerWidth - rect.right;

    // Prefer 'bottom' if space above is less than 300px, or if space below is larger
    const vertical = (spaceAbove > 300 && spaceBelow < 280) ? 'top' : 'bottom';

    // Prevent horizontal overflowing
    let horizontal = 'center';
    if (rect.left < 160) {
      horizontal = 'left';
    } else if (spaceRight < 160) {
      horizontal = 'right';
    }

    setPlacement({ vertical, horizontal });
    setShowTooltip(true);
  };

  // If we couldn't find the citation object, just render a fallback button
  if (!citeObj) {
    return (
      <button
        type="button"
        onClick={onClick}
        className="inline-flex items-center justify-center px-1.5 mx-0.5 rounded text-[11px] font-bold bg-blue-100 text-blue-700 hover:bg-blue-200 dark:bg-blue-900/60 dark:text-blue-300 dark:hover:bg-blue-800 transition-colors shadow-sm"
      >
        {children || `[${citeId}]`}
      </button>
    );
  }

  const title = citeObj.paper_title || 'Unknown Paper';
  const snippet = citeObj.snippet || 'Không có đoạn trích dẫn cụ thể.';

  // Position classes
  const vClass = placement.vertical === 'top' 
    ? 'bottom-full mb-2 slide-in-from-bottom-2' 
    : 'top-full mt-2 slide-in-from-top-2';

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
    <div 
      className="inline-block relative group align-middle"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <button
        type="button"
        onClick={onClick}
        className="inline-flex items-center justify-center px-1.5 py-0.5 mx-0.5 rounded text-[11px] font-bold bg-blue-100/90 text-blue-700 hover:bg-blue-200 dark:bg-blue-900/60 dark:text-blue-300 dark:hover:bg-blue-800 border border-blue-200/80 dark:border-blue-800/60 transition-all shadow-xs active:scale-95 cursor-pointer align-baseline select-none"
        title={title}
      >
        [{citeId}]
      </button>

      {/* Popover / Tooltip */}
      {showTooltip && (
        <div 
          className={`absolute z-50 w-[320px] max-w-[85vw] animate-in fade-in zoom-in-95 duration-150 ease-out cursor-default text-left whitespace-normal ${vClass} ${hClass}`}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Container matching theme */}
          <div className={`relative p-3.5 rounded-xl shadow-2xl overflow-hidden border ${
            darkMode 
              ? 'bg-slate-900 border-slate-700 shadow-black/80' 
              : 'bg-white border-slate-200 shadow-slate-400/50'
          }`}>
            {/* Title */}
            <h4 className={`font-bold text-[13px] leading-snug line-clamp-2 mb-2 ${
              darkMode ? 'text-white' : 'text-slate-800'
            }`} title={title}>
              {title}
            </h4>
            
            {/* Snippet Content */}
            <div className={`pl-3 border-l-2 py-0.5 ${
              darkMode ? 'border-blue-500' : 'border-blue-400'
            }`}>
              <p className={`text-[12px] leading-relaxed italic line-clamp-4 ${
                darkMode ? 'text-slate-300' : 'text-slate-600'
              }`}>
                "{snippet}"
              </p>
            </div>
            
            {/* Action Button */}
            <button
              onClick={onClick}
              className={`w-full mt-3 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-xs font-bold transition-all duration-200 shadow-sm ${
                darkMode 
                  ? 'bg-blue-600 hover:bg-blue-500 text-white' 
                  : 'bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200/50'
              }`}
            >
              <span>Xem chi tiết PDF</span>
              <ChevronRight className="w-3 h-3" />
            </button>
          </div>
          
          {/* Tooltip Arrow/Triangle */}
          <div className={`absolute w-3 h-3 rotate-45 transform -z-10 ${arrowHClass} ${arrowVClass}`}
             style={{
               backgroundColor: darkMode ? '#0f172a' : '#ffffff',
               borderColor: darkMode ? '#334155' : '#e2e8f0'
             }}
          />
        </div>
      )}
    </div>
  );
}
