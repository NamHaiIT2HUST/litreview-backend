import React, { useState } from 'react';
import { Quote, FileText, ChevronRight } from 'lucide-react';

export default function CitationChip({ citeId, citeObj, onClick, darkMode, children }) {
  const [showTooltip, setShowTooltip] = useState(false);

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
      onMouseEnter={() => setShowTooltip(true)}
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
          className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-3 w-[450px] md:w-[500px] animate-in fade-in zoom-in-95 slide-in-from-bottom-2 duration-200 ease-out cursor-default text-left whitespace-normal"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Glassmorphic Container */}
          <div className={`relative p-5 rounded-2xl shadow-2xl overflow-hidden border backdrop-blur-xl ${
            darkMode 
              ? 'bg-slate-900/95 border-slate-700/60 shadow-black/60' 
              : 'bg-white/95 border-slate-200/60 shadow-blue-900/10'
          }`}>
            {/* Title with Gradient */}
            <h4 className={`font-extrabold text-lg leading-snug line-clamp-2 bg-clip-text text-transparent bg-gradient-to-r ${
              darkMode ? 'from-blue-400 to-indigo-400' : 'from-blue-700 to-indigo-700'
            }`}>
              {title}
            </h4>

            {/* Subtitle */}
            <h5 className={`font-semibold text-[13px] uppercase tracking-wider mb-2 mt-4 ${
              darkMode ? 'text-slate-400' : 'text-slate-500'
            }`}>
              Relevant snippets from the paper
            </h5>
            
            {/* Elegant Divider */}
            <div className={`h-[1px] w-full mb-3 bg-gradient-to-r ${
              darkMode ? 'from-slate-700 via-slate-700/50 to-transparent' : 'from-slate-200 via-slate-200/50 to-transparent'
            }`}></div>
            
            {/* Snippet Content */}
            <div className={`mt-3 pl-4 border-l-2 py-1 ${
              darkMode ? 'border-blue-500/50' : 'border-blue-500'
            }`}>
              <p className={`text-[14px] leading-relaxed italic ${
                darkMode ? 'text-slate-300' : 'text-slate-700'
              }`}>
                "{snippet}"
              </p>
            </div>
            
            {/* Action Button */}
            <button
              onClick={onClick}
              className={`w-full mt-5 flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-bold transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] ${
                darkMode 
                  ? 'bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 border border-blue-500/20' 
                  : 'bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200/50'
              }`}
            >
              <span>Xem chi tiết PDF</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
          
          {/* Tooltip Arrow/Triangle */}
          <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 w-4 h-4 rotate-45 transform border-b border-r shadow-sm -z-10"
               style={{
                 backgroundColor: darkMode ? '#0f172a' : '#ffffff',
                 borderColor: darkMode ? 'rgba(51, 65, 85, 0.6)' : 'rgba(226, 232, 240, 0.6)'
               }}
          />
        </div>
      )}
    </div>
  );
}
