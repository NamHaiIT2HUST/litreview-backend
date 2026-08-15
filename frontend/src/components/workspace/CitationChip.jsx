import React, { useState } from 'react';
import { Quote, FileText, ChevronRight } from 'lucide-react';

export default function CitationChip({ citeId, citeObj, onClick, darkMode, children }) {
  const [showTooltip, setShowTooltip] = useState(false);
  const [tooltipPos, setTooltipPos] = useState('top');

  const handleMouseEnter = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    if (rect.top < 250) {
      setTooltipPos('bottom');
    } else {
      setTooltipPos('top');
    }
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
        {children}
      </button>
    );
  }

  const title = citeObj.paper_title || 'Unknown Paper';
  const snippet = citeObj.snippet || 'Không có đoạn trích dẫn cụ thể.';

  return (
    <div 
      className="inline-block relative group align-middle"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <button
        type="button"
        onClick={onClick}
        className="inline-flex items-center gap-1 px-2 mx-1 rounded-full text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 dark:bg-blue-900/40 dark:text-blue-300 dark:border-blue-800/60 dark:hover:bg-blue-800/60 transition-all shadow-sm active:scale-95 whitespace-nowrap"
      >
        <span className="bg-blue-600 text-white dark:bg-blue-500 w-4 h-4 rounded-full flex items-center justify-center text-[9px] -ml-1 shadow-sm shrink-0">
          {citeId}
        </span>
        <span className="truncate max-w-[150px] leading-tight py-0.5 shrink-0">{title}</span>
      </button>

      {/* Popover / Tooltip */}
      {showTooltip && (
        <div 
          className={`absolute z-50 left-1/2 -translate-x-1/2 w-[320px] animate-in fade-in zoom-in-95 duration-200 ease-out cursor-default text-left whitespace-normal ${
            tooltipPos === 'top' 
              ? 'bottom-full mb-2 slide-in-from-bottom-2' 
              : 'top-full mt-2 slide-in-from-top-2'
          }`}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Premium Container matching theme */}
          <div className={`relative p-3.5 rounded-xl shadow-xl overflow-hidden border ${
            darkMode 
              ? 'bg-slate-900 border-slate-700 shadow-black/60' 
              : 'bg-white border-slate-200 shadow-slate-300/60'
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
          <div className={`absolute left-1/2 -translate-x-1/2 w-3 h-3 rotate-45 transform -z-10 ${
            tooltipPos === 'top' 
              ? '-bottom-1.5 border-b border-r' 
              : '-top-1.5 border-t border-l'
            }`}
             style={{
               backgroundColor: darkMode ? '#0f172a' : '#ffffff', // slate-900 or white
               borderColor: darkMode ? '#334155' : '#e2e8f0'      // slate-700 or slate-200
             }}
          />
        </div>
      )}
    </div>
  );
}
