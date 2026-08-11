import React from 'react';
import { Search, Sparkles, History, Bot, Layers, CheckCircle2, Cpu } from 'lucide-react';

export default function Sidebar({ activeTab, setActiveTab, workspaceCount, darkMode }) {
  const menuItems = [
    { id: 'search', label: 'Truy cập & Tìm kiếm', icon: Search, badge: 'Multi-Agent' },
    { id: 'synthesis', label: 'Synthesis (RAG)', icon: Sparkles, count: workspaceCount },
    { id: 'history', label: 'Lịch sử & Dataset Logs', icon: History },
  ];

  return (
    <aside className={`w-64 border-r min-h-screen flex flex-col justify-between shrink-0 hidden md:flex transition-colors ${
      darkMode 
        ? 'bg-slate-900 border-slate-800 text-slate-200' 
        : 'bg-white border-slate-200 text-slate-800'
    }`}>
      <div>
        {/* Brand Header */}
        <div className="h-16 px-6 border-b border-slate-200 dark:border-slate-800 flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-purple-600 flex items-center justify-center text-white font-bold text-lg shadow-md">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h1 className="font-extrabold text-slate-900 dark:text-white text-base tracking-tight">LitReview Agent</h1>
            <p className="text-[10px] text-purple-600 dark:text-purple-400 font-bold uppercase tracking-wider">Multi-Agent System</p>
          </div>
        </div>

        {/* Navigation Menu */}
        <div className="p-4 space-y-1">
          <p className="px-3 text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-2">Hệ thống Multi-Agent</p>
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                  isActive
                    ? darkMode
                      ? 'bg-purple-950/60 text-purple-300 border border-purple-800 font-bold'
                      : 'bg-blue-50 text-blue-600 font-bold border border-blue-100 shadow-xs'
                    : darkMode
                      ? 'text-slate-400 hover:bg-slate-800 hover:text-white'
                      : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Icon className={`w-4 h-4 ${isActive ? 'text-blue-500 dark:text-purple-400' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <span className="text-[10px] bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300 px-2 py-0.5 rounded-full font-bold">
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

        {/* Multi-Agent Active Network List Widget */}
        <div className="px-4 py-2">
          <div className={`p-3 rounded-xl border space-y-2 text-xs ${
            darkMode ? 'bg-slate-800/60 border-slate-700/60' : 'bg-slate-50 border-slate-200'
          }`}>
            <p className="font-bold text-[11px] text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center justify-between">
              <span>Biệt đội Agents</span>
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            </p>
            
            <div className="space-y-1.5 text-[11px]">
              <div className="flex items-center justify-between font-medium">
                <span className="flex items-center gap-1.5">🕷️ ScraperAgent</span>
                <span className="text-emerald-500 font-bold">Online</span>
              </div>
              <div className="flex items-center justify-between font-medium">
                <span className="flex items-center gap-1.5">🔍 RetrieverAgent</span>
                <span className="text-emerald-500 font-bold">Online</span>
              </div>
              <div className="flex items-center justify-between font-medium">
                <span className="flex items-center gap-1.5">📝 SynthesizerAgent</span>
                <span className="text-emerald-500 font-bold">Online</span>
              </div>
              <div className="flex items-center justify-between font-medium">
                <span className="flex items-center gap-1.5">🛡️ VerifierAgent</span>
                <span className="text-emerald-500 font-bold">Online</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer System Info */}
      <div className="p-4 border-t border-slate-200 dark:border-slate-800">
        <div className={`p-3 rounded-xl border space-y-1 ${
          darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-slate-200'
        }`}>
          <div className="flex items-center justify-between text-xs">
            <span className="font-bold text-slate-700 dark:text-slate-200 flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-blue-500" /> Model Local
            </span>
            <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/60 px-1.5 py-0.5 rounded">Fine-tuned</span>
          </div>
          <p className="text-[10px] text-slate-500 dark:text-slate-400">Llama-3-8B-Instruct (GGUF)</p>
        </div>
      </div>
    </aside>
  );
}
