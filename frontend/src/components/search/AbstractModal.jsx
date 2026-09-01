import React, { useState } from 'react';
import { X, Copy, Check, FileText, ExternalLink, Award, BrainCircuit, BookOpen } from 'lucide-react';

export default function AbstractModal({ paper, onClose, darkMode }) {
  const [copied, setCopied] = useState(false);

  if (!paper) return null;

  const handleCopyAbstract = () => {
    navigator.clipboard.writeText(`Title: ${paper.title}\nAuthors: ${paper.authors}\nJournal: ${paper.journal} (${paper.year})\nAbstract: ${paper.abstract}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 bg-slate-950/70 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-200">
      <div 
        className={`rounded-3xl p-6 md:p-8 max-w-2xl w-full max-h-[90vh] flex flex-col shadow-2xl border transition-all ${
          'bg-white border-slate-200 text-slate-900 dark:bg-slate-900 dark:border-slate-800 dark:text-slate-100'
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header Bar */}
        <div className="flex items-start justify-between gap-4 border-b pb-4 border-slate-200 dark:border-slate-800 shrink-0">
          <div className="space-y-1.5 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="px-3 py-1 bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-sky-300 text-xs font-bold rounded-lg border border-blue-200 dark:border-blue-800">
                {paper.journal} ({paper.year})
              </span>
              <span className="px-2.5 py-0.5 bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 text-xs font-bold rounded-lg border border-amber-200 dark:border-amber-800 flex items-center gap-1">
                <Award className="w-3.5 h-3.5 text-amber-500" />
                <span>LitScore: {paper.litScore}/100</span>
              </span>
            </div>
            <h3 className="font-extrabold text-lg md:text-xl leading-snug">
              {paper.title}
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">
              Tác giả: {paper.authors}
            </p>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-2xl text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors shrink-0"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Content Body */}
        <div className="overflow-y-auto py-5 space-y-4 flex-1 pr-1 text-sm leading-relaxed scrollbar-thin">
          
          {/* AI TL;DR Banner if present */}
          {paper.tldr && (
            <div className="p-4 rounded-2xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/60">
              <div className="flex items-center gap-2 font-bold text-emerald-800 dark:text-emerald-300 text-xs uppercase tracking-wider mb-1">
                <BrainCircuit className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                <span>⚡ Tóm tắt siêu tốc (AI TL;DR)</span>
              </div>
              <p className="text-emerald-900 dark:text-emerald-200 font-medium text-xs md:text-sm">
                {paper.tldr.replace('TL;DR: ', '')}
              </p>
            </div>
          )}

          {/* Full Abstract Section */}
          <div className={`p-5 rounded-2xl border ${
            'bg-slate-50 border-slate-200 text-slate-800 dark:bg-slate-800/60 dark:border-slate-700/80 dark:text-slate-200'
          }`}>
            <div className="flex items-center justify-between mb-3 border-b pb-2 border-slate-200/60 dark:border-slate-700/60">
              <h4 className="font-bold text-xs uppercase tracking-wider text-blue-600 dark:text-sky-400 flex items-center gap-1.5">
                <BookOpen className="w-4 h-4" />
                <span>📝 Nội dung tóm tắt đầy đủ (Full Abstract)</span>
              </h4>
              <button
                onClick={handleCopyAbstract}
                className="text-xs font-bold text-slate-500 hover:text-blue-600 dark:hover:text-sky-400 flex items-center gap-1 transition-colors"
                title="Sao chép toàn bộ Abstract"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Đã chép' : 'Sao chép'}</span>
              </button>
            </div>
            
            <p className="text-xs md:text-sm leading-relaxed whitespace-pre-line font-normal">
              {paper.abstract}
            </p>
          </div>

          {/* Metadata Footer */}
          <div className="text-xs text-slate-500 dark:text-slate-400 space-y-1 font-mono pt-2">
            <p><strong>DOI:</strong> {paper.doi}</p>
            <p><strong>Trích dẫn:</strong> {paper.citations ? paper.citations.toLocaleString() : 0} lượt</p>
            <p><strong>Mã ID:</strong> {paper.id}</p>
          </div>
        </div>

        {/* Modal Action Buttons Footer */}
        <div className="flex items-center justify-between gap-3 border-t pt-4 border-slate-200 dark:border-slate-800 shrink-0">
          <button
            onClick={onClose}
            className={`px-5 py-2.5 rounded-2xl text-xs font-bold transition-all border ${
              'bg-slate-100 border-slate-200 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-700'
            }`}
          >
            Đóng lại
          </button>

          <a
            href={paper.url}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-2xl text-xs transition-all shadow-md"
          >
            <FileText className="w-4 h-4" />
            <span>Mở link bài gốc (PDF)</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        </div>
      </div>
    </div>
  );
}
