import React, { useState } from 'react';
import { ShieldAlert, Loader2, Check, X, HelpCircle, Activity } from 'lucide-react';

const API_BASE = 'http://localhost:8000/api/v1';

export default function ScreeningTab({ papers, setPapers, darkMode }) {
  const [screeningLoading, setScreeningLoading] = useState({});

  const handleScreenPaper = async (paperId) => {
    setScreeningLoading(prev => ({ ...prev, [paperId]: true }));
    try {
      const res = await fetch(`${API_BASE}/papers/${paperId}/screen`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setPapers(prev => prev.map(p => p.id === paperId ? { ...p, screening_data: data } : p));
      }
    } catch (err) {
      console.error(err);
    } finally {
      setScreeningLoading(prev => ({ ...prev, [paperId]: false }));
    }
  };

  const handleDecision = async (paperId, decision) => {
    // Optimistic UI update - Xóa bài báo khỏi danh sách chờ screening sau khi đã quyết định
    setPapers(prev => prev.filter(p => p.id !== paperId));
    
    // Server update
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

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="text-center space-y-3 mb-8">
        <h2 className={`text-3xl font-extrabold ${darkMode ? 'text-white' : 'text-slate-900'}`}>
          AI Sàng Lọc Bài Báo (Screening)
        </h2>
        <p className={`text-base ${darkMode ? 'text-slate-400' : 'text-slate-600'}`}>
          Đánh giá mức độ liên quan dựa trên Tiêu chí Inclusion / Exclusion.
        </p>
      </div>

      <div className="space-y-6">
        {papers.length === 0 ? (
          <div className="p-10 text-center rounded-3xl border bg-white dark:bg-slate-900 text-slate-500">
            <ShieldAlert className="w-12 h-12 mx-auto mb-3 opacity-30 text-blue-500" />
            <p>Chưa có bài báo nào để sàng lọc. Hãy quay lại bước Search để tìm bài báo nhé.</p>
          </div>
        ) : (
          papers.map((paper) => {
            const isLoading = screeningLoading[paper.id];
            const screenData = paper.screening_data;
            
            return (
              <div key={paper.id} className={`p-6 rounded-3xl border shadow-sm ${darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'}`}>
                <div className="flex justify-between items-start gap-4">
                  <div className="flex-1">
                    <h3 className="text-lg font-bold text-slate-800 dark:text-slate-200 mb-2">{paper.title}</h3>
                    <p className="text-sm text-slate-500 line-clamp-2 mb-4">{paper.abstract}</p>
                    
                    {!screenData && !isLoading && (
                      <button 
                        onClick={() => handleScreenPaper(paper.id)}
                        className="px-4 py-2 bg-indigo-100 text-indigo-700 font-bold text-xs rounded-xl hover:bg-indigo-200 flex items-center gap-2"
                      >
                        <Activity className="w-4 h-4"/> Bắt đầu AI Screening
                      </button>
                    )}

                    {isLoading && (
                      <div className="flex items-center gap-2 text-indigo-600 text-sm font-bold animate-pulse">
                        <Loader2 className="w-4 h-4 animate-spin"/> Đang phân tích...
                      </div>
                    )}

                    {screenData && (
                      <div className={`p-4 mt-3 rounded-2xl border ${screenData.relevance_bucket === 'high' ? 'bg-emerald-50 border-emerald-200' : screenData.relevance_bucket === 'medium' ? 'bg-amber-50 border-amber-200' : 'bg-red-50 border-red-200'}`}>
                        <div className="font-extrabold text-sm uppercase mb-2">Relevance: {screenData.relevance_bucket}</div>
                        
                        <div className="text-sm text-slate-700 space-y-2">
                          {screenData.reason?.matches?.length > 0 && (
                            <div>
                              <span className="font-bold text-emerald-700">Khớp:</span>
                              <ul className="list-disc ml-5">{screenData.reason.matches.map((m, i) => <li key={i}>{m}</li>)}</ul>
                            </div>
                          )}
                          {screenData.reason?.mismatches?.length > 0 && (
                            <div>
                              <span className="font-bold text-red-700">Không khớp:</span>
                              <ul className="list-disc ml-5">{screenData.reason.mismatches.map((m, i) => <li key={i}>{m}</li>)}</ul>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>

                  {screenData && (
                    <div className="flex flex-col gap-2 shrink-0">
                      <button onClick={() => handleDecision(paper.id, 'keep')} className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl flex items-center gap-2 text-sm shadow">
                        <Check className="w-4 h-4"/> Keep
                      </button>
                      <button onClick={() => handleDecision(paper.id, 'maybe')} className="px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-white font-bold rounded-xl flex items-center gap-2 text-sm shadow">
                        <HelpCircle className="w-4 h-4"/> Maybe
                      </button>
                      <button onClick={() => handleDecision(paper.id, 'remove')} className="px-5 py-2.5 bg-red-600 hover:bg-red-700 text-white font-bold rounded-xl flex items-center gap-2 text-sm shadow">
                        <X className="w-4 h-4"/> Remove
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
