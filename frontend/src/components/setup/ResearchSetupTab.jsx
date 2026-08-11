import React, { useState } from 'react';
import { BookOpen, Target, Settings, Save, Loader2, Wand2, Plus, X } from 'lucide-react';

const API_BASE = 'http://localhost:8000/api/v1';
const DEFAULT_PROJECT_ID = '00000000-0000-0000-0000-000000000001';

export default function ResearchSetupTab({ setActiveTab, darkMode }) {
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);
  
  const [projectData, setProjectData] = useState({
    name: '',
    research_question: '',
    research_field: '',
    year_from: 2018,
    year_to: 2024,
    criteria_include: [],
    criteria_exclude: []
  });

  const [newInclude, setNewInclude] = useState('');
  const [newExclude, setNewExclude] = useState('');
  const [suggestedKeywords, setSuggestedKeywords] = useState([]);
  const [loadingKeywords, setLoadingKeywords] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  React.useEffect(() => {
    const fetchProject = async () => {
      try {
        const res = await fetch(`${API_BASE}/projects/${DEFAULT_PROJECT_ID}`);
        if (res.ok) {
          const data = await res.json();
          setProjectData(data);
        } else {
          // If not found or error, leave as empty
          console.warn("Could not fetch default project");
        }
      } catch (err) {
        console.error("DB connection error:", err);
        setErrorMsg("Không thể kết nối đến Database. Vui lòng kiểm tra Docker!");
      }
    };
    fetchProject();
  }, []);

  const handleSave = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/projects/${DEFAULT_PROJECT_ID}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(projectData)
      });
      if (res.ok) setSaved(true);
    } catch (err) {
      console.error("Save error:", err);
    } finally {
      setLoading(false);
      setTimeout(() => setSaved(false), 3000);
    }
  };

  const handleSuggestKeywords = async () => {
    setLoadingKeywords(true);
    setErrorMsg(null);
    try {
      const res = await fetch(`${API_BASE}/projects/${DEFAULT_PROJECT_ID}/suggest-keywords`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(projectData)
      });
      if (res.ok) {
        const data = await res.json();
        setSuggestedKeywords(data.suggested_keywords || []);
      } else {
        setErrorMsg("Lỗi khi lấy gợi ý từ AI. Hãy chắc chắn Server đang chạy và DB hoạt động.");
      }
    } catch (err) {
      console.error(err);
      setErrorMsg("Mất kết nối đến Server. Vui lòng kiểm tra Docker / DB!");
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
          <h2 className="text-2xl font-extrabold">Cấu hình Đề tài Nghiên cứu</h2>
        </div>
        
        {errorMsg && (
          <div className="mb-6 p-4 rounded-xl bg-red-50 text-red-700 border border-red-200 font-medium">
            {errorMsg}
          </div>
        )}

        <div className="space-y-5">
          <div>
            <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">Tên dự án / Đề tài</label>
            <input 
              type="text" 
              value={projectData.name}
              onChange={e => setProjectData({...projectData, name: e.target.value})}
              className={`w-full p-3 rounded-xl border focus:ring-2 focus:ring-blue-500 ${darkMode ? 'bg-slate-800 border-slate-700' : 'bg-slate-50 border-slate-300'}`}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
              <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">Câu hỏi nghiên cứu (Research Question)</label>
              <textarea 
                rows="3"
                value={projectData.research_question}
                onChange={e => setProjectData({...projectData, research_question: e.target.value})}
                className={`w-full p-3 rounded-xl border focus:ring-2 focus:ring-blue-500 ${darkMode ? 'bg-slate-800 border-slate-700' : 'bg-slate-50 border-slate-300'}`}
              />
            </div>
            <div>
              <label className="block text-sm font-bold text-slate-700 dark:text-slate-300 mb-2">Lĩnh vực (Field)</label>
              <input 
                type="text" 
                value={projectData.research_field}
                onChange={e => setProjectData({...projectData, research_field: e.target.value})}
                className={`w-full p-3 rounded-xl border focus:ring-2 focus:ring-blue-500 ${darkMode ? 'bg-slate-800 border-slate-700' : 'bg-slate-50 border-slate-300'}`}
              />
              <div className="flex gap-4 mt-4">
                <div className="flex-1">
                  <label className="block text-xs font-bold text-slate-500 mb-1">Từ năm</label>
                  <input type="number" value={projectData.year_from} onChange={e => setProjectData({...projectData, year_from: parseInt(e.target.value)})} className={`w-full p-2 rounded-lg border ${darkMode ? 'bg-slate-800 border-slate-700' : 'bg-slate-50'}`} />
                </div>
                <div className="flex-1">
                  <label className="block text-xs font-bold text-slate-500 mb-1">Đến năm</label>
                  <input type="number" value={projectData.year_to} onChange={e => setProjectData({...projectData, year_to: parseInt(e.target.value)})} className={`w-full p-2 rounded-lg border ${darkMode ? 'bg-slate-800 border-slate-700' : 'bg-slate-50'}`} />
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
          <h3 className="text-xl font-extrabold">Tiêu chí Sàng lọc (Criteria)</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Inclusion */}
          <div className="space-y-3">
            <h4 className="font-bold text-emerald-600 dark:text-emerald-400">Inclusion Criteria (Nên có)</h4>
            <div className="flex gap-2">
              <input 
                type="text" 
                value={newInclude}
                onChange={e => setNewInclude(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && addInclude()}
                placeholder="VD: Viết bằng tiếng Anh..."
                className={`flex-1 p-2 rounded-lg border ${darkMode ? 'bg-slate-800 border-slate-700' : 'bg-slate-50'}`}
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
            <h4 className="font-bold text-red-600 dark:text-red-400">Exclusion Criteria (Loại trừ)</h4>
            <div className="flex gap-2">
              <input 
                type="text" 
                value={newExclude}
                onChange={e => setNewExclude(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && addExclude()}
                placeholder="VD: Review papers..."
                className={`flex-1 p-2 rounded-lg border ${darkMode ? 'bg-slate-800 border-slate-700' : 'bg-slate-50'}`}
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

      {/* Suggestion AI & Actions */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <button 
          onClick={handleSuggestKeywords}
          disabled={loadingKeywords}
          className="w-full sm:w-auto px-6 py-3 rounded-2xl font-bold bg-indigo-100 text-indigo-700 hover:bg-indigo-200 flex items-center justify-center gap-2 transition-colors"
        >
          {loadingKeywords ? <Loader2 className="w-5 h-5 animate-spin" /> : <Wand2 className="w-5 h-5" />}
          AI Gợi ý Keywords
        </button>

        <button 
          onClick={handleSave}
          disabled={loading}
          className="w-full sm:w-auto px-8 py-3 rounded-2xl font-bold bg-blue-600 text-white hover:bg-blue-700 flex items-center justify-center gap-2 shadow-lg transition-all"
        >
          {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Save className="w-5 h-5" />}
          {saved ? "Đã Lưu Thành Công!" : "Lưu & Sang Bước Tìm Kiếm"}
        </button>
      </div>

      {/* Suggested Keywords Display */}
      {suggestedKeywords.length > 0 && (
        <div className={`p-6 rounded-3xl border border-indigo-200 bg-indigo-50 dark:bg-indigo-900/20 dark:border-indigo-800`}>
          <h4 className="font-bold text-indigo-800 dark:text-indigo-300 mb-3 flex items-center gap-2">
            <Wand2 className="w-4 h-4" /> Keywords AI Đề Xuất
          </h4>
          <div className="flex flex-wrap gap-2">
            {suggestedKeywords.map((kw, i) => (
              <span key={i} className="px-3 py-1.5 bg-white dark:bg-slate-800 text-indigo-700 dark:text-indigo-400 rounded-xl text-sm font-semibold border shadow-sm animate-in zoom-in duration-300 hover:scale-105 transition-transform cursor-default" style={{ animationDelay: `${i * 50}ms`, animationFillMode: 'both' }}>
                {kw}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
