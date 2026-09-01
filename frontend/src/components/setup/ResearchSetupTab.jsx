import React, { useState, useEffect, useRef } from 'react';
import { 
  BookOpen, Target, Settings, Save, Loader2, Plus, X, 
  CheckCircle2, Compass, AlertCircle, ArrowRight, ArrowLeft, Check,
  ShieldCheck, Edit3, Copy, Search, BrainCircuit,
  ChevronRight, Layers, FileCheck, HelpCircle, Lightbulb,
  CheckCheck, Bookmark, ArrowUpRight, Filter, Zap, Download
} from 'lucide-react';
import { normalizeResearchSetup } from '../../utils/researchSetup';
import { downloadSetupFrameworkMarkdown } from '../../utils/exportUtils';
import { useLanguage } from '../../contexts/LanguageContext';
import { useProject } from '../../contexts/ProjectContext';
import { useAuth } from '../../contexts/AuthContext';
import { API_BASE, safeFetch } from '../../utils/apiConfig';

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
        <Compass className="w-5 h-5 text-white animate-spin-slow" />
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
        <BrainCircuit className="w-5 h-5 text-white animate-pulse" />
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
  const [activeStep, setActiveStep] = useState(1);
  const [topicApproved, setTopicApproved] = useState(false);
  const [criteriaApproved, setCriteriaApproved] = useState(false);
  const [isEditingTopicMeta, setIsEditingTopicMeta] = useState(false);

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
      // NOTE: previously cleared research_question here whenever it matched
      // the project name (meant to hide an old auto-fill placeholder), but
      // that had no way to tell "system auto-filled this" apart from "user
      // deliberately typed a question identical to the project name" -- a
      // real, not-uncommon case for short project names. Since this effect
      // reruns on every reload/project switch, it silently wiped a real
      // saved answer every time, and a Save right after would persist the
      // blank to the backend. Removed rather than guessed at a heuristic;
      // showing the real saved value is always correct, a placeholder is not.
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

      // activeStep defaults to 1 on every mount (useState(1) never persists),
      // so leaving/returning to this tab silently reset progress back to
      // step 1 even though topic/criteria were already approved and saved.
      // Restore the step that matches what's actually done, same as the
      // per-step "Đã duyệt" badges already reflect.
      if (isGate2Done) {
        setActiveStep(3);
      } else if (isGate1Done) {
        setActiveStep(2);
      } else {
        setActiveStep(1);
      }

      try {
        const cachedScope = localStorage.getItem(`slr_scope_result_${pId}`);
        setScopeResult(cachedScope ? JSON.parse(cachedScope) : null);
      } catch { setScopeResult(null); }

      try {
        const cachedKw = localStorage.getItem(`suggested_keywords_${pId}`);
        setSuggestedKeywords(cachedKw ? JSON.parse(cachedKw) : []);
      } catch { setSuggestedKeywords([]); }

      try {
        const cachedPico = localStorage.getItem(`slr_pico_data_${pId}`);
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
        const res = await safeFetch(`${API_BASE}/projects/${pId}`, {
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

      const res = await safeFetch('/slr-swarm/optimize-scope', {
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
    setActiveStep(2);
    await handleSave(updated, { topicApproved: true });
  };

  // Agent 2: Suggested Criteria
  const handleGenerateCriteria = async () => {
    setLoadingCriteria(true);
    setErrorMsg(null);
    try {
      const ideaText = projectData.research_question || projectData.name || '';
      const res = await safeFetch('/slr-swarm/suggest-criteria', {
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
    setActiveStep(3);
    await handleSave(projectData, { topicApproved: true, criteriaApproved: true });
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
      
      const res = await safeFetch('/slr-swarm/step1-setup', {
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
    <div id="tour-setup-main" className="space-y-6 pb-24 w-full max-w-7xl 2xl:max-w-[1600px] mx-auto px-2 sm:px-4 lg:px-6">
      
      {/* ── Page Header ─────────────────────────────────────────────────── */}
      <div className="pt-2">
        <h1 className="font-display font-bold text-xl sm:text-2xl lg:text-3xl text-surface-900 dark:text-white tracking-tight">
          {isVi ? 'Xây dựng khung đề tài nghiên cứu' : 'Research Setup Framework'}
        </h1>
        <p className="text-xs sm:text-sm text-surface-500 dark:text-surface-400 mt-1">
          {isVi 
            ? 'Thiết lập phạm vi đề tài, tiêu chí sàng lọc PRISMA và bộ từ khóa tìm kiếm học thuật cho nghiên cứu của bạn.' 
            : 'Define your research topic, screening criteria, and academic search keywords for your study.'}
        </p>
      </div>

      {/* ── 3 Process Stepper Tabs (Clickable to switch view) ───────────── */}
      <div id="tour-setup-stepper" className="card p-2 sm:p-2.5 border-surface-200/80 dark:border-surface-800 shadow-xs bg-surface-50/70 dark:bg-surface-850/70 backdrop-blur-sm">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 relative">
          
          {/* Step 1 Tab */}
          <button 
            type="button"
            onClick={() => setActiveStep(1)}
            className={`flex items-center gap-3 p-3 rounded-xl transition-all text-left cursor-pointer border ${
              activeStep === 1 
                ? 'bg-white dark:bg-slate-900 border-blue-500/50 shadow-sm ring-2 ring-blue-500/10' 
                : 'border-transparent hover:bg-white/60 dark:hover:bg-slate-900/60'
            }`}
          >
            <TopicStepperIcon isApproved={topicApproved} isActive={activeStep === 1} />
            <div className="min-w-0 flex-1">
              <p className={`text-xs font-bold uppercase tracking-wider truncate ${activeStep === 1 ? 'text-blue-600 dark:text-blue-400' : 'text-surface-900 dark:text-white'}`}>
                {isVi ? 'Định hình đề tài' : 'Topic Scope'}
              </p>
              <p className="text-[11px] font-semibold truncate mt-0.5 flex items-center gap-1 text-cyan-600 dark:text-cyan-400">
                {topicApproved ? (isVi ? '🎯 Đã định hình' : '🎯 Topic Defined') : (isVi ? '💡 Đang thiết lập' : '💡 In Progress')}
              </p>
            </div>
            {activeStep === 1 && <span className="w-2 h-2 rounded-full bg-blue-600 shrink-0 mr-1" />}
          </button>

          {/* Step 2 Tab */}
          <button 
            type="button"
            onClick={() => {
              if (topicApproved) {
                setActiveStep(2);
              } else {
                setErrorMsg(isVi ? 'Vui lòng lưu thông tin đề tài ở bước 1 trước khi sang bước 2.' : 'Please save Topic Scope in Step 1 first.');
              }
            }}
            className={`flex items-center gap-3 p-3 rounded-xl transition-all text-left border ${
              activeStep === 2 
                ? 'bg-white dark:bg-slate-900 border-teal-500/50 shadow-sm ring-2 ring-teal-500/10' 
                : 'border-transparent hover:bg-white/60 dark:hover:bg-slate-900/60'
            } ${topicApproved ? 'cursor-pointer' : 'opacity-50 cursor-not-allowed'}`}
          >
            <CriteriaStepperIcon isApproved={criteriaApproved} isActive={activeStep === 2} />
            <div className="min-w-0 flex-1">
              <p className={`text-xs font-bold uppercase tracking-wider truncate ${activeStep === 2 ? 'text-teal-600 dark:text-teal-400' : 'text-surface-900 dark:text-white'}`}>
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
            {activeStep === 2 && <span className="w-2 h-2 rounded-full bg-teal-600 shrink-0 mr-1" />}
          </button>

          {/* Step 3 Tab */}
          <button 
            type="button"
            onClick={() => {
              if (criteriaApproved) {
                setActiveStep(3);
              } else {
                setErrorMsg(isVi ? 'Vui lòng hoàn thành tiêu chí sàng lọc ở bước 2 trước khi sang bước 3.' : 'Please complete Screening Criteria in Step 2 first.');
              }
            }}
            className={`flex items-center gap-3 p-3 rounded-xl transition-all text-left border ${
              activeStep === 3 
                ? 'bg-white dark:bg-slate-900 border-purple-500/50 shadow-sm ring-2 ring-purple-500/10' 
                : 'border-transparent hover:bg-white/60 dark:hover:bg-slate-900/60'
            } ${criteriaApproved ? 'cursor-pointer' : 'opacity-50 cursor-not-allowed'}`}
          >
            <PicoStepperIcon isApproved={Boolean(picoData)} isActive={activeStep === 3} />
            <div className="min-w-0 flex-1">
              <p className={`text-xs font-bold uppercase tracking-wider truncate ${activeStep === 3 ? 'text-purple-600 dark:text-purple-400' : 'text-surface-900 dark:text-white'}`}>
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
            {activeStep === 3 && <span className="w-2 h-2 rounded-full bg-purple-600 shrink-0 mr-1" />}
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3.5 rounded-2xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800/60 text-rose-700 dark:text-rose-300 text-xs sm:text-sm flex items-center justify-between gap-2.5 animate-slide-up shadow-xs">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-500" />
            <span className="font-medium">{errorMsg}</span>
          </div>
          <button onClick={() => setErrorMsg(null)} className="text-rose-400 hover:text-rose-600 cursor-pointer">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* ── SINGLE MAIN WORKSPACE DISPLAY AREA ──────────────────────────── */}
      <div className="transition-all duration-200">

        {/* ═══════════════════════════════════════════════════════════════════ */}
        {/* STEP 1: ĐỊNH HÌNH ĐỀ TÀI (TOPIC SCOPE)                              */}
        {/* ═══════════════════════════════════════════════════════════════════ */}
        {activeStep === 1 && (
          <div className="space-y-6 animate-slide-up">
            
            {/* Top Subtle Notebook Topic Breadcrumb Bar */}
            <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 px-4 rounded-2xl bg-surface-50/80 dark:bg-surface-850/60 border border-surface-200/80 dark:border-surface-800 shadow-2xs">
              <div className="flex items-center gap-2.5 min-w-0">
                <span className="text-[11px] font-bold uppercase tracking-wider text-surface-400 dark:text-surface-500 shrink-0 flex items-center gap-1.5">
                  <BookOpen className="w-3.5 h-3.5 text-blue-500" />
                  {isVi ? 'Đề tài nghiên cứu:' : 'Research Project:'}
                </span>
                <span className="font-bold text-xs sm:text-sm text-surface-900 dark:text-white truncate">
                  {projectData.name || (isVi ? 'Chưa đặt tên đề tài' : 'Untitled Project')}
                </span>
                <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 border border-blue-200/80 dark:border-blue-800/80 shrink-0">
                  🏷️ {projectData.research_field || (isVi ? 'Nghiên cứu liên ngành' : 'Interdisciplinary')}
                </span>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <button
                  type="button"
                  onClick={() => setIsEditingTopicMeta(!isEditingTopicMeta)}
                  className="btn btn-sm btn-ghost text-xs text-surface-500 hover:text-blue-600 dark:text-surface-400 dark:hover:text-blue-400 font-semibold flex items-center gap-1 cursor-pointer"
                >
                  <Edit3 className="w-3.5 h-3.5" />
                  <span>{isEditingTopicMeta ? (isVi ? 'Đóng' : 'Close') : (isVi ? 'Đổi tên / lĩnh vực' : 'Edit')}</span>
                </button>
              </div>
            </div>

            {/* Expandable Topic Name / Field Editor */}
            {isEditingTopicMeta && (
              <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-blue-200 dark:border-blue-900/60 space-y-4 animate-slide-up shadow-sm">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="section-label font-bold text-xs mb-1.5 block">
                      {isVi ? 'Tên đề tài nghiên cứu' : 'Project Name'}
                    </label>
                    <input 
                      type="text" 
                      value={projectData.name}
                      onChange={e => setProjectData({...projectData, name: e.target.value})}
                      placeholder={isVi ? 'Nhập tên đề tài...' : 'Enter project name...'}
                      className="input input-sm font-medium"
                    />
                  </div>
                  <div>
                    <label className="section-label font-bold text-xs mb-1.5 block">
                      {isVi ? 'Lĩnh vực nghiên cứu' : 'Research Field'}
                    </label>
                    <select
                      value={projectData.research_field}
                      onChange={e => setProjectData({...projectData, research_field: e.target.value})}
                      className="input input-sm cursor-pointer appearance-none font-medium text-xs"
                    >
                      <option value="">{isVi ? '-- Chọn lĩnh vực nghiên cứu --' : '-- Select research domain --'}</option>
                      <option value="Khoa học Máy tính & Trí tuệ Nhân tạo">{isVi ? 'Khoa học máy tính & Trí tuệ nhân tạo' : 'Computer Science & AI'}</option>
                      <option value="Y sinh & Chẩn đoán Y tế">{isVi ? 'Y sinh & Chẩn đoán y tế' : 'Healthcare & Biomedicine'}</option>
                      <option value="Robotics & Hệ thống Tự hành">{isVi ? 'Robotics & Hệ thống tự hành' : 'Robotics & Autonomous Systems'}</option>
                      <option value="Xử lý Ngôn ngữ Tự nhiên & LLM">{isVi ? 'Xử lý ngôn ngữ tự nhiên & LLM' : 'NLP & Large Language Models'}</option>
                      <option value="Toán học, Thống kê & Tối ưu hóa">{isVi ? 'Toán học, thống kê & Tối ưu hóa' : 'Mathematics & Optimization'}</option>
                      <option value="Khoa học Môi trường & Năng lượng">{isVi ? 'Khoa học môi trường & Năng lượng' : 'Environment & Renewable Energy'}</option>
                      <option value="Kinh tế, Tài chính & Quản trị">{isVi ? 'Kinh tế, tài chính & Quản trị' : 'Economics & Business Administration'}</option>
                      <option value="Khoa học Xã hội & Giáo dục">{isVi ? 'Khoa học xã hội & Giáo dục' : 'Social Sciences & Education'}</option>
                      <option value="Nghiên cứu Liên ngành Khác">{isVi ? 'Nghiên cứu liên ngành khác' : 'Interdisciplinary / Other'}</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            {/* ── HERO CORE INPUT ARENA: The Visual Center of Attention ────────── */}
            <div id="section-topic-info" className="card p-6 sm:p-8 bg-white dark:bg-slate-900 border-2 border-blue-500/30 dark:border-blue-500/30 shadow-md shadow-blue-500/5 space-y-6">
              
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100 dark:border-slate-800">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-2xl bg-blue-600 text-white flex items-center justify-center shadow-md shadow-blue-500/25 shrink-0">
                    <Target className="w-5 h-5 stroke-[2.4]" />
                  </div>
                  <div>
                    <h2 className="font-display font-extrabold text-lg sm:text-xl text-slate-900 dark:text-white flex items-center gap-2">
                      <span>{isVi ? 'Xác định câu hỏi nghiên cứu & Khung năm' : 'Formulate Research Question & Timeframe'}</span>
                      {topicApproved && (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-cyan-700 dark:text-cyan-300 bg-cyan-100 dark:bg-cyan-950/60 px-2.5 py-0.5 rounded-full border border-cyan-200 dark:border-cyan-800">
                          <Check className="w-3 h-3 stroke-[2.5]" /> {isVi ? 'Đã định hình' : 'Confirmed'}
                        </span>
                      )}
                    </h2>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                      {isVi ? 'Vui lòng điền câu hỏi nghiên cứu cụ thể và khoảng năm xuất bản dưới đây:' : 'Please enter your specific research problem statement and publication window below:'}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleSave()}
                    disabled={loading}
                    className="btn btn-sm btn-secondary flex items-center gap-1.5 font-semibold cursor-pointer"
                  >
                    {saved ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-600 stroke-[2.5]" />
                        <span>{isVi ? 'Đã lưu!' : 'Saved!'}</span>
                      </>
                    ) : (
                      <>
                        {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                        <span>{isVi ? 'Lưu nháp' : 'Save Draft'}</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Full Width Hero Question with Inline Compact Year Filter */}
              <div className="space-y-3">
                
                {/* Header with Title on Left and Compact Year Filter on Right */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
                  <label className="text-xs sm:text-sm font-extrabold text-blue-700 dark:text-blue-400 flex items-center gap-2">
                    <span>{isVi ? 'Câu hỏi / Bài toán nghiên cứu cốt lõi *' : 'Core Research Question / Problem Statement *'}</span>
                  </label>

                  {/* Compact Year Filter Right in Header */}
                  <div className="flex items-center gap-1.5 self-start sm:self-auto bg-slate-100/90 dark:bg-slate-800/90 px-3 py-1.5 rounded-xl border border-slate-200/80 dark:border-slate-700/80 text-xs shadow-2xs">
                    <span className="text-slate-500 dark:text-slate-400 font-semibold text-[11px] flex items-center gap-1">
                      <span>📅</span> {isVi ? 'Khung năm:' : 'Years:'}
                    </span>
                    <input
                      type="number"
                      value={projectData.year_from || 2020}
                      onChange={e => setProjectData({...projectData, year_from: parseInt(e.target.value) || 2020})}
                      className="w-16 py-0.5 px-1.5 text-center text-xs font-bold rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200"
                    />
                    <span className="text-slate-400 font-bold">-</span>
                    <input
                      type="number"
                      value={projectData.year_to || 2026}
                      onChange={e => setProjectData({...projectData, year_to: parseInt(e.target.value) || 2026})}
                      className="w-16 py-0.5 px-1.5 text-center text-xs font-bold rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200"
                    />
                  </div>
                </div>

                <textarea 
                  rows="4"
                  value={projectData.research_question || ''}
                  onChange={e => setProjectData({...projectData, research_question: e.target.value})}
                  placeholder={isVi 
                    ? 'Hãy điền câu hỏi nghiên cứu cụ thể của bạn vào đây (Ví dụ: Các thuật toán xấp xỉ nào hiệu quả nhất để giải bài toán Split Feasibility trong không gian Hilbert vô hạn chiều?)...' 
                    : 'Please enter your specific research question here (e.g. Which iterative approximation algorithms converge fastest for Split Feasibility Problems in infinite-dimensional Hilbert spaces?)...'}
                  className="input w-full p-4 rounded-2xl border-2 border-blue-300 dark:border-blue-800/80 focus:border-blue-600 dark:focus:border-blue-400 bg-blue-50/20 dark:bg-slate-800/60 text-slate-900 dark:text-white font-medium text-xs sm:text-sm leading-relaxed resize-none transition-all shadow-inner placeholder:text-slate-400 dark:placeholder:text-slate-500"
                />

                <p className="text-[11px] text-slate-500 dark:text-slate-400 flex items-center gap-1.5 pl-1">
                  <BrainCircuit className="w-3.5 h-3.5 text-blue-500 shrink-0" />
                  <span>{isVi ? 'Mẹo: Nêu rõ đối tượng, phương pháp và mục tiêu so sánh giúp AI đề xuất tiêu chí & từ khóa chuẩn xác nhất.' : 'Tip: Stating the method, target, and evaluation criteria helps AI generate the most accurate keywords.'}</span>
                </p>
              </div>

              {/* Action buttons directly beneath the 2 inputs */}
              <div className="pt-5 border-t border-slate-100 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3">
                <button
                  type="button"
                  onClick={handleOptimizeScope}
                  disabled={loadingScope}
                  className="btn btn-secondary w-full sm:w-auto flex items-center justify-center gap-2.5 font-bold px-5 py-3 rounded-xl border border-cyan-300 dark:border-cyan-800 text-cyan-800 dark:text-cyan-200 bg-cyan-50/60 dark:bg-cyan-950/40 hover:bg-cyan-100 transition-all cursor-pointer shadow-xs"
                >
                  {loadingScope ? <Loader2 className="w-4 h-4 animate-spin text-cyan-600" /> : <Compass className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />}
                  <span>{isVi ? 'Nhận xét về phạm vi đề tài' : 'Review Topic Scope'}</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleApproveTopic()}
                  disabled={loading}
                  className="btn btn-primary w-full sm:w-auto flex items-center justify-center gap-2.5 shadow-md font-extrabold text-sm px-7 py-3 rounded-xl cursor-pointer hover:scale-[1.02] transition-all"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4 stroke-[2.5]" />}
                  <span>{isVi ? 'Lưu & Sang bước 2: Tiêu chí' : 'Save & Continue to Step 2'}</span>
                  <ArrowRight className="w-4 h-4 ml-0.5" />
                </button>
              </div>
            </div>

            {/* TOPIC SCOPE FEEDBACK CARD */}
            {scopeResult && (
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
                    scopeResult.status === 'too_narrow' ? 'badge-primary' : 
                    scopeResult.status === 'error' ? 'bg-red-100 text-red-700 dark:bg-red-950/60 dark:text-red-300 border border-red-300 dark:border-red-800' :
                    'badge-warning'
                  }`}>
                    {scopeResult.status === 'optimal' 
                      ? (isVi ? '✨ Phạm vi tối ưu' : '✨ Optimal Scope')
                      : scopeResult.status === 'too_narrow' 
                      ? (isVi ? '🔍 Đề tài quá hẹp' : '🔍 Too Narrow')
                      : scopeResult.status === 'error'
                      ? (isVi ? '⚠️ Tạm thời gián đoạn' : '⚠️ Service Unavailable')
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
                              className="btn btn-sm btn-ghost text-xs hover:bg-surface-100 dark:hover:bg-surface-700 font-semibold cursor-pointer"
                            >
                              {isVi ? 'Áp dụng' : 'Apply'}
                            </button>
                            <button
                              onClick={() => handleApproveTopic(topic)}
                              className="btn btn-sm btn-primary text-xs font-bold cursor-pointer"
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
          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════════════ */}
        {/* STEP 2: TIÊU CHÍ SÀNG LỌC (SCREENING CRITERIA)                      */}
        {/* ═══════════════════════════════════════════════════════════════════ */}
        {activeStep === 2 && (
          <div className="space-y-6 animate-slide-up">
            <div ref={criteriaCardRef} className="card p-6 sm:p-7 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
              
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6 pb-4 border-b border-surface-100 dark:border-surface-800">
                <div>
                  <h2 className="font-display font-bold text-lg text-surface-900 dark:text-white flex items-center gap-2">
                    <span>{isVi ? '2. Tiêu chí sàng lọc PRISMA' : '2. PRISMA Screening Criteria'}</span>
                    {criteriaApproved && (
                      <span className="inline-flex items-center gap-1 text-[11px] font-bold text-teal-700 dark:text-teal-300 bg-teal-100 dark:bg-teal-950/60 px-2.5 py-0.5 rounded-full border border-teal-200 dark:border-teal-800 shadow-xs">
                        <Check className="w-3 h-3 stroke-[2.5]" /> {isVi ? 'Đã xác nhận' : 'Confirmed'}
                      </span>
                    )}
                  </h2>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleGenerateCriteria}
                    disabled={loadingCriteria}
                    className="btn btn-sm btn-secondary flex items-center gap-1.5 font-semibold cursor-pointer"
                  >
                    {loadingCriteria ? <Loader2 className="w-3.5 h-3.5 animate-spin text-teal-500" /> : <BrainCircuit className="w-3.5 h-3.5 text-teal-500" />}
                    <span>{isVi ? 'AI gợi ý tiêu chí' : 'AI Suggested Criteria'}</span>
                  </button>
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
                  
                  <div className="flex gap-2">
                    <input 
                      type="text" 
                      value={newInclude} 
                      onChange={e => setNewInclude(e.target.value)} 
                      onKeyDown={e => e.key === 'Enter' && addInclude()}
                      placeholder={isVi ? 'Thêm tiêu chí chọn (VD: Bài báo từ 2020-2026, Q1/Q2...)' : 'Add inclusion criterion...'}
                      className="input input-sm flex-1 font-medium"
                    />
                    <button onClick={addInclude} className="btn btn-sm btn-secondary px-3 cursor-pointer">
                      <Plus className="w-4 h-4"/>
                    </button>
                  </div>
                  
                  <ul className="space-y-2">
                    {projectData.criteria_include.map((item, idx) => (
                      <li key={idx} className="group flex justify-between items-start bg-emerald-50/70 dark:bg-emerald-950/30 p-3.5 rounded-xl text-xs font-semibold border border-emerald-200/70 dark:border-emerald-900/40 text-slate-800 dark:text-slate-100 shadow-2xs">
                        <span className="pr-3 leading-relaxed">{item}</span>
                        <button onClick={() => setProjectData(p => ({...p, criteria_include: p.criteria_include.filter((_, i) => i !== idx)}))} className="text-slate-400 hover:text-rose-500 transition-colors opacity-0 group-hover:opacity-100 flex-shrink-0 cursor-pointer">
                          <X className="w-3.5 h-3.5"/>
                        </button>
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
                  
                  <div className="flex gap-2">
                    <input 
                      type="text" 
                      value={newExclude} 
                      onChange={e => setNewExclude(e.target.value)} 
                      onKeyDown={e => e.key === 'Enter' && addExclude()}
                      placeholder={isVi ? 'Thêm tiêu chí loại (VD: Bài báo review tổng quan, thư toà soạn...)' : 'Add exclusion criterion...'}
                      className="input input-sm flex-1 font-medium"
                    />
                    <button onClick={addExclude} className="btn btn-sm btn-secondary px-3 cursor-pointer">
                      <Plus className="w-4 h-4"/>
                    </button>
                  </div>
                  
                  <ul className="space-y-2">
                    {projectData.criteria_exclude.map((item, idx) => (
                      <li key={idx} className="group flex justify-between items-start bg-rose-50/70 dark:bg-rose-950/30 p-3.5 rounded-xl text-xs font-semibold border border-rose-200/70 dark:border-rose-900/40 text-slate-800 dark:text-slate-100 shadow-2xs">
                        <span className="pr-3 leading-relaxed">{item}</span>
                        <button onClick={() => setProjectData(p => ({...p, criteria_exclude: p.criteria_exclude.filter((_, i) => i !== idx)}))} className="text-slate-400 hover:text-rose-500 transition-colors opacity-0 group-hover:opacity-100 flex-shrink-0 cursor-pointer">
                          <X className="w-3.5 h-3.5"/>
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>

              </div>

              {/* Step 2 Bottom Navigation */}
              <div className="pt-4 border-t border-slate-100 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3">
                <button
                  type="button"
                  onClick={() => setActiveStep(1)}
                  className="btn btn-secondary w-full sm:w-auto flex items-center justify-center gap-2 font-semibold cursor-pointer"
                >
                  <ArrowLeft className="w-4 h-4" />
                  <span>{isVi ? 'Quay lại bước 1: Định hình' : 'Back to Step 1: Definition'}</span>
                </button>

                <button 
                  type="button" 
                  onClick={handleApproveCriteria} 
                  disabled={loading}
                  className="btn btn-primary w-full sm:w-auto shadow-primary-sm font-bold flex items-center justify-center gap-2 cursor-pointer"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
                  <span>{isVi ? 'Lưu & Sang bước 3: PICO & Từ khóa' : 'Save & Continue to PICO'}</span>
                  <ArrowRight className="w-4 h-4 ml-1" />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════════════ */}
        {/* STEP 3: PHÂN TÍCH KHUNG PICO & BỘ TỪ KHÓA (PICO & KEYWORDS)        */}
        {/* ═══════════════════════════════════════════════════════════════════ */}
        {activeStep === 3 && (
          <div className="space-y-6 animate-slide-up">
            
            <div className="card p-7 sm:p-9 text-center rounded-2xl bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-100 space-y-6 shadow-sm border border-slate-200 dark:border-slate-800">
              <div className="w-14 h-14 mx-auto rounded-2xl bg-blue-50 dark:bg-blue-950/60 border border-blue-100 dark:border-blue-800/80 flex items-center justify-center shadow-xs">
                <svg className="w-7 h-7 text-blue-600 dark:text-blue-400 animate-pulse" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 3a9 9 0 0 1 9 9c0 3.87-2.45 7.17-5.9 8.44L12 21l-3.1-1.56A8.99 8.99 0 0 1 3 12a9 9 0 0 1 9-9z" className="fill-blue-500/10 stroke-blue-600 dark:stroke-blue-400" />
                  <path d="M12 7v5l3 3" className="stroke-blue-600 dark:stroke-blue-400 stroke-[2]" />
                  <circle cx="12" cy="12" r="1.5" className="fill-blue-600 dark:fill-blue-400" />
                </svg>
              </div>
              
              <div className="max-w-2xl mx-auto space-y-2">
                <h3 className="font-display font-extrabold text-xl sm:text-2xl text-slate-900 dark:text-white tracking-tight">
                  {isVi ? '3. Phân tích khung PICO & Bộ từ khóa tìm kiếm' : '3. PICO Framework & Academic Search Keywords'}
                </h3>
                <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-300 leading-relaxed font-medium">
                  {isVi 
                    ? 'Khung PICO (Đối tượng, Can thiệp, So sánh, Kết quả) giúp cấu trúc hóa câu hỏi nghiên cứu và trích xuất các từ khóa học thuật tiếng Anh chuẩn xác nhất để tìm kiếm bài báo trên Google Scholar & Scopus.'
                    : 'The PICO framework (Population, Intervention, Comparison, Outcome) structures your research question and extracts the most accurate academic search keywords for literature discovery.'}
                </p>
              </div>

              {/* Action buttons at end of Step 3 - Identical to Step 2 */}
              <div className="pt-5 mt-4 border-t border-surface-100 dark:border-surface-800 flex flex-col sm:flex-row items-center justify-between gap-3">
                <button
                  type="button"
                  onClick={() => setActiveStep(2)}
                  className="btn btn-secondary w-full sm:w-auto flex items-center justify-center gap-2 font-semibold cursor-pointer"
                >
                  <ArrowLeft className="w-4 h-4" />
                  <span>{isVi ? 'Quay lại bước 2: Tiêu chí' : 'Back to Step 2: Criteria'}</span>
                </button>

                <button 
                  onClick={handleSuggestKeywords} 
                  disabled={loadingKeywords}
                  className="btn btn-primary w-full sm:w-auto shadow-primary-sm font-bold flex items-center justify-center gap-2 cursor-pointer"
                >
                  {loadingKeywords ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin text-white" />
                      <span>{isVi ? 'Đang phân tích & tra cứu...' : 'Analyzing & Synthesizing...'}</span>
                    </>
                  ) : (
                    <>
                      <Search className="w-4 h-4" />
                      <span>{picoData ? (isVi ? 'Tra cứu lại PICO' : 'Re-synthesize PICO') : (isVi ? 'Tra cứu PICO & Sinh từ khóa' : 'Synthesize PICO')}</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {picoData && (
              <div ref={picoCardRef} className="card p-6 sm:p-8 space-y-6 animate-slide-up bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm rounded-2xl">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100 dark:border-slate-800">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-blue-50 dark:bg-blue-950/60 border border-blue-100 dark:border-blue-800 flex items-center justify-center text-blue-600 dark:text-blue-400 shadow-xs">
                      <BookOpen className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="font-display font-extrabold text-lg text-slate-900 dark:text-white">
                        {isVi ? 'Kết quả phân tích khung PICO' : 'PICO Analysis Results'}
                      </h4>
                      <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                        {isVi ? 'Đã phân tích và trích xuất cấu trúc đề tài thành công' : 'Analysis and scoping completed successfully'}
                      </p>
                    </div>
                  </div>

                  {/* Top Right Save Button */}
                  <button 
                    type="button"
                    onClick={() => handleSave()}
                    disabled={loading}
                    className="btn btn-primary self-start sm:self-auto flex items-center gap-2 font-bold shadow-md px-5 py-2.5 rounded-xl transition-all hover:scale-105 cursor-pointer"
                  >
                    {saved ? (
                      <>
                        <Check className="w-4 h-4 stroke-[2.5]" />
                        <span>{isVi ? 'Đã lưu khung đề tài!' : 'Framework Saved!'}</span>
                      </>
                    ) : (
                      <>
                        {loading ? <Loader2 className="w-4 h-4 animate-spin text-white" /> : <Save className="w-4 h-4 text-white" />}
                        <span>{isVi ? 'Lưu khung đề tài' : 'Save Framework'}</span>
                      </>
                    )}
                  </button>
                </div>

                {/* 4 PICO Blocks */}
                <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
                  <div className="p-4 rounded-xl bg-blue-50/50 dark:bg-slate-800/80 border border-blue-100 dark:border-slate-700 shadow-xs space-y-1.5">
                    <span className="section-label text-blue-700 dark:text-blue-400 block font-bold text-xs">
                      [P] {isVi ? 'Đối tượng nghiên cứu' : 'Population / Problem'}:
                    </span>
                    <p className="text-xs font-semibold text-slate-800 dark:text-slate-100 leading-relaxed">
                      {picoData.population || 'N/A'}
                    </p>
                  </div>

                  <div className="p-4 rounded-xl bg-indigo-50/50 dark:bg-slate-800/80 border border-indigo-100 dark:border-slate-700 shadow-xs space-y-1.5">
                    <span className="section-label text-indigo-700 dark:text-indigo-400 block font-bold text-xs">
                      [I] {isVi ? 'Giải pháp & Phương pháp' : 'Intervention / Method'}:
                    </span>
                    <p className="text-xs font-semibold text-slate-800 dark:text-slate-100 leading-relaxed">
                      {picoData.intervention || 'N/A'}
                    </p>
                  </div>

                  <div className="p-4 rounded-xl bg-amber-50/50 dark:bg-slate-800/80 border border-amber-100 dark:border-slate-700 shadow-xs space-y-1.5">
                    <span className="section-label text-amber-700 dark:text-amber-400 block font-bold text-xs">
                      [C] {isVi ? 'Tiêu chuẩn đối chiếu' : 'Comparison'}:
                    </span>
                    <p className="text-xs font-semibold text-slate-800 dark:text-slate-100 leading-relaxed">
                      {picoData.comparison || 'N/A'}
                    </p>
                  </div>

                  <div className="p-4 rounded-xl bg-emerald-50/50 dark:bg-slate-800/80 border border-emerald-100 dark:border-slate-700 shadow-xs space-y-1.5">
                    <span className="section-label text-emerald-700 dark:text-emerald-400 block font-bold text-xs">
                      [O] {isVi ? 'Kết quả kỳ vọng' : 'Outcome'}:
                    </span>
                    <p className="text-xs font-semibold text-slate-800 dark:text-slate-100 leading-relaxed">
                      {picoData.outcome || 'N/A'}
                    </p>
                  </div>
                </div>

                {/* Keywords & Boolean Query Container */}
                <div className="p-5 sm:p-6 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white space-y-4 shadow-xs">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-200 dark:border-slate-700">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 flex items-center gap-2">
                      <Search className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                      {isVi ? 'Bộ từ khóa học thuật đề xuất' : 'Academic Search Keywords'}
                    </span>

                    <div className="flex flex-wrap items-center gap-2">
                      {picoData.search_keywords && picoData.search_keywords.length > 0 && (
                        <button
                          onClick={handleCopyKeywords}
                          className="btn btn-sm btn-secondary text-xs flex items-center gap-1.5 font-semibold cursor-pointer"
                        >
                          {copiedKeywords ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                          <span>{copiedKeywords ? (isVi ? 'Đã sao chép!' : 'Copied!') : (isVi ? 'Sao chép chuỗi từ khóa' : 'Copy Search String')}</span>
                        </button>
                      )}

                      <button
                        onClick={() => downloadSetupFrameworkMarkdown(projectData, picoData, `${(projectData?.name || 'khung_de_tai').replace(/\s+/g, '_')}_framework.md`)}
                        className="btn btn-sm btn-secondary text-xs flex items-center gap-1.5 font-semibold cursor-pointer"
                        title={isVi ? 'Tải tóm tắt khung đề tài dạng Markdown' : 'Download Research Framework summary as Markdown'}
                      >
                        <Download className="w-3.5 h-3.5 text-blue-500" />
                        <span>{isVi ? 'Xuất khung đề tài (.md)' : 'Export Framework (.md)'}</span>
                      </button>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2.5">
                    {(picoData.search_keywords || []).map((kw, i) => (
                      <span 
                        key={i} 
                        className="px-3 py-1 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 text-xs font-bold border border-blue-200/80 dark:border-blue-800 shadow-xs"
                      >
                        {kw}
                      </span>
                    ))}
                  </div>

                  {/* Big Next Step Guidance */}
                  <div className="pt-4 border-t border-slate-200 dark:border-slate-700 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <button
                      type="button"
                      onClick={() => setActiveStep(2)}
                      className="btn btn-secondary w-full sm:w-auto flex items-center justify-center gap-2 font-semibold text-xs cursor-pointer"
                    >
                      <ArrowLeft className="w-4 h-4" />
                      <span>{isVi ? 'Quay lại bước 2: Tiêu chí' : 'Back to Step 2: Criteria'}</span>
                    </button>

                    <button 
                      onClick={handleProceedToSearch}
                      className="btn btn-primary btn-lg font-bold shrink-0 flex items-center justify-center gap-2 shadow-primary-md cursor-pointer"
                    >
                      <span>{isVi ? 'Tiến hành tìm kiếm bài báo' : 'Proceed to Search Papers'}</span>
                      <ArrowRight className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}
