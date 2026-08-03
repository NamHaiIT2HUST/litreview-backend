import React, { useState } from 'react';
import { Award, ExternalLink, FileText, Copy, Check, Quote } from 'lucide-react';

export default function PaperTable({ papers, selectedPaperIds, toggleSelectPaper }) {
  const [copiedDoi, setCopiedDoi] = useState(null);
  const [citationModalPaper, setCitationModalPaper] = useState(null);

  const handleCopyDoi = (doi) => {
    navigator.clipboard.writeText(doi);
    setCopiedDoi(doi);
    setTimeout(() => setCopiedDoi(null), 2000);
  };

  return (
    <div className="mota-card overflow-hidden">
      {/* Table Header / Title */}
      <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
        <div>
          <h3 className="font-bold text-slate-800 text-sm">Danh sách kết quả bài báo</h3>
          <p className="text-xs text-slate-500">Dữ liệu từ Scopus và Web of Science đã qua xử lý lọc trùng</p>
        </div>
        <span className="text-xs font-semibold text-slate-600 bg-white px-2.5 py-1 rounded-md border border-slate-200">
          Hiển thị {papers.length} bài báo
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-100/70 border-b border-slate-200 text-xs font-bold text-slate-700 uppercase tracking-wider">
              <th className="p-4 w-12 text-center">Chọn</th>
              <th className="p-4">Tên bài báo & Thông tin nhận diện</th>
              <th className="p-4 w-28 text-center">LitScore 🎖️</th>
              <th className="p-4">Tác giả & Tạp chí</th>
              <th className="p-4 w-24 text-center">Trích dẫn</th>
              <th className="p-4">Tóm tắt AI (TL;DR)</th>
              <th className="p-4 w-36 text-right">Thao tác</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-xs">
            {papers.map((paper) => {
              const isSelected = selectedPaperIds.includes(paper.id);
              return (
                <tr 
                  key={paper.id}
                  className={`hover:bg-blue-50/30 transition-colors ${isSelected ? 'bg-blue-50/60' : ''}`}
                >
                  {/* Select Checkbox */}
                  <td className="p-4 text-center">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleSelectPaper(paper.id)}
                      className="w-4 h-4 rounded text-blue-600 focus:ring-blue-500 border-slate-300 cursor-pointer"
                    />
                  </td>

                  {/* Title & Identifiers */}
                  <td className="p-4">
                    <div className="space-y-1">
                      <a
                        href={paper.url}
                        target="_blank"
                        rel="noreferrer"
                        className="font-bold text-blue-700 hover:text-blue-900 text-sm leading-snug flex items-start gap-1.5"
                      >
                        <span>{paper.title}</span>
                        <ExternalLink className="w-3.5 h-3.5 text-blue-400 shrink-0 mt-0.5" />
                      </a>
                      <div className="flex items-center gap-2 text-[11px] text-slate-500">
                        <span className="font-mono bg-slate-100 px-1.5 py-0.5 rounded text-slate-600 font-semibold">{paper.id}</span>
                        <span>DOI: {paper.doi}</span>
                        <button
                          onClick={() => handleCopyDoi(paper.doi)}
                          className="text-slate-400 hover:text-blue-600 transition-colors"
                          title="Sao chép DOI"
                        >
                          {copiedDoi === paper.doi ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
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
                      <p className="font-medium text-slate-800 line-clamp-1">{paper.authors}</p>
                      <p className="text-slate-500 italic font-semibold">{paper.journal} ({paper.year})</p>
                    </div>
                  </td>

                  {/* Citations Count */}
                  <td className="p-4 text-center">
                    <span className="font-bold text-slate-800 bg-slate-100 border border-slate-200 px-2.5 py-1 rounded-md">
                      {paper.citations.toLocaleString()}
                    </span>
                  </td>

                  {/* TL;DR Summary */}
                  <td className="p-4 max-w-xs">
                    <p className="text-slate-700 text-[11px] line-clamp-2 bg-blue-50/50 p-2 rounded-lg border border-blue-100/60 leading-relaxed">
                      {paper.tldr}
                    </p>
                  </td>

                  {/* Action Buttons (AIoT Lab Style Citation Modal + Download PDF) */}
                  <td className="p-4 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        onClick={() => setCitationModalPaper(paper)}
                        className="p-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-all"
                        title="Trích dẫn bài báo (APA/BibTeX)"
                      >
                        <Quote className="w-3.5 h-3.5" />
                      </button>
                      <a
                        href={paper.url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-all text-xs"
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

      {/* Citation Modal (Identical Feature to AIoT Lab) */}
      {citationModalPaper && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-6 max-w-lg w-full space-y-4 shadow-xl border border-slate-200">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-800 text-sm">Trích dẫn bài báo</h3>
              <button 
                onClick={() => setCitationModalPaper(null)}
                className="text-slate-400 hover:text-slate-600 text-lg font-bold"
              >
                ✕
              </button>
            </div>
            <div>
              <p className="text-xs font-bold text-slate-700 mb-1">{citationModalPaper.title}</p>
              <textarea
                readOnly
                rows={3}
                value={`${citationModalPaper.authors} (${citationModalPaper.year}). ${citationModalPaper.title}. ${citationModalPaper.journal}. https://doi.org/${citationModalPaper.doi}`}
                className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs font-mono focus:outline-none"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => {
                  navigator.clipboard.writeText(`${citationModalPaper.authors} (${citationModalPaper.year}). ${citationModalPaper.title}. ${citationModalPaper.journal}. https://doi.org/${citationModalPaper.doi}`);
                  setCitationModalPaper(null);
                }}
                className="px-4 py-2 bg-blue-600 text-white font-bold rounded-xl text-xs hover:bg-blue-700"
              >
                Sao chép Trích dẫn APA
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
