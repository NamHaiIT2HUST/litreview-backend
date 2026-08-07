import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import SearchTab from './components/search/SearchTab';
import UploadTab from './components/upload/UploadTab';
import WorkspaceTab from './components/workspace/WorkspaceTab';
import InsightsTab from './components/insights/InsightsTab';
import HomeTab from './components/home/HomeTab';
export default function App() {
  const [activeTab, setActiveTab] = useState(() => {
    return localStorage.getItem('litreview_active_tab') || 'home';
  }); // 'home' | 'search' | 'upload' | 'workspace' | 'insights'

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
      text: `Chào mừng bạn đến với **LitReview Agent**! Hãy tra cứu bài báo ở bước 1 và đưa vào AI Workspace để bắt đầu phân tích.`
    }
  ]);

  const toggleSelectPaper = async (id) => {
    const isSelecting = !selectedPaperIds.includes(id);

    if (selectedPaperIds.includes(id)) {
      setSelectedPaperIds(selectedPaperIds.filter(item => item !== id));
    } else {
      setSelectedPaperIds([...selectedPaperIds, id]);
    }

    // Khi người dùng chọn Keep paper (Thêm vào AI Workspace), tự động trigger Quality Check API
    if (isSelecting) {
      try {
        const res = await fetch(`http://localhost:8000/api/v1/papers/${id}/quality-check`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });
        if (res.ok) {
          const updated = await res.json();
          setPapers(prevPapers => prevPapers.map(p => {
            if (p.id === id || p.id === updated.external_id) {
              return {
                ...p,
                issn: updated.issn,
                scopus_status: updated.scopus_status,
                scopus_quartile: updated.scopus_quartile,
                coverage_year_status: updated.coverage_year_status
              };
            }
            return p;
          }));
        }
      } catch (err) {
        console.warn('Quality check trigger failed:', err);
      }
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
            workspacePapers={workspacePapers}
            setWorkspacePapers={setWorkspacePapers}
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
