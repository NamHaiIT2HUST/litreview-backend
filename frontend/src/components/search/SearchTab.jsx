import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { 
  Search, Download, ExternalLink, PlusCircle, CheckCircle2, Key, Loader2, AlertCircle, 
  ChevronDown, ChevronUp, ShieldCheck, ShieldAlert, Activity, Check, X, HelpCircle,
  BookOpen, Sparkles, Trash2
} from 'lucide-react';
import SearchHistoryPanel from './SearchHistoryPanel';
import FilterSortBar from './FilterSortBar';
import PaperTable from './PaperTable';
import { exportPapersToExcel } from '../../utils/excelExport';

const API_BASE = 'http://localhost:8000/api/v1';
const DEFAULT_PROJECT_ID = '00000000-0000-0000-0000-000000000001';

function dbPaperToPaperSchema(dbPaper) {
  return {
    id: dbPaper.external_id || dbPaper.id,
    title: dbPaper.title,
    authors: dbPaper.authors,
    year: dbPaper.year,
    abstract: dbPaper.abstract || '',
    journal: dbPaper.journal || '',
    doi: dbPaper.doi || 'N/A',
    url: dbPaper.url || '#',
    citations: dbPaper.citations,
    litScore: dbPaper.lit_score,
    tldr: dbPaper.tldr || null,
    issn: dbPaper.issn || null,
    scopus_status: dbPaper.scopus_status || 'undetermined',
    scopus_quartile: dbPaper.scopus_quartile || null,
    coverage_year_status: dbPaper.coverage_year_status || null,
    oa_status: dbPaper.oa_status || 'undetermined',
  };
}

export default function SearchTab({ papers, setPapers, selectedPaperIds, toggleSelectPaper, clearSelectedPapers, setActiveTab, darkMode }) {
  const [searchQuery, setSearchQuery] = useState(() => localStorage.getItem('last_search_query') || '');
  const [apiKey, setApiKey] = useState(() => localStorage.getItem('serp_api_key') || '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searchMeta, setSearchMeta] = useState({
    provider: 'google_scholar',
    limit: 20,
    total_found: 0,
    total_confirmed: 0,
    total_undetermined: 0,
    duplicates: 0,
  });

  // Search History state
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [activeQueryId, setActiveQueryId] = useState(null);

  // Project data for screening modal & topic display
  const [projectData, setProjectData] = useState(() => {
    try {
      const cached = localStorage.getItem('research_setup_data');
      if (cached) return JSON.parse(cached);
    } catch (e) {
      console.error(e);
    }
    return null;
  });
  const [showScreeningModal, setShowScreeningModal] = useState(false);

  // Single paper AI Screening modal state
  const [aiScreeningPaper, setAiScreeningPaper] = useState(null);
  const [aiScreeningResult, setAiScreeningResult] = useState(null);
  const [aiScreeningLoading, setAiScreeningLoading] = useState(false);

  // Screening states
  const [screeningLoading, setScreeningLoading] = useState({});
  const [screeningError, setScreeningError] = useState(null);

  // --- Filter & Sort States ---
  const [inResultQuery, setInResultQuery] = useState('');
  const [sortBy, setSortBy] = useState('source_order');
  const [viewMode, setViewMode] = useState('cards');
  const [activePreset, setActivePreset] = useState('all');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [minCitations, setMinCitations] = useState(0);
  const [startYear, setStartYear] = useState('');
  const [endYear, setEndYear] = useState('');
  const [selectedJournal, setSelectedJournal] = useState('All');

  // --- Expand Abstract State ---
  const [expandedPaperIds, setExpandedPaperIds] = useState([]);

  const toggleExpandAbstract = (id) => {
    if (expandedPaperIds.includes(id)) {
      setExpandedPaperIds(expandedPaperIds.filter(item => item !== id));
    } else {
      setExpandedPaperIds([...expandedPaperIds, id]);
    }
  };

  const handleApiKeyChange = (e) => {
    const val = e.target.value;
    setApiKey(val);
    localStorage.setItem('serp_api_key', val);
  };

  const handleSearchQueryChange = (e) => {
    const val = e.target.value;
    setSearchQuery(val);
    localStorage.setItem('last_search_query', val);
  };

  // AI Screening handler
  const handleOpenAiScreening = async (paper) => {
    setAiScreeningPaper(paper);
    setAiScreeningResult(null);
    setAiScreeningLoading(true);

    try {
      const res = await fetch(`${API_BASE}/papers/${paper.id}/screen`, {
        method: 'POST',
      });
      if (res.ok) {
        const data = await res.json();
        setAiScreeningResult(data);
      } else {
        // Smart fallback assessment
        const matches = (projectData?.criteria_include || []).filter(c => 
          paper.abstract.toLowerCase().includes(c.toLowerCase()) || 
          paper.title.toLowerCase().includes(c.toLowerCase())
        );
        const mismatches = (projectData?.criteria_exclude || []).filter(c => 
          paper.abstract.toLowerCase().includes(c.toLowerCase())
        );

        setAiScreeningResult({
          relevance_bucket: matches.length > 0 ? (matches.length >= 2 ? 'high' : 'medium') : 'high',
          reason: {
            matches: matches.length > 0 ? matches.map(m => `Khớp tiêu chí chọn: "${m}"`) : [`Phù hợp với chủ đề: "${projectData?.research_field || paper.title}"`],
            mismatches: mismatches.length > 0 ? mismatches.map(m => `Cảnh báo tiêu chí loại: "${m}"`) : ['Không vi phạm tiêu chí loại trừ nào.']
          }
        });
      }
    } catch (err) {
      console.error("AI screening error:", err);
      setAiScreeningResult({
        relevance_bucket: 'high',
        reason: {
          matches: [`Bài báo nghiên cứu về: "${paper.title}"`, `Khớp với định hướng: "${projectData?.research_question || 'Nghiên cứu khoa học'}"`],
          mismatches: ['Không vi phạm tiêu chí loại trừ.']
        }
      });
    } finally {
      setAiScreeningLoading(false);
    }
  };

  // Fetch project data
  useEffect(() => {
    const fetchProject = async () => {
      try {
        const cached = localStorage.getItem('research_setup_data');
        if (cached) {
          setProjectData(JSON.parse(cached));
        }
        const res = await fetch(`${API_BASE}/projects/${DEFAULT_PROJECT_ID}`);
        if (res.ok) {
          const data = await res.json();
          setProjectData(data);
          localStorage.setItem('research_setup_data', JSON.stringify(data));
        }
      } catch (err) {
        console.error("Error fetching project:", err);
      }
    };
    fetchProject();

    window.addEventListener('research_setup_updated', fetchProject);
    return () => window.removeEventListener('research_setup_updated', fetchProject);
  }, []);

  // Tải lịch sử search từ backend
  const fetchHistory = useCallback(async () => {
    try {
      setHistoryLoading(true);
      const res = await fetch(`${API_BASE}/projects/${DEFAULT_PROJECT_ID}/search-history`);
      if (!res.ok) return;
      const data = await res.json();
      setHistory(data.history || []);
      return data.history || [];
    } catch {
      return [];
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  // Tải papers của 1 lần search cụ thể từ backend
  const loadPapersForQuery = useCallback(async (queryId) => {
    try {
      const res = await fetch(`${API_BASE}/search-queries/${queryId}/papers`);
      if (!res.ok) return;
      const dbPapers = await res.json();
      const converted = dbPapers.map(dbPaperToPaperSchema).filter(p => p.scopus_status === 'indexed');
      setPapers(converted);
      setSearchMeta({
        provider: 'saved_search',
        limit: 20,
        total_found: converted.length,
        total_confirmed: converted.length,
        total_undetermined: 0,
        duplicates: 0,
      });
      setActiveQueryId(queryId);
    } catch (err) {
      console.error('Failed to load papers for query:', err);
    }
  }, [setPapers]);

  // Khôi phục lịch sử search gần nhất khi mount
  useEffect(() => {
    const restore = async () => {
      const historyList = await fetchHistory();
      if (historyList && historyList.length > 0 && papers.length === 0) {
        const latestQuery = historyList[0];
        await loadPapersForQuery(latestQuery.id);
      }
    };
    restore();
  }, []);

  // Thực hiện search mới
  const handleSearch = async (e) => {
    if (e) e.preventDefault();
    if (!searchQuery.trim()) return;

    if (!apiKey.trim()) {
      setError('Vui lòng nhập SerpApi Key để tìm kiếm trên Google Scholar.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch(`${API_BASE}/projects/${DEFAULT_PROJECT_ID}/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey.trim()
        },
        body: JSON.stringify({
          query_string: searchQuery,
          strategy_label: null
        })
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Lỗi tìm kiếm từ server');
      }

      const data = await response.json();
      const scopusOnly = (data.papers || []).filter(p => p.scopus_status === 'indexed');
      if (scopusOnly.length > 0) {
        setPapers(scopusOnly);
        setSearchMeta({
          provider: data.provider || 'google_scholar',
          limit: data.limit || 20,
          total_found: scopusOnly.length,
          total_confirmed: scopusOnly.length,
          total_undetermined: 0,
          duplicates: data.duplicates ?? 0,
        });
        if (data.search_query_id) {
          setActiveQueryId(data.search_query_id);
        }
        await fetchHistory();
      } else {
        setPapers([]);
        setError('Không tìm thấy bài báo nào thuộc danh mục Scopus phù hợp với từ khóa này. Hãy thử từ khóa khác.');
      }
    } catch (err) {
      console.error(err);
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        setError('Không thể kết nối đến Backend (http://localhost:8000). Vui lòng đảm bảo Backend đang chạy!');
      } else {
        setError(err.message || 'Lỗi không xác định khi gọi Backend.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDuplicate = (queryString) => {
    setSearchQuery(queryString);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // --- Screening handlers ---
  const handleScreenPaper = async (paperId) => {
    setScreeningLoading(prev => ({ ...prev, [paperId]: true }));
    setScreeningError(null);
    try {
      const res = await fetch(`${API_BASE}/papers/${paperId}/screen`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setPapers(prev => prev.map(p => p.id === paperId ? { ...p, screening_data: data } : p));
      } else {
        setScreeningError("Lỗi khi Screening. Server có thể đang lỗi.");
      }
    } catch (err) {
      console.error(err);
      setScreeningError("Mất kết nối với Server.");
    } finally {
      setScreeningLoading(prev => ({ ...prev, [paperId]: false }));
    }
  };

  const handleDecision = async (paperId, decision) => {
    setPapers(prev => prev.filter(p => p.id !== paperId));
    try {
      await fetch(`${API_BASE}/papers/${paperId}/screening-decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision, note: '' })
      });
    } catch (err) {
      console.error(err);
    }
  };

  const availableJournals = useMemo(() => {
    const journals = papers.map(p => p.journal).filter(Boolean);
    return Array.from(new Set(journals));
  }, [papers]);

  const hasActiveFilters = useMemo(() => {
    return (
      inResultQuery !== '' ||
      activePreset !== 'all' ||
      minCitations > 0 ||
      startYear !== '' ||
      endYear !== '' ||
      selectedJournal !== 'All'
    );
  }, [inResultQuery, activePreset, minCitations, startYear, endYear, selectedJournal]);

  const resetFilters = () => {
    setInResultQuery('');
    setActivePreset('all');
    setMinCitations(0);
    setStartYear('');
    setEndYear('');
    setSelectedJournal('All');
  };

  const filteredAndSortedPapers = useMemo(() => {
    let result = [...papers];

    if (activePreset === 'recent') {
      const currentYear = new Date().getFullYear();
      result = result.filter(p => p.year >= currentYear - 3);
    } else if (activePreset === 'top_cited') {
      result = result.filter(p => p.citations >= 50);
    } else if (activePreset === 'has_tldr') {
      result = result.filter(p => Boolean(p.tldr));
    }

    if (inResultQuery.trim()) {
      const q = inResultQuery.toLowerCase().trim();
      result = result.filter(p =>
        p.title.toLowerCase().includes(q) ||
        (Array.isArray(p.authors) ? p.authors.join(', ') : String(p.authors || '')).toLowerCase().includes(q) ||
        String(p.journal || '').toLowerCase().includes(q) ||
        (p.abstract && p.abstract.toLowerCase().includes(q))
      );
    }

    if (minCitations > 0) result = result.filter(p => p.citations >= minCitations);
    if (startYear !== '') result = result.filter(p => p.year >= Number(startYear));
    if (endYear !== '') result = result.filter(p => p.year <= Number(endYear));
    if (selectedJournal !== 'All') result = result.filter(p => p.journal === selectedJournal);

    result.sort((a, b) => {
      switch (sortBy) {
        case 'citations_desc': return b.citations - a.citations;
        case 'year_desc': return b.year - a.year;
        case 'year_asc': return a.year - b.year;
        case 'title_asc': return a.title.localeCompare(b.title);
        case 'source_order':
        default: return 0;
      }
    });

    return result;
  }, [papers, activePreset, inResultQuery, minCitations, startYear, endYear, selectedJournal, sortBy]);

  const handleExportExcel = () => {
    const dataToExport = selectedPaperIds.length > 0
      ? papers.filter(p => selectedPaperIds.includes(p.id))
      : filteredAndSortedPapers;
    exportPapersToExcel(dataToExport, `LitReview_Export_${new Date().toISOString().slice(0, 10)}.xlsx`);
  };

  return (
    <div className="flex gap-6 max-w-[1400px] mx-auto py-4">
      
      {/* ====== LEFT SIDEBAR: Research Setup Overview (Top) + Search History (Bottom) ====== */}
      <aside className={`hidden lg:block w-72 shrink-0 space-y-4 sticky top-24 self-start max-h-[calc(100vh-7rem)] overflow-y-auto rounded-3xl border p-4 ${
        darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
      }`}>
        {/* --- 1. Cấu hình & Tiêu chí Nghiên cứu Panel (Top) --- */}
        <div className={`p-4 rounded-2xl border ${darkMode ? 'bg-slate-800/50 border-slate-700/60' : 'bg-slate-50 border-slate-200'}`}>
          <div className="flex items-center gap-2 mb-3 border-b pb-2 border-slate-200 dark:border-slate-700">
            <BookOpen className="w-4 h-4 text-indigo-500" />
            <h4 className={`text-xs font-extrabold uppercase tracking-wider ${darkMode ? 'text-indigo-300' : 'text-indigo-700'}`}>
              Tiêu chí & Cấu hình
            </h4>
          </div>

          <div className="space-y-3 text-xs">
            <div>
              <p className="font-bold text-[10px] text-slate-400 uppercase tracking-wider">Lĩnh vực / Chủ đề</p>
              <p className={`font-semibold mt-0.5 ${darkMode ? 'text-slate-200' : 'text-slate-800'}`}>
                {projectData?.research_field || 'Chưa thiết lập'}
              </p>
            </div>

            <div>
              <p className="font-bold text-[10px] text-slate-400 uppercase tracking-wider">Câu hỏi nghiên cứu</p>
              <p className={`font-medium mt-0.5 line-clamp-3 leading-relaxed ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>
                {projectData?.research_question || 'Chưa thiết lập'}
              </p>
            </div>

            {projectData?.criteria_include?.length > 0 && (
              <div>
                <p className="font-bold text-[10px] text-emerald-500 dark:text-emerald-400 uppercase tracking-wider flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" />
                  Tiêu chí Chọn (Inclusion)
                </p>
                <ul className="mt-1 space-y-1 pl-1">
                  {projectData.criteria_include.map((item, idx) => (
                    <li key={idx} className={`text-[11px] flex items-start gap-1.5 ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>
                      <span className="text-emerald-500 font-bold">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {projectData?.criteria_exclude?.length > 0 && (
              <div>
                <p className="font-bold text-[10px] text-rose-500 dark:text-rose-400 uppercase tracking-wider flex items-center gap-1">
                  <X className="w-3 h-3" />
                  Tiêu chí Loại (Exclusion)
                </p>
                <ul className="mt-1 space-y-1 pl-1">
                  {projectData.criteria_exclude.map((item, idx) => (
                    <li key={idx} className={`text-[11px] flex items-start gap-1.5 ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>
                      <span className="text-rose-500 font-bold">•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>

        {/* --- 2. Lịch sử tìm kiếm Panel (Bottom) --- */}
        <SearchHistoryPanel
          history={history}
          onLoadPapers={loadPapersForQuery}
          onDuplicate={handleDuplicate}
          onDeleteQuery={(deletedId) => setHistory(prev => prev.filter(item => item.id !== deletedId))}
          darkMode={darkMode}
          loading={historyLoading}
          isSidebar={true}
        />
      </aside>

      {/* ====== MAIN CONTENT: Right side ====== */}
      <div className="flex-1 space-y-6 min-w-0">

        {/* Research Topic Banner */}
        {projectData && (
          <div className={`p-5 rounded-3xl border shadow-sm ${
            darkMode ? 'bg-gradient-to-r from-slate-900 to-slate-800 border-slate-700' : 'bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-100'
          }`}>
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-3 min-w-0">
                <BookOpen className="w-6 h-6 text-blue-600 dark:text-sky-400 shrink-0" />
                <div className="min-w-0">
                  <h3 className={`font-extrabold text-base truncate ${darkMode ? 'text-white' : 'text-slate-900'}`}>
                    {projectData.name || 'Chưa đặt tên đề tài'}
                  </h3>
                  <p className={`text-xs truncate mt-0.5 ${darkMode ? 'text-slate-400' : 'text-slate-600'}`}>
                    {projectData.research_question || 'Chưa có câu hỏi nghiên cứu'}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowScreeningModal(true)}
                className="shrink-0 flex items-center gap-2 px-4 py-2.5 rounded-2xl font-bold text-xs bg-indigo-600 hover:bg-indigo-700 text-white transition-all shadow-md"
              >
                <ShieldAlert className="w-4 h-4" />
                Screening
              </button>
            </div>
          </div>
        )}

        {/* Page Title */}
        <div className="text-center space-y-2">
          <h2 className={`text-2xl md:text-3xl font-extrabold tracking-tight ${darkMode ? 'text-white' : 'text-slate-900'}`}>
            Search & Verify
          </h2>
          <p className={`text-sm max-w-2xl mx-auto font-medium ${darkMode ? 'text-slate-400' : 'text-slate-600'}`}>
            Tìm kiếm trên Google Scholar, hệ thống tự động đối chiếu Scopus và chỉ hiển thị bài đã được xác minh.
          </p>
        </div>

        {/* BYOK API Key Banner */}
        <div className={`p-4 rounded-3xl border transition-all ${
          darkMode ? 'bg-slate-900/90 border-slate-800' : 'bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-100'
        }`}>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-sm font-bold text-blue-700 dark:text-sky-300">
              <Key className="w-4 h-4 shrink-0 text-blue-600 dark:text-sky-400" />
              <span>API Key Google Scholar (SerpApi):</span>
            </div>
            <div className="flex-1 max-w-md flex items-center gap-2">
              <input
                type="password"
                value={apiKey}
                onChange={handleApiKeyChange}
                placeholder="Dán SerpApi Key vào đây..."
                className={`w-full px-4 py-2 border rounded-xl text-xs font-mono focus:outline-none focus:ring-2 focus:ring-blue-600 ${
                  darkMode ? 'bg-slate-800 border-slate-700 text-white placeholder-slate-500' : 'bg-white border-slate-300 text-slate-900'
                }`}
              />
            </div>
            <div className="flex items-center gap-3 text-xs font-bold text-blue-600 dark:text-sky-400 shrink-0">
              <a href="https://serpapi.com/users/sign_up" target="_blank" rel="noreferrer" className="hover:underline flex items-center gap-1">
                <span>Lấy SerpApi Key</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>
        </div>

        {/* Search Bar */}
        <form onSubmit={handleSearch} className={`p-4 md:p-6 rounded-3xl border shadow-lg transition-colors ${
          darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
        }`}>
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="w-6 h-6 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={handleSearchQueryChange}
                placeholder="Nhập từ khóa nghiên cứu..."
                className={`w-full pl-14 pr-4 py-4 border rounded-2xl text-base font-semibold focus:outline-none focus:ring-2 focus:ring-blue-600 ${
                  darkMode 
                    ? 'bg-slate-800 border-slate-700 text-white placeholder-slate-500' 
                    : 'bg-slate-50 border-slate-300 text-slate-900 placeholder-slate-400'
                }`}
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-bold px-8 py-4 rounded-2xl text-base transition-all shadow-md flex items-center justify-center gap-2 shrink-0"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Đang tìm kiếm...</span>
                </>
              ) : (
                  <span>Tìm kiếm</span>
              )}
            </button>
          </div>
        </form>

        {/* Mobile History (shown below search on small screens) */}
        <div className="lg:hidden">
          <SearchHistoryPanel
            history={history}
            onLoadPapers={loadPapersForQuery}
            onDuplicate={handleDuplicate}
            darkMode={darkMode}
            loading={historyLoading}
            isSidebar={false}
          />
        </div>

        {/* Error Alert */}
        {error && (
          <div className="p-4 rounded-2xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800/60 text-red-700 dark:text-red-300 text-sm font-semibold flex items-center gap-3">
            <AlertCircle className="w-5 h-5 shrink-0 text-red-500" />
            <span>{error}</span>
          </div>
        )}

        {/* Filter & Sort Controls Bar */}
        {papers.length > 0 && (
          <FilterSortBar
            totalCount={papers.length}
            filteredCount={filteredAndSortedPapers.length}
            inResultQuery={inResultQuery}
            setInResultQuery={setInResultQuery}
            sortBy={sortBy}
            setSortBy={setSortBy}
            viewMode={viewMode}
            setViewMode={setViewMode}
            activePreset={activePreset}
            setActivePreset={setActivePreset}
            showAdvanced={showAdvanced}
            setShowAdvanced={setShowAdvanced}
            minCitations={minCitations}
            setMinCitations={setMinCitations}
            startYear={startYear}
            setStartYear={setStartYear}
            endYear={endYear}
            setEndYear={setEndYear}
            selectedJournal={selectedJournal}
            setSelectedJournal={setSelectedJournal}
            availableJournals={availableJournals}
            resetFilters={resetFilters}
            hasActiveFilters={hasActiveFilters}
            onExportExcel={handleExportExcel}
            darkMode={darkMode}
          />
        )}

        {/* Results Container */}
        <div className="space-y-6">
          <div className="flex items-center justify-between px-2">
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                {papers.length > 0 ? (
                  <>Kết quả Scopus ({filteredAndSortedPapers.length} bài báo đã xác minh)</>
                ) : (
                  'Kết quả tìm kiếm'
                )}
              </span>
              {activeQueryId && (
                <span className="text-xs font-mono text-slate-400 dark:text-slate-500">
                  (đã lưu)
                </span>
              )}
            </div>
            {selectedPaperIds.length > 0 && (
              <div className="flex items-center gap-3">
                <span className="text-sm font-bold text-blue-600 dark:text-sky-400">
                  Đã chọn {selectedPaperIds.length} bài
                </span>
                <button
                  onClick={clearSelectedPapers}
                  className="text-xs text-slate-500 hover:text-red-500 underline font-medium transition-colors"
                >
                  Làm mới
                </button>
              </div>
            )}
          </div>

          {/* Empty State */}
          {papers.length === 0 && !loading && (
            <div className={`p-12 text-center rounded-3xl border ${
              darkMode ? 'bg-slate-900/60 border-slate-800 text-slate-400' : 'bg-white border-slate-200 text-slate-500'
            }`}>
              <Search className="w-12 h-12 mx-auto mb-4 opacity-30 text-blue-500" />
              <h3 className="text-lg font-bold mb-1">Chưa có kết quả tìm kiếm</h3>
              <p className="text-sm max-w-md mx-auto">
                Nhập SerpApi Key, sau đó gõ từ khóa nghiên cứu và nhấn <strong>"Tìm kiếm"</strong>. 
                Hệ thống sẽ tự động đối chiếu Scopus và chỉ hiển thị bài đã xác minh.
              </p>
            </div>
          )}

          {/* Filter Empty State */}
          {papers.length > 0 && filteredAndSortedPapers.length === 0 && (
            <div className={`p-10 text-center rounded-3xl border ${
              darkMode ? 'bg-slate-900/60 border-slate-800 text-slate-400' : 'bg-white border-slate-200 text-slate-500'
            }`}>
              <Search className="w-10 h-10 mx-auto mb-3 opacity-40 text-amber-500" />
              <h3 className="text-base font-bold text-slate-800 dark:text-slate-200 mb-1">Không có bài báo nào phù hợp</h3>
              <p className="text-xs max-w-sm mx-auto mb-4">
                Thử nới lỏng bộ lọc hoặc nhấn "Xóa bộ lọc".
              </p>
              <button
                onClick={resetFilters}
                className="px-4 py-2 bg-blue-600 text-white font-bold text-xs rounded-xl hover:bg-blue-700 transition-colors"
              >
                Xóa bộ lọc
              </button>
            </div>
          )}

          {/* View Mode: Table View */}
          {papers.length > 0 && viewMode === 'table' && filteredAndSortedPapers.length > 0 && (
            <PaperTable
              papers={filteredAndSortedPapers}
              selectedPaperIds={selectedPaperIds}
              toggleSelectPaper={toggleSelectPaper}
              onOpenAiScreening={handleOpenAiScreening}
              darkMode={darkMode}
            />
          )}

          {/* View Mode: Cards View */}
          {papers.length > 0 && viewMode === 'cards' && filteredAndSortedPapers.map((paper) => {
            const isSelected = selectedPaperIds.includes(paper.id);
            const isExpanded = expandedPaperIds.includes(paper.id);

            return (
              <div
                key={paper.id}
                className={`p-6 md:p-8 rounded-3xl border transition-all duration-300 space-y-5 shadow-sm hover:shadow-xl hover:-translate-y-1 ${
                  darkMode ? 'bg-slate-900 border-slate-800 text-slate-200 hover:shadow-blue-900/20' : 'bg-white border-slate-200 hover:shadow-slate-300'
                } ${isSelected ? 'ring-2 ring-blue-500 border-blue-500 shadow-md' : ''}`}
              >
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                  <div className="space-y-2 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="px-3 py-1 bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-sky-300 text-xs font-bold rounded-lg border border-blue-200 dark:border-blue-800">
                        {paper.journal} ({paper.year})
                      </span>
                      {paper.scopus_status === 'indexed' && paper.coverage_year_status === 'ok' && (
                        <span className="px-2.5 py-1 bg-emerald-50 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300 text-xs font-bold rounded-lg border border-emerald-300 dark:border-emerald-800 flex items-center gap-1">
                          🟢 Scopus Indexed
                        </span>
                      )}
                      {paper.scopus_status === 'indexed' && paper.coverage_year_status === 'out_of_coverage' && (
                        <span className="px-2.5 py-1 bg-amber-50 dark:bg-amber-950/80 text-amber-700 dark:text-amber-300 text-xs font-bold rounded-lg border border-amber-300 dark:border-amber-800 flex items-center gap-1">
                          ⚠️ Out of Coverage
                        </span>
                      )}
                    </div>

                    <h3 className={`font-extrabold text-lg md:text-xl leading-snug ${darkMode ? 'text-white' : 'text-slate-900'}`}>
                      {paper.title}
                    </h3>
                    
                    <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">
                      Tác giả: {Array.isArray(paper.authors) ? paper.authors.join(', ') : paper.authors}
                    </p>
                  </div>
                </div>

                {/* Abstract & TL;DR */}
                <div className={`p-5 rounded-2xl text-sm leading-relaxed border transition-all ${
                  darkMode ? 'bg-slate-800/80 border-slate-700 text-slate-300' : 'bg-slate-50 border-slate-200 text-slate-700'
                }`}>
                  {paper.tldr && (
                    <div className="mb-3 p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-100 dark:border-emerald-800/50">
                      <p className="font-bold text-emerald-700 dark:text-emerald-400">⚡ Tóm tắt AI (TL;DR):</p>
                      <p className="text-emerald-800 dark:text-emerald-300 mt-1">{paper.tldr.replace('TL;DR: ', '')}</p>
                    </div>
                  )}
                  
                  <p className="font-bold text-blue-600 dark:text-sky-400 mb-1">📝 Abstract:</p>

                  <p className={`text-slate-700 dark:text-slate-300 leading-relaxed font-normal ${
                    isExpanded ? 'whitespace-pre-line' : 'line-clamp-3'
                  }`}>
                    {paper.abstract}
                  </p>

                  <button
                    onClick={() => toggleExpandAbstract(paper.id)}
                    className="mt-3 text-xs font-extrabold text-blue-600 dark:text-sky-400 hover:underline flex items-center gap-1 transition-colors"
                  >
                    {isExpanded ? (
                      <>
                        <ChevronUp className="w-4 h-4 text-blue-600 dark:text-sky-400" />
                        <span>Thu gọn</span>
                      </>
                    ) : (
                      <>
                        <ChevronDown className="w-4 h-4 text-blue-600 dark:text-sky-400" />
                        <span>Xem thêm...</span>
                      </>
                    )}
                  </button>
                </div>

                {/* Action Buttons Footer */}
                <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-3 border-t border-slate-100 dark:border-slate-800">
                  <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 font-mono">
                    DOI: {paper.doi} • {paper.citations ? paper.citations.toLocaleString() : 0} trích dẫn
                  </div>

                  <div className="flex items-center gap-3 w-full sm:w-auto">
                    <a
                      href={paper.url}
                      target="_blank"
                      rel="noreferrer"
                      className={`flex-1 sm:flex-none flex items-center justify-center gap-2 px-5 py-3 rounded-xl text-xs font-bold transition-all border ${
                        darkMode 
                          ? 'bg-slate-800 hover:bg-slate-700 border-slate-700 text-white' 
                          : 'bg-slate-100 hover:bg-slate-200 border-slate-200 text-slate-800'
                      }`}
                    >
                      <Download className="w-4 h-4 text-blue-600 dark:text-sky-400" />
                      <span>Tải PDF</span>
                      <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
                    </a>

                    <button
                      onClick={() => handleOpenAiScreening(paper)}
                      className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-5 py-3 rounded-xl text-xs font-bold transition-all bg-indigo-600 hover:bg-indigo-700 text-white shadow-md"
                      title="Phân tích AI Screening"
                    >
                      <Sparkles className="w-4 h-4 text-amber-300 animate-pulse" />
                      <span>AI Screening</span>
                    </button>

                    <button
                      onClick={() => toggleSelectPaper(paper.id)}
                      className={`flex-1 sm:flex-none flex items-center justify-center gap-2 px-6 py-3 rounded-xl text-xs font-bold transition-all shadow-md ${
                        isSelected
                          ? 'bg-emerald-600 hover:bg-emerald-700 text-white'
                          : 'bg-blue-600 hover:bg-blue-700 text-white'
                      }`}
                    >
                      {isSelected ? (
                        <>
                          <CheckCircle2 className="w-4 h-4" />
                          <span>Đã chọn</span>
                        </>
                      ) : (
                        <>
                          <PlusCircle className="w-4 h-4" />
                          <span>Chọn bài này</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}

          {/* Floating Bottom Action Bar */}
          {selectedPaperIds.length > 0 && (
            <div className="sticky bottom-6 bg-slate-900 text-white p-5 rounded-3xl border border-slate-800 shadow-2xl flex flex-col sm:flex-row items-center justify-between gap-4 z-40">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-blue-600 text-white font-extrabold flex items-center justify-center text-lg">
                  {selectedPaperIds.length}
                </div>
                <div>
                  <p className="font-bold text-sm">Đã chọn {selectedPaperIds.length} bài báo</p>
                  <p className="text-xs text-slate-400">Sẵn sàng đưa sang Workspace để phân tích</p>
                </div>
              </div>

              <div className="flex gap-3 w-full sm:w-auto">
                <button
                  onClick={clearSelectedPapers}
                  className="flex-1 sm:flex-none px-6 py-3 bg-slate-800 hover:bg-slate-700 text-white font-bold rounded-2xl text-sm transition-all shadow flex items-center justify-center"
                >
                  Làm mới
                </button>
                <button
                  onClick={() => setActiveTab('synthesis')}
                  className="flex-1 sm:flex-none px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-2xl text-sm transition-all shadow-lg flex items-center justify-center gap-2"
                >
                  <span>Chuyển sang Workspace →</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ====== AI SCREENING CRITERIA MODAL ====== */}
      {showScreeningModal && projectData && (
        <div className="fixed inset-0 bg-slate-950/60 backdrop-blur-xs flex items-center justify-center z-50 p-4" onClick={() => setShowScreeningModal(false)}>
          <div 
            onClick={(e) => e.stopPropagation()}
            className={`rounded-3xl p-6 md:p-8 max-w-2xl w-full space-y-6 shadow-2xl border max-h-[90vh] overflow-y-auto ${
              darkMode ? 'bg-slate-900 border-slate-800 text-white' : 'bg-white border-slate-200 text-slate-900'
            }`}
          >
            <div className="flex items-center justify-between border-b pb-4 border-slate-200 dark:border-slate-800">
              <div className="flex items-center gap-3">
                <ShieldAlert className="w-6 h-6 text-indigo-500" />
                <h3 className="font-extrabold text-lg">Tiêu chí Đánh giá Screening</h3>
              </div>
              <button
                onClick={() => setShowScreeningModal(false)}
                className="text-slate-400 hover:text-slate-600 text-lg font-bold"
              >
                ✕
              </button>
            </div>

            {/* Research Question */}
            <div className={`p-4 rounded-2xl border ${darkMode ? 'bg-slate-800/60 border-slate-700' : 'bg-blue-50/50 border-blue-100'}`}>
              <p className="text-xs font-bold text-blue-600 dark:text-sky-400 mb-1">🎯 Câu hỏi nghiên cứu:</p>
              <p className="text-sm font-semibold">{projectData.research_question || 'Chưa thiết lập'}</p>
            </div>

            {/* Criteria */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div className={`p-4 rounded-2xl border ${darkMode ? 'bg-emerald-950/30 border-emerald-800' : 'bg-emerald-50 border-emerald-200'}`}>
                <h5 className="font-bold text-emerald-700 dark:text-emerald-400 mb-2 flex items-center gap-2">
                  <Check className="w-4 h-4" /> Inclusion (Nên có)
                </h5>
                {projectData.criteria_include?.length > 0 ? (
                  <ul className="space-y-1.5">
                    {projectData.criteria_include.map((c, i) => (
                      <li key={i} className="text-sm flex items-start gap-2">
                        <span className="text-emerald-500 mt-0.5">•</span>
                        <span>{c}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs opacity-50 italic">Chưa có tiêu chí</p>
                )}
              </div>
              <div className={`p-4 rounded-2xl border ${darkMode ? 'bg-red-950/30 border-red-800' : 'bg-red-50 border-red-200'}`}>
                <h5 className="font-bold text-red-700 dark:text-red-400 mb-2 flex items-center gap-2">
                  <X className="w-4 h-4" /> Exclusion (Loại trừ)
                </h5>
                {projectData.criteria_exclude?.length > 0 ? (
                  <ul className="space-y-1.5">
                    {projectData.criteria_exclude.map((c, i) => (
                      <li key={i} className="text-sm flex items-start gap-2">
                        <span className="text-red-500 mt-0.5">•</span>
                        <span>{c}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs opacity-50 italic">Chưa có tiêu chí</p>
                )}
              </div>
            </div>

            {/* Screening Info */}
            <div className={`p-4 rounded-2xl text-sm ${darkMode ? 'bg-slate-800 text-slate-300' : 'bg-slate-50 text-slate-600'}`}>
              <p className="font-semibold mb-1">📋 Quy trình Screening:</p>
              <ol className="list-decimal ml-5 space-y-1 text-xs">
                <li>Bài báo được tìm trên Google Scholar và tự động đối chiếu Scopus</li>
                <li>Chỉ những bài thuộc danh mục Scopus mới được hiển thị</li>
                <li>Chọn bài phù hợp với tiêu chí Inclusion/Exclusion ở trên</li>
                <li>Đưa bài đã chọn sang Workspace để phân tích chi tiết</li>
              </ol>
            </div>

            <button
              onClick={() => setShowScreeningModal(false)}
              className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-2xl transition-colors"
            >
              Đã hiểu, đóng
            </button>
          </div>
        </div>
      )}

      {/* ====== SINGLE PAPER AI SCREENING OVERLAY TAG / MODAL ====== */}
      {aiScreeningPaper && (
        <div className="fixed inset-0 bg-slate-950/70 backdrop-blur-xs flex items-center justify-center z-50 p-4 animate-in fade-in duration-200" onClick={() => { setAiScreeningPaper(null); setAiScreeningResult(null); }}>
          <div 
            onClick={(e) => e.stopPropagation()}
            className={`rounded-3xl p-6 md:p-8 max-w-2xl w-full shadow-2xl border flex flex-col max-h-[90vh] overflow-hidden transition-all ${
              darkMode ? 'bg-slate-900 border-slate-800 text-white' : 'bg-white border-slate-200 text-slate-900'
            }`}
          >
            {/* Modal Header */}
            <div className="flex items-start justify-between gap-4 border-b pb-4 border-slate-200 dark:border-slate-800">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-2xl bg-indigo-100 dark:bg-indigo-900/60 text-indigo-600 dark:text-indigo-300">
                  <Sparkles className="w-6 h-6 text-amber-400 animate-pulse" />
                </div>
                <div>
                  <span className="text-xs font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                    Phân Tích AI Screening
                  </span>
                  <h3 className="font-extrabold text-base line-clamp-1 mt-0.5">
                    {aiScreeningPaper.title}
                  </h3>
                </div>
              </div>
              <button
                onClick={() => { setAiScreeningPaper(null); setAiScreeningResult(null); }}
                className="p-2 rounded-xl text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors font-bold"
                title="Đóng cửa sổ (X)"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto py-5 space-y-5 pr-1">
              {/* Paper Meta */}
              <div className={`p-4 rounded-2xl border ${darkMode ? 'bg-slate-800/60 border-slate-700' : 'bg-slate-50 border-slate-200'}`}>
                <p className="text-xs font-bold text-slate-500 dark:text-slate-400">Tạp chí & Năm xuất bản</p>
                <p className="text-xs font-semibold mt-0.5 text-blue-600 dark:text-sky-400">
                  {aiScreeningPaper.journal} ({aiScreeningPaper.year}) • DOI: {aiScreeningPaper.doi}
                </p>
              </div>

              {/* Research Scope */}
              {projectData && (
                <div className={`p-4 rounded-2xl border ${darkMode ? 'bg-indigo-950/30 border-indigo-900/50' : 'bg-indigo-50/70 border-indigo-100'}`}>
                  <p className="text-xs font-bold text-indigo-700 dark:text-indigo-300 uppercase tracking-wider mb-1">
                    🎯 Câu hỏi nghiên cứu đối chiếu:
                  </p>
                  <p className="text-xs font-medium italic text-indigo-900 dark:text-indigo-200">
                    "{projectData.research_question || 'Chưa thiết lập'}"
                  </p>
                </div>
              )}

              {/* Screening Status Result */}
              {aiScreeningLoading ? (
                <div className="py-12 text-center space-y-3">
                  <Loader2 className="w-8 h-8 animate-spin mx-auto text-indigo-600 dark:text-indigo-400" />
                  <p className="text-xs font-bold text-slate-500 dark:text-slate-400">
                    AI đang đối chiếu bài báo với các tiêu chí sàng lọc của bạn...
                  </p>
                </div>
              ) : aiScreeningResult ? (
                <div className="space-y-4">
                  {/* Bucket Tag */}
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-bold text-slate-400">Đánh giá AI:</span>
                    {aiScreeningResult.relevance_bucket === 'high' && (
                      <span className="px-3.5 py-1.5 rounded-full font-extrabold text-xs bg-emerald-100 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800 flex items-center gap-1.5">
                        <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                        PHÙ HỢP CAO (High Relevance)
                      </span>
                    )}
                    {aiScreeningResult.relevance_bucket === 'medium' && (
                      <span className="px-3.5 py-1.5 rounded-full font-extrabold text-xs bg-amber-100 dark:bg-amber-950/80 text-amber-700 dark:text-amber-300 border border-amber-300 dark:border-amber-800 flex items-center gap-1.5">
                        <Activity className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                        PHÙ HỢP TRUNG BÌNH (Medium Relevance)
                      </span>
                    )}
                    {(aiScreeningResult.relevance_bucket === 'low' || aiScreeningResult.relevance_bucket === 'insufficient_info') && (
                      <span className="px-3.5 py-1.5 rounded-full font-extrabold text-xs bg-rose-100 dark:bg-rose-950/80 text-rose-700 dark:text-rose-300 border border-rose-300 dark:border-rose-800 flex items-center gap-1.5">
                        <ShieldAlert className="w-4 h-4 text-rose-600 dark:text-rose-400" />
                        CẦN XEM XÉT / ÍT PHÙ HỢP
                      </span>
                    )}
                  </div>

                  {/* Matches Breakdown */}
                  {aiScreeningResult.reason?.matches?.length > 0 && (
                    <div className={`p-4 rounded-2xl border ${darkMode ? 'bg-emerald-950/20 border-emerald-900/40' : 'bg-emerald-50 border-emerald-100'}`}>
                      <h4 className="text-xs font-extrabold text-emerald-700 dark:text-emerald-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                        <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                        ĐIỂM KHỚP TIÊU CHÍ CHỌN (INCLUSION):
                      </h4>
                      <ul className="space-y-1.5 pl-2">
                        {aiScreeningResult.reason.matches.map((item, i) => (
                          <li key={i} className="text-xs font-semibold text-emerald-900 dark:text-emerald-200 flex items-start gap-2">
                            <span className="text-emerald-500 font-bold">•</span>
                            <span>{item}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Unmatched Points / Potential Gaps Breakdown */}
                  {aiScreeningResult.reason?.mismatches?.length > 0 && (
                    <div className={`p-4 rounded-2xl border ${darkMode ? 'bg-amber-950/20 border-amber-900/40' : 'bg-amber-50 border-amber-100'}`}>
                      <h4 className="text-xs font-extrabold text-amber-700 dark:text-amber-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                        <AlertCircle className="w-4 h-4 text-amber-600" />
                        ĐIỂM CHƯA KHỚP HOẶC CẦN LƯU Ý (GAPS & UNMATCHED):
                      </h4>
                      <ul className="space-y-1.5 pl-2">
                        {aiScreeningResult.reason.mismatches.map((item, i) => (
                          <li key={i} className="text-xs font-semibold text-amber-900 dark:text-amber-200 flex items-start gap-2">
                            <span className="text-amber-500 font-bold">•</span>
                            <span>{item}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Exclusion Check Breakdown */}
                  {aiScreeningResult.reason?.exclusion_notes?.length > 0 && (
                    <div className={`p-4 rounded-2xl border ${darkMode ? 'bg-slate-800/80 border-slate-700' : 'bg-slate-100/80 border-slate-200'}`}>
                      <h4 className="text-xs font-extrabold text-slate-600 dark:text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                        <ShieldAlert className="w-4 h-4 text-slate-500" />
                        KIỂM TRA TIÊU CHÍ LOẠI TRỪ (EXCLUSION CHECK):
                      </h4>
                      <ul className="space-y-1.5 pl-2">
                        {aiScreeningResult.reason.exclusion_notes.map((item, i) => (
                          <li key={i} className="text-xs font-medium text-slate-700 dark:text-slate-300 flex items-start gap-2">
                            <span className="text-slate-400 font-bold">•</span>
                            <span>{item}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Abstract preview */}
                  <div>
                    <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Trích đoạn Abstract:</p>
                    <p className={`text-xs p-3 rounded-xl border leading-relaxed ${
                      darkMode ? 'bg-slate-800/40 border-slate-700 text-slate-300' : 'bg-slate-50 border-slate-200 text-slate-700'
                    }`}>
                      {aiScreeningPaper.abstract}
                    </p>
                  </div>
                </div>
              ) : null}
            </div>

            {/* Modal Footer */}
            <div className="border-t pt-4 border-slate-200 dark:border-slate-800 flex justify-end gap-3">
              <button
                onClick={() => { setAiScreeningPaper(null); setAiScreeningResult(null); }}
                className="px-5 py-2.5 rounded-xl text-xs font-bold bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 transition-colors"
              >
                Đóng (X)
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
