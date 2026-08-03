import React from 'react';
import ChatPanel from './ChatPanel';
import VerificationPanel from './VerificationPanel';
import { Sparkles } from 'lucide-react';

export default function WorkspaceTab({ 
  workspacePapers, 
  chatMessages, 
  setChatMessages, 
  activeCitation, 
  setActiveCitation 
}) {
  return (
    <div className="space-y-4">
      {/* Top Workspace Header Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-100 text-purple-700 rounded-lg">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h2 className="font-bold text-slate-900 text-sm">Grounded Academic Workspace</h2>
            <p className="text-xs text-slate-500">
              Loaded <strong>{workspacePapers.length} papers</strong> for zero-hallucination synthesis
            </p>
          </div>
        </div>

        {/* Action Chips */}
        <div className="flex items-center gap-2 flex-wrap">
          <button className="px-3 py-1.5 bg-purple-50 hover:bg-purple-100 text-purple-700 text-xs font-bold rounded-lg border border-purple-200 transition-all">
            💡 Research Gap Detector
          </button>
          <button className="px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 text-xs font-bold rounded-lg border border-blue-200 transition-all">
            📊 Auto-Generate Comparison Table
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
          />
        </div>

        {/* RIGHT SIDE (40%): INSTANT VERIFICATION PANEL (ZERO HALLUCINATION) */}
        <div className="lg:col-span-5 space-y-4">
          <VerificationPanel activeCitation={activeCitation} />
        </div>
      </div>
    </div>
  );
}
