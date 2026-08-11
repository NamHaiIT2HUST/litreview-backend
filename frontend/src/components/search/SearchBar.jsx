import React from 'react';
import { Search, SlidersHorizontal, Cpu, Bot } from 'lucide-react';

export default function SearchBar({ 
  searchQuery, 
  setSearchQuery, 
  showAdvancedFilters, 
  setShowAdvancedFilters,
  dateRange,
  setDateRange,
  language,
  setLanguage,
  articleType,
  setArticleType,
  darkMode
}) {
  return (
    <div className={`p-6 rounded-2xl border transition-colors space-y-6 ${
      darkMode ? 'bg-slate-800 border-slate-700 text-white' : 'bg-white border-slate-200 text-slate-800'
    }`}>
      {/* Top Header Row - Multi-Agent Engine Status */}
      <div className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b ${
        darkMode ? 'border-slate-700' : 'border-slate-100'
      }`}>
        <div>
          <h3 className="font-bold text-sm flex items-center gap-2">
            <span>Xây dựng truy vấn tìm kiếm Multi-Agent</span>
            <span className="text-[10px] font-extrabold bg-blue-100 dark:bg-blue-900/60 text-blue-700 dark:text-blue-300 px-2 py-0.5 rounded-full">Google Scholar Top 20</span>
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">Gõ từ khóa khoa học để biệt đội Agents tự động thu thập và sàng lọc bài báo.</p>
        </div>
        <div className={`flex items-center gap-2 text-xs px-3 py-1.5 rounded-xl border ${
          darkMode ? 'bg-slate-900 border-slate-700 text-slate-300' : 'bg-slate-50 border-slate-200 text-slate-700'
        }`}>
          <Bot className="w-3.5 h-3.5 text-purple-500" />
          <span className="font-semibold">Engine:</span>
          <span className="font-bold text-purple-600 dark:text-purple-400">ScraperAgent + RetrieverAgent</span>
        </div>
      </div>

      {/* Main Search Input */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="w-5 h-5 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Nhập chủ đề nghiên cứu (ví dụ: 'large language models in medical diagnostics')..."
            className={`w-full pl-12 pr-4 py-3 border rounded-xl font-medium text-sm transition-all focus:outline-none focus:ring-2 focus:ring-purple-500 ${
              darkMode 
                ? 'bg-slate-900 border-slate-700 text-white placeholder-slate-500' 
                : 'bg-slate-50 border-slate-300 text-slate-800 placeholder-slate-400'
            }`}
          />
        </div>
        <button className="bg-gradient-to-r from-blue-600 to-purple-600 hover:opacity-95 text-white font-bold px-8 py-3 rounded-xl text-sm transition-all shadow-md">
          Chạy Multi-Agent Search
        </button>
      </div>

      {/* Toggle Advanced Filters Button */}
      <div className="text-center">
        <button
          onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
          className={`inline-flex items-center gap-2 font-semibold px-6 py-2 rounded-xl text-xs transition-all border ${
            darkMode 
              ? 'bg-slate-700/60 hover:bg-slate-700 text-slate-200 border-slate-600' 
              : 'bg-slate-100 hover:bg-slate-200 text-slate-700 border-slate-200'
          }`}
        >
          <SlidersHorizontal className="w-3.5 h-3.5" />
          <span>Bộ lọc nghiên cứu chuyên sâu {showAdvancedFilters ? '↑' : '↓'}</span>
        </button>
      </div>

      {/* Collapsible Advanced Filters Panel */}
      {showAdvancedFilters && (
        <div className={`pt-6 border-t space-y-6 ${darkMode ? 'border-slate-700' : 'border-slate-200'}`}>
          {/* Section 1: Bộ lọc Xuất bản */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider pb-2 mb-4 border-b border-slate-200/40">
              Bộ lọc Xuất bản & Tác giả
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-xs">
              <div>
                <label className="block font-semibold mb-1">Tác giả</label>
                <input
                  type="text"
                  placeholder="ví dụ: Smith J"
                  className={`w-full p-2 border rounded-lg ${
                    darkMode ? 'bg-slate-900 border-slate-700 text-white' : 'bg-white border-slate-300'
                  }`}
                />
              </div>

              <div>
                <label className="block font-semibold mb-1">Tạp chí khoa học</label>
                <input
                  type="text"
                  placeholder="ví dụ: Lancet, Nature"
                  className={`w-full p-2 border rounded-lg ${
                    darkMode ? 'bg-slate-900 border-slate-700 text-white' : 'bg-white border-slate-300'
                  }`}
                />
              </div>

              <div>
                <label className="block font-semibold mb-1">Loại bài báo</label>
                <select 
                  value={articleType} 
                  onChange={e => setArticleType(e.target.value)}
                  className={`w-full p-2 border rounded-lg ${
                    darkMode ? 'bg-slate-900 border-slate-700 text-white' : 'bg-white border-slate-300'
                  }`}
                >
                  <option value="All">Tất cả các loại</option>
                  <option value="Review">Systematic Review</option>
                  <option value="Clinical Study">Clinical Study / Trial</option>
                  <option value="Meta-Analysis">Meta-Analysis</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold mb-1">Ngôn ngữ</label>
                <select 
                  value={language} 
                  onChange={e => setLanguage(e.target.value)}
                  className={`w-full p-2 border rounded-lg ${
                    darkMode ? 'bg-slate-900 border-slate-700 text-white' : 'bg-white border-slate-300'
                  }`}
                >
                  <option value="english">Tiếng Anh</option>
                  <option value="vietnamese">Tiếng Việt</option>
                  <option value="all">Tất cả ngôn ngữ</option>
                </select>
              </div>
            </div>
          </div>

          {/* Section 2: Bộ lọc Thời gian */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider pb-2 mb-3 border-b border-slate-200/40">
              Bộ lọc Khoảng thời gian
            </h4>
            <div className="flex flex-wrap items-center gap-6 text-xs">
              {[
                { id: 'any', label: 'Tất cả các năm' },
                { id: '1', label: '1 năm gần nhất' },
                { id: '5', label: '5 năm gần nhất' },
                { id: '10', label: '10 năm gần nhất' },
              ].map(opt => (
                <label key={opt.id} className="flex items-center gap-2 font-medium cursor-pointer">
                  <input
                    type="radio"
                    name="dateRange"
                    value={opt.id}
                    checked={dateRange === opt.id}
                    onChange={e => setDateRange(e.target.value)}
                    className="text-purple-600 focus:ring-purple-500"
                  />
                  <span>{opt.label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Section 3: Bộ lọc Chất lượng */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider pb-2 mb-3 border-b border-slate-200/40">
              Bộ lọc Chất lượng Dữ liệu
            </h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" defaultChecked className="rounded text-purple-600" />
                <span>Có tóm tắt (Abstract)</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" defaultChecked className="rounded text-purple-600" />
                <span>Toàn văn miễn phí</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" className="rounded text-purple-600" />
                <span>Chỉ mục MEDLINE</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" defaultChecked className="rounded text-purple-600" />
                <span>Loại trừ Preprints</span>
              </label>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
