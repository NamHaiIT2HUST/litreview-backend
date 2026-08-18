import React, { useState } from 'react';
import { BookOpen, Target, Settings, Save, Loader2, Wand2, Plus, X, CheckCircle2 } from 'lucide-react';
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
      setSaved(true); // Persisted locally anyway
    } finally {
      setLoading(false);
      setTimeout(() => setSaved(false), 4000);
    }
  };

  const handleSuggestKeywords = async () => {
    setLoadingKeywords(true);
    setErrorMsg(null);
    try {
      // Call new Agent 1 setup phase
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
          
          // Lấy search_keywords (phải là mảng từ khóa tiếng Anh chuẩn từ AI)
          const rawKws = data.pico.search_keywords || [];
          // Lọc: chỉ giữ các từ khóa tiếng Anh hợp lệ (>= 2 ký tự, không phải từ tiếng Việt đơn lẻ)
          const kwList = rawKws.filter(kw => 
            kw && kw.trim().length >= 3 && /^[a-zA-Z0-9\s\-\/&]+$/.test(kw.trim())
          );
          
          if (kwList.length > 0) {
            setSuggestedKeywords(kwList);
            localStorage.setItem('suggested_keywords', JSON.stringify(kwList));
          }
          
          // Boolean query for search tab
          const boolQuery = kwList.length > 0 ? kwList.join(' ') : (data.pico.boolean_query || '');
          if (boolQuery) {
             localStorage.setItem('litreview_active_mesh_query', boolQuery);
             window.dispatchEvent(new Event('new_mesh_query_ready'));
          }
        }
        
        // Gap Map Heatmap
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
      <div className={`p-6 md:p-8 rounded-3xl border shadow-sm ${darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'}`}>
        <div className="flex items-center gap-3 mb-6">
          <BookOpen className="w-8 h-8 text-blue-600 dark:text-sky-400" />
          <h2 className="text-2xl font-extrabold">{t('setup.title')}</h2>
        </div>
        
        {errorMsg && (
          <div className="mb-6 p-4 rounded-xl bg-red-50 text-red-700 border border-red-200 font-medium">
            {errorMsg}
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
              <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">{t('setup.research_question')}</label>
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
        </div>
      </div>

      {/* Criteria Section */}
      <div className={`p-6 md:p-8 rounded-3xl border shadow-sm ${darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'}`}>
        <div className="flex items-center gap-3 mb-6">
          <Target className="w-7 h-7 text-emerald-500" />
          <h3 className="text-xl font-extrabold">{t('setup.criteria_title')}</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Inclusion */}
          <div className="space-y-3">
            <h4 className="font-bold text-emerald-600 dark:text-emerald-400">{t('setup.inclusion')}</h4>
            <div className="flex gap-2">
              <input 
                type="text" 
                value={newInclude}
                onChange={e => setNewInclude(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && addInclude()}
                placeholder={t('setup.inclusion_placeholder')}
                autoComplete="off"
                className={`flex-1 p-2 rounded-lg border ${darkMode ? 'bg-slate-800 border-slate-700 dark:text-white' : 'bg-slate-50 text-slate-900'}`}
              />
              <button onClick={addInclude} className="p-2 bg-emerald-100 text-emerald-700 rounded-lg hover:bg-emerald-200"><Plus className="w-5 h-5"/></button>
            </div>
            <ul className="space-y-2 mt-3">
              {projectData.criteria_include.map((item, idx) => (
                <li key={idx} className="flex justify-between items-center bg-emerald-50 dark:bg-emerald-900/30 p-2 rounded-lg text-sm border border-emerald-100 dark:border-emerald-800 animate-in fade-in slide-in-from-left-4 duration-300">
                  <span>{item}</span>
                  <button onClick={() => setProjectData(p => ({...p, criteria_include: p.criteria_include.filter((_, i) => i !== idx)}))}><X className="w-4 h-4 text-emerald-600"/></button>
                </li>
              ))}
            </ul>
          </div>

          {/* Exclusion */}
          <div className="space-y-3">
            <h4 className="font-bold text-red-600 dark:text-red-400">{t('setup.exclusion')}</h4>
            <div className="flex gap-2">
              <input 
                type="text" 
                value={newExclude}
                onChange={e => setNewExclude(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && addExclude()}
                placeholder={t('setup.exclusion_placeholder')}
                autoComplete="off"
                className={`flex-1 p-2 rounded-lg border ${darkMode ? 'bg-slate-800 border-slate-700 dark:text-white' : 'bg-slate-50 text-slate-900'}`}
              />
              <button onClick={addExclude} className="p-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200"><Plus className="w-5 h-5"/></button>
            </div>
            <ul className="space-y-2 mt-3">
              {projectData.criteria_exclude.map((item, idx) => (
                <li key={idx} className="flex justify-between items-center bg-red-50 dark:bg-red-900/30 p-2 rounded-lg text-sm border border-red-100 dark:border-red-800 animate-in fade-in slide-in-from-right-4 duration-300">
                  <span>{item}</span>
                  <button onClick={() => setProjectData(p => ({...p, criteria_exclude: p.criteria_exclude.filter((_, i) => i !== idx)}))}><X className="w-4 h-4 text-red-600"/></button>
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

      {/* Suggestion AI & Actions */}
      {/* Suggestion AI & Actions */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <button 
          onClick={handleSuggestKeywords}
          disabled={loadingKeywords}
          className="w-full sm:w-auto px-6 py-3.5 rounded-2xl font-bold bg-indigo-600 text-white hover:bg-indigo-700 transition-colors flex items-center justify-center gap-2 shadow-lg"
        >
          {loadingKeywords ? <Loader2 className="w-5 h-5 animate-spin" /> : <Wand2 className="w-5 h-5 text-amber-300" />}
          Tìm kiếm từ khóa gợi ý
        </button>

        <button 
          onClick={handleSave}
          disabled={loading}
          className={`w-full sm:w-auto px-8 py-3.5 rounded-2xl font-extrabold flex items-center justify-center gap-2 shadow-lg transition-all ${
            saved
              ? 'bg-emerald-600 text-white hover:bg-emerald-700 ring-2 ring-emerald-400'
              : 'bg-blue-600 text-white hover:bg-blue-700'
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
