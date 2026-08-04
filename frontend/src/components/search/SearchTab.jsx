import React, { useState } from 'react';
import { Search, Download, ExternalLink, PlusCircle, CheckCircle2, Award, Key, Loader2, AlertCircle } from 'lucide-react';

export default function SearchTab({ papers, setPapers, selectedPaperIds, toggleSelectPaper, setActiveTab, darkMode }) {
  const [searchQuery, setSearchQuery] = useState('large language models in healthcare');
  const [apiKey, setApiKey] = useState(() => localStorage.getItem('serp_api_key') || '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleApiKeyChange = (e) => {
    const val = e.target.value;
    setApiKey(val);
    localStorage.setItem('serp_api_key', val);
  };

  const handleSearch = async (e) => {
    if (e) e.preventDefault();
    if (!searchQuery.trim()) return;

    if (!apiKey.trim()) {
      setError('Vui lòng nhập SerpApi Key của bạn để bắt đầu tìm kiếm dữ liệu thật!');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch(`http://localhost:8000/api/v1/search?query=${encodeURIComponent(searchQuery)}`, {
        headers: {
          'X-API-Key': apiKey.trim()
        }
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Lỗi tìm kiếm từ server');
      }

      const data = await response.json();
      if (data.papers && data.papers.length > 0) {
        setPapers(data.papers);
      } else {
        setError('Không tìm thấy bài báo nào phù hợp với từ khóa này.');
      }
    } catch (err) {
      console.error(err);
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        setError('Không thể kết nối đến Backend (http://localhost:8000). Vui lòng đảm bảo bạn đã bật Backend bằng lệnh `uvicorn src.main:app --reload` trên máy!');
      } else {
        setError(err.message || 'Lỗi không xác định khi gọi Backend.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto py-4">
      
      {/* Page Title Header */}
      <div className="text-center space-y-3">
        <h2 className={`text-3xl md:text-4xl font-extrabold tracking-tight ${darkMode ? 'text-white' : 'text-slate-900'}`}>
          1. Tra cứu bài báo & Lấy Link PDF
        </h2>
        <p className={`text-base max-w-2xl mx-auto font-medium ${darkMode ? 'text-slate-400' : 'text-slate-600'}`}>
          Tìm kiếm bài báo khoa học trực tiếp từ Google Scholar qua SerpApi, tự động tính điểm uy tín (LitScore) & lấy link PDF gốc.
        </p>
      </div>

      {/* BYOK API Key Banner */}
      <div className={`p-4 md:p-5 rounded-2xl border transition-all ${
        darkMode ? 'bg-slate-900/90 border-slate-800' : 'bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-100'
      }`}>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-sm font-bold text-blue-700 dark:text-sky-300">
            <Key className="w-4 h-4 shrink-0 text-blue-600 dark:text-sky-400" />
            <span>API Key (SerpApi / S2 Key):</span>
          </div>
          <div className="flex-1 max-w-md flex items-center gap-2">
            <input
              type="password"
              value={apiKey}
              onChange={handleApiKeyChange}
              placeholder="Dán SerpApi Key hoặc S2 Key (s2k-...) vào đây..."
              className={`w-full px-4 py-2 border rounded-xl text-xs font-mono focus:outline-none focus:ring-2 focus:ring-blue-600 ${
                darkMode ? 'bg-slate-800 border-slate-700 text-white placeholder-slate-500' : 'bg-white border-slate-300 text-slate-900'
              }`}
            />
          </div>
          <div className="flex items-center gap-3 text-xs font-bold text-blue-600 dark:text-sky-400 shrink-0">
            <a
              href="https://serpapi.com/users/sign_up"
              target="_blank"
              rel="noreferrer"
              className="hover:underline flex items-center gap-1"
            >
              <span>Lấy SerpApi Key</span>
              <ExternalLink className="w-3 h-3" />
            </a>
            <span>•</span>
            <a
              href="https://www.semanticscholar.org/product/api"
              target="_blank"
              rel="noreferrer"
              className="hover:underline flex items-center gap-1"
            >
              <span>Lấy S2 Key</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>
      </div>

      {/* Spacious Search Bar */}
      <form onSubmit={handleSearch} className={`p-4 md:p-6 rounded-3xl border shadow-lg transition-colors ${
        darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
      }`}>
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-6 h-6 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Nhập từ khóa nghiên cứu (ví dụ: 'large language models in healthcare')..."
              className={`w-full pl-14 pr-4 py-4 border rounded-2xl text-base font-semibold focus:outline-none focus:ring-2 focus:ring-blue-600 ${
                darkMode 
                  ? 'bg-slate-800 border-slate-700 text-white placeholder-slate-500' 
                  : 'bg-slate-50 border-slate-300 text-slate-900 placeholder-slate-400'
              }`}
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-bold px-8 py-4 rounded-2xl text-base transition-all shadow-md flex items-center justify-center gap-2 shrink-0"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Đang tìm kiếm...</span>
              </>
            ) : (
              <span>Tìm bài báo</span>
            )}
          </button>
        </div>
      </form>

      {/* Error Alert */}
      {error && (
        <div className="p-4 rounded-2xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800/60 text-red-700 dark:text-red-300 text-sm font-semibold flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0 text-red-500" />
          <span>{error}</span>
        </div>
      )}

      {/* Results List Cards */}
      <div className="space-y-6">
        <div className="flex items-center justify-between px-2">
          <span className="text-sm font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
            Kết quả tìm thấy ({papers.length} bài báo)
          </span>
          {selectedPaperIds.length > 0 && (
            <span className="text-sm font-bold text-blue-600 dark:text-sky-400">
              Đã chọn {selectedPaperIds.length} bài để đưa lên AI
            </span>
          )}
        </div>

        {papers.length === 0 && !loading && (
          <div className={`p-12 text-center rounded-3xl border ${
            darkMode ? 'bg-slate-900/60 border-slate-800 text-slate-400' : 'bg-white border-slate-200 text-slate-500'
          }`}>
            <Search className="w-12 h-12 mx-auto mb-4 opacity-30 text-blue-500" />
            <h3 className="text-lg font-bold mb-1">Chưa có kết quả tìm kiếm nào</h3>
            <p className="text-sm max-w-md mx-auto">
              Hãy nhập SerpApi Key / S2 Key ở trên, sau đó gõ từ khóa nghiên cứu và nhấn nút <strong>"Tìm bài báo"</strong> để kết nối dữ liệu thật!
            </p>
          </div>
        )}

        {papers.map((paper) => {
          const isSelected = selectedPaperIds.includes(paper.id);
          return (
            <div
              key={paper.id}
              className={`p-6 md:p-8 rounded-3xl border transition-all duration-300 space-y-5 shadow-sm hover:shadow-xl hover:-translate-y-1 ${
                darkMode ? 'bg-slate-900 border-slate-800 text-slate-200 hover:shadow-blue-900/20' : 'bg-white border-slate-200 hover:shadow-slate-300'
              } ${isSelected ? 'ring-2 ring-blue-500 border-blue-500 shadow-md' : ''}`}
            >
              {/* Paper Header */}
              <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                <div className="space-y-2 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="px-3 py-1 bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-sky-300 text-xs font-bold rounded-lg border border-blue-200 dark:border-blue-800">
                      {paper.journal} ({paper.year})
                    </span>
                    <span className="text-xs font-mono font-bold text-slate-400">ID: {paper.id}</span>
                  </div>

                  <h3 className={`font-extrabold text-lg md:text-xl leading-snug ${darkMode ? 'text-white' : 'text-slate-900'}`}>
                    {paper.title}
                  </h3>
                  
                  <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">
                    Tác giả: {paper.authors}
                  </p>
                </div>

                <div className="shrink-0">
                  <span className="px-3 py-1.5 bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800 text-xs font-bold rounded-xl flex items-center gap-1.5">
                    <Award className="w-4 h-4 text-amber-500" />
                    <span>LitScore: {paper.litScore}/100</span>
                  </span>
                </div>
              </div>

              {/* Abstract & TL;DR Section */}
              <div className={`p-5 rounded-2xl text-sm leading-relaxed border ${
                darkMode ? 'bg-slate-800/80 border-slate-700 text-slate-300' : 'bg-slate-50 border-slate-200 text-slate-700'
              }`}>
                {paper.tldr && (
                  <div className="mb-3 p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-100 dark:border-emerald-800/50">
                    <p className="font-bold text-emerald-700 dark:text-emerald-400">⚡ Tóm tắt siêu tốc (AI TL;DR):</p>
                    <p className="text-emerald-800 dark:text-emerald-300 mt-1">{paper.tldr.replace('TL;DR: ', '')}</p>
                  </div>
                )}
                <p className="font-bold text-blue-600 dark:text-sky-400 mb-1">📝 Tóm tắt Abstract:</p>
                <p>{paper.abstract}</p>
              </div>

              {/* Action Buttons Footer */}
              <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-3 border-t border-slate-100 dark:border-slate-800">
                <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 font-mono">
                  DOI: {paper.doi} • {paper.citations.toLocaleString()} lượt trích dẫn
                </div>

                <div className="flex items-center gap-3 w-full sm:w-auto">
                  {/* Download PDF Button */}
                  <a
                    href={paper.url}
                    target="_blank"
                    rel="noreferrer"
                    className={`flex-1 sm:flex-none flex items-center justify-center gap-2 px-5 py-3 rounded-xl text-xs font-bold transition-all border ${
                      darkMode 
                        ? 'bg-slate-800 hover:bg-slate-700 border-slate-700 text-white' 
                        : 'bg-slate-100 hover:bg-slate-200 border-slate-200 text-slate-800'
                    }`}
                  >
                    <Download className="w-4 h-4 text-blue-600 dark:text-sky-400" />
                    <span>Tải PDF Bài Gốc</span>
                    <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
                  </a>

                  {/* Toggle Select Button */}
                  <button
                    onClick={() => toggleSelectPaper(paper.id)}
                    className={`flex-1 sm:flex-none flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-xs font-bold transition-all shadow-md ${
                      isSelected
                        ? 'bg-emerald-600 hover:bg-emerald-700 text-white'
                        : 'bg-blue-600 hover:bg-blue-700 text-white'
                    }`}
                  >
                    {isSelected ? (
                      <>
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Đã thêm vào Workspace</span>
                      </>
                    ) : (
                      <>
                        <PlusCircle className="w-4 h-4" />
                        <span>Thêm vào AI Workspace</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          );
        })}

        {/* Floating Bottom Step Bar */}
        {selectedPaperIds.length > 0 && (
          <div className="sticky bottom-6 bg-slate-900 text-white p-5 rounded-3xl border border-slate-800 shadow-2xl flex flex-col sm:flex-row items-center justify-between gap-4 z-40">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl bg-blue-600 text-white font-extrabold flex items-center justify-center text-lg">
                {selectedPaperIds.length}
              </div>
              <div>
                <p className="font-bold text-sm">Đã chọn {selectedPaperIds.length} bài báo</p>
                <p className="text-xs text-slate-400">Sẵn sàng để đưa vào không gian làm việc của AI</p>
              </div>
            </div>

            <button
              onClick={() => setActiveTab('workspace')}
              className="bg-blue-600 hover:bg-blue-700 text-white font-bold px-6 py-3.5 rounded-2xl text-xs transition-all shadow-lg w-full sm:w-auto"
            >
              Chuyển sang AI Workspace →
            </button>
          </div>
        )}

      </div>
    </div>
  );
}
