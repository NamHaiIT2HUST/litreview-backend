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
  const page = citeObj.page || citeObj.page_display || 'N/A';

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
          className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-80 shadow-xl rounded-2xl border overflow-hidden animate-in fade-in slide-in-from-bottom-2 duration-200 cursor-default text-left whitespace-normal"
          onClick={(e) => e.stopPropagation()}
        >
          <div className={`p-4 ${darkMode ? 'bg-slate-900 border-slate-700' : 'bg-white border-slate-200'}`}>
            <div className="flex gap-2 items-start mb-3">
              <div className="mt-1 p-1.5 bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400 rounded-lg shrink-0">
                <FileText className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <h4 className={`font-bold text-sm leading-snug line-clamp-2 ${darkMode ? 'text-slate-100' : 'text-slate-800'}`}>
                  {title}
                </h4>
                <p className={`text-xs mt-1 font-medium ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                  Trang {page}
                </p>
              </div>
            </div>
            
            <div className={`p-3 rounded-xl border relative ${darkMode ? 'bg-slate-800 border-slate-700' : 'bg-slate-50 border-slate-100'}`}>
              <Quote className={`absolute top-2 left-2 w-4 h-4 opacity-20 ${darkMode ? 'text-white' : 'text-black'}`} />
              <p className={`text-xs italic leading-relaxed pl-5 line-clamp-6 ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>
                "{snippet}"
              </p>
            </div>
            
            <button
              onClick={onClick}
              className={`w-full mt-3 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-xs font-bold transition-colors ${
                darkMode ? 'bg-slate-800 hover:bg-slate-700 text-blue-400' : 'bg-slate-100 hover:bg-slate-200 text-blue-600'
              }`}
            >
              <span>Xem chi tiết PDF</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
