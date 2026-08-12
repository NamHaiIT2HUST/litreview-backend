import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import SearchTab from './components/search/SearchTab';
import WorkspaceTab from './components/workspace/WorkspaceTab';
import InsightsTab from './components/insights/InsightsTab';
import HomeTab from './components/home/HomeTab';
import ResearchSetupTab from './components/setup/ResearchSetupTab';

export default function App() {
  const [activeTab, setActiveTab] = useState(() => {
    const savedTab = localStorage.getItem('litreview_active_tab') || 'overview';
    return savedTab === 'home' || savedTab === 'quality' ? 'overview' : savedTab;
  }); // 'overview' | 'setup' | 'search' | 'screening' | 'library' | 'synthesis' | 'export'

  useEffect(() => {
    localStorage.setItem('litreview_active_tab', activeTab);
  }, [activeTab]);

  const [darkMode, setDarkMode] = useState(() => {
    return localStorage.getItem('litreview_dark_mode') === 'true';
  });
  
  const [papers, setPapers] = useState([]);
  const [selectedPaperIds, setSelectedPaperIds] = useState([]);
  const [workspacePapers, setWorkspacePapers] = useState(() => {
    const saved = sessionStorage.getItem('litreview_workspace_papers');
    return saved ? JSON.parse(saved) : [];
  });
  const [activeCitation, setActiveCitation] = useState(null);
  const [searchResults, setSearchResults] = useState([]);
  const [searchMeta, setSearchMeta] = useState({
    provider: 'google_scholar',
    limit: 20,
    total_found: 0,
    total_confirmed: 0,
    total_undetermined: 0,
    duplicates: 0,
  });

  useEffect(() => {
    localStorage.setItem('litreview_dark_mode', darkMode);
  }, [darkMode]);

  useEffect(() => {
    sessionStorage.setItem('litreview_workspace_papers', JSON.stringify(workspacePapers));
  }, [workspacePapers]);
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
            searchResults={searchResults}
            setSearchResults={setSearchResults}
            searchMeta={searchMeta}
            setSearchMeta={setSearchMeta}
            selectedPaperIds={selectedPaperIds}
            toggleSelectPaper={toggleSelectPaper}
            workspacePapers={workspacePapers}
            setWorkspacePapers={setWorkspacePapers}
            setActiveTab={setActiveTab}
            darkMode={darkMode}
          />
        )}

        {activeTab === 'synthesis' && (
          <WorkspaceTab
            papers={papers}
            setPapers={setPapers}
            selectedPapers={selectedPapers}
            setSelectedPaperIds={setSelectedPaperIds}
            workspacePapers={workspacePapers}
            setWorkspacePapers={setWorkspacePapers}
            chatMessages={chatMessages}
            setChatMessages={setChatMessages}
            activeCitation={activeCitation}
            setActiveCitation={setActiveCitation}
            darkMode={darkMode}
          />
        )}

        {activeTab === 'export' && (
          <div className="bg-white dark:bg-slate-900 rounded-xl shadow p-6 border dark:border-slate-800">
            <h2 className="text-2xl font-bold mb-4">Module 7: Export</h2>
            <p className="text-slate-600 dark:text-slate-400 mb-4">Export your findings and citations to BibTeX/CSV.</p>
          </div>
        )}
      </main>
    </div>
  );
}
