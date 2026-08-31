import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { 
  Search, Download, ExternalLink, Plus, PlusCircle, CheckCircle2, Key, Loader2, AlertCircle, 
  ChevronDown, ChevronUp, ShieldCheck, ShieldAlert, Activity, Check, X, HelpCircle,
  BookOpen, Sparkles, Trash2, Target, GitFork, FileText, ArrowRight, Code
} from 'lucide-react';
import SearchHistoryPanel from './SearchHistoryPanel';
import FilterSortBar from './FilterSortBar';
import PaperTable from './PaperTable';
import { 
  downloadClientBibTeX, 
  downloadClientCSV, 
  downloadClientMarkdown, 
  downloadClientJSON 
} from '../../utils/exportUtils';
import { useLanguage } from '../../contexts/LanguageContext';
import { useProject } from '../../contexts/ProjectContext';
import { API_BASE, safeFetch } from '../../utils/apiConfig';
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

export default function SearchTab({ papers, setPapers, selectedPaperIds, selectedPapers = [], toggleSelectPaper, clearSelectedPapers, setActiveTab, workspacePapers = [], setWorkspacePapers, darkMode }) {
  const { t, language } = useLanguage();
  const isVi = language === 'vi';
  const { activeProject, activeProjectId } = useProject();
  const currentProjectId = activeProjectId || activeProject?.id || DEFAULT_PROJECT_ID;

  const [apiKey, setApiKey] = useState(() => {
    return localStorage.getItem('litreview_serpapi_key') || localStorage.getItem('serp_api_key') || '';
  });
  // The input for this was dropped from the UI during the branding/layout
  // overhaul while apiKey/handleApiKeyChange (and the X-API-Key header this
  // feeds) stayed wired up -- there was no way left to actually set or
  // change a SerpApi key. Collapsed by default so it doesn't clutter the
  // main search bar for users who don't need it.
  const [showApiKeyInput, setShowApiKeyInput] = useState(false);

  // Helper: Trích xuất và chuẩn hóa từ khóa học thuật chuẩn xác (tránh bị dính nguyên cả câu văn dài)
  const extractCleanKeywordsFromText = (text = '') => {
    if (!text || typeof text !== 'string') return [];
    const extracted = [];

    // 1. Trích xuất các thuật toán/từ viết tắt trong ngoặc đơn e.g. (Newton, BFGS)
    const parenMatches = text.match(/\(([^)]+)\)/g) || [];
    parenMatches.forEach(pm => {
      const inside = pm.replace(/[()]/g, '');
      inside.split(',').forEach(item => {
        const cleaned = item.trim();
        if (cleaned && cleaned.length >= 2 && cleaned.length <= 35) {
          extracted.push(cleaned.split(/\s+/).length === 1 ? `${cleaned} algorithm` : cleaned);
        }
      });
    });

    const cleanText = text.replace(/\([^)]*\)/g, '');
    const mappings = [
      { vi: 'tốc độ hội tụ', en: ['convergence rate', 'rate of convergence'] },
      { vi: 'tối ưu bậc hai', en: ['second-order optimization', 'second-order algorithms'] },
      { vi: 'tối ưu hóa', en: ['optimization methods', 'mathematical optimization'] },
      { vi: 'tối thiểu hóa', en: ['convex minimization', 'objective minimization'] },
      { vi: 'hàm lồi', en: ['convex function', 'convex optimization'] },
      { vi: 'ràng buộc lồi', en: ['convex constraints', 'constrained optimization'] },
      { vi: 'chấp nhận tách', en: ['split feasibility problem', 'split feasibility'] },
      { vi: 'học sâu', en: ['deep learning', 'neural networks'] },
      { vi: 'mô hình ngôn ngữ', en: ['large language models', 'LLM task planning'] },
      { vi: 'robot', en: ['robotics', 'mobile robot navigation'] },
    ];

    const cleanLower = cleanText.toLowerCase();
    mappings.forEach(m => {
      if (cleanLower.includes(m.vi)) {
        extracted.push(...m.en);
      }
    });

    // Trích xuất cụm danh từ ngắn
    const delimiters = /[;:,]|cho bài toán|đối với|của các|dành cho|dựa trên|phân tích|nghiên cứu|đánh giá|khảo sát/i;
    const chunks = cleanText.split(delimiters);
    chunks.forEach(c => {
      const cClean = c.trim();
      const words = cClean.split(/\s+/);
      if (words.length >= 2 && words.length <= 5 && cClean.length <= 40) {
        extracted.push(cClean);
      }
    });

    const seen = new Set();
    const result = [];
    extracted.forEach(item => {
      const k = item.trim();
      if (k && !seen.has(k.toLowerCase()) && k.length <= 45 && k.split(/\s+/).length <= 5) {
        seen.add(k.toLowerCase());
        result.push(k);
      }
    });

    return result.slice(0, 8);
  };

  const filterEnglishKeywords = (arr) => {
    if (!Array.isArray(arr)) return [];
    const results = [];
    const seen = new Set();

    arr.forEach(kw => {
      if (!kw || typeof kw !== 'string') return;
      const k = kw.trim();
      if (k.length < 2) return;

      // Nếu từ khóa quá dài (> 45 ký tự hoặc > 5 từ), tự động bóc tách thành các từ khóa ngắn
      if (k.length > 45 || k.split(/\s+/).length > 5) {
        const subKws = extractCleanKeywordsFromText(k);
        subKws.forEach(sk => {
          if (!seen.has(sk.toLowerCase())) {
            seen.add(sk.toLowerCase());
            results.push(sk);
          }
        });
      } else {
        if (!seen.has(k.toLowerCase())) {
          seen.add(k.toLowerCase());
          results.push(k);
        }
      }
    });

    return results;
  };

  const getProjectKeywords = useCallback(() => {
    try {
      const pId = currentProjectId;
      const cachedKw = localStorage.getItem(`suggested_keywords_${pId}`);
      if (cachedKw) {
        const arr = JSON.parse(cachedKw);
        const filtered = filterEnglishKeywords(arr);
        if (filtered.length > 0) return filtered;
      }
      const cachedPico = localStorage.getItem(`slr_pico_data_${pId}`) || localStorage.getItem('slr_pico_data');
      if (cachedPico) {
        const p = typeof cachedPico === 'string' ? JSON.parse(cachedPico) : cachedPico;
        const filtered = filterEnglishKeywords(p.search_keywords);
        if (filtered.length > 0) return filtered;
      }
      if (activeProject?.pico?.search_keywords) {
        const filtered = filterEnglishKeywords(activeProject.pico.search_keywords);
        if (filtered.length > 0) return filtered;
      }
      const raw = localStorage.getItem('suggested_keywords');
      if (raw) {
        const arr = JSON.parse(raw);
        const filtered = filterEnglishKeywords(arr);
        if (filtered.length > 0) return filtered;
      }

      // Tự động trích xuất từ tên đề tài & câu hỏi nghiên cứu của project nếu chưa có PICO
      const autoExtracted = [
        ...extractCleanKeywordsFromText(activeProject?.name || ''),
        ...extractCleanKeywordsFromText(activeProject?.research_question || '')
      ];
      const filteredAuto = filterEnglishKeywords(autoExtracted);
      if (filteredAuto.length > 0) return filteredAuto;

    } catch (e) {}
    return [];
  }, [currentProjectId, activeProject]);

  const [suggestedKeywords, setSuggestedKeywords] = useState(() => getProjectKeywords());
  
  const [selectedKeywords, setSelectedKeywords] = useState(() => {
    try {
      const cached = localStorage.getItem(`litreview_selected_keywords_${currentProjectId}`);
      if (cached) {
        const parsed = JSON.parse(cached);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
    } catch {}
    const kws = getProjectKeywords();
    return kws.length > 0 ? kws : [];
  });

  const [searchQuery, setSearchQuery] = useState('');

  // Sync keywords and restore cached search papers when activeProject or currentProjectId changes
  useEffect(() => {
    const kws = getProjectKeywords();
    setSuggestedKeywords(kws);
    
    // Restore or initialize selectedKeywords
    try {
      const cachedSelected = localStorage.getItem(`litreview_selected_keywords_${currentProjectId}`);
      if (cachedSelected) {
        const parsed = JSON.parse(cachedSelected);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setSelectedKeywords(parsed);
        } else {
          setSelectedKeywords(kws);
        }
      } else {
        setSelectedKeywords(kws);
      }
    } catch {
      setSelectedKeywords(kws);
    }

    // Restore cached papers for this project if available
    try {
      const cachedPapers = localStorage.getItem(`litreview_search_papers_${currentProjectId}`);
      if (cachedPapers) {
        const parsed = JSON.parse(cachedPapers);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setPapers(parsed);
          const cachedMeta = localStorage.getItem(`litreview_search_meta_${currentProjectId}`);
          if (cachedMeta) setSearchMeta(JSON.parse(cachedMeta));
        }
      }
      const cachedGap = localStorage.getItem(`slr_gap_map_${currentProjectId}`);
      if (cachedGap) setGapMapData(JSON.parse(cachedGap));
    } catch {}
  }, [currentProjectId, activeProject, getProjectKeywords, setPapers]);

  // Lắng nghe sự kiện chuyển từ Tab Cấu hình sang
  useEffect(() => {
    const handleMeshQuery = () => {
      const kws = getProjectKeywords();
      if (kws.length > 0) {
        setSuggestedKeywords(kws);
        setSelectedKeywords(kws);
        localStorage.setItem(`litreview_selected_keywords_${currentProjectId}`, JSON.stringify(kws));
      }
    };
    window.addEventListener('new_mesh_query_ready', handleMeshQuery);
    return () => window.removeEventListener('new_mesh_query_ready', handleMeshQuery);
  }, [currentProjectId, getProjectKeywords]);

  const toggleKeyword = (kw) => {
    let updated;
    if (selectedKeywords.includes(kw)) {
      updated = selectedKeywords.filter(k => k !== kw);
    } else {
      updated = [...selectedKeywords, kw];
    }
    setSelectedKeywords(updated);
    localStorage.setItem(`litreview_selected_keywords_${currentProjectId}`, JSON.stringify(updated));
  };

  const removeSelectedKeyword = (idx) => {
    const updated = selectedKeywords.filter((_, i) => i !== idx);
    setSelectedKeywords(updated);
    localStorage.setItem(`litreview_selected_keywords_${currentProjectId}`, JSON.stringify(updated));
  };

  const handleAddCustomKeyword = (e) => {
    if (e) e.preventDefault();
    const trimmed = searchQuery.trim();
    if (!trimmed) return;
    if (!selectedKeywords.includes(trimmed)) {
      const updated = [...selectedKeywords, trimmed];
      setSelectedKeywords(updated);
      localStorage.setItem(`litreview_selected_keywords_${currentProjectId}`, JSON.stringify(updated));
    }
    setSearchQuery('');
  };

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
      const cached = localStorage.getItem(`research_setup_data_${currentProjectId}`) || localStorage.getItem('research_setup_data');
      if (cached) return JSON.parse(cached);
    } catch (e) {
      console.error(e);
    }
    return activeProject || null;
  });
  const [showScreeningModal, setShowScreeningModal] = useState(false);

  // Single paper AI Screening modal state
  const [aiScreeningPaper, setAiScreeningPaper] = useState(null);
  const [aiScreeningResult, setAiScreeningResult] = useState(null);
  const [aiScreeningLoading, setAiScreeningLoading] = useState(false);

  // Gap Map Modal state for Search Tab
  const [showGapModal, setShowGapModal] = useState(false);
  const [gapMapLoading, setGapMapLoading] = useState(false);
  const [gapMapData, setGapMapData] = useState(() => {
    try {
      const cachedGap = localStorage.getItem(`slr_gap_map_${currentProjectId}`);
      if (cachedGap) return JSON.parse(cachedGap);
    } catch {}
    return null;
  });

  const [selectedGapCell, setSelectedGapCell] = useState(null);

  // In-Context Export state & notification
  const [exportMenuOpen, setExportMenuOpen] = useState(false);
  const [searchToast, setSearchToast] = useState(null);
  const showSearchToast = (msg) => {
    setSearchToast(msg);
    setTimeout(() => setSearchToast(null), 3000);
  };

  const handleExportSelectedBibTeX = (targetList = null) => {
    const list = targetList || (selectedPapers.length > 0 ? selectedPapers : papers);
    if (!list || list.length === 0) return;
    downloadClientBibTeX(list, `${(activeProject?.name || 'literature').replace(/\s+/g, '_')}_citations.bib`);
    showSearchToast(isVi ? `Đã xuất ${list.length} bài báo sang BibTeX (.bib)!` : `Exported ${list.length} papers to BibTeX (.bib)!`);
  };

  const handleExportSelectedCSV = (targetList = null) => {
    const list = targetList || (selectedPapers.length > 0 ? selectedPapers : papers);
    if (!list || list.length === 0) return;
    downloadClientCSV(list, true, `${(activeProject?.name || 'literature').replace(/\s+/g, '_')}_papers.csv`);
    showSearchToast(isVi ? `Đã xuất ${list.length} bài báo sang Excel/CSV!` : `Exported ${list.length} papers to Excel/CSV!`);
  };

  const handleExportSelectedMarkdown = (targetList = null) => {
    const list = targetList || (selectedPapers.length > 0 ? selectedPapers : papers);
    if (!list || list.length === 0) return;
    downloadClientMarkdown(list, activeProject || {}, '', `${(activeProject?.name || 'literature').replace(/\s+/g, '_')}_summary.md`);
    showSearchToast(isVi ? `Đã xuất ${list.length} bài báo sang Markdown (.md)!` : `Exported ${list.length} papers to Markdown (.md)!`);
  };

  const handleExportSelectedJSON = (targetList = null) => {
    const list = targetList || (selectedPapers.length > 0 ? selectedPapers : papers);
    if (!list || list.length === 0) return;
    downloadClientJSON(list, activeProject || {}, '', `${(activeProject?.name || 'literature').replace(/\s+/g, '_')}_dataset.json`);
    showSearchToast(isVi ? `Đã xuất ${list.length} bài báo sang JSON (.json)!` : `Exported ${list.length} papers to JSON (.json)!`);
  };

  const handleExportExcel = () => {
    handleExportSelectedCSV(filteredAndSortedPapers);
  };

  const handleOpenGapAnalysis = async () => {
    setShowGapModal(true);
    setGapMapLoading(true);
    try {
      const idea = projectData?.research_question || projectData?.name || activeProject?.research_question || activeProject?.name || 'LLM for Mobile Robot Task Planning';
      const currentPapers = (papers && papers.length > 0) 
        ? papers 
        : (() => {
            try {
              const cached = localStorage.getItem(`litreview_search_papers_${currentProjectId}`);
              return cached ? JSON.parse(cached) : [];
            } catch { return []; }
          })();

      const res = await safeFetch('/slr-swarm/step1-setup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          idea,
          research_field: projectData?.research_field || activeProject?.research_field || '',
          criteria_include: projectData?.criteria_include || activeProject?.criteria_include || [],
          criteria_exclude: projectData?.criteria_exclude || activeProject?.criteria_exclude || [],
          corpus: currentPapers.map((p, i) => ({
            paper_id: String(p.id || p.doi || i),
            title: p.title || '',
            abstract: p.abstract || '',
            year: Number(p.year) || 2024,
            venue: p.journal || p.venue || '',
            doi: p.doi || ''
          }))
        })
      });
      if (res.ok) {
        const data = await res.json();
        if (data.gap_map && data.gap_map.cells && data.gap_map.cells.length > 0) {
          setGapMapData(data.gap_map);
          localStorage.setItem(`slr_gap_map_${currentProjectId}`, JSON.stringify(data.gap_map));
        }
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
      const res = await safeFetch('/slr-swarm/paper-summary', {
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
      const res = await safeFetch('/slr-swarm/paper-genealogy', {
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
    const titleLower = newPaper.title.toLowerCase();
    // The button reads "Đã trong danh sách" (already in the list) once added,
    // but this only ever added -- clicking again did nothing, so there was no
    // way to undo adding a paper from the genealogy tree. Toggling here makes
    // the button's own displayed state (added vs not) match what clicking it
    // actually does.
    if (papers.some(p => p.title.toLowerCase() === titleLower)) {
      setPapers(prev => prev.filter(p => p.title.toLowerCase() !== titleLower));
      return;
    }
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
    setPapers(prev => [formatted, ...prev]);
  };

  const toggleExpandAbstract = (key) => {
    if (!key) return;
    setExpandedPaperIds(prev => 
      prev.includes(key) ? prev.filter(item => item !== key) : [...prev, key]
    );
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

    // `currentProjectId` (line 41) falls back to the hardcoded demo/default
    // project id whenever ProjectContext hasn't resolved an active project
    // yet -- sending THAT id here is indistinguishable from the researcher
    // genuinely having that project open, so screening would silently judge
    // the paper against an unrelated project's criteria (confirmed live:
    // a Robotics paper got screened against an ECG project's inclusion
    // criteria). Use the unmasked signal so a not-yet-resolved project fails
    // loudly instead of guessing.
    const resolvedProjectId = activeProjectId || activeProject?.id || null;
    if (!resolvedProjectId) {
      setAiScreeningLoading(false);
      setAiScreeningResult({
        relevance_bucket: 'insufficient_info',
        reason: {
          matches: [],
          mismatches: ['Chưa xác định được đề tài (project) đang mở. Vui lòng tải lại trang và thử lại.']
        }
      });
      return;
    }

    try {
      const res = await safeFetch(`/papers/${encodeURIComponent(paper.id)}/screen`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: paper.title,
          abstract: paper.abstract,
          journal: paper.journal,
          year: paper.year,
          doi: paper.doi,
          authors: paper.authors,
          project_id: resolvedProjectId
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
        if (activeProject) {
          setProjectData(activeProject);
          return;
        }
        const cached = localStorage.getItem(`research_setup_data_${currentProjectId}`);
        if (cached) {
          setProjectData(JSON.parse(cached));
        }
        const res = await safeFetch(`/projects/${currentProjectId}`);
        if (res.ok) {
          const data = await res.json();
          setProjectData(data);
          localStorage.setItem(`research_setup_data_${currentProjectId}`, JSON.stringify(data));
        }
      } catch (err) {
        console.error("Error fetching project:", err);
      }
    };
    fetchProject();

    window.addEventListener('research_setup_updated', fetchProject);
    return () => window.removeEventListener('research_setup_updated', fetchProject);
  }, [currentProjectId, activeProject]);

  // Tải lịch sử search từ backend
  const fetchHistory = useCallback(async () => {
    try {
      setHistoryLoading(true);
      const res = await safeFetch(`/projects/${currentProjectId}/search-history`);
      if (!res.ok) return;
      const data = await res.json();
      setHistory(data.history || []);
      return data.history || [];
    } catch {
      return [];
    } finally {
      setHistoryLoading(false);
    }
  }, [currentProjectId]);

  // Tải papers của 1 lần search cụ thể từ backend
  const loadPapersForQuery = useCallback(async (queryId, queryString) => {
    try {
      const res = await safeFetch(`/search-queries/${queryId}/papers`);
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
    
    // Combine selected keywords and any custom text in search input
    const terms = [...selectedKeywords];
    if (searchQuery.trim() && !terms.includes(searchQuery.trim())) {
      terms.push(searchQuery.trim());
    }

    const finalQueryString = terms.join(' ').trim();

    if (!finalQueryString) {
      setError(t('search.error_no_keyword'));
      return;
    }

    localStorage.setItem(`last_search_query_${currentProjectId}`, finalQueryString);
    localStorage.setItem('last_search_query', finalQueryString);

    setLoading(true);
    setError('');

    try {
      const response = await safeFetch(`/projects/${currentProjectId}/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(apiKey.trim() ? { 'X-API-Key': apiKey.trim() } : {})
        },
        body: JSON.stringify({
          query_string: finalQueryString,
          strategy_label: null
        })
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || (isVi ? 'Lỗi tìm kiếm từ server' : 'Search failed from server'));
      }

      const data = await response.json();
      const scopusOnly = data.papers || [];
      if (scopusOnly.length > 0) {
        setPapers(scopusOnly);
        const confirmedCount = scopusOnly.filter(p => p.scopus_status === 'indexed').length;
        const undeterminedCount = scopusOnly.filter(p => p.scopus_status !== 'indexed').length;
        const meta = {
          provider: data.provider || 'google_scholar',
          limit: data.limit || 20,
          total_found: scopusOnly.length,
          total_confirmed: confirmedCount,
          total_undetermined: undeterminedCount,
          duplicates: data.duplicates ?? 0,
        };
        setSearchMeta(meta);
        localStorage.setItem(`litreview_search_papers_${currentProjectId}`, JSON.stringify(scopusOnly));
        localStorage.setItem(`litreview_search_meta_${currentProjectId}`, JSON.stringify(meta));

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
        setError(err.message || (isVi ? 'Lỗi không xác định khi gọi Backend.' : 'Unknown error calling backend.'));
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
      const res = await safeFetch(`/papers/${paperId}/screen`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: currentProjectId }),
      });
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
      await safeFetch(`/papers/${paperId}/screening-decision`, {
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

  return (
    <div className="flex gap-0 min-h-screen relative">
      {/* Toast Notification */}
      {searchToast && (
        <div className="fixed bottom-24 left-1/2 -translate-x-1/2 z-50 px-4 py-2.5 rounded-xl bg-slate-900/95 dark:bg-slate-800/95 backdrop-blur-md text-white text-xs font-semibold shadow-xl flex items-center gap-2 border border-slate-700/80 animate-slide-up">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{searchToast}</span>
        </div>
      )}
      
      {/* ====== LEFT SIDEBAR ====== */}
      <aside className="hidden lg:flex flex-col w-72 shrink-0 sticky top-0 h-screen overflow-y-auto border-r border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900 p-4 space-y-4">
        {/* Topic Overview */}
        <div className="card p-4 space-y-3">
          <div className="flex items-center justify-between gap-2 pb-2 border-b border-surface-100 dark:border-surface-800">
            <div className="flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-primary-600 dark:text-primary-400" />
              <h4 className="section-label">
                {t('search.topic_scope')}
              </h4>
            </div>
            <span className="badge badge-primary text-[10px]">
              {projectData?.year_from || 2020} – {projectData?.year_to || 2026}
            </span>
          </div>

          <div className="space-y-2 text-xs">
            <div>
              <p className="section-label mb-0.5">{t('search.field_label')}</p>
              <p className="font-medium text-surface-800 dark:text-surface-200">
                {projectData?.research_field || '—'}
              </p>
            </div>

            <div>
              <p className="section-label mb-0.5">{t('search.question_label')}</p>
              <p className={`text-surface-600 dark:text-surface-400 mt-0.5 leading-relaxed ${
                isQuestionExpanded ? '' : 'line-clamp-2'
              }`}>
                {projectData?.research_question || projectData?.name || '—'}
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

        {/* Gap Analysis */}
        <div className="card p-4 space-y-3">
          <div className="flex items-center gap-2">
            <Target className="w-4 h-4 text-primary-600 dark:text-primary-400" />
            <h4 className="section-label">{t('search.opportunities_gaps')}</h4>
          </div>
          <p className="text-xs text-surface-500 dark:text-surface-400 leading-relaxed">
            {t('search.gap_desc', { count: papers.length })}
          </p>
          <button
            type="button"
            onClick={handleOpenGapAnalysis}
            className="btn btn-primary btn-sm w-full"
          >
            <Target className="w-3.5 h-3.5" />
            <span>{t('search.gap_btn')}</span>
          </button>
        </div>
      </aside>

      {/* ====== MAIN CONTENT ====== */}
      <div className="flex-1 min-w-0 px-6 py-6 space-y-5">

        {/* Research Topic Banner */}
        {projectData && (
          <div className="card p-4 flex items-center justify-between gap-4">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-8 h-8 rounded-xl bg-primary-50 dark:bg-primary-950 flex items-center justify-center flex-shrink-0">
                <BookOpen className="w-4 h-4 text-primary-600 dark:text-primary-400" />
              </div>
              <div className="min-w-0">
                <h3 className="text-xs font-bold text-surface-900 dark:text-white truncate">
                  {projectData.name || t('search.unnamed_project')}
                </h3>
                <p className="text-xs text-surface-400 truncate mt-0.5">
                  {projectData.research_question || t('search.no_question')}
                </p>
              </div>
            </div>
            <button
              onClick={() => setShowScreeningModal(true)}
              className="btn btn-primary btn-sm flex-shrink-0"
            >
              <ShieldAlert className="w-3.5 h-3.5" />
              Screening
            </button>
          </div>
        )}

        {/* Page Header */}
        <div className="page-header">
          <div>
            <h1 className="page-title">{t('search.tab_title')}</h1>
            <p className="text-sm text-surface-500 dark:text-surface-400">{t('search.tab_desc')}</p>
          </div>
          {papers.length > 0 && (
            <span className="badge badge-primary">{papers.length} {t('search.verified_papers')}</span>
          )}
        </div>

        {/* Unified Search Console */}
        <form id="tour-search-bar" onSubmit={handleSearch} className="card p-5 sm:p-6 space-y-4 shadow-xl border border-surface-200 dark:border-surface-800 bg-white dark:bg-surface-900">
          {/* Main Input Row */}
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="w-5 h-5 text-surface-400 absolute left-4 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={handleSearchQueryChange}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    if (searchQuery.trim()) {
                      handleAddCustomKeyword();
                    } else {
                      handleSearch();
                    }
                  }
                }}
                placeholder={isVi ? 'Nhập thêm từ khóa tùy chỉnh (nhấn Enter hoặc bấm Thêm để lưu vào danh sách)...' : 'Type custom keyword (press Enter or click Add)...'}
                className="w-full pl-12 pr-24 py-3.5 border rounded-2xl text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-primary-500 bg-surface-50 border-surface-300 text-surface-900 placeholder-surface-400 dark:bg-surface-800 dark:border-surface-700 dark:text-white dark:placeholder-surface-500 shadow-inner"
              />
              {searchQuery ? (
                <button
                  type="button"
                  onClick={handleAddCustomKeyword}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-bold text-primary-600 dark:text-primary-400 bg-primary-100 dark:bg-primary-950/60 px-2.5 py-1 rounded-lg hover:bg-primary-200 transition-colors"
                >
                  {isVi ? '+ Thêm' : '+ Add'}
                </button>
              ) : null}
            </div>

            <button
              type="submit"
              disabled={loading || (selectedKeywords.length === 0 && !searchQuery.trim())}
              className="btn btn-primary font-bold px-7 py-3.5 rounded-2xl text-sm transition-all shadow-primary-md flex items-center justify-center gap-2 shrink-0"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>{t('search.searching')}</span>
                </>
              ) : (
                <>
                  <Search className="w-4 h-4" />
                  <span>{isVi ? `Tìm kiếm bài báo (${selectedKeywords.length})` : `Search Papers (${selectedKeywords.length})`}</span>
                </>
              )}
            </button>
          </div>

          {/* SerpApi Key (optional, collapsible) */}
          <div className="pt-1">
            <button
              type="button"
              onClick={() => setShowApiKeyInput(prev => !prev)}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-surface-500 hover:text-primary-600 dark:text-surface-400 dark:hover:text-primary-400 transition-colors"
            >
              <Key className="w-3.5 h-3.5" />
              <span>{isVi ? 'Cấu hình SerpApi Key (tùy chọn)' : 'Configure SerpApi Key (optional)'}</span>
              {apiKey.trim() && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />}
              {showApiKeyInput ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>
            {showApiKeyInput && (
              <div className="mt-2 flex flex-col sm:flex-row sm:items-center gap-2">
                <div className="relative flex-1">
                  <Key className="w-4 h-4 text-surface-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="password"
                    value={apiKey}
                    onChange={handleApiKeyChange}
                    placeholder={isVi ? 'Dán SerpApi key của bạn tại đây...' : 'Paste your SerpApi key here...'}
                    className="w-full pl-9 pr-3 py-2 border rounded-xl text-xs font-medium focus:outline-none focus:ring-2 focus:ring-primary-500 bg-surface-50 border-surface-300 text-surface-900 placeholder-surface-400 dark:bg-surface-800 dark:border-surface-700 dark:text-white dark:placeholder-surface-500"
                  />
                </div>
                <span className="text-xs text-surface-400 dark:text-surface-500 shrink-0">
                  {isVi ? 'Dùng để tăng giới hạn tìm kiếm học thuật (Google Scholar).' : 'Used to raise the academic search (Google Scholar) rate limit.'}
                </span>
              </div>
            )}
          </div>

          {/* 1. Suggested Keywords from Topic Area */}
          {suggestedKeywords && suggestedKeywords.length > 0 && (
            <div className="pt-3 border-t border-surface-100 dark:border-surface-800 space-y-2.5">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <span className="text-xs font-bold text-surface-600 dark:text-surface-300 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-amber-500 animate-pulse" />
                  <span>{isVi ? 'Gợi ý từ khóa từ đề tài nghiên cứu (PICO):' : 'Suggested Keywords from Topic (PICO):'}</span>
                </span>

                <div className="flex items-center gap-2 self-start sm:self-auto">
                  <button
                    type="button"
                    onClick={() => {
                      setSelectedKeywords(suggestedKeywords);
                      localStorage.setItem(`litreview_selected_keywords_${currentProjectId}`, JSON.stringify(suggestedKeywords));
                    }}
                    className="px-3.5 py-1.5 rounded-xl text-xs font-bold bg-primary-50 dark:bg-primary-950/60 text-primary-700 dark:text-primary-300 border border-primary-200 dark:border-primary-800/80 hover:bg-primary-100 dark:hover:bg-primary-900/80 transition-all shadow-2xs flex items-center gap-1.5 cursor-pointer"
                  >
                    <Check className="w-3.5 h-3.5 stroke-[2.5]" />
                    <span>{isVi ? 'Chọn tất cả' : 'Select all'}</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      navigator.clipboard.writeText(suggestedKeywords.join(' '));
                    }}
                    className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-surface-100 hover:bg-surface-200 dark:bg-surface-800 dark:hover:bg-surface-700 text-surface-700 dark:text-surface-300 border border-surface-200 dark:border-surface-700/60 transition-all shadow-2xs flex items-center gap-1 cursor-pointer"
                  >
                    <span>{isVi ? 'Sao chép' : 'Copy'}</span>
                  </button>
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                {suggestedKeywords.map((kw, idx) => {
                  const isSelected = selectedKeywords.includes(kw);
                  return (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => toggleKeyword(kw)}
                      className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 border shadow-xs cursor-pointer ${
                        isSelected
                          ? 'bg-primary-50 dark:bg-primary-950/40 text-primary-700 dark:text-primary-300 border-primary-300 dark:border-primary-800 ring-1 ring-primary-400/40'
                          : 'bg-surface-100 hover:bg-surface-200 dark:bg-surface-800/80 dark:hover:bg-surface-800 text-surface-600 dark:text-surface-400 border-surface-200 dark:border-surface-700/60'
                      }`}
                      title={isSelected ? (isVi ? 'Nhấn để bỏ chọn' : 'Click to deselect') : (isVi ? 'Nhấn để thêm vào danh sách tìm kiếm' : 'Click to select')}
                    >
                      <span>{kw}</span>
                      {isSelected ? <Check className="w-3 h-3 text-primary-600 dark:text-primary-400 stroke-[2.5]" /> : <Plus className="w-3 h-3 text-surface-400" />}
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* 2. Selected Keywords (Các từ khóa đã chọn để tìm kiếm) */}
          <div className="pt-3 border-t border-surface-100 dark:border-surface-800 space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-surface-900 dark:text-white flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                <span>{isVi ? `Các từ khóa đã chọn để tìm kiếm (${selectedKeywords.length}):` : `Selected Search Keywords (${selectedKeywords.length}):`}</span>
              </span>

              {selectedKeywords.length > 0 && (
                <button
                  type="button"
                  onClick={() => {
                    setSelectedKeywords([]);
                    localStorage.setItem(`litreview_selected_keywords_${currentProjectId}`, JSON.stringify([]));
                  }}
                  className="px-3.5 py-1.5 rounded-xl text-xs font-bold bg-rose-50 dark:bg-rose-950/50 hover:bg-rose-100 dark:hover:bg-rose-900/60 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800/70 transition-all shadow-2xs flex items-center gap-1.5 cursor-pointer"
                >
                  <Trash2 className="w-3.5 h-3.5 text-rose-500" />
                  <span>{isVi ? 'Xóa hết từ khóa đã chọn' : 'Clear all keywords'}</span>
                </button>
              )}
            </div>

            {selectedKeywords.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {selectedKeywords.map((kw, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-bold bg-primary-600 text-white border border-primary-500 shadow-sm animate-scale-in"
                  >
                    <span>{kw}</span>
                    <button
                      type="button"
                      onClick={() => removeSelectedKeyword(idx)}
                      className="hover:bg-primary-700 rounded-full p-0.5 transition-colors cursor-pointer"
                      title={isVi ? 'Xóa từ khóa này' : 'Remove this keyword'}
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-xs text-surface-400 italic">
                {isVi ? 'Chưa có từ khóa nào được chọn. Hãy bấm vào các từ khóa gợi ý ở trên hoặc gõ từ khóa mới.' : 'No keywords selected. Click suggestions above or type custom keywords.'}
              </p>
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
          <div className="p-3 rounded-xl bg-danger-light dark:bg-danger-dark border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0 text-danger" />
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
            <div className="card flex flex-col items-center justify-center py-20 text-center">
              <div className="w-16 h-16 rounded-2xl bg-surface-100 dark:bg-surface-800 flex items-center justify-center mb-4">
                <Search className="w-8 h-8 text-surface-400" />
              </div>
              <p className="font-display font-semibold text-surface-700 dark:text-surface-300 mb-1">{t('search.empty_title')}</p>
              <p className="text-sm text-surface-400 max-w-xs">{t('search.empty_desc')}</p>
            </div>
          )}

          {/* Filter Empty State */}
          {papers.length > 0 && filteredAndSortedPapers.length === 0 && (
            <div className="card flex flex-col items-center justify-center py-16 text-center">
              <div className="w-12 h-12 rounded-2xl bg-surface-100 dark:bg-surface-800 flex items-center justify-center mb-3">
                <Search className="w-6 h-6 text-surface-400" />
              </div>
              <p className="font-semibold text-surface-700 dark:text-surface-300 mb-1">{t('search.filter_empty_title')}</p>
              <p className="text-sm text-surface-400 mb-4">{t('search.filter_empty_desc')}</p>
              <button onClick={resetFilters} className="btn btn-primary btn-sm">
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
          {papers.length > 0 && viewMode === 'cards' && filteredAndSortedPapers.map((paper, idx) => {
            const paperKey = String(paper.id || paper.doi || paper.title || `paper_${idx}`);
            const isSelected = selectedPaperIds.includes(paper.id || paperKey);
            const isExpanded = expandedPaperIds.includes(paperKey);

            return (
              <div
                key={paperKey}
                className={`p-6 md:p-8 rounded-3xl border transition-all duration-300 space-y-5 shadow-sm hover:shadow-xl hover:-translate-y-1 ${
                  'bg-white border-slate-200 hover:shadow-slate-300 dark:bg-slate-900 dark:border-slate-800 dark:text-slate-200 dark:hover:shadow-blue-900/20'
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

                    <h3 className={`font-extrabold text-lg md:text-xl leading-snug ${'text-slate-900 dark:text-white'}`}>
                      {paper.title}
                    </h3>
                    
                    <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">
                      {isVi ? 'Tác giả:' : 'Authors:'} {Array.isArray(paper.authors) ? paper.authors.join(', ') : paper.authors}
                    </p>
                  </div>
                </div>

                {/* Abstract & TL;DR */}
                <div className={`p-5 rounded-2xl text-sm leading-relaxed border transition-all ${
                  'bg-slate-50 border-slate-200 text-slate-700 dark:bg-slate-800/80 dark:border-slate-700 dark:text-slate-300'
                }`}>
                  {paper.tldr && (
                    <div className="mb-3 p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-100 dark:border-emerald-800/50">
                      <p className="font-bold text-emerald-700 dark:text-emerald-400">⚡ {isVi ? 'Tóm tắt AI (TL;DR):' : 'AI Summary (TL;DR):'}</p>
                      <p className="text-emerald-800 dark:text-emerald-300 mt-1">{paper.tldr.replace('TL;DR: ', '')}</p>
                    </div>
                  )}
                  
                  <p className="font-bold text-blue-600 dark:text-sky-400 mb-1">📝 Abstract:</p>

                  <p className={`text-slate-700 dark:text-slate-300 leading-relaxed font-normal ${
                    paper.abstract && paper.abstract.length > 250 && !isExpanded ? 'line-clamp-3' : 'whitespace-pre-line'
                  }`}>
                    {paper.abstract || (isVi ? 'Không có tóm tắt.' : 'No abstract available.')}
                  </p>

                  {paper.abstract && paper.abstract.length > 250 && (
                    <button
                      type="button"
                      onClick={() => toggleExpandAbstract(paperKey)}
                      className="mt-3 text-xs font-extrabold text-blue-600 dark:text-sky-400 hover:underline flex items-center gap-1 transition-colors cursor-pointer"
                    >
                      {isExpanded ? (
                        <>
                          <ChevronUp className="w-4 h-4 text-blue-600 dark:text-sky-400" />
                          <span>{isVi ? 'Thu gọn' : 'Show less'}</span>
                        </>
                      ) : (
                        <>
                          <ChevronDown className="w-4 h-4 text-blue-600 dark:text-sky-400" />
                          <span>{isVi ? 'Xem thêm...' : 'Read more...'}</span>
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
                        'bg-slate-100 hover:bg-slate-200 border-slate-200 text-slate-800 dark:bg-slate-800 dark:hover:bg-slate-700 dark:border-slate-700 dark:text-white'
                      }`}
                    >
                      <Download className="w-4 h-4 text-blue-600 dark:text-sky-400" />
                      <span>Tải PDF</span>
                      <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
                    </a>

                    <button
                      onClick={() => handleOpenSummary(paper)}
                      className={`flex-1 sm:flex-none flex items-center justify-center gap-2 px-3.5 py-2.5 rounded-lg text-xs font-bold transition-all border shadow-sm ${
                        'bg-emerald-50 hover:bg-emerald-100 border-emerald-200 text-emerald-700 dark:bg-slate-800 dark:hover:bg-slate-700 dark:border-emerald-500/40 dark:text-emerald-400'
                      }`}
                      title="Xem Hồ sơ tóm tắt bài báo (TL;DR)"
                    >
                      <FileText className="w-4 h-4 text-emerald-500" />
                      <span>Tóm tắt bài báo</span>
                    </button>

                    <button
                      onClick={() => handleOpenGenealogy(paper)}
                      className={`flex-1 sm:flex-none flex items-center justify-center gap-2 px-3.5 py-2.5 rounded-lg text-xs font-bold transition-all border shadow-sm ${
                        'bg-sky-50 hover:bg-sky-100 border-sky-200 text-sky-700 dark:bg-slate-800 dark:hover:bg-slate-700 dark:border-sky-500/40 dark:text-sky-400'
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

          {/* Floating Bottom Action Bar (Fixed Sticky Dock) */}
          {selectedPaperIds.length > 0 && (
            <div className="fixed bottom-6 left-1/2 -translate-x-1/2 w-[94%] max-w-4xl bg-slate-900/95 backdrop-blur-md text-white p-3.5 sm:p-4 rounded-3xl border border-slate-700/80 shadow-2xl flex flex-col sm:flex-row items-center justify-between gap-3 z-50 animate-slide-up ring-1 ring-white/10">
              <div className="flex items-center gap-3 w-full sm:w-auto">
                <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white font-extrabold flex items-center justify-center text-sm shadow-md shrink-0">
                  {selectedPaperIds.length}
                </div>
                <div>
                  <p className="font-bold text-xs sm:text-sm text-slate-100">
                    {isVi ? `Đã chọn ${selectedPaperIds.length} bài báo` : `Selected ${selectedPaperIds.length} papers`}
                  </p>
                  <p className="text-[11px] text-slate-400">
                    {isVi ? 'Xuất trích dẫn hoặc chuyển sang phân tích chuyên sâu' : 'Export citations or proceed to analysis'}
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap sm:flex-nowrap gap-2 w-full sm:w-auto items-center justify-end">
                <button
                  onClick={clearSelectedPapers}
                  className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white font-semibold rounded-xl text-xs transition-all border border-slate-700 cursor-pointer"
                >
                  {isVi ? 'Bỏ chọn' : 'Deselect'}
                </button>

                {/* In-Context Export Dropdown Hub */}
                <div className="relative">
                  <button
                    onClick={() => setExportMenuOpen(!exportMenuOpen)}
                    className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-white font-bold rounded-xl text-xs transition-all border border-slate-600 shadow-md flex items-center justify-center gap-1.5 cursor-pointer"
                  >
                    <Download className="w-3.5 h-3.5 text-emerald-400" />
                    <span>{isVi ? 'Xuất dữ liệu' : 'Export'}</span>
                    <ChevronDown className={`w-3 h-3 transition-transform ${exportMenuOpen ? 'rotate-180' : ''}`} />
                  </button>

                  {exportMenuOpen && (
                    <>
                      <div className="fixed inset-0 z-40" onClick={() => setExportMenuOpen(false)} />
                      <div className="absolute right-0 bottom-full mb-2 w-60 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl p-1.5 z-50 animate-slide-up text-slate-800 dark:text-slate-200">
                        <div className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-400 border-b border-slate-100 dark:border-slate-800 mb-1">
                          {isVi ? 'Chọn định dạng xuất' : 'Select Export Format'}
                        </div>
                        <button
                          onClick={() => { setExportMenuOpen(false); handleExportSelectedBibTeX(); }}
                          className="w-full px-2.5 py-2 rounded-xl text-xs font-semibold hover:bg-blue-50 dark:hover:bg-blue-950/40 text-left flex items-center gap-2 text-blue-600 dark:text-blue-400 cursor-pointer transition-colors"
                        >
                          <FileText className="w-3.5 h-3.5" />
                          <span>BibTeX (.bib) - LaTeX/Overleaf</span>
                        </button>
                        <button
                          onClick={() => { setExportMenuOpen(false); handleExportSelectedCSV(); }}
                          className="w-full px-2.5 py-2 rounded-xl text-xs font-semibold hover:bg-emerald-50 dark:hover:bg-emerald-950/40 text-left flex items-center gap-2 text-emerald-600 dark:text-emerald-400 cursor-pointer transition-colors"
                        >
                          <Download className="w-3.5 h-3.5" />
                          <span>Excel / CSV (.csv)</span>
                        </button>
                        <button
                          onClick={() => { setExportMenuOpen(false); handleExportSelectedMarkdown(); }}
                          className="w-full px-2.5 py-2 rounded-xl text-xs font-semibold hover:bg-indigo-50 dark:hover:bg-indigo-950/40 text-left flex items-center gap-2 text-indigo-600 dark:text-indigo-400 cursor-pointer transition-colors"
                        >
                          <BookOpen className="w-3.5 h-3.5" />
                          <span>Markdown Summary (.md)</span>
                        </button>
                        <button
                          onClick={() => { setExportMenuOpen(false); handleExportSelectedJSON(); }}
                          className="w-full px-2.5 py-2 rounded-xl text-xs font-semibold hover:bg-purple-50 dark:hover:bg-purple-950/40 text-left flex items-center gap-2 text-purple-600 dark:text-purple-400 cursor-pointer transition-colors"
                        >
                          <Code className="w-3.5 h-3.5" />
                          <span>JSON Dataset (.json)</span>
                        </button>
                      </div>
                    </>
                  )}
                </div>

                {/* Direct CTA: Go to Review */}
                <button
                  onClick={() => {
                    // Merge the papers the user just selected into the workspace
                    // (dedup by id, keep whatever was already there) -- without
                    // this, the button only switched tabs and SynthesisPanel
                    // saw an empty workspacePapers, silently discarding the
                    // selection the user just made.
                    if (typeof setWorkspacePapers === 'function' && selectedPapers.length) {
                      setWorkspacePapers((prev) => {
                        const existingIds = new Set((prev || []).map((p) => p.id));
                        const toAdd = selectedPapers.filter((p) => !existingIds.has(p.id));
                        return toAdd.length ? [...(prev || []), ...toAdd] : (prev || []);
                      });
                    }
                    setActiveTab('synthesis');
                  }}
                  className="px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold rounded-xl text-xs transition-all shadow-md flex items-center justify-center gap-1.5 cursor-pointer shrink-0"
                >
                  <span>{isVi ? 'Đưa vào tổng quan' : 'Proceed to Review'}</span>
                  <ArrowRight className="w-3.5 h-3.5" />
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
              'bg-white border-slate-200 text-slate-900 dark:bg-slate-900 dark:border-slate-800 dark:text-white'
            }`}
          >
            <div className="flex items-center justify-between border-b pb-4 border-slate-200 dark:border-slate-800">
              <div className="flex items-center gap-3">
                <ShieldAlert className="w-6 h-6 text-indigo-500" />
                <h3 className="font-extrabold text-lg">
                  {isVi ? 'Tiêu chí đánh giá screening & PRISMA' : 'PRISMA Screening Protocol & Criteria'}
                </h3>
              </div>
              <button
                onClick={() => setShowScreeningModal(false)}
                className="text-slate-400 hover:text-slate-600 text-lg font-bold"
              >
                ✕
              </button>
            </div>

            {/* Research Question */}
            <div className={`p-4 rounded-2xl border ${'bg-blue-50/50 border-blue-100 dark:bg-slate-800/60 dark:border-slate-700'}`}>
              <p className="text-xs font-bold text-blue-600 dark:text-sky-400 mb-1">🎯 Câu hỏi nghiên cứu:</p>
              <p className="text-sm font-semibold">{projectData.research_question || 'Chưa thiết lập'}</p>
            </div>

            {/* Criteria */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div className={`p-4 rounded-2xl border ${'bg-emerald-50 border-emerald-200 dark:bg-emerald-950/30 dark:border-emerald-800'}`}>
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
              <div className={`p-4 rounded-2xl border ${'bg-red-50 border-red-200 dark:bg-red-950/30 dark:border-red-800'}`}>
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
            <div className={`p-4 rounded-2xl text-sm ${'bg-slate-50 text-slate-600 dark:bg-slate-800 dark:text-slate-300'}`}>
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
              'bg-white border-slate-200 text-slate-900 dark:bg-slate-900 dark:border-slate-800 dark:text-white'
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
                title="Đóng cửa sổ"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto py-5 space-y-5 pr-1">
              {/* Paper Meta */}
              <div className={`p-4 rounded-2xl border ${'bg-slate-50 border-slate-200 dark:bg-slate-800/60 dark:border-slate-700'}`}>
                <p className="text-xs font-bold text-slate-500 dark:text-slate-400">Tạp chí & Năm xuất bản</p>
                <p className="text-xs font-semibold mt-0.5 text-blue-600 dark:text-sky-400">
                  {aiScreeningPaper.journal} ({aiScreeningPaper.year}) • DOI: {aiScreeningPaper.doi}
                </p>
              </div>

              {/* Research Scope */}
              {projectData && (
                <div className={`p-4 rounded-2xl border ${'bg-indigo-50/70 border-indigo-100 dark:bg-indigo-950/30 dark:border-indigo-900/50'}`}>
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
                    <div className={`p-4 rounded-2xl border ${'bg-emerald-50 border-emerald-100 dark:bg-emerald-950/20 dark:border-emerald-900/40'}`}>
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
                    <div className={`p-4 rounded-2xl border ${'bg-amber-50 border-amber-100 dark:bg-amber-950/20 dark:border-amber-900/40'}`}>
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
                    <div className={`p-4 rounded-2xl border ${'bg-slate-100/80 border-slate-200 dark:bg-slate-800/80 dark:border-slate-700'}`}>
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
                      'bg-slate-50 border-slate-200 text-slate-700 dark:bg-slate-800/40 dark:border-slate-700 dark:text-slate-300'
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
                Đóng
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ====== MODAL 3: KHOẢNG TRỐNG & CƠ HỘI ĐỀ TÀI (DEEP GAP ANALYSIS MODAL) ====== */}
      {showGapModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md animate-in fade-in duration-200">
          <div className={`w-full max-w-4xl max-h-[90vh] flex flex-col p-6 md:p-8 rounded-3xl border shadow-2xl overflow-hidden ${
            'bg-white border-slate-200 text-slate-900 dark:bg-slate-900 dark:border-slate-800 dark:text-white'
          }`}>
            {/* Header */}
            <div className="flex items-center justify-between pb-5 border-b border-slate-200 dark:border-slate-800">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-2xl bg-blue-500/10 border border-blue-500/20 text-blue-600 dark:text-sky-400 flex items-center justify-center">
                  <Target className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-lg font-display font-bold flex items-center gap-2">
                    {isVi ? 'Phân tích cơ hội & Khoảng trống nghiên cứu' : 'Research Gaps & Opportunity Analysis'}
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    {isVi 
                      ? `Phân tích điểm nghẽn và cơ hội đề tài dựa trên ${papers.length} bài báo bạn vừa tìm kiếm`
                      : `Analyze saturation and open research opportunities across ${papers.length} discovered papers`}
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
                  <p className="text-sm font-bold">{isVi ? `Đang quét toàn văn ${papers.length} bài báo để phân tích khoảng trống nghiên cứu...` : `Scanning full text of ${papers.length} papers to analyze research gaps...`}</p>
                </div>
              ) : gapMapData && gapMapData.cells && gapMapData.cells.length > 0 ? (
                (() => {
                  // Calculate dynamic matching against the active search papers
                  const computedCells = gapMapData.cells.map(c => {
                    if (!papers || papers.length === 0) return c;
                    const xWords = (c.dimension_x || '').toLowerCase().split(/[\s,&/]+/).filter(w => w.length >= 3 && !['with', 'from', 'using', 'models', 'and', 'the'].includes(w));
                    const yWords = (c.dimension_y || '').toLowerCase().split(/[\s,&/]+/).filter(w => w.length >= 3 && !['with', 'from', 'using', 'models', 'and', 'the'].includes(w));
                    
                    const count = papers.filter(p => {
                      const full = `${p.title || ''} ${p.abstract || ''} ${p.journal || ''}`.toLowerCase();
                      const matchX = xWords.length === 0 || xWords.some(w => full.includes(w));
                      const matchY = yWords.length === 0 || yWords.some(w => full.includes(w));
                      return matchX && matchY;
                    }).length;
                    
                    const sat = count === 0 ? 'empty' : count <= 2 ? 'sparse' : 'saturated';
                    return { ...c, paper_count: count, saturation: sat };
                  });

                  const totalCells = computedCells.length;
                  const emptyCount = computedCells.filter(c => c.saturation === 'empty').length;
                  const sparseCount = computedCells.filter(c => c.saturation === 'sparse').length;
                  const saturatedCount = computedCells.filter(c => c.saturation === 'saturated').length;
                  const emptyPct = Math.round((emptyCount / totalCells) * 100);
                  const sparsePct = Math.round((sparseCount / totalCells) * 100);
                  const saturatedPct = Math.max(0, 100 - emptyPct - sparsePct);

                  // Group by Dimension X (Architecture / Method)
                  const archDistribution = {};
                  computedCells.forEach(c => {
                    archDistribution[c.dimension_x] = Math.max(archDistribution[c.dimension_x] || 0, c.paper_count || 0);
                  });
                  // Calculate direct matching count per architectural branch
                  Object.keys(archDistribution).forEach(arch => {
                    const archWords = arch.toLowerCase().split(/[\s,&/]+/).filter(w => w.length >= 3 && !['with', 'from', 'using', 'models', 'and', 'the'].includes(w));
                    const directCount = (papers || []).filter(p => {
                      const full = `${p.title || ''} ${p.abstract || ''} ${p.journal || ''}`.toLowerCase();
                      return archWords.some(w => full.includes(w));
                    }).length;
                    archDistribution[arch] = Math.max(archDistribution[arch], directCount);
                  });

                  const maxArchPapers = Math.max(...Object.values(archDistribution), 1);

                  return (
                    <div className="space-y-6">
                      
                      {/* 1. VISUAL SATURATION SPECTRUM & ANALYTICS BAR */}
                      <div className="p-4 rounded-3xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80 space-y-3 shadow-xs">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <Activity className="w-4 h-4 text-blue-600 dark:text-sky-400" />
                            <span className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-200">
                              {isVi ? 'Phổ phân bố mức độ bão hòa đề tài (Gap Spectrum)' : 'Research Saturation Spectrum & Opportunity Index'}
                            </span>
                          </div>
                          <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
                            {isVi ? `Tổng cộng ${totalCells} giao điểm nghiên cứu` : `Total ${totalCells} topic intersections`}
                          </span>
                        </div>

                        {/* Multi-segment Spectrum Progress Bar */}
                        <div className="h-4 w-full rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden flex shadow-inner">
                          {emptyPct > 0 && (
                            <div 
                              style={{ width: `${emptyPct}%` }} 
                              className="h-full bg-emerald-500 hover:brightness-110 transition-all cursor-help relative group"
                              title={`${isVi ? 'Khoảng trống mới' : 'Open Gaps'}: ${emptyCount} ô (${emptyPct}%)`}
                            />
                          )}
                          {sparsePct > 0 && (
                            <div 
                              style={{ width: `${sparsePct}%` }} 
                              className="h-full bg-amber-500 hover:brightness-110 transition-all cursor-help relative group"
                              title={`${isVi ? 'Đang phát triển' : 'Emerging'}: ${sparseCount} ô (${sparsePct}%)`}
                            />
                          )}
                          {saturatedPct > 0 && (
                            <div 
                              style={{ width: `${saturatedPct}%` }} 
                              className="h-full bg-rose-500 hover:brightness-110 transition-all cursor-help relative group"
                              title={`${isVi ? 'Đã bão hòa' : 'Saturated'}: ${saturatedCount} ô (${saturatedPct}%)`}
                            />
                          )}
                        </div>

                        {/* Legend Cards */}
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5 pt-1">
                          <div className="p-3 rounded-2xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="w-3 h-3 rounded-full bg-emerald-500 inline-block shadow-xs"></span>
                              <span className="font-bold text-xs text-emerald-800 dark:text-emerald-300">
                                {isVi ? 'Khoảng trống mới' : 'Open Gap (0 papers)'}
                              </span>
                            </div>
                            <span className="text-xs font-extrabold text-emerald-700 dark:text-emerald-400 bg-white dark:bg-emerald-900/60 px-2 py-0.5 rounded-lg border border-emerald-300/40">
                              {emptyCount} ô ({emptyPct}%)
                            </span>
                          </div>

                          <div className="p-3 rounded-2xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="w-3 h-3 rounded-full bg-amber-500 inline-block shadow-xs"></span>
                              <span className="font-bold text-xs text-amber-800 dark:text-amber-300">
                                {isVi ? 'Đang phát triển' : 'Emerging (< 3 papers)'}
                              </span>
                            </div>
                            <span className="text-xs font-extrabold text-amber-700 dark:text-amber-400 bg-white dark:bg-amber-900/60 px-2 py-0.5 rounded-lg border border-amber-300/40">
                              {sparseCount} ô ({sparsePct}%)
                            </span>
                          </div>

                          <div className="p-3 rounded-2xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="w-3 h-3 rounded-full bg-rose-500 inline-block shadow-xs"></span>
                              <span className="font-bold text-xs text-rose-800 dark:text-rose-300">
                                {isVi ? 'Đã bão hòa' : 'Saturated (> 3 papers)'}
                              </span>
                            </div>
                            <span className="text-xs font-extrabold text-rose-700 dark:text-rose-400 bg-white dark:bg-rose-900/60 px-2 py-0.5 rounded-lg border border-rose-300/40">
                              {saturatedCount} ô ({saturatedPct}%)
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* 2. TOPIC DISTRIBUTION CHART (Biểu đồ mật độ theo kiến trúc phương pháp) */}
                      <div className="p-4 rounded-3xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80 space-y-3">
                        <div className="flex items-center justify-between">
                          <h4 className="text-xs font-display font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                            <Sparkles className="w-3.5 h-3.5 text-blue-500" />
                            <span>{isVi ? 'Mật độ bài báo theo trục kiến trúc & Phương pháp' : 'Paper Density by Method & Architecture Axis'}</span>
                          </h4>
                          <span className="text-[11px] font-semibold text-slate-500">
                            {isVi ? 'Phân loại từ tập kết quả' : 'Categorized from corpus'}
                          </span>
                        </div>

                        <div className="space-y-2.5">
                          {Object.entries(archDistribution).map(([archName, count], idx) => {
                            const barWidth = Math.round((count / maxArchPapers) * 100);
                            return (
                              <div key={idx} className="space-y-1">
                                <div className="flex justify-between text-xs font-semibold">
                                  <span className="text-slate-800 dark:text-slate-200 font-medium">{archName}</span>
                                  <span className="font-bold text-blue-600 dark:text-sky-400">{count} {isVi ? 'bài báo' : 'papers'}</span>
                                </div>
                                <div className="h-2.5 w-full bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                                  <div 
                                    style={{ width: `${Math.max(barWidth, 8)}%` }} 
                                    className="h-full bg-gradient-to-r from-blue-500 to-indigo-600 rounded-full transition-all duration-500"
                                  />
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>

                      {/* 3. GRID MATRIX (Chi tiết 16 ô giao điểm) */}
                      <div className="space-y-2.5">
                        <div className="flex items-center justify-between">
                          <h4 className="text-xs font-display font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                            {isVi ? '3. Chi tiết các ô giao điểm nghiên cứu (nhấp vào ô để xem phân tích chi tiết):' : '3. Topic Intersections Matrix (Click any cell to inspect opportunities):'}
                          </h4>
                          <span className="text-[11px] text-blue-500 font-semibold flex items-center gap-1">
                            <span>👆 {isVi ? 'Nhấp ô bất kỳ để xem đề xuất' : 'Click cell for proposals'}</span>
                          </span>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                          {computedCells.map((c, idx) => (
                            <button 
                              key={idx} 
                              type="button"
                              onClick={() => setSelectedGapCell(c)}
                              className={`p-4 rounded-2xl border text-left transition-all duration-200 cursor-pointer hover:scale-[1.03] hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-primary-500/50 ${
                                c.saturation === 'saturated' 
                                  ? 'bg-rose-50/70 hover:bg-rose-100/80 border-rose-200 dark:bg-rose-950/30 dark:hover:bg-rose-950/50 dark:border-rose-800/80' 
                                  : c.saturation === 'sparse' 
                                    ? 'bg-amber-50/70 hover:bg-amber-100/80 border-amber-200 dark:bg-amber-950/30 dark:hover:bg-amber-950/50 dark:border-amber-800/80' 
                                    : 'bg-emerald-50/70 hover:bg-emerald-100/80 border-emerald-200 dark:bg-emerald-950/30 dark:hover:bg-emerald-950/50 dark:border-emerald-800/80'
                              }`}
                            >
                              <div className="flex justify-between items-center text-[10px] font-bold uppercase tracking-wider mb-2">
                                <span className={`px-2 py-0.5 rounded-md ${
                                  c.saturation === 'saturated' ? 'bg-rose-200/80 text-rose-800 dark:bg-rose-900/60 dark:text-rose-300' :
                                  c.saturation === 'sparse' ? 'bg-amber-200/80 text-amber-800 dark:bg-amber-900/60 dark:text-amber-300' :
                                  'bg-emerald-200/80 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-300'
                                }`}>
                                  {c.saturation === 'empty' ? (isVi ? 'Khoảng trống mới' : 'Open Gap') : c.saturation === 'sparse' ? (isVi ? 'Còn dư địa' : 'Emerging') : (isVi ? 'Đã bão hòa' : 'Saturated')}
                                </span>
                                <span className="font-bold text-slate-600 dark:text-slate-300">
                                  {c.paper_count} {isVi ? 'bài báo' : 'papers'}
                                </span>
                              </div>
                              <div className="font-bold text-sm text-slate-900 dark:text-slate-100 leading-snug">
                                {c.dimension_x} <span className="text-blue-600 dark:text-sky-400">&</span> {c.dimension_y}
                              </div>
                              <div className="text-[11px] font-semibold text-primary-600 dark:text-primary-400 mt-2 flex items-center gap-1 pt-1 border-t border-slate-200/40 dark:border-slate-800/40">
                                <span>{isVi ? 'Xem bài đã có & Hướng mở rộng ➔' : 'Inspect papers & Novel angles ➔'}</span>
                              </div>
                            </button>
                          ))}
                        </div>
                      </div>

                      {/* 4. DEEP ANALYTICAL BREAKDOWN & 3 NOVEL DIRECTIONS */}
                      <div className="space-y-4 pt-2 border-t border-slate-200 dark:border-slate-800">
                        <h4 className="text-xs font-display font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                          {isVi ? '4. Phân tích chuyên sâu & Đề xuất đột phá' : '4. In-Depth Analysis & Breakthrough Directions'}
                        </h4>

                        {/* Limitations */}
                        <div className={`p-4 rounded-2xl border ${'bg-slate-50 border-slate-200 dark:bg-slate-800/50 dark:border-slate-700'} space-y-2`}>
                          <div className="flex items-center gap-2 text-xs font-bold text-amber-700 dark:text-amber-400">
                            <AlertCircle className="w-4 h-4" />
                            <span>{isVi ? 'Điểm nghẽn chưa được giải quyết trong các bài báo hiện tại:' : 'Unresolved bottlenecks in current literature:'}</span>
                          </div>
                          <ul className="text-xs text-slate-600 dark:text-slate-300 space-y-1.5 pl-4 list-disc leading-relaxed">
                            <li>{isVi ? 'Phần lớn các công trình tập trung vào các mô hình đơn lẻ, thiếu cơ chế kiểm chứng đối chiếu chéo (Cross-verification).' : 'Most works focus on isolated models without cross-verification mechanisms.'}</li>
                            <li>{isVi ? 'Chưa có nhiều nghiên cứu đánh giá toàn diện độ tin cậy và khả năng giải thích được (Explainability) trên tập dữ liệu thực tế lớn.' : 'Limited empirical benchmarks evaluating reliability and explainability on real-world datasets.'}</li>
                            <li>{isVi ? 'Chi phí tính toán và độ trễ xử lý tài liệu dài (Long-context reasoning) vẫn là rào cản lớn chưa được tối ưu triệt để.' : 'Computational complexity and inference latency remain significant bottlenecks for long-context tasks.'}</li>
                          </ul>
                        </div>

                        {/* 3 Novel Research Directions */}
                        <div className={`p-4 rounded-2xl border ${'bg-blue-50/50 border-blue-200 dark:bg-blue-950/30 dark:border-blue-800/60'} space-y-3`}>
                          <div className="flex items-center gap-2 text-xs font-bold text-blue-700 dark:text-sky-300">
                            <Sparkles className="w-4 h-4" />
                            <span>{isVi ? '3 hướng đề tài đề xuất có tiềm năng công bố cao:' : '3 Proposed High-Impact Research Directions:'}</span>
                          </div>
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1">
                            <div className="p-3 rounded-xl bg-white dark:bg-slate-900 border border-blue-100 dark:border-blue-900 space-y-1">
                              <p className="font-bold text-xs text-blue-600 dark:text-sky-400">{isVi ? 'Hướng 1: Multi-Agent tri thức' : 'Direction 1: Multi-Agent Knowledge'}</p>
                              <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed">
                                {isVi ? 'Xây dựng hệ thống Swarm phân tầng để trích xuất và đối chiếu bằng chứng chéo giữa các bài báo.' : 'Hierarchical multi-agent swarm architecture for multi-document synthesis and cross-evidence verification.'}
                              </p>
                            </div>
                            <div className="p-3 rounded-xl bg-white dark:bg-slate-900 border border-blue-100 dark:border-blue-900 space-y-1">
                              <p className="font-bold text-xs text-blue-600 dark:text-sky-400">{isVi ? 'Hướng 2: Giảm thiểu ảo giác' : 'Direction 2: Hallucination Mitigation'}</p>
                              <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed">
                                {isVi ? 'Cơ chế Grounding 100% với trích dẫn DOI trực tiếp từ PDF toàn văn để đảm bảo tính liêm chính học thuật.' : '100% grounded claim-evidence mapping with verifiable DOI & page-level citation anchors.'}
                              </p>
                            </div>
                            <div className="p-3 rounded-xl bg-white dark:bg-slate-900 border border-blue-100 dark:border-blue-900 space-y-1">
                              <p className="font-bold text-xs text-blue-600 dark:text-sky-400">{isVi ? 'Hướng 3: Tối ưu chi phí & Tốc độ' : 'Direction 3: Cost & Latency Optimization'}</p>
                              <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed">
                                {isVi ? 'Áp dụng kỹ thuật phân đoạn thông minh và Embedding phân cấp để xử lý hàng trăm trang tài liệu trong vài giây.' : 'Smart chunking and hierarchical embeddings to process hundreds of pages in real time.'}
                              </p>
                            </div>
                          </div>
                        </div>
                      </div>

                    </div>
                  );
                })()
              ) : (
                <div className="py-16 text-center text-slate-400 text-sm">
                  {isVi ? 'Chưa có dữ liệu khoảng trống. Hãy bấm tìm kiếm bài báo trước!' : 'No research gap data yet. Please search for papers first!'}
                </div>
              )}
            </div>

            {/* Clean Modal Footer (Action Oriented without redundant close button) */}
            <div className="border-t pt-4 border-slate-200 dark:border-slate-800 flex items-center justify-between">
              <span className="text-xs text-slate-400">
                {isVi ? '💡 Gợi ý: Bấm vào từng ô màu để xem bài báo đã có và hướng phát triển đề tài chi tiết' : '💡 Tip: Click any cell above to inspect existing papers and novel development angles'}
              </span>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(
                    `3 Hướng Đề Tài Nghiên Cứu Đột Phá:\n1. Multi-Agent Tri thức\n2. Giảm Thiểu Ảo Giác với DOI Grounding\n3. Tối Ưu Chi Phí & Tốc Độ Xử Lý`
                  );
                  alert(isVi ? 'Đã sao chép 3 hướng đề tài vào clipboard!' : 'Copied 3 research directions to clipboard!');
                }}
                className="px-5 py-2 rounded-xl text-xs font-bold bg-primary-600 hover:bg-primary-700 text-white transition-all shadow-sm flex items-center gap-1.5 cursor-pointer"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>{isVi ? 'Sao chép 3 hướng đề tài' : 'Copy Research Directions'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ====== MODAL: CELL DEEP DIVE (CHI TIẾT GIAO ĐIỂM NGHIÊN CỨU) ====== */}
      {selectedGapCell && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200" onClick={() => setSelectedGapCell(null)}>
          <div 
            onClick={(e) => e.stopPropagation()}
            className={`w-full max-w-3xl max-h-[88vh] flex flex-col p-6 md:p-8 rounded-3xl border shadow-2xl overflow-hidden ${
              'bg-white border-slate-200 text-slate-900 dark:bg-slate-900 dark:border-slate-800 dark:text-white'
            }`}
          >
            {/* Header */}
            <div className="flex items-start justify-between pb-4 border-b border-slate-200 dark:border-slate-800">
              <div className="flex items-center gap-3">
                <div className={`w-12 h-12 rounded-2xl flex items-center justify-center ${
                  selectedGapCell.saturation === 'saturated' ? 'bg-rose-500/10 text-rose-600 border border-rose-500/20' :
                  selectedGapCell.saturation === 'sparse' ? 'bg-amber-500/10 text-amber-600 border border-amber-500/20' :
                  'bg-emerald-500/10 text-emerald-600 border border-emerald-500/20'
                }`}>
                  <Target className="w-6 h-6" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className={`px-2.5 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider ${
                      selectedGapCell.saturation === 'saturated' ? 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300' :
                      selectedGapCell.saturation === 'sparse' ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300' :
                      'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
                    }`}>
                      {selectedGapCell.saturation === 'empty' ? (isVi ? 'Khoảng trống mới (0 bài)' : 'Open Gap (0 papers)') : selectedGapCell.saturation === 'sparse' ? (isVi ? 'Đang phát triển (< 3 bài)' : 'Emerging Topic') : (isVi ? 'Đã bão hòa (nhiều bài)' : 'Saturated')}
                    </span>
                    <span className="text-xs font-bold text-slate-500">
                      {selectedGapCell.paper_count} {isVi ? 'bài báo trong tập dữ liệu' : 'papers in corpus'}
                    </span>
                  </div>
                  <h3 className="text-lg font-display font-bold mt-1">
                    {selectedGapCell.dimension_x} <span className="text-blue-600 dark:text-sky-400">✕</span> {selectedGapCell.dimension_y}
                  </h3>
                </div>
              </div>

              <button
                onClick={() => setSelectedGapCell(null)}
                className="w-9 h-9 rounded-full flex items-center justify-center hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto py-5 space-y-5 custom-scrollbar">
              {/* 1. Existing Papers in Corpus */}
              <div className="space-y-2.5">
                <h4 className="text-xs font-display font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                  <BookOpen className="w-4 h-4 text-blue-500" />
                  <span>{isVi ? '1. Tổng quan các bài báo đã có trong tập tìm kiếm:' : '1. Overview of existing papers in your search results:'}</span>
                </h4>

                {(() => {
                  const xWords = selectedGapCell.dimension_x.toLowerCase().split(' ').filter(w => w.length > 2);
                  const yWords = selectedGapCell.dimension_y.toLowerCase().split(' ').filter(w => w.length > 2);
                  const matched = (papers || []).filter(p => {
                    const full = `${p.title || ''} ${p.abstract || ''}`.toLowerCase();
                    return xWords.some(w => full.includes(w)) && yWords.some(w => full.includes(w));
                  });

                  if (matched.length === 0) {
                    return (
                      <div className="p-4 rounded-2xl bg-emerald-50/60 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800/60 space-y-1.5">
                        <p className="text-xs font-bold text-emerald-800 dark:text-emerald-300">
                          {isVi ? '✨ 100% khoảng trống nghiên cứu chưa được khai thác!' : '✨ 100% Open Research Gap in your discovered papers!'}
                        </p>
                        <p className="text-xs text-emerald-900/80 dark:text-emerald-300/80 leading-relaxed">
                          {isVi 
                            ? 'Chưa có công trình nào trong 20 bài báo của bạn kết hợp đồng thời phương pháp này. Đây là hướng đi có độ mới rất cao để viết bài báo Scopus/IEEE!'
                            : 'No papers in your current search corpus combine this method and application. High potential for novel publication!'}
                        </p>
                      </div>
                    );
                  }

                  return (
                    <div className="space-y-2">
                      {matched.slice(0, 3).map((p, i) => (
                        <div key={i} className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 space-y-1">
                          <p className="font-bold text-xs text-slate-900 dark:text-white leading-snug">{p.title}</p>
                          <p className="text-[11px] text-slate-500 dark:text-slate-400">
                            {p.journal} ({p.year}) • {p.citations || 0} {isVi ? 'trích dẫn' : 'citations'} • {Array.isArray(p.authors) ? p.authors.join(', ') : p.authors}
                          </p>
                        </div>
                      ))}
                    </div>
                  );
                })()}
              </div>

              {/* 2. Bottlenecks & Open Research Angles */}
              <div className="p-4.5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80 space-y-2.5">
                <div className="flex items-center gap-2 text-xs font-bold text-amber-700 dark:text-amber-400">
                  <AlertCircle className="w-4 h-4" />
                  <span>{isVi ? 'Điểm nghẽn học thuật hiện tại của giao điểm này:' : 'Current academic bottlenecks for this intersection:'}</span>
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed pl-3 border-l-2 border-amber-400">
                  {isVi 
                    ? `Các công trình hiện tại về ${selectedGapCell.dimension_x} khi áp dụng cho ${selectedGapCell.dimension_y} thường gặp giới hạn về độ trễ xử lý thời gian thực, chi phí bộ nhớ khi suy luận chuỗi dài, và thiếu cơ chế kiểm chứng độ an toàn vật lý khi triển khai trên robot.`
                    : `Current works on ${selectedGapCell.dimension_x} applied to ${selectedGapCell.dimension_y} face limitations in real-time inference latency, long-context memory footprint, and physical safety verification.`}
                </p>
              </div>

              {/* 3. Actionable Research Proposal Directions */}
              <div className="p-4.5 rounded-2xl bg-blue-50/60 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800/60 space-y-3">
                <div className="flex items-center gap-2 text-xs font-bold text-blue-700 dark:text-sky-300">
                  <Sparkles className="w-4 h-4 text-amber-500" />
                  <span>{isVi ? '2 hướng phát triển đột phá có thể công bố thành bài báo mới:' : '2 Novel Breakthrough Angles for Publication:'}</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="p-3.5 rounded-xl bg-white dark:bg-slate-900 border border-blue-100 dark:border-blue-900/60 space-y-1.5 shadow-2xs">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-blue-600 dark:text-sky-400 bg-blue-50 dark:bg-blue-950 px-2 py-0.5 rounded-md">
                      {isVi ? 'Đề xuất 1: Thuật toán & Tối ưu' : 'Proposal 1: Algorithm Optimization'}
                    </span>
                    <p className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                      {isVi 
                        ? `Xây dựng kiến trúc phân tầng kết hợp ${selectedGapCell.dimension_x} với bộ nhớ hồi quy để tăng tốc ${selectedGapCell.dimension_y}.`
                        : `Develop hierarchical architecture combining ${selectedGapCell.dimension_x} with recurrent state memory for fast ${selectedGapCell.dimension_y}.`}
                    </p>
                  </div>

                  <div className="p-3.5 rounded-xl bg-white dark:bg-slate-900 border border-blue-100 dark:border-blue-900/60 space-y-1.5 shadow-2xs">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-950 px-2 py-0.5 rounded-md">
                      {isVi ? 'Đề xuất 2: Đối chuẩn thực nghiệm' : 'Proposal 2: Benchmark Evaluation'}
                    </span>
                    <p className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                      {isVi 
                        ? `Đánh giá đối chuẩn độ tin cậy và sai số va chạm của ${selectedGapCell.dimension_x} trên môi trường thực tế.`
                        : `Empirical reliability and collision rate benchmarking of ${selectedGapCell.dimension_x} in realistic testbeds.`}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="border-t pt-4 border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-3">
              <button
                type="button"
                onClick={() => setSelectedGapCell(null)}
                className="px-4 py-2 rounded-xl text-xs font-bold bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 transition-colors cursor-pointer"
              >
                {isVi ? '← Quay lại ma trận' : '← Back to Matrix'}
              </button>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    const query = `${selectedGapCell.dimension_x} ${selectedGapCell.dimension_y}`;
                    setSearchQuery(query);
                    if (!selectedKeywords.includes(query)) {
                      setSelectedKeywords([...selectedKeywords, query]);
                    }
                    setSelectedGapCell(null);
                    setShowGapModal(false);
                  }}
                  className="px-4 py-2 rounded-xl text-xs font-bold bg-blue-600 hover:bg-blue-700 text-white transition-all shadow-sm flex items-center gap-1.5 cursor-pointer"
                >
                  <Search className="w-3.5 h-3.5" />
                  <span>{isVi ? 'Tìm kiếm sâu theo giao điểm này' : 'Search this intersection'}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ====== MODAL 5: PAPER SUMMARY (TL;DR) ====== */}
      {summaryPaper && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-in fade-in duration-200">
          <div className={`w-full max-w-4xl max-h-[92vh] flex flex-col p-6 md:p-8 rounded-3xl border shadow-2xl overflow-hidden ${
            'bg-white border-slate-200 text-slate-900 dark:bg-slate-900 dark:border-slate-800 dark:text-white'
          }`}>
            <div className="flex items-center justify-between pb-5 border-b border-slate-200 dark:border-slate-800">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 flex items-center justify-center">
                  <FileText className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-lg font-display font-bold">
                    {isVi ? 'Hồ sơ tóm tắt bài báo (TL;DR one-pager)' : 'Paper Summary & Key Insights (TL;DR)'}
                  </h3>
                  <p className="text-xs font-mono text-slate-500 mt-1">{summaryPaper.id} | {isVi ? 'Trích xuất bởi AI' : 'Extracted by AI'}</p>
                </div>
              </div>
              <button
                onClick={() => { setSummaryPaper(null); setSummaryData(null); }}
                className="w-10 h-10 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 flex items-center justify-center transition-colors cursor-pointer"
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
                  <div className={`p-5 rounded-2xl border ${'bg-emerald-50 border-emerald-100 dark:bg-emerald-950/30 dark:border-emerald-900/50'}`}>
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
                    <div className={`p-5 rounded-2xl border ${'bg-slate-50 border-slate-200 dark:bg-slate-800/50 dark:border-slate-700/50'}`}>
                      <h5 className="text-xs font-bold text-blue-500 mb-2">🎯 MỤC TIÊU (OBJECTIVE)</h5>
                      <p className="text-sm leading-relaxed">{summaryData.objective}</p>
                    </div>
                    <div className={`p-5 rounded-2xl border ${'bg-slate-50 border-slate-200 dark:bg-slate-800/50 dark:border-slate-700/50'}`}>
                      <h5 className="text-xs font-bold text-purple-500 mb-2">⚙️ PHƯƠNG PHÁP (METHODOLOGY)</h5>
                      <p className="text-sm leading-relaxed">{summaryData.methodology}</p>
                    </div>
                    <div className={`p-5 rounded-2xl border ${'bg-slate-50 border-slate-200 dark:bg-slate-800/50 dark:border-slate-700/50'}`}>
                      <h5 className="text-xs font-bold text-amber-500 mb-2">📦 DỮ LIỆU & MẪU (DATASET)</h5>
                      <p className="text-sm leading-relaxed">{summaryData.dataset}</p>
                    </div>
                    <div className={`p-5 rounded-2xl border ${'bg-slate-50 border-slate-200 dark:bg-slate-800/50 dark:border-slate-700/50'}`}>
                      <h5 className="text-xs font-bold text-red-500 mb-2">🚧 HẠN CHẾ (LIMITATIONS)</h5>
                      <p className="text-sm leading-relaxed">{summaryData.limitations}</p>
                    </div>
                  </div>

                  {/* Key Findings (Full width) */}
                  <div className={`p-5 rounded-2xl border ${'bg-indigo-50 border-indigo-100 dark:bg-indigo-950/30 dark:border-indigo-900/50'}`}>
                    <h5 className="text-xs font-bold text-indigo-600 dark:text-indigo-400 mb-2">📈 KẾT QUẢ NỔI BẬT (KEY FINDINGS & METRICS)</h5>
                    <p className="text-sm leading-relaxed">{summaryData.key_findings}</p>
                  </div>

                  {/* Reliability Metrics */}
                  <div className={`p-4 rounded-xl border flex flex-wrap gap-6 items-center ${'bg-white border-slate-200 dark:bg-slate-900 dark:border-slate-800'}`}>
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
            'bg-white border-slate-200 text-slate-900 dark:bg-slate-900 dark:border-slate-800 dark:text-white'
          }`}>
            {/* Header */}
            <div className="flex items-center justify-between pb-5 border-b border-slate-200 dark:border-slate-800">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-2xl bg-sky-500/10 border border-sky-500/20 text-sky-500 flex items-center justify-center">
                  <GitFork className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-lg font-display font-bold flex items-center gap-2">
                    {isVi ? 'Cây phả hệ trích dẫn & Khám phá nguồn (Smart Snowballing)' : 'Citation Genealogy & Academic Snowballing'}
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    {isVi ? 'Lần theo dòng chảy học thuật 2 chiều: tiền đề lịch sử & Kế thừa mới nhất' : 'Trace bidirectional citation graph: Historical Foundations & Recent Extensions'}
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
                'bg-blue-50/50 border-blue-200 dark:bg-slate-800/80 dark:border-slate-700'
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
                  <p className="text-sm font-bold">Đang tìm nguồn tiền đề & Kế thừa liên quan đến bài báo này...</p>
                </div>
              ) : genealogyData ? (
                <div className="space-y-4">
                {genealogyData.has_unverified_ai_entries && (
                  <div className="p-3.5 rounded-2xl border border-amber-300 bg-amber-50 dark:bg-amber-950/30 dark:border-amber-900/60 flex items-start gap-2.5">
                    <span className="text-base leading-none mt-0.5">⚠️</span>
                    <p className="text-xs text-amber-800 dark:text-amber-300 leading-relaxed">
                      <span className="font-bold">Chưa xác minh:</span> Hệ thống chưa có kết nối tới cơ sở dữ liệu trích dẫn thật (Semantic Scholar/Crossref). Các bài báo đánh dấu <span className="font-bold">"AI gợi ý"</span> dưới đây do AI tự suy đoán dựa trên chủ đề — có thể KHÔNG tồn tại thật, DOI/link PDF có thể không mở được. Vui lòng tự tra cứu để xác nhận trước khi thêm vào project.
                    </p>
                  </div>
                )}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  
                  {/* Column 1: Backward Ancestors */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between pb-2 border-b border-amber-200 dark:border-amber-900/60">
                      <div className="flex items-center gap-2">
                        <span className="text-base">🏛️</span>
                        <h4 className="font-display font-bold text-xs uppercase tracking-wider text-amber-700 dark:text-amber-400">
                          Nguồn gốc & Tiền đề (backward citations)
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
                            'bg-amber-50/20 border-amber-100 hover:border-amber-300 dark:bg-slate-800/40 dark:border-slate-700 dark:hover:border-amber-500/50'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <h5 className="font-bold text-xs text-slate-900 dark:text-slate-100 leading-snug">
                              {p.title}
                            </h5>
                            <div className="shrink-0 flex flex-col items-end gap-1">
                              {p.source === 'ai_generated' && (
                                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-md bg-amber-500/20 text-amber-700 dark:text-amber-400" title="AI tự suy đoán, chưa xác minh có tồn tại thật hay không">
                                  ⚠️ AI gợi ý
                                </span>
                              )}
                              <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300">
                                {p.year}
                              </span>
                            </div>
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
                              href={(p.source !== 'ai_generated' && p.doi) ? (p.doi.startsWith('http') ? p.doi : `https://doi.org/${p.doi}`) : `https://scholar.google.com/scholar?q=${encodeURIComponent(p.title)}`}
                              target="_blank"
                              rel="noreferrer"
                              className={`px-2.5 py-1.5 rounded-xl text-[11px] font-bold transition-all border flex items-center gap-1.5 ${
                                'bg-white hover:bg-slate-100 border-slate-200 text-slate-700 shadow-xs dark:bg-slate-700/80 dark:hover:bg-slate-700 dark:border-slate-600 dark:text-slate-200'
                              }`}
                              title={p.source === 'ai_generated' ? 'DOI do AI suy đoán, chưa xác minh -- tìm trên Google Scholar' : 'Xem bài gốc / Tải PDF'}
                            >
                              <Download className="w-3.5 h-3.5 text-blue-500" />
                              <span>{p.source === 'ai_generated' ? 'Tìm trên Scholar' : 'PDF'}</span>
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
                                  ? 'bg-emerald-600 hover:bg-rose-600 text-white cursor-pointer group/toggle'
                                  : 'bg-amber-600 hover:bg-amber-700 text-white hover:scale-105 active:scale-95'
                              }`}
                              title={papers.some(item => item.title.toLowerCase() === p.title.toLowerCase()) ? 'Bấm để bỏ khỏi danh sách' : 'Thêm bài này vào danh sách'}
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
                          Kế thừa & Phát triển mới (forward citations)
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
                            'bg-sky-50/20 border-sky-100 hover:border-sky-300 dark:bg-slate-800/40 dark:border-slate-700 dark:hover:border-sky-500/50'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <h5 className="font-bold text-xs text-slate-900 dark:text-slate-100 leading-snug">
                              {p.title}
                            </h5>
                            <div className="shrink-0 flex flex-col items-end gap-1">
                              {p.source === 'ai_generated' && (
                                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-md bg-amber-500/20 text-amber-700 dark:text-amber-400" title="AI tự suy đoán, chưa xác minh có tồn tại thật hay không">
                                  ⚠️ AI gợi ý
                                </span>
                              )}
                              <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-sky-100 dark:bg-sky-950 text-sky-800 dark:text-sky-300">
                                {p.year}
                              </span>
                            </div>
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
                              href={(p.source !== 'ai_generated' && p.doi) ? (p.doi.startsWith('http') ? p.doi : `https://doi.org/${p.doi}`) : `https://scholar.google.com/scholar?q=${encodeURIComponent(p.title)}`}
                              target="_blank"
                              rel="noreferrer"
                              className={`px-2.5 py-1.5 rounded-xl text-[11px] font-bold transition-all border flex items-center gap-1.5 ${
                                'bg-white hover:bg-slate-100 border-slate-200 text-slate-700 shadow-xs dark:bg-slate-700/80 dark:hover:bg-slate-700 dark:border-slate-600 dark:text-slate-200'
                              }`}
                              title={p.source === 'ai_generated' ? 'DOI do AI suy đoán, chưa xác minh -- tìm trên Google Scholar' : 'Xem bài gốc / Tải PDF'}
                            >
                              <Download className="w-3.5 h-3.5 text-blue-500" />
                              <span>{p.source === 'ai_generated' ? 'Tìm trên Scholar' : 'PDF'}</span>
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
                                  ? 'bg-emerald-600 hover:bg-rose-600 text-white cursor-pointer group/toggle'
                                  : 'bg-sky-600 hover:bg-sky-700 text-white hover:scale-105 active:scale-95'
                              }`}
                              title={papers.some(item => item.title.toLowerCase() === p.title.toLowerCase()) ? 'Bấm để bỏ khỏi danh sách' : 'Thêm bài này vào danh sách'}
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
                </div>
              ) : null}
            </div>

            {/* Footer */}
            <div className="border-t pt-4 border-slate-200 dark:border-slate-800 flex justify-end">
              <button
                onClick={() => { setGenealogyPaper(null); setGenealogyData(null); }}
                className="px-6 py-2.5 rounded-xl text-xs font-bold bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 transition-colors"
              >
                Đóng
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
