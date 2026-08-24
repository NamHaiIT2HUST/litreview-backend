import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import SearchTab from './components/search/SearchTab';
import WorkspaceTab from './components/workspace/WorkspaceTab';
import PersonalizedDashboard from './components/dashboard/PersonalizedDashboard';
import ResearchSetupTab from './components/setup/ResearchSetupTab';
import ExportTab from './components/export/ExportTab';
import PublicLandingPage from './components/landing/PublicLandingPage';
import AuthModal from './components/auth/AuthModal';
import NewProjectModal from './components/projects/NewProjectModal';
import OnboardingTour from './components/onboarding/OnboardingTour';
import ErrorBoundary from './components/ErrorBoundary';
import AdminDashboard from './components/admin/AdminDashboard';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ProjectProvider, useProject } from './contexts/ProjectContext';
import { LanguageProvider } from './contexts/LanguageContext';
import { useDarkMode } from './contexts/DarkModeContext';

function MainAppShell() {
  const { isAuthenticated, currentUser } = useAuth();
  const { activeProject, activeProjectId } = useProject();
  const { darkMode } = useDarkMode();

  // ── First-time User Onboarding Tour ─────────────────────────────────────
  const [isTourOpen, setIsTourOpen] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      const tourCompleted = localStorage.getItem('litreview_tour_completed');
      if (!tourCompleted) {
        const timer = setTimeout(() => {
          setIsTourOpen(true);
        }, 700);
        return () => clearTimeout(timer);
      }
    }
  }, [isAuthenticated]);

  const handleStartTour = () => {
    setIsTourOpen(true);
  };

  // ── Auth Modal & New Project Modal ──────────────────────────────────────
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authModalMode, setAuthModalMode] = useState('login');
  const [newProjectModalOpen, setNewProjectModalOpen] = useState(false);

  const handleOpenAuth = (mode = 'login') => {
    setAuthModalMode(mode);
    setAuthModalOpen(true);
  };

  // ── Active Tab ──────────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState(() => {
    const saved = localStorage.getItem('litreview_active_tab') || 'overview';
    if (['home', 'quality', 'screening'].includes(saved)) return 'overview';
    return saved;
  });

  useEffect(() => {
    localStorage.setItem('litreview_active_tab', activeTab);
  }, [activeTab]);

  // ── Sidebar Collapsed State ─────────────────────────────────────────────
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(() => {
    return localStorage.getItem('litreview_sidebar_collapsed') === 'true';
  });

  useEffect(() => {
    localStorage.setItem('litreview_sidebar_collapsed', String(isSidebarCollapsed));
  }, [isSidebarCollapsed]);

  // ── Mobile Sidebar State ────────────────────────────────────────────────
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  useEffect(() => {
    setMobileSidebarOpen(false);
  }, [activeTab]);

  // ── Project Scoped Paper State ──────────────────────────────────────────
  const [papers, setPapers] = useState(() => {
    try {
      const saved = localStorage.getItem(`litreview_papers_${activeProjectId}`);
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [selectedPaperIds, setSelectedPaperIds] = useState(() => {
    try {
      const saved = localStorage.getItem(`litreview_selected_ids_${activeProjectId}`);
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [selectedPapers, setSelectedPapers] = useState(() => {
    try {
      const saved = localStorage.getItem(`litreview_selected_papers_${activeProjectId}`);
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [workspacePapers, setWorkspacePapers] = useState(() => {
    try {
      const saved = localStorage.getItem(`litreview_workspace_papers_${activeProjectId}`);
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  // Reload project data when activeProjectId changes
  useEffect(() => {
    try {
      const savedPapers = localStorage.getItem(`litreview_papers_${activeProjectId}`);
      setPapers(savedPapers ? JSON.parse(savedPapers) : []);

      const savedSelectedIds = localStorage.getItem(`litreview_selected_ids_${activeProjectId}`);
      setSelectedPaperIds(savedSelectedIds ? JSON.parse(savedSelectedIds) : []);

      const savedSelectedPapers = localStorage.getItem(`litreview_selected_papers_${activeProjectId}`);
      setSelectedPapers(savedSelectedPapers ? JSON.parse(savedSelectedPapers) : []);

      const savedWorkspacePapers = localStorage.getItem(`litreview_workspace_papers_${activeProjectId}`);
      setWorkspacePapers(savedWorkspacePapers ? JSON.parse(savedWorkspacePapers) : []);
    } catch {
      setPapers([]);
      setSelectedPaperIds([]);
      setSelectedPapers([]);
      setWorkspacePapers([]);
    }
  }, [activeProjectId]);

  // Persist project scoped data
  useEffect(() => {
    if (activeProjectId) {
      localStorage.setItem(`litreview_papers_${activeProjectId}`, JSON.stringify(papers));
    }
  }, [papers, activeProjectId]);

  useEffect(() => {
    if (activeProjectId) {
      localStorage.setItem(`litreview_selected_ids_${activeProjectId}`, JSON.stringify(selectedPaperIds));
    }
  }, [selectedPaperIds, activeProjectId]);

  useEffect(() => {
    if (activeProjectId) {
      localStorage.setItem(`litreview_selected_papers_${activeProjectId}`, JSON.stringify(selectedPapers));
    }
  }, [selectedPapers, activeProjectId]);

  useEffect(() => {
    if (activeProjectId) {
      localStorage.setItem(`litreview_workspace_papers_${activeProjectId}`, JSON.stringify(workspacePapers));
    }
  }, [workspacePapers, activeProjectId]);

  // ── Search Meta ─────────────────────────────────────────────────────────
  const [activeCitation, setActiveCitation] = useState(null);
  const [searchResults, setSearchResults] = useState([]);
  const [searchMeta, setSearchMeta] = useState({
    provider: 'google_scholar', limit: 20,
    total_found: 0, total_confirmed: 0, total_undetermined: 0, duplicates: 0,
  });

  // ── Chat Messages ───────────────────────────────────────────────────────
  const [chatMessages, setChatMessages] = useState(() => {
    try {
      const saved = localStorage.getItem(`litreview_workspace_chat_messages_${activeProjectId}`);
      return saved ? JSON.parse(saved) : [{ sender: 'ai', text: `Chào mừng bạn đến với **LitReview Agent**! Hãy tìm kiếm trên Google Scholar, hệ thống sẽ tự động đối chiếu Scopus và chỉ giữ các bài đã xác minh.` }];
    } catch { return []; }
  });

  useEffect(() => {
    try {
      const saved = localStorage.getItem(`litreview_workspace_chat_messages_${activeProjectId}`);
      setChatMessages(saved ? JSON.parse(saved) : [{ sender: 'ai', text: `Chào mừng bạn đến với **LitReview Agent**! Hãy tìm kiếm trên Google Scholar, hệ thống sẽ tự động đối chiếu Scopus và chỉ giữ các bài đã xác minh.` }]);
    } catch {}
  }, [activeProjectId]);

  useEffect(() => {
    if (activeProjectId) {
      localStorage.setItem(`litreview_workspace_chat_messages_${activeProjectId}`, JSON.stringify(chatMessages));
    }
  }, [chatMessages, activeProjectId]);

  // ── Paper Helpers ───────────────────────────────────────────────────────
  const toggleSelectPaper = (id) => {
    if (selectedPaperIds.includes(id)) {
      setSelectedPaperIds(ids => ids.filter(i => i !== id));
      setSelectedPapers(ps => ps.filter(p => p.id !== id));
    } else {
      setSelectedPaperIds(ids => [...ids, id]);
      const paperToAdd = papers.find(p => p.id === id);
      if (paperToAdd && !selectedPapers.find(p => p.id === id)) {
        setSelectedPapers(ps => [...ps, paperToAdd]);
      }
    }
  };
  const clearSelectedPapers = () => {
    setSelectedPaperIds([]);
    setSelectedPapers([]);
  };

  // ── Dark Mode class on <html> ───────────────────────────────────────────
  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode);
  }, [darkMode]);

  // ── RENDER: Public Landing Page if not authenticated ────────────────────
  if (!isAuthenticated) {
    return (
      <>
        <PublicLandingPage onOpenAuth={handleOpenAuth} />
        <AuthModal
          isOpen={authModalOpen}
          onClose={() => setAuthModalOpen(false)}
          defaultMode={authModalMode}
        />
      </>
    );
  }

  // ── RENDER: Authenticated Workspace Shell ───────────────────────────────
  return (
    <div className={`app-shell ${darkMode ? 'dark' : ''}`}>
      
      {/* ── Sidebar ──────────────────────────────────────────────────── */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        mobileOpen={mobileSidebarOpen}
        setMobileOpen={setMobileSidebarOpen}
        isCollapsed={isSidebarCollapsed}
        setIsCollapsed={setIsSidebarCollapsed}
        onOpenNewProject={() => setNewProjectModalOpen(true)}
        onStartTour={handleStartTour}
        paperCount={papers.length}
        selectedCount={selectedPapers.length}
      />

      {/* ── Mobile Overlay ────────────────────────────────────────────── */}
      {mobileSidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/40 backdrop-blur-sm lg:hidden"
          onClick={() => setMobileSidebarOpen(false)}
        />
      )}

      {/* ── Main Content Area ─────────────────────────────────────────── */}
      <main className={`app-content ${isSidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
        <ErrorBoundary>
          <div className="animate-slide-up w-full">

            {/* Admin Dashboard */}
            {(activeTab === 'admin' || (currentUser?.role === 'admin' && activeTab === 'overview')) && (
              <div className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-10 py-6">
                <AdminDashboard darkMode={darkMode} />
              </div>
            )}

            {/* Overview / Personalized Dashboard */}
            {activeTab === 'overview' && currentUser?.role !== 'admin' && (
              <div className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-10 py-6">
                <PersonalizedDashboard
                  setActiveTab={setActiveTab}
                  onOpenNewProject={() => setNewProjectModalOpen(true)}
                  onStartTour={handleStartTour}
                />
              </div>
            )}

            {/* Research Setup Tab */}
            {activeTab === 'setup' && (
              <div className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-10 py-6">
                <ResearchSetupTab setActiveTab={setActiveTab} />
              </div>
            )}

            {/* Search & Paper Discovery Tab */}
            {activeTab === 'search' && (
              <div className="w-full">
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
                />
              </div>
            )}

            {/* AI Workspace & Synthesis Tab */}
            {activeTab === 'synthesis' && (
              <div className="w-full">
                <WorkspaceTab
                  papers={papers}
                  setPapers={setPapers}
                  selectedPapers={selectedPapers}
                  setSelectedPapers={setSelectedPapers}
                  setSelectedPaperIds={setSelectedPaperIds}
                  workspacePapers={workspacePapers}
                  setWorkspacePapers={setWorkspacePapers}
                  chatMessages={chatMessages}
                  setChatMessages={setChatMessages}
                  activeCitation={activeCitation}
                  setActiveCitation={setActiveCitation}
                />
              </div>
            )}

            {/* Export & Report Generation Tab */}
            {activeTab === 'export' && (
              <div className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-10 py-6">
                <ExportTab
                  papers={papers}
                  selectedPapers={selectedPapers}
                  workspacePapers={workspacePapers}
                />
              </div>
            )}

          </div>
        </ErrorBoundary>
      </main>

      {/* First-time User Product Onboarding Tour */}
      <OnboardingTour
        isOpen={isTourOpen}
        onClose={() => setIsTourOpen(false)}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
      />

      {/* New Project Creation Modal */}
      <NewProjectModal
        isOpen={newProjectModalOpen}
        onClose={() => setNewProjectModalOpen(false)}
      />
    </div>
  );
}

export default function App() {
  return (
    <LanguageProvider>
      <AuthProvider>
        <ProjectProvider>
          <MainAppShell />
        </ProjectProvider>
      </AuthProvider>
    </LanguageProvider>
  );
}
