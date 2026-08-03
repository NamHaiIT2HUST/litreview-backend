import React from 'react';
import { Search, ChevronDown, ChevronUp, SlidersHorizontal, Key } from 'lucide-react';

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
  setArticleType
}) {
  return (
    <div className="mota-card p-6 space-y-6">
      {/* Top Header Row - API Key Status */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
        <div>
          <h3 className="font-bold text-slate-800 text-sm">Xây dựng truy vấn chính</h3>
          <p className="text-xs text-slate-500">Hãy nhập từ khóa như cách bạn tìm kiếm trên Google Scholar hoặc Scopus.</p>
        </div>
        <div className="flex items-center gap-2 text-xs bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200">
          <Key className="w-3.5 h-3.5 text-blue-600" />
          <span className="font-semibold text-slate-700">Dữ liệu kết nối:</span>
          <span className="font-bold text-emerald-600">Scopus & Web of Science API</span>
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
            placeholder="Nhập từ khóa (ví dụ: 'large language models in healthcare')..."
            className="w-full pl-12 pr-4 py-3 bg-slate-50 border border-slate-300 rounded-xl focus:bg-white focus:ring-2 focus:ring-blue-600 focus:border-blue-600 text-slate-800 font-medium text-sm transition-all"
          />
        </div>
        <button className="bg-blue-600 hover:bg-blue-700 text-white font-bold px-8 py-3 rounded-xl text-sm transition-all shadow-sm">
          Tìm kiếm
        </button>
      </div>

      {/* Toggle Advanced Filters Button (AIoT Lab Style) */}
      <div className="text-center">
        <button
          onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
          className="inline-flex items-center gap-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold px-6 py-2 rounded-lg text-xs transition-all border border-slate-200"
        >
          <SlidersHorizontal className="w-3.5 h-3.5" />
          <span>Bộ lọc khác {showAdvancedFilters ? '↑' : '↓'}</span>
        </button>
      </div>

      {/* Collapsible Advanced Filters Panel (Identical Layout to AIoT Lab) */}
      {showAdvancedFilters && (
        <div className="pt-6 border-t border-slate-200 space-y-6">
          
          {/* Section 1: Bộ lọc Xuất bản */}
          <div>
            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider border-b border-slate-100 pb-2 mb-4">
              Bộ lọc Xuất bản
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Tác giả</label>
                <input
                  type="text"
                  placeholder="ví dụ: Smith J"
                  className="w-full p-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Tạp chí</label>
                <input
                  type="text"
                  placeholder="ví dụ: Lancet, Nature"
                  className="w-full p-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Loại bài báo</label>
                <select 
                  value={articleType} 
                  onChange={e => setArticleType(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg bg-white"
                >
                  <option value="All">Tất cả các loại</option>
                  <option value="Review">Systematic Review</option>
                  <option value="Clinical Study">Clinical Study / Trial</option>
                  <option value="Meta-Analysis">Meta-Analysis</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Ngôn ngữ</label>
                <select 
                  value={language} 
                  onChange={e => setLanguage(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-lg bg-white"
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
            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider border-b border-slate-100 pb-2 mb-3">
              Bộ lọc Thời gian
            </h4>
            <div className="flex flex-wrap items-center gap-6 text-xs text-slate-700">
              {[
                { id: 'any', label: 'Bất kỳ' },
                { id: '1', label: '1 năm' },
                { id: '5', label: '5 năm' },
                { id: '10', label: '10 năm' },
              ].map(opt => (
                <label key={opt.id} className="flex items-center gap-2 font-medium cursor-pointer">
                  <input
                    type="radio"
                    name="dateRange"
                    value={opt.id}
                    checked={dateRange === opt.id}
                    onChange={e => setDateRange(e.target.value)}
                    className="text-blue-600 focus:ring-blue-500"
                  />
                  <span>{opt.label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Section 3: Bộ lọc Đối tượng & Chất lượng */}
          <div>
            <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider border-b border-slate-100 pb-2 mb-3">
              Bộ lọc Chất lượng & Đối tượng
            </h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs text-slate-700">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" defaultChecked className="rounded text-blue-600" />
                <span>Có tóm tắt (Abstract)</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" defaultChecked className="rounded text-blue-600" />
                <span>Toàn văn miễn phí</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" className="rounded text-blue-600" />
                <span>Chỉ mục MEDLINE</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" defaultChecked className="rounded text-blue-600" />
                <span>Loại trừ Preprints</span>
              </label>
            </div>
          </div>

        </div>
      )}
    </div>
  );
}
