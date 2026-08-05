/**
 * SearchHistoryPanel — hiển thị lịch sử search và hỗ trợ:
 *  - Xem lại danh sách lần search cũ (query, số kết quả, thời gian)
 *  - Click "Xem kết quả" để load lại papers của lần search đó
 *  - Click "Duplicate" để copy query vào ô search mà không tự chạy lại
 */
import React, { useState } from 'react';
import { History, Copy, RotateCcw, ChevronDown, ChevronUp, Clock } from 'lucide-react';

const API_BASE = 'http://localhost:8000/api/v1';
const DEFAULT_PROJECT_ID = '00000000-0000-0000-0000-000000000001';

function formatTime(isoString) {
  if (!isoString) return '';
  const d = new Date(isoString);
  return d.toLocaleString('vi-VN', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

export default function SearchHistoryPanel({
  history,           // SearchQueryRecord[]
  onLoadPapers,      // (queryId) => void — tải papers cho lần search đó
  onDuplicate,       // (queryString) => void — điền query vào ô search
  darkMode,
  loading,           // boolean — đang tải lịch sử
}) {
  const [collapsed, setCollapsed] = useState(false);
  const [duplicating, setDuplicating] = useState(null); // queryId đang duplicate
  const [loadingQueryId, setLoadingQueryId] = useState(null);

  const handleDuplicate = async (queryId, queryString) => {
    setDuplicating(queryId);
    try {
      const res = await fetch(`${API_BASE}/search-queries/${queryId}/duplicate`, {
        method: 'POST',
      });
      if (res.ok) {
        // Điền query cũ vào ô search để user chỉnh sửa
        onDuplicate(queryString);
      }
    } catch (err) {
      console.error('Duplicate failed:', err);
      // Fallback: vẫn điền query vào ô search
      onDuplicate(queryString);
    } finally {
      setDuplicating(null);
    }
  };

  const handleLoadPapers = async (queryId) => {
    setLoadingQueryId(queryId);
    try {
      await onLoadPapers(queryId);
    } finally {
      setLoadingQueryId(null);
    }
  };

  if (!history || history.length === 0) return null;

  return (
    <div className={`rounded-2xl border transition-all ${
      darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
    }`}>
      {/* Header */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className={`w-full flex items-center justify-between px-5 py-4 text-left transition-colors rounded-2xl ${
          darkMode ? 'hover:bg-slate-800/60' : 'hover:bg-slate-50'
        }`}
      >
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-blue-500" />
          <span className={`text-sm font-bold ${darkMode ? 'text-white' : 'text-slate-800'}`}>
            Lịch sử tìm kiếm
          </span>
          <span className="text-xs font-bold bg-blue-100 dark:bg-blue-900/60 text-blue-700 dark:text-blue-300 px-2 py-0.5 rounded-full">
            {history.length} lần
          </span>
        </div>
        {collapsed
          ? <ChevronDown className="w-4 h-4 text-slate-400" />
          : <ChevronUp className="w-4 h-4 text-slate-400" />
        }
      </button>

      {/* List */}
      {!collapsed && (
        <div className="px-4 pb-4 space-y-2 max-h-72 overflow-y-auto">
          {loading && (
            <p className="text-xs text-slate-400 text-center py-4">Đang tải lịch sử...</p>
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
              {/* Left: query info */}
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
                  <span className="font-bold text-blue-500">{item.result_count} kết quả</span>
                  {item.is_duplicated_from && (
                    <>
                      <span>•</span>
                      <span className="italic text-amber-500">Duplicate</span>
                    </>
                  )}
                </div>
              </div>

              {/* Right: actions */}
              <div className="flex items-center gap-2 shrink-0">
                {/* Xem kết quả */}
                <button
                  onClick={() => handleLoadPapers(item.id)}
                  disabled={loadingQueryId === item.id}
                  title="Tải lại danh sách paper của lần search này"
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all border ${
                    darkMode
                      ? 'bg-slate-700 hover:bg-slate-600 border-slate-600 text-white disabled:opacity-50'
                      : 'bg-white hover:bg-slate-100 border-slate-200 text-slate-700 disabled:opacity-50'
                  }`}
                >
                  <RotateCcw className={`w-3.5 h-3.5 ${loadingQueryId === item.id ? 'animate-spin' : ''}`} />
                  {loadingQueryId === item.id ? 'Đang tải...' : 'Xem kết quả'}
                </button>

                {/* Duplicate */}
                <button
                  onClick={() => handleDuplicate(item.id, item.query_string)}
                  disabled={duplicating === item.id}
                  title="Copy query này để chỉnh sửa"
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all border ${
                    darkMode
                      ? 'bg-blue-600/20 hover:bg-blue-600/40 border-blue-700 text-blue-300 disabled:opacity-50'
                      : 'bg-blue-50 hover:bg-blue-100 border-blue-200 text-blue-700 disabled:opacity-50'
                  }`}
                >
                  <Copy className="w-3.5 h-3.5" />
                  {duplicating === item.id ? 'Đang copy...' : 'Duplicate'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
