import React, { useState } from 'react';
import { Award, ExternalLink, FileText, Copy, Check, Quote, PlusCircle, CheckCircle2, Sparkles, GitFork } from 'lucide-react';

export default function PaperTable({ papers, selectedPaperIds, toggleSelectPaper, onOpenAiScreening, onOpenGenealogy, darkMode }) {
  const [copiedDoi, setCopiedDoi] = useState(null);
  const [citationModalPaper, setCitationModalPaper] = useState(null);
  const [expandedRowIds, setExpandedRowIds] = useState([]);

  const toggleExpandRow = (id) => {
    if (expandedRowIds.includes(id)) {
      setExpandedRowIds(expandedRowIds.filter(item => item !== id));
    } else {
      setExpandedRowIds([...expandedRowIds, id]);
    }
  };

  const handleCopyDoi = (doi) => {
    if (!doi || doi === 'N/A') return;
    navigator.clipboard.writeText(doi);
    setCopiedDoi(doi);
    setTimeout(() => setCopiedDoi(null), 2000);
  };

  const allSelected = papers.length > 0 && papers.every(p => selectedPaperIds.includes(p.id));

  const handleToggleSelectAll = () => {
    if (allSelected) {
      papers.forEach(p => {
        if (selectedPaperIds.includes(p.id)) {
          toggleSelectPaper(p.id);
        }
      });
    } else {
      papers.forEach(p => {
        if (!selectedPaperIds.includes(p.id)) {
          toggleSelectPaper(p.id);
        }
      });
    }
  };

  return (
    <div className={`rounded-3xl border overflow-hidden transition-all shadow-sm ${
      darkMode ? 'bg-slate-900 border-slate-800 text-slate-200' : 'bg-white border-slate-200 text-slate-800'
    }`}>
      {/* Table Sub-Header */}
      <div className={`p-4 border-b flex items-center justify-between gap-3 ${
        darkMode ? 'bg-slate-900/90 border-slate-800' : 'bg-slate-50 border-slate-100'
      }`}>
        <div>
          <h3 className="font-extrabold text-sm flex items-center gap-2">
            <span>Danh sách kết quả bài báo khoa học (Dạng bảng)</span>
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">Bấm vào ô tóm tắt để mở rộng / thu gọn full Abstract</p>
        </div>
        <span className={`text-xs font-bold px-3 py-1 rounded-xl border ${
          darkMode ? 'bg-slate-800 border-slate-700 text-slate-300' : 'bg-white border-slate-200 text-slate-600'
        }`}>
          Hiển thị {papers.length} bài báo
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className={`border-b text-[11px] font-extrabold uppercase tracking-wider ${
              darkMode ? 'bg-slate-800/80 border-slate-700 text-slate-400' : 'bg-slate-100/70 border-slate-200 text-slate-600'
            }`}>
              <th className="p-4 w-12 text-center">
                <input
                  type="checkbox"
                  checked={allSelected}
                  onChange={handleToggleSelectAll}
                  className="w-4 h-4 rounded text-blue-600 focus:ring-blue-500 border-slate-300 cursor-pointer"
                  title="Chọn tất cả bài báo hiện tại"
                />
              </th>
              <th className="p-4">Tên bài báo & Định danh DOI</th>
              <th className="p-4">Tác giả & Tạp chí</th>
              <th className="p-4 w-28 text-center">Trích dẫn</th>
              <th className="p-4">Tóm tắt AI (TL;DR) & Abstract</th>
              <th className="p-4 w-44 text-right">Thao tác</th>
            </tr>
          </thead>
          <tbody className={`divide-y text-xs ${darkMode ? 'divide-slate-800' : 'divide-slate-100'}`}>
            {papers.length === 0 ? (
              <tr>
                <td colSpan={7} className="p-8 text-center text-slate-400">
                  Không tìm thấy bài báo nào phù hợp với bộ lọc hiện tại.
                </td>
              </tr>
            ) : (
              papers.map((paper) => {
                const isSelected = selectedPaperIds.includes(paper.id);
                const isExpanded = expandedRowIds.includes(paper.id);

                return (
                  <tr 
                    key={paper.id}
                    className={`transition-colors ${
                      isSelected 
                        ? darkMode ? 'bg-blue-950/30' : 'bg-blue-50/60' 
                        : darkMode ? 'hover:bg-slate-800/50' : 'hover:bg-slate-50'
                    }`}
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
                      <div className="space-y-1 max-w-md">
                        <a
                          href={paper.url}
                          target="_blank"
                          rel="noreferrer"
                          className={`font-bold hover:underline text-sm leading-snug flex items-start gap-1.5 ${
                            darkMode ? 'text-white hover:text-sky-400' : 'text-slate-900 hover:text-blue-600'
                          }`}
                        >
                          <span>{paper.title}</span>
                          <ExternalLink className="w-3.5 h-3.5 shrink-0 mt-0.5 text-slate-400" />
                        </a>
                        <div className="flex items-center gap-2 text-[11px] text-slate-500 dark:text-slate-400 flex-wrap">
                          <span className={`font-mono px-1.5 py-0.5 rounded font-semibold text-[10px] ${
                            darkMode ? 'bg-slate-800 text-slate-300' : 'bg-slate-100 text-slate-600'
                          }`}>{paper.id}</span>
                          {paper.scopus_status === 'indexed' && paper.coverage_year_status === 'ok' && (
                            <span className="px-1.5 py-0.5 rounded font-bold text-[10px] bg-emerald-100 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800">
                              🟢 Scopus Indexed
                            </span>
                          )}
                          {paper.scopus_status === 'indexed' && paper.coverage_year_status === 'out_of_coverage' && (
                            <span className="px-1.5 py-0.5 rounded font-bold text-[10px] bg-amber-100 dark:bg-amber-950/80 text-amber-700 dark:text-amber-300 border border-amber-300 dark:border-amber-800">
                              ⚠️ Out of Coverage
                            </span>
                          )}
                          {(paper.scopus_status === 'undetermined' || !paper.scopus_status) && (
                            <span className="px-1.5 py-0.5 rounded font-bold text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
                              ⚪ Undetermined
                            </span>
                          )}
                          <span>DOI: {paper.doi}</span>
                          {paper.doi && paper.doi !== 'N/A' && (
                            <button
                              onClick={() => handleCopyDoi(paper.doi)}
                              className="hover:text-blue-500 transition-colors"
                              title="Sao chép DOI"
                            >
                              {copiedDoi === paper.doi ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
                            </button>
                          )}
                        </div>
                      </div>
                    </td>

                    {/* Authors & Journal */}
                    <td className="p-4">
                      <div className="space-y-0.5 max-w-xs">
                        <p className="font-semibold text-slate-700 dark:text-slate-300 line-clamp-1">{paper.authors}</p>
                        <p className="text-slate-400 italic text-[11px] font-medium">{paper.journal} ({paper.year})</p>
                      </div>
                    </td>

                    {/* Citations Count */}
                    <td className="p-4 text-center">
                      <span className={`font-bold border px-2.5 py-1 rounded-xl text-xs ${
                        darkMode ? 'bg-slate-800 border-slate-700 text-slate-200' : 'bg-slate-100 border-slate-200 text-slate-800'
                      }`}>
                        {paper.citations ? paper.citations.toLocaleString() : 0}
                      </span>
                    </td>

                    {/* TL;DR Summary & Abstract Clickable Cell */}
                    <td className="p-4 max-w-xs">
                      <div 
                        onClick={() => toggleExpandRow(paper.id)}
                        className={`cursor-pointer p-2.5 rounded-xl border leading-relaxed transition-all ${
                          darkMode 
                            ? 'bg-slate-800/60 border-slate-700/60 hover:border-blue-500/60 text-slate-300' 
                            : 'bg-blue-50/50 border-blue-100/60 hover:border-blue-300 text-slate-700'
                        }`}
                        title="Click để mở rộng / thu gọn Abstract"
                      >
                        <p className={`text-[11px] ${isExpanded ? 'whitespace-pre-line' : 'line-clamp-2'}`}>
                          {paper.abstract}
                        </p>
                        <span className="mt-1 text-[10px] font-bold text-blue-600 dark:text-sky-400 block">
                          {isExpanded ? "▲ Thu gọn" : "▼ Xem đầy đủ..."}
                        </span>
                      </div>
                    </td>

                    {/* Action Buttons */}
                    <td className="p-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => onOpenAiScreening && onOpenAiScreening(paper)}
                          className="flex items-center gap-1 px-2.5 py-1.5 rounded-xl text-[11px] font-bold bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition-all"
                          title="Phân tích AI Screening đối chiếu tiêu chí"
                        >
                          <Sparkles className="w-3.5 h-3.5 text-amber-300 animate-pulse" />
                          <span>AI Screening</span>
                        </button>

                        <button
                          onClick={() => setCitationModalPaper(paper)}
                          className={`p-2 rounded-xl transition-all border ${
                            darkMode ? 'bg-slate-800 hover:bg-slate-700 border-slate-700 text-slate-200' : 'bg-slate-100 hover:bg-slate-200 border-slate-200 text-slate-700'
                          }`}
                          title="Trích dẫn APA"
                        >
                          <Quote className="w-3.5 h-3.5" />
                        </button>
                        
                        <a
                          href={paper.url}
                          target="_blank"
                          rel="noreferrer"
                          className={`p-2 rounded-xl transition-all border ${
                            darkMode ? 'bg-slate-800 hover:bg-slate-700 border-slate-700 text-blue-400' : 'bg-slate-100 hover:bg-slate-200 border-slate-200 text-blue-600'
                          }`}
                          title="Tải bài gốc (PDF)"
                        >
                          <FileText className="w-3.5 h-3.5" />
                        </a>

                        <button
                          onClick={() => onOpenGenealogy && onOpenGenealogy(paper)}
                          className={`p-2 rounded-xl transition-all border ${
                            darkMode ? 'bg-slate-800 hover:bg-slate-700 border-sky-500/40 text-sky-400' : 'bg-sky-50 hover:bg-sky-100 border-sky-200 text-sky-700'
                          }`}
                          title="Khám phá Cây phả hệ trích dẫn"
                        >
                          <GitFork className="w-3.5 h-3.5" />
                        </button>

                        <button
                          onClick={() => toggleSelectPaper(paper.id)}
                          className={`p-2 rounded-xl transition-all border font-bold ${
                            isSelected
                              ? 'bg-emerald-600 border-emerald-600 text-white'
                              : 'bg-blue-600 border-blue-600 text-white hover:bg-blue-700'
                          }`}
                          title={isSelected ? "Bỏ chọn khỏi Screening" : "Thêm vào Screening"}
                        >
                          {isSelected ? <CheckCircle2 className="w-3.5 h-3.5" /> : <PlusCircle className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Citation Modal */}
      {citationModalPaper && (
        <div className="fixed inset-0 bg-slate-950/60 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className={`rounded-3xl p-6 max-w-lg w-full space-y-4 shadow-2xl border ${
            darkMode ? 'bg-slate-900 border-slate-800 text-white' : 'bg-white border-slate-200 text-slate-900'
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
                className="px-4 py-2 bg-blue-600 text-white font-bold rounded-xl text-xs hover:bg-blue-700 transition-colors"
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
