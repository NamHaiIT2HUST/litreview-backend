import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
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
      text: `Dựa trên **${workspacePapers.length} bài báo đã chọn** từ Scopus & Web of Science, dưới đây là tổng quan tài liệu (Literature Synthesis):\n\n1. **Chẩn đoán Lâm sàng**: Các mô hình ngôn ngữ lớn đạt độ chính xác chẩn đoán trên 89% ở 15 chuyên khoa [1]. Tuy nhiên, ứng dụng thực tế vẫn cần giám sát do tỷ lệ ảo giác 11% [1].\n\n2. **Khắc phục Ảo giác (RAG)**: Thử nghiệm Fine-tune Llama-3-8B với nhãn trích dẫn nghiêm ngặt (SciRAG) đạt độ chính xác trích dẫn 99.4% [2].`
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
    <div className="flex min-h-screen bg-slate-100 font-sans">
      {/* 1. MotaAdmin Left Sidebar */}
      <Sidebar 
        activeTab={activeTab} 
        setActiveTab={setActiveTab} 
        workspaceCount={workspacePapers.length} 
      />

      {/* 2. Right Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <Navbar 
          activeTab={activeTab} 
          setActiveTab={setActiveTab} 
        />

        <main className="flex-1 p-4 md:p-6 max-w-7xl w-full mx-auto">
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
    </div>
  );
}
