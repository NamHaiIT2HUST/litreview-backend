import React, { useState } from 'react';
import { Award, ExternalLink, FileText, Copy, Check, Quote } from 'lucide-react';

export default function PaperTable({ papers, selectedPaperIds, toggleSelectPaper, darkMode }) {
  const [copiedDoi, setCopiedDoi] = useState(null);
  const [citationModalPaper, setCitationModalPaper] = useState(null);

  const handleCopyDoi = (doi) => {
    navigator.clipboard.writeText(doi);
    setCopiedDoi(doi);
    setTimeout(() => setCopiedDoi(null), 2000);
  };

  return (
    <div className={`rounded-2xl border overflow-hidden transition-colors ${
      darkMode ? 'bg-slate-800 border-slate-700 text-slate-200' : 'bg-white border-slate-200 text-slate-800'
    }`}>
      {/* Table Header */}
      <div className={`p-4 border-b flex items-center justify-between ${
        darkMode ? 'bg-slate-900/60 border-slate-700' : 'bg-slate-50/60 border-slate-100'
      }`}>
        <div>
          <h3 className="font-bold text-sm">Danh sách kết quả bài báo khoa học</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">ScraperAgent đã lọc trùng và RetrieverAgent đã nhúng Vector</p>
        </div>
        <span className={`text-xs font-semibold px-2.5 py-1 rounded-md border ${
          darkMode ? 'bg-slate-700 border-slate-600 text-slate-300' : 'bg-white border-slate-200 text-slate-600'
        }`}>
          Hiển thị {papers.length} bài báo
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className={`border-b text-xs font-bold uppercase tracking-wider ${
              darkMode ? 'bg-slate-900/80 border-slate-700 text-slate-400' : 'bg-slate-100/70 border-slate-200 text-slate-700'
            }`}>
              <th className="p-4 w-12 text-center">Chọn</th>
              <th className="p-4">Tên bài báo & Định danh DOI</th>
              <th className="p-4 w-28 text-center">LitScore 🎖️</th>
              <th className="p-4">Tác giả & Tạp chí</th>
              <th className="p-4 w-24 text-center">Trích dẫn</th>
              <th className="p-4">Tóm tắt AI (TL;DR)</th>
              <th className="p-4 w-36 text-right">Thao tác</th>
            </tr>
          </thead>
          <tbody className={`divide-y text-xs ${darkMode ? 'divide-slate-700/60' : 'divide-slate-100'}`}>
            {papers.map((paper) => {
              const isSelected = selectedPaperIds.includes(paper.id);
              return (
                <tr 
                  key={paper.id}
                  className={`transition-colors ${
                    isSelected 
                      ? darkMode ? 'bg-purple-950/40' : 'bg-blue-50/60' 
                      : darkMode ? 'hover:bg-slate-700/30' : 'hover:bg-blue-50/30'
                  }`}
                >
                  {/* Select Checkbox */}
                  <td className="p-4 text-center">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleSelectPaper(paper.id)}
                      className="w-4 h-4 rounded text-purple-600 focus:ring-purple-500 border-slate-300 cursor-pointer"
                    />
                  </td>

                  {/* Title & Identifiers */}
                  <td className="p-4">
                    <div className="space-y-1">
                      <a
                        href={paper.url}
                        target="_blank"
                        rel="noreferrer"
                        className={`font-bold hover:underline text-sm leading-snug flex items-start gap-1.5 ${
                          darkMode ? 'text-blue-400' : 'text-blue-700'
                        }`}
                      >
                        <span>{paper.title}</span>
                        <ExternalLink className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                      </a>
                      <div className="flex items-center gap-2 text-[11px] text-slate-500 dark:text-slate-400">
                        <span className={`font-mono px-1.5 py-0.5 rounded font-semibold ${
                          darkMode ? 'bg-slate-900 text-slate-300' : 'bg-slate-100 text-slate-600'
                        }`}>{paper.id}</span>
                        <span>DOI: {paper.doi}</span>
                        <button
                          onClick={() => handleCopyDoi(paper.doi)}
                          className="hover:text-purple-500 transition-colors"
                          title="Sao chép DOI"
                        >
                          {copiedDoi === paper.doi ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
                        </button>
                      </div>
                    </div>
                  </td>

                  {/* LitScore Badge */}
                  <td className="p-4 text-center">
                    <span className="mota-badge badge-amber text-xs">
                      <Award className="w-3.5 h-3.5 text-amber-600" />
                      <span>{paper.litScore}/100</span>
                    </span>
                  </td>

                  {/* Authors & Journal */}
                  <td className="p-4">
                    <div className="space-y-0.5 max-w-xs">
                      <p className="font-medium line-clamp-1">{paper.authors}</p>
                      <p className="text-slate-500 dark:text-slate-400 italic font-semibold">{paper.journal} ({paper.year})</p>
                    </div>
                  </td>

                  {/* Citations Count */}
                  <td className="p-4 text-center">
                    <span className={`font-bold border px-2.5 py-1 rounded-md ${
                      darkMode ? 'bg-slate-900 border-slate-700 text-slate-200' : 'bg-slate-100 border-slate-200 text-slate-800'
                    }`}>
                      {paper.citations.toLocaleString()}
                    </span>
                  </td>

                  {/* TL;DR Summary */}
                  <td className="p-4 max-w-xs">
                    <p className={`text-[11px] line-clamp-2 p-2 rounded-lg border leading-relaxed ${
                      darkMode 
                        ? 'bg-slate-900/60 border-slate-700 text-slate-300' 
                        : 'bg-blue-50/50 border-blue-100/60 text-slate-700'
                    }`}>
                      {paper.tldr}
                    </p>
                  </td>

                  {/* Action Buttons */}
                  <td className="p-4 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        onClick={() => setCitationModalPaper(paper)}
                        className={`p-1.5 rounded-lg transition-all ${
                          darkMode ? 'bg-slate-700 hover:bg-slate-600 text-slate-200' : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
                        }`}
                        title="Trích dẫn bài báo (APA/BibTeX)"
                      >
                        <Quote className="w-3.5 h-3.5" />
                      </button>
                      <a
                        href={paper.url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-purple-600 hover:bg-purple-700 text-white font-semibold rounded-lg transition-all text-xs"
                      >
                        <FileText className="w-3.5 h-3.5" />
                        <span>Tải PDF</span>
                      </a>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Citation Modal */}
      {citationModalPaper && (
        <div className="fixed inset-0 bg-slate-950/60 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className={`rounded-2xl p-6 max-w-lg w-full space-y-4 shadow-2xl border ${
            darkMode ? 'bg-slate-900 border-slate-700 text-white' : 'bg-white border-slate-200 text-slate-900'
          }`}>
            <div className="flex items-center justify-between border-b pb-3 border-slate-200 dark:border-slate-800">
              <h3 className="font-bold text-sm">Trích dẫn bài báo chuẩn APA</h3>
              <button 
                onClick={() => setCitationModalPaper(null)}
                className="text-slate-400 hover:text-slate-600 text-lg font-bold"
              >
                ✕
              </button>
            </div>
            <div>
              <p className="text-xs font-bold mb-2">{citationModalPaper.title}</p>
              <textarea
                readOnly
                rows={3}
                value={`${citationModalPaper.authors} (${citationModalPaper.year}). ${citationModalPaper.title}. ${citationModalPaper.journal}. https://doi.org/${citationModalPaper.doi}`}
                className={`w-full p-3 border rounded-xl text-xs font-mono focus:outline-none ${
                  darkMode ? 'bg-slate-800 border-slate-700 text-slate-200' : 'bg-slate-50 border-slate-200 text-slate-800'
                }`}
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => {
                  navigator.clipboard.writeText(`${citationModalPaper.authors} (${citationModalPaper.year}). ${citationModalPaper.title}. ${citationModalPaper.journal}. https://doi.org/${citationModalPaper.doi}`);
                  setCitationModalPaper(null);
                }}
                className="px-4 py-2 bg-purple-600 text-white font-bold rounded-xl text-xs hover:bg-purple-700"
              >
                Sao chép Trích dẫn
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
