import React, { useState, useEffect, useRef } from 'react';
import { 
  BookOpen, Target, Settings, Save, Loader2, Plus, X, 
  CheckCircle2, Compass, AlertCircle, ArrowRight, Check,
  ShieldCheck, Edit3, Copy, Search, CheckCheck, Sparkles,
  ChevronRight, Layers, FileCheck
} from 'lucide-react';
import { normalizeResearchSetup } from '../../utils/researchSetup';
import { useLanguage } from '../../contexts/LanguageContext';
import { API_BASE } from '../../utils/apiConfig';

import { useProject } from '../../contexts/ProjectContext';
import { useAuth } from '../../contexts/AuthContext';

export default function ResearchSetupTab({ setActiveTab }) {
  const { t } = useLanguage();
  const { activeProject, activeProjectId, updateProject, createProject } = useProject();
  const { token, currentUser } = useAuth();

  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);
  
  const [projectData, setProjectData] = useState(() => {
    return normalizeResearchSetup(activeProject || {});
  });

  const [newInclude, setNewInclude] = useState('');
  const [newExclude, setNewExclude] = useState('');

  // Human-in-the-Loop (HITL) Gate Statuses (Project-Scoped)
  const [topicApproved, setTopicApproved] = useState(false);
  const [criteriaApproved, setCriteriaApproved] = useState(false);

  // State: Agent 1 (Scope Optimizer)
  const [scopeResult, setScopeResult] = useState(null);
  const [loadingScope, setLoadingScope] = useState(false);
  const [appliedTopicToast, setAppliedTopicToast] = useState(null);

  // State: Agent 2 (Criteria Generator)
  const [loadingCriteria, setLoadingCriteria] = useState(false);
  const [criteriaToast, setCriteriaToast] = useState(false);

  // State: Agent 3 (PICO & Keywords Finder)
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

  // Sync state when activeProject changes
  useEffect(() => {
    if (activeProject) {
      setProjectData(normalizeResearchSetup(activeProject));
    } else {
      setProjectData(normalizeResearchSetup({}));
    }

    if (activeProjectId) {
      const g1 = localStorage.getItem(`slr_gate1_topic_approved_${activeProjectId}`);
      setTopicApproved(g1 === 'true');

      const g2 = localStorage.getItem(`slr_gate2_criteria_approved_${activeProjectId}`);
      setCriteriaApproved(g2 === 'true');

      try {
        const cachedScope = localStorage.getItem(`slr_scope_result_${activeProjectId}`);
        setScopeResult(cachedScope ? JSON.parse(cachedScope) : null);
      } catch { setScopeResult(null); }

      try {
        const cachedKw = localStorage.getItem(`suggested_keywords_${activeProjectId}`);
        setSuggestedKeywords(cachedKw ? JSON.parse(cachedKw) : []);
      } catch { setSuggestedKeywords([]); }

      try {
        const cachedPico = localStorage.getItem(`slr_pico_data_${activeProjectId}`);
        setPicoData(cachedPico ? JSON.parse(cachedPico) : null);
      } catch { setPicoData(null); }

      try {
        const cachedGap = localStorage.getItem(`slr_gap_map_${activeProjectId}`);
        setGapMapData(cachedGap ? JSON.parse(cachedGap) : null);
      } catch { setGapMapData(null); }
    } else {
      setTopicApproved(false);
      setCriteriaApproved(false);
      setScopeResult(null);
      setSuggestedKeywords([]);
      setPicoData(null);
      setGapMapData(null);
    }
  }, [activeProjectId, activeProject]);

  const handleSave = async (updatedData = projectData) => {
    setLoading(true);
    setSaved(false);
    setErrorMsg(null);
    try {
      if (activeProjectId) {
        const res = await fetch(`${API_BASE}/projects/${activeProjectId}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify(updatedData)
        });
        if (res.ok) {
          const savedData = await res.json();
          setSaved(true);
          localStorage.setItem(`research_setup_data_${activeProjectId}`, JSON.stringify(updatedData));
          setTimeout(() => setSaved(false), 3000);
        } else {
          setErrorMsg(t('setup.error_ai') || 'Save failed');
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
      setErrorMsg(t('setup.error_server') || 'Server connection error');
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
        setErrorMsg('Vui lòng nhập tên đề tài hoặc câu hỏi nghiên cứu trước khi tối ưu.');
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
        if (activeProjectId) {
          localStorage.setItem(`slr_scope_result_${activeProjectId}`, JSON.stringify(data));
        }
        scrollToRef(scopeCardRef);
      } else {
        setErrorMsg(t('setup.error_ai') + ' (Agent 1 error)');
      }
    } catch (err) {
      console.error(err);
      setErrorMsg(t('setup.error_server'));
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
    if (activeProjectId) {
      localStorage.setItem(`slr_gate1_topic_approved_${activeProjectId}`, 'true');
    }
    await handleSave(updated);
    scrollToRef(criteriaCardRef);
  };

  // Agent 2: Criteria Generation
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
        setErrorMsg(t('setup.error_ai') + ' (Agent 2 error)');
      }
    } catch (err) {
      console.error(err);
      setErrorMsg(t('setup.error_server'));
    } finally {
      setLoadingCriteria(false);
    }
  };

  const handleApproveCriteria = async () => {
    setCriteriaApproved(true);
    if (activeProjectId) {
      localStorage.setItem(`slr_gate2_criteria_approved_${activeProjectId}`, 'true');
    }
    await handleSave(projectData);
    scrollToRef(step3CardRef);
  };

  // Agent 3: PICO & Keywords
  const handleSuggestKeywords = async () => {
    setLoadingKeywords(true);
    setErrorMsg(null);
    try {
      const ideaText = projectData.research_question || projectData.name || '';
      if (!ideaText.trim()) {
        setErrorMsg('Vui lòng nhập câu hỏi nghiên cứu hoặc tên đề tài ở Bước 1.');
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
          setErrorMsg(`Lỗi từ AI: ${data.error}`);
          return;
        }
        
        if (data.pico) {
          setPicoData(data.pico);
          if (activeProjectId) {
            localStorage.setItem(`slr_pico_data_${activeProjectId}`, JSON.stringify(data.pico));
          }
          
          const rawKws = data.pico.search_keywords || [];
          const kwList = rawKws.filter(kw => 
            kw && kw.trim().length >= 3 && /^[a-zA-Z0-9\s\-\/&.]+$/.test(kw.trim())
          );
          
          if (kwList.length > 0) {
            setSuggestedKeywords(kwList);
            localStorage.setItem('suggested_keywords', JSON.stringify(kwList));
            if (activeProjectId) {
              localStorage.setItem(`suggested_keywords_${activeProjectId}`, JSON.stringify(kwList));
            }
          }
          
          const boolQuery = kwList.length > 0 ? kwList.join(' ') : (data.pico.boolean_query || '');
          if (boolQuery) {
             localStorage.setItem('litreview_active_mesh_query', boolQuery);
             localStorage.setItem('last_search_query', boolQuery);
             if (activeProjectId) {
               localStorage.setItem(`litreview_active_mesh_query_${activeProjectId}`, boolQuery);
               localStorage.setItem(`last_search_query_${activeProjectId}`, boolQuery);
             }
             window.dispatchEvent(new Event('new_mesh_query_ready'));
          }

          scrollToRef(picoCardRef);
        }
        
        if (data.gap_map && activeProjectId) {
          setGapMapData(data.gap_map);
          localStorage.setItem(`slr_gap_map_${activeProjectId}`, JSON.stringify(data.gap_map));
        }

      } else {
        setErrorMsg(t('setup.error_ai') + ' (Agent 3 failed)');
      }
    } catch (err) {
      console.error(err);
      setErrorMsg(t('setup.error_server'));
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
    <div className="space-y-6 pb-20 max-w-6xl mx-auto">
      
      {/* ── Page Header & Workflow Guide ─────────────────────────────────── */}
      <div className="card p-6 bg-gradient-to-r from-primary-900/40 via-surface-900/60 to-surface-900/40 border-primary-500/20 backdrop-blur-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="badge badge-primary text-xs font-bold uppercase tracking-wider">
                Quy trình Bước 1 / SLR Swarm
              </span>
              {saved && (
                <span className="badge badge-success animate-fade-in text-xs">
                  <Check className="w-3 h-3" /> Đã lưu thay đổi
                </span>
              )}
            </div>
            <h1 className="font-display font-black text-2xl sm:text-3xl text-surface-900 dark:text-white tracking-tight">
              Cấu hình Đề tài Nghiên cứu
            </h1>
            <p className="text-xs sm:text-sm text-surface-500 dark:text-surface-300 mt-1 max-w-2xl leading-relaxed">
              Hoàn thành 3 bước bên dưới để AI phân tích phạm vi đề tài, thiết lập bộ tiêu chí sàng lọc PRISMA và sinh từ khóa tìm kiếm học thuật tối ưu.
            </p>
          </div>

          <div className="flex items-center gap-2 self-start md:self-auto">
            <button
              type="button"
              onClick={() => handleSave()}
              disabled={loading}
              className="btn btn-primary shadow-primary-sm"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              <span>Lưu Cấu hình</span>
            </button>
          </div>
        </div>
      </div>

      {/* ── Stepper Indicator ───────────────────────────────────────────── */}
      <div className="card p-4">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          
          {/* Step 1 */}
          <div className="flex items-center gap-3">
            <div className={`w-9 h-9 rounded-xl flex items-center justify-center font-bold text-xs flex-shrink-0 transition-colors ${
              topicApproved
                ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
                : 'bg-primary-600 text-white'
            }`}>
              {topicApproved ? <Check className="w-4 h-4" /> : '01'}
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-surface-900 dark:text-white uppercase tracking-wider truncate">
                {t('setup.step1_label')}
              </p>
              <p className="text-[11px] text-surface-400 truncate">
                {topicApproved ? 'Approved' : t('setup.step1_desc')}
              </p>
            </div>
          </div>

          {/* Step 2 */}
          <div className="flex items-center gap-3">
            <div className={`w-9 h-9 rounded-xl flex items-center justify-center font-bold text-xs flex-shrink-0 transition-colors ${
              criteriaApproved
                ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
                : topicApproved
                ? 'bg-primary-600 text-white'
                : 'bg-surface-100 dark:bg-surface-800 text-surface-400'
            }`}>
              {criteriaApproved ? <Check className="w-4 h-4" /> : '02'}
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-surface-900 dark:text-white uppercase tracking-wider truncate">
                {t('setup.step2_label')}
              </p>
              <p className="text-[11px] text-surface-400 truncate">
                {criteriaApproved ? 'Approved' : topicApproved ? 'PRISMA 2020' : t('setup.step_not_open')}
              </p>
            </div>
          </div>

          {/* Step 3 */}
          <div className="flex items-center gap-3">
            <div className={`w-9 h-9 rounded-xl flex items-center justify-center font-bold text-xs flex-shrink-0 transition-colors ${
              picoData
                ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
                : criteriaApproved
                ? 'bg-primary-600 text-white'
                : 'bg-surface-100 dark:bg-surface-800 text-surface-400'
            }`}>
              {picoData ? <Check className="w-4 h-4" /> : '03'}
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-surface-900 dark:text-white uppercase tracking-wider truncate">
                {t('setup.step3_label')}
              </p>
              <p className="text-[11px] text-surface-400 truncate">
                {picoData ? 'Completed' : criteriaApproved ? 'Ready' : t('setup.step_not_open')}
              </p>
            </div>
          </div>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 rounded-xl bg-danger-light dark:bg-danger-dark border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0 text-danger" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* ── PHASE 1: RESEARCH TOPIC CONFIGURATION ────────────────────────── */}
      <div id="tour-setup-pico" className={`card p-6 transition-all ${topicApproved ? 'border-emerald-200 dark:border-emerald-900/40 bg-emerald-50/20 dark:bg-emerald-950/10' : ''}`}>
        
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="badge badge-primary text-[10px]">PHASE 01</span>
              {topicApproved && (
                <span className="badge badge-success text-[10px]">
                  <Check className="w-2.5 h-2.5" /> Approved
                </span>
              )}
            </div>
            <h2 className="font-display font-bold text-lg text-surface-900 dark:text-white">
              {t('setup.title')}
            </h2>
          </div>

          {topicApproved && (
            <button
              type="button"
              onClick={() => setTopicApproved(false)}
              className="btn btn-sm btn-secondary self-start sm:self-auto"
            >
              <Edit3 className="w-3.5 h-3.5" />
              Edit Scope
            </button>
          )}
        </div>

        <div className="space-y-4">
          <div>
            <label className="section-label block mb-1.5">{t('setup.project_name')}</label>
            <input 
              type="text" 
              value={projectData.name}
              onChange={e => setProjectData({...projectData, name: e.target.value})}
              placeholder={t('setup.project_name_placeholder')}
              disabled={topicApproved}
              className="input input-sm disabled:opacity-60"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="section-label block mb-1.5">{t('setup.research_question')}</label>
              <textarea 
                rows="4"
                value={projectData.research_question}
                onChange={e => setProjectData({...projectData, research_question: e.target.value})}
                placeholder={t('setup.research_question_placeholder')}
                disabled={topicApproved}
                className="input input-sm disabled:opacity-60 resize-none"
              />
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="section-label block mb-1.5">{t('setup.research_field')}</label>
                <select
                  value={projectData.research_field}
                  onChange={e => setProjectData({...projectData, research_field: e.target.value})}
                  disabled={topicApproved}
                  className="input input-sm disabled:opacity-60 cursor-pointer appearance-none"
                >
                  <option value="">{t('setup.select_field')}</option>
                  <option value="Toán học & Tối ưu hóa">Toán học & Tối ưu hóa (Mathematics & Optimization)</option>
                  <option value="Y tế & Chẩn đoán Y sinh">Y tế & Chẩn đoán Y sinh (Healthcare & Biomedicine)</option>
                  <option value="Robotics & Tự hành">Robotics & Tự hành (Robotics & Autonomous Systems)</option>
                  <option value="Khác">Khác (General Academic)</option>
                </select>
              </div>

              <div className="flex gap-3">
                <div className="flex-1">
                  <label className="section-label block mb-1.5">{t('setup.year_from')}</label>
                  <input
                    type="number"
                    disabled={topicApproved}
                    value={projectData.year_from}
                    onChange={e => setProjectData({...projectData, year_from: parseInt(e.target.value)})}
                    className="input input-sm disabled:opacity-60"
                  />
                </div>
                <div className="flex-1">
                  <label className="section-label block mb-1.5">{t('setup.year_to')}</label>
                  <input
                    type="number"
                    disabled={topicApproved}
                    value={projectData.year_to}
                    onChange={e => setProjectData({...projectData, year_to: parseInt(e.target.value)})}
                    className="input input-sm disabled:opacity-60"
                  />
                </div>
              </div>
            </div>
          </div>

          {!topicApproved && (
            <div className="pt-4 border-t border-surface-100 dark:border-surface-800 flex flex-col sm:flex-row items-center justify-between gap-3">
              <button
                type="button"
                onClick={handleOptimizeScope}
                disabled={loadingScope}
                className="btn btn-secondary w-full sm:w-auto"
              >
                {loadingScope ? <Loader2 className="w-4 h-4 animate-spin" /> : <Compass className="w-4 h-4 text-primary-500" />}
                <span>{t('setup.agent_review')}</span>
              </button>

              <button
                type="button"
                onClick={() => handleApproveTopic()}
                className="btn btn-primary w-full sm:w-auto"
              >
                <Check className="w-4 h-4" />
                <span>{t('setup.approve_btn')}</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ── AGENT 1 RESULT ──────────────────────────────────────────────── */}
      {scopeResult && !topicApproved && (
        <div ref={scopeCardRef} className="card p-6 border-primary-200 dark:border-primary-800 bg-primary-50/20 dark:bg-primary-950/20 space-y-4 animate-slide-up">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Compass className="w-5 h-5 text-primary-600 dark:text-primary-400" />
              <h3 className="font-display font-semibold text-sm text-surface-900 dark:text-white">
                Scope Advisor Feedback
              </h3>
            </div>
            
            <span className={`badge ${
              scopeResult.status === 'optimal' ? 'badge-success' :
              scopeResult.status === 'too_narrow' ? 'badge-primary' : 'badge-warning'
            }`}>
              {scopeResult.status === 'optimal' ? '✨ Optimal' : scopeResult.status === 'too_narrow' ? '🔍 Too Narrow' : '⚠️ Too Broad'}
            </span>
          </div>

          <p className="text-sm text-surface-600 dark:text-surface-300 leading-relaxed bg-white dark:bg-surface-800 p-4 rounded-xl border border-surface-200 dark:border-surface-700">
            {scopeResult.feedback}
          </p>

          {scopeResult.suggested_topics && scopeResult.suggested_topics.length > 0 && (
            <div className="space-y-2">
              <p className="section-label">Suggested Refinements:</p>
              <div className="grid gap-2">
                {scopeResult.suggested_topics.map((topic, i) => (
                  <div key={i} className="p-3 rounded-xl bg-white dark:bg-surface-800 border border-surface-200 dark:border-surface-700 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:border-primary-300 transition-colors">
                    <span className="text-xs text-surface-700 dark:text-surface-200 leading-relaxed">{topic}</span>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <button
                        onClick={() => handleApplyTopic(topic)}
                        className="btn btn-sm btn-ghost text-xs"
                      >
                        Apply
                      </button>
                      <button
                        onClick={() => handleApproveTopic(topic)}
                        className="btn btn-sm btn-primary text-xs"
                      >
                        Approve
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── PHASE 2: SCREENING CRITERIA ──────────────────────────────────── */}
      {topicApproved && (
        <div ref={criteriaCardRef} className={`card p-6 transition-all animate-slide-up ${criteriaApproved ? 'border-emerald-200 dark:border-emerald-900/40 bg-emerald-50/20 dark:bg-emerald-950/10' : ''}`}>
          
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="badge badge-primary text-[10px]">PHASE 02</span>
                {criteriaApproved && (
                  <span className="badge badge-success text-[10px]">
                    <Check className="w-2.5 h-2.5" /> Approved
                  </span>
                )}
              </div>
              <h2 className="font-display font-bold text-lg text-surface-900 dark:text-white">
                {t('setup.criteria_title')}
              </h2>
            </div>

            <div className="flex items-center gap-2">
              {criteriaApproved ? (
                <button
                  type="button"
                  onClick={() => setCriteriaApproved(false)}
                  className="btn btn-sm btn-secondary"
                >
                  <Edit3 className="w-3.5 h-3.5" />
                  Edit Criteria
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleGenerateCriteria}
                  disabled={loadingCriteria}
                  className="btn btn-sm btn-secondary"
                >
                  {loadingCriteria ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5 text-primary-500" />}
                  <span>Agent 2: Auto-Generate</span>
                </button>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* INCLUSION */}
            <div className="space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-surface-100 dark:border-surface-800">
                <h4 className="font-semibold text-xs text-emerald-600 dark:text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4" />
                  {t('setup.inclusion')}
                </h4>
                <span className="badge badge-success text-[10px]">
                  {projectData.criteria_include.length}
                </span>
              </div>
              
              {!criteriaApproved && (
                <div className="flex gap-2">
                  <input 
                    type="text" value={newInclude} onChange={e => setNewInclude(e.target.value)} onKeyDown={e => e.key === 'Enter' && addInclude()}
                    placeholder={t('setup.inclusion_placeholder')}
                    className="input input-sm flex-1"
                  />
                  <button onClick={addInclude} className="btn btn-sm btn-secondary px-3">
                    <Plus className="w-4 h-4"/>
                  </button>
                </div>
              )}
              
              <ul className="space-y-2">
                {projectData.criteria_include.map((item, idx) => (
                  <li key={idx} className="group flex justify-between items-start bg-emerald-50/50 dark:bg-emerald-950/20 p-3 rounded-lg text-xs font-medium border border-emerald-100 dark:border-emerald-900/30 text-surface-700 dark:text-surface-300">
                    <span className="pr-3 leading-relaxed">{item}</span>
                    {!criteriaApproved && (
                      <button onClick={() => setProjectData(p => ({...p, criteria_include: p.criteria_include.filter((_, i) => i !== idx)}))} className="text-surface-400 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100 flex-shrink-0">
                        <X className="w-3.5 h-3.5"/>
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            </div>

            {/* EXCLUSION */}
            <div className="space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-surface-100 dark:border-surface-800">
                <h4 className="font-semibold text-xs text-rose-600 dark:text-rose-400 uppercase tracking-wider flex items-center gap-1.5">
                  <AlertCircle className="w-4 h-4" />
                  {t('setup.exclusion')}
                </h4>
                <span className="badge badge-danger text-[10px]">
                  {projectData.criteria_exclude.length}
                </span>
              </div>
              
              {!criteriaApproved && (
                <div className="flex gap-2">
                  <input 
                    type="text" value={newExclude} onChange={e => setNewExclude(e.target.value)} onKeyDown={e => e.key === 'Enter' && addExclude()}
                    placeholder={t('setup.exclusion_placeholder')}
                    className="input input-sm flex-1"
                  />
                  <button onClick={addExclude} className="btn btn-sm btn-secondary px-3">
                    <Plus className="w-4 h-4"/>
                  </button>
                </div>
              )}
              
              <ul className="space-y-2">
                {projectData.criteria_exclude.map((item, idx) => (
                  <li key={idx} className="group flex justify-between items-start bg-rose-50/50 dark:bg-rose-950/20 p-3 rounded-lg text-xs font-medium border border-rose-100 dark:border-rose-900/30 text-surface-700 dark:text-surface-300">
                    <span className="pr-3 leading-relaxed">{item}</span>
                    {!criteriaApproved && (
                      <button onClick={() => setProjectData(p => ({...p, criteria_exclude: p.criteria_exclude.filter((_, i) => i !== idx)}))} className="text-surface-400 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100 flex-shrink-0">
                        <X className="w-3.5 h-3.5"/>
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {!criteriaApproved && (
            <div className="pt-4 mt-6 border-t border-surface-100 dark:border-surface-800 flex justify-end">
              <button 
                type="button" onClick={handleApproveCriteria} disabled={loading}
                className="btn btn-primary"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
                <span>Approve & Save Criteria</span>
              </button>
            </div>
          )}
        </div>
      )}

      {/* ── PHASE 3: PICO FRAMEWORK & KEYWORDS ──────────────────────────── */}
      {criteriaApproved && (
        <div ref={step3CardRef} className="space-y-6 animate-slide-up">
          <div className="card p-8 text-center rounded-2xl bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-950 text-white space-y-5 shadow-2xl border border-indigo-500/30">
            <div className="w-14 h-14 mx-auto rounded-2xl bg-indigo-500/20 border border-indigo-400/30 flex items-center justify-center shadow-inner">
              <Search className="w-7 h-7 text-indigo-300" />
            </div>
            
            <div className="max-w-2xl mx-auto space-y-2">
              <span className="badge bg-indigo-500/20 text-indigo-300 border border-indigo-400/30 text-xs font-bold uppercase tracking-wider">
                PHASE 03 / QUERY & PICO SYNTHESIS
              </span>
              <h3 className="font-display font-black text-2xl sm:text-3xl text-white tracking-tight">
                Phân tích Khung PICO & Bộ Từ khóa Tìm kiếm
              </h3>
              <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
                Agent 3 sẽ bóc tách đề tài của bạn thành 4 thành tố PICO (Population, Intervention, Comparison, Outcome) và sinh bộ từ khóa học thuật tiếng Anh chuẩn xác cho Google Scholar & Scopus.
              </p>
            </div>
            
            <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
              <button 
                onClick={handleSuggestKeywords} 
                disabled={loadingKeywords}
                className="btn bg-white text-slate-900 hover:bg-slate-100 hover:scale-105 transition-all text-sm font-bold shadow-xl px-6 py-3 rounded-xl flex items-center gap-2 cursor-pointer"
              >
                {loadingKeywords ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin text-indigo-600" />
                    <span>AI đang phân tích PICO & Từ khóa...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-5 h-5 text-amber-500" />
                    <span>{picoData ? 'Tái tạo lại Khung PICO & Từ khóa' : 'Bắt đầu Phân tích PICO & Sinh Từ khóa'}</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {picoData && (
            <div ref={picoCardRef} className="card p-6 sm:p-8 space-y-6 animate-slide-up border-emerald-500/30 bg-emerald-500/5">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-surface-200 dark:border-surface-800">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-emerald-100 dark:bg-emerald-950/60 border border-emerald-500/30 flex items-center justify-center">
                    <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
                  </div>
                  <div>
                    <h4 className="font-display font-bold text-lg text-surface-900 dark:text-white">
                      Kết quả Phân tích Khung PICO
                    </h4>
                    <p className="text-xs text-surface-500 dark:text-surface-400">
                      Cấu trúc 4 thành tố nghiên cứu và bộ từ khóa tìm kiếm đã sẵn sàng
                    </p>
                  </div>
                </div>

                <button 
                  onClick={handleProceedToSearch}
                  className="btn btn-primary shadow-primary-sm self-start sm:self-auto flex items-center gap-2"
                >
                  <span>Chuyển sang Bước 2: Tìm kiếm</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>

              {/* 4 PICO Blocks */}
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
                <div className="p-4 rounded-xl bg-white dark:bg-surface-800/80 border border-primary-100 dark:border-primary-900/30 shadow-xs space-y-1.5">
                  <span className="section-label text-primary-600 dark:text-primary-400 block font-bold">
                    [P] Population / Đối tượng:
                  </span>
                  <p className="text-xs font-semibold text-surface-900 dark:text-surface-100 leading-relaxed">
                    {picoData.population || 'N/A'}
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-white dark:bg-surface-800/80 border border-indigo-100 dark:border-indigo-900/30 shadow-xs space-y-1.5">
                  <span className="section-label text-indigo-600 dark:text-indigo-400 block font-bold">
                    [I] Intervention / Can thiệp:
                  </span>
                  <p className="text-xs font-semibold text-surface-900 dark:text-surface-100 leading-relaxed">
                    {picoData.intervention || 'N/A'}
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-white dark:bg-surface-800/80 border border-amber-100 dark:border-amber-900/30 shadow-xs space-y-1.5">
                  <span className="section-label text-amber-600 dark:text-amber-400 block font-bold">
                    [C] Comparison / So sánh:
                  </span>
                  <p className="text-xs font-semibold text-surface-900 dark:text-surface-100 leading-relaxed">
                    {picoData.comparison || 'N/A'}
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-white dark:bg-surface-800/80 border border-emerald-100 dark:border-emerald-900/30 shadow-xs space-y-1.5">
                  <span className="section-label text-emerald-600 dark:text-emerald-400 block font-bold">
                    [O] Outcome / Kết quả:
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
                    Bộ Từ khóa Học thuật Đề xuất (Academic Search Keywords)
                  </span>

                  {picoData.search_keywords && picoData.search_keywords.length > 0 && (
                    <button
                      onClick={handleCopyKeywords}
                      className="btn btn-sm btn-ghost text-xs text-white hover:bg-white/10 self-start sm:self-auto"
                    >
                      {copiedKeywords ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copiedKeywords ? 'Đã sao chép!' : 'Sao chép chuỗi tìm kiếm'}</span>
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
                    💡 <strong className="text-surface-200">Bước tiếp theo:</strong> Nhấn nút bên cạnh để chuyển sang tab Tìm kiếm. Toàn bộ từ khóa sẽ được tự động điền sẵn vào thanh tìm kiếm.
                  </p>

                  <button 
                    onClick={handleProceedToSearch}
                    className="btn btn-primary btn-lg font-bold shrink-0 flex items-center justify-center gap-2 shadow-primary-md"
                  >
                    <span>Tiến hành Tìm kiếm Bài báo</span>
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
