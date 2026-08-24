import React from 'react';
import {
  SlidersHorizontal,
  ArrowUpDown,
  LayoutGrid,
  Table as TableIcon,
  Search,
  RotateCcw,
  X,
  Calendar,
  Quote,
  FileText,
  Download,
  ChevronDown,
} from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';

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
  const { t } = useLanguage();

  const presets = [
    { id: 'all',       label: t('search.filter_all'),    icon: FileText },
    { id: 'recent',    label: t('search.filter_new'),    icon: Calendar },
    { id: 'top_cited', label: t('search.filter_cited'),  icon: Quote },
    { id: 'has_tldr',  label: t('search.filter_tldr'),   icon: FileText },
  ];

  return (
    <div className="space-y-3">
      {/* ── Top Row: Search + Sort + View ─────────────────────────────── */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
        
        {/* Search input */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-400" />
          <input
            type="text"
            value={inResultQuery}
            onChange={e => setInResultQuery(e.target.value)}
            placeholder={t('search.filter_placeholder')}
            className="input input-sm pl-9 pr-8"
          />
          {inResultQuery && (
            <button
              onClick={() => setInResultQuery('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 p-0.5 rounded text-surface-400 hover:text-surface-600 dark:hover:text-surface-300 transition-colors"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Sort Dropdown */}
        <div className="relative">
          <ArrowUpDown className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-surface-400 pointer-events-none" />
          <select
            value={sortBy}
            onChange={e => setSortBy(e.target.value)}
            className="input input-sm pl-8 pr-7 cursor-pointer appearance-none min-w-[160px]"
          >
            <option value="source_order">Relevance</option>
            <option value="year_desc">Year (Newest)</option>
            <option value="year_asc">Year (Oldest)</option>
            <option value="citations_desc">Citations (Most)</option>
            <option value="title_asc">Title (A–Z)</option>
          </select>
          <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-surface-400 pointer-events-none" />
        </div>

        {/* View Mode Toggle */}
        <div className="hidden sm:flex items-center gap-0.5 p-1 rounded-xl bg-surface-100 dark:bg-surface-800 border border-surface-200 dark:border-surface-700">
          <button
            onClick={() => setViewMode('grid')}
            className={`p-1.5 rounded-lg transition-all ${
              viewMode === 'grid'
                ? 'bg-white dark:bg-surface-700 text-primary-600 dark:text-primary-400 shadow-xs'
                : 'text-surface-400 hover:text-surface-600 dark:hover:text-surface-300'
            }`}
            title="Grid view"
          >
            <LayoutGrid className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setViewMode('table')}
            className={`p-1.5 rounded-lg transition-all ${
              viewMode === 'table'
                ? 'bg-white dark:bg-surface-700 text-primary-600 dark:text-primary-400 shadow-xs'
                : 'text-surface-400 hover:text-surface-600 dark:hover:text-surface-300'
            }`}
            title="Table view"
          >
            <TableIcon className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Advanced Filters Toggle */}
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className={`btn btn-sm ${
            showAdvanced || hasActiveFilters
              ? 'bg-primary-50 text-primary-700 border border-primary-200 dark:bg-primary-950 dark:text-primary-300 dark:border-primary-800'
              : 'btn-secondary'
          }`}
        >
          <SlidersHorizontal className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">{t('search.advanced_filter')}</span>
          {hasActiveFilters && <span className="w-1.5 h-1.5 rounded-full bg-primary-500" />}
        </button>

        {/* Export */}
        <button
          onClick={onExportExcel}
          disabled={filteredCount === 0}
          className="btn btn-sm btn-secondary"
          title={t('search.export_excel')}
        >
          <Download className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">{t('search.export_excel')}</span>
        </button>
      </div>

      {/* ── Quick Filter Presets ────────────────────────────────────────── */}
      <div className="flex items-center gap-2 overflow-x-auto pb-0.5">
        <span className="text-[10px] font-bold text-surface-400 uppercase tracking-wider flex-shrink-0">
          {t('search.quick_filter')}
        </span>
        <div className="flex items-center gap-1.5">
          {presets.map(preset => {
            const Icon = preset.icon;
            const isActive = activePreset === preset.id;
            return (
              <button
                key={preset.id}
                onClick={() => setActivePreset(preset.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
                  isActive
                    ? 'bg-primary-600 text-white shadow-xs'
                    : 'bg-surface-100 dark:bg-surface-800 text-surface-600 dark:text-surface-400 hover:bg-primary-50 dark:hover:bg-primary-950 hover:text-primary-600 dark:hover:text-primary-400 border border-surface-200 dark:border-surface-700'
                }`}
              >
                <Icon className="w-3 h-3" />
                {preset.label}
              </button>
            );
          })}
        </div>

        {/* Count */}
        <div className="ml-auto flex-shrink-0 text-xs text-surface-500 font-medium">
          {filteredCount === totalCount
            ? `${totalCount} papers`
            : `${filteredCount} / ${totalCount}`}
        </div>
      </div>

      {/* ── Advanced Filters Panel ──────────────────────────────────────── */}
      {showAdvanced && (
        <div className="card p-4 animate-slide-up">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            
            {/* Citations Range */}
            <div>
              <label className="section-label block mb-2">
                Min Citations: <span className="text-primary-600 dark:text-primary-400 font-mono">{minCitations}</span>
              </label>
              <input
                type="range"
                min="0" max="1000" step="10"
                value={minCitations}
                onChange={e => setMinCitations(parseInt(e.target.value))}
                className="w-full accent-primary-600"
              />
            </div>

            {/* Year Range */}
            <div>
              <label className="section-label block mb-2">Year Range</label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  placeholder="From"
                  value={startYear}
                  onChange={e => setStartYear(e.target.value)}
                  className="input input-sm w-full"
                />
                <span className="text-surface-400 text-xs">–</span>
                <input
                  type="number"
                  placeholder="To"
                  value={endYear}
                  onChange={e => setEndYear(e.target.value)}
                  className="input input-sm w-full"
                />
              </div>
            </div>

            {/* Journal Filter */}
            <div className="lg:col-span-2">
              <label className="section-label block mb-2">Journal / Conference</label>
              <div className="flex gap-2">
                <select
                  value={selectedJournal}
                  onChange={e => setSelectedJournal(e.target.value)}
                  className="input input-sm flex-1 appearance-none"
                >
                  <option value="">All publications</option>
                  {availableJournals.map(j => (
                    <option key={j} value={j}>{j}</option>
                  ))}
                </select>
                {hasActiveFilters && (
                  <button
                    onClick={resetFilters}
                    className="btn btn-sm btn-ghost text-danger-600 dark:text-danger-400 hover:bg-danger-light dark:hover:bg-danger-dark"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span className="hidden sm:inline">Reset</span>
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
