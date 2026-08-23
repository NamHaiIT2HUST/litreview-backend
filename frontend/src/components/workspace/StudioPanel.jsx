import React, { useState, useEffect } from 'react';
import { 
  Sparkles, 
  Share2, 
  FileText, 
  ListChecks, 
  PieChart, 
  Headphones, 
  Network, 
  LayoutTemplate,
  Loader2,
  CheckCircle2,
  Target
} from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';
import { API_BASE } from '../../utils/apiConfig';

export default function StudioPanel({ workspacePapers, darkMode }) {
  const { t } = useLanguage();
  const [loadingAgent, setLoadingAgent] = useState(null);
  const [results, setResults] = useState({});
  const [picoData, setPicoData] = useState(null);

  useEffect(() => {
     try {
       const cached = localStorage.getItem('slr_pico_data');
       if (cached) setPicoData(JSON.parse(cached));
     } catch (e) {}
  }, []);

  const handleRunAgent2 = async () => {
    setLoadingAgent('agent2');
    try {
      const idea = picoData?.research_question || 'N/A';
      const res = await fetch(`${API_BASE}/slr-swarm/step2-search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ idea, pico: picoData || {}, corpus: workspacePapers })
      });
      if (res.ok) {
        const data = await res.json();
        setResults(prev => ({ ...prev, agent2: `Đã tìm thêm ${data.corpus.length - workspacePapers.length} bài báo mới!` }));
      } else {
        setResults(prev => ({ ...prev, agent2: 'Lỗi khi chạy Agent 2' }));
      }
    } catch (e) {
      setResults(prev => ({ ...prev, agent2: 'Lỗi kết nối Agent 2' }));
    }
    setLoadingAgent(null);
  };

  const handleRunAgent34 = async () => {
    setLoadingAgent('agent34');
    try {
      const idea = picoData?.research_question || 'N/A';
      const res = await fetch(`${API_BASE}/slr-swarm/step3-draft`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ idea, pico: picoData || {}, corpus: workspacePapers })
      });
      if (res.ok) {
        const data = await res.json();
        setResults(prev => ({ 
          ...prev, 
          agent34: `Đã sàng lọc giữ lại ${data.included_ids.length} bài. LaTeX: ${data.latex ? 'Có' : 'Không'}` 
        }));
      } else {
        setResults(prev => ({ ...prev, agent34: 'Lỗi khi chạy Agent 3&4' }));
      }
    } catch (e) {
      setResults(prev => ({ ...prev, agent34: 'Lỗi kết nối Agent 3&4' }));
    }
    setLoadingAgent(null);
  };

  const [gapMapData, setGapMapData] = useState(null);

  const handleRunGapMap = async () => {
    setLoadingAgent('gapmap');
    try {
      const idea = picoData?.research_question || 'N/A';
      const res = await fetch(`${API_BASE}/slr-swarm/step1-setup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ idea, corpus: workspacePapers })
      });
      if (res.ok) {
        const data = await res.json();
        setGapMapData(data.gap_map);
        setResults(prev => ({ ...prev, gapmap: `Đã phân tích khoảng trống từ ${workspacePapers.length} bài báo!` }));
      } else {
        setResults(prev => ({ ...prev, gapmap: 'Lỗi khi phân tích khoảng trống' }));
      }
    } catch (e) {
      setResults(prev => ({ ...prev, gapmap: 'Lỗi kết nối phân tích khoảng trống' }));
    }
    setLoadingAgent(null);
  };

  const actions = [
    {
      id: 'gapmap',
      title: 'Bản đồ khoảng trống (Gap Map)',
      desc: 'Phát hiện hướng đi mới từ tập bài báo',
      icon: Target,
      color: 'text-rose-500 bg-rose-100 dark:bg-rose-900/30',
      onClick: handleRunGapMap
    },
    {
      id: 'agent2',
      title: 'Mở rộng tìm kiếm',
      desc: 'Quét vết dầu loang (Snowballing)',
      icon: Network,
      color: 'text-blue-500 bg-blue-100 dark:bg-blue-900/30',
      onClick: handleRunAgent2
    },
    {
      id: 'agent34',
      title: 'Sàng lọc Kép & PRISMA',
      desc: 'Agent 3 (Lọc) & Agent 4 (Trích xuất)',
      icon: ListChecks,
      color: 'text-emerald-500 bg-emerald-100 dark:bg-emerald-900/30',
      onClick: handleRunAgent34
    },
    {
      id: 'agent4_draft',
      title: 'Viết Bản thảo LaTeX',
      desc: 'Tự động sinh Literature Review',
      icon: FileText,
      color: 'text-indigo-500 bg-indigo-100 dark:bg-indigo-900/30',
      onClick: () => {}
    },
    {
      id: 'agent5',
      title: 'Phân tích Dữ liệu CSV',
      desc: 'Agent 5 (Data Copilot)',
      icon: PieChart,
      color: 'text-rose-500 bg-rose-100 dark:bg-rose-900/30',
      onClick: () => {}
    }
  ];

  const bonusActions = [
    { title: 'Tổng quan bằng âm thanh', icon: Headphones },
    { title: 'Bản đồ tư duy', icon: LayoutTemplate },
    { title: 'Thẻ ghi nhớ', icon: Share2 }
  ];

  return (
    <div className={`w-[280px] lg:w-[320px] h-full overflow-y-auto custom-scrollbar flex flex-col p-4 rounded-3xl border shadow-sm shrink-0 ${darkMode ? 'bg-slate-900 border-slate-800' : 'bg-slate-50 border-slate-200'}`}>
      <div className="flex items-center gap-2 mb-4 border-b pb-3 border-slate-200 dark:border-slate-800">
        <Sparkles className="w-5 h-5 text-amber-500" />
        <h3 className={`font-extrabold text-sm ${darkMode ? 'text-white' : 'text-slate-900'}`}>
          AI Studio (Agent 2-5)
        </h3>
      </div>

      <div className="space-y-3">
        <div className="text-[11px] font-bold text-slate-500 dark:text-slate-400 mb-2 uppercase tracking-wider">Tiến trình chuẩn (SLR)</div>
        
        {actions.map(action => (
          <div key={action.id}>
            <button 
              onClick={action.onClick}
              disabled={loadingAgent !== null}
              className={`w-full text-left flex items-center gap-3 p-3 rounded-2xl border transition-all group ${
                darkMode 
                  ? 'bg-slate-800/50 border-slate-700 hover:bg-slate-800 hover:border-slate-600' 
                  : 'bg-white border-slate-200 hover:shadow-md hover:border-slate-300'
              }`}
            >
              <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 shadow-inner ${action.color}`}>
                {loadingAgent === action.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <action.icon className="w-4 h-4" />}
              </div>
              <div>
                <div className={`text-sm font-bold ${darkMode ? 'text-slate-200' : 'text-slate-800'}`}>
                  {action.title}
                </div>
                <div className={`text-[11px] font-medium ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                  {action.desc}
                </div>
              </div>
            </button>
            
            {results[action.id] && (
              <div className="mt-1.5 ml-2 p-2 rounded-xl bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-100 dark:border-emerald-800/50 flex items-center gap-2 animate-in fade-in zoom-in duration-300">
                <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                <span className="text-xs font-bold text-emerald-700 dark:text-emerald-400 leading-tight">{results[action.id]}</span>
              </div>
            )}
          </div>
        ))}

        <div className="text-[11px] font-bold text-slate-500 dark:text-slate-400 mt-6 mb-2 uppercase tracking-wider border-t pt-4 border-slate-200 dark:border-slate-800">
          Mở rộng (NotebookLM)
        </div>

        {bonusActions.map((action, idx) => (
          <button 
            key={idx}
            className={`w-full text-left flex items-center justify-between p-3 rounded-2xl border transition-all ${
              darkMode 
                ? 'bg-slate-800 border-slate-700 hover:bg-slate-700' 
                : 'bg-white border-slate-200 hover:bg-slate-50 hover:shadow-sm'
            }`}
          >
            <div className="flex items-center gap-3">
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${darkMode ? 'bg-slate-900 text-slate-400' : 'bg-slate-100 text-slate-500'}`}>
                <action.icon className="w-4 h-4" />
              </div>
              <span className={`text-[13px] font-bold ${darkMode ? 'text-slate-300' : 'text-slate-700'}`}>
                {action.title}
              </span>
            </div>
            <div className={`text-[9px] font-extrabold px-2 py-0.5 rounded-md ${darkMode ? 'bg-slate-900 text-slate-500' : 'bg-slate-100 text-slate-400'}`}>
              PRO
            </div>
          </button>
        ))}

        {gapMapData && gapMapData.cells && gapMapData.cells.length > 0 && (
          <div className="mt-4 p-3 rounded-2xl border bg-slate-100 dark:bg-slate-800/80 border-slate-200 dark:border-slate-700 space-y-2 animate-in fade-in slide-in-from-bottom-2 duration-300">
            <div className="flex items-center gap-1.5 text-xs font-bold text-slate-800 dark:text-slate-200">
              <Target className="w-4 h-4 text-rose-500" />
              <span>Bản Đồ Khoảng Trống (Gap Map)</span>
            </div>
            <div className="space-y-1.5 max-h-48 overflow-y-auto custom-scrollbar pr-1">
              {gapMapData.cells.map((c, idx) => (
                <div 
                  key={idx} 
                  className={`p-2 rounded-xl border text-xs ${
                    c.saturation === 'saturated' 
                      ? 'bg-red-50 border-red-200 dark:bg-red-950/40 dark:border-red-800' 
                      : c.saturation === 'sparse' 
                        ? 'bg-amber-50 border-amber-200 dark:bg-amber-950/40 dark:border-amber-800' 
                        : 'bg-emerald-50 border-emerald-200 dark:bg-emerald-950/40 dark:border-emerald-800'
                  }`}
                >
                  <div className="flex justify-between items-center font-bold text-[10px] text-slate-500 dark:text-slate-400 capitalize mb-0.5">
                    <span>{c.saturation}</span>
                    <span>{c.paper_count} bài</span>
                  </div>
                  <div className="font-extrabold text-slate-900 dark:text-slate-100 text-[11px] leading-tight">
                    {c.dimension_x} & {c.dimension_y}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

      </div>
      
      <div className="mt-auto pt-6 text-center">
         <p className={`text-[11px] font-semibold flex items-center justify-center gap-1.5 ${darkMode ? 'text-slate-500' : 'text-slate-400'}`}>
           <Sparkles className="w-3.5 h-3.5" /> Đầu ra của Studio sẽ được lưu ở đây.
         </p>
      </div>
    </div>
  );
}
