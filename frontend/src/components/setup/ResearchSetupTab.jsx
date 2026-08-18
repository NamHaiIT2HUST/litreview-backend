import React, { useState } from 'react';
import { 
  BookOpen, Target, Settings, Save, Loader2, Wand2, Plus, X, 
  CheckCircle2, Sparkles, Compass, AlertCircle, ArrowRight, Check,
  Flame, Sliders, ShieldCheck
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
  const [suggestedKeywords, setSuggestedKeywords] = useState(() => {
    try {
      const cached = localStorage.getItem('suggested_keywords');
      if (cached) return JSON.parse(cached);
    } catch (e) {
      console.error(e);
    }
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

  // State for Scope Optimizer Agent (Agent Cố Vấn Phạm Vi)
  const [scopeResult, setScopeResult] = useState(() => {
    try {
      const cached = localStorage.getItem('slr_scope_result');
      if (cached) return JSON.parse(cached);
    } catch (e) {}
    return null;
  });
  const [loadingScope, setLoadingScope] = useState(false);
  const [appliedTopicToast, setAppliedTopicToast] = useState(null);

  // State for Criteria Auto-Generator Agent (Agent Tự Động Sinh Tiêu Chí)
  const [loadingCriteria, setLoadingCriteria] = useState(false);
  const [criteriaToast, setCriteriaToast] = useState(false);

  const [loadingKeywords, setLoadingKeywords] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  React.useEffect(() => {
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

  const handleSave = async () => {
    setLoading(true);
    setSaved(false);
    localStorage.setItem('research_setup_data', JSON.stringify(projectData));
    window.dispatchEvent(new Event('research_setup_updated'));
    try {
      const res = await fetch(`${API_BASE}/projects/${DEFAULT_PROJECT_ID}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(projectData)
      });
      if (res.ok) {
        setSaved(true);
      } else {
        setSaved(true);
      }
    } catch (err) {
      console.error("Save error:", err);
      setSaved(true);
    } finally {
      setLoading(false);
      setTimeout(() => setSaved(false), 4000);
    }
  };

  // --- AGENT 1: SCOPE OPTIMIZER (Cố vấn phạm vi đề tài) ---
  const handleOptimizeScope = async () => {
    const ideaText = projectData.research_question || projectData.name;
    if (!ideaText || ideaText.trim().length < 3) {
      setErrorMsg("Vui lòng nhập câu hỏi hoặc tên đề tài nghiên cứu trước khi cố vấn phạm vi!");
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
      } else {
        setErrorMsg("Không thể kết nối đến Scope Optimizer Agent.");
      }
    } catch (err) {
      console.error(err);
      setErrorMsg("Lỗi khi chạy Scope Optimizer Agent.");
    } finally {
      setLoadingScope(false);
    }
  };

  const handleApplyTopic = (topic) => {
    setProjectData(p => ({ ...p, research_question: topic }));
    setAppliedTopicToast(topic);
    setTimeout(() => setAppliedTopicToast(null), 3500);
  };

  // --- AGENT 2: CRITERIA AUTO-GENERATOR (Tự động sinh tiêu chí) ---
  const handleGenerateCriteria = async () => {
    const ideaText = projectData.research_question || projectData.name;
    if (!ideaText || ideaText.trim().length < 3) {
      setErrorMsg("Vui lòng nhập câu hỏi hoặc tên đề tài nghiên cứu trước khi sinh tiêu chí!");
      return;
    }

    setLoadingCriteria(true);
    setErrorMsg(null);

    try {
      const res = await fetch(`${API_BASE}/slr-swarm/generate-criteria`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          idea: ideaText,
          research_field: projectData.research_field || ''
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
      } else {
        setErrorMsg("Không thể kết nối đến Criteria Generator Agent.");
      }
    } catch (err) {
      console.error(err);
      setErrorMsg("Lỗi khi chạy Criteria Generator Agent.");
    } finally {
      setLoadingCriteria(false);
    }
  };

  // --- AGENT 3: PICO & KEYWORDS FINDER ---
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
        
        // PICO & Keywords
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
        }
        
        if (data.gap_map) {
          setGapMapData(data.gap_map);
          localStorage.setItem('slr_gap_map', JSON.stringify(data.gap_map));
        }

      } else {
        setErrorMsg(t('setup.error_ai') + ' (Agent 1 failed)');
      }
    } catch (err) {
      console.error(err);
      setErrorMsg(t('setup.error_server'));
    } finally {
      setLoadingKeywords(false);
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
    <div className="max-w-4xl mx-auto space-y-6">
      
      {/* Header Banner with Multi-Agent Swarm Badge */}
      <div className={`p-6 md:p-8 rounded-3xl border shadow-sm ${darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'}`}>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-3">
            <BookOpen className="w-8 h-8 text-blue-600 dark:text-sky-400" />
            <div>
              <h2 className="text-2xl font-extrabold">{t('setup.title')}</h2>
              <p className="text-xs text-slate-500 font-medium mt-0.5">Thiết lập bài toán nghiên cứu với sự hỗ trợ của Multi-Agent Swarm</p>
            </div>
          </div>
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300 text-xs font-bold shrink-0">
            <Sparkles className="w-3.5 h-3.5 text-amber-500 animate-pulse" />
            <span>Multi-Agent Swarm Active</span>
          </div>
        </div>
        
        {errorMsg && (
          <div className="mb-6 p-4 rounded-xl bg-red-50 dark:bg-red-950/50 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800 font-medium text-sm flex items-center gap-2">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {appliedTopicToast && (
          <div className="mb-6 p-3.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 font-bold text-xs flex items-center justify-between shadow-sm animate-in fade-in slide-in-from-top-2">
            <div className="flex items-center gap-2">
              <Check className="w-4 h-4 text-emerald-600" />
              <span>Đã áp dụng câu hỏi nghiên cứu mới từ Scope Optimizer Agent!</span>
            </div>
            <button onClick={() => setAppliedTopicToast(null)} className="text-slate-400 hover:text-slate-600">✕</button>
          </div>
        )}

        <div className="space-y-5">
          <div>
            <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">{t('setup.project_name')}</label>
            <input 
              type="text" 
              value={projectData.name}
              onChange={e => setProjectData({...projectData, name: e.target.value})}
              placeholder={t('setup.project_name_placeholder')}
              className={`w-full p-3 rounded-xl border focus:ring-2 focus:ring-blue-500 ${darkMode ? 'bg-slate-800 border-slate-700 dark:text-white' : 'bg-slate-50 border-slate-300 text-slate-900'}`}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-bold text-slate-700 dark:text-slate-300">{t('setup.research_question')}</label>
                <button
                  type="button"
                  onClick={handleOptimizeScope}
                  disabled={loadingScope}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-600 dark:text-amber-400 text-xs font-bold transition-all border border-amber-500/30 shadow-sm hover:scale-105"
                  title="Đo lường độ rộng/hẹp và đề xuất câu hỏi tinh chỉnh"
                >
                  {loadingScope ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Compass className="w-3.5 h-3.5" />}
                  <span>🎯 Cố vấn phạm vi đề tài</span>
                </button>
              </div>
              <textarea 
                rows="3"
                value={projectData.research_question}
                onChange={e => setProjectData({...projectData, research_question: e.target.value})}
                placeholder={t('setup.research_question_placeholder')}
                className={`w-full p-3 rounded-xl border focus:ring-2 focus:ring-blue-500 ${darkMode ? 'bg-slate-800 border-slate-700 dark:text-white' : 'bg-slate-50 border-slate-300 text-slate-900'}`}
              />
            </div>
            <div>
              <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">{t('setup.research_field')}</label>
              <input 
                type="text" 
                value={projectData.research_field}
                onChange={e => setProjectData({...projectData, research_field: e.target.value})}
                placeholder={t('setup.research_field_placeholder')}
                className={`w-full p-3 rounded-xl border focus:ring-2 focus:ring-blue-500 ${darkMode ? 'bg-slate-800 border-slate-700 dark:text-white' : 'bg-slate-50 border-slate-300 text-slate-900'}`}
              />
              <div className="flex gap-4 mt-4">
                <div className="flex-1">
                  <label className="block text-xs font-bold text-slate-500 mb-1">{t('setup.year_from')}</label>
                  <input type="number" value={projectData.year_from} onChange={e => setProjectData({...projectData, year_from: parseInt(e.target.value)})} className={`w-full p-2 rounded-lg border ${darkMode ? 'bg-slate-800 border-slate-700 dark:text-white' : 'bg-slate-50 text-slate-900'}`} />
                </div>
                <div className="flex-1">
                  <label className="block text-xs font-bold text-slate-500 mb-1">{t('setup.year_to')}</label>
                  <input type="number" value={projectData.year_to} onChange={e => setProjectData({...projectData, year_to: parseInt(e.target.value)})} className={`w-full p-2 rounded-lg border ${darkMode ? 'bg-slate-800 border-slate-700 dark:text-white' : 'bg-slate-50 text-slate-900'}`} />
                </div>
              </div>
            </div>
          </div>

          {/* SCOPE OPTIMIZER CARD (Agent Cố Vấn Phạm Vi) */}
          {scopeResult && (
            <div className={`mt-4 p-5 rounded-2xl border transition-all ${
              scopeResult.status === 'optimal'
                ? 'bg-emerald-500/10 border-emerald-500/30 dark:bg-emerald-950/30'
                : scopeResult.status === 'too_narrow'
                ? 'bg-purple-500/10 border-purple-500/30 dark:bg-purple-950/30'
                : 'bg-amber-500/10 border-amber-500/30 dark:bg-amber-950/30'
            } shadow-sm animate-in fade-in slide-in-from-top-4 duration-300`}>
              
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
                <div className="flex items-center gap-2.5">
                  <Compass className={`w-5 h-5 ${
                    scopeResult.status === 'optimal' ? 'text-emerald-600 dark:text-emerald-400' :
                    scopeResult.status === 'too_narrow' ? 'text-purple-600 dark:text-purple-400' : 'text-amber-600 dark:text-amber-400'
                  }`} />
                  <span className="font-extrabold text-sm text-slate-800 dark:text-slate-100">
                    Đánh giá phạm vi đề tài (Scope Optimizer)
                  </span>
                </div>
                
                {/* Status Badge */}
                <div className="flex items-center gap-2">
                  <span className={`px-3 py-1 rounded-full text-xs font-black uppercase tracking-wider ${
                    scopeResult.status === 'optimal'
                      ? 'bg-emerald-500 text-white'
                      : scopeResult.status === 'too_narrow'
                      ? 'bg-purple-600 text-white'
                      : 'bg-amber-500 text-white'
                  }`}>
                    {scopeResult.status === 'optimal' ? '✨ Vừa vặn / Tối ưu' :
                     scopeResult.status === 'too_narrow' ? '🔍 Đề tài Quá hẹp' : '⚠️ Đề tài Quá rộng'}
                  </span>
                  <span className="text-xs font-bold text-slate-500 dark:text-slate-400">
                    Điểm tối ưu: {scopeResult.score}/100
                  </span>
                </div>
              </div>

              <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed mb-4">
                {scopeResult.feedback}
              </p>

              {/* Refined Topics Suggestions */}
              {scopeResult.suggested_topics && scopeResult.suggested_topics.length > 0 && (
                <div className="space-y-2 pt-2 border-t border-slate-200/50 dark:border-slate-800/50">
                  <span className="block text-xs font-extrabold uppercase tracking-wider text-slate-600 dark:text-slate-300 mb-1.5">
                    💡 Đề xuất câu hỏi nghiên cứu tinh chỉnh (Nhấn để áp dụng ngay):
                  </span>
                  <div className="grid grid-cols-1 gap-2">
                    {scopeResult.suggested_topics.map((topic, i) => (
                      <div 
                        key={i} 
                        className="p-3 rounded-xl bg-white dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700 flex items-center justify-between gap-3 hover:border-indigo-400 dark:hover:border-indigo-500 transition-colors shadow-sm group"
                      >
                        <span className="text-xs font-medium text-slate-800 dark:text-slate-200 leading-snug">
                          {topic}
                        </span>
                        <button
                          type="button"
                          onClick={() => handleApplyTopic(topic)}
                          className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold shrink-0 transition-transform group-hover:scale-105 flex items-center gap-1 shadow-sm"
                        >
                          <span>Áp dụng</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Criteria Section (Agent Tự Động Sinh Tiêu Chí) */}
      <div className={`p-6 md:p-8 rounded-3xl border shadow-sm ${darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'}`}>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-3">
            <Target className="w-7 h-7 text-emerald-500" />
            <div>
              <h3 className="text-xl font-extrabold">{t('setup.criteria_title')}</h3>
              <p className="text-xs text-slate-500 font-medium">Tiêu chí chọn vào (Inclusion) và loại trừ (Exclusion) chuẩn PRISMA</p>
            </div>
          </div>

          {/* AI Criteria Generator Button */}
          <button
            type="button"
            onClick={handleGenerateCriteria}
            disabled={loadingCriteria}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-extrabold text-xs shadow-md transition-all hover:scale-105"
            title="AI đọc câu hỏi nghiên cứu và tự động sinh 3 tiêu chí chọn + 3 tiêu chí loại"
          >
            {loadingCriteria ? (
              <Loader2 className="w-4 h-4 animate-spin text-emerald-200" />
            ) : (
              <Sparkles className="w-4 h-4 text-amber-300" />
            )}
            <span>⚡ AI Tự động sinh tiêu chí</span>
          </button>
        </div>

        {criteriaToast && (
          <div className="mb-6 p-3.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 font-bold text-xs flex items-center justify-between shadow-sm animate-in fade-in slide-in-from-top-2">
            <div className="flex items-center gap-2">
              <Check className="w-4 h-4 text-emerald-600" />
              <span>Đã tự động tạo và điền bộ tiêu chí Inclusion & Exclusion chuẩn học thuật!</span>
            </div>
            <button onClick={() => setCriteriaToast(false)} className="text-slate-400 hover:text-slate-600">✕</button>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Inclusion */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="font-bold text-emerald-600 dark:text-emerald-400 text-sm flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4" />
                <span>{t('setup.inclusion')}</span>
              </h4>
              <span className="text-xs text-slate-400 font-medium">({projectData.criteria_include.length} tiêu chí)</span>
            </div>
            <div className="flex gap-2">
              <input 
                type="text" 
                value={newInclude}
                onChange={e => setNewInclude(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && addInclude()}
                placeholder={t('setup.inclusion_placeholder')}
                autoComplete="off"
                className={`flex-1 p-2.5 rounded-xl border text-sm ${darkMode ? 'bg-slate-800 border-slate-700 dark:text-white' : 'bg-slate-50 text-slate-900 border-slate-300'}`}
              />
              <button onClick={addInclude} className="p-2.5 bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 rounded-xl hover:bg-emerald-200 transition-colors">
                <Plus className="w-5 h-5"/>
              </button>
            </div>
            <ul className="space-y-2 mt-3">
              {projectData.criteria_include.map((item, idx) => (
                <li key={idx} className="flex justify-between items-center bg-emerald-50 dark:bg-emerald-900/30 p-2.5 rounded-xl text-xs font-medium border border-emerald-100 dark:border-emerald-800 animate-in fade-in slide-in-from-left-4 duration-300 text-slate-800 dark:text-slate-200">
                  <span className="pr-2">{item}</span>
                  <button onClick={() => setProjectData(p => ({...p, criteria_include: p.criteria_include.filter((_, i) => i !== idx)}))} className="text-slate-400 hover:text-red-500 transition-colors">
                    <X className="w-4 h-4"/>
                  </button>
                </li>
              ))}
            </ul>
          </div>

          {/* Exclusion */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="font-bold text-red-600 dark:text-red-400 text-sm flex items-center gap-1.5">
                <AlertCircle className="w-4 h-4" />
                <span>{t('setup.exclusion')}</span>
              </h4>
              <span className="text-xs text-slate-400 font-medium">({projectData.criteria_exclude.length} tiêu chí)</span>
            </div>
            <div className="flex gap-2">
              <input 
                type="text" 
                value={newExclude}
                onChange={e => setNewExclude(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && addExclude()}
                placeholder={t('setup.exclusion_placeholder')}
                autoComplete="off"
                className={`flex-1 p-2.5 rounded-xl border text-sm ${darkMode ? 'bg-slate-800 border-slate-700 dark:text-white' : 'bg-slate-50 text-slate-900 border-slate-300'}`}
              />
              <button onClick={addExclude} className="p-2.5 bg-red-100 dark:bg-red-950 text-red-700 dark:text-red-300 rounded-xl hover:bg-red-200 transition-colors">
                <Plus className="w-5 h-5"/>
              </button>
            </div>
            <ul className="space-y-2 mt-3">
              {projectData.criteria_exclude.map((item, idx) => (
                <li key={idx} className="flex justify-between items-center bg-red-50 dark:bg-red-900/30 p-2.5 rounded-xl text-xs font-medium border border-red-100 dark:border-red-800 animate-in fade-in slide-in-from-right-4 duration-300 text-slate-800 dark:text-slate-200">
                  <span className="pr-2">{item}</span>
                  <button onClick={() => setProjectData(p => ({...p, criteria_exclude: p.criteria_exclude.filter((_, i) => i !== idx)}))} className="text-slate-400 hover:text-red-500 transition-colors">
                    <X className="w-4 h-4"/>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* Save Success Alert Banner */}
      {saved && (
        <div className="p-4 rounded-2xl bg-emerald-50 dark:bg-emerald-950/80 border border-emerald-300 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200 text-sm font-bold flex items-center justify-between shadow-md animate-in fade-in slide-in-from-top-2 duration-300">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0" />
            <span>{t('setup.save_success_msg')}</span>
          </div>
          <button onClick={() => setSaved(false)} className="text-emerald-700 dark:text-emerald-300 hover:text-emerald-900 font-bold text-xs">
            ✕
          </button>
        </div>
      )}

      {/* Action Buttons: Agent 1 (Keywords) & Save */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <button 
          onClick={handleSuggestKeywords}
          disabled={loadingKeywords}
          className="w-full sm:w-auto px-6 py-3.5 rounded-2xl font-extrabold bg-indigo-600 text-white hover:bg-indigo-700 transition-all flex items-center justify-center gap-2 shadow-lg hover:scale-105"
        >
          {loadingKeywords ? <Loader2 className="w-5 h-5 animate-spin" /> : <Wand2 className="w-5 h-5 text-amber-300" />}
          <span>Tìm kiếm từ khóa gợi ý</span>
        </button>

        <button 
          onClick={handleSave}
          disabled={loading}
          className={`w-full sm:w-auto px-8 py-3.5 rounded-2xl font-extrabold flex items-center justify-center gap-2 shadow-lg transition-all ${
            saved
              ? 'bg-emerald-600 text-white hover:bg-emerald-700 ring-2 ring-emerald-400'
              : 'bg-blue-600 text-white hover:bg-blue-700 hover:scale-105'
          }`}
        >
          {loading ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : saved ? (
            <CheckCircle2 className="w-5 h-5 text-white" />
          ) : (
            <Save className="w-5 h-5" />
          )}
          <span>{saved ? t('setup.saved') : t('setup.save')}</span>
        </button>
      </div>

      {/* Suggested Keywords & Frame Display */}
      {picoData && (
        <div className={`p-6 md:p-8 rounded-3xl border border-indigo-200 bg-gradient-to-br from-indigo-50 to-white dark:from-indigo-950/30 dark:to-slate-900 dark:border-indigo-800 shadow-sm space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500`}>
          
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-600 text-white flex items-center justify-center font-black shadow-md">
              <CheckCircle2 className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-lg font-extrabold text-indigo-900 dark:text-indigo-300 leading-tight">
                Kết quả tra cứu
              </h4>
              <p className="text-xs text-indigo-600 dark:text-indigo-400 font-bold">Khung phân tích nghiên cứu & Đề xuất từ khoá tìm kiếm</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-white dark:bg-slate-800 p-4 rounded-2xl border shadow-sm">
              <strong className="block text-indigo-700 dark:text-indigo-400 mb-1 text-sm font-bold">Vấn đề / Đối tượng nghiên cứu:</strong>
              <p className="text-sm font-medium leading-relaxed">{picoData.population}</p>
            </div>
            <div className="bg-white dark:bg-slate-800 p-4 rounded-2xl border shadow-sm">
              <strong className="block text-emerald-700 dark:text-emerald-400 mb-1 text-sm font-bold">Giải pháp / Kỹ thuật chính:</strong>
              <p className="text-sm font-medium leading-relaxed">{picoData.intervention}</p>
            </div>
            <div className="bg-white dark:bg-slate-800 p-4 rounded-2xl border shadow-sm">
              <strong className="block text-amber-700 dark:text-amber-400 mb-1 text-sm font-bold">Phương pháp đối chứng:</strong>
              <p className="text-sm font-medium leading-relaxed">{picoData.comparison || "Không áp dụng"}</p>
            </div>
            <div className="bg-white dark:bg-slate-800 p-4 rounded-2xl border shadow-sm">
              <strong className="block text-sky-700 dark:text-sky-400 mb-1 text-sm font-bold">Kết quả đánh giá mong đợi:</strong>
              <p className="text-sm font-medium leading-relaxed">{picoData.outcome}</p>
            </div>
          </div>

          {/* Unified Keywords Block */}
          <div className="p-5 bg-slate-900 text-slate-100 rounded-2xl border border-slate-800 shadow-inner space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-extrabold text-amber-400 uppercase tracking-wider">
                Các từ khóa gợi ý:
              </span>
              {picoData.search_keywords && picoData.search_keywords.length > 0 && (
                <button
                  type="button"
                  onClick={() => navigator.clipboard.writeText(picoData.search_keywords.join(' '))}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-amber-300 rounded-lg text-xs font-bold shrink-0 transition-colors border border-slate-700 shadow-sm"
                >
                  Sao chép từ khóa
                </button>
              )}
            </div>

            <div className="flex flex-wrap gap-2 pt-1">
              {(picoData.search_keywords || []).map((kw, i) => (
                <span key={i} className="px-3.5 py-1.5 bg-indigo-600/80 text-white rounded-xl text-xs font-bold border border-indigo-500/50 shadow-sm">
                  {kw}
                </span>
              ))}
            </div>
          </div>

          <div className="flex justify-end pt-4">
             <button 
                onClick={() => setActiveTab('search')}
                className="px-6 py-2.5 bg-blue-600 text-white rounded-xl font-bold hover:bg-blue-700 shadow-md transition-transform hover:scale-105"
             >
                Đem Keyword đi Tìm kiếm →
             </button>
          </div>
        </div>
      )}
    </div>
  );
}
