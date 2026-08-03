import React, { useState } from 'react';
import Navbar from './components/Navbar';
import SearchEngineTab from './components/search/SearchEngineTab';
import WorkspaceTab from './components/workspace/WorkspaceTab';
import HistoryTab from './components/history/HistoryTab';
import { MOCK_PAPERS } from './data/mockPapers';

export default function App() {
  const [activeTab, setActiveTab] = useState('search'); // 'search' | 'workspace' | 'history'
  const [selectedPaperIds, setSelectedPaperIds] = useState(['WOS-2024-001', 'SCOPUS-2024-089']);
  const [workspacePapers, setWorkspacePapers] = useState([MOCK_PAPERS[0], MOCK_PAPERS[1]]);
  const [activeCitation, setActiveCitation] = useState(MOCK_PAPERS[0]);
  const [chatMessages, setChatMessages] = useState([
    {
      sender: 'ai',
      text: `Based on your **${workspacePapers.length} selected papers** from Scopus & Web of Science, here is the synthesis:\n\n1. **Clinical Diagnostics**: Large language models have reached passing-level diagnostic accuracy (over 89%) across multiple medical specialties [1]. However, clinical deployment is hindered by a baseline 11% hallucination rate in patient record synthesis [1].\n\n2. **RAG Mitigation**: To eliminate these hallucinations, recent fine-tuning methods (such as SciRAG-FineTune) enforce strict citation alignment [2]. By fine-tuning Llama-3-8B on curated academic abstracts, researchers achieved 99.4% citation accuracy [2].`
    }
  ]);

  const pushToWorkspace = () => {
    const papersToPush = MOCK_PAPERS.filter(p => selectedPaperIds.includes(p.id));
    setWorkspacePapers(papersToPush);
    if (papersToPush.length > 0) {
      setActiveCitation(papersToPush[0]);
    }
    setActiveTab('workspace');
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* NAVBAR COMPONENT */}
      <Navbar 
        activeTab={activeTab} 
        setActiveTab={setActiveTab} 
        workspaceCount={workspacePapers.length} 
      />

      {/* MAIN CONTENT AREA */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-6">
        {activeTab === 'search' && (
          <SearchEngineTab
            papers={MOCK_PAPERS}
            selectedPaperIds={selectedPaperIds}
            setSelectedPaperIds={setSelectedPaperIds}
            pushToWorkspace={pushToWorkspace}
          />
        )}

        {activeTab === 'workspace' && (
          <WorkspaceTab
            workspacePapers={workspacePapers}
            chatMessages={chatMessages}
            setChatMessages={setChatMessages}
            activeCitation={activeCitation}
            setActiveCitation={setActiveCitation}
          />
        )}

        {activeTab === 'history' && <HistoryTab />}
      </main>
    </div>
  );
}
