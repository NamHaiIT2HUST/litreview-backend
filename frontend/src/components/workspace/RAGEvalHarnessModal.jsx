import React, { useState, useEffect } from 'react';
import { 
  X, 
  Play, 
  ShieldCheck, 
  AlertTriangle, 
  CheckCircle2, 
  XCircle, 
  FileText, 
  Layers, 
  Activity, 
  Zap, 
  Clock, 
  Sparkles,
  BarChart2,
  RefreshCw,
  Award,
  ChevronRight
} from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';
import { API_BASE, safeFetch } from '../../utils/apiConfig';

export default function RAGEvalHarnessModal({ isOpen, onClose, workspacePapers = [], darkMode = false }) {
  const { t, language } = useLanguage();
  const isEn = language === 'en';

  const [selectedPaperIds, setSelectedPaperIds] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const [currentReport, setCurrentReport] = useState(null);
  const [reportsHistory, setReportsHistory] = useState([]);
  const [activeTab, setActiveTab] = useState('run'); // 'run' | 'history'
  const [expandedCaseId, setExpandedCaseId] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  // Initialize selected papers
  useEffect(() => {
    if (workspacePapers && workspacePapers.length > 0) {
      setSelectedPaperIds(workspacePapers.map(p => p.id));
    }
  }, [workspacePapers]);

  // Fetch recent reports on open
  useEffect(() => {
    if (isOpen) {
      fetchReports();
    }
  }, [isOpen]);

  const fetchReports = async () => {
    try {
      const res = await safeFetch('/workspace/eval-reports');
      if (res.ok) {
        const data = await res.json();
        setReportsHistory(data || []);
        if (data && data.length > 0 && !currentReport) {
          setCurrentReport(data[0]);
        }
      }
    } catch (e) {
      console.error('Failed to fetch reports:', e);
    }
  };

  const handleTogglePaper = (id) => {
    setSelectedPaperIds(prev => 
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const handleSelectAll = () => {
    if (selectedPaperIds.length === workspacePapers.length) {
      setSelectedPaperIds([]);
    } else {
      setSelectedPaperIds(workspacePapers.map(p => p.id));
    }
  };

  const handleRunBenchmark = async () => {
    if (selectedPaperIds.length === 0) {
      setErrorMsg(isEn ? 'Please select at least one paper.' : 'Vui lòng chọn ít nhất một bài báo để kiểm thử.');
      return;
    }

    setErrorMsg(null);
    setIsRunning(true);

    try {
      const res = await safeFetch('/workspace/run-eval-harness', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          paper_ids: selectedPaperIds,
          max_questions_per_paper: 2,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Lỗi máy chủ (${res.status})`);
      }

      const report = await res.json();
      setCurrentReport(report);
      setReportsHistory(prev => [report, ...prev]);
      setActiveTab('run');
    } catch (e) {
      console.error('Benchmark run failed:', e);
      setErrorMsg(e.message || (isEn ? 'Benchmark failed to run.' : 'Chạy kiểm thử thất bại. Vui lòng thử lại.'));
    } finally {
      setIsRunning(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className={`w-full max-w-5xl h-[88vh] rounded-3xl border flex flex-col overflow-hidden shadow-2xl transition-all ${
        darkMode ? 'bg-slate-900 border-slate-800 text-slate-100' : 'bg-white border-slate-200 text-slate-900'
      }`}>
        
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b dark:border-slate-800 border-slate-200 shrink-0">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white shadow-md">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-extrabold text-base flex items-center gap-2">
                <span>{isEn ? 'RAG Evaluation Benchmark Harness' : 'Hệ thống Đánh giá RAG & Kiểm định Ảo giác'}</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full font-mono font-bold bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
                  LitReview Scientific Standard
                </span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                {isEn 
                  ? 'Automated evaluation suite to measure Faithfulness, Hallucination Rate, and Citation Precision.'
                  : 'Bộ kiểm thử tự động đo lường độ trung thực (Faithfulness), tỷ lệ ảo giác (Hallucination) và độ chính xác trích dẫn.'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex bg-slate-100 dark:bg-slate-800 p-1 rounded-xl text-xs font-bold">
              <button
                onClick={() => setActiveTab('run')}
                className={`px-3 py-1.5 rounded-lg transition-all ${
                  activeTab === 'run' ? 'bg-white dark:bg-slate-700 shadow-xs text-blue-600 dark:text-blue-400' : 'text-slate-500'
                }`}
              >
                {isEn ? 'Benchmark Runner' : 'Chạy kiểm thử'}
              </button>
              <button
                onClick={() => setActiveTab('history')}
                className={`px-3 py-1.5 rounded-lg transition-all ${
                  activeTab === 'history' ? 'bg-white dark:bg-slate-700 shadow-xs text-blue-600 dark:text-blue-400' : 'text-slate-500'
                }`}
              >
                {isEn ? `History (${reportsHistory.length})` : `Lịch sử (${reportsHistory.length})`}
              </button>
            </div>

            <button
              onClick={onClose}
              className="p-2 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="flex-1 flex min-h-0 overflow-hidden">
          
          {/* Left Sidebar: Paper Selector */}
          <div className={`w-72 border-r dark:border-slate-800 border-slate-200 flex flex-col shrink-0 ${
            darkMode ? 'bg-slate-900/50' : 'bg-slate-50/50'
          }`}>
            <div className="p-4 border-b dark:border-slate-800 border-slate-200 flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-xs font-bold text-slate-700 dark:text-slate-300">
                <FileText className="w-4 h-4 text-blue-500" />
                <span>{isEn ? 'Select Papers' : 'Chọn tài liệu'}</span>
                <span className="text-[11px] text-slate-400 font-mono">({selectedPaperIds.length}/{workspacePapers.length})</span>
              </div>
              <button
                onClick={handleSelectAll}
                className="text-[11px] font-bold text-blue-600 dark:text-blue-400 hover:underline"
              >
                {selectedPaperIds.length === workspacePapers.length ? (isEn ? 'Deselect All' : 'Bỏ chọn') : (isEn ? 'Select All' : 'Chọn hết')}
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-3 space-y-1.5 custom-scrollbar">
              {workspacePapers.length === 0 ? (
                <div className="text-center p-4 text-xs text-slate-400">
                  {isEn ? 'No papers in workspace.' : 'Chưa có tài liệu trong Workspace.'}
                </div>
              ) : (
                workspacePapers.map(paper => {
                  const isChecked = selectedPaperIds.includes(paper.id);
                  return (
                    <div
                      key={paper.id}
                      onClick={() => handleTogglePaper(paper.id)}
                      className={`p-2.5 rounded-xl border transition-all cursor-pointer select-none text-xs flex items-start gap-2.5 ${
                        isChecked 
                          ? 'bg-blue-50/70 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800 text-slate-800 dark:text-slate-200'
                          : 'bg-white dark:bg-slate-800/40 border-slate-200 dark:border-slate-800 text-slate-500 opacity-70 hover:opacity-100'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => {}}
                        className="mt-0.5 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold truncate">{paper.title || paper.filename}</p>
                        <p className="text-[10px] text-slate-400 mt-0.5">
                          {paper.year ? `${paper.year} · ` : ''}{paper.authors ? `${paper.authors.split(',')[0]} et al.` : 'N/A'}
                        </p>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            <div className="p-4 border-t dark:border-slate-800 border-slate-200">
              <button
                onClick={handleRunBenchmark}
                disabled={isRunning || workspacePapers.length === 0}
                className="w-full py-3 rounded-2xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 text-white font-extrabold text-xs flex items-center justify-center gap-2 shadow-lg shadow-blue-500/20 active:scale-98 transition-all cursor-pointer"
              >
                {isRunning ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>{isEn ? 'Running Benchmark...' : 'Đang chạy kiểm thử...'}</span>
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-white" />
                    <span>{isEn ? 'Run RAG Benchmark Harness' : 'Bắt đầu Chạy Kiểm Thử RAG'}</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Right Main Panel: Report & Metrics */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
            
            {errorMsg && (
              <div className="p-4 rounded-2xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            {isRunning ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-8 space-y-4">
                <div className="relative">
                  <div className="w-16 h-16 rounded-full border-4 border-blue-200 dark:border-blue-900 border-t-blue-600 animate-spin" />
                  <Sparkles className="w-6 h-6 text-blue-500 absolute inset-0 m-auto animate-pulse" />
                </div>
                <div>
                  <h4 className="font-extrabold text-base text-slate-800 dark:text-slate-200">
                    {isEn ? 'Executing RAG Benchmark Suite...' : 'Đang thực thi bộ kiểm thử RAG tự động...'}
                  </h4>
                  <p className="text-xs text-slate-400 mt-1 max-w-md">
                    {isEn 
                      ? 'Generating challenging questions, evaluating multi-hop retrieval, and running claim-level attribution verification.'
                      : 'Đang tự động trích xuất câu hỏi, chạy truy vấn RAG song song và chấm điểm từng luận điểm (Attributable / Hallucination).'}
                  </p>
                </div>
              </div>
            ) : currentReport ? (
              <>
                {/* Benchmark Summary KPI Cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div className={`p-4 rounded-2xl border transition-all ${
                    darkMode ? 'bg-slate-800/60 border-slate-700' : 'bg-slate-50 border-slate-200'
                  }`}>
                    <div className="flex items-center justify-between text-slate-400 text-xs font-semibold">
                      <span>{isEn ? 'Pass Rate' : 'Tỷ lệ đạt chuẩn'}</span>
                      <Award className="w-4 h-4 text-emerald-500" />
                    </div>
                    <div className="text-2xl font-black text-emerald-600 dark:text-emerald-400 mt-1">
                      {currentReport.pass_rate_pct}%
                    </div>
                    <div className="text-[11px] text-slate-400 mt-0.5 font-medium">
                      {currentReport.passed_test_cases}/{currentReport.total_test_cases} test cases pass
                    </div>
                  </div>

                  <div className={`p-4 rounded-2xl border transition-all ${
                    darkMode ? 'bg-slate-800/60 border-slate-700' : 'bg-slate-50 border-slate-200'
                  }`}>
                    <div className="flex items-center justify-between text-slate-400 text-xs font-semibold">
                      <span>{isEn ? 'Faithfulness' : 'Độ trung thực nguồn'}</span>
                      <ShieldCheck className="w-4 h-4 text-blue-500" />
                    </div>
                    <div className="text-2xl font-black text-blue-600 dark:text-blue-400 mt-1">
                      {currentReport.overall_faithfulness_pct}%
                    </div>
                    <div className="text-[11px] text-slate-400 mt-0.5 font-medium">
                      {isEn ? 'Attributable ratio' : 'Tỷ lệ có căn cứ'}
                    </div>
                  </div>

                  <div className={`p-4 rounded-2xl border transition-all ${
                    darkMode ? 'bg-slate-800/60 border-slate-700' : 'bg-slate-50 border-slate-200'
                  }`}>
                    <div className="flex items-center justify-between text-slate-400 text-xs font-semibold">
                      <span>{isEn ? 'Hallucination Rate' : 'Tỷ lệ ảo giác'}</span>
                      <AlertTriangle className="w-4 h-4 text-amber-500" />
                    </div>
                    <div className={`text-2xl font-black mt-1 ${
                      currentReport.overall_hallucination_rate_pct > 15 ? 'text-rose-500' : 'text-amber-500'
                    }`}>
                      {currentReport.overall_hallucination_rate_pct}%
                    </div>
                    <div className="text-[11px] text-slate-400 mt-0.5 font-medium">
                      Extrapolatory ratio
                    </div>
                  </div>

                  <div className={`p-4 rounded-2xl border transition-all ${
                    darkMode ? 'bg-slate-800/60 border-slate-700' : 'bg-slate-50 border-slate-200'
                  }`}>
                    <div className="flex items-center justify-between text-slate-400 text-xs font-semibold">
                      <span>{isEn ? 'Citation Precision' : 'Độ chuẩn xác trích dẫn'}</span>
                      <Zap className="w-4 h-4 text-indigo-500" />
                    </div>
                    <div className="text-2xl font-black text-indigo-600 dark:text-indigo-400 mt-1">
                      {currentReport.overall_citation_precision_pct}%
                    </div>
                    <div className="text-[11px] text-slate-400 mt-0.5 font-medium">
                      Avg Latency: {currentReport.average_latency_ms}ms
                    </div>
                  </div>
                </div>

                {/* Recommendations Box */}
                {currentReport.recommendations && currentReport.recommendations.length > 0 && (
                  <div className={`p-4 rounded-2xl border ${
                    darkMode ? 'bg-blue-950/20 border-blue-900/50' : 'bg-blue-50/50 border-blue-200/80'
                  }`}>
                    <h5 className="text-xs font-bold text-blue-700 dark:text-blue-300 flex items-center gap-1.5 mb-2">
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>{isEn ? 'RAG Optimization Recommendations' : 'Khuyến nghị Tối ưu hóa RAG'}</span>
                    </h5>
                    <ul className="space-y-1 text-xs text-slate-600 dark:text-slate-300">
                      {currentReport.recommendations.map((rec, rIdx) => (
                        <li key={rIdx} className="flex items-start gap-2">
                          <span className="text-blue-500 font-bold">•</span>
                          <span>{rec}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Detailed Test Cases Table */}
                <div className="space-y-3">
                  <h4 className="text-xs font-extrabold text-slate-700 dark:text-slate-200 uppercase tracking-wider">
                    {isEn ? 'Detailed Test Case Results' : 'Chi tiết Kết quả từng Test Case'}
                  </h4>

                  <div className="space-y-2">
                    {currentReport.results && currentReport.results.map((tc, idx) => {
                      const isExpanded = expandedCaseId === tc.test_case_id;
                      return (
                        <div 
                          key={tc.test_case_id || idx}
                          className={`rounded-2xl border transition-all overflow-hidden ${
                            darkMode ? 'bg-slate-800/40 border-slate-800' : 'bg-white border-slate-200 shadow-xs'
                          }`}
                        >
                          <div 
                            onClick={() => setExpandedCaseId(isExpanded ? null : tc.test_case_id)}
                            className="p-4 flex items-center justify-between gap-3 cursor-pointer select-none"
                          >
                            <div className="flex items-center gap-3 min-w-0">
                              {tc.passed ? (
                                <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
                              ) : (
                                <XCircle className="w-5 h-5 text-rose-500 shrink-0" />
                              )}
                              <div className="min-w-0">
                                <p className="text-xs font-bold text-slate-800 dark:text-slate-200 truncate">
                                  {tc.question}
                                </p>
                                <p className="text-[11px] text-slate-400 mt-0.5 truncate">
                                  📄 {tc.paper_title} · {tc.retrieval_chunk_count} chunks · {tc.latency_ms}ms
                                </p>
                              </div>
                            </div>

                            <div className="flex items-center gap-3 shrink-0">
                              <span className="text-xs font-mono font-bold text-slate-600 dark:text-slate-300">
                                Faithfulness: {Math.round(tc.faithfulness_score * 100)}%
                              </span>
                              <ChevronRight className={`w-4 h-4 text-slate-400 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                            </div>
                          </div>

                          {isExpanded && (
                            <div className="p-4 border-t dark:border-slate-800 border-slate-100 bg-slate-50/50 dark:bg-slate-900/50 space-y-3 text-xs">
                              <div>
                                <span className="font-bold text-[11px] text-slate-500 uppercase tracking-wider block mb-1">
                                  {isEn ? 'Generated RAG Answer:' : 'Câu trả lời sinh ra từ RAG:'}
                                </span>
                                <div className="p-3 rounded-xl bg-white dark:bg-slate-800 border dark:border-slate-700 text-slate-700 dark:text-slate-300 leading-relaxed">
                                  {tc.answer}
                                </div>
                              </div>

                              {tc.claims && tc.claims.length > 0 && (
                                <div>
                                  <span className="font-bold text-[11px] text-slate-500 uppercase tracking-wider block mb-1">
                                    {isEn ? 'Claim Attribution Breakdown:' : 'Phân tích kiểm định từng luận điểm:'}
                                  </span>
                                  <div className="space-y-1.5">
                                    {tc.claims.map((claim, cIdx) => (
                                      <div key={cIdx} className="p-2.5 rounded-lg border dark:border-slate-700 bg-white dark:bg-slate-800 text-[11.5px] flex flex-col gap-1">
                                        <div className="flex items-center justify-between gap-2">
                                          <span className="font-medium">{claim.sentence}</span>
                                          <span className={`px-2 py-0.2 rounded text-[9.5px] font-bold ${
                                            claim.status === 'Attributable' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300' :
                                            claim.status === 'Contradictory' ? 'bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300' :
                                            'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300'
                                          }`}>
                                            {claim.status}
                                          </span>
                                        </div>
                                        {claim.supporting_excerpt && (
                                          <p className="text-[10.5px] text-slate-400 italic">
                                            "{claim.supporting_excerpt}"
                                          </p>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-center p-8 space-y-3">
                <div className="w-12 h-12 rounded-2xl bg-blue-50 dark:bg-blue-950/60 text-blue-500 flex items-center justify-center shadow-xs">
                  <Activity className="w-6 h-6" />
                </div>
                <div>
                  <h4 className="font-bold text-sm text-slate-800 dark:text-slate-200">
                    {isEn ? 'No Benchmark Report Yet' : 'Chưa có Báo cáo Kiểm thử'}
                  </h4>
                  <p className="text-xs text-slate-400 mt-1 max-w-sm">
                    {isEn 
                      ? 'Select papers on the left and click "Run RAG Benchmark Harness" to evaluate your workspace.'
                      : 'Chọn các tài liệu ở thanh bên trái và bấm nút "Bắt đầu Chạy Kiểm Thử RAG" để đo lường chất lượng hệ thống.'}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
