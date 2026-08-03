import React, { useState } from 'react';
import * as XLSX from 'xlsx';
import { 
  Search, Filter, Download, Sparkles, BookOpen, Layers, CheckSquare, 
  Square, ExternalLink, FileText, ChevronDown, ChevronUp, Award, BarChart3, 
  MessageSquare, ShieldCheck, History, ArrowRight, RefreshCw, Info, Database
} from 'lucide-react';

// Sample Academic Dataset (Scopus + Web of Science + OpenAlex Combined)
const MOCK_PAPERS = [
  {
    id: 'WOS-2024-001',
    title: 'Large Language Models in Medicine: A Comprehensive Review of Clinical Applications and Limitations',
    authors: 'Eric J. Topol, Pranav Rajpurkar, Hannah A. Valantine',
    journal: 'Nature Medicine',
    year: 2024,
    citations: 1420,
    litScore: 98,
    doi: '10.1038/s41591-024-02891-w',
    url: 'https://doi.org/10.1038/s41591-024-02891-w',
    tldr: 'TL;DR: Summarizes GPT-4 and LLaMA performance across 15 clinical specialties, showing 89% diagnostic accuracy but warning against 11% hallucination risk.',
    abstract: 'Recent advances in large language models (LLMs) have transformed clinical decision support systems. In this review, we analyze 150 empirical studies evaluating LLM performance in medical diagnostics, patient communication, and EHR synthesis. We highlight key limitations including hallucination, bias, and privacy risks, and propose a framework for clinical validation.'
  },
  {
    id: 'SCOPUS-2024-089',
    title: 'Mitigating Hallucinations in Grounded Academic RAG Systems using Citation-Aware Fine-Tuning',
    authors: 'Nguyen Dao Nam Hai, Le Van Tuan, Sarah Jenkins',
    journal: 'IEEE Transactions on Artificial Intelligence',
    year: 2024,
    citations: 380,
    litScore: 95,
    doi: '10.1109/TAI.2024.3391029',
    url: 'https://doi.org/10.1109/TAI.2024.3391029',
    tldr: 'TL;DR: Introduces a novel LoRA fine-tuning method on LLaMA-3 that enforces strict citation tags [1] and eliminates false academic references.',
    abstract: 'Retrieval-Augmented Generation (RAG) often suffers from subtle hallucinations where generated summaries contain facts not backed by retrieved abstracts. We present SciRAG-FineTune, an open-source framework using knowledge distillation to fine-tune LLaMA-3-8B. Our model achieves 99.4% citation precision on Web of Science benchmark datasets.'
  },
  {
    id: 'ALEX-2023-402',
    title: 'Adam: A Method for Stochastic Optimization in Deep Neural Networks',
    authors: 'Diederik P. Kingma, Jimmy Ba',
    journal: 'International Conference on Learning Representations (ICLR)',
    year: 2023,
    citations: 84790,
    litScore: 99,
    doi: '10.48550/arXiv.1412.6980',
    url: 'https://arxiv.org/abs/1412.6980',
    tldr: 'TL;DR: The foundational first-order gradient optimization method widely used across deep learning and LLM training architectures.',
    abstract: 'We introduce Adam, an algorithm for first-order gradient-based optimization of stochastic objective functions, based on adaptive estimates of lower-order moments. The method is straightforward to implement, computationally efficient, and well-suited for problems with large data and parameters.'
  },
  {
    id: 'WOS-2023-112',
    title: 'Evaluating GPT-4 on Medical Licensing Examinations: Diagnostic Accuracy and Reasoning Trajectories',
    authors: 'Tiffany H. Kung, Morgan Cheatham, Aidan Gilson',
    journal: 'PLOS Digital Health',
    year: 2023,
    citations: 2150,
    litScore: 93,
    doi: '10.1371/journal.pdig.0000198',
    url: 'https://doi.org/10.1371/journal.pdig.0000198',
    tldr: 'TL;DR: Demonstrates that GPT-4 passed the US Medical Licensing Examination (USMLE) without specialized domain fine-tuning.',
    abstract: 'This study evaluated GPT-4 on the United States Medical Licensing Examination (USMLE). GPT-4 performed at or above the passing threshold of 60% accuracy across all exam steps, demonstrating high concordance and explainability in clinical reasoning without task-specific tuning.'
  },
  {
    id: 'SCOPUS-2025-004',
    title: 'Closed-Domain RAG for Scientific Literature Review: Comparative Benchmark of Vector Databases',
    authors: 'Alexander Wright, Chen Wei, Maria Santos',
    journal: 'ACM Computing Surveys',
    year: 2025,
    citations: 45,
    litScore: 89,
    doi: '10.1145/3651049',
    url: 'https://doi.org/10.1145/3651049',
    tldr: 'TL;DR: Benchmarks ChromaDB, Qdrant, and Pinecone on 500,000 Scopus abstracts, finding ChromaDB local index fastest for under 50k papers.',
    abstract: 'Selecting the optimal vector database is critical for domain-specific RAG applications. We benchmark ChromaDB, Qdrant, and Milvus on latency, recall rate, and memory footprint using 500k PubMed/Scopus paper embeddings. Results show ChromaDB achieves sub-50ms query latency for small-to-medium academic corpora.'
  }
];

export default function App() {
  const [activeTab, setActiveTab] = useState('search'); // 'search' | 'workspace' | 'history'
  const [searchQuery, setSearchQuery] = useState('large language models in healthcare');
  const [isSemanticMode, setIsSemanticMode] = useState(true);
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [selectedPaperIds, setSelectedPaperIds] = useState(['WOS-2024-001', 'SCOPUS-2024-089']);
  const [workspacePapers, setWorkspacePapers] = useState([MOCK_PAPERS[0], MOCK_PAPERS[1]]);
  const [activeCitation, setActiveCitation] = useState(MOCK_PAPERS[0]);
  const [chatMessages, setChatMessages] = useState([
    {
      sender: 'ai',
      text: `Based on your **${workspacePapers.length} selected papers** from Scopus & Web of Science, here is the synthesis:\n\n1. **Clinical Diagnostics**: Large language models have reached passing-level diagnostic accuracy (over 89%) across multiple medical specialties [1]. However, clinical deployment is hindered by a baseline 11% hallucination rate in patient record synthesis [1].\n\n2. **RAG Mitigation**: To eliminate these hallucinations, recent fine-tuning methods (such as SciRAG-FineTune) enforce strict citation alignment [2]. By fine-tuning Llama-3-8B on curated academic abstracts, researchers achieved 99.4% citation accuracy [2].`
    }
  ]);
  const [inputQuestion, setInputQuestion] = useState('');

  // Filter States
  const [minYear, setMinYear] = useState('2020');
  const [articleType, setArticleType] = useState('All');

  // Toggle selection
  const toggleSelectPaper = (id) => {
    if (selectedPaperIds.includes(id)) {
      setSelectedPaperIds(selectedPaperIds.filter(item => item !== id));
    } else {
      setSelectedPaperIds([...selectedPaperIds, id]);
    }
  };

  // Push to Workspace
  const pushToWorkspace = () => {
    const papersToPush = MOCK_PAPERS.filter(p => selectedPaperIds.includes(p.id));
    setWorkspacePapers(papersToPush);
    if (papersToPush.length > 0) {
      setActiveCitation(papersToPush[0]);
    }
    setActiveTab('workspace');
  };

  // Export to Excel
  const exportToExcel = () => {
    const papersToExport = MOCK_PAPERS.filter(p => selectedPaperIds.includes(p.id));
    const worksheetData = papersToExport.map(p => ({
      ID: p.id,
      Title: p.title,
      Authors: p.authors,
      Journal: p.journal,
      Year: p.year,
      Citations: p.citations,
      LitScore: p.litScore,
      DOI: p.doi,
      TLDR: p.tldr,
      Abstract: p.abstract
    }));

    const worksheet = XLSX.utils.json_to_sheet(worksheetData);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, 'LitReview_Export');
    XLSX.writeFile(workbook, `LitReview_Dataset_${new Date().toISOString().slice(0,10)}.xlsx`);
  };

  // Handle User Chat Input
  const handleSendMessage = (e) => {
    e.preventDefault();
    if (!inputQuestion.trim()) return;

    const userMsg = { sender: 'user', text: inputQuestion };
    setChatMessages(prev => [...prev, userMsg]);
    setInputQuestion('');

    // Simulate AI response
    setTimeout(() => {
      const aiReply = {
        sender: 'ai',
        text: `Regarding your query "${inputQuestion}": Research indicates that combining Vector DB retrieval with citation enforcement reduces hallucination risks significantly [2]. In clinical trials, models like GPT-4 required human validation prior to record insertion [1].`
      };
      setChatMessages(prev => [...prev, aiReply]);
    }, 800);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* HEADER NAVBAR */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-purple-600 flex items-center justify-center text-white font-bold text-xl shadow-md">
              L
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="font-extrabold text-lg text-slate-900 tracking-tight">LitReview AI Scholar</h1>
                <span className="px-2 py-0.5 text-xs font-semibold bg-blue-100 text-blue-700 rounded-full border border-blue-200">
                  Pro MVP v2.0
                </span>
              </div>
              <p className="text-xs text-slate-500">Scopus & Web of Science Closed-Domain Agent</p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex items-center bg-slate-100 p-1 rounded-xl border border-slate-200">
            <button
              onClick={() => setActiveTab('search')}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg transition-all ${
                activeTab === 'search'
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Search className="w-4 h-4" />
              <span>1. Academic Search</span>
            </button>

            <button
              onClick={() => setActiveTab('workspace')}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg transition-all ${
                activeTab === 'workspace'
                  ? 'bg-white text-purple-600 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Sparkles className="w-4 h-4 text-purple-600" />
              <span>2. AI Workspace</span>
              {workspacePapers.length > 0 && (
                <span className="w-5 h-5 bg-purple-600 text-white rounded-full text-xs flex items-center justify-center font-bold">
                  {workspacePapers.length}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab('history')}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg transition-all ${
                activeTab === 'history'
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <History className="w-4 h-4" />
              <span>History & Logs</span>
            </button>
          </nav>

          {/* Status Indicator */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-50 text-emerald-700 text-xs font-semibold rounded-lg border border-emerald-200">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span>Local Vector DB (550 Papers)</span>
            </div>
          </div>
        </div>
      </header>

      {/* MAIN CONTAINER */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-6">
        
        {/* ========================================================================= */}
        {/* TAB 1: ACADEMIC SEARCH ENGINE (SUPERIOR TO AIOT LAB SCHOLAR)             */}
        {/* ========================================================================= */}
        {activeTab === 'search' && (
          <div className="space-y-6">
            
            {/* Search Box Card */}
            <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
              <div className="flex flex-col md:flex-row gap-4 items-center">
                
                {/* Search Mode Switch */}
                <div className="flex bg-slate-100 p-1 rounded-xl border border-slate-200 shrink-0">
                  <button
                    onClick={() => setIsSemanticMode(true)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg transition-all ${
                      isSemanticMode ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-600'
                    }`}
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>AI Semantic Search</span>
                  </button>
                  <button
                    onClick={() => setIsSemanticMode(false)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg transition-all ${
                      !isSemanticMode ? 'bg-slate-800 text-white shadow-sm' : 'text-slate-600'
                    }`}
                  >
                    <Search className="w-3.5 h-3.5" />
                    <span>Exact Keyword</span>
                  </button>
                </div>

                {/* Input Bar */}
                <div className="relative flex-1 w-full">
                  <Search className="w-5 h-5 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search Scopus & Web of Science databases (e.g., 'LLM applications in diagnostic radiology')..."
                    className="w-full pl-12 pr-28 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white text-slate-800 font-medium transition-all"
                  />
                  <button className="absolute right-2 top-1/2 -translate-y-1/2 bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-lg text-sm font-semibold transition-all">
                    Search
                  </button>
                </div>
              </div>

              {/* Quick Preset Filter Chips */}
              <div className="flex flex-wrap items-center gap-2 pt-2">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Quick Trends:</span>
                {[
                  'LLM Healthcare 2024',
                  'RAG Hallucination Benchmark',
                  'Stochastic Optimization (Adam)',
                  'Medical Diagnostics Accuracy'
                ].map((chip, idx) => (
                  <button
                    key={idx}
                    onClick={() => setSearchQuery(chip)}
                    className="px-3 py-1 bg-slate-100 hover:bg-slate-200 text-slate-600 text-xs font-semibold rounded-full transition-all border border-slate-200"
                  >
                    + {chip}
                  </button>
                ))}

                <button
                  onClick={() => setShowAdvancedFilters(!showAdvancedFilters)}
                  className="ml-auto flex items-center gap-1 text-xs font-bold text-blue-600 hover:text-blue-700"
                >
                  <Filter className="w-3.5 h-3.5" />
                  <span>{showAdvancedFilters ? 'Hide Filters ▲' : 'Advanced Filters ▼'}</span>
                </button>
              </div>

              {/* Collapsible Advanced Filters */}
              {showAdvancedFilters && (
                <div className="pt-4 border-t border-slate-100 grid grid-cols-1 md:grid-cols-4 gap-4 bg-slate-50 p-4 rounded-xl">
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">Publication Year</label>
                    <select 
                      value={minYear} 
                      onChange={e => setMinYear(e.target.value)}
                      className="w-full p-2 text-xs border border-slate-200 rounded-lg bg-white"
                    >
                      <option value="2020">2020 - 2025 (Recent)</option>
                      <option value="2023">2023 - 2025 (Last 2 Years)</option>
                      <option value="all">All Years</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">Article Type</label>
                    <select 
                      value={articleType} 
                      onChange={e => setArticleType(e.target.value)}
                      className="w-full p-2 text-xs border border-slate-200 rounded-lg bg-white"
                    >
                      <option value="All">All Types (Review, Article)</option>
                      <option value="Review">Systematic Review Only</option>
                      <option value="Clinical Trial">Clinical Study / Trial</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">Minimum Citations</label>
                    <input 
                      type="number" 
                      placeholder="e.g. 50" 
                      className="w-full p-2 text-xs border border-slate-200 rounded-lg bg-white"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-1">Data Source</label>
                    <div className="flex gap-2 mt-1">
                      <label className="flex items-center gap-1 text-xs text-slate-700">
                        <input type="checkbox" defaultChecked /> Scopus
                      </label>
                      <label className="flex items-center gap-1 text-xs text-slate-700">
                        <input type="checkbox" defaultChecked /> Web of Science
                      </label>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Research Trend Chart Widget */}
            <div className="bg-gradient-to-r from-blue-900 to-indigo-900 rounded-2xl p-5 text-white flex flex-col md:flex-row items-center justify-between gap-4 shadow-lg">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-blue-400" />
                  <h3 className="font-bold text-base">Research Momentum Visualizer</h3>
                </div>
                <p className="text-xs text-blue-200">Publication growth for "{searchQuery}" surged 340% between 2023 and 2024.</p>
              </div>
              
              {/* Visual Bar Graph */}
              <div className="flex items-end gap-3 h-12 bg-white/10 p-2 rounded-xl border border-white/10">
                {[
                  { year: '2021', count: 20 },
                  { year: '2022', count: 45 },
                  { year: '2023', count: 120 },
                  { year: '2024', count: 280 },
                  { year: '2025', count: 85 }
                ].map((item, idx) => (
                  <div key={idx} className="flex flex-col items-center gap-1">
                    <div 
                      style={{ height: `${(item.count / 280) * 32}px` }} 
                      className="w-6 bg-gradient-to-t from-blue-400 to-cyan-300 rounded-t-sm"
                    ></div>
                    <span className="text-[10px] text-blue-200">{item.year}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Action Bar (Export to Excel & Push to Workspace) */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
              <div className="flex items-center gap-3">
                <span className="text-xs font-bold text-slate-600">
                  Selected: <strong className="text-blue-600 text-sm">{selectedPaperIds.length}</strong> / {MOCK_PAPERS.length} papers
                </span>
                <button
                  onClick={() => setSelectedPaperIds(MOCK_PAPERS.map(p => p.id))}
                  className="text-xs text-blue-600 hover:underline font-semibold"
                >
                  Select All
                </button>
                <button
                  onClick={() => setSelectedPaperIds([])}
                  className="text-xs text-slate-500 hover:underline font-semibold"
                >
                  Clear Selection
                </button>
              </div>

              <div className="flex items-center gap-3 w-full sm:w-auto">
                <button
                  onClick={exportToExcel}
                  className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold transition-all shadow-sm"
                >
                  <Download className="w-4 h-4" />
                  <span>Export to Excel (.xlsx)</span>
                </button>

                <button
                  onClick={pushToWorkspace}
                  disabled={selectedPaperIds.length === 0}
                  className="flex-1 sm:flex-none flex items-center justify-center gap-2 px-5 py-2 bg-gradient-to-r from-blue-600 to-purple-600 hover:opacity-95 text-white rounded-xl text-xs font-bold transition-all shadow-md disabled:opacity-50"
                >
                  <Sparkles className="w-4 h-4" />
                  <span>Push {selectedPaperIds.length} Papers to AI Workspace →</span>
                </button>
              </div>
            </div>

            {/* Papers Data Table */}
            <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-slate-50 border-b border-slate-200 text-xs font-bold text-slate-600 uppercase tracking-wider">
                      <th className="p-4 w-12 text-center">Select</th>
                      <th className="p-4">Paper Title & Source</th>
                      <th className="p-4 w-28">LitScore 🎖️</th>
                      <th className="p-4">Authors & Journal</th>
                      <th className="p-4 w-24">Citations</th>
                      <th className="p-4">TL;DR AI Summary</th>
                      <th className="p-4 w-28 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-xs">
                    {MOCK_PAPERS.map((paper) => {
                      const isSelected = selectedPaperIds.includes(paper.id);
                      return (
                        <tr 
                          key={paper.id}
                          className={`hover:bg-slate-50 transition-colors ${isSelected ? 'bg-blue-50/50' : ''}`}
                        >
                          <td className="p-4 text-center">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => toggleSelectPaper(paper.id)}
                              className="w-4 h-4 rounded text-blue-600 focus:ring-blue-500 border-slate-300"
                            />
                          </td>
                          <td className="p-4">
                            <div className="space-y-1">
                              <a
                                href={paper.url}
                                target="_blank"
                                rel="noreferrer"
                                className="font-bold text-slate-900 hover:text-blue-600 text-sm line-clamp-2 flex items-center gap-1.5"
                              >
                                <span>{paper.title}</span>
                                <ExternalLink className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                              </a>
                              <div className="flex items-center gap-2 text-[11px] text-slate-500">
                                <span className="font-mono bg-slate-100 px-1.5 py-0.5 rounded text-slate-600">{paper.id}</span>
                                <span>DOI: {paper.doi}</span>
                              </div>
                            </div>
                          </td>
                          <td className="p-4">
                            <span className="badge-litscore text-xs">
                              <Award className="w-3.5 h-3.5 text-amber-600" />
                              <span>{paper.litScore}/100</span>
                            </span>
                          </td>
                          <td className="p-4">
                            <div className="space-y-0.5">
                              <p className="font-medium text-slate-800 line-clamp-1">{paper.authors}</p>
                              <p className="text-slate-500 italic">{paper.journal} ({paper.year})</p>
                            </div>
                          </td>
                          <td className="p-4">
                            <span className="font-bold text-slate-900 bg-slate-100 px-2 py-1 rounded-md">
                              {paper.citations.toLocaleString()}
                            </span>
                          </td>
                          <td className="p-4 max-w-xs">
                            <p className="text-slate-600 text-[11px] line-clamp-2 bg-amber-50/60 p-2 rounded-lg border border-amber-100">
                              {paper.tldr}
                            </p>
                          </td>
                          <td className="p-4 text-right">
                            <a
                              href={paper.url}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex items-center gap-1 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-lg transition-all"
                            >
                              <FileText className="w-3.5 h-3.5" />
                              <span>PDF Link</span>
                            </a>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 2: LITREVIEW AI WORKSPACE (NOTEBOOKLM SPLIT-SCREEN VERIFICATION)       */}
        {/* ========================================================================= */}
        {activeTab === 'workspace' && (
          <div className="space-y-4">
            
            {/* Top Workspace Bar */}
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-100 text-purple-700 rounded-lg">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="font-bold text-slate-900 text-sm">Grounded Academic Workspace</h2>
                  <p className="text-xs text-slate-500">
                    Loaded <strong>{workspacePapers.length} papers</strong> for zero-hallucination synthesis
                  </p>
                </div>
              </div>

              {/* Action Chips */}
              <div className="flex items-center gap-2 flex-wrap">
                <button className="px-3 py-1.5 bg-purple-50 hover:bg-purple-100 text-purple-700 text-xs font-bold rounded-lg border border-purple-200 transition-all">
                  💡 Research Gap Detector
                </button>
                <button className="px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 text-xs font-bold rounded-lg border border-blue-200 transition-all">
                  📊 Auto-Generate Comparison Table
                </button>
              </div>
            </div>

            {/* SPLIT SCREEN LAYOUT */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              
              {/* LEFT SIDE (60%): CHAT & SYNTHESIS */}
              <div className="lg:col-span-7 space-y-4">
                <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4 min-h-[500px] flex flex-col justify-between">
                  
                  {/* Chat Message List */}
                  <div className="space-y-4">
                    {chatMessages.map((msg, idx) => (
                      <div
                        key={idx}
                        className={`flex gap-3 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                      >
                        {msg.sender === 'ai' && (
                          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-purple-600 text-white flex items-center justify-center font-bold text-xs shrink-0">
                            AI
                          </div>
                        )}
                        <div
                          className={`p-4 rounded-2xl max-w-xl text-xs leading-relaxed ${
                            msg.sender === 'user'
                              ? 'bg-blue-600 text-white font-medium'
                              : 'bg-slate-50 border border-slate-200 text-slate-800 space-y-2'
                          }`}
                        >
                          <div dangerouslySetInnerHTML={{ __html: msg.text.replace(/\n/g, '<br/>') }} />

                          {/* Render Citation Clickable Buttons if AI message */}
                          {msg.sender === 'ai' && (
                            <div className="pt-2 border-t border-slate-200 flex items-center gap-2">
                              <span className="text-[10px] font-bold text-slate-400 uppercase">Click to Verify:</span>
                              {workspacePapers.map((paper, pIdx) => (
                                <button
                                  key={pIdx}
                                  onClick={() => setActiveCitation(paper)}
                                  className={`px-2 py-0.5 text-[10px] font-bold rounded ${
                                    activeCitation?.id === paper.id
                                      ? 'bg-purple-600 text-white'
                                      : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
                                  }`}
                                >
                                  [{pIdx + 1}] {paper.id}
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Auto-Generated Comparison Table Widget */}
                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <h4 className="font-bold text-xs text-slate-800 flex items-center gap-1.5">
                        <Layers className="w-4 h-4 text-purple-600" />
                        <span>Auto-Generated Literature Comparison Table</span>
                      </h4>
                      <span className="text-[10px] bg-purple-100 text-purple-700 px-2 py-0.5 rounded font-bold">Auto-Synthesized</span>
                    </div>

                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-[11px] border-collapse bg-white rounded-lg overflow-hidden border border-slate-200">
                        <thead>
                          <tr className="bg-slate-100 text-slate-700 font-bold border-b border-slate-200">
                            <th className="p-2">Paper</th>
                            <th className="p-2">Core Focus</th>
                            <th className="p-2">Limitation / Gap</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {workspacePapers.map((paper, idx) => (
                            <tr key={idx} className="hover:bg-slate-50">
                              <td className="p-2 font-bold text-blue-600">[{idx+1}] {paper.id}</td>
                              <td className="p-2 text-slate-800">{paper.tldr.slice(7, 60)}...</td>
                              <td className="p-2 text-slate-500">Requires validation on larger patient cohorts</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Chat Input Bar */}
                  <form onSubmit={handleSendMessage} className="relative pt-2">
                    <input
                      type="text"
                      value={inputQuestion}
                      onChange={e => setInputQuestion(e.target.value)}
                      placeholder="Ask AI assistant about limitations, methodology, or future research gaps..."
                      className="w-full pl-4 pr-24 py-3 bg-slate-100 border border-slate-200 rounded-xl text-xs focus:bg-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                    />
                    <button
                      type="submit"
                      className="absolute right-2 top-1/2 -translate-y-1/2 bg-purple-600 hover:bg-purple-700 text-white px-4 py-1.5 rounded-lg text-xs font-bold transition-all"
                    >
                      Send
                    </button>
                  </form>
                </div>
              </div>

              {/* RIGHT SIDE (40%): INSTANT VERIFICATION PANEL (ZERO HALLUCINATION) */}
              <div className="lg:col-span-5 space-y-4">
                <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4 sticky top-20">
                  <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="w-5 h-5 text-emerald-600" />
                      <h3 className="font-bold text-slate-900 text-sm">Source Verification Panel</h3>
                    </div>
                    <span className="text-[10px] font-bold bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full">
                      Zero-Hallucination
                    </span>
                  </div>

                  {activeCitation ? (
                    <div className="space-y-4 text-xs">
                      <div>
                        <span className="font-mono text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                          Selected Citation: {activeCitation.id}
                        </span>
                        <h4 className="font-bold text-slate-900 text-sm mt-2 leading-snug">
                          {activeCitation.title}
                        </h4>
                      </div>

                      <div className="space-y-1 text-slate-600">
                        <p><strong>Authors:</strong> {activeCitation.authors}</p>
                        <p><strong>Source:</strong> {activeCitation.journal} ({activeCitation.year})</p>
                        <p><strong>DOI:</strong> <a href={activeCitation.url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">{activeCitation.doi}</a></p>
                      </div>

                      {/* Highlighted Abstract Snippet */}
                      <div className="space-y-2">
                        <h5 className="font-bold text-slate-800 text-xs">Full Abstract Grounding:</h5>
                        <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl leading-relaxed text-slate-700 text-xs">
                          {activeCitation.abstract}
                        </div>
                      </div>

                      <a
                        href={activeCitation.url}
                        target="_blank"
                        rel="noreferrer"
                        className="w-full flex items-center justify-center gap-2 py-2.5 bg-slate-900 hover:bg-slate-800 text-white rounded-xl font-bold transition-all text-xs"
                      >
                        <ExternalLink className="w-4 h-4" />
                        <span>Download Full Paper PDF (Publisher Source)</span>
                      </a>
                    </div>
                  ) : (
                    <p className="text-slate-400 text-xs italic">Click a citation tag like [1] in the chat to inspect its ground truth abstract.</p>
                  )}
                </div>
              </div>

            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* TAB 3: HISTORY & EXPORTS                                                   */}
        {/* ========================================================================= */}
        {activeTab === 'history' && (
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
            <h2 className="font-bold text-slate-900 text-base">Export & Query History</h2>
            <p className="text-xs text-slate-500">Track all dataset downloads and previous literature review sessions.</p>
            
            <div className="divide-y divide-slate-100 text-xs">
              <div className="py-3 flex items-center justify-between">
                <div>
                  <p className="font-bold text-slate-800">LitReview_Dataset_2026-08-03.xlsx</p>
                  <p className="text-slate-500">5 Papers exported to Excel format</p>
                </div>
                <span className="px-2 py-1 bg-emerald-100 text-emerald-700 font-bold rounded">Completed</span>
              </div>
              <div className="py-3 flex items-center justify-between">
                <div>
                  <p className="font-bold text-slate-800">scopus_dataset_full.csv</p>
                  <p className="text-slate-500">550 Scopus & Web of Science records crawled</p>
                </div>
                <span className="px-2 py-1 bg-blue-100 text-blue-700 font-bold rounded">In Vector DB</span>
              </div>
            </div>
          </div>
        )}

      </main>
    </div>
  );
}
