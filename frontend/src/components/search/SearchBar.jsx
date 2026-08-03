import React from 'react';
import { Search, Sparkles, Filter } from 'lucide-react';

export default function SearchBar({ 
  searchQuery, 
  setSearchQuery, 
  isSemanticMode, 
  setIsSemanticMode, 
  showAdvancedFilters, 
  setShowAdvancedFilters 
}) {
  return (
    <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
      <div className="flex flex-col md:flex-row gap-4 items-center">
        {/* Search Mode Switch */}
        <div className="flex bg-slate-100 p-1 rounded-xl border border-slate-200 shrink-0">
          <button
            onClick={() => setIsSemanticMode(true)}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg transition-all ${
              isSemanticMode ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-600'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI Semantic Search</span>
          </button>
          <button
            onClick={() => setIsSemanticMode(false)}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg transition-all ${
              !isSemanticMode ? 'bg-slate-800 text-white shadow-sm' : 'text-slate-600'
            }`}
          >
            <Search className="w-3.5 h-3.5" />
            <span>Exact Keyword</span>
          </button>
        </div>

        {/* Input Bar */}
        <div className="relative flex-1 w-full">
          <Search className="w-5 h-5 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search Scopus & Web of Science databases (e.g., 'LLM applications in diagnostic radiology')..."
            className="w-full pl-12 pr-28 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white text-slate-800 font-medium transition-all text-xs sm:text-sm"
          />
          <button className="absolute right-2 top-1/2 -translate-y-1/2 bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-lg text-xs sm:text-sm font-semibold transition-all">
            Search
          </button>
        </div>
      </div>

      {/* Quick Preset Filter Chips */}
      <div className="flex flex-wrap items-center gap-2 pt-2">
        <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Quick Trends:</span>
        {[
          'LLM Healthcare 2024',
          'RAG Hallucination Benchmark',
          'Stochastic Optimization (Adam)',
          'Medical Diagnostics Accuracy'
        ].map((chip, idx) => (
          <button
            key={idx}
            onClick={() => setSearchQuery(chip)}
            className="px-3 py-1 bg-slate-100 hover:bg-slate-200 text-slate-600 text-xs font-semibold rounded-full transition-all border border-slate-200"
          >
            + {chip}
          </button>
        ))}

        <button
          onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
          className="ml-auto flex items-center gap-1 text-xs font-bold text-blue-600 hover:text-blue-700"
        >
          <Filter className="w-3.5 h-3.5" />
          <span>{showAdvancedFilters ? 'Hide Filters ▲' : 'Advanced Filters ▼'}</span>
        </button>
      </div>
    </div>
  );
}
