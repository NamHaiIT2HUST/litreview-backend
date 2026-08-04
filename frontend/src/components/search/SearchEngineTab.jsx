import React, { useState } from 'react';
import SearchBar from './SearchBar';
import StatCards from './StatCards';
import PaperTable from './PaperTable';
import { Download, Sparkles } from 'lucide-react';
import { exportPapersToExcel } from '../../utils/excelExport';

export default function SearchEngineTab({ 
  papers, 
  selectedPaperIds, 
  setSelectedPaperIds, 
  pushToWorkspace,
  darkMode
}) {
  const [searchQuery, setSearchQuery] = useState('large language models in healthcare');
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [dateRange, setDateRange] = useState('any');
  const [language, setLanguage] = useState('english');
  const [articleType, setArticleType] = useState('All');

  const toggleSelectPaper = (id) => {
    if (selectedPaperIds.includes(id)) {
      setSelectedPaperIds(selectedPaperIds.filter(item => item !== id));
    } else {
      setSelectedPaperIds([...selectedPaperIds, id]);
    }
  };

  const handleExport = () => {
    const papersToExport = papers.filter(p => selectedPaperIds.includes(p.id));
    exportPapersToExcel(papersToExport, `LitReview_Dataset_${new Date().toISOString().slice(0, 10)}.xlsx`);
  };

  return (
    <div className="space-y-6">
      {/* 1. Top Stat Cards */}
      <StatCards 
        totalPapers={papers.length} 
        selectedCount={selectedPaperIds.length} 
        darkMode={darkMode}
      />

      {/* 2. Search & Advanced Filters */}
      <SearchBar
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        showAdvancedFilters={showAdvancedFilters}
        setShowAdvancedFilters={setShowAdvancedFilters}
        dateRange={dateRange}
        setDateRange={setDateRange}
        language={language}
        setLanguage={setLanguage}
        articleType={articleType}
        setArticleType={setArticleType}
        darkMode={darkMode}
      />

      {/* 3. Action Bar (Export Excel & Push Workspace) */}
      <div className={`p-4 flex flex-col sm:flex-row items-center justify-between gap-4 rounded-2xl border transition-colors ${
        darkMode ? 'bg-slate-800 border-slate-700 text-white' : 'bg-white border-slate-200 text-slate-800'
      }`}>
        <div className="flex items-center gap-3">
          <span className="text-xs font-bold">
            Đã chọn: <strong className="text-purple-500 text-sm">{selectedPaperIds.length}</strong> / {papers.length} bài báo
          </span>
          <button
            onClick={() => setSelectedPaperIds(papers.map(p => p.id))}
            className="text-xs text-purple-600 dark:text-purple-400 hover:underline font-bold"
          >
            Chọn tất cả
          </button>
          <button
            onClick={() => setSelectedPaperIds([])}
            className="text-xs text-slate-500 hover:underline font-semibold"
          >
            Bỏ chọn
          </button>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <button
            onClick={handleExport}
            className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold transition-all shadow-sm"
          >
            <Download className="w-4 h-4" />
            <span>Tải xuống File Excel (.xlsx)</span>
          </button>

          <button
            onClick={pushToWorkspace}
            disabled={selectedPaperIds.length === 0}
            className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-6 py-2.5 bg-gradient-to-r from-blue-600 to-purple-600 hover:opacity-95 text-white rounded-xl text-xs font-bold transition-all shadow-md disabled:opacity-50"
          >
            <Sparkles className="w-4 h-4" />
            <span>Đẩy {selectedPaperIds.length} Bài sang AI Workspace →</span>
          </button>
        </div>
      </div>

      {/* 4. Main Papers Data Table */}
      <PaperTable
        papers={papers}
        selectedPaperIds={selectedPaperIds}
        toggleSelectPaper={toggleSelectPaper}
        darkMode={darkMode}
      />
    </div>
  );
}
