import React from 'react';
import { Home, Search, Sparkles, History, Settings, Database, Layers, CheckCircle2 } from 'lucide-react';

export default function Sidebar({ activeTab, setActiveTab, workspaceCount }) {
  const menuItems = [
    { id: 'search', label: 'Truy cập & Tìm kiếm', icon: Search, badge: 'Scopus/WoS' },
    { id: 'workspace', label: 'AI Workspace (RAG)', icon: Sparkles, count: workspaceCount },
    { id: 'history', label: 'Quản lý Lịch sử', icon: History },
  ];

  return (
    <aside className="w-64 bg-white border-r border-slate-200 min-h-screen flex flex-col justify-between shrink-0 hidden md:flex">
      <div>
        {/* Brand Header */}
        <div className="h-16 px-6 border-b border-slate-200 flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold text-lg shadow-sm">
            <Database className="w-5 h-5" />
          </div>
          <div>
            <h1 className="font-bold text-slate-900 text-sm tracking-tight">Scholar AI Helper</h1>
            <p className="text-[11px] text-slate-500 font-medium">AIoT Lab VN & Scopus RAG</p>
          </div>
        </div>

        {/* Navigation Menu */}
        <div className="p-4 space-y-1">
          <p className="px-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">Menu chính</p>
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-semibold transition-all ${
                  isActive
                    ? 'bg-blue-50 text-blue-600 font-bold border border-blue-100 shadow-xs'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-blue-600' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-mono">
                    {item.badge}
                  </span>
                )}
                {item.count !== undefined && item.count > 0 && (
                  <span className="w-5 h-5 bg-purple-600 text-white rounded-full text-[10px] flex items-center justify-center font-bold">
                    {item.count}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Footer System Status */}
      <div className="p-4 border-t border-slate-200 bg-slate-50/50">
        <div className="p-3 bg-white rounded-lg border border-slate-200 space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-slate-700 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" /> API Status
            </span>
            <span className="text-[10px] font-bold text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded">Active</span>
          </div>
          <p className="text-[10px] text-slate-500">Vector DB: 550 Papers Indexed</p>
        </div>
      </div>
    </aside>
  );
}
