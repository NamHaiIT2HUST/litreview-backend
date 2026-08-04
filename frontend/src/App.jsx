import React, { useState } from 'react';
import Navbar from './components/Navbar';
import SearchTab from './components/search/SearchTab';
import UploadTab from './components/upload/UploadTab';
import WorkspaceTab from './components/workspace/WorkspaceTab';
import InsightsTab from './components/insights/InsightsTab';
import HomeTab from './components/home/HomeTab';
import { MOCK_PAPERS } from './data/mockPapers';

export default function App() {
  const [activeTab, setActiveTab] = useState('home'); // 'home' | 'search' | 'upload' | 'workspace' | 'insights'
  const [darkMode, setDarkMode] = useState(false);
  const [papers, setPapers] = useState(MOCK_PAPERS);
  const [selectedPaperIds, setSelectedPaperIds] = useState(['WOS-2024-001', 'SCOPUS-2024-089']);
  const [workspacePapers, setWorkspacePapers] = useState([MOCK_PAPERS[0], MOCK_PAPERS[1]]);
  const [activeCitation, setActiveCitation] = useState(MOCK_PAPERS[0]);
  const [chatMessages, setChatMessages] = useState([
    {
      sender: 'ai',
      text: `Dựa trên **${workspacePapers.length} bài báo bạn đã tải lên hệ thống**, biệt đội Agents đã sẵn sàng hỗ trợ tra cứu như NotebookLM:\n\n1. **Chẩn đoán Lâm sàng**: Các mô hình ngôn ngữ lớn đạt độ chính xác chẩn đoán trên 89% ở 15 chuyên khoa [1]. Tuy nhiên, ứng dụng thực tế vẫn cần giám sát do tỷ lệ ảo giác 11% [1].\n\n2. **Khắc phục Ảo giác (RAG)**: Thử nghiệm Fine-tune Llama-3-8B với nhãn trích dẫn nghiêm ngặt (SciRAG) đạt độ chính xác trích dẫn 99.4% [2].`
    }
  ]);

  const toggleSelectPaper = (id) => {
    if (selectedPaperIds.includes(id)) {
      setSelectedPaperIds(selectedPaperIds.filter(item => item !== id));
    } else {
      setSelectedPaperIds([...selectedPaperIds, id]);
    }
  };

  const selectedPapers = papers.filter(p => selectedPaperIds.includes(p.id));

  return (
    <div className={`min-h-screen font-sans transition-colors ${darkMode ? 'dark bg-slate-950 text-slate-100' : 'bg-slate-50 text-slate-900'}`}>
      
      {/* VinMotion Header Bar */}
      <Navbar 
        activeTab={activeTab} 
        setActiveTab={setActiveTab}
        darkMode={darkMode}
        setDarkMode={setDarkMode}
        uploadedCount={selectedPaperIds.length}
      />

      {/* Main Multi-Step Navigation Content Area */}
      <main className="p-4 md:p-8 max-w-7xl mx-auto">
        {activeTab === 'home' && (
          <HomeTab setActiveTab={setActiveTab} darkMode={darkMode} />
        )}

        {activeTab === 'search' && (
          <SearchTab
            papers={papers}
            setPapers={setPapers}
            selectedPaperIds={selectedPaperIds}
            toggleSelectPaper={toggleSelectPaper}
            setActiveTab={setActiveTab}
            darkMode={darkMode}
          />
        )}

        {activeTab === 'upload' && (
          <UploadTab
            selectedPapers={selectedPapers}
            setActiveTab={setActiveTab}
            darkMode={darkMode}
          />
        )}

        {activeTab === 'workspace' && (
          <WorkspaceTab
            workspacePapers={workspacePapers}
            chatMessages={chatMessages}
            setChatMessages={setChatMessages}
            activeCitation={activeCitation}
            setActiveCitation={setActiveCitation}
            darkMode={darkMode}
          />
        )}

        {activeTab === 'insights' && (
          <InsightsTab
            workspacePapers={workspacePapers}
            darkMode={darkMode}
          />
        )}
      </main>
    </div>
  );
}
