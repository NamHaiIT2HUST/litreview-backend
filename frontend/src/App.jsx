import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import SearchTab from './components/search/SearchTab';
import UploadTab from './components/upload/UploadTab';
import WorkspaceTab from './components/workspace/WorkspaceTab';
import InsightsTab from './components/insights/InsightsTab';
import HomeTab from './components/home/HomeTab';
import ResearchSetupTab from './components/setup/ResearchSetupTab';

import ScreeningTab from './components/screening/ScreeningTab';
import ExportTab from './components/export/ExportTab';

export default function App() {
  const [activeTab, setActiveTab] = useState(() => {
    const savedTab = localStorage.getItem('litreview_active_tab') || 'overview';
    return savedTab === 'home' || savedTab === 'quality' ? 'overview' : savedTab;
  }); // 'overview' | 'setup' | 'search' | 'screening' | 'library' | 'synthesis' | 'export'

  useEffect(() => {
    localStorage.setItem('litreview_active_tab', activeTab);
  }, [activeTab]);

  const [darkMode, setDarkMode] = useState(false);
  const [papers, setPapers] = useState([]);
  const [selectedPaperIds, setSelectedPaperIds] = useState([]);
  const [workspacePapers, setWorkspacePapers] = useState([]);
  const [activeCitation, setActiveCitation] = useState(null);
  const [chatMessages, setChatMessages] = useState([
    {
      sender: 'ai',
      text: `Chào mừng bạn đến với **LitReview Agent**! Hãy tìm Top 20 bằng Google Scholar, đối chiếu Scopus, rồi đưa bài đã chọn sang Screening và Synthesis.`
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
        {activeTab === 'overview' && (
          <HomeTab setActiveTab={setActiveTab} darkMode={darkMode} />
        )}

        {activeTab === 'setup' && (
          <ResearchSetupTab setActiveTab={setActiveTab} darkMode={darkMode} />
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

        {activeTab === 'screening' && (
          <ScreeningTab
            papers={papers}
            setPapers={setPapers}
            darkMode={darkMode}
          />
        )}

        {activeTab === 'library' && (
          <UploadTab
            selectedPapers={selectedPapers}
            workspacePapers={workspacePapers}
            setWorkspacePapers={setWorkspacePapers}
            setActiveTab={setActiveTab}
            darkMode={darkMode}
          />
        )}

        {activeTab === 'synthesis' && (
          <WorkspaceTab
            workspacePapers={workspacePapers}
            chatMessages={chatMessages}
            setChatMessages={setChatMessages}
            activeCitation={activeCitation}
            setActiveCitation={setActiveCitation}
            darkMode={darkMode}
          />
        )}

        {activeTab === 'export' && (
          <ExportTab
            papers={papers}
            workspacePapers={workspacePapers}
            darkMode={darkMode}
          />
        )}
      </main>
    </div>
  );
}
