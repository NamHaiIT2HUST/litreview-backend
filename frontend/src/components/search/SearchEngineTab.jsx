import React, { useState } from 'react';
import SearchBar from './SearchBar';
import TrendVisualizer from './TrendVisualizer';
import PaperTable from './PaperTable';
import { Download, Sparkles } from 'lucide-react';
import { exportPapersToExcel } from '../../utils/excelExport';

export default function SearchEngineTab({ 
  papers, 
  selectedPaperIds, 
  setSelectedPaperIds, 
  pushToWorkspace 
}) {
  const [searchQuery, setSearchQuery] = useState('large language models in healthcare');
  const [isSemanticMode, setIsSemanticMode] = useState(true);
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [minYear, setMinYear] = useState('2020');
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
      {/* Search Input Card */}
      <SearchBar
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        isSemanticMode={isSemanticMode}
        setIsSemanticMode={setIsSemanticMode}
        showAdvancedFilters={showAdvancedFilters}
        setShowAdvancedFilters={setShowAdvancedFilters}
      />

      {/* Collapsible Advanced Filters */}
      {showAdvancedFilters && (
        <div className="pt-4 border-t border-slate-100 grid grid-cols-1 md:grid-cols-4 gap-4 bg-slate-50 p-4 rounded-xl">
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">Publication Year</label>
            <select 
              value={minYear} 
              onChange={e => setMinYear(e.target.value)}
              className="w-full p-2 text-xs border border-slate-200 rounded-lg bg-white"
            >
              <option value="2020">2020 - 2025 (Recent)</option>
              <option value="2023">2023 - 2025 (Last 2 Years)</option>
              <option value="all">All Years</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">Article Type</label>
            <select 
              value={articleType} 
              onChange={e => setArticleType(e.target.value)}
              className="w-full p-2 text-xs border border-slate-200 rounded-lg bg-white"
            >
              <option value="All">All Types (Review, Article)</option>
              <option value="Review">Systematic Review Only</option>
              <option value="Clinical Trial">Clinical Study / Trial</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">Minimum Citations</label>
            <input 
              type="number" 
              placeholder="e.g. 50" 
              className="w-full p-2 text-xs border border-slate-200 rounded-lg bg-white"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">Data Source</label>
            <div className="flex gap-2 mt-1">
              <label className="flex items-center gap-1 text-xs text-slate-700">
                <input type="checkbox" defaultChecked /> Scopus
              </label>
              <label className="flex items-center gap-1 text-xs text-slate-700">
                <input type="checkbox" defaultChecked /> Web of Science
              </label>
            </div>
          </div>
        </div>
      )}

      {/* Research Momentum Visualizer Widget */}
      <TrendVisualizer searchQuery={searchQuery} />

      {/* Action Bar (Export to Excel & Push to Workspace) */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex items-center gap-3">
          <span className="text-xs font-bold text-slate-600">
            Selected: <strong className="text-blue-600 text-sm">{selectedPaperIds.length}</strong> / {papers.length} papers
          </span>
          <button
            onClick={() => setSelectedPaperIds(papers.map(p => p.id))}
            className="text-xs text-blue-600 hover:underline font-semibold"
          >
            Select All
          </button>
          <button
            onClick={() => setSelectedPaperIds([])}
            className="text-xs text-slate-500 hover:underline font-semibold"
          >
            Clear Selection
          </button>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto">
          <button
            onClick={handleExport}
            className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold transition-all shadow-sm"
          >
            <Download className="w-4 h-4" />
            <span>Export to Excel (.xlsx)</span>
          </button>

          <button
            onClick={pushToWorkspace}
            disabled={selectedPaperIds.length === 0}
            className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-5 py-2 bg-gradient-to-r from-blue-600 to-purple-600 hover:opacity-95 text-white rounded-xl text-xs font-bold transition-all shadow-md disabled:opacity-50"
          >
            <Sparkles className="w-4 h-4" />
            <span>Push {selectedPaperIds.length} Papers to AI Workspace →</span>
          </button>
        </div>
      </div>

      {/* Papers Data Table */}
      <PaperTable
        papers={papers}
        selectedPaperIds={selectedPaperIds}
        toggleSelectPaper={toggleSelectPaper}
      />
    </div>
  );
}
