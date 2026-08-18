import React, { useState, useEffect, useRef } from 'react';
import { 
  BookOpen, Target, Settings, Save, Loader2, Wand2, Plus, X, 
  CheckCircle2, Sparkles, Compass, AlertCircle, ArrowRight, Check,
  ChevronDown, ChevronUp, Layers, HelpCircle, UserCheck, ShieldCheck,
  Edit3, Unlock, Lock, Copy, Search, ArrowDown
} from 'lucide-react';
import { normalizeResearchSetup } from '../../utils/researchSetup';
import { useLanguage } from '../../contexts/LanguageContext';

import { API_BASE } from '../../utils/apiConfig';
const DEFAULT_PROJECT_ID = '00000000-0000-0000-0000-000000000001';

export default function ResearchSetupTab({ setActiveTab, darkMode }) {
  const { t } = useLanguage();
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);
  
  const [projectData, setProjectData] = useState(() => {
    return normalizeResearchSetup({});
  });

  const [newInclude, setNewInclude] = useState('');
  const [newExclude, setNewExclude] = useState('');

  // Human-in-the-Loop (HITL) Gate Statuses
  const [topicApproved, setTopicApproved] = useState(() => {
    return localStorage.getItem('slr_gate1_topic_approved') === 'true';
  });
  const [criteriaApproved, setCriteriaApproved] = useState(() => {
    return localStorage.getItem('slr_gate2_criteria_approved') === 'true';
  });

  // State: Agent 1 (Scope Optimizer)
  const [scopeResult, setScopeResult] = useState(() => {
    try {
      const cached = localStorage.getItem('slr_scope_result');
      if (cached) return JSON.parse(cached);
    } catch (e) {}
    return null;
  });
  const [loadingScope, setLoadingScope] = useState(false);
  const [appliedTopicToast, setAppliedTopicToast] = useState(null);

  // State: Agent 2 (Criteria Generator)
  const [loadingCriteria, setLoadingCriteria] = useState(false);
  const [criteriaToast, setCriteriaToast] = useState(false);

  // State: Agent 3 (PICO & Keywords Finder)
  const [suggestedKeywords, setSuggestedKeywords] = useState(() => {
    try {
      const cached = localStorage.getItem('suggested_keywords');
      if (cached) return JSON.parse(cached);
    } catch (e) {}
    return [];
  });
  const [picoData, setPicoData] = useState(() => {
    try {
      const cached = localStorage.getItem('slr_pico_data');
      if (cached) return JSON.parse(cached);
    } catch (e) {}
    return null;
  });
  const [gapMapData, setGapMapData] = useState(() => {
    try {
      const cached = localStorage.getItem('slr_gap_map');
      if (cached) return JSON.parse(cached);
    } catch (e) {}
    return null;
  });
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

  useEffect(() => {
    const fetchProject = async () => {
      try {
        const res = await fetch(`${API_BASE}/projects/${DEFAULT_PROJECT_ID}`);
        if (res.ok) {
          const data = await res.json();
          const normalized = normalizeResearchSetup(data);
          setProjectData(normalized);
          localStorage.setItem('research_setup_data', JSON.stringify(normalized));
        }
      } catch (err) {
        console.error("DB connection error:", err);
      }
    };
    fetchProject();
  }, []);

  // --- SAVE HELPER ---
  const persistProject = async (updatedData) => {
    const dataToSave = updatedData || projectData;
    localStorage.setItem('research_setup_data', JSON.stringify(dataToSave));
    window.dispatchEvent(new Event('research_setup_updated'));
    try {
      await fetch(`${API_BASE}/projects/${DEFAULT_PROJECT_ID}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dataToSave)
      });
    } catch (err) {
      console.error("Save error:", err);
    }
  };

  // --- AGENT 1: NHẬN XÉT PHẠM VI ĐỀ TÀI ---
  const handleOptimizeScope = async () => {
    const ideaText = projectData.research_question || projectData.name;
    if (!ideaText || ideaText.trim().length < 3) {
      setErrorMsg("Vui lòng nhập câu hỏi hoặc tên đề tài nghiên cứu trước khi nhận xét phạm vi!");
      return;
    }

    setLoadingScope(true);
    setErrorMsg(null);

    try {
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
        localStorage.setItem('slr_scope_result', JSON.stringify(data));
        scrollToRef(scopeCardRef);
      } else {
        setErrorMsg("Không thể kết nối đến Agent Nhận xét phạm vi.");
      }
    } catch (err) {
      console.error(err);
      setErrorMsg("Lỗi khi chạy Nhận xét phạm vi đề tài.");
    } finally {
      setLoadingScope(false);
    }
  };

  const handleApplyTopic = (topic) => {
    setProjectData(p => ({ ...p, research_question: topic }));
    setAppliedTopicToast(topic);
    setTimeout(() => setAppliedTopicToast(null), 3500);
  };

  // --- CỔNG DUYỆT 1: HUMAN PHÊ DUYỆT ĐỀ TÀI ---
  const handleApproveTopic = async (approvedTopic) => {
    let updated = { ...projectData };
    if (approvedTopic && typeof approvedTopic === 'string') {
      updated.research_question = approvedTopic;
      setProjectData(updated);
    }
    
    setTopicApproved(true);
    localStorage.setItem('slr_gate1_topic_approved', 'true');
    await persistProject(updated);

    scrollToRef(criteriaCardRef);

    // Tự động kích hoạt Agent 2 sinh tiêu chí nếu chưa có tiêu chí
    if (updated.criteria_include.length === 0 && updated.criteria_exclude.length === 0) {
      await handleGenerateCriteriaWithTopic(updated.research_question || updated.name, updated.research_field);
    }
  };

  // --- AGENT 2: TỰ ĐỘNG SINH TIÊU CHÍ ---
  const handleGenerateCriteriaWithTopic = async (topic, field) => {
    setLoadingCriteria(true);
    setErrorMsg(null);
    try {
      const res = await fetch(`${API_BASE}/slr-swarm/generate-criteria`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          idea: topic,
          research_field: field || ''
        })
      });

      if (res.ok) {
        const data = await res.json();
        const newInc = data.criteria_include || [];
        const newExc = data.criteria_exclude || [];
        
        setProjectData(p => ({
          ...p,
          criteria_include: newInc,
          criteria_exclude: newExc
        }));

        setCriteriaToast(true);
        setTimeout(() => setCriteriaToast(false), 3500);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingCriteria(false);
    }
  };

  const handleGenerateCriteria = async () => {
    const ideaText = projectData.research_question || projectData.name;
    if (!ideaText || ideaText.trim().length < 3) {
      setErrorMsg("Vui lòng nhập câu hỏi hoặc tên đề tài nghiên cứu trước khi sinh tiêu chí!");
      return;
    }
    await handleGenerateCriteriaWithTopic(ideaText, projectData.research_field);
  };

  // --- CỔNG DUYỆT 2: HUMAN PHÊ DUYỆT TIÊU CHÍ & LƯU CẤU HÌNH ---
  const handleApproveCriteria = async () => {
    setLoading(true);
    setCriteriaApproved(true);
    localStorage.setItem('slr_gate2_criteria_approved', 'true');
    await persistProject();
    setSaved(true);
    setLoading(false);
    setTimeout(() => setSaved(false), 3500);
    scrollToRef(step3CardRef);
  };

  // --- AGENT 3: PHÂN TÍCH PICO & TỪ KHÓA ---
  const handleSuggestKeywords = async () => {
    setLoadingKeywords(true);
    setErrorMsg(null);
    try {
      const ideaText = projectData.research_question || projectData.name;
      if (!ideaText) {
        setErrorMsg("Vui lòng nhập câu hỏi hoặc tên đề tài nghiên cứu!");
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
        
        if (data.pico) {
          setPicoData(data.pico);
          localStorage.setItem('slr_pico_data', JSON.stringify(data.pico));
          
          const rawKws = data.pico.search_keywords || [];
          const kwList = rawKws.filter(kw => 
            kw && kw.trim().length >= 3 && /^[a-zA-Z0-9\s\-\/&]+$/.test(kw.trim())
          );
          
          if (kwList.length > 0) {
            setSuggestedKeywords(kwList);
            localStorage.setItem('suggested_keywords', JSON.stringify(kwList));
          }
          
          const boolQuery = kwList.length > 0 ? kwList.join(' ') : (data.pico.boolean_query || '');
          if (boolQuery) {
             localStorage.setItem('litreview_active_mesh_query', boolQuery);
             window.dispatchEvent(new Event('new_mesh_query_ready'));
          }

          scrollToRef(picoCardRef);
        }
        
        if (data.gap_map) {
          setGapMapData(data.gap_map);
          localStorage.setItem('slr_gap_map', JSON.stringify(data.gap_map));
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
    <div className="max-w-4xl mx-auto space-y-6 pb-12">
      
      {/* 🧭 PROGRESS TRACKER (3 GIAI ĐOẠN HỘI ĐỒNG) */}
      <div className={`p-4 md:p-5 rounded-3xl border ${
        darkMode ? 'bg-slate-900/90 border-slate-800' : 'bg-white border-slate-200'
      } shadow-sm backdrop-blur-sm`}>
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 text-xs">
          
          {/* Step 1 */}
          <div className="flex items-center gap-3">
            <div className={`w-8 h-8 rounded-2xl flex items-center justify-center font-bold text-xs shrink-0 transition-all ${
              topicApproved 
                ? 'bg-emerald-600 text-white shadow-sm' 
                : 'bg-indigo-600 text-white ring-4 ring-indigo-100 dark:ring-indigo-950 shadow-md'
            }`}>
              {topicApproved ? <Check className="w-4 h-4" /> : '1'}
            </div>
            <div>
              <span className="font-extrabold text-slate-800 dark:text-slate-200 text-xs block">
                1. Định hình Đề tài
              </span>
              <span className="text-[11px] text-slate-500 font-medium">
                {topicApproved ? '✓ Đã phê duyệt' : 'Agent 1 ➔ Chờ duyệt'}
              </span>
            </div>
          </div>

          <div className="hidden sm:block w-8 h-[2px] bg-slate-200 dark:bg-slate-800" />

          {/* Step 2 */}
          <div className="flex items-center gap-3">
            <div className={`w-8 h-8 rounded-2xl flex items-center justify-center font-bold text-xs shrink-0 transition-all ${
              criteriaApproved 
                ? 'bg-emerald-600 text-white shadow-sm' 
                : topicApproved 
                ? 'bg-indigo-600 text-white ring-4 ring-indigo-100 dark:ring-indigo-950 shadow-md' 
                : 'bg-slate-100 dark:bg-slate-800 text-slate-400'
            }`}>
              {criteriaApproved ? <Check className="w-4 h-4" /> : '2'}
            </div>
            <div>
              <span className="font-extrabold text-slate-800 dark:text-slate-200 text-xs block">
                2. Tiêu chí Sàng lọc
              </span>
              <span className="text-[11px] text-slate-500 font-medium">
                {criteriaApproved ? '✓ Đã phê duyệt' : topicApproved ? 'Agent 2 ➔ Chờ duyệt' : 'Chưa mở'}
              </span>
            </div>
          </div>

          <div className="hidden sm:block w-8 h-[2px] bg-slate-200 dark:bg-slate-800" />

          {/* Step 3 */}
          <div className="flex items-center gap-3">
            <div className={`w-8 h-8 rounded-2xl flex items-center justify-center font-bold text-xs shrink-0 transition-all ${
              picoData 
                ? 'bg-emerald-600 text-white shadow-sm' 
                : criteriaApproved 
                ? 'bg-indigo-600 text-white ring-4 ring-indigo-100 dark:ring-indigo-950 shadow-md' 
                : 'bg-slate-100 dark:bg-slate-800 text-slate-400'
            }`}>
              {picoData ? <Check className="w-4 h-4" /> : '3'}
            </div>
            <div>
              <span className="font-extrabold text-slate-800 dark:text-slate-200 text-xs block">
                3. PICO & Từ khóa
              </span>
              <span className="text-[11px] text-slate-500 font-medium">
                {picoData ? '✓ Sẵn sàng tìm kiếm' : criteriaApproved ? 'Agent 3 ➔ Sẵn sàng sinh' : 'Chưa mở'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-2xl bg-rose-50 dark:bg-rose-950/50 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800 font-semibold text-xs flex items-center gap-2.5 shadow-sm animate-in fade-in">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {appliedTopicToast && (
        <div className="p-3.5 rounded-2xl bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 font-bold text-xs flex items-center justify-between shadow-sm animate-in fade-in slide-in-from-top-2">
          <div className="flex items-center gap-2">
            <Check className="w-4 h-4 text-emerald-600" />
            <span>Đã áp dụng câu hỏi nghiên cứu tinh chỉnh mới!</span>
          </div>
          <button onClick={() => setAppliedTopicToast(null)} className="text-slate-400 hover:text-slate-600">✕</button>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 1. GIAI ĐOẠN 1: CẤU HÌNH & PHÊ DUYỆT ĐỀ TÀI (CỔNG DUYỆT 1) */}
      {/* ========================================================================= */}
      <div className={`p-6 md:p-8 rounded-3xl border transition-all ${
        topicApproved 
          ? 'bg-white dark:bg-slate-900 border-emerald-500/40 shadow-sm' 
          : darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200 shadow-sm'
      }`}>
        
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-2xl flex items-center justify-center font-extrabold shadow-sm ${
              topicApproved ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300' : 'bg-blue-50 text-blue-600 dark:bg-slate-800 dark:text-sky-400'
            }`}>
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-xl font-black tracking-tight">{t('setup.title')}</h2>
              <p className="text-xs text-slate-500 font-medium mt-0.5">Giai đoạn 1: Thiết lập và tham vấn phạm vi nghiên cứu</p>
            </div>
          </div>

          {topicApproved && (
            <div className="flex items-center gap-2">
              <span className="px-3 py-1.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300 text-xs font-extrabold flex items-center gap-1.5 border border-emerald-200 dark:border-emerald-800 shadow-sm">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>Đã phê duyệt đề tài</span>
              </span>
              <button
                type="button"
                onClick={() => setTopicApproved(false)}
                className="p-1.5 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-600 transition-colors border border-slate-200 dark:border-slate-700"
                title="Mở khóa để chỉnh sửa lại đề tài"
              >
                <Edit3 className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>

        <div className="space-y-5">
          <div>
            <label className="block text-xs font-extrabold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-2">{t('setup.project_name')}</label>
            <input 
              type="text" 
              value={projectData.name}
              onChange={e => setProjectData({...projectData, name: e.target.value})}
              placeholder={t('setup.project_name_placeholder')}
              disabled={topicApproved}
              className={`w-full p-3.5 rounded-2xl border text-sm focus:ring-2 focus:ring-blue-500 disabled:opacity-75 disabled:cursor-not-allowed transition-colors ${darkMode ? 'bg-slate-800/80 border-slate-700 dark:text-white' : 'bg-slate-50 border-slate-200 text-slate-900'}`}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <label className="block text-xs font-extrabold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-2">{t('setup.research_question')}</label>
              <textarea 
                rows="3"
                value={projectData.research_question}
                onChange={e => setProjectData({...projectData, research_question: e.target.value})}
                placeholder={t('setup.research_question_placeholder')}
                disabled={topicApproved}
                className={`w-full p-3.5 rounded-2xl border text-sm focus:ring-2 focus:ring-blue-500 disabled:opacity-75 disabled:cursor-not-allowed transition-colors leading-relaxed ${darkMode ? 'bg-slate-800/80 border-slate-700 dark:text-white' : 'bg-slate-50 border-slate-200 text-slate-900'}`}
              />
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-extrabold uppercase tracking-wider text-slate-600 dark:text-slate-400 mb-2">{t('setup.research_field')}</label>
                <input 
                  type="text" 
                  value={projectData.research_field}
                  onChange={e => setProjectData({...projectData, research_field: e.target.value})}
                  placeholder={t('setup.research_field_placeholder')}
                  disabled={topicApproved}
                  className={`w-full p-3.5 rounded-2xl border text-sm focus:ring-2 focus:ring-blue-500 disabled:opacity-75 disabled:cursor-not-allowed transition-colors ${darkMode ? 'bg-slate-800/80 border-slate-700 dark:text-white' : 'bg-slate-50 border-slate-200 text-slate-900'}`}
                />
              </div>
              <div className="flex gap-4">
                <div className="flex-1">
                  <label className="block text-[11px] font-bold text-slate-500 mb-1">{t('setup.year_from')}</label>
                  <input type="number" disabled={topicApproved} value={projectData.year_from} onChange={e => setProjectData({...projectData, year_from: parseInt(e.target.value)})} className={`w-full p-2.5 rounded-xl border text-sm disabled:opacity-75 ${darkMode ? 'bg-slate-800 border-slate-700 dark:text-white' : 'bg-slate-50 border-slate-200 text-slate-900'}`} />
                </div>
                <div className="flex-1">
                  <label className="block text-[11px] font-bold text-slate-500 mb-1">{t('setup.year_to')}</label>
                  <input type="number" disabled={topicApproved} value={projectData.year_to} onChange={e => setProjectData({...projectData, year_to: parseInt(e.target.value)})} className={`w-full p-2.5 rounded-xl border text-sm disabled:opacity-75 ${darkMode ? 'bg-slate-800 border-slate-700 dark:text-white' : 'bg-slate-50 border-slate-200 text-slate-900'}`} />
                </div>
              </div>
            </div>
          </div>

          {/* Action Bar bên trong Thẻ 1 */}
          {!topicApproved && (
            <div className="pt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 dark:border-slate-800">
              <button
                type="button"
                onClick={handleOptimizeScope}
                disabled={loadingScope}
                className="px-5 py-3 rounded-2xl bg-amber-500 hover:bg-amber-600 text-white text-xs font-black transition-all shadow-sm hover:scale-[1.02] active:scale-95 flex items-center gap-2"
              >
                {loadingScope ? <Loader2 className="w-4 h-4 animate-spin" /> : <Compass className="w-4 h-4" />}
                <span>Agent 1: Nhận xét phạm vi đề tài</span>
              </button>

              {/* Nút Human Phê Duyệt đề tài hiện tại */}
              <button
                type="button"
                onClick={() => handleApproveTopic()}
                className="px-6 py-3 rounded-2xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-black transition-all shadow-md hover:scale-[1.02] active:scale-95 flex items-center gap-2"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>✓ Phê duyệt đề tài & Chuyển sang Bước 2</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ========================================================================= */}
      {/* 2. THẺ ĐÁNH GIÁ PHẠM VI ĐỀ TÀI (Sau khi Agent 1 phản hồi) */}
      {/* ========================================================================= */}
      {scopeResult && !topicApproved && (
        <div 
          ref={scopeCardRef}
          className={`p-6 md:p-8 rounded-3xl border transition-all scroll-mt-6 ${
            scopeResult.status === 'optimal'
              ? 'bg-emerald-500/5 border-emerald-500/30 dark:bg-emerald-950/20'
              : scopeResult.status === 'too_narrow'
              ? 'bg-purple-500/5 border-purple-500/30 dark:bg-purple-950/20'
              : 'bg-amber-500/5 border-amber-500/30 dark:bg-amber-950/20'
          } shadow-sm animate-in fade-in slide-in-from-top-4 duration-300 space-y-4`}
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <Compass className={`w-5 h-5 ${
                scopeResult.status === 'optimal' ? 'text-emerald-600 dark:text-emerald-400' :
                scopeResult.status === 'too_narrow' ? 'text-purple-600 dark:text-purple-400' : 'text-amber-600 dark:text-amber-400'
              }`} />
              <h3 className="font-extrabold text-sm text-slate-800 dark:text-slate-100">
                Đánh giá phạm vi đề tài (Agent 1: Scope Advisor)
              </h3>
            </div>
            
            <span className={`px-3 py-1 rounded-full text-xs font-black uppercase tracking-wider ${
              scopeResult.status === 'optimal'
                ? 'bg-emerald-600 text-white shadow-sm'
                : scopeResult.status === 'too_narrow'
                ? 'bg-purple-600 text-white shadow-sm'
                : 'bg-amber-600 text-white shadow-sm'
            }`}>
              {scopeResult.status === 'optimal' ? '✨ Vừa vặn / Tối ưu' :
               scopeResult.status === 'too_narrow' ? '🔍 Đề tài Quá hẹp' : '⚠️ Đề tài Quá rộng'}
            </span>
          </div>

          <p className="text-xs md:text-sm text-slate-700 dark:text-slate-300 leading-relaxed font-medium">
            {scopeResult.feedback}
          </p>

          {/* Gợi ý tinh chỉnh & Phê duyệt trực tiếp từng gợi ý */}
          {scopeResult.suggested_topics && scopeResult.suggested_topics.length > 0 && (
            <div className="space-y-2.5 pt-3 border-t border-slate-200/50 dark:border-slate-800/50">
              <span className="block text-xs font-extrabold uppercase tracking-wider text-slate-600 dark:text-slate-300">
                💡 Gợi ý tinh chỉnh đề tài (Chọn đề tài ưng ý để phê duyệt):
              </span>
              <div className="grid grid-cols-1 gap-2.5">
                {scopeResult.suggested_topics.map((topic, i) => (
                  <div 
                    key={i} 
                    className="p-4 rounded-2xl bg-white dark:bg-slate-800/90 border border-slate-200/80 dark:border-slate-700 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:border-indigo-400 dark:hover:border-indigo-500 transition-all shadow-sm"
                  >
                    <span className="text-xs font-medium text-slate-800 dark:text-slate-200 leading-relaxed">
                      {topic}
                    </span>
                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        type="button"
                        onClick={() => handleApplyTopic(topic)}
                        className="px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 text-slate-700 dark:text-slate-200 text-xs font-bold transition-colors"
                      >
                        Áp dụng
                      </button>
                      <button
                        type="button"
                        onClick={() => handleApproveTopic(topic)}
                        className="px-3.5 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-extrabold transition-transform hover:scale-105 flex items-center gap-1.5 shadow-sm"
                      >
                        <Check className="w-3.5 h-3.5" />
                        <span>Duyệt đề tài này</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* 2. GIAI ĐOẠN 2: THIẾT LẬP & PHÊ DUYỆT TIÊU CHÍ (CỔNG DUYỆT 2) */}
      {/* ========================================================================= */}
      {topicApproved && (
        <div 
          ref={criteriaCardRef}
          className={`p-6 md:p-8 rounded-3xl border transition-all space-y-6 scroll-mt-6 animate-in fade-in slide-in-from-bottom-3 ${
            criteriaApproved
              ? 'bg-white dark:bg-slate-900 border-emerald-500/40 shadow-sm'
              : darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200 shadow-sm'
          }`}
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-2xl flex items-center justify-center font-extrabold shadow-sm ${
                criteriaApproved ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300' : 'bg-emerald-50 text-emerald-600 dark:bg-slate-800 dark:text-emerald-400'
              }`}>
                <Target className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-xl font-black tracking-tight">{t('setup.criteria_title')}</h3>
                <p className="text-xs text-slate-500 font-medium mt-0.5">Giai đoạn 2: Tiêu chí chọn vào (Inclusion) và loại trừ (Exclusion) chuẩn PRISMA</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {criteriaApproved ? (
                <div className="flex items-center gap-2">
                  <span className="px-3 py-1.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300 text-xs font-extrabold flex items-center gap-1.5 border border-emerald-200 dark:border-emerald-800 shadow-sm">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    <span>Đã phê duyệt tiêu chí</span>
                  </span>
                  <button
                    type="button"
                    onClick={() => setCriteriaApproved(false)}
                    className="p-1.5 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-600 transition-colors border border-slate-200 dark:border-slate-700"
                    title="Mở khóa để chỉnh sửa lại tiêu chí"
                  >
                    <Edit3 className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={handleGenerateCriteria}
                  disabled={loadingCriteria}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-100 dark:hover:bg-emerald-900 border border-emerald-200 dark:border-emerald-800 font-bold text-xs shadow-sm transition-all"
                  title="Yêu cầu Agent 2 sinh lại tiêu chí mới"
                >
                  {loadingCriteria ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                  )}
                  <span>Agent 2: Sinh lại tiêu chí</span>
                </button>
              )}
            </div>
          </div>

          {criteriaToast && (
            <div className="p-3.5 rounded-2xl bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 font-bold text-xs flex items-center justify-between shadow-sm animate-in fade-in slide-in-from-top-2">
              <div className="flex items-center gap-2">
                <Check className="w-4 h-4 text-emerald-600" />
                <span>Agent 2 đã tự động gợi ý trọn bộ tiêu chí Inclusion & Exclusion!</span>
              </div>
              <button onClick={() => setCriteriaToast(false)} className="text-slate-400 hover:text-slate-600">✕</button>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Inclusion */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="font-extrabold text-emerald-600 dark:text-emerald-400 text-xs uppercase tracking-wider flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>{t('setup.inclusion')}</span>
                </h4>
                <span className="text-xs text-slate-400 font-bold">({projectData.criteria_include.length} tiêu chí)</span>
              </div>
              {!criteriaApproved && (
                <div className="flex gap-2">
                  <input 
                    type="text" 
                    value={newInclude}
                    onChange={e => setNewInclude(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && addInclude()}
                    placeholder={t('setup.inclusion_placeholder')}
                    autoComplete="off"
                    className={`flex-1 p-3 rounded-xl border text-xs ${darkMode ? 'bg-slate-800/80 border-slate-700 dark:text-white' : 'bg-slate-50 text-slate-900 border-slate-200'}`}
                  />
                  <button onClick={addInclude} className="p-3 bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 rounded-xl hover:bg-emerald-200 transition-colors">
                    <Plus className="w-4 h-4"/>
                  </button>
                </div>
              )}
              <ul className="space-y-2.5 mt-3">
                {projectData.criteria_include.map((item, idx) => (
                  <li key={idx} className="flex justify-between items-center bg-emerald-50/70 dark:bg-emerald-950/20 p-3 rounded-2xl text-xs font-medium border border-emerald-100 dark:border-emerald-800/50 animate-in fade-in slide-in-from-left-4 duration-300 text-slate-800 dark:text-slate-200">
                    <span className="pr-2 leading-relaxed">{item}</span>
                    {!criteriaApproved && (
                      <button onClick={() => setProjectData(p => ({...p, criteria_include: p.criteria_include.filter((_, i) => i !== idx)}))} className="text-slate-400 hover:text-rose-500 transition-colors p-1">
                        <X className="w-3.5 h-3.5"/>
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            </div>

            {/* Exclusion */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="font-extrabold text-rose-600 dark:text-rose-400 text-xs uppercase tracking-wider flex items-center gap-1.5">
                  <AlertCircle className="w-4 h-4" />
                  <span>{t('setup.exclusion')}</span>
                </h4>
                <span className="text-xs text-slate-400 font-bold">({projectData.criteria_exclude.length} tiêu chí)</span>
              </div>
              {!criteriaApproved && (
                <div className="flex gap-2">
                  <input 
                    type="text" 
                    value={newExclude}
                    onChange={e => setNewExclude(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && addExclude()}
                    placeholder={t('setup.exclusion_placeholder')}
                    autoComplete="off"
                    className={`flex-1 p-3 rounded-xl border text-xs ${darkMode ? 'bg-slate-800/80 border-slate-700 dark:text-white' : 'bg-slate-50 text-slate-900 border-slate-200'}`}
                  />
                  <button onClick={addExclude} className="p-3 bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-300 rounded-xl hover:bg-rose-200 transition-colors">
                    <Plus className="w-4 h-4"/>
                  </button>
                </div>
              )}
              <ul className="space-y-2.5 mt-3">
                {projectData.criteria_exclude.map((item, idx) => (
                  <li key={idx} className="flex justify-between items-center bg-rose-50/70 dark:bg-rose-950/20 p-3 rounded-2xl text-xs font-medium border border-rose-100 dark:border-rose-800/50 animate-in fade-in slide-in-from-right-4 duration-300 text-slate-800 dark:text-slate-200">
                    <span className="pr-2 leading-relaxed">{item}</span>
                    {!criteriaApproved && (
                      <button onClick={() => setProjectData(p => ({...p, criteria_exclude: p.criteria_exclude.filter((_, i) => i !== idx)}))} className="text-slate-400 hover:text-rose-500 transition-colors p-1">
                        <X className="w-3.5 h-3.5"/>
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Action Bar Bước 2: Human Phê Duyệt Tiêu Chí & Lưu */}
          {!criteriaApproved && (
            <div className="pt-4 border-t border-slate-100 dark:border-slate-800 flex justify-end">
              <button 
                type="button"
                onClick={handleApproveCriteria}
                disabled={loading}
                className="px-8 py-3.5 rounded-2xl font-black text-xs bg-emerald-600 hover:bg-emerald-700 text-white flex items-center justify-center gap-2 shadow-md transition-all hover:scale-[1.02] active:scale-95"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
                <span>✓ Phê duyệt bộ tiêu chí & Lưu cấu hình</span>
              </button>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* 3. GIAI ĐOẠN 3: PHÂN TÍCH PICO & TỪ KHÓA (CỔNG DUYỆT 3) */}
      {/* ========================================================================= */}
      {criteriaApproved && (
        <div 
          ref={step3CardRef}
          className="pt-2 space-y-6 scroll-mt-6 animate-in fade-in slide-in-from-bottom-3"
        >
          <div className="flex flex-col items-center justify-center p-8 rounded-3xl bg-gradient-to-b from-indigo-50/80 to-slate-50/50 dark:from-indigo-950/20 dark:to-slate-900/40 border border-indigo-200/60 dark:border-indigo-800/40 text-center space-y-3 shadow-sm">
            <div className="w-12 h-12 rounded-2xl bg-indigo-600 text-white flex items-center justify-center font-black shadow-md">
              <Wand2 className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-lg font-black text-slate-900 dark:text-slate-100 tracking-tight">
                Giai đoạn 3: Phân tích Khung PICO & Xuất Bộ Từ khóa Học thuật
              </h3>
              <p className="text-xs text-slate-600 dark:text-slate-400 max-w-lg mt-1 leading-relaxed">
                Agent 3 (PICO & Query Synthesizer) sẽ tổng hợp toàn bộ Đề tài và Bộ tiêu chí bạn đã phê duyệt để xây dựng chuỗi từ khóa tra cứu tối ưu.
              </p>
            </div>
            
            <button 
              onClick={handleSuggestKeywords}
              disabled={loadingKeywords}
              className="px-8 py-4 rounded-2xl font-black bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-700 hover:to-blue-700 text-white transition-all flex items-center justify-center gap-3 shadow-lg hover:scale-[1.02] active:scale-95 text-xs"
            >
              {loadingKeywords ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4 text-amber-300" />}
              <span>Agent 3: Phân tích PICO & Sinh từ khóa gợi ý</span>
            </button>
          </div>

          {/* KẾT QUẢ TRA CỨU PICO & KEYWORDS */}
          {picoData && (
            <div 
              ref={picoCardRef}
              className={`p-6 md:p-8 rounded-3xl border border-indigo-200/80 bg-gradient-to-br from-indigo-50/40 via-white to-slate-50 dark:from-indigo-950/20 dark:via-slate-900 dark:to-slate-900 dark:border-indigo-800/60 shadow-md space-y-6 scroll-mt-6 animate-in fade-in slide-in-from-bottom-4 duration-500`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-2xl bg-indigo-600 text-white flex items-center justify-center font-black shadow-md">
                    <CheckCircle2 className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="text-lg font-black text-slate-900 dark:text-slate-100 tracking-tight">
                      Kết quả tra cứu PICO & Từ khóa
                    </h4>
                    <p className="text-xs text-indigo-600 dark:text-indigo-400 font-bold mt-0.5">Khung phân tích nghiên cứu & Đề xuất từ khoá đã qua phê duyệt</p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleSuggestKeywords}
                  disabled={loadingKeywords}
                  className="p-2 rounded-xl text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                  title="Chạy lại Agent 3"
                >
                  <Loader2 className={`w-4 h-4 ${loadingKeywords ? 'animate-spin' : 'hidden'}`} />
                </button>
              </div>

              {/* 4 Khung PICO */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-white dark:bg-slate-800/80 p-5 rounded-2xl border border-slate-200/70 dark:border-slate-700/70 shadow-sm space-y-1">
                  <strong className="block text-indigo-700 dark:text-indigo-400 text-xs font-black uppercase tracking-wider">Vấn đề / Đối tượng nghiên cứu:</strong>
                  <p className="text-xs md:text-sm font-medium text-slate-800 dark:text-slate-200 leading-relaxed">{picoData.population}</p>
                </div>
                <div className="bg-white dark:bg-slate-800/80 p-5 rounded-2xl border border-slate-200/70 dark:border-slate-700/70 shadow-sm space-y-1">
                  <strong className="block text-emerald-700 dark:text-emerald-400 text-xs font-black uppercase tracking-wider">Giải pháp / Kỹ thuật chính:</strong>
                  <p className="text-xs md:text-sm font-medium text-slate-800 dark:text-slate-200 leading-relaxed">{picoData.intervention}</p>
                </div>
                <div className="bg-white dark:bg-slate-800/80 p-5 rounded-2xl border border-slate-200/70 dark:border-slate-700/70 shadow-sm space-y-1">
                  <strong className="block text-amber-700 dark:text-amber-400 text-xs font-black uppercase tracking-wider">Phương pháp đối chứng:</strong>
                  <p className="text-xs md:text-sm font-medium text-slate-800 dark:text-slate-200 leading-relaxed">{picoData.comparison || "Không áp dụng"}</p>
                </div>
                <div className="bg-white dark:bg-slate-800/80 p-5 rounded-2xl border border-slate-200/70 dark:border-slate-700/70 shadow-sm space-y-1">
                  <strong className="block text-sky-700 dark:text-sky-400 text-xs font-black uppercase tracking-wider">Kết quả đánh giá mong đợi:</strong>
                  <p className="text-xs md:text-sm font-medium text-slate-800 dark:text-slate-200 leading-relaxed">{picoData.outcome}</p>
                </div>
              </div>

              {/* Khối từ khóa gợi ý */}
              <div className="p-5 bg-slate-900 text-slate-100 rounded-2xl border border-slate-800 shadow-inner space-y-3.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-extrabold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>Các từ khóa gợi ý tra cứu:</span>
                  </span>
                  {picoData.search_keywords && picoData.search_keywords.length > 0 && (
                    <button
                      type="button"
                      onClick={handleCopyKeywords}
                      className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-amber-300 rounded-xl text-xs font-bold shrink-0 transition-colors border border-slate-700 shadow-sm flex items-center gap-1.5"
                    >
                      {copiedKeywords ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copiedKeywords ? 'Đã sao chép!' : 'Sao chép từ khóa'}</span>
                    </button>
                  )}
                </div>

                <div className="flex flex-wrap gap-2 pt-1">
                  {(picoData.search_keywords || []).map((kw, i) => (
                    <span key={i} className="px-3.5 py-1.5 bg-indigo-600/90 text-white rounded-xl text-xs font-bold border border-indigo-400/30 shadow-sm hover:scale-105 transition-transform cursor-default">
                      {kw}
                    </span>
                  ))}
                </div>
              </div>

              {/* Nút chuyển tiếp sang Tab Tìm kiếm */}
              <div className="flex justify-end pt-2">
                 <button 
                    onClick={() => setActiveTab('search')}
                    className="px-8 py-3.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white rounded-2xl font-black text-xs shadow-lg transition-transform hover:scale-[1.02] active:scale-95 flex items-center gap-2"
                 >
                    <span>Đem Keyword đi Tìm kiếm</span>
                    <ArrowRight className="w-4 h-4" />
                 </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
