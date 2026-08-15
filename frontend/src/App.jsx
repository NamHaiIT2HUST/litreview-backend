import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import SearchTab from './components/search/SearchTab';
import WorkspaceTab from './components/workspace/WorkspaceTab';
import InsightsTab from './components/insights/InsightsTab';
import HomeTab from './components/home/HomeTab';
import ResearchSetupTab from './components/setup/ResearchSetupTab';

import ExportTab from './components/export/ExportTab';
export default function App() {
  const [activeTab, setActiveTab] = useState(() => {
    const savedTab = localStorage.getItem('litreview_active_tab') || 'overview';
    // Remove old screening tab redirect
    if (savedTab === 'home' || savedTab === 'quality' || savedTab === 'screening') return 'overview';
    return savedTab;
  });

  useEffect(() => {
    localStorage.setItem('litreview_active_tab', activeTab);
  }, [activeTab]);

  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('litreview_dark_mode');
    return saved === 'true';
  });
  useEffect(() => {
    localStorage.setItem('litreview_dark_mode', String(darkMode));
  }, [darkMode]);

  // --- Persist papers & selectedPaperIds to localStorage ---
  const [papers, setPapers] = useState(() => {
    try {
      const saved = localStorage.getItem('litreview_papers');
      return saved ? JSON.parse(saved) : [];
    } catch { return []; }
  });
  const [selectedPaperIds, setSelectedPaperIds] = useState(() => {
    try {
      const saved = localStorage.getItem('litreview_selected_ids');
      return saved ? JSON.parse(saved) : [];
    } catch { return []; }
  });
  const [selectedPapers, setSelectedPapers] = useState(() => {
    try {
      const saved = localStorage.getItem('litreview_selected_papers');
      return saved ? JSON.parse(saved) : [];
    } catch { return []; }
  });
  const [workspacePapers, setWorkspacePapers] = useState(() => {
    try {
      const saved = localStorage.getItem('litreview_workspace_papers');
      return saved ? JSON.parse(saved) : [];
    } catch { return []; }
  });

  useEffect(() => {
    localStorage.setItem('litreview_papers', JSON.stringify(papers));
  }, [papers]);
  useEffect(() => {
    localStorage.setItem('litreview_selected_ids', JSON.stringify(selectedPaperIds));
  }, [selectedPaperIds]);
  useEffect(() => {
    localStorage.setItem('litreview_selected_papers', JSON.stringify(selectedPapers));
  }, [selectedPapers]);
  useEffect(() => {
    localStorage.setItem('litreview_workspace_papers', JSON.stringify(workspacePapers));
  }, [workspacePapers]);


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


  const [chatMessages, setChatMessages] = useState([
    {
      sender: 'ai',
      text: `Chào mừng bạn đến với **LitReview Agent**! Hãy tìm kiếm trên Google Scholar, hệ thống sẽ tự động đối chiếu Scopus và chỉ giữ các bài đã xác minh.`
    }
  ]);

  const toggleSelectPaper = (id) => {
    if (selectedPaperIds.includes(id)) {
      setSelectedPaperIds(selectedPaperIds.filter(item => item !== id));
      setSelectedPapers(selectedPapers.filter(p => p.id !== id));
    } else {
      setSelectedPaperIds([...selectedPaperIds, id]);
      const paperToAdd = papers.find(p => p.id === id);
      if (paperToAdd && !selectedPapers.find(p => p.id === id)) {
        setSelectedPapers([...selectedPapers, paperToAdd]);
      }
    }
  };

  const clearSelectedPapers = () => {
    setSelectedPaperIds([]);
    setSelectedPapers([]);
  };


  return (
    <div className={`min-h-screen font-sans transition-colors ${darkMode ? 'dark bg-slate-950 text-slate-100' : 'bg-slate-50 text-slate-900'}`}>
      
      <Navbar 
        activeTab={activeTab} 
        setActiveTab={setActiveTab}
        darkMode={darkMode}
        setDarkMode={setDarkMode}
      />

      {/* Main Multi-Step Navigation Content Area */}
      <main className={`mx-auto transition-all ${activeTab === 'synthesis' ? 'p-0 max-w-[1920px] w-full' : 'p-4 md:p-8'} ${activeTab === 'search' ? 'max-w-[1920px] w-full' : activeTab === 'synthesis' ? '' : 'max-w-7xl'}`}>
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
            clearSelectedPapers={clearSelectedPapers}
            selectedPapers={selectedPapers}

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
          <ExportTab
            papers={papers}
            selectedPapers={selectedPapers}
            workspacePapers={workspacePapers}
            darkMode={darkMode}
          />
        )}
      </main>
    </div>
  );
}
