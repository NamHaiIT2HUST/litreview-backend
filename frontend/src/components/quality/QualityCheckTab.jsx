import React, { useState, useEffect } from 'react';
import { CheckCircle2, XCircle, HelpCircle, Loader2, PlayCircle, ShieldAlert, BadgeCheck } from 'lucide-react';

const API_BASE = 'http://localhost:8000/api/v1';
const DEFAULT_PROJECT_ID = '00000000-0000-0000-0000-000000000001';

export default function QualityCheckTab({ darkMode }) {
  const [papers, setPapers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [checkingIds, setCheckingIds] = useState({});
  const [errorMsg, setErrorMsg] = useState(null);

  useEffect(() => {
    fetchKeptPapers();
  }, []);

  const fetchKeptPapers = async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await fetch(`${API_BASE}/projects/${DEFAULT_PROJECT_ID}/papers?decision=keep`);
      if (res.ok) {
        const data = await res.json();
        setPapers(data);
      } else {
        setErrorMsg('Lỗi khi tải danh sách bài báo.');
      }
    } catch (err) {
      console.error(err);
      setErrorMsg('Mất kết nối với Server.');
    } finally {
      setLoading(false);
    }
  };

  const handleQualityCheck = async (paperId) => {
    setCheckingIds(prev => ({ ...prev, [paperId]: true }));
    try {
      const res = await fetch(`${API_BASE}/papers/${paperId}/quality-check`, { method: 'POST' });
      if (res.ok) {
        const updated = await res.json();
        setPapers(prev => prev.map(p => p.id === paperId ? updated : p));
      } else {
        console.error('Quality check failed');
      }
    } catch (err) {
      console.error('Network error during quality check', err);
    } finally {
      setCheckingIds(prev => ({ ...prev, [paperId]: false }));
    }
  };

  const handleBulkQualityCheck = async () => {
    // Only check papers that haven't been checked (undetermined or not_applicable without check)
    const toCheck = papers.filter(p => p.scopus_status === 'undetermined');
    for (const p of toCheck) {
      await handleQualityCheck(p.id);
    }
  };

  const renderScopusBadge = (status) => {
    if (status === 'indexed') return <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800"><CheckCircle2 className="w-3.5 h-3.5"/> Indexed</span>;
    if (status === 'not_indexed') return <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400 border border-red-200 dark:border-red-800"><XCircle className="w-3.5 h-3.5"/> Not Indexed</span>;
    return <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400 border border-slate-200 dark:border-slate-700"><HelpCircle className="w-3.5 h-3.5"/> Undetermined</span>;
  };

  const renderCoverageBadge = (status) => {
    if (status === 'ok') return <span className="text-emerald-600 dark:text-emerald-400 font-medium">Trong vùng phủ sóng</span>;
    if (status === 'out_of_coverage') return <span className="text-red-600 dark:text-red-400 font-medium">Ngoài vùng phủ sóng</span>;
    return <span className="text-slate-500 font-medium">Không xác định</span>;
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-20 text-slate-500">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500 mb-4" />
        <p>Đang tải danh sách bài báo...</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-8 gap-4">
        <div className="space-y-3">
          <h2 className={`text-3xl font-extrabold ${darkMode ? 'text-white' : 'text-slate-900'}`}>
            Module 4: Quality Verification
          </h2>
          <p className={`text-base max-w-2xl ${darkMode ? 'text-slate-400' : 'text-slate-600'}`}>
            Kiểm tra nguồn gốc bài báo với cơ sở dữ liệu Scopus. Tính năng này chỉ áp dụng cho những bài báo bạn đã chọn <span className="font-semibold text-emerald-600">Keep</span>.
          </p>
        </div>
        
        {papers.some(p => p.scopus_status === 'undetermined') && (
          <button 
            onClick={handleBulkQualityCheck}
            className="shrink-0 px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl flex items-center gap-2 text-sm shadow-md transition-all hover:scale-105 active:scale-95"
          >
            <BadgeCheck className="w-4 h-4"/> Kiểm tra hàng loạt
          </button>
        )}
      </div>

      {errorMsg && (
        <div className="p-4 rounded-xl bg-red-50 text-red-700 border border-red-200 font-medium flex items-center gap-2">
          <ShieldAlert className="w-5 h-5" /> {errorMsg}
        </div>
      )}

      {papers.length === 0 ? (
        <div className="p-12 text-center rounded-3xl border bg-white dark:bg-slate-900 text-slate-500 shadow-sm">
          <ShieldAlert className="w-16 h-16 mx-auto mb-4 opacity-30 text-blue-500" />
          <h3 className="text-xl font-bold mb-2">Chưa có bài báo nào</h3>
          <p>Bạn chưa chọn "Keep" bài báo nào ở bước Screening. Hãy quay lại và chọn bài báo nhé.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {papers.map(paper => (
            <div key={paper.id} className={`p-5 rounded-2xl border shadow-sm transition-colors ${darkMode ? 'bg-slate-900 border-slate-800 hover:border-slate-700' : 'bg-white border-slate-200 hover:border-blue-100'}`}>
              <div className="flex flex-col md:flex-row justify-between gap-6">
                
                {/* Left side: Paper Info */}
                <div className="flex-1 space-y-3">
                  <h3 className="text-lg font-bold text-slate-800 dark:text-slate-200 leading-tight">
                    {paper.title}
                  </h3>
                  
                  <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-slate-600 dark:text-slate-400">
                    <div><span className="font-semibold text-slate-700 dark:text-slate-300">Tạp chí:</span> {paper.journal || 'N/A'}</div>
                    <div><span className="font-semibold text-slate-700 dark:text-slate-300">Năm:</span> {paper.year}</div>
                    <div><span className="font-semibold text-slate-700 dark:text-slate-300">ISSN:</span> {paper.issn || 'N/A'}</div>
                    <div><span className="font-semibold text-slate-700 dark:text-slate-300">Citations:</span> {paper.citations}</div>
                  </div>
                </div>

                {/* Right side: Quality Status */}
                <div className={`shrink-0 flex flex-col md:w-64 gap-3 p-4 rounded-xl border ${darkMode ? 'bg-slate-800/50 border-slate-700/50' : 'bg-slate-50 border-slate-100'}`}>
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-semibold text-slate-500 uppercase tracking-wider">Scopus</span>
                    {renderScopusBadge(paper.scopus_status)}
                  </div>
                  
                  {paper.scopus_status === 'indexed' && (
                    <>
                      <div className="flex justify-between items-center border-t border-slate-200 dark:border-slate-700 pt-2">
                        <span className="text-sm text-slate-600 dark:text-slate-400">Quartile</span>
                        <span className="font-bold text-slate-800 dark:text-slate-200">{paper.scopus_quartile || 'N/A'}</span>
                      </div>
                      <div className="flex justify-between items-center border-t border-slate-200 dark:border-slate-700 pt-2">
                        <span className="text-sm text-slate-600 dark:text-slate-400">Coverage Year</span>
                        <span className="text-sm text-right">{renderCoverageBadge(paper.coverage_year_status)}</span>
                      </div>
                    </>
                  )}

                  {paper.scopus_status === 'undetermined' && (
                    <button 
                      onClick={() => handleQualityCheck(paper.id)}
                      disabled={checkingIds[paper.id]}
                      className="mt-2 w-full py-2 bg-blue-100 hover:bg-blue-200 text-blue-700 dark:bg-blue-900/30 dark:hover:bg-blue-900/50 dark:text-blue-400 font-bold text-xs rounded-lg flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
                    >
                      {checkingIds[paper.id] ? (
                        <><Loader2 className="w-4 h-4 animate-spin"/> Đang kiểm tra...</>
                      ) : (
                        <><PlayCircle className="w-4 h-4"/> Kiểm tra chất lượng</>
                      )}
                    </button>
                  )}
                </div>

              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
