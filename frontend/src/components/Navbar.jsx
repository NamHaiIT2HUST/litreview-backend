import React from 'react';
import { Key, User, Bell, Search, ShieldCheck } from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab }) {
  return (
    <header className="bg-white border-b border-slate-200 h-16 sticky top-0 z-40 px-6 flex items-center justify-between shadow-xs">
      {/* Left Title / Breadcrumb */}
      <div className="flex items-center gap-3">
        <h2 className="font-bold text-slate-800 text-sm md:text-base">
          {activeTab === 'search' && 'Công cụ trích xuất Google Scholar & Scopus'}
          {activeTab === 'workspace' && 'LitReview AI Workspace (Closed-Domain RAG)'}
          {activeTab === 'history' && 'Lịch sử Tìm kiếm & Tải về'}
        </h2>
        <span className="text-xs text-slate-400 hidden sm:inline">|</span>
        <span className="text-xs text-slate-500 hidden sm:inline">AIoT Lab VN Design Framework</span>
      </div>

      {/* Right User & API Control */}
      <div className="flex items-center gap-4">
        {/* API Key Modal Button */}
        <div className="flex items-center gap-2 bg-blue-50 border border-blue-200 px-3 py-1.5 rounded-lg text-xs">
          <Key className="w-3.5 h-3.5 text-blue-600" />
          <span className="font-semibold text-blue-700 hidden sm:inline">SerpAPI / Scopus Key:</span>
          <span className="font-bold text-emerald-600 bg-white px-1.5 py-0.5 rounded border border-blue-100">Đã nhập</span>
        </div>

        {/* User Profile */}
        <div className="flex items-center gap-2 pl-2 border-l border-slate-200">
          <div className="w-8 h-8 rounded-full bg-slate-800 text-white font-bold flex items-center justify-center text-xs">
            NH
          </div>
          <div className="hidden lg:block">
            <p className="text-xs font-bold text-slate-800 leading-tight">Nam Hai Nguyen</p>
            <p className="text-[10px] text-slate-400">Researcher / Admin</p>
          </div>
        </div>
      </div>
    </header>
  );
}
