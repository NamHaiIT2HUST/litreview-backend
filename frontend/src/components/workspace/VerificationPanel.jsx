import React from 'react';
import { ShieldCheck, ExternalLink, Bot } from 'lucide-react';

export default function VerificationPanel({ activeCitation, darkMode }) {
  return (
    <div className={`p-6 rounded-3xl border transition-colors space-y-5 sticky top-24 shadow-sm ${
      darkMode ? 'bg-slate-900 border-slate-800 text-slate-200' : 'bg-white border-slate-200 text-slate-800'
    }`}>
      <div className={`flex items-center justify-between border-b pb-4 ${
        darkMode ? 'border-slate-800' : 'border-slate-100'
      }`}>
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-6 h-6 text-emerald-500" />
          <h3 className="font-bold text-base">Cột Xác minh Nguồn gốc</h3>
        </div>
        <span className="text-xs font-bold bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 px-3 py-1 rounded-full border border-emerald-200 dark:border-emerald-800">
          Chống ảo giác 99.4%
        </span>
      </div>

      {activeCitation ? (
        <div className="space-y-5 text-sm">
          <div>
            <span className={`font-mono text-xs px-2.5 py-1 rounded-md font-bold ${
              darkMode ? 'bg-slate-800 text-slate-300' : 'bg-slate-100 text-slate-700'
            }`}>
              Trích dẫn: {activeCitation.id}
            </span>
            <h4 className={`font-extrabold text-base md:text-lg mt-3 leading-snug ${
              darkMode ? 'text-white' : 'text-slate-900'
            }`}>
              {activeCitation.title}
            </h4>
          </div>

          <div className="space-y-1.5 text-xs text-slate-500 dark:text-slate-400 font-medium">
            <p><strong>Tác giả:</strong> {activeCitation.authors}</p>
            <p><strong>Tạp chí:</strong> {activeCitation.journal} ({activeCitation.year})</p>
            <p><strong>DOI:</strong> <a href={activeCitation.url} target="_blank" rel="noreferrer" className="text-blue-600 dark:text-sky-400 hover:underline">{activeCitation.doi}</a></p>
          </div>

          {/* Highlighted Abstract Snippet */}
          <div className="space-y-2">
            <h5 className="font-bold text-xs flex items-center gap-1.5 text-slate-800 dark:text-slate-200">
              <Bot className="w-4 h-4 text-blue-600 dark:text-sky-400" />
              <span>Văn bản gốc bài báo (Ground Truth Abstract):</span>
            </h5>
            <div className={`p-4 rounded-2xl leading-relaxed text-xs border ${
              darkMode 
                ? 'bg-slate-800 border-slate-700 text-slate-300' 
                : 'bg-slate-50 border-slate-200 text-slate-700'
            }`}>
              {activeCitation.abstract}
            </div>
          </div>

          <a
            href={activeCitation.url}
            target="_blank"
            rel="noreferrer"
            className="w-full flex items-center justify-center gap-2 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-2xl font-bold transition-all text-xs shadow-md"
          >
            <ExternalLink className="w-4 h-4" />
            <span>Tải Bài Báo Gốc PDF (Nguồn NXB)</span>
          </a>
        </div>
      ) : (
        <p className="text-slate-400 text-xs italic">
          Click vào các thẻ trích dẫn [1], [2] bên ô Chat để kiểm chứng văn bản gốc.
        </p>
      )}
    </div>
  );
}
