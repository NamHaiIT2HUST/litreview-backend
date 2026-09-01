import React, { useState, useEffect, useRef } from 'react';
import Sidebar from './components/Sidebar';
import HorizontalNavbar from './components/navigation/HorizontalNavbar';
import SearchTab from './components/search/SearchTab';
import WorkspaceTab from './components/workspace/WorkspaceTab';
import PersonalizedDashboard from './components/dashboard/PersonalizedDashboard';
import ResearchSetupTab from './components/setup/ResearchSetupTab';
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
    // The tour walks through researcher-only tabs (Setup/Search/Synthesis) and
    // steers activeTab as it goes -- for an admin account, whose navbar only
    // ever exposes the Admin tab, that steering fights the admin redirect
    // effect below and leaves the user stuck bouncing off the Admin tab.
    if (isAuthenticated && currentUser?.role !== 'admin') {
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

  // ── Always remember/persist current active tab across refreshes ───────────
  // Valid tabs the shell actually knows how to render (see the switch below).
  // A tab that existed in a previous release (e.g. 'export', removed later)
  // can still be sitting in a user's sessionStorage from before that release
  // shipped -- restoring it unchecked renders an empty main content area with
  // no tab matching. Validate against the known-render list and fall back to
  // 'overview' instead.
  const VALID_TABS = ['admin', 'overview', 'setup', 'search', 'chat', 'synthesis', 'data_analysis', 'analyze'];
  const [activeTab, setActiveTabState] = useState(() => {
    try {
      const stored = sessionStorage.getItem('litreview_active_tab');
      return stored && VALID_TABS.includes(stored) ? stored : 'overview';
    } catch {
      return 'overview';
    }
  });

  const setActiveTab = (tab) => {
    setActiveTabState(tab);
    try {
      sessionStorage.setItem('litreview_active_tab', tab);
    } catch {}
  };

  // A fresh login must always land on Overview so the user can pick which
  // notebook to open. Without this, a tab left over in sessionStorage from a
  // previous session (e.g. Setup, from before logging out) silently persists
  // and a brand new login appears to "skip" Overview entirely.
  const wasAuthenticatedRef = useRef(isAuthenticated);
  useEffect(() => {
    if (!wasAuthenticatedRef.current && isAuthenticated) {
      setActiveTab('overview');
    }
    wasAuthenticatedRef.current = isAuthenticated;
  }, [isAuthenticated]);

  useEffect(() => {
    // Admin accounts are a stats-only viewer role, not a researcher account --
    // they must never land on the full Overview hub (project grid, "Tạo mới",
    // search). The 'overview' exception below used to let that happen: a
    // fresh login forces activeTab to 'overview' (see the effect above), and
    // that value slipped past this guard's condition, so it never redirected
    // an admin away from Overview.
    if (currentUser?.role === 'admin' && activeTab !== 'admin') {
      setActiveTab('admin');
    }
  }, [activeTab, currentUser]);

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

  const loadedProjectIdRef = useRef(activeProjectId);

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
      isWelcome: true,
      text: "",
    },
  ];

  const [chatMessages, setChatMessages] = useState(() => {
    const saved = localStorage.getItem(chatMessagesKey);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (parsed && parsed.length > 0 && parsed[0].text && (parsed[0].text.includes('LitReview Agent') || parsed[0].text.includes('Không gian Phân tích'))) {
          return getDefaultWelcomeMessage(activeProject?.name);
        }
        return parsed;
      } catch (e) {
        console.error('Failed to parse saved chat messages:', e);
      }
    }
    return getDefaultWelcomeMessage(activeProject?.name);
  });

  // Switch project data when active project changes
  useEffect(() => {
    loadedProjectIdRef.current = activeProjectId;
    try {
      const pKey = activeProjectId ? `litreview_papers_${activeProjectId}` : 'litreview_papers';
      const sIdsKey = activeProjectId ? `litreview_selected_ids_${activeProjectId}` : 'litreview_selected_ids';
      const sPapersKey = activeProjectId ? `litreview_selected_papers_${activeProjectId}` : 'litreview_selected_papers';
      const wsKey = activeProjectId ? `litreview_workspace_papers_${activeProjectId}` : 'litreview_workspace_papers';
      const cKey = activeProjectId ? `litreview_workspace_chat_${activeProjectId}` : 'litreview_workspace_chat_messages';

      const savedPapers = localStorage.getItem(pKey);
      setPapers(savedPapers ? JSON.parse(savedPapers) : []);

      const savedIds = localStorage.getItem(sIdsKey);
      setSelectedPaperIds(savedIds ? JSON.parse(savedIds) : []);

      const savedSelected = localStorage.getItem(sPapersKey);
      setSelectedPapers(savedSelected ? JSON.parse(savedSelected) : []);

      const savedWs = localStorage.getItem(wsKey);
      setWorkspacePapers(savedWs ? JSON.parse(savedWs) : []);

      const savedChat = localStorage.getItem(cKey);
      if (savedChat) {
        setChatMessages(JSON.parse(savedChat));
      } else {
        setChatMessages(getDefaultWelcomeMessage(activeProject?.name));
      }
    } catch {
      // ignore
    }
    // activeCitation (which paper/quote the Verification panel is showing)
    // belongs to whatever paper the user was just looking at -- it has no
    // meaning once the project underneath it has changed, but it was never
    // cleared here, so switching notebooks left the Verification panel
    // showing a stale citation from the PREVIOUS project (wrong paper,
    // wrong quote) until the user happened to click a new one themselves.
    setActiveCitation(null);
  }, [activeProjectId, activeProject?.name]);

  useEffect(() => {
    if (loadedProjectIdRef.current === activeProjectId && papersStorageKey) {
      localStorage.setItem(papersStorageKey, JSON.stringify(papers));
    }
  }, [papers, papersStorageKey, activeProjectId]);

  useEffect(() => {
    if (loadedProjectIdRef.current === activeProjectId && selectedIdsKey) {
      localStorage.setItem(selectedIdsKey, JSON.stringify(selectedPaperIds));
    }
  }, [selectedPaperIds, selectedIdsKey, activeProjectId]);

  useEffect(() => {
    if (loadedProjectIdRef.current === activeProjectId && selectedPapersKey) {
      localStorage.setItem(selectedPapersKey, JSON.stringify(selectedPapers));
    }
  }, [selectedPapers, selectedPapersKey, activeProjectId]);

  useEffect(() => {
    if (loadedProjectIdRef.current === activeProjectId && workspacePapersKey) {
      localStorage.setItem(workspacePapersKey, JSON.stringify(workspacePapers));
    }
  }, [workspacePapers, workspacePapersKey, activeProjectId]);

  useEffect(() => {
    if (loadedProjectIdRef.current === activeProjectId && chatMessagesKey && chatMessages) {
      localStorage.setItem(chatMessagesKey, JSON.stringify(chatMessages));
    }
  }, [chatMessages, chatMessagesKey, activeProjectId]);

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
        {activeTab === 'admin' && (
          <div className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-10 py-6">
            <AdminDashboard darkMode={darkMode} />
          </div>
        )}

        {/* Overview / Personalized Dashboard */}
        {activeTab === 'overview' && (
          <div className="w-full min-h-screen">
            <PersonalizedDashboard
              setActiveTab={setActiveTab}
              onOpenNewProject={() => setNewProjectModalOpen(true)}
            />
          </div>
        )}

        {/* Research Setup Tab */}
        {activeTab === 'setup' && (
          <div className="w-full max-w-7xl 2xl:max-w-[1600px] mx-auto px-3 sm:px-6 lg:px-8 py-6">
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

        {/* AI Workspace Panels (Chat with sources, Literature review, Data Analysis) */}
        {['chat', 'synthesis', 'data_analysis', 'analyze'].includes(activeTab) && (
          <div className="w-full">
            <WorkspaceTab
              key={`workspace_${activeProjectId || 'default'}`}
              activeTab={activeTab}
              setActiveTab={setActiveTab}
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

  const isOverviewHub = activeTab === 'overview';

  // ── RENDER: Authenticated Workspace Shell ───────────────────────────────
  return (
    <div className={`min-h-screen w-full bg-[#F8FAFC] dark:bg-[#0A0D14] text-slate-900 dark:text-slate-100 transition-colors duration-200 ${darkMode ? 'dark' : ''}`}>
      {!isOverviewHub && (
        <HorizontalNavbar
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          onOpenNewProject={() => setNewProjectModalOpen(true)}
          onStartTour={handleStartTour}
        />
      )}

      {/* ── Main Content Area ─────── */}
      <main className={isOverviewHub ? "w-full min-h-screen" : "w-full min-h-[calc(100vh-4rem)] pt-14 sm:pt-16 pb-16 md:pb-0"}>
        {renderMainContent()}
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
        onCreated={() => {
          setActiveTab('setup');
          setIsTourOpen(true);
        }}
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
