import React, { useState } from 'react';
import Navbar from './components/Navbar';
import SearchTab from './components/search/SearchTab';
import UploadTab from './components/upload/UploadTab';
import WorkspaceTab from './components/workspace/WorkspaceTab';
import InsightsTab from './components/insights/InsightsTab';
import HomeTab from './components/home/HomeTab';
export default function App() {
  const [activeTab, setActiveTab] = useState('home'); // 'home' | 'search' | 'upload' | 'workspace' | 'insights'
  const [darkMode, setDarkMode] = useState(false);
  const [papers, setPapers] = useState([]);
  const [selectedPaperIds, setSelectedPaperIds] = useState([]);
  const [workspacePapers, setWorkspacePapers] = useState([]);
  const [activeCitation, setActiveCitation] = useState(null);
  const [chatMessages, setChatMessages] = useState([
    {
      sender: 'ai',
      text: `Chào mừng bạn đến với **LitReview Agent**! Hãy tra cứu bài báo ở bước 1 và đưa vào AI Workspace để bắt đầu phân tích.`
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
