import React, { useState, useEffect, useRef } from 'react';
import { 
  BookOpen, Target, Settings, Save, Loader2, Plus, X, 
  CheckCircle2, Compass, AlertCircle, ArrowRight, ArrowLeft, Check,
  ShieldCheck, Edit3, Copy, Search, Sparkles,
  ChevronRight, Layers, FileCheck, HelpCircle, Lightbulb,
  CheckCheck, Bookmark, ArrowUpRight, Filter, Zap
} from 'lucide-react';
import { normalizeResearchSetup } from '../../utils/researchSetup';
import { useLanguage } from '../../contexts/LanguageContext';
import { useProject } from '../../contexts/ProjectContext';
import { useAuth } from '../../contexts/AuthContext';
import { API_BASE } from '../../utils/apiConfig';

// ── Custom Vibrant Animated Academic Illustrative Badges ─────────────────────
function TopicStepperIcon({ isApproved, isActive }) {
  if (isApproved) {
    return (
      <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-cyan-500 via-blue-600 to-indigo-600 p-0.5 shadow-lg shadow-cyan-500/25 flex items-center justify-center transition-all duration-300 transform hover:scale-105">
        <div className="w-full h-full bg-slate-950/20 backdrop-blur-xs rounded-[14px] flex items-center justify-center">
          <svg className="w-6 h-6 text-cyan-200 animate-pulse" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" className="opacity-40 stroke-cyan-400" />
            <circle cx="12" cy="12" r="6" className="opacity-70 stroke-cyan-300" />
            <circle cx="12" cy="12" r="2" className="fill-cyan-200 stroke-cyan-100" />
            <path d="M12 2v3m0 14v3M2 12h3m14 0h3" className="stroke-cyan-300 opacity-60" />
          </svg>
        </div>
      </div>
    );
  }
  if (isActive) {
    return (
      <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-700 p-0.5 shadow-md shadow-blue-500/20 flex items-center justify-center ring-4 ring-blue-500/20">
        <svg className="w-5 h-5 text-white animate-spin-slow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polygon points="12 2 19 21 12 17 5 21 12 2" className="fill-blue-400/30" />
        </svg>
      </div>
    );
  }
  return (
    <div className="w-11 h-11 rounded-2xl bg-surface-200 dark:bg-surface-800 flex items-center justify-center text-surface-400 font-bold text-xs">
      01
    </div>
  );
}

function CriteriaStepperIcon({ isApproved, isActive }) {
  if (isApproved) {
    return (
      <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-emerald-400 via-teal-500 to-emerald-600 p-0.5 shadow-lg shadow-teal-500/25 flex items-center justify-center transition-all duration-300 transform hover:scale-105">
        <div className="w-full h-full bg-slate-950/20 backdrop-blur-xs rounded-[14px] flex items-center justify-center">
          <svg className="w-6 h-6 text-teal-100 animate-pulse" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" className="fill-teal-400/20 stroke-teal-300" />
            <path d="M9 12l2 2 4-4" className="stroke-white stroke-[2.5]" />
          </svg>
        </div>
      </div>
    );
  }
  if (isActive) {
    return (
      <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-teal-600 to-emerald-700 p-0.5 shadow-md shadow-teal-500/20 flex items-center justify-center ring-4 ring-teal-500/20">
        <svg className="w-5 h-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
          <polyline points="22 4 12 14.01 9 11.01" />
        </svg>
      </div>
    );
  }
  return (
    <div className="w-11 h-11 rounded-2xl bg-surface-200 dark:bg-surface-800 flex items-center justify-center text-surface-400 font-bold text-xs">
      02
    </div>
  );
}

function PicoStepperIcon({ isApproved, isActive }) {
  if (isApproved) {
    return (
      <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-purple-500 via-indigo-600 to-pink-500 p-0.5 shadow-lg shadow-purple-500/25 flex items-center justify-center transition-all duration-300 transform hover:scale-105">
        <div className="w-full h-full bg-slate-950/20 backdrop-blur-xs rounded-[14px] flex items-center justify-center">
          <svg className="w-6 h-6 text-pink-100 animate-pulse" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 3a9 9 0 0 1 9 9c0 3.87-2.45 7.17-5.9 8.44L12 21l-3.1-1.56A8.99 8.99 0 0 1 3 12a9 9 0 0 1 9-9z" className="fill-purple-400/25 stroke-purple-300" />
            <path d="M12 7v5l3 3" className="stroke-pink-200 stroke-[2]" />
            <circle cx="12" cy="12" r="1.5" className="fill-white" />
          </svg>
        </div>
      </div>
    );
  }
  if (isActive) {
    return (
      <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-indigo-600 to-purple-700 p-0.5 shadow-md shadow-indigo-500/20 flex items-center justify-center ring-4 ring-indigo-500/20">
        <Sparkles className="w-5 h-5 text-white animate-pulse" />
      </div>
    );
  }
  return (
    <div className="w-11 h-11 rounded-2xl bg-surface-200 dark:bg-surface-800 flex items-center justify-center text-surface-400 font-bold text-xs">
      03
    </div>
  );
}

export default function ResearchSetupTab({ setActiveTab }) {
  const { t, language } = useLanguage();
  const isVi = language === 'vi';
  const { activeProject, activeProjectId, updateProject, createProject } = useProject();
  const { token, currentUser } = useAuth();

  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);
  
  const [projectData, setProjectData] = useState(() => {
    return normalizeResearchSetup(activeProject || {});
  });

  const [newInclude, setNewInclude] = useState('');
  const [newExclude, setNewExclude] = useState('');

  // Human-in-the-Loop (HITL) Gate Statuses (Project-Scoped & Inferred)
  const [topicApproved, setTopicApproved] = useState(false);
  const [criteriaApproved, setCriteriaApproved] = useState(false);

  // State: Scope Review
  const [scopeResult, setScopeResult] = useState(null);
  const [loadingScope, setLoadingScope] = useState(false);
  const [appliedTopicToast, setAppliedTopicToast] = useState(null);

  // State: Criteria Suggestions
  const [loadingCriteria, setLoadingCriteria] = useState(false);
  const [criteriaToast, setCriteriaToast] = useState(false);

  // State: PICO & Keywords Finder
  const [suggestedKeywords, setSuggestedKeywords] = useState([]);
  const [picoData, setPicoData] = useState(null);
  const [gapMapData, setGapMapData] = useState(null);
  const [loadingKeywords, setLoadingKeywords] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [copiedKeywords, setCopiedKeywords] = useState(false);

  // DOM Refs for Smooth Auto-Scroll
  const scopeCardRef = useRef(null);
  const criteriaCardRef = useRef(null);
  const step3CardRef = useRef(null);
  const picoCardRef = useRef(null);

  const scrollToRef = (ref) => {
    setTimeout(() => {
      if (ref && ref.current) {
        ref.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }, 200);
  };

  // Sync state when activeProject changes or on initial page load / F5
  useEffect(() => {
    if (activeProject) {
      const normalized = normalizeResearchSetup(activeProject);
      setProjectData(normalized);

      const pId = activeProjectId || activeProject.id;
      const hasQuestion = Boolean(normalized.research_question && normalized.research_question.trim().length > 3);
      const hasCriteria = Boolean(normalized.criteria_include && normalized.criteria_include.length > 0);

      // Gate 1: Check localStorage first, or infer from saved research question
      const g1 = localStorage.getItem(`slr_gate1_topic_approved_${pId}`);
      const isGate1Done = g1 === 'true' || (g1 !== 'false' && hasQuestion);
      setTopicApproved(isGate1Done);

      // Gate 2: Check localStorage first, or infer from saved inclusion criteria
      const g2 = localStorage.getItem(`slr_gate2_criteria_approved_${pId}`);
      const isGate2Done = g2 === 'true' || (g2 !== 'false' && isGate1Done && hasCriteria);
      setCriteriaApproved(isGate2Done);

      try {
        const cachedScope = localStorage.getItem(`slr_scope_result_${pId}`);
        setScopeResult(cachedScope ? JSON.parse(cachedScope) : null);
      } catch { setScopeResult(null); }

      try {
        const cachedKw = localStorage.getItem(`suggested_keywords_${pId}`) || localStorage.getItem('suggested_keywords');
        setSuggestedKeywords(cachedKw ? JSON.parse(cachedKw) : []);
      } catch { setSuggestedKeywords([]); }

      try {
        const cachedPico = localStorage.getItem(`slr_pico_data_${pId}`) || (activeProject.pico ? activeProject.pico : null);
        setPicoData(cachedPico ? (typeof cachedPico === 'string' ? JSON.parse(cachedPico) : cachedPico) : null);
      } catch { setPicoData(null); }

      try {
        const cachedGap = localStorage.getItem(`slr_gap_map_${pId}`);
        setGapMapData(cachedGap ? JSON.parse(cachedGap) : null);
      } catch { setGapMapData(null); }

    } else {
      setProjectData(normalizeResearchSetup({}));
      setTopicApproved(false);
      setCriteriaApproved(false);
      setScopeResult(null);
      setSuggestedKeywords([]);
      setPicoData(null);
      setGapMapData(null);
    }
  }, [activeProjectId, activeProject]);

  const handleSave = async (updatedData = projectData, options = {}) => {
    setLoading(true);
    setSaved(false);
    setErrorMsg(null);
    try {
      const pId = activeProjectId || activeProject?.id;
      if (pId) {
        // 1. Update memory in ProjectContext
        if (updateProject) {
          await updateProject(pId, updatedData);
        }

        // 2. Persist to localStorage
        localStorage.setItem(`research_setup_data_${pId}`, JSON.stringify(updatedData));
        
        const g1Val = options.topicApproved !== undefined ? options.topicApproved : topicApproved;
        const g2Val = options.criteriaApproved !== undefined ? options.criteriaApproved : criteriaApproved;
        
        localStorage.setItem(`slr_gate1_topic_approved_${pId}`, g1Val ? 'true' : 'false');
        localStorage.setItem(`slr_gate2_criteria_approved_${pId}`, g2Val ? 'true' : 'false');

        // 3. Sync to backend API
        const res = await fetch(`${API_BASE}/projects/${pId}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify(updatedData)
        });

        if (res.ok) {
          setSaved(true);
          setTimeout(() => setSaved(false), 3000);
        } else {
          setSaved(true);
          setTimeout(() => setSaved(false), 3000);
        }
      } else {
        const created = await createProject(updatedData);
        if (created) {
          setSaved(true);
          setTimeout(() => setSaved(false), 3000);
        }
      }
    } catch (err) {
      console.error(err);
      setErrorMsg(isVi ? 'Lỗi kết nối máy chủ' : 'Server connection error');
    } finally {
      setLoading(false);
    }
  };

  // Agent 1: Scope Optimization
  const handleOptimizeScope = async () => {
    setLoadingScope(true);
    setErrorMsg(null);
    try {
      const ideaText = projectData.research_question || projectData.name || '';
      if (!ideaText.trim()) {
        setErrorMsg(isVi ? 'Vui lòng nhập tên đề tài hoặc câu hỏi nghiên cứu trước khi nhận xét.' : 'Please enter research question or project name first.');
        setLoadingScope(false);
        return;
      }

      const res = await fetch(`${API_BASE}/slr-swarm/optimize-scope`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          idea: ideaText,
          research_field: projectData.research_field || ''
        })
      });
      if (res.ok) {
        const data = await res.json();
        setScopeResult(data);
        const pId = activeProjectId || activeProject?.id;
        if (pId) {
          localStorage.setItem(`slr_scope_result_${pId}`, JSON.stringify(data));
        }
        scrollToRef(scopeCardRef);
      } else {
        setErrorMsg(isVi ? 'Không thể nhận xét phạm vi đề tài lúc này.' : 'Failed to analyze topic scope.');
      }
    } catch (err) {
      console.error(err);
      setErrorMsg(isVi ? 'Lỗi kết nối máy chủ' : 'Server connection error');
    } finally {
      setLoadingScope(false);
    }
  };

  const handleApplyTopic = (topic) => {
    const updated = { ...projectData, research_question: topic };
    setProjectData(updated);
    setAppliedTopicToast(topic);
    setTimeout(() => setAppliedTopicToast(null), 3000);
  };

  const handleApproveTopic = async (customTopic = null) => {
    const updatedQuestion = customTopic || projectData.research_question || projectData.name;
    const updated = { ...projectData, research_question: updatedQuestion };
    setProjectData(updated);
    setTopicApproved(true);
    const pId = activeProjectId || activeProject?.id;
    if (pId) {
      localStorage.setItem(`slr_gate1_topic_approved_${pId}`, 'true');
    }
    await handleSave(updated, { topicApproved: true });
    scrollToRef(criteriaCardRef);
  };

  // Agent 2: Suggested Criteria
  const handleGenerateCriteria = async () => {
    setLoadingCriteria(true);
    setErrorMsg(null);
    try {
      const ideaText = projectData.research_question || projectData.name || '';
      const res = await fetch(`${API_BASE}/slr-swarm/suggest-criteria`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          idea: ideaText,
          research_field: projectData.research_field || ''
        })
      });
      if (res.ok) {
        const data = await res.json();
        const updated = {
          ...projectData,
          criteria_include: data.criteria_include || projectData.criteria_include,
          criteria_exclude: data.criteria_exclude || projectData.criteria_exclude
        };
        setProjectData(updated);
        setCriteriaToast(true);
        setTimeout(() => setCriteriaToast(false), 3000);
      } else {
        setErrorMsg(isVi ? 'Không thể sinh tiêu chí gợi ý lúc này.' : 'Failed to generate criteria.');
      }
    } catch (err) {
      console.error(err);
      setErrorMsg(isVi ? 'Lỗi kết nối máy chủ' : 'Server connection error');
    } finally {
      setLoadingCriteria(false);
    }
  };

  const handleApproveCriteria = async () => {
    setCriteriaApproved(true);
    const pId = activeProjectId || activeProject?.id;
    if (pId) {
      localStorage.setItem(`slr_gate2_criteria_approved_${pId}`, 'true');
    }
    await handleSave(projectData, { topicApproved: true, criteriaApproved: true });
    scrollToRef(step3CardRef);
  };

  // Agent 3: PICO & Keywords (Tra cứu)
  const handleSuggestKeywords = async () => {
    setLoadingKeywords(true);
    setErrorMsg(null);
    try {
      const ideaText = projectData.research_question || projectData.name || '';
      if (!ideaText.trim()) {
        setErrorMsg(isVi ? 'Vui lòng nhập câu hỏi nghiên cứu hoặc tên đề tài ở Bước 1.' : 'Please enter research question or topic at Step 1.');
        setLoadingKeywords(false);
        return;
      }
      
      const res = await fetch(`${API_BASE}/slr-swarm/step1-setup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          idea: ideaText,
          research_field: projectData.research_field || '',
          criteria_include: projectData.criteria_include || [],
          criteria_exclude: projectData.criteria_exclude || []
        })
      });
      if (res.ok) {
        const data = await res.json();
        if (data.error && !data.pico) {
          setErrorMsg(isVi ? `Lỗi: ${data.error}` : `Error: ${data.error}`);
          return;
        }
        
        if (data.pico) {
          setPicoData(data.pico);
          const pId = activeProjectId || activeProject?.id;
          if (pId) {
            localStorage.setItem(`slr_pico_data_${pId}`, JSON.stringify(data.pico));
          }
          
          const rawKws = data.pico.search_keywords || [];
          const kwList = rawKws.filter(kw => 
            kw && kw.trim().length >= 3 && /^[a-zA-Z0-9\s\-\/&.]+$/.test(kw.trim())
          );
          
          if (kwList.length > 0) {
            setSuggestedKeywords(kwList);
            localStorage.setItem('suggested_keywords', JSON.stringify(kwList));
            if (pId) {
              localStorage.setItem(`suggested_keywords_${pId}`, JSON.stringify(kwList));
            }
          }
          
          const boolQuery = kwList.length > 0 ? kwList.join(' ') : (data.pico.boolean_query || '');
          if (boolQuery) {
             localStorage.setItem('litreview_active_mesh_query', boolQuery);
             localStorage.setItem('last_search_query', boolQuery);
             if (pId) {
               localStorage.setItem(`litreview_active_mesh_query_${pId}`, boolQuery);
               localStorage.setItem(`last_search_query_${pId}`, boolQuery);
             }
             window.dispatchEvent(new Event('new_mesh_query_ready'));
          }

          scrollToRef(picoCardRef);
        }
        
        if (data.gap_map) {
          const pId = activeProjectId || activeProject?.id;
          setGapMapData(data.gap_map);
          if (pId) {
            localStorage.setItem(`slr_gap_map_${pId}`, JSON.stringify(data.gap_map));
          }
        }

      } else {
        setErrorMsg(isVi ? 'Không thể tra cứu PICO lúc này.' : 'Failed to synthesize PICO.');
      }
    } catch (err) {
      console.error(err);
      setErrorMsg(isVi ? 'Lỗi kết nối máy chủ' : 'Server connection error');
    } finally {
      setLoadingKeywords(false);
    }
  };

  const handleProceedToSearch = () => {
    if (picoData?.search_keywords && picoData.search_keywords.length > 0) {
      const kws = picoData.search_keywords.filter(kw => kw && kw.trim().length >= 3);
      localStorage.setItem('suggested_keywords', JSON.stringify(kws));
      localStorage.setItem('last_search_query', kws.join(' '));
      window.dispatchEvent(new Event('new_mesh_query_ready'));
    }
    setActiveTab('search');
  };

  const handleCopyKeywords = () => {
    if (picoData?.search_keywords) {
      navigator.clipboard.writeText(picoData.search_keywords.join(' '));
      setCopiedKeywords(true);
      setTimeout(() => setCopiedKeywords(false), 2500);
    }
  };

  const addInclude = () => {
    if (newInclude.trim()) {
      setProjectData(p => ({ ...p, criteria_include: [...p.criteria_include, newInclude.trim()] }));
      setNewInclude('');
    }
  };

  const addExclude = () => {
    if (newExclude.trim()) {
      setProjectData(p => ({ ...p, criteria_exclude: [...p.criteria_exclude, newExclude.trim()] }));
      setNewExclude('');
    }
  };

  return (
    <div className="space-y-8 pb-24 max-w-5xl mx-auto px-4 sm:px-6">
      
      {/* ── Page Header ─────────────────────────────────────────────────── */}
      <div className="pt-2">
        <h1 className="font-display font-bold text-2xl sm:text-3xl text-surface-900 dark:text-white tracking-tight">
          {isVi ? 'Cấu hình Đề tài Nghiên cứu' : 'Research Setup'}
        </h1>
        <p className="text-sm text-surface-500 dark:text-surface-400 mt-1">
          {isVi 
            ? 'Thiết lập đề tài, tiêu chí chọn lọc và bộ từ khóa tìm kiếm học thuật cho nghiên cứu của bạn.' 
            : 'Define your research topic, screening criteria, and academic search keywords for your study.'}
        </p>
      </div>

      {/* ── Visual Stepper with Illustrated Animated Badges ─────────────── */}
      <div className="card p-4 sm:p-5 border-surface-200/80 dark:border-surface-800 shadow-sm bg-surface-50/50 dark:bg-surface-850/50 backdrop-blur-sm">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 relative">
          
          {/* Step 1 Indicator */}
          <div 
            onClick={() => scrollToRef({ current: document.getElementById('section-topic-info') })}
            className="flex items-center gap-3.5 group cursor-pointer"
          >
            <TopicStepperIcon isApproved={topicApproved} isActive={!topicApproved} />
            <div className="min-w-0">
              <p className="text-xs font-bold text-surface-900 dark:text-white uppercase tracking-wider truncate group-hover:text-primary-500 transition-colors">
                {isVi ? 'Định hình đề tài' : 'Topic Scope'}
              </p>
              <p className="text-[11px] font-semibold truncate mt-0.5 flex items-center gap-1 text-cyan-600 dark:text-cyan-400">
                {topicApproved ? (isVi ? '🎯 Đã định hình' : '🎯 Topic Defined') : (isVi ? '💡 Đang thiết lập' : '💡 In Progress')}
              </p>
            </div>
          </div>

          {/* Step 2 Indicator */}
          <div 
            onClick={() => topicApproved && scrollToRef(criteriaCardRef)}
            className={`flex items-center gap-3.5 group ${topicApproved ? 'cursor-pointer' : 'opacity-60'}`}
          >
            <CriteriaStepperIcon isApproved={criteriaApproved} isActive={topicApproved && !criteriaApproved} />
            <div className="min-w-0">
              <p className="text-xs font-bold text-surface-900 dark:text-white uppercase tracking-wider truncate group-hover:text-teal-500 transition-colors">
                {isVi ? 'Tiêu chí sàng lọc' : 'Screening Criteria'}
              </p>
              <p className="text-[11px] font-semibold truncate mt-0.5 flex items-center gap-1 text-teal-600 dark:text-teal-400">
                {criteriaApproved 
                  ? (isVi ? '🛡️ Đã có tiêu chí' : '🛡️ Criteria Set') 
                  : topicApproved 
                  ? (isVi ? '📋 Thiết lập tiêu chí' : '📋 In Progress') 
                  : (isVi ? '⏳ Chưa mở' : '⏳ Pending')}
              </p>
            </div>
          </div>

          {/* Step 3 Indicator */}
          <div 
            onClick={() => criteriaApproved && scrollToRef(step3CardRef)}
            className={`flex items-center gap-3.5 group ${criteriaApproved ? 'cursor-pointer' : 'opacity-60'}`}
          >
            <PicoStepperIcon isApproved={Boolean(picoData)} isActive={criteriaApproved && !picoData} />
            <div className="min-w-0">
              <p className="text-xs font-bold text-surface-900 dark:text-white uppercase tracking-wider truncate group-hover:text-purple-500 transition-colors">
                {isVi ? 'PICO & Từ khóa' : 'PICO & Keywords'}
              </p>
              <p className="text-[11px] font-semibold truncate mt-0.5 flex items-center gap-1 text-purple-600 dark:text-purple-400">
                {picoData 
                  ? (isVi ? '🔬 Đã có bộ từ khóa' : '🔬 Synthesized') 
                  : criteriaApproved 
                  ? (isVi ? '✨ Sẵn sàng tra cứu' : '✨ Ready') 
                  : (isVi ? '⏳ Chưa mở' : '⏳ Pending')}
              </p>
            </div>
          </div>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3.5 rounded-2xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800/60 text-rose-700 dark:text-rose-300 text-xs sm:text-sm flex items-center gap-2.5 animate-slide-up shadow-xs">
          <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-500" />
          <span className="font-medium">{errorMsg}</span>
        </div>
      )}

      {/* ── SECTION 1: THÔNG TIN VỀ ĐỀ TÀI NGHIÊN CỨU ────────────────────── */}
      <div id="section-topic-info" className={`card p-6 sm:p-7 transition-all ${topicApproved ? 'border-cyan-200/80 dark:border-cyan-900/40 bg-cyan-50/10 dark:bg-cyan-950/5' : ''}`}>
        
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6 pb-4 border-b border-surface-100 dark:border-surface-800">
          <div>
            <h2 className="font-display font-bold text-lg text-surface-900 dark:text-white flex items-center gap-2">
              <span>{isVi ? 'Thông tin về đề tài nghiên cứu' : 'Research Topic Information'}</span>
              {topicApproved && (
                <span className="inline-flex items-center gap-1 text-[11px] font-bold text-cyan-700 dark:text-cyan-300 bg-cyan-100 dark:bg-cyan-950/60 px-2.5 py-0.5 rounded-full border border-cyan-200 dark:border-cyan-800 shadow-xs">
                  <Check className="w-3 h-3 stroke-[2.5]" /> {isVi ? 'Đã xác nhận' : 'Confirmed'}
                </span>
              )}
            </h2>
          </div>

          {topicApproved && (
            <button
              type="button"
              onClick={() => {
                setTopicApproved(false);
                const pId = activeProjectId || activeProject?.id;
                if (pId) localStorage.setItem(`slr_gate1_topic_approved_${pId}`, 'false');
              }}
              className="btn btn-sm btn-secondary self-start sm:self-auto flex items-center gap-1.5 font-semibold"
            >
              <Edit3 className="w-3.5 h-3.5 text-surface-500" />
              <span>{isVi ? 'Chỉnh sửa' : 'Edit'}</span>
            </button>
          )}
        </div>

        <div className="space-y-4">
          <div>
            <label className="section-label block mb-1.5 font-bold text-xs">
              {isVi ? 'Tên đề tài nghiên cứu' : 'Project Name'}
            </label>
            <input 
              type="text" 
              value={projectData.name}
              onChange={e => setProjectData({...projectData, name: e.target.value})}
              placeholder={isVi ? 'Ví dụ: Đánh giá hiệu năng LLM cho Robot di động...' : 'E.g., Benchmarking Open Source LLMs for Mobile Robots...'}
              disabled={topicApproved}
              className="input input-sm disabled:opacity-60 font-medium"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="section-label block mb-1.5 font-bold text-xs">
                {isVi ? 'Câu hỏi / Ý tưởng nghiên cứu chính' : 'Main Research Question / Focus'}
              </label>
              <textarea 
                rows="4"
                value={projectData.research_question}
                onChange={e => setProjectData({...projectData, research_question: e.target.value})}
                placeholder={isVi ? 'Nhập câu hỏi hoặc bài toán nghiên cứu cốt lõi mà bạn muốn khám phá...' : 'Describe your core research question or problem statement...'}
                disabled={topicApproved}
                className="input input-sm disabled:opacity-60 resize-none font-medium text-xs leading-relaxed"
              />
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="section-label block mb-1.5 font-bold text-xs">
                  {isVi ? 'Lĩnh vực nghiên cứu' : 'Research Field'}
                </label>
                <select
                  value={projectData.research_field}
                  onChange={e => setProjectData({...projectData, research_field: e.target.value})}
                  disabled={topicApproved}
                  className="input input-sm disabled:opacity-60 cursor-pointer appearance-none font-medium text-xs"
                >
                  <option value="">{isVi ? '-- Chọn lĩnh vực nghiên cứu chuyên sâu --' : '-- Select research domain --'}</option>
                  <option value="Toán học & Tối ưu hóa">{isVi ? 'Toán học & Tối ưu hóa' : 'Mathematics & Optimization'}</option>
                  <option value="Y tế & Chẩn đoán Y sinh">{isVi ? 'Y tế & Chẩn đoán Y sinh' : 'Healthcare & Biomedicine'}</option>
                  <option value="Robotics & Tự hành">{isVi ? 'Robotics & Tự hành' : 'Robotics & Autonomous Systems'}</option>
                  <option value="Khác">{isVi ? 'Khác / Tổng quan' : 'General Academic'}</option>
                </select>
              </div>

              <div className="flex gap-3">
                <div className="flex-1">
                  <label className="section-label block mb-1.5 font-bold text-xs">
                    {isVi ? 'Từ năm' : 'From Year'}
                  </label>
                  <input
                    type="number"
                    disabled={topicApproved}
                    value={projectData.year_from || 2018}
                    onChange={e => setProjectData({...projectData, year_from: parseInt(e.target.value) || 2018})}
                    className="input input-sm disabled:opacity-60 font-medium"
                  />
                </div>
                <div className="flex-1">
                  <label className="section-label block mb-1.5 font-bold text-xs">
                    {isVi ? 'Đến năm' : 'To Year'}
                  </label>
                  <input
                    type="number"
                    disabled={topicApproved}
                    value={projectData.year_to || 2026}
                    onChange={e => setProjectData({...projectData, year_to: parseInt(e.target.value) || 2026})}
                    className="input input-sm disabled:opacity-60 font-medium"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Action buttons at end of Step 1 */}
          {!topicApproved && (
            <div className="pt-4 mt-4 border-t border-surface-100 dark:border-surface-800 flex flex-col sm:flex-row items-center justify-between gap-3">
              <button
                type="button"
                onClick={handleOptimizeScope}
                disabled={loadingScope}
                className="btn btn-secondary w-full sm:w-auto flex items-center gap-2 font-semibold"
              >
                {loadingScope ? <Loader2 className="w-4 h-4 animate-spin text-primary-500" /> : <Compass className="w-4 h-4 text-cyan-500" />}
                <span>{isVi ? 'Nhận xét về phạm vi đề tài' : 'Review Topic Scope'}</span>
              </button>

              <button
                type="button"
                onClick={() => handleApproveTopic()}
                disabled={loading}
                className="btn btn-primary w-full sm:w-auto flex items-center gap-2 shadow-primary-sm font-bold"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                <span>{isVi ? 'Lưu & Chuyển sang bước tiếp theo' : 'Save & Continue'}</span>
                <ArrowRight className="w-4 h-4 ml-1" />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ── TOPIC SCOPE FEEDBACK CARD ────────────────────────────────────── */}
      {scopeResult && !topicApproved && (
        <div ref={scopeCardRef} className="card p-6 border-cyan-200 dark:border-cyan-800/80 bg-cyan-50/20 dark:bg-cyan-950/20 space-y-4 animate-slide-up shadow-sm">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-cyan-100 dark:bg-cyan-900/60 flex items-center justify-center text-cyan-600 dark:text-cyan-300">
                <Compass className="w-5 h-5 animate-spin-slow" />
              </div>
              <h3 className="font-display font-bold text-sm text-surface-900 dark:text-white">
                {isVi ? 'Nhận xét về phạm vi đề tài' : 'Topic Scope Assessment'}
              </h3>
            </div>
            
            <span className={`badge text-xs font-bold ${
              scopeResult.status === 'optimal' ? 'badge-success' :
              scopeResult.status === 'too_narrow' ? 'badge-primary' : 'badge-warning'
            }`}>
              {scopeResult.status === 'optimal' 
                ? (isVi ? '✨ Phạm vi tối ưu' : '✨ Optimal Scope')
                : scopeResult.status === 'too_narrow' 
                ? (isVi ? '🔍 Đề tài quá hẹp' : '🔍 Too Narrow')
                : (isVi ? '⚠️ Đề tài quá rộng' : '⚠️ Too Broad')}
            </span>
          </div>

          <p className="text-xs sm:text-sm text-surface-700 dark:text-surface-300 leading-relaxed bg-white dark:bg-surface-800 p-4 rounded-xl border border-surface-200 dark:border-surface-700 shadow-xs font-medium">
            {scopeResult.feedback}
          </p>

          {scopeResult.suggested_topics && scopeResult.suggested_topics.length > 0 && (
            <div className="space-y-2.5 pt-1">
              <p className="section-label text-surface-600 dark:text-surface-400 font-bold text-xs">
                {isVi ? 'Gợi ý tinh chỉnh đề tài sắc bén hơn:' : 'Suggested Refinements:'}
              </p>
              <div className="grid gap-2.5">
                {scopeResult.suggested_topics.map((topic, i) => (
                  <div key={i} className="p-3.5 rounded-xl bg-white dark:bg-surface-800 border border-surface-200 dark:border-surface-700 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:border-cyan-300 dark:hover:border-cyan-700 transition-colors shadow-xs">
                    <span className="text-xs font-medium text-surface-800 dark:text-surface-200 leading-relaxed">{topic}</span>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <button
                        onClick={() => handleApplyTopic(topic)}
                        className="btn btn-sm btn-ghost text-xs hover:bg-surface-100 dark:hover:bg-surface-700 font-semibold"
                      >
                        {isVi ? 'Áp dụng' : 'Apply'}
                      </button>
                      <button
                        onClick={() => handleApproveTopic(topic)}
                        className="btn btn-sm btn-primary text-xs font-bold"
                      >
                        {isVi ? 'Lưu & Tiếp tục' : 'Save & Continue'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── SECTION 2: TIÊU CHÍ SÀNG LỌC ─────────────────────────────────── */}
      {topicApproved && (
        <div ref={criteriaCardRef} className={`card p-6 sm:p-7 transition-all animate-slide-up ${criteriaApproved ? 'border-teal-200/80 dark:border-teal-900/40 bg-teal-50/10 dark:bg-teal-950/5' : ''}`}>
          
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6 pb-4 border-b border-surface-100 dark:border-surface-800">
            <div>
              <h2 className="font-display font-bold text-lg text-surface-900 dark:text-white flex items-center gap-2">
                <span>{isVi ? 'Tiêu chí sàng lọc' : 'Screening Criteria'}</span>
                {criteriaApproved && (
                  <span className="inline-flex items-center gap-1 text-[11px] font-bold text-teal-700 dark:text-teal-300 bg-teal-100 dark:bg-teal-950/60 px-2.5 py-0.5 rounded-full border border-teal-200 dark:border-teal-800 shadow-xs">
                    <Check className="w-3 h-3 stroke-[2.5]" /> {isVi ? 'Đã xác nhận' : 'Confirmed'}
                  </span>
                )}
              </h2>
            </div>

            <div className="flex items-center gap-2">
              {criteriaApproved ? (
                <button
                  type="button"
                  onClick={() => {
                    setCriteriaApproved(false);
                    const pId = activeProjectId || activeProject?.id;
                    if (pId) localStorage.setItem(`slr_gate2_criteria_approved_${pId}`, 'false');
                  }}
                  className="btn btn-sm btn-secondary flex items-center gap-1.5 font-semibold"
                >
                  <Edit3 className="w-3.5 h-3.5 text-surface-500" />
                  <span>{isVi ? 'Chỉnh sửa' : 'Edit'}</span>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleGenerateCriteria}
                  disabled={loadingCriteria}
                  className="btn btn-sm btn-secondary flex items-center gap-1.5 font-semibold"
                >
                  {loadingCriteria ? <Loader2 className="w-3.5 h-3.5 animate-spin text-teal-500" /> : <Sparkles className="w-3.5 h-3.5 text-teal-500" />}
                  <span>{isVi ? 'Các tiêu chí gợi ý' : 'Suggested Criteria'}</span>
                </button>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* INCLUSION CRITERIA */}
            <div className="space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-surface-100 dark:border-surface-800">
                <h4 className="font-bold text-xs text-emerald-600 dark:text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>{isVi ? 'Tiêu chí chọn vào (Inclusion)' : 'Inclusion Criteria'}</span>
                </h4>
                <span className="badge badge-success text-[10px] font-bold">
                  {projectData.criteria_include.length}
                </span>
              </div>
              
              {!criteriaApproved && (
                <div className="flex gap-2">
                  <input 
                    type="text" 
                    value={newInclude} 
                    onChange={e => setNewInclude(e.target.value)} 
                    onKeyDown={e => e.key === 'Enter' && addInclude()}
                    placeholder={isVi ? 'Thêm tiêu chí chọn...' : 'Add inclusion criterion...'}
                    className="input input-sm flex-1 font-medium"
                  />
                  <button onClick={addInclude} className="btn btn-sm btn-secondary px-3">
                    <Plus className="w-4 h-4"/>
                  </button>
                </div>
              )}
              
              <ul className="space-y-2">
                {projectData.criteria_include.map((item, idx) => (
                  <li key={idx} className="group flex justify-between items-start bg-emerald-50/50 dark:bg-emerald-950/20 p-3 rounded-xl text-xs font-medium border border-emerald-100 dark:border-emerald-900/30 text-surface-700 dark:text-surface-300">
                    <span className="pr-3 leading-relaxed">{item}</span>
                    {!criteriaApproved && (
                      <button onClick={() => setProjectData(p => ({...p, criteria_include: p.criteria_include.filter((_, i) => i !== idx)}))} className="text-surface-400 hover:text-rose-500 transition-colors opacity-0 group-hover:opacity-100 flex-shrink-0">
                        <X className="w-3.5 h-3.5"/>
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            </div>

            {/* EXCLUSION CRITERIA */}
            <div className="space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-surface-100 dark:border-surface-800">
                <h4 className="font-bold text-xs text-rose-600 dark:text-rose-400 uppercase tracking-wider flex items-center gap-1.5">
                  <AlertCircle className="w-4 h-4" />
                  <span>{isVi ? 'Tiêu chí loại trừ (Exclusion)' : 'Exclusion Criteria'}</span>
                </h4>
                <span className="badge badge-danger text-[10px] font-bold">
                  {projectData.criteria_exclude.length}
                </span>
              </div>
              
              {!criteriaApproved && (
                <div className="flex gap-2">
                  <input 
                    type="text" 
                    value={newExclude} 
                    onChange={e => setNewExclude(e.target.value)} 
                    onKeyDown={e => e.key === 'Enter' && addExclude()}
                    placeholder={isVi ? 'Thêm tiêu chí loại...' : 'Add exclusion criterion...'}
                    className="input input-sm flex-1 font-medium"
                  />
                  <button onClick={addExclude} className="btn btn-sm btn-secondary px-3">
                    <Plus className="w-4 h-4"/>
                  </button>
                </div>
              )}
              
              <ul className="space-y-2">
                {projectData.criteria_exclude.map((item, idx) => (
                  <li key={idx} className="group flex justify-between items-start bg-rose-50/50 dark:bg-rose-950/20 p-3 rounded-xl text-xs font-medium border border-rose-100 dark:border-rose-900/30 text-surface-700 dark:text-surface-300">
                    <span className="pr-3 leading-relaxed">{item}</span>
                    {!criteriaApproved && (
                      <button onClick={() => setProjectData(p => ({...p, criteria_exclude: p.criteria_exclude.filter((_, i) => i !== idx)}))} className="text-surface-400 hover:text-rose-500 transition-colors opacity-0 group-hover:opacity-100 flex-shrink-0">
                        <X className="w-3.5 h-3.5"/>
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Action buttons at end of Step 2 */}
          {!criteriaApproved && (
            <div className="pt-4 mt-6 border-t border-surface-100 dark:border-surface-800 flex flex-col sm:flex-row items-center justify-between gap-3">
              <button
                type="button"
                onClick={() => scrollToRef({ current: document.getElementById('section-topic-info') })}
                className="btn btn-secondary w-full sm:w-auto flex items-center justify-center gap-2 font-semibold"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>{isVi ? 'Quay lại Bước 1: Đề tài' : 'Back to Step 1: Topic'}</span>
              </button>

              <button 
                type="button" 
                onClick={handleApproveCriteria} 
                disabled={loading}
                className="btn btn-primary w-full sm:w-auto shadow-primary-sm font-bold flex items-center justify-center gap-2"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
                <span>{isVi ? 'Lưu & Chuyển sang bước tiếp theo' : 'Save & Continue to PICO'}</span>
                <ArrowRight className="w-4 h-4 ml-1" />
              </button>
            </div>
          )}
        </div>
      )}

      {/* ── SECTION 3: PHÂN TÍCH KHUNG PICO VÀ BỘ TỪ KHÓA TÌM KIẾM ────────── */}
      {criteriaApproved && (
        <div ref={step3CardRef} className="space-y-6 animate-slide-up">
          
          {/* Quick Back to Step 2 Link */}
          <div className="flex justify-start">
            <button
              type="button"
              onClick={() => scrollToRef(criteriaCardRef)}
              className="btn btn-sm btn-ghost text-xs text-surface-500 hover:text-surface-900 dark:hover:text-white flex items-center gap-1.5 font-semibold"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>{isVi ? 'Quay lại Bước 2: Tiêu chí sàng lọc' : 'Back to Step 2: Criteria'}</span>
            </button>
          </div>

          <div className="card p-7 sm:p-9 text-center rounded-3xl bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-950 text-white space-y-5 shadow-2xl border border-indigo-500/20">
            <div className="w-14 h-14 mx-auto rounded-2xl bg-indigo-500/15 border border-indigo-400/20 flex items-center justify-center shadow-inner">
              <svg className="w-7 h-7 text-indigo-300 animate-pulse" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 3a9 9 0 0 1 9 9c0 3.87-2.45 7.17-5.9 8.44L12 21l-3.1-1.56A8.99 8.99 0 0 1 3 12a9 9 0 0 1 9-9z" className="fill-indigo-400/25 stroke-indigo-300" />
                <path d="M12 7v5l3 3" className="stroke-indigo-200 stroke-[2]" />
                <circle cx="12" cy="12" r="1.5" className="fill-white" />
              </svg>
            </div>
            
            <div className="max-w-2xl mx-auto space-y-2">
              <h3 className="font-display font-bold text-xl sm:text-2xl text-white tracking-tight">
                {isVi ? 'Phân tích Khung PICO và bộ từ khóa tìm kiếm' : 'PICO Framework & Academic Search Keywords'}
              </h3>
              <p className="text-xs sm:text-sm text-slate-300 leading-relaxed font-medium">
                {isVi 
                  ? 'Khung PICO (Đối tượng, Can thiệp, So sánh, Kết quả) giúp cấu trúc hóa câu hỏi nghiên cứu và trích xuất các từ khóa học thuật tiếng Anh chuẩn xác nhất để tìm kiếm bài báo trên Google Scholar & Scopus.'
                  : 'The PICO framework (Population, Intervention, Comparison, Outcome) structures your research question and extracts the most accurate academic search keywords for literature discovery.'}
              </p>
            </div>
            
            <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
              <button 
                onClick={handleSuggestKeywords} 
                disabled={loadingKeywords}
                className="btn bg-white text-slate-900 hover:bg-slate-100 hover:scale-105 transition-all text-sm font-bold shadow-xl px-7 py-3 rounded-2xl flex items-center gap-2 cursor-pointer"
              >
                {loadingKeywords ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
                    <span>{isVi ? 'Thinking... Đang phân tích & tra cứu' : 'Thinking... Analyzing & Synthesizing'}</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4 text-amber-500" />
                    <span>{picoData ? (isVi ? 'Tra cứu lại' : 'Re-synthesize') : (isVi ? 'Tra cứu' : 'Synthesize')}</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {picoData && (
            <div ref={picoCardRef} className="card p-6 sm:p-8 space-y-6 animate-slide-up border-purple-500/20 bg-purple-500/5 shadow-md">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-surface-200 dark:border-surface-800">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-2xl bg-purple-100 dark:bg-purple-950/60 border border-purple-500/30 flex items-center justify-center text-purple-600 dark:text-purple-300 shadow-xs">
                    <Sparkles className="w-5 h-5 animate-pulse" />
                  </div>
                  <div>
                    <h4 className="font-display font-bold text-lg text-surface-900 dark:text-white">
                      {isVi ? 'Kết quả phân tích Khung PICO' : 'PICO Analysis Results'}
                    </h4>
                    <p className="text-xs text-surface-500 dark:text-surface-400 font-medium">
                      {isVi ? 'Đã phân tích và tra cứu thành công' : 'Analysis and synthesis completed successfully'}
                    </p>
                  </div>
                </div>

                {/* Top Right Save Configuration & Analysis Button (Prominent & Clear) */}
                <button 
                  type="button"
                  onClick={() => handleSave()}
                  disabled={loading}
                  className="btn bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white self-start sm:self-auto flex items-center gap-2 font-bold shadow-md shadow-emerald-500/20 px-4 py-2.5 rounded-xl border border-emerald-400/30 transition-all hover:scale-105"
                >
                  {saved ? (
                    <>
                      <Check className="w-4 h-4 stroke-[2.5]" />
                      <span>{isVi ? 'Đã lưu cấu hình!' : 'Configuration Saved!'}</span>
                    </>
                  ) : (
                    <>
                      {loading ? <Loader2 className="w-4 h-4 animate-spin text-white" /> : <Save className="w-4 h-4 text-white" />}
                      <span>{isVi ? 'Lưu Cấu hình & Phân tích' : 'Save Setup & Analysis'}</span>
                    </>
                  )}
                </button>
              </div>

              {/* 4 PICO Blocks */}
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
                <div className="p-4 rounded-2xl bg-white dark:bg-surface-800/90 border border-primary-100 dark:border-primary-900/30 shadow-xs space-y-1.5">
                  <span className="section-label text-primary-600 dark:text-primary-400 block font-bold text-xs">
                    [P] {isVi ? 'Đối tượng nghiên cứu' : 'Population / Problem'}:
                  </span>
                  <p className="text-xs font-semibold text-surface-900 dark:text-surface-100 leading-relaxed">
                    {picoData.population || 'N/A'}
                  </p>
                </div>

                <div className="p-4 rounded-2xl bg-white dark:bg-surface-800/90 border border-indigo-100 dark:border-indigo-900/30 shadow-xs space-y-1.5">
                  <span className="section-label text-indigo-600 dark:text-indigo-400 block font-bold text-xs">
                    [I] {isVi ? 'Giải pháp & Phương pháp' : 'Intervention / Method'}:
                  </span>
                  <p className="text-xs font-semibold text-surface-900 dark:text-surface-100 leading-relaxed">
                    {picoData.intervention || 'N/A'}
                  </p>
                </div>

                <div className="p-4 rounded-2xl bg-white dark:bg-surface-800/90 border border-amber-100 dark:border-amber-900/30 shadow-xs space-y-1.5">
                  <span className="section-label text-amber-600 dark:text-amber-400 block font-bold text-xs">
                    [C] {isVi ? 'Tiêu chuẩn đối chiếu' : 'Comparison'}:
                  </span>
                  <p className="text-xs font-semibold text-surface-900 dark:text-surface-100 leading-relaxed">
                    {picoData.comparison || 'N/A'}
                  </p>
                </div>

                <div className="p-4 rounded-2xl bg-white dark:bg-surface-800/90 border border-emerald-100 dark:border-emerald-900/30 shadow-xs space-y-1.5">
                  <span className="section-label text-emerald-600 dark:text-emerald-400 block font-bold text-xs">
                    [O] {isVi ? 'Kết quả kỳ vọng' : 'Outcome'}:
                  </span>
                  <p className="text-xs font-semibold text-surface-900 dark:text-surface-100 leading-relaxed">
                    {picoData.outcome || 'N/A'}
                  </p>
                </div>
              </div>

              {/* Keywords & Boolean Query Container */}
              <div className="p-5 sm:p-6 rounded-2xl bg-surface-900 dark:bg-surface-950 text-white space-y-4 shadow-xl border border-surface-800">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-white/10">
                  <span className="text-xs font-bold uppercase tracking-wider text-primary-300 flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-amber-400" />
                    {isVi ? 'Bộ từ khóa học thuật đề xuất' : 'Academic Search Keywords'}
                  </span>

                  {picoData.search_keywords && picoData.search_keywords.length > 0 && (
                    <button
                      onClick={handleCopyKeywords}
                      className="btn btn-sm btn-ghost text-xs text-white hover:bg-white/10 self-start sm:self-auto flex items-center gap-1.5 font-semibold"
                    >
                      {copiedKeywords ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copiedKeywords ? (isVi ? 'Đã sao chép!' : 'Copied!') : (isVi ? 'Sao chép chuỗi tìm kiếm' : 'Copy Search String')}</span>
                    </button>
                  )}
                </div>

                <div className="flex flex-wrap gap-2.5">
                  {(picoData.search_keywords || []).map((kw, i) => (
                    <span 
                      key={i} 
                      className="px-3.5 py-1.5 rounded-xl bg-primary-500/20 text-primary-200 text-xs font-semibold border border-primary-500/30 shadow-xs"
                    >
                      {kw}
                    </span>
                  ))}
                </div>

                {/* Big Next Step Guidance */}
                <div className="pt-4 border-t border-white/10 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <p className="text-xs text-surface-400">
                    💡 <strong className="text-surface-200">{isVi ? 'Bước tiếp theo:' : 'Next Step:'}</strong> {isVi 
                      ? 'Nhấn nút bên cạnh để chuyển sang tab Tìm kiếm. Toàn bộ từ khóa sẽ được tự động điền vào thanh tìm kiếm.' 
                      : 'Click the button to switch to the Search tab. All keywords will be auto-filled into the search bar.'}
                  </p>

                  <button 
                    onClick={handleProceedToSearch}
                    className="btn btn-primary btn-lg font-bold shrink-0 flex items-center justify-center gap-2 shadow-primary-md"
                  >
                    <span>{isVi ? 'Tiến hành Tìm kiếm Bài báo' : 'Proceed to Search Papers'}</span>
                    <ArrowRight className="w-5 h-5" />
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
