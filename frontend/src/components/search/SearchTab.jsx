import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { 
  Search, Download, ExternalLink, PlusCircle, CheckCircle2, Award, Key, Loader2, AlertCircle, ChevronDown, ChevronUp, ShieldCheck, CircleHelp,
  Activity, Check, X, HelpCircle
} from 'lucide-react';
import SearchHistoryPanel from './SearchHistoryPanel';
import FilterSortBar from './FilterSortBar';
import PaperTable from './PaperTable';
import { exportPapersToExcel } from '../../utils/excelExport';

const API_BASE = 'http://localhost:8000/api/v1';
const DEFAULT_PROJECT_ID = '00000000-0000-0000-0000-000000000001';

/**
 * Chuyển đổi PaperRecord (từ DB) sang định dạng Paper (Pydantic) để render.
 * DB dùng snake_case (lit_score, external_id); FE dùng camelCase (litScore, id).
 */
function dbPaperToPaperSchema(dbPaper) {
  return {
    // Always use our canonical DB UUID for Keep/Quality/Upload/Synthesis.
    id: dbPaper.id,
    externalId: dbPaper.external_id || null,
    title: dbPaper.title,
    authors: Array.isArray(dbPaper.authors) ? dbPaper.authors.join(', ') : (dbPaper.authors || ''),
    year: dbPaper.year,
    abstract: dbPaper.abstract || '',
    journal: dbPaper.journal || '',
    doi: dbPaper.doi || 'N/A',
    url: dbPaper.url || '#',
    citations: dbPaper.citations || 0,
    litScore: dbPaper.lit_score || 0,
    tldr: dbPaper.tldr || null,
    issn: dbPaper.issn || null,
    scopus_status: dbPaper.scopus_status || 'undetermined',
    scopus_quartile: dbPaper.scopus_quartile || null,
    coverage_year_status: dbPaper.coverage_year_status || null,
    oa_status: dbPaper.oa_status || 'undetermined',
  };
}

function apiPaperToCanonicalSchema(apiPaper) {
  return {
    ...apiPaper,
    externalId: apiPaper.id,
    id: apiPaper.db_id || apiPaper.id,
  };
}

export default function SearchTab({ 
  papers, 
  setPapers, 
  searchResults, 
  setSearchResults, 
  searchMeta, 
  setSearchMeta, 
  selectedPaperIds, 
  toggleSelectPaper, 
  workspacePapers,
  setWorkspacePapers,
  setActiveTab, 
  darkMode 
}) {
  const [searchQuery, setSearchQuery] = useState('large language models in healthcare');
  const [apiKey, setApiKey] = useState(() => localStorage.getItem('serp_api_key') || '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Screening States
  const [screeningLoading, setScreeningLoading] = useState({});
  const [projectData, setProjectData] = useState(null);
  const [screenErrorMsg, setScreenErrorMsg] = useState(null);

  // Search History state
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [activeQueryId, setActiveQueryId] = useState(null);

  // --- Filter & Sort States ---
  const [inResultQuery, setInResultQuery] = useState('');
  const [sortBy, setSortBy] = useState('source_order');
  const [viewMode, setViewMode] = useState('cards'); // 'cards' | 'table'
  const [activePreset, setActivePreset] = useState('scopus_confirmed');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [minLitScore, setMinLitScore] = useState(0);
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
      const converted = dbPapers.map(dbPaperToPaperSchema);
      setSearchResults(converted);
      
      // Update global papers to ensure data exists for selection
      setPapers(prev => {
        const newPapers = [...prev];
        converted.forEach(p => {
          if (!newPapers.find(existing => existing.id === p.id)) {
            newPapers.push(p);
          }
        });
        return newPapers;
      });

      setSearchMeta({
        provider: 'saved_search',
        limit: 20,
        total_found: converted.length,
        total_confirmed: converted.filter(p => p.scopus_status === 'indexed').length,
        total_undetermined: converted.filter(p => p.scopus_status === 'undetermined').length,
        duplicates: 0,
      });
      setActiveQueryId(queryId);
    } catch (err) {
      console.error('Failed to load papers for query:', err);
    }
  }, [setPapers, setSearchResults, setSearchMeta]);

  // Load project details for Screening criteria
  useEffect(() => {
    const fetchProject = async () => {
      try {
        const res = await fetch(`${API_BASE}/projects/00000000-0000-0000-0000-000000000001`);
        if (res.ok) {
          const data = await res.json();
          setProjectData(data);
        }
      } catch (err) {
        console.error("Lỗi khi fetch project:", err);
      }
    };
    fetchProject();
  }, []);

  // API Screening Logic
  const handleScreenPaper = async (paperId) => {
    setScreeningLoading(prev => ({ ...prev, [paperId]: true }));
    setScreenErrorMsg(null);
    try {
      const res = await fetch(`${API_BASE}/papers/${paperId}/screen`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setSearchResults(prev => prev.map(p => p.id === paperId ? { ...p, screening_data: data } : p));
        setPapers(prev => prev.map(p => p.id === paperId ? { ...p, screening_data: data } : p));
      } else {
        setScreenErrorMsg("Lỗi khi Screening. DB có thể đang đóng hoặc API lỗi.");
      }
    } catch (err) {
      console.error(err);
      setScreenErrorMsg("Mất kết nối với Server. Vui lòng kiểm tra Docker!");
    } finally {
      setScreeningLoading(prev => ({ ...prev, [paperId]: false }));
    }
  };

  const handleDecision = async (paperId, decision) => {
    // Optimistic update
    setSearchResults(prev => prev.map(p => p.id === paperId ? { ...p, screeningDecision: decision } : p));
    setPapers(prev => prev.map(p => p.id === paperId ? { ...p, screeningDecision: decision, screening_decision: decision } : p));
    
    // Save to workspace if kept
    if (decision === 'keep' || decision === 'maybe') {
      const paperToSave = searchResults.find(p => p.id === paperId) || papers.find(p => p.id === paperId);
      if (paperToSave && setWorkspacePapers) {
        setWorkspacePapers(prev => {
          if (!prev.find(p => p.id === paperId)) {
            return [...prev, { ...paperToSave, screeningDecision: decision, screening_decision: decision }];
          }
          return prev;
        });
      }
    }

    // Server update
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

  // Chỉ tải danh sách lịch sử khi mount (không tự động load papers cũ ra màn hình)
  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  // Thực hiện search mới
  const handleSearch = async (e) => {
    if (e) e.preventDefault();
    if (!searchQuery.trim()) return;

    if (!apiKey.trim()) {
      setError('Vui lòng nhập SerpApi Key để lấy Top 20 từ Google Scholar.');
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
      if (data.papers && data.papers.length > 0) {
        const canonicalPapers = data.papers.map(apiPaperToCanonicalSchema);
        setSearchResults(canonicalPapers);
        
        // Update global papers
        setPapers(prev => {
          const newPapers = [...prev];
          canonicalPapers.forEach(p => {
            if (!newPapers.find(existing => existing.id === p.id)) {
              newPapers.push(p);
            }
          });
          return newPapers;
        });

        setSearchMeta({
          provider: data.provider || 'google_scholar',
          limit: data.limit || 20,
          total_found: data.total_found ?? canonicalPapers.length,
          total_confirmed: data.total_confirmed ?? canonicalPapers.filter(p => p.scopus_status === 'indexed').length,
          total_undetermined: data.total_undetermined ?? canonicalPapers.filter(p => p.scopus_status === 'undetermined').length,
          duplicates: data.duplicates ?? 0,
        });
        if (data.search_query_id) {
          setActiveQueryId(data.search_query_id);
        }
        await fetchHistory();
      } else {
        setSearchResults([]);
        setError('Không tìm thấy bài báo nào phù hợp với từ khóa này.');
      }
    } catch (err) {
      console.error(err);
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        setError('Không thể kết nối đến Backend (http://localhost:8000). Vui lòng đảm bảo bạn đã bật Backend bằng lệnh `uvicorn src.main:app --reload` trên máy!');
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

  const availableJournals = useMemo(() => {
    const journals = searchResults.map(p => p.journal).filter(Boolean);
    return Array.from(new Set(journals));
  }, [searchResults]);

  const hasActiveFilters = useMemo(() => {
    return (
      inResultQuery !== '' ||
      activePreset !== 'scopus_confirmed' ||
      minLitScore > 0 ||
      minCitations > 0 ||
      startYear !== '' ||
      endYear !== '' ||
      selectedJournal !== 'All'
    );
  }, [inResultQuery, activePreset, minLitScore, minCitations, startYear, endYear, selectedJournal]);

  const resetFilters = () => {
    setInResultQuery('');
    setActivePreset('scopus_confirmed');
    setMinLitScore(0);
    setMinCitations(0);
    setStartYear('');
    setEndYear('');
    setSelectedJournal('All');
  };

  const filteredAndSortedPapers = useMemo(() => {
    let result = [...searchResults];

    if (activePreset === 'scopus_confirmed' || activePreset === 'scopus_only') {
      result = result.filter(p => p.scopus_status === 'indexed');
    } else if (activePreset === 'undetermined') {
      result = result.filter(p => p.scopus_status === 'undetermined' || !p.scopus_status);
    } else if (activePreset === 'high_score') {
      result = result.filter(p => p.litScore >= 70);
    } else if (activePreset === 'recent') {
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

    if (minLitScore > 0) result = result.filter(p => p.litScore >= minLitScore);
    if (minCitations > 0) result = result.filter(p => p.citations >= minCitations);
    if (startYear !== '') result = result.filter(p => p.year >= Number(startYear));
    if (endYear !== '') result = result.filter(p => p.year <= Number(endYear));
    if (selectedJournal !== 'All') result = result.filter(p => p.journal === selectedJournal);

    result.sort((a, b) => {
      switch (sortBy) {
        case 'litscore_desc': return b.litScore - a.litScore;
        case 'litscore_asc': return a.litScore - b.litScore;
        case 'citations_desc': return b.citations - a.citations;
        case 'year_desc': return b.year - a.year;
        case 'year_asc': return a.year - b.year;
        case 'title_asc': return a.title.localeCompare(b.title);
        case 'source_order':
        default: return 0;
      }
    });

    return result;
  }, [searchResults, activePreset, inResultQuery, minLitScore, minCitations, startYear, endYear, selectedJournal, sortBy]);

  const handleExportExcel = () => {
    const dataToExport = selectedPaperIds.length > 0
      ? papers.filter(p => selectedPaperIds.includes(p.id))
      : filteredAndSortedPapers;
    exportPapersToExcel(dataToExport, `LitReview_Export_${new Date().toISOString().slice(0, 10)}.xlsx`);
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto py-4">
      {/* Page Title Header */}
      <div className="text-center space-y-3">
        <h2 className={`text-3xl md:text-4xl font-extrabold tracking-tight ${darkMode ? 'text-white' : 'text-slate-900'}`}>
          Search & Verify
        </h2>
        <p className={`text-base max-w-2xl mx-auto font-medium ${darkMode ? 'text-slate-400' : 'text-slate-600'}`}>
          Lấy Top 20 từ Google Scholar theo đúng thứ tự Google trả về, sau đó đối chiếu Scopus trước khi hiển thị để bạn chọn bài đưa vào Screening.
        </p>
      </div>

      {/* BYOK API Key Banner */}
      <div className={`p-4 md:p-5 rounded-3xl border transition-all ${
        darkMode ? 'bg-slate-900/90 border-slate-800' : 'bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-100'
      }`}>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-sm font-bold text-blue-700 dark:text-sky-300">
            <Key className="w-4 h-4 shrink-0 text-blue-600 dark:text-sky-400" />
            <span>API Key Google Scholar qua SerpApi:</span>
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
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Nhập từ khóa nghiên cứu (ví dụ: 'large language models in healthcare')..."
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
                <span>Tìm Top 20</span>
            )}
          </button>
        </div>
      </form>

      {searchResults.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div className={`p-4 rounded-2xl border ${darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'}`}>
            <p className="text-xs font-bold text-slate-500 uppercase">Provider</p>
            <p className="mt-1 text-sm font-extrabold flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-blue-600" />
              {searchMeta.provider === 'google_scholar' ? 'Google Scholar' : searchMeta.provider}
            </p>
          </div>
          <div className={`p-4 rounded-2xl border ${darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'}`}>
            <p className="text-xs font-bold text-slate-500 uppercase">Top results</p>
            <p className="mt-1 text-2xl font-extrabold">{searchMeta.total_found}/{searchMeta.limit}</p>
          </div>
          <div className={`p-4 rounded-2xl border ${darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'}`}>
            <p className="text-xs font-bold text-slate-500 uppercase">Scopus confirmed</p>
            <p className="mt-1 text-2xl font-extrabold text-emerald-600">{searchMeta.total_confirmed}</p>
          </div>
          <div className={`p-4 rounded-2xl border ${darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'}`}>
            <p className="text-xs font-bold text-slate-500 uppercase">Undetermined</p>
            <p className="mt-1 text-2xl font-extrabold text-slate-500 flex items-center gap-2">
              {searchMeta.total_undetermined}
              <CircleHelp className="w-4 h-4" title="Thiếu dữ liệu để kết luận, không phải Not indexed" />
            </p>
          </div>
        </div>
      )}

      {/* Search History Panel */}
      <SearchHistoryPanel
        history={history}
        onLoadPapers={loadPapersForQuery}
        onDuplicate={handleDuplicate}
        darkMode={darkMode}
        loading={historyLoading}
      />

      {/* Error Alert */}
      {error && (
        <div className="p-4 rounded-2xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800/60 text-red-700 dark:text-red-300 text-sm font-semibold flex items-center gap-3">
          <AlertCircle className="w-5 h-5 shrink-0 text-red-500" />
          <span>{error}</span>
        </div>
      )}

      {/* Filter & Sort Controls Bar */}
      {searchResults.length > 0 && (
        <FilterSortBar
          totalCount={searchResults.length}
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
          minLitScore={minLitScore}
          setMinLitScore={setMinLitScore}
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
              Kết quả tìm thấy ({searchResults.length} bài báo)
            </span>
            {activeQueryId && (
              <span className="text-xs font-mono text-slate-400 dark:text-slate-500">
                (đã lưu)
              </span>
            )}
          </div>
          {selectedPaperIds.length > 0 && (
            <span className="text-sm font-bold text-blue-600 dark:text-sky-400">
              Đã chọn {selectedPaperIds.length} bài để đưa lên AI
            </span>
          )}
        </div>

        {/* Project Criteria Banner */}
        {projectData && searchResults.length > 0 && (
          <div className={`p-5 rounded-3xl border shadow-sm ${darkMode ? 'bg-slate-900 border-slate-800' : 'bg-blue-50 border-blue-100'} mb-6`}>
            <h3 className="font-bold text-lg mb-2">Chủ đề: {projectData.name}</h3>
            <p className="text-sm mb-3"><span className="font-semibold">Câu hỏi NC:</span> {projectData.research_question}</p>
            <div className="flex gap-6 text-sm">
              <div>
                <span className="font-semibold text-emerald-600">Nên có (Inclusion):</span>
                <ul className="list-disc ml-5 opacity-80">
                  {projectData.criteria_include?.map((c, i) => <li key={i}>{c}</li>)}
                </ul>
              </div>
              <div>
                <span className="font-semibold text-red-600">Loại trừ (Exclusion):</span>
                <ul className="list-disc ml-5 opacity-80">
                  {projectData.criteria_exclude?.map((c, i) => <li key={i}>{c}</li>)}
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* Empty State */}
        {searchResults.length === 0 && !loading && (
          <div className={`p-12 text-center rounded-3xl border ${
            darkMode ? 'bg-slate-900/60 border-slate-800 text-slate-400' : 'bg-white border-slate-200 text-slate-500'
          }`}>
            <Search className="w-12 h-12 mx-auto mb-4 opacity-30 text-blue-500" />
            <h3 className="text-lg font-bold mb-1">Chưa có kết quả tìm kiếm nào</h3>
            <p className="text-sm max-w-md mx-auto">
              Hãy nhập SerpApi Key ở trên, sau đó gõ từ khóa nghiên cứu và nhấn nút <strong>"Tìm Top 20"</strong>. 
            </p>
          </div>
        )}

        {/* Filter Empty State */}
        {searchResults.length > 0 && filteredAndSortedPapers.length === 0 && (
          <div className={`p-10 text-center rounded-3xl border ${
            darkMode ? 'bg-slate-900/60 border-slate-800 text-slate-400' : 'bg-white border-slate-200 text-slate-500'
          }`}>
            <Search className="w-10 h-10 mx-auto mb-3 opacity-40 text-amber-500" />
            <h3 className="text-base font-bold text-slate-800 dark:text-slate-200 mb-1">Không có bài báo nào phù hợp với bộ lọc</h3>
            <p className="text-xs max-w-sm mx-auto mb-4">
              Vui lòng thử nới lỏng các tiêu chí lọc hoặc nhấn "Xóa bộ lọc" để hiển thị lại toàn bộ kết quả.
            </p>
            <button
              onClick={resetFilters}
              className="px-4 py-2 bg-blue-600 text-white font-bold text-xs rounded-xl hover:bg-blue-700 transition-colors"
            >
              Xóa bộ lọc hiện tại
            </button>
          </div>
        )}

        {/* View Mode: Table View */}
        {searchResults.length > 0 && viewMode === 'table' && filteredAndSortedPapers.length > 0 && (
          <PaperTable
            papers={filteredAndSortedPapers}
            selectedPaperIds={selectedPaperIds}
            toggleSelectPaper={toggleSelectPaper}
            darkMode={darkMode}
          />
        )}

        {/* View Mode: Cards View */}
        {searchResults.length > 0 && viewMode === 'cards' && filteredAndSortedPapers.map((paper) => {
          const isSelected = selectedPaperIds.includes(paper.id);
          const isExpanded = expandedPaperIds.includes(paper.id);
          const isScreening = screeningLoading[paper.id];
          const screenData = paper.screening_data;
          const decision = paper.screeningDecision;

          if (decision) return null; // Hide paper if decision is made

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
                    {(paper.scopus_status === 'undetermined' || !paper.scopus_status) && (
                      <span className="px-2.5 py-1 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 text-xs font-bold rounded-lg border border-slate-200 dark:border-slate-700 flex items-center gap-1">
                        ⚪ Undetermined
                      </span>
                    )}
                    <span className="text-xs font-mono font-bold text-slate-400">ID: {paper.id}</span>
                  </div>

                  <h3 className={`font-extrabold text-lg md:text-xl leading-snug ${darkMode ? 'text-white' : 'text-slate-900'}`}>
                    {paper.title}
                  </h3>
                  
                  <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">
                    Tác giả: {paper.authors}
                  </p>
                </div>
              </div>

              {/* Abstract & TL;DR */}
              <div className={`p-5 rounded-2xl text-sm leading-relaxed border transition-all ${
                darkMode ? 'bg-slate-800/80 border-slate-700 text-slate-300' : 'bg-slate-50 border-slate-200 text-slate-700'
              }`}>
                {paper.tldr && (
                  <div className="mb-3 p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-100 dark:border-emerald-800/50">
                    <p className="font-bold text-emerald-700 dark:text-emerald-400">⚡ Tóm tắt siêu tốc (AI TL;DR):</p>
                    <p className="text-emerald-800 dark:text-emerald-300 mt-1">{paper.tldr.replace('TL;DR: ', '')}</p>
                  </div>
                )}
                
                <p className="font-bold text-blue-600 dark:text-sky-400 mb-1">📝 Tóm tắt Abstract:</p>

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
                      <span>Thu gọn tóm tắt</span>
                    </>
                  ) : (
                    <>
                      <ChevronDown className="w-4 h-4 text-blue-600 dark:text-sky-400" />
                      <span>Xem thêm tóm tắt đầy đủ...</span>
                    </>
                  )}
                </button>
              </div>

              {/* Action Buttons Footer (Screening Integrated) */}
              <div className="flex flex-col gap-4 pt-4 border-t border-slate-100 dark:border-slate-800">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 font-mono">
                    DOI: {paper.doi} • {paper.citations ? paper.citations.toLocaleString() : 0} lượt trích dẫn
                  </div>
                  <a
                    href={paper.url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1 text-xs font-bold text-blue-600 dark:text-sky-400 hover:underline"
                  >
                    Tải PDF Gốc <ExternalLink className="w-3 h-3" />
                  </a>
                </div>

                {!screenData && !isScreening && (
                  <button 
                    onClick={() => handleScreenPaper(paper.id)}
                    className="w-full sm:w-auto px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl flex items-center justify-center gap-2 shadow-md transition-colors"
                  >
                    <Activity className="w-5 h-5"/> Bắt đầu AI Screening
                  </button>
                )}

                {isScreening && (
                  <div className="flex items-center gap-2 text-indigo-600 text-sm font-bold animate-pulse p-2">
                    <Loader2 className="w-5 h-5 animate-spin"/> Đang phân tích mức độ liên quan...
                  </div>
                )}

                {screenData && (
                  <div className={`p-5 rounded-2xl border shadow-inner ${screenData.relevance_bucket === 'high' ? 'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800' : screenData.relevance_bucket === 'medium' ? 'bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800' : 'bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800'}`}>
                    <div className="font-extrabold text-sm uppercase mb-3 flex items-center gap-2">
                      Độ phù hợp (Relevance): 
                      <span className={`${screenData.relevance_bucket === 'high' ? 'text-emerald-700 dark:text-emerald-400' : screenData.relevance_bucket === 'medium' ? 'text-amber-700 dark:text-amber-400' : 'text-red-700 dark:text-red-400'}`}>
                        {screenData.relevance_bucket}
                      </span>
                    </div>
                    
                    <div className="text-sm text-slate-700 dark:text-slate-300 space-y-3 mb-5">
                      {screenData.reason?.matches?.length > 0 && (
                        <div>
                          <span className="font-bold text-emerald-700 dark:text-emerald-400 flex items-center gap-1"><CheckCircle2 className="w-4 h-4"/> Khớp:</span>
                          <ul className="list-disc ml-6 mt-1 opacity-90">{screenData.reason.matches.map((m, i) => <li key={i}>{m}</li>)}</ul>
                        </div>
                      )}
                      {screenData.reason?.mismatches?.length > 0 && (
                        <div>
                          <span className="font-bold text-red-700 dark:text-red-400 flex items-center gap-1"><X className="w-4 h-4"/> Không khớp:</span>
                          <ul className="list-disc ml-6 mt-1 opacity-90">{screenData.reason.mismatches.map((m, i) => <li key={i}>{m}</li>)}</ul>
                        </div>
                      )}
                    </div>

                    <div className="flex flex-col sm:flex-row gap-3">
                      <button onClick={() => handleDecision(paper.id, 'keep')} className="flex-1 px-5 py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl flex items-center justify-center gap-2 text-sm shadow transition-colors">
                        <Check className="w-4 h-4"/> Keep (Đưa vào Workspace)
                      </button>
                      <button onClick={() => handleDecision(paper.id, 'maybe')} className="flex-1 px-5 py-3 bg-amber-500 hover:bg-amber-600 text-white font-bold rounded-xl flex items-center justify-center gap-2 text-sm shadow transition-colors">
                        <HelpCircle className="w-4 h-4"/> Maybe
                      </button>
                      <button onClick={() => handleDecision(paper.id, 'remove')} className="flex-1 px-5 py-3 bg-red-600 hover:bg-red-700 text-white font-bold rounded-xl flex items-center justify-center gap-2 text-sm shadow transition-colors">
                        <X className="w-4 h-4"/> Remove
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
