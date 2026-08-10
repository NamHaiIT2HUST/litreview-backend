import React from 'react';
import { 
  SlidersHorizontal, 
  ArrowUpDown, 
  LayoutGrid, 
  Table as TableIcon, 
  Search, 
  RotateCcw, 
  X, 
  Award, 
  Calendar, 
  Quote, 
  FileText, 
  Sparkles,
  Download
} from 'lucide-react';

export default function FilterSortBar({
  totalCount,
  filteredCount,
  inResultQuery,
  setInResultQuery,
  sortBy,
  setSortBy,
  viewMode,
  setViewMode,
  activePreset,
  setActivePreset,
  showAdvanced,
  setShowAdvanced,
  minLitScore,
  setMinLitScore,
  minCitations,
  setMinCitations,
  startYear,
  setStartYear,
  endYear,
  setEndYear,
  selectedJournal,
  setSelectedJournal,
  availableJournals,
  resetFilters,
  hasActiveFilters,
  onExportExcel,
  darkMode
}) {

  const presets = [
    { id: 'scopus_confirmed', label: 'Scopus confirmed', icon: Sparkles },
    { id: 'undetermined', label: 'Undetermined', icon: FileText },
    { id: 'all', label: 'Tất cả bài báo', icon: FileText },
    { id: 'high_score', label: 'LitScore ≥ 70 (Uy tín cao)', icon: Award },
    { id: 'recent', label: 'Bài mới (3 năm gần đây)', icon: Calendar },
    { id: 'top_cited', label: 'Trích dẫn nhiều (≥ 50)', icon: Quote },
    { id: 'has_tldr', label: 'Có AI TL;DR', icon: FileText }
  ];

  return (
    <div className={`rounded-3xl border shadow-sm transition-all p-5 space-y-4 ${
      darkMode ? 'bg-slate-900 border-slate-800 text-slate-200' : 'bg-white border-slate-200 text-slate-800'
    }`}>
      {/* Top Toolbar: Search in results, Sort selector, View mode toggle, Advanced Toggle */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
        
        {/* Real-time In-Result Search */}
        <div className="relative flex-1 min-w-[240px]">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={inResultQuery}
            onChange={(e) => setInResultQuery(e.target.value)}
            placeholder="Lọc nhanh theo tiêu đề, tác giả, tóm tắt..."
            className={`w-full pl-10 pr-8 py-2.5 rounded-2xl text-xs font-semibold border transition-all focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              darkMode 
                ? 'bg-slate-800 border-slate-700 text-white placeholder-slate-500' 
                : 'bg-slate-50 border-slate-200 text-slate-900 placeholder-slate-400'
            }`}
          />
          {inResultQuery && (
            <button
              onClick={() => setInResultQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Right Tools Group */}
        <div className="flex flex-wrap items-center gap-2.5 justify-end">
          
          {/* Sort Selector Dropdown */}
          <div className="flex items-center gap-1.5 border rounded-2xl px-3 py-2 text-xs font-bold transition-all shrink-0">
            <ArrowUpDown className="w-3.5 h-3.5 text-blue-600 dark:text-sky-400 shrink-0" />
            <span className="text-slate-400 hidden sm:inline">Sắp xếp:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className={`bg-transparent font-bold focus:outline-none cursor-pointer text-xs ${
                darkMode ? 'text-white bg-slate-900' : 'text-slate-800 bg-white'
              }`}
            >
              <option value="source_order">Google Scholar Rank</option>
              <option value="litscore_desc">🎖️ LitScore (Cao → Thấp)</option>
              <option value="litscore_asc">LitScore (Thấp → Cao)</option>
              <option value="year_desc">📅 Năm (Mới nhất)</option>
              <option value="year_asc">Năm (Cũ nhất)</option>
              <option value="citations_desc">💬 Trích dẫn (Nhiều nhất)</option>
              <option value="title_asc">🔤 Tiêu đề (A → Z)</option>
            </select>
          </div>

          {/* Advanced Filter Panel Toggle */}
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className={`flex items-center gap-1.5 px-3.5 py-2.5 rounded-2xl text-xs font-bold transition-all border shrink-0 ${
              showAdvanced || hasActiveFilters
                ? 'bg-blue-50 dark:bg-blue-950/60 border-blue-300 dark:border-blue-800 text-blue-700 dark:text-sky-300'
                : darkMode ? 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700' : 'bg-slate-100 border-slate-200 text-slate-700 hover:bg-slate-200'
            }`}
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
            <span>Bộ lọc nâng cao</span>
            {hasActiveFilters && (
              <span className="w-2 h-2 rounded-full bg-blue-600 animate-pulse"></span>
            )}
          </button>

          {/* View Mode Switcher */}
          <div className={`flex items-center p-1 border rounded-2xl shrink-0 ${
            darkMode ? 'bg-slate-800 border-slate-700' : 'bg-slate-100 border-slate-200'
          }`}>
            <button
              onClick={() => setViewMode('cards')}
              className={`p-1.5 rounded-xl transition-all ${
                viewMode === 'cards'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-200'
              }`}
              title="Xem dạng thẻ (Card View)"
            >
              <LayoutGrid className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('table')}
              className={`p-1.5 rounded-xl transition-all ${
                viewMode === 'table'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-200'
              }`}
              title="Xem dạng bảng (Table View)"
            >
              <TableIcon className="w-4 h-4" />
            </button>
          </div>

        </div>
      </div>

      {/* Quick Preset Filter Chips */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 shrink-0">
          Lọc nhanh:
        </span>
        {presets.map((preset) => {
          const Icon = preset.icon;
          const isActive = activePreset === preset.id;
          return (
            <button
              key={preset.id}
              onClick={() => setActivePreset(preset.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all whitespace-nowrap border shrink-0 ${
                isActive
                  ? 'bg-blue-600 border-blue-600 text-white shadow-sm'
                  : darkMode
                    ? 'bg-slate-800/80 border-slate-700/80 text-slate-300 hover:bg-slate-800 hover:border-slate-600'
                    : 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100'
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-white' : 'text-blue-500 dark:text-sky-400'}`} />
              <span>{preset.label}</span>
            </button>
          );
        })}
      </div>

      {/* Collapsible Advanced Filters Drawer */}
      {showAdvanced && (
        <div className={`p-4 md:p-5 rounded-2xl border space-y-4 animate-in fade-in slide-in-from-top-2 duration-200 ${
          darkMode ? 'bg-slate-800/70 border-slate-700' : 'bg-slate-50 border-slate-200'
        }`}>
          <div className="flex items-center justify-between border-b pb-2 border-slate-200 dark:border-slate-700">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
              <SlidersHorizontal className="w-3.5 h-3.5 text-blue-500" />
              <span>Cấu hình bộ lọc chuyên sâu</span>
            </h4>
            {hasActiveFilters && (
              <button
                onClick={resetFilters}
                className="text-xs font-bold text-red-500 hover:underline flex items-center gap-1"
              >
                <RotateCcw className="w-3 h-3" />
                <span>Đặt lại tất cả</span>
              </button>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
            {/* LitScore Range Filter */}
            <div className="space-y-1.5">
              <label className="font-bold flex items-center justify-between text-slate-700 dark:text-slate-300">
                <span>Điểm LitScore tối thiểu:</span>
                <span className="text-blue-600 dark:text-sky-400 font-extrabold">{minLitScore}/100</span>
              </label>
              <input
                type="range"
                min="0"
                max="100"
                step="5"
                value={minLitScore}
                onChange={(e) => setMinLitScore(Number(e.target.value))}
                className="w-full accent-blue-600 cursor-pointer"
              />
              <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                <span>0 (Tất cả)</span>
                <span>50</span>
                <span>100 (Uy tín cao)</span>
              </div>
            </div>

            {/* Citations Min Filter */}
            <div className="space-y-1.5">
              <label className="font-bold text-slate-700 dark:text-slate-300">
                Số lượt trích dẫn (Min):
              </label>
              <select
                value={minCitations}
                onChange={(e) => setMinCitations(Number(e.target.value))}
                className={`w-full p-2.5 border rounded-xl font-bold focus:outline-none ${
                  darkMode ? 'bg-slate-900 border-slate-700 text-white' : 'bg-white border-slate-300 text-slate-800'
                }`}
              >
                <option value={0}>Tất cả lượt trích dẫn</option>
                <option value={10}>≥ 10 trích dẫn</option>
                <option value={50}>≥ 50 trích dẫn</option>
                <option value={100}>≥ 100 trích dẫn</option>
                <option value={500}>≥ 500 trích dẫn</option>
              </select>
            </div>

            {/* Publication Year Range Filter */}
            <div className="space-y-1.5">
              <label className="font-bold text-slate-700 dark:text-slate-300">
                Khoảng năm xuất bản:
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  placeholder="Từ năm"
                  value={startYear}
                  onChange={(e) => setStartYear(e.target.value)}
                  className={`w-full p-2 border rounded-xl font-semibold text-center focus:outline-none ${
                    darkMode ? 'bg-slate-900 border-slate-700 text-white' : 'bg-white border-slate-300 text-slate-800'
                  }`}
                />
                <span className="text-slate-400 font-bold">-</span>
                <input
                  type="number"
                  placeholder="Đến năm"
                  value={endYear}
                  onChange={(e) => setEndYear(e.target.value)}
                  className={`w-full p-2 border rounded-xl font-semibold text-center focus:outline-none ${
                    darkMode ? 'bg-slate-900 border-slate-700 text-white' : 'bg-white border-slate-300 text-slate-800'
                  }`}
                />
              </div>
            </div>

            {/* Journal Source Filter */}
            <div className="space-y-1.5">
              <label className="font-bold text-slate-700 dark:text-slate-300">
                Tạp chí / Nguồn xuất bản:
              </label>
              <select
                value={selectedJournal}
                onChange={(e) => setSelectedJournal(e.target.value)}
                className={`w-full p-2.5 border rounded-xl font-bold focus:outline-none ${
                  darkMode ? 'bg-slate-900 border-slate-700 text-white' : 'bg-white border-slate-300 text-slate-800'
                }`}
              >
                <option value="All">Tất cả nguồn ({availableJournals.length})</option>
                {availableJournals.map(j => (
                  <option key={j} value={j}>{j}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Stats Bar & Active Filter Badges */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2 border-t border-slate-100 dark:border-slate-800 text-xs">
        
        {/* Count & Status */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-bold text-slate-500 dark:text-slate-400">
            Hiển thị <strong className="text-blue-600 dark:text-sky-400 font-extrabold">{filteredCount}</strong> / {totalCount} bài báo
          </span>

          {filteredCount !== totalCount && (
            <span className="px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 font-bold text-[10px]">
              Đang áp dụng bộ lọc
            </span>
          )}
        </div>

        {/* Bulk Actions (Excel Export & Select Controls) */}
        <div className="flex items-center gap-2">
          {onExportExcel && (
            <button
              onClick={onExportExcel}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all border ${
                darkMode
                  ? 'bg-slate-800 border-slate-700 hover:bg-slate-700 text-emerald-400'
                  : 'bg-emerald-50 border-emerald-200 hover:bg-emerald-100 text-emerald-700'
              }`}
              title="Xuất kết quả đã lọc ra Excel"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Xuất Excel</span>
            </button>
          )}

          {hasActiveFilters && (
            <button
              onClick={resetFilters}
              className="text-xs font-bold text-slate-400 hover:text-red-500 transition-colors flex items-center gap-1"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Xóa bộ lọc</span>
            </button>
          )}
        </div>
      </div>

    </div>
  );
}
