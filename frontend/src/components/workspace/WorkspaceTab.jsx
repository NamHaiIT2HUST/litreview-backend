import React from 'react';
import ChatPanel from './ChatPanel';
import VerificationPanel from './VerificationPanel';
import { Sparkles, Bot } from 'lucide-react';

export default function WorkspaceTab({ 
  workspacePapers, 
  chatMessages, 
  setChatMessages, 
  activeCitation, 
  setActiveCitation,
  darkMode
}) {
  return (
    <div className="space-y-4">
      {/* Top Workspace Header Bar */}
      <div className={`p-4 rounded-2xl border transition-colors flex flex-col sm:flex-row items-center justify-between gap-4 ${
        darkMode ? 'bg-slate-800 border-slate-700 text-white' : 'bg-white border-slate-200 text-slate-900'
      }`}>
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-100 dark:bg-purple-950 text-purple-600 dark:text-purple-300 rounded-xl">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h2 className="font-bold text-sm">Multi-Agent LitReview Workspace</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Đã nạp <strong>{workspacePapers.length} bài báo</strong> vào RetrieverAgent & SynthesizerAgent
            </p>
          </div>
        </div>

        {/* Action Chips */}
        <div className="flex items-center gap-2 flex-wrap">
          <button className="px-3 py-1.5 bg-purple-50 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 text-xs font-bold rounded-xl border border-purple-200 dark:border-purple-800 hover:bg-purple-100 transition-all">
            💡 Biệt đội Detect Research Gaps
          </button>
          <button className="px-3 py-1.5 bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 text-xs font-bold rounded-xl border border-blue-200 dark:border-blue-800 hover:bg-blue-100 transition-all">
            📊 Tự động vẽ Bảng so sánh
          </button>
        </div>
      </div>

      {/* SPLIT SCREEN LAYOUT */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* LEFT SIDE (60%): CHAT & SYNTHESIS */}
        <div className="lg:col-span-7 space-y-4">
          <ChatPanel
            workspacePapers={workspacePapers}
            chatMessages={chatMessages}
            setChatMessages={setChatMessages}
            activeCitation={activeCitation}
            setActiveCitation={setActiveCitation}
            darkMode={darkMode}
          />
        </div>

        {/* RIGHT SIDE (40%): INSTANT VERIFICATION PANEL (ZERO HALLUCINATION) */}
        <div className="lg:col-span-5 space-y-4">
          <VerificationPanel 
            activeCitation={activeCitation} 
            darkMode={darkMode}
          />
        </div>
      </div>
    </div>
  );
}
