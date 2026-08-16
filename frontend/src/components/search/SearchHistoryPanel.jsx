/**
 * SearchHistoryPanel — hiển thị lịch sử search:
 *  - Xem lại danh sách lần search cũ (query, số kết quả, thời gian)
 *  - Click "Xem kết quả" để load lại papers của lần search đó
 *  - Click "Duplicate" để copy query vào ô search
 *  - Supports sidebar mode (isSidebar=true) with compact layout
 */
import React, { useState } from 'react';
import { History, Copy, RotateCcw, ChevronDown, ChevronUp, Clock, Search, Trash2 } from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/v1';
const DEFAULT_PROJECT_ID = '00000000-0000-0000-0000-000000000001';

function formatTime(isoString) {
  if (!isoString) return '';
  let clean = isoString;
  if (!clean.endsWith('Z') && !clean.includes('+') && !clean.includes('-')) {
    clean += 'Z';
  }
  const d = new Date(clean);
  return d.toLocaleString('vi-VN', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

export default function SearchHistoryPanel({
  history,
  onLoadPapers,
  onDuplicate,
  onDeleteQuery,
  darkMode,
  loading,
  isSidebar = false,
}) {
  const { t } = useLanguage();
  const [collapsed, setCollapsed] = useState(false);
  const [duplicating, setDuplicating] = useState(null);
  const [loadingQueryId, setLoadingQueryId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  const handleDuplicate = async (queryId, queryString) => {
    setDuplicating(queryId);
    try {
      const res = await fetch(`${API_BASE}/search-queries/${queryId}/duplicate`, {
        method: 'POST',
      });
      if (res.ok) {
        onDuplicate(queryString);
      }
    } catch (err) {
      console.error('Duplicate failed:', err);
      onDuplicate(queryString);
    } finally {
      setDuplicating(null);
    }
  };

  const handleLoadPapers = async (queryId, queryString) => {
    setLoadingQueryId(queryId);
    try {
      await onLoadPapers(queryId, queryString);
    } finally {
      setLoadingQueryId(null);
    }
  };

  const handleDelete = async (queryId, e) => {
    if (e) e.stopPropagation();
    if (onDeleteQuery) {
      onDeleteQuery(queryId);
    }
    try {
      await fetch(`${API_BASE}/search-queries/${queryId}`, {
        method: 'DELETE',
      });
    } catch (err) {
      console.error('Delete search query failed:', err);
    }
  };

  if (!history || history.length === 0) {
    if (isSidebar) {
      return (
        <div className="text-center py-6">
          <History className="w-8 h-8 mx-auto mb-2 opacity-20 text-blue-500" />
          <p className={`text-xs font-semibold ${darkMode ? 'text-slate-500' : 'text-slate-400'}`}>
            {t('search.no_history_yet')}
          </p>
        </div>
      );
    }
    return null;
  }

  // Sidebar mode: always expanded, fixed max-height scrollable (~3 items visible)
  if (isSidebar) {
    return (
      <div className="space-y-3">
        <div className="flex items-center gap-2 mb-2">
          <History className="w-4 h-4 text-blue-500" />
          <span className={`text-sm font-bold ${darkMode ? 'text-white' : 'text-slate-800'}`}>
            {t('search.search_history')}
          </span>
          <span className="text-xs font-bold bg-blue-100 dark:bg-blue-900/60 text-blue-700 dark:text-blue-300 px-2 py-0.5 rounded-full">
            {history.length}
          </span>
        </div>

        {loading && (
          <p className="text-xs text-slate-400 text-center py-1">{t('search.loading_history')}</p>
        )}

        <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1">
          {history.map((item) => (
            <div
              key={item.id}
              className={`p-3 rounded-xl border transition-colors ${
                darkMode
                  ? 'bg-slate-800/60 border-slate-700 hover:bg-slate-700/60'
                  : 'bg-slate-50 border-slate-200 hover:bg-slate-100'
              }`}
            >
              <p className={`text-xs font-semibold truncate mb-1 ${darkMode ? 'text-slate-100' : 'text-slate-800'}`}>
                {item.query_string}
              </p>
              <div className="flex items-center gap-1.5 text-[10px] text-slate-400 mb-2">
                <Clock className="w-2.5 h-2.5" />
                <span>{formatTime(item.executed_at)}</span>
                <span>•</span>
                <span className="font-bold text-blue-500">{item.result_count} {t('search.results')}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => handleLoadPapers(item.id, item.query_string)}
                  disabled={loadingQueryId === item.id}
                  className={`flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded-lg text-[10px] font-bold transition-all border ${
                    darkMode
                      ? 'bg-slate-700 hover:bg-slate-600 border-slate-600 text-white disabled:opacity-50'
                      : 'bg-white hover:bg-slate-100 border-slate-200 text-slate-700 disabled:opacity-50'
                  }`}
                >
                  <RotateCcw className={`w-2.5 h-2.5 ${loadingQueryId === item.id ? 'animate-spin' : ''}`} />
                  {loadingQueryId === item.id ? '...' : t('search.view')}
                </button>
                <button
                  onClick={() => handleDuplicate(item.id, item.query_string)}
                  disabled={duplicating === item.id}
                  className={`flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded-lg text-[10px] font-bold transition-all border ${
                    darkMode
                      ? 'bg-blue-600/20 hover:bg-blue-600/40 border-blue-700 text-blue-300 disabled:opacity-50'
                      : 'bg-blue-50 hover:bg-blue-100 border-blue-200 text-blue-700 disabled:opacity-50'
                  }`}
                >
                  <Copy className="w-2.5 h-2.5" />
                  {duplicating === item.id ? '...' : t('search.copy')}
                </button>
                <button
                  onClick={(e) => handleDelete(item.id, e)}
                  disabled={deletingId === item.id}
                  className={`p-1.5 rounded-lg text-[10px] font-bold transition-all border ${
                    darkMode
                      ? 'bg-rose-900/30 hover:bg-rose-900/50 border-rose-800 text-rose-300 disabled:opacity-50'
                      : 'bg-rose-50 hover:bg-rose-100 border-rose-200 text-rose-600 disabled:opacity-50'
                  }`}
                  title={t('search.delete_history')}
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Default (non-sidebar) collapsible mode
  return (
    <div className={`rounded-2xl border transition-all ${
      darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
    }`}>
      <button
        onClick={() => setCollapsed(!collapsed)}
        className={`w-full flex items-center justify-between px-5 py-4 text-left transition-colors rounded-2xl ${
          darkMode ? 'hover:bg-slate-800/60' : 'hover:bg-slate-50'
        }`}
      >
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-blue-500" />
          <span className={`text-sm font-bold ${darkMode ? 'text-white' : 'text-slate-800'}`}>
            {t('search.search_history')}
          </span>
          <span className="text-xs font-bold bg-blue-100 dark:bg-blue-900/60 text-blue-700 dark:text-blue-300 px-2 py-0.5 rounded-full">
            {history.length} {t('search.times')}
          </span>
        </div>
        {collapsed
          ? <ChevronDown className="w-4 h-4 text-slate-400" />
          : <ChevronUp className="w-4 h-4 text-slate-400" />
        }
      </button>

      {!collapsed && (
        <div className="px-4 pb-4 space-y-2 max-h-72 overflow-y-auto">
          {loading && (
            <p className="text-xs text-slate-400 text-center py-4">{t('search.loading_history')}</p>
          )}
          {history.map((item) => (
            <div
              key={item.id}
              className={`p-3 rounded-xl border flex flex-col sm:flex-row sm:items-center gap-3 transition-colors ${
                darkMode
                  ? 'bg-slate-800/60 border-slate-700'
                  : 'bg-slate-50 border-slate-200'
              }`}
            >
              <div className="flex-1 min-w-0">
                <p className={`text-sm font-semibold truncate ${darkMode ? 'text-slate-100' : 'text-slate-800'}`}>
                  {item.query_string}
                </p>
                <div className="flex items-center gap-2 mt-1 text-xs text-slate-400 flex-wrap">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {formatTime(item.executed_at)}
                  </span>
                  <span>•</span>
                  <span className="font-bold text-blue-500">{item.result_count} {t('search.results')}</span>
                  {item.is_duplicated_from && (
                    <>
                      <span>•</span>
                      <span className="italic text-amber-500">Duplicate</span>
                    </>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => handleLoadPapers(item.id, item.query_string)}
                  disabled={loadingQueryId === item.id}
                  title={t('search.view_results')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all border ${
                    darkMode
                      ? 'bg-slate-700 hover:bg-slate-600 border-slate-600 text-white disabled:opacity-50'
                      : 'bg-white hover:bg-slate-100 border-slate-200 text-slate-700 disabled:opacity-50'
                  }`}
                >
                  <RotateCcw className={`w-3.5 h-3.5 ${loadingQueryId === item.id ? 'animate-spin' : ''}`} />
                  {loadingQueryId === item.id ? '...' : t('search.view_results')}
                </button>

                <button
                  onClick={() => handleDuplicate(item.id, item.query_string)}
                  disabled={duplicating === item.id}
                  title={t('search.copy')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all border ${
                    darkMode
                      ? 'bg-blue-600/20 hover:bg-blue-600/40 border-blue-700 text-blue-300 disabled:opacity-50'
                      : 'bg-blue-50 hover:bg-blue-100 border-blue-200 text-blue-700 disabled:opacity-50'
                  }`}
                >
                  <Copy className="w-3.5 h-3.5" />
                  {duplicating === item.id ? '...' : t('search.copy')}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
