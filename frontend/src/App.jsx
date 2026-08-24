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
    if (currentUser?.role === 'admin' && activeTab !== 'admin' && activeTab !== 'overview') {
      setActiveTab('admin');
    }
    localStorage.setItem('litreview_active_tab', activeTab);
  }, [activeTab, currentUser]);

  // ── Sidebar Collapsed State ─────────────────────────────────────────────
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(() => {
    return localStorage.getItem('litreview_sidebar_collapsed') === 'true';
  });

  useEffect(() => {
    localStorage.setItem('litreview_sidebar_collapsed', String(isSidebarCollapsed));
  }, [isSidebarCollapsed]);

  // ── Mobile Sidebar State ────────────────────────────────────────────────
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  // ── Project-Scoped Papers & State ───────────────────────────────────────
  const papersStorageKey = activeProjectId
    ? `litreview_papers_${activeProjectId}`
    : 'litreview_papers';
  const selectedIdsKey = activeProjectId
    ? `litreview_selected_ids_${activeProjectId}`
    : 'litreview_selected_ids';
  const selectedPapersKey = activeProjectId
    ? `litreview_selected_papers_${activeProjectId}`
    : 'litreview_selected_papers';
  const workspacePapersKey = activeProjectId
    ? `litreview_workspace_papers_${activeProjectId}`
    : 'litreview_workspace_papers';
  const chatMessagesKey = activeProjectId
    ? `litreview_workspace_chat_${activeProjectId}`
    : 'litreview_workspace_chat_messages';

  const [papers, setPapers] = useState(() => {
    try {
      const saved = localStorage.getItem(papersStorageKey);
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [selectedPaperIds, setSelectedPaperIds] = useState(() => {
    try {
      const saved = localStorage.getItem(selectedIdsKey);
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [selectedPapers, setSelectedPapers] = useState(() => {
    try {
      const saved = localStorage.getItem(selectedPapersKey);
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [workspacePapers, setWorkspacePapers] = useState(() => {
    try {
      const saved = localStorage.getItem(workspacePapersKey);
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  // Switch project data when active project changes
  useEffect(() => {
    try {
      const savedPapers = localStorage.getItem(papersStorageKey);
      setPapers(savedPapers ? JSON.parse(savedPapers) : []);

      const savedIds = localStorage.getItem(selectedIdsKey);
      setSelectedPaperIds(savedIds ? JSON.parse(savedIds) : []);

      const savedSelected = localStorage.getItem(selectedPapersKey);
      setSelectedPapers(savedSelected ? JSON.parse(savedSelected) : []);

      const savedWs = localStorage.getItem(workspacePapersKey);
      setWorkspacePapers(savedWs ? JSON.parse(savedWs) : []);
    } catch {
      // ignore
    }
  }, [activeProjectId]);

  useEffect(() => {
    localStorage.setItem(papersStorageKey, JSON.stringify(papers));
  }, [papers, papersStorageKey]);

  useEffect(() => {
    localStorage.setItem(selectedIdsKey, JSON.stringify(selectedPaperIds));
  }, [selectedPaperIds, selectedIdsKey]);

  useEffect(() => {
    localStorage.setItem(selectedPapersKey, JSON.stringify(selectedPapers));
  }, [selectedPapers, selectedPapersKey]);

  useEffect(() => {
    localStorage.setItem(workspacePapersKey, JSON.stringify(workspacePapers));
  }, [workspacePapers, workspacePapersKey]);

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

  const [chatMessages, setChatMessages] = useState(() => {
    const saved = localStorage.getItem(chatMessagesKey);
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        console.error('Failed to parse saved chat messages:', e);
      }
    }
    return [
      {
        sender: 'ai',
        text: `Chào mừng bạn đến với **LitReview AI Workspace**! Hãy chọn các bài báo từ phần *Tìm kiếm* để bắt đầu tổng hợp y văn có dẫn nguồn, hoặc tải lên tập tin PDF toàn văn để trích xuất sâu.`,
      },
    ];
  });

  useEffect(() => {
    localStorage.setItem(chatMessagesKey, JSON.stringify(chatMessages));
  }, [chatMessages, chatMessagesKey]);

  const toggleSelectPaper = (id) => {
    if (selectedPaperIds.includes(id)) {
      setSelectedPaperIds(selectedPaperIds.filter((item) => item !== id));
      setSelectedPapers(selectedPapers.filter((p) => p.id !== id));
    } else {
      setSelectedPaperIds([...selectedPaperIds, id]);
      const paperToAdd = papers.find((p) => p.id === id);
      if (paperToAdd && !selectedPapers.find((p) => p.id === id)) {
        setSelectedPapers([...selectedPapers, paperToAdd]);
      }
    }
  };

  const clearSelectedPapers = () => {
    setSelectedPaperIds([]);
    setSelectedPapers([]);
  };

  // ── RENDER: Public Landing Page for unauthenticated visitors ───────────
  if (!isAuthenticated) {
    return (
      <>
        <PublicLandingPage
          onOpenAuth={handleOpenAuth}
          onExploreDemo={() => handleOpenAuth('demo')}
        />
        <AuthModal
          isOpen={authModalOpen}
          onClose={() => setAuthModalOpen(false)}
          initialMode={authModalMode}
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

            {/* Overview / Personalized Dashboard (for regular users) */}
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

      {/* Auth Modal for switching accounts */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        initialMode={authModalMode}
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
