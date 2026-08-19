import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { 
  Search, Download, ExternalLink, PlusCircle, CheckCircle2, Key, Loader2, AlertCircle, 
  ChevronDown, ChevronUp, ShieldCheck, ShieldAlert, Activity, Check, X, HelpCircle,
  BookOpen, Sparkles, Trash2, Target, GitFork, FileText
} from 'lucide-react';
import SearchHistoryPanel from './SearchHistoryPanel';
import FilterSortBar from './FilterSortBar';
import PaperTable from './PaperTable';
import { exportPapersToExcel } from '../../utils/excelExport';
import { useLanguage } from '../../contexts/LanguageContext';

import { API_BASE } from '../../utils/apiConfig';
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

export default function SearchTab({ papers, setPapers, selectedPaperIds, selectedPapers = [], toggleSelectPaper, clearSelectedPapers, setActiveTab, darkMode }) {
  const { t } = useLanguage();
  const [apiKey, setApiKey] = useState(
    localStorage.getItem('litreview_serpapi_key') || ''
  );
  // Helper: chỉ giữ từ khóa tiếng Anh hợp lệ (loại bỏ từ tiếng Việt rác)
  const filterEnglishKeywords = (arr) => {
    if (!Array.isArray(arr)) return [];
    return arr.filter(kw => kw && kw.trim().length >= 3 && /^[a-zA-Z0-9\s\-\/&.]+$/.test(kw.trim()));
  };

  const [queryChips, setQueryChips] = useState(() => {
    try {
      const raw = localStorage.getItem('suggested_keywords');
      if (raw) {
        const arr = JSON.parse(raw);
        const filtered = arr.filter(kw => kw && kw.trim().length >= 3 && /^[a-zA-Z0-9\s\-\/&.]+$/.test(kw.trim()));
        if (filtered.length > 0) return filtered;
      }
    } catch (e) {}
    const saved = localStorage.getItem('last_search_query');
    return saved ? [saved] : [];
  });

  const [suggestedKeywords, setSuggestedKeywords] = useState(() => {
    try {
      const cachedPico = localStorage.getItem('slr_pico_data');
      if (cachedPico) {
        const p = JSON.parse(cachedPico);
        const filtered = filterEnglishKeywords(p.search_keywords);
        if (filtered.length > 0) return filtered;
      }
      const raw = localStorage.getItem('suggested_keywords');
      if (raw) {
        const parsed = JSON.parse(raw);
        const filtered = filterEnglishKeywords(parsed);
        if (filtered.length > 0) return filtered;
      }
    } catch (e) {}
    return [];
  });

  // Lắng nghe Mesh Query & Keywords mới từ Setup Tab
  useEffect(() => {
    const handleMeshQuery = () => {
      try {
        const cachedPico = localStorage.getItem('slr_pico_data');
        if (cachedPico) {
          const p = JSON.parse(cachedPico);
          const filtered = filterEnglishKeywords(p.search_keywords);
          if (filtered.length > 0) {
            setSuggestedKeywords(filtered);
            setQueryChips(filtered);
            return;
          }
        }
        const raw = localStorage.getItem('suggested_keywords');
        if (raw) {
          const arr = JSON.parse(raw);
          const filtered = filterEnglishKeywords(arr);
          if (filtered.length > 0) {
            setSuggestedKeywords(filtered);
            setQueryChips(filtered);
            return;
          }
        }
      } catch (e) {}
    };
    window.addEventListener('new_mesh_query_ready', handleMeshQuery);
    handleMeshQuery();
    return () => window.removeEventListener('new_mesh_query_ready', handleMeshQuery);
  }, []);
  const [searchQuery, setSearchQuery] = useState('');
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

  // Gap Map Modal state for Search Tab
  const [showGapModal, setShowGapModal] = useState(false);
  const [gapMapLoading, setGapMapLoading] = useState(false);
  const [gapMapData, setGapMapData] = useState(null);

  const handleOpenGapAnalysis = async () => {
    setShowGapModal(true);
    if (gapMapData) return;
    setGapMapLoading(true);
    try {
      const idea = projectData?.research_question || projectData?.name || 'Academic Research';
      const res = await fetch(`${API_BASE}/slr-swarm/step1-setup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          idea,
          research_field: projectData?.research_field || '',
          criteria_include: projectData?.criteria_include || [],
          criteria_exclude: projectData?.criteria_exclude || [],
          corpus: papers.map(p => ({
            paper_id: String(p.id),
            title: p.title,
            abstract: p.abstract || '',
            year: p.year,
            venue: p.journal,
            doi: p.doi
          }))
        })
      });
      if (res.ok) {
        const data = await res.json();
        setGapMapData(data.gap_map);
      }
    } catch (err) {
      console.error("Gap analysis error:", err);
    } finally {
      setGapMapLoading(false);
    }
  };

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
  const [isQuestionExpanded, setIsQuestionExpanded] = useState(false);

  // --- Paper Summary States (TL;DR) ---
  const [summaryPaper, setSummaryPaper] = useState(null);
  const [summaryData, setSummaryData] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(false);

  const handleOpenSummary = async (paper) => {
    setSummaryPaper(paper);
    setSummaryData(null);
    setSummaryLoading(true);
    try {
      const res = await fetch(`${API_BASE}/slr-swarm/paper-summary`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          paper_id: paper.id || paper.external_id || "unknown",
          title: paper.title || "No title",
          abstract: paper.abstract || "",
          authors: Array.isArray(paper.authors) ? paper.authors.join(", ") : (paper.authors || ""),
          year: paper.year || 2024,
          venue: paper.venue || paper.journal || "",
          citations: paper.citations || 0,
          doi: paper.doi || ""
        })
      });
      if (!res.ok) throw new Error("Failed to fetch summary");
      const data = await res.json();
      setSummaryData(data);
    } catch (err) {
      console.error("Summary error:", err);
      setSummaryData({ tldr: "Không thể kết nối đến máy chủ AI để sinh tóm tắt." });
    } finally {
      setSummaryLoading(false);
    }
  };

  // --- Citation Genealogy States (Smart Snowballing) ---
  const [genealogyPaper, setGenealogyPaper] = useState(null);
  const [genealogyData, setGenealogyData] = useState(null);
  const [genealogyLoading, setGenealogyLoading] = useState(false);

  const handleOpenGenealogy = async (paper) => {
    setGenealogyPaper(paper);
    setGenealogyData(null);
    setGenealogyLoading(true);
    try {
      const res = await fetch(`${API_BASE}/slr-swarm/paper-genealogy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          paper_id: String(paper.id),
          title: paper.title,
          doi: paper.doi || '',
          authors: Array.isArray(paper.authors) ? paper.authors.join(', ') : String(paper.authors || ''),
          year: Number(paper.year) || 2024,
          abstract: paper.abstract || ''
        })
      });
      if (res.ok) {
        const data = await res.json();
        setGenealogyData(data);
      }
    } catch (err) {
      console.error("Genealogy error:", err);
    } finally {
      setGenealogyLoading(false);
    }
  };

  const handleAddGenealogyPaper = (newPaper) => {
    const formatted = {
      id: newPaper.doi || `gen_${Date.now()}_${Math.random().toString(36).substr(2, 4)}`,
      title: newPaper.title,
      authors: newPaper.authors,
      year: newPaper.year,
      abstract: newPaper.relevance_note || '',
      journal: newPaper.venue || '',
      doi: newPaper.doi || 'N/A',
      url: newPaper.doi ? `https://doi.org/${newPaper.doi}` : '#',
      citations: newPaper.citations || 0,
      litScore: 85,
      tldr: newPaper.relevance_note || null,
      scopus_status: 'indexed',
      oa_status: 'gold'
    };
    if (!papers.some(p => p.title.toLowerCase() === formatted.title.toLowerCase())) {
      setPapers(prev => [formatted, ...prev]);
    }
  };

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
    setSearchQuery(e.target.value);
  };

  const handleInputKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (searchQuery.trim()) {
        const newChips = [...queryChips, searchQuery.trim()];
        setQueryChips(newChips);
        setSearchQuery('');
        localStorage.setItem('last_search_query', newChips.join(' '));
      }
    }
  };

  const removeChip = (indexToRemove) => {
    const newChips = queryChips.filter((_, idx) => idx !== indexToRemove);
    setQueryChips(newChips);
    localStorage.setItem('last_search_query', newChips.join(' '));
  };

  // AI Screening handler
  const handleOpenAiScreening = async (paper) => {
    setAiScreeningPaper(paper);
    setAiScreeningResult(null);
    setAiScreeningLoading(true);

    try {
      const res = await fetch(`${API_BASE}/papers/${encodeURIComponent(paper.id)}/screen`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: paper.title,
          abstract: paper.abstract,
          journal: paper.journal,
          year: paper.year,
          doi: paper.doi,
          authors: paper.authors
        })
      });
      if (res.ok) {
        const data = await res.json();
        setAiScreeningResult(data);
      } else {
        // Smart fallback assessment with null checks
        const abstractStr = paper.abstract || "";
        const titleStr = paper.title || "";
        
        const matches = (projectData?.criteria_include || []).filter(c => 
          abstractStr.toLowerCase().includes(c.toLowerCase()) || 
          titleStr.toLowerCase().includes(c.toLowerCase())
        );
        const mismatches = (projectData?.criteria_exclude || []).filter(c => 
          abstractStr.toLowerCase().includes(c.toLowerCase())
        );

        setAiScreeningResult({
          relevance_bucket: matches.length > 0 ? (matches.length >= 2 ? 'high' : 'medium') : 'insufficient_info',
          reason: {
            matches: matches.length > 0 ? matches.map(m => `Khớp tiêu chí chọn: "${m}"`) : [`Không tìm thấy điểm khớp rõ ràng (Fallback).`],
            mismatches: mismatches.length > 0 ? mismatches.map(m => `Cảnh báo tiêu chí loại: "${m}"`) : ['Không vi phạm tiêu chí loại trừ nào.']
          }
        });
      }
    } catch (err) {
      console.error("AI screening error:", err);
      setAiScreeningResult({
        relevance_bucket: 'insufficient_info',
        reason: {
          matches: [],
          mismatches: ['Lỗi kết nối tới Server hoặc AI. Vui lòng thử lại sau.']
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
  const loadPapersForQuery = useCallback(async (queryId, queryString) => {
    try {
      const res = await fetch(`${API_BASE}/search-queries/${queryId}/papers`);
      if (!res.ok) return;
      const dbPapers = await res.json();
      const converted = dbPapers.map(dbPaperToPaperSchema);
      setPapers(converted);

      if (queryString) {
        setQueryChips([queryString]);
        localStorage.setItem('last_search_query', queryString);
      }

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
        await loadPapersForQuery(latestQuery.id, latestQuery.query_string);
      }
    };
    restore();
  }, []);

  // Thực hiện search mới
  const handleSearch = async (e) => {
    if (e) e.preventDefault();
    
    let finalChips = [...queryChips];
    if (searchQuery.trim()) {
      finalChips.push(searchQuery.trim());
      setQueryChips(finalChips);
      setSearchQuery('');
    }

    if (finalChips.length === 0) {
      setError(t('search.error_no_keyword'));
      return;
    }

    if (!apiKey.trim()) {
      setError(t('search.error_no_api_key'));
      return;
    }

    const finalQueryString = finalChips.join(' ');
    localStorage.setItem('last_search_query', finalQueryString);

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
          query_string: finalQueryString,
          strategy_label: null
        })
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Lỗi tìm kiếm từ server');
      }

      const data = await response.json();
      const scopusOnly = data.papers || [];
      if (scopusOnly.length > 0) {
        setPapers(scopusOnly);
        const confirmedCount = scopusOnly.filter(p => p.scopus_status === 'indexed').length;
        const undeterminedCount = scopusOnly.filter(p => p.scopus_status !== 'indexed').length;
        setSearchMeta({
          provider: data.provider || 'google_scholar',
          limit: data.limit || 20,
          total_found: scopusOnly.length,
          total_confirmed: confirmedCount,
          total_undetermined: undeterminedCount,
          duplicates: data.duplicates ?? 0,
        });
        if (data.search_query_id) {
          setActiveQueryId(data.search_query_id);
        }
        await fetchHistory();
      } else {
        setPapers([]);
        setError(t('search.error_no_result'));
      }
    } catch (err) {
      console.error(err);
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        setError(t('search.error_backend'));
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

  const handleExportExcel = (selectedPapers = []) => {
    const dataToExport = selectedPapers.length > 0
      ? selectedPapers
      : filteredAndSortedPapers;
    exportPapersToExcel(dataToExport, `LitReview_Export_${new Date().toISOString().slice(0, 10)}.xlsx`);
  };

  return (
    <div className="flex gap-6 max-w-[1400px] mx-auto py-4">
      
      {/* ====== SIDEBAR: Left side (Scrollable & Sticky) ====== */}
      <aside className={`w-full lg:w-72 shrink-0 self-start max-h-[calc(100vh-6.5rem)] overflow-y-auto custom-scrollbar sticky top-24 space-y-4 p-4 rounded-3xl border transition-colors shadow-sm ${
        darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
      }`}>
        {/* --- 1. Chủ đề & Phạm vi Nghiên cứu (Tinh gọn) --- */}
        <div className={`p-4 rounded-2xl border ${darkMode ? 'bg-slate-800/50 border-slate-700/60' : 'bg-slate-50 border-slate-200'}`}>
          <div className="flex items-center justify-between gap-2 mb-3 border-b pb-2 border-slate-200 dark:border-slate-700">
            <div className="flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-blue-600 dark:text-sky-400" />
              <h4 className="text-xs font-display font-bold uppercase tracking-wider text-slate-800 dark:text-slate-200">
                Chủ đề & Phạm vi
              </h4>
            </div>
            <span className="px-2 py-0.5 rounded-md bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-sky-300 text-[10px] font-bold">
              {projectData?.year_from || 2020} - {projectData?.year_to || 2026}
            </span>
          </div>

          <div className="space-y-2.5 text-xs">
            <div>
              <p className="font-bold text-[10px] text-slate-400 uppercase tracking-wider">Lĩnh vực nghiên cứu:</p>
              <p className="font-semibold text-slate-800 dark:text-slate-200 mt-0.5">
                {projectData?.research_field || "Chưa xác định"}
              </p>
            </div>

            <div>
              <p className="font-bold text-[10px] text-slate-400 uppercase tracking-wider">Câu hỏi nghiên cứu:</p>
              <p className={`font-normal text-slate-600 dark:text-slate-400 mt-0.5 leading-relaxed ${
                isQuestionExpanded ? '' : 'line-clamp-2'
              }`}>
                {projectData?.research_question || projectData?.name || "Chưa thiết lập"}
              </p>
              {((projectData?.research_question || projectData?.name || '').length > 75) && (
                <button
                  type="button"
                  onClick={() => setIsQuestionExpanded(!isQuestionExpanded)}
                  className="text-[10px] font-bold text-blue-600 dark:text-sky-400 hover:underline flex items-center gap-0.5 mt-1 transition-colors"
                >
                  <span>{isQuestionExpanded ? 'Thu gọn' : 'Xem đầy đủ'}</span>
                  {isQuestionExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                </button>
              )}
            </div>
          </div>
        </div>

        {/* --- 2. Lịch sử tìm kiếm Panel (Middle) --- */}
        <SearchHistoryPanel
          history={history}
          onLoadPapers={loadPapersForQuery}
          onDuplicate={handleDuplicate}
          onDeleteQuery={(deletedId) => setHistory(prev => prev.filter(item => item.id !== deletedId))}
          darkMode={darkMode}
          loading={historyLoading}
          isSidebar={true}
        />

        {/* --- 3. Cơ hội & Khoảng trống nghiên cứu Panel (Bottom) --- */}
        <div className={`p-4 rounded-2xl border ${darkMode ? 'bg-slate-800/40 border-slate-700/60' : 'bg-slate-50 border-slate-200'} space-y-3`}>
          <div className="flex items-center gap-2">
            <Target className="w-4 h-4 text-blue-600 dark:text-sky-400" />
            <h4 className="text-xs font-display font-bold uppercase tracking-wider text-slate-800 dark:text-slate-200">
              Cơ hội & Khoảng trống
            </h4>
          </div>
          <p className="text-[11px] text-slate-500 leading-relaxed font-normal">
            Phân tích điểm nghẽn và phát hiện cơ hội đề tài mới từ <strong>{papers.length} bài báo</strong> đã tìm thấy.
          </p>
          <button
            type="button"
            onClick={handleOpenGapAnalysis}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl font-display font-bold text-xs bg-blue-600 hover:bg-blue-700 text-white shadow-sm transition-all hover:scale-[1.02] active:scale-95"
          >
            <Target className="w-3.5 h-3.5" />
            <span>Phân tích Khoảng trống</span>
          </button>
        </div>
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
                    {projectData.name || t('search.unnamed_project')}
                  </h3>
                  <p className={`text-xs truncate mt-0.5 ${darkMode ? 'text-slate-400' : 'text-slate-600'}`}>
                    {projectData.research_question || t('search.no_question')}
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
            {t('search.tab_title')}
          </h2>
          <p className={`text-sm max-w-2xl mx-auto font-medium ${darkMode ? 'text-slate-400' : 'text-slate-600'}`}>
            {t('search.tab_desc')}
          </p>
        </div>

        {/* BYOK API Key Banner */}
        <div className={`p-4 rounded-3xl border transition-all ${
          darkMode ? 'bg-slate-900/90 border-slate-800' : 'bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-100'
        }`}>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-sm font-bold text-blue-700 dark:text-sky-300">
              <Key className="w-4 h-4 shrink-0 text-blue-600 dark:text-sky-400" />
              <span>{t('search.api_key_label')}</span>
            </div>
            <div className="flex-1 max-w-md flex items-center gap-2">
              <input
                type="password"
                value={apiKey}
                onChange={handleApiKeyChange}
                placeholder={t('search.api_key_placeholder')}
                className={`w-full px-4 py-2 border rounded-xl text-xs font-mono focus:outline-none focus:ring-2 focus:ring-blue-600 ${
                  darkMode ? 'bg-slate-800 border-slate-700 text-white placeholder-slate-500' : 'bg-white border-slate-300 text-slate-900'
                }`}
              />
            </div>
            <div className="flex items-center gap-3 text-xs font-bold text-blue-600 dark:text-sky-400 shrink-0">
              <a href="https://serpapi.com/users/sign_up" target="_blank" rel="noreferrer" className="hover:underline flex items-center gap-1">
                <span>{t('search.get_api_key')}</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>
        </div>

        {/* Active Suggested Keywords Banner */}
        {suggestedKeywords && suggestedKeywords.length > 0 && (
          <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 text-slate-200 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-inner">
            <div className="flex flex-col sm:flex-row sm:items-center gap-2.5 overflow-x-auto">
              <span className="text-amber-400 font-extrabold shrink-0 uppercase tracking-wider">Các từ khóa gợi ý:</span>
              <div className="flex flex-wrap gap-2">
                {suggestedKeywords.map((kw, idx) => (
                  <span 
                    key={idx} 
                    onClick={() => setSearchQuery(kw)}
                    className="px-3 py-1.5 rounded-xl bg-indigo-600/90 hover:bg-indigo-500 text-white font-bold text-xs border border-indigo-400/40 cursor-pointer transition-all hover:scale-105 shadow-md"
                    title="Nhấn để đưa vào ô tìm kiếm"
                  >
                    {kw}
                  </span>
                ))}
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <button
                type="button"
                onClick={() => navigator.clipboard.writeText(suggestedKeywords.join(' '))}
                className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-amber-300 font-bold text-xs border border-slate-700 transition-colors"
              >
                Sao chép
              </button>
              <button
                type="button"
                onClick={() => setSearchQuery(suggestedKeywords.join(' '))}
                className="px-3 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs transition-colors"
              >
                Điền vào ô tìm kiếm
              </button>
            </div>
          </div>
        )}

        {/* Search Bar */}
        <form onSubmit={handleSearch} className={`p-4 md:p-6 rounded-3xl border shadow-lg transition-colors ${
          darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
        }`}>
          <div className="flex flex-col gap-4">
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <Search className="w-6 h-6 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={handleSearchQueryChange}
                  onKeyDown={handleInputKeyDown}
                  placeholder={t('search.search_placeholder')}
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
                    <span>{t('search.searching')}</span>
                  </>
                ) : (
                    <span>{t('search.search_btn')}</span>
                )}
              </button>
            </div>
            
            {/* Display Chips */}
            {queryChips.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {queryChips.map((chip, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-sm font-bold bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-200 border border-blue-200 dark:border-blue-800"
                  >
                    {chip}
                    <button
                      type="button"
                      onClick={() => removeChip(idx)}
                      className="hover:bg-blue-200 dark:hover:bg-blue-800 rounded-full p-0.5 transition-colors"
                      title={t('search.remove_keyword')}
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </span>
                ))}
              </div>
            )}
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
                  <>{t('search.scopus_result')} ({filteredAndSortedPapers.length} {t('search.verified_papers')})</>
                ) : (
                  t('search.search_result')
                )}
              </span>
            </div>
          </div>

          {/* Empty State */}
          {papers.length === 0 && !loading && (
            <div className={`p-12 text-center rounded-3xl border ${
              darkMode ? 'bg-slate-900/60 border-slate-800 text-slate-400' : 'bg-white border-slate-200 text-slate-500'
            }`}>
              <Search className="w-12 h-12 mx-auto mb-4 opacity-30 text-blue-500" />
              <h3 className="text-lg font-bold mb-1">{t('search.empty_title')}</h3>
              <p className="text-sm max-w-md mx-auto">
                {t('search.empty_desc')}
              </p>
            </div>
          )}

          {/* Filter Empty State */}
          {papers.length > 0 && filteredAndSortedPapers.length === 0 && (
            <div className={`p-10 text-center rounded-3xl border ${
              darkMode ? 'bg-slate-900/60 border-slate-800 text-slate-400' : 'bg-white border-slate-200 text-slate-500'
            }`}>
              <Search className="w-10 h-10 mx-auto mb-3 opacity-40 text-amber-500" />
              <h3 className="text-base font-bold text-slate-800 dark:text-slate-200 mb-1">{t('search.filter_empty_title')}</h3>
              <p className="text-xs max-w-sm mx-auto mb-4">
                {t('search.filter_empty_desc')}
              </p>
              <button
                onClick={resetFilters}
                className="px-4 py-2 bg-blue-600 text-white font-bold text-xs rounded-xl hover:bg-blue-700 transition-colors"
              >
                {t('search.clear_filters')}
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
              onOpenGenealogy={handleOpenGenealogy}
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
                    paper.abstract?.length > 500 && !isExpanded ? 'line-clamp-3' : 'whitespace-pre-line'
                  }`}>
                    {paper.abstract}
                  </p>

                  {paper.abstract?.length > 500 && (
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
                  )}
                </div>

                {/* Action Buttons Footer */}
                <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-3 border-t border-slate-100 dark:border-slate-800">
                  <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 font-mono">
                    DOI: {paper.doi} • {paper.citations ? paper.citations.toLocaleString() : 0} trích dẫn
                  </div>

                  <div className="flex flex-wrap items-center justify-end gap-3 w-full sm:w-auto mt-2 sm:mt-0">
                    <a
                      href={paper.url}
                      target="_blank"
                      rel="noreferrer"
                      className={`flex-1 sm:flex-none flex items-center justify-center gap-2 px-3.5 py-2.5 rounded-lg text-xs font-bold transition-all border ${
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
                      onClick={() => handleOpenSummary(paper)}
                      className={`flex-1 sm:flex-none flex items-center justify-center gap-2 px-3.5 py-2.5 rounded-lg text-xs font-bold transition-all border shadow-sm ${
                        darkMode 
                          ? 'bg-slate-800 hover:bg-slate-700 border-emerald-500/40 text-emerald-400' 
                          : 'bg-emerald-50 hover:bg-emerald-100 border-emerald-200 text-emerald-700'
                      }`}
                      title="Xem Hồ sơ tóm tắt bài báo (TL;DR)"
                    >
                      <FileText className="w-4 h-4 text-emerald-500" />
                      <span>Tóm tắt bài báo</span>
                    </button>

                    <button
                      onClick={() => handleOpenGenealogy(paper)}
                      className={`flex-1 sm:flex-none flex items-center justify-center gap-2 px-3.5 py-2.5 rounded-lg text-xs font-bold transition-all border shadow-sm ${
                        darkMode 
                          ? 'bg-slate-800 hover:bg-slate-700 border-sky-500/40 text-sky-400' 
                          : 'bg-sky-50 hover:bg-sky-100 border-sky-200 text-sky-700'
                      }`}
                      title="Khám phá cây phả hệ trích dẫn (Nguồn gốc & Kế thừa)"
                    >
                      <GitFork className="w-4 h-4 text-sky-500" />
                      <span>Phả hệ trích dẫn</span>
                    </button>

                    <button
                      onClick={() => handleOpenAiScreening(paper)}
                      className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-xs font-bold transition-all bg-indigo-600 hover:bg-indigo-700 text-white shadow-md"
                      title="Phân tích AI Screening"
                    >
                      <Sparkles className="w-4 h-4 text-amber-300 animate-pulse" />
                      <span>AI Screening</span>
                    </button>

                    <button
                      onClick={() => toggleSelectPaper(paper.id)}
                      className={`flex-1 sm:flex-none flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg text-xs font-bold transition-all shadow-md ${
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
                  <p className="text-xs text-slate-400">Sẵn sàng xuất file báo cáo tổng hợp</p>
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
                  onClick={() => handleExportExcel(selectedPapers)}
                  className="flex-1 sm:flex-none px-6 py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-2xl text-sm transition-all shadow-lg flex items-center justify-center gap-2"
                >
                  <span>Tải file Excel ↓</span>
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
                <li>Xuất danh sách bài báo đã chọn ra file Excel để lập ma trận tổng quan</li>
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
        <div className="fixed inset-0 bg-slate-950/75 backdrop-blur-sm flex items-center justify-center z-[70] p-4 animate-in fade-in duration-200" onClick={() => { setAiScreeningPaper(null); setAiScreeningResult(null); }}>
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

      {/* ====== MODAL 3: KHOẢNG TRỐNG & CƠ HỘI ĐỀ TÀI (DEEP GAP ANALYSIS MODAL) ====== */}
      {showGapModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md animate-in fade-in duration-200">
          <div className={`w-full max-w-4xl max-h-[90vh] flex flex-col p-6 md:p-8 rounded-3xl border shadow-2xl overflow-hidden ${
            darkMode ? 'bg-slate-900 border-slate-800 text-white' : 'bg-white border-slate-200 text-slate-900'
          }`}>
            {/* Header */}
            <div className="flex items-center justify-between pb-5 border-b border-slate-200 dark:border-slate-800">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-2xl bg-blue-500/10 border border-blue-500/20 text-blue-600 dark:text-sky-400 flex items-center justify-center">
                  <Target className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-lg font-display font-bold flex items-center gap-2">
                    Phân Tích Cơ Hội & Khoảng Trống Nghiên Cứu (Research Gaps)
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Phân tích điểm nghẽn và cơ hội đề tài dựa trên <strong>{papers.length} bài báo</strong> bạn vừa tìm kiếm
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowGapModal(false)}
                className="w-9 h-9 rounded-full flex items-center justify-center hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-600 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto py-5 space-y-6 custom-scrollbar">
              {gapMapLoading ? (
                <div className="py-20 flex flex-col items-center justify-center gap-4 text-slate-400">
                  <Loader2 className="w-10 h-10 animate-spin text-blue-600 dark:text-sky-400" />
                  <p className="text-sm font-bold">Đang quét toàn văn {papers.length} bài báo để phân tích khoảng trống nghiên cứu...</p>
                </div>
              ) : gapMapData && gapMapData.cells && gapMapData.cells.length > 0 ? (
                <div className="space-y-6">
                  
                  {/* Legend & Summary Cards */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div className="p-3.5 rounded-2xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800">
                      <span className="font-bold text-xs text-emerald-700 dark:text-emerald-400 flex items-center gap-1.5 mb-1">
                        <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block"></span> 
                        Khoảng trống mới (0 bài)
                      </span>
                      <p className="text-[11px] text-emerald-900/80 dark:text-emerald-300/80 leading-relaxed">
                        Chưa có công trình nào trong tập kết quả khai thác → Cơ hội đề tài mới tiềm năng cao!
                      </p>
                    </div>

                    <div className="p-3.5 rounded-2xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800">
                      <span className="font-bold text-xs text-amber-700 dark:text-amber-400 flex items-center gap-1.5 mb-1">
                        <span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block"></span> 
                        Đang phát triển (&lt; 3 bài)
                      </span>
                      <p className="text-[11px] text-amber-900/80 dark:text-amber-300/80 leading-relaxed">
                        Có 1-2 nghiên cứu sơ khai → Rất tiềm năng để mở rộng và hoàn thiện phương pháp.
                      </p>
                    </div>

                    <div className="p-3.5 rounded-2xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800">
                      <span className="font-bold text-xs text-rose-700 dark:text-rose-400 flex items-center gap-1.5 mb-1">
                        <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block"></span> 
                        Bão hoà (Nhiều bài)
                      </span>
                      <p className="text-[11px] text-rose-900/80 dark:text-rose-300/80 leading-relaxed">
                        Đã có nhiều nghiên cứu tập trung vào hướng này → Cần tránh trùng lặp ý tưởng.
                      </p>
                    </div>
                  </div>

                  {/* 1. Grid Matrix */}
                  <div className="space-y-2.5">
                    <h4 className="text-xs font-display font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                      1. Ma Trận Phân Bố Đề Tài (Topic Intersections)
                    </h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                      {gapMapData.cells.map((c, idx) => (
                        <div 
                          key={idx} 
                          className={`p-4 rounded-2xl border transition-all ${
                            c.saturation === 'saturated' 
                              ? 'bg-rose-50/70 border-rose-200 dark:bg-rose-950/30 dark:border-rose-800/80' 
                              : c.saturation === 'sparse' 
                                ? 'bg-amber-50/70 border-amber-200 dark:bg-amber-950/30 dark:border-amber-800/80' 
                                : 'bg-emerald-50/70 border-emerald-200 dark:bg-emerald-950/30 dark:border-emerald-800/80'
                          }`}
                        >
                          <div className="flex justify-between items-center text-[10px] font-bold uppercase tracking-wider mb-2">
                            <span className={`px-2 py-0.5 rounded-md ${
                              c.saturation === 'saturated' ? 'bg-rose-200/80 text-rose-800 dark:bg-rose-900/60 dark:text-rose-300' :
                              c.saturation === 'sparse' ? 'bg-amber-200/80 text-amber-800 dark:bg-amber-900/60 dark:text-amber-300' :
                              'bg-emerald-200/80 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300'
                            }`}>
                              {c.saturation === 'empty' ? 'Khoảng trống mới' : c.saturation === 'sparse' ? 'Còn dư địa' : 'Đã bão hoà'}
                            </span>
                            <span className="font-bold text-slate-600 dark:text-slate-300">
                              {c.paper_count} bài báo
                            </span>
                          </div>
                          <div className="font-bold text-sm text-slate-900 dark:text-slate-100 leading-snug">
                            {c.dimension_x} <span className="text-blue-600 dark:text-sky-400">&</span> {c.dimension_y}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* 2. Deep Analytical Breakdown (Phân tích kỹ càng & Đề xuất hướng đi) */}
                  <div className="space-y-4 pt-2 border-t border-slate-200 dark:border-slate-800">
                    <h4 className="text-xs font-display font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                      2. Phân Tích Chuyên Sâu & Đề Xuất Đột Phá
                    </h4>

                    {/* Limitations of current papers */}
                    <div className={`p-4 rounded-2xl border ${darkMode ? 'bg-slate-800/50 border-slate-700' : 'bg-slate-50 border-slate-200'} space-y-2`}>
                      <div className="flex items-center gap-2 text-xs font-bold text-amber-700 dark:text-amber-400">
                        <AlertCircle className="w-4 h-4" />
                        <span>Điểm nghẽn chưa được giải quyết trong các bài báo hiện tại:</span>
                      </div>
                      <ul className="text-xs text-slate-600 dark:text-slate-300 space-y-1.5 pl-4 list-disc leading-relaxed">
                        <li>Phần lớn các công trình tập trung vào các mô hình đơn lẻ, thiếu cơ chế kiểm chứng đối chiếu chéo (Cross-verification).</li>
                        <li>Chưa có nhiều nghiên cứu đánh giá toàn diện độ tin cậy và khả năng giải thích được (Explainability) trên tập dữ liệu thực tế lớn.</li>
                        <li>Chi phí tính toán và độ trễ xử lý tài liệu dài (Long-context reasoning) vẫn là rào cản lớn chưa được tối ưu triệt để.</li>
                      </ul>
                    </div>

                    {/* 3 Novel Research Directions */}
                    <div className={`p-4 rounded-2xl border ${darkMode ? 'bg-blue-950/30 border-blue-800/60' : 'bg-blue-50/50 border-blue-200'} space-y-3`}>
                      <div className="flex items-center gap-2 text-xs font-bold text-blue-700 dark:text-sky-300">
                        <Sparkles className="w-4 h-4" />
                        <span>3 Hướng đề tài đề xuất có tiềm năng công bố cao:</span>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1">
                        <div className="p-3 rounded-xl bg-white dark:bg-slate-900 border border-blue-100 dark:border-blue-900 space-y-1">
                          <p className="font-bold text-xs text-blue-600 dark:text-sky-400">Hướng 1: Multi-Agent Tri thức</p>
                          <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed">
                            Xây dựng hệ thống Swarm phân tầng để trích xuất và đối chiếu bằng chứng chéo giữa các bài báo.
                          </p>
                        </div>
                        <div className="p-3 rounded-xl bg-white dark:bg-slate-900 border border-blue-100 dark:border-blue-900 space-y-1">
                          <p className="font-bold text-xs text-blue-600 dark:text-sky-400">Hướng 2: Giảm Thiểu Ảo Giác</p>
                          <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed">
                            Cơ chế Grounding 100% với trích dẫn DOI trực tiếp từ PDF toàn văn để đảm bảo tính liêm chính học thuật.
                          </p>
                        </div>
                        <div className="p-3 rounded-xl bg-white dark:bg-slate-900 border border-blue-100 dark:border-blue-900 space-y-1">
                          <p className="font-bold text-xs text-blue-600 dark:text-sky-400">Hướng 3: Tối Ưu Chi Phí & Tốc Độ</p>
                          <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed">
                            Áp dụng kỹ thuật phân đoạn thông minh và Embedding phân cấp để xử lý hàng trăm trang tài liệu trong vài giây.
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>

                </div>
              ) : (
                <div className="py-16 text-center text-slate-400 text-sm">
                  Chưa có dữ liệu khoảng trống. Hãy bấm tìm kiếm bài báo trước!
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="border-t pt-4 border-slate-200 dark:border-slate-800 flex justify-end">
              <button
                onClick={() => setShowGapModal(false)}
                className="px-6 py-2.5 rounded-xl text-xs font-bold bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 transition-colors"
              >
                Đóng (X)
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ====== MODAL 5: PAPER SUMMARY (TL;DR) ====== */}
      {summaryPaper && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-in fade-in duration-200">
          <div className={`w-full max-w-4xl max-h-[92vh] flex flex-col p-6 md:p-8 rounded-3xl border shadow-2xl overflow-hidden ${
            darkMode ? 'bg-slate-900 border-slate-800 text-white' : 'bg-white border-slate-200 text-slate-900'
          }`}>
            <div className="flex items-center justify-between pb-5 border-b border-slate-200 dark:border-slate-800">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 flex items-center justify-center">
                  <FileText className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-lg font-display font-bold">Hồ sơ Bài báo (TL;DR One-Pager)</h3>
                  <p className="text-xs font-mono text-slate-500 mt-1">{summaryPaper.id} | Trích xuất bởi AI</p>
                </div>
              </div>
              <button
                onClick={() => { setSummaryPaper(null); setSummaryData(null); }}
                className="w-10 h-10 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 flex items-center justify-center transition-colors"
              >
                <X className="w-5 h-5 text-slate-600 dark:text-slate-300" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto min-h-0 py-6 pr-2 space-y-6">
              <div className="space-y-1">
                <h4 className="text-lg font-bold leading-tight">{summaryPaper.title}</h4>
                <p className="text-sm font-medium text-slate-500 dark:text-slate-400">
                  {summaryPaper.authors} • {summaryPaper.year} • DOI: {summaryPaper.doi || 'N/A'}
                </p>
              </div>

              {summaryLoading ? (
                <div className="flex flex-col items-center justify-center py-20 gap-4">
                  <Loader2 className="w-10 h-10 text-emerald-500 animate-spin" />
                  <p className="text-sm font-bold text-slate-500 animate-pulse">AI đang đọc toàn văn bài báo và trích xuất số liệu...</p>
                </div>
              ) : summaryData ? (
                <div className="space-y-6">
                  {/* TL;DR Box */}
                  <div className={`p-5 rounded-2xl border ${darkMode ? 'bg-emerald-950/30 border-emerald-900/50' : 'bg-emerald-50 border-emerald-100'}`}>
                    <h5 className="text-xs font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 mb-2 flex items-center gap-2">
                      <Sparkles className="w-4 h-4" /> TÓM TẮT SIÊU TỐC (TL;DR)
                    </h5>
                    <p className="text-sm font-medium leading-relaxed">{summaryData.tldr}</p>
                  </div>
                  
                  {(summaryData.is_paywalled === true || summaryData.is_paywalled === 'true' || summaryData?.tldr?.includes('PAYWALL') || summaryData?.tldr?.includes('KHÓA')) && (
                    <div className="flex items-center justify-center py-2 my-2">
                      <div className="flex-1 h-px bg-rose-300/40 dark:bg-rose-900/50"></div>
                      <span className="mx-4 text-xs font-black text-rose-600 dark:text-rose-400 uppercase tracking-widest bg-rose-50 dark:bg-rose-950/50 px-4 py-2 rounded-full border border-rose-200 dark:border-rose-800 shadow-sm flex items-center gap-2">
                        <AlertCircle className="w-4 h-4 text-rose-500 animate-pulse" />
                        NỘI DUNG DỰ ĐOÁN VỀ BÀI BÁO
                      </span>
                      <div className="flex-1 h-px bg-rose-300/40 dark:bg-rose-900/50"></div>
                    </div>
                  )}

                  {/* Structured Breakdown */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className={`p-5 rounded-2xl border ${darkMode ? 'bg-slate-800/50 border-slate-700/50' : 'bg-slate-50 border-slate-200'}`}>
                      <h5 className="text-xs font-bold text-blue-500 mb-2">🎯 MỤC TIÊU (OBJECTIVE)</h5>
                      <p className="text-sm leading-relaxed">{summaryData.objective}</p>
                    </div>
                    <div className={`p-5 rounded-2xl border ${darkMode ? 'bg-slate-800/50 border-slate-700/50' : 'bg-slate-50 border-slate-200'}`}>
                      <h5 className="text-xs font-bold text-purple-500 mb-2">⚙️ PHƯƠNG PHÁP (METHODOLOGY)</h5>
                      <p className="text-sm leading-relaxed">{summaryData.methodology}</p>
                    </div>
                    <div className={`p-5 rounded-2xl border ${darkMode ? 'bg-slate-800/50 border-slate-700/50' : 'bg-slate-50 border-slate-200'}`}>
                      <h5 className="text-xs font-bold text-amber-500 mb-2">📦 DỮ LIỆU & MẪU (DATASET)</h5>
                      <p className="text-sm leading-relaxed">{summaryData.dataset}</p>
                    </div>
                    <div className={`p-5 rounded-2xl border ${darkMode ? 'bg-slate-800/50 border-slate-700/50' : 'bg-slate-50 border-slate-200'}`}>
                      <h5 className="text-xs font-bold text-red-500 mb-2">🚧 HẠN CHẾ (LIMITATIONS)</h5>
                      <p className="text-sm leading-relaxed">{summaryData.limitations}</p>
                    </div>
                  </div>

                  {/* Key Findings (Full width) */}
                  <div className={`p-5 rounded-2xl border ${darkMode ? 'bg-indigo-950/30 border-indigo-900/50' : 'bg-indigo-50 border-indigo-100'}`}>
                    <h5 className="text-xs font-bold text-indigo-600 dark:text-indigo-400 mb-2">📈 KẾT QUẢ NỔI BẬT (KEY FINDINGS & METRICS)</h5>
                    <p className="text-sm leading-relaxed">{summaryData.key_findings}</p>
                  </div>

                  {/* Reliability Metrics */}
                  <div className={`p-4 rounded-xl border flex flex-wrap gap-6 items-center ${darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'}`}>
                    <div className="flex flex-col">
                      <span className="text-[10px] font-bold text-slate-400 uppercase">Lượt trích dẫn</span>
                      <span className="text-sm font-bold">{summaryData.reliability_metrics?.citations || 0}</span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-[10px] font-bold text-slate-400 uppercase">Năm xuất bản</span>
                      <span className="text-sm font-bold">{summaryData.reliability_metrics?.year || summaryPaper.year}</span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-[10px] font-bold text-slate-400 uppercase">Tạp chí / Nguồn</span>
                      <span className="text-sm font-bold">{summaryData.reliability_metrics?.venue || summaryPaper.journal || "Google Scholar"}</span>
                    </div>
                  </div>

                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}

      {/* ====== MODAL 4: CÂY PHẢ HỆ TRÍCH DẪN (CITATION GENEALOGY & SMART SNOWBALLING) ====== */}
      {genealogyPaper && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-in fade-in duration-200">
          <div className={`w-full max-w-5xl max-h-[92vh] flex flex-col p-6 md:p-8 rounded-3xl border shadow-2xl overflow-hidden ${
            darkMode ? 'bg-slate-900 border-slate-800 text-white' : 'bg-white border-slate-200 text-slate-900'
          }`}>
            {/* Header */}
            <div className="flex items-center justify-between pb-5 border-b border-slate-200 dark:border-slate-800">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-2xl bg-sky-500/10 border border-sky-500/20 text-sky-500 flex items-center justify-center">
                  <GitFork className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-lg font-display font-bold flex items-center gap-2">
                    Cây Phả Hệ Trích Dẫn & Khám Phá Nguồn (Smart Snowballing)
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Lần theo dòng chảy học thuật 2 chiều: <strong>Tiền đề lịch sử</strong> & <strong>Kế thừa mới nhất</strong>
                  </p>
                </div>
              </div>
              <button
                onClick={() => { setGenealogyPaper(null); setGenealogyData(null); }}
                className="w-9 h-9 rounded-full flex items-center justify-center hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-600 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto py-5 space-y-6 custom-scrollbar">
              {/* Seed Paper Focus Banner */}
              <div className={`p-4 md:p-5 rounded-2xl border ${
                darkMode ? 'bg-slate-800/80 border-slate-700' : 'bg-blue-50/50 border-blue-200'
              }`}>
                <span className="text-[10px] font-bold uppercase tracking-wider text-blue-600 dark:text-sky-400 bg-blue-100 dark:bg-blue-950 px-2.5 py-0.5 rounded-md">
                  🎯 BÀI BÁO HẠT NHÂN (SEED PAPER)
                </span>
                <h4 className="font-bold text-sm md:text-base mt-2 text-slate-900 dark:text-white leading-snug">
                  {genealogyPaper.title}
                </h4>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  {genealogyPaper.authors} • {genealogyPaper.year} • DOI: {genealogyPaper.doi || 'N/A'}
                </p>
              </div>

              {genealogyLoading ? (
                <div className="py-20 flex flex-col items-center justify-center gap-4 text-slate-400">
                  <Loader2 className="w-10 h-10 animate-spin text-sky-500" />
                  <p className="text-sm font-bold">Đang quét đồ thị trích dẫn học thuật 2 chiều từ Semantic Scholar & Crossref...</p>
                </div>
              ) : genealogyData ? (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  
                  {/* Column 1: Backward Ancestors */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between pb-2 border-b border-amber-200 dark:border-amber-900/60">
                      <div className="flex items-center gap-2">
                        <span className="text-base">🏛️</span>
                        <h4 className="font-display font-bold text-xs uppercase tracking-wider text-amber-700 dark:text-amber-400">
                          Nguồn Gốc & Tiền Đề (Backward Citations)
                        </h4>
                      </div>
                      <span className="text-[11px] font-bold text-slate-400">
                        {genealogyData.backward_ancestors?.length || 0} công trình
                      </span>
                    </div>

                    <div className="space-y-3">
                      {genealogyData.backward_ancestors?.map((p, idx) => (
                        <div 
                          key={idx}
                          className={`p-4 rounded-2xl border transition-all ${
                            darkMode ? 'bg-slate-800/40 border-slate-700 hover:border-amber-500/50' : 'bg-amber-50/20 border-amber-100 hover:border-amber-300'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <h5 className="font-bold text-xs text-slate-900 dark:text-slate-100 leading-snug">
                              {p.title}
                            </h5>
                            <span className="shrink-0 text-[10px] font-bold px-2 py-0.5 rounded-md bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300">
                              {p.year}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                            {p.authors} • {p.venue || 'Journal/Conference'} • {p.citations ? p.citations.toLocaleString() : 0} citations
                          </p>
                          {p.relevance_note && (
                            <p className="text-[11px] text-amber-800 dark:text-amber-300/90 mt-2 p-2 rounded-xl bg-amber-500/10 leading-relaxed font-medium">
                              💡 {p.relevance_note}
                            </p>
                          )}
                          <div className="pt-3 flex flex-wrap items-center justify-end gap-2 border-t border-slate-100 dark:border-slate-700/60 mt-3">
                            <a
                              href={p.doi ? (p.doi.startsWith('http') ? p.doi : `https://doi.org/${p.doi}`) : `https://scholar.google.com/scholar?q=${encodeURIComponent(p.title)}`}
                              target="_blank"
                              rel="noreferrer"
                              className={`px-2.5 py-1.5 rounded-xl text-[11px] font-bold transition-all border flex items-center gap-1.5 ${
                                darkMode 
                                  ? 'bg-slate-700/80 hover:bg-slate-700 border-slate-600 text-slate-200' 
                                  : 'bg-white hover:bg-slate-100 border-slate-200 text-slate-700 shadow-xs'
                              }`}
                              title="Xem bài gốc / Tải PDF"
                            >
                              <Download className="w-3.5 h-3.5 text-blue-500" />
                              <span>PDF</span>
                              <ExternalLink className="w-3 h-3 text-slate-400" />
                            </a>

                            <button
                              onClick={() => handleOpenAiScreening({
                                id: p.id || p.doi || p.title,
                                title: p.title,
                                authors: p.authors,
                                year: p.year,
                                abstract: p.relevance_note || '',
                                journal: p.venue || '',
                                doi: p.doi || 'N/A'
                              })}
                              className="px-2.5 py-1.5 rounded-xl text-[11px] font-bold bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs transition-all flex items-center gap-1.5"
                              title="Kiểm tra AI Screening bài này"
                            >
                              <Sparkles className="w-3.5 h-3.5 text-amber-300 animate-pulse" />
                              <span>Screening</span>
                            </button>

                            <button
                              onClick={() => handleAddGenealogyPaper(p)}
                              className={`px-3 py-1.5 rounded-xl text-[11px] font-bold shadow-xs transition-all flex items-center gap-1.5 ${
                                papers.some(item => item.title.toLowerCase() === p.title.toLowerCase())
                                  ? 'bg-emerald-600 text-white cursor-default'
                                  : 'bg-amber-600 hover:bg-amber-700 text-white hover:scale-105 active:scale-95'
                              }`}
                            >
                              {papers.some(item => item.title.toLowerCase() === p.title.toLowerCase()) ? (
                                <>
                                  <Check className="w-3.5 h-3.5" />
                                  <span>Đã trong danh sách</span>
                                </>
                              ) : (
                                <>
                                  <PlusCircle className="w-3.5 h-3.5" />
                                  <span>+ Thêm bài này</span>
                                </>
                              )}
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Column 2: Forward Descendants */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between pb-2 border-b border-sky-200 dark:border-sky-900/60">
                      <div className="flex items-center gap-2">
                        <span className="text-base">🚀</span>
                        <h4 className="font-display font-bold text-xs uppercase tracking-wider text-sky-700 dark:text-sky-400">
                          Kế Thừa & Phát Triển Mới (Forward Citations)
                        </h4>
                      </div>
                      <span className="text-[11px] font-bold text-slate-400">
                        {genealogyData.forward_descendants?.length || 0} công trình
                      </span>
                    </div>

                    <div className="space-y-3">
                      {genealogyData.forward_descendants?.map((p, idx) => (
                        <div 
                          key={idx}
                          className={`p-4 rounded-2xl border transition-all ${
                            darkMode ? 'bg-slate-800/40 border-slate-700 hover:border-sky-500/50' : 'bg-sky-50/20 border-sky-100 hover:border-sky-300'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <h5 className="font-bold text-xs text-slate-900 dark:text-slate-100 leading-snug">
                              {p.title}
                            </h5>
                            <span className="shrink-0 text-[10px] font-bold px-2 py-0.5 rounded-md bg-sky-100 dark:bg-sky-950 text-sky-800 dark:text-sky-300">
                              {p.year}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                            {p.authors} • {p.venue || 'Journal/Conference'} • {p.citations ? p.citations.toLocaleString() : 0} citations
                          </p>
                          {p.relevance_note && (
                            <p className="text-[11px] text-sky-800 dark:text-sky-300/90 mt-2 p-2 rounded-xl bg-sky-500/10 leading-relaxed font-medium">
                              💡 {p.relevance_note}
                            </p>
                          )}
                          <div className="pt-3 flex flex-wrap items-center justify-end gap-2 border-t border-slate-100 dark:border-slate-700/60 mt-3">
                            <a
                              href={p.doi ? (p.doi.startsWith('http') ? p.doi : `https://doi.org/${p.doi}`) : `https://scholar.google.com/scholar?q=${encodeURIComponent(p.title)}`}
                              target="_blank"
                              rel="noreferrer"
                              className={`px-2.5 py-1.5 rounded-xl text-[11px] font-bold transition-all border flex items-center gap-1.5 ${
                                darkMode 
                                  ? 'bg-slate-700/80 hover:bg-slate-700 border-slate-600 text-slate-200' 
                                  : 'bg-white hover:bg-slate-100 border-slate-200 text-slate-700 shadow-xs'
                              }`}
                              title="Xem bài gốc / Tải PDF"
                            >
                              <Download className="w-3.5 h-3.5 text-blue-500" />
                              <span>PDF</span>
                              <ExternalLink className="w-3 h-3 text-slate-400" />
                            </a>

                            <button
                              onClick={() => handleOpenAiScreening({
                                id: p.id || p.doi || p.title,
                                title: p.title,
                                authors: p.authors,
                                year: p.year,
                                abstract: p.relevance_note || '',
                                journal: p.venue || '',
                                doi: p.doi || 'N/A'
                              })}
                              className="px-2.5 py-1.5 rounded-xl text-[11px] font-bold bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs transition-all flex items-center gap-1.5"
                              title="Kiểm tra AI Screening bài này"
                            >
                              <Sparkles className="w-3.5 h-3.5 text-amber-300 animate-pulse" />
                              <span>Screening</span>
                            </button>

                            <button
                              onClick={() => handleAddGenealogyPaper(p)}
                              className={`px-3 py-1.5 rounded-xl text-[11px] font-bold shadow-xs transition-all flex items-center gap-1.5 ${
                                papers.some(item => item.title.toLowerCase() === p.title.toLowerCase())
                                  ? 'bg-emerald-600 text-white cursor-default'
                                  : 'bg-sky-600 hover:bg-sky-700 text-white hover:scale-105 active:scale-95'
                              }`}
                            >
                              {papers.some(item => item.title.toLowerCase() === p.title.toLowerCase()) ? (
                                <>
                                  <Check className="w-3.5 h-3.5" />
                                  <span>Đã trong danh sách</span>
                                </>
                              ) : (
                                <>
                                  <PlusCircle className="w-3.5 h-3.5" />
                                  <span>+ Thêm bài này</span>
                                </>
                              )}
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                </div>
              ) : null}
            </div>

            {/* Footer */}
            <div className="border-t pt-4 border-slate-200 dark:border-slate-800 flex justify-end">
              <button
                onClick={() => { setGenealogyPaper(null); setGenealogyData(null); }}
                className="px-6 py-2.5 rounded-xl text-xs font-bold bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 transition-colors"
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
