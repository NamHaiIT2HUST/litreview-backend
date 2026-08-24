import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import HorizontalNavbar from './components/navigation/HorizontalNavbar';
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

  // ── Layout Mode: horizontal navbar (like image 2) vs vertical sidebar ──
  const [layoutMode, setLayoutMode] = useState(() => {
    return localStorage.getItem('litreview_layout_mode') || 'horizontal';
  });

  useEffect(() => {
    localStorage.setItem('litreview_layout_mode', layoutMode);
  }, [layoutMode]);

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

  const getDefaultWelcomeMessage = (projectName) => [
    {
      sender: 'ai',
      text: projectName
        ? `Chào mừng bạn đến với **Không gian Phân tích** cho đề tài **${projectName}**! Hãy chọn các bài báo từ phần *Tìm kiếm* để bắt đầu tổng hợp y văn có dẫn nguồn, hoặc tải lên tập tin PDF toàn văn để trích xuất sâu.`
        : `Chào mừng bạn đến với **LitReview Workspace**! Hãy chọn các bài báo từ phần *Tìm kiếm* để bắt đầu tổng hợp y văn có dẫn nguồn, hoặc tải lên tập tin PDF toàn văn để trích xuất sâu.`,
    },
  ];

  const [chatMessages, setChatMessages] = useState(() => {
    const saved = localStorage.getItem(chatMessagesKey);
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        console.error('Failed to parse saved chat messages:', e);
      }
    }
    return getDefaultWelcomeMessage(activeProject?.name);
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

      const savedChat = localStorage.getItem(chatMessagesKey);
      if (savedChat) {
        setChatMessages(JSON.parse(savedChat));
      } else {
        setChatMessages(getDefaultWelcomeMessage(activeProject?.name));
      }
    } catch {
      // ignore
    }
  }, [activeProjectId, chatMessagesKey, papersStorageKey, selectedIdsKey, selectedPapersKey, workspacePapersKey]);

  useEffect(() => {
    if (papersStorageKey) {
      localStorage.setItem(papersStorageKey, JSON.stringify(papers));
    }
  }, [papers, papersStorageKey]);

  useEffect(() => {
    if (selectedIdsKey) {
      localStorage.setItem(selectedIdsKey, JSON.stringify(selectedPaperIds));
    }
  }, [selectedPaperIds, selectedIdsKey]);

  useEffect(() => {
    if (selectedPapersKey) {
      localStorage.setItem(selectedPapersKey, JSON.stringify(selectedPapers));
    }
  }, [selectedPapers, selectedPapersKey]);

  useEffect(() => {
    if (workspacePapersKey) {
      localStorage.setItem(workspacePapersKey, JSON.stringify(workspacePapers));
    }
  }, [workspacePapers, workspacePapersKey]);

  useEffect(() => {
    if (chatMessagesKey && chatMessages) {
      localStorage.setItem(chatMessagesKey, JSON.stringify(chatMessages));
    }
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

  // ── Main Content Tab Dispatcher ─────────────────────────────────────────
  const renderMainContent = () => (
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
  );

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
    <>
      {layoutMode === 'horizontal' ? (
        <div className={`min-h-screen bg-[#F4F6F9] dark:bg-[#0B1120] text-slate-900 dark:text-slate-100 ${darkMode ? 'dark' : ''}`}>
          {/* ── Top Horizontal Navbar ─────────────────────────────────── */}
          <HorizontalNavbar
            activeTab={activeTab}
            setActiveTab={setActiveTab}
            onOpenNewProject={() => setNewProjectModalOpen(true)}
            layoutMode={layoutMode}
            setLayoutMode={setLayoutMode}
          />

          {/* ── Main Content Area (Full width) ────────────────────────── */}
          <main className="w-full min-h-[calc(100vh-4rem)]">
            {renderMainContent()}
          </main>
        </div>
      ) : (
        <div className={`app-shell ${darkMode ? 'dark' : ''}`}>
          {/* ── Vertical Sidebar ───────────────────────────────────────── */}
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
            layoutMode={layoutMode}
            setLayoutMode={setLayoutMode}
          />

          {/* ── Mobile Overlay ─────────────────────────────────────────── */}
          {mobileSidebarOpen && (
            <div
              className="fixed inset-0 z-30 bg-black/40 backdrop-blur-sm lg:hidden"
              onClick={() => setMobileSidebarOpen(false)}
            />
          )}

          {/* ── Main Content Area (Sidebar Offset) ─────────────────────── */}
          <main className={`app-content ${isSidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
            {renderMainContent()}
          </main>
        </div>
      )}

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
    </>
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
