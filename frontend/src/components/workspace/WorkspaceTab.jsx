import React from 'react';
import ChatPanel from './ChatPanel';
import VerificationPanel from './VerificationPanel';
import SynthesisPanel from './SynthesisPanel';
import { Bot } from 'lucide-react';

export default function WorkspaceTab({
  workspacePapers,
  chatMessages,
  setChatMessages,
  activeCitation,
  setActiveCitation,
  darkMode,
}) {
  return (
    <div className="space-y-5">
      <div className={`p-4 rounded-2xl border flex flex-col sm:flex-row items-center justify-between gap-4 ${
        darkMode ? 'bg-slate-800 border-slate-700 text-white' : 'bg-white border-slate-200 text-slate-900'
      }`}>
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-100 dark:bg-purple-950 text-purple-600 dark:text-purple-300 rounded-xl">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h2 className="font-bold text-sm">LitReview Evidence Workspace</h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {workspacePapers.length} paper có PageText/chunk provenance sẵn sàng cho RAG và Synthesis
            </p>
          </div>
        </div>
      </div>

      <SynthesisPanel
        workspacePapers={workspacePapers}
        setActiveCitation={setActiveCitation}
        darkMode={darkMode}
      />

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
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

        <div className="lg:col-span-5 space-y-4">
          <VerificationPanel activeCitation={activeCitation} darkMode={darkMode} />
        </div>
      </div>
    </div>
  );
}
