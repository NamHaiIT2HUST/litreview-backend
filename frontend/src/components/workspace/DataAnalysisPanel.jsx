import React, { useRef, useState } from 'react';
import { 
  Send, 
  Paperclip, 
  X, 
  BarChart2, 
  Copy, 
  Check, 
  Sparkles, 
  FileSpreadsheet, 
  TrendingUp, 
  PieChart, 
  Database,
  ArrowRight,
  RefreshCw,
  Zap,
  ChevronDown,
  ChevronUp,
  Microscope,
  HelpCircle,
  FolderOpen,
  FileCode,
  Layers
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import * as XLSX from 'xlsx';
import { useLanguage } from '../../contexts/LanguageContext';
import { safeFetch } from '../../utils/apiConfig';
import DynamicDataChart, { KPICardsGrid, DatasetHealthCard } from './DataCharts';

// Preloaded Demo Datasets inspired by ASTA
const DEMO_DATASETS = {
  air_quality: {
    name: 'air_quality_seasonal.csv',
    label: 'Chất lượng không khí (AQI & Mùa)',
    content: `Date,Month,Season,AQI,PM25,PM10,SO2,NO2,CO,O3_8h,Temperature_C,Humidity_Pct
2023-01-15,Jan,Winter,165,85.2,142.1,32.4,54.1,1.8,24.5,8.5,78
2023-02-14,Feb,Winter,142,68.4,118.0,28.1,48.2,1.5,28.0,11.2,72
2023-03-20,Mar,Spring,95,35.0,72.4,18.5,36.0,0.9,45.2,18.4,65
2023-04-18,Apr,Spring,82,28.6,60.1,15.2,30.5,0.8,52.1,23.1,62
2023-05-22,May,Summer,64,18.4,42.0,11.0,24.0,0.6,68.4,29.5,70
2023-06-19,Jun,Summer,55,14.2,35.5,9.2,20.1,0.5,75.0,33.2,76
2023-07-25,Jul,Summer,48,12.0,30.2,8.0,18.5,0.4,82.1,35.0,80
2023-08-20,Aug,Summer,52,13.5,33.0,8.5,19.2,0.5,78.5,34.1,82
2023-09-18,Sep,Autumn,88,32.1,68.4,16.4,32.8,0.8,55.0,27.4,74
2023-10-22,Oct,Autumn,115,52.4,98.2,22.0,42.5,1.2,40.1,21.0,68
2023-11-19,Nov,Winter,155,78.9,135.0,29.5,50.8,1.6,26.4,14.2,75
2023-12-21,Dec,Winter,178,94.5,158.2,35.2,58.4,2.0,21.0,7.8,81`
  },
  titanic: {
    name: 'titanic_survival.csv',
    label: 'Titanic Survival Dataset',
    content: `PassengerId,Survived,Pclass,Sex,Age,SibSp,Parch,Fare,Embarked,Class_Category
1,0,3,male,22,1,0,7.25,S,Third Class
2,1,1,female,38,1,0,71.28,C,First Class
3,1,3,female,26,0,0,7.925,S,Third Class
4,1,1,female,35,1,0,53.1,S,First Class
5,0,3,male,35,0,0,8.05,S,Third Class
6,0,3,male,28,0,0,8.46,Q,Third Class
7,0,1,male,54,0,0,51.86,S,First Class
8,0,3,male,2,3,1,21.075,S,Third Class
9,1,3,female,27,0,2,11.13,S,Third Class
10,1,2,female,14,1,0,30.07,C,Second Class
11,1,3,female,4,1,1,16.7,S,Third Class
12,1,1,female,58,0,0,26.55,S,First Class
13,0,3,male,20,0,0,8.05,S,Third Class
14,0,3,male,39,1,5,31.275,S,Third Class
15,1,2,female,55,0,0,16.0,S,Second Class`
  },
  cell_biology: {
    name: 'tabula_macrophages_expression.csv',
    label: 'Tabula Sapiens - Macrophages Expression',
    content: `Cell_ID,Tissue,Subpopulation,M1_Score,M2_Score,CD68_Exp,CD163_Exp,TNF_Exp,IL10_Exp,Status
Cell_001,Kidney,M1-skewed,0.88,0.21,8.4,1.2,6.5,0.8,Pro-inflammatory
Cell_002,Kidney,M1-skewed,0.79,0.25,7.9,1.5,5.9,1.1,Pro-inflammatory
Cell_003,Kidney,M2-skewed,0.24,0.85,6.8,7.8,1.2,5.8,Anti-inflammatory
Cell_004,Kidney,M2-skewed,0.18,0.92,7.1,8.4,0.9,6.4,Anti-inflammatory
Cell_005,Kidney,Intermediate,0.52,0.49,7.5,4.2,3.1,3.4,Transitioning
Cell_006,Heart,M2-skewed,0.15,0.89,6.5,8.1,0.8,6.0,Anti-inflammatory
Cell_007,Heart,M1-skewed,0.82,0.19,8.0,1.1,6.1,0.9,Pro-inflammatory
Cell_008,Lung,M1-skewed,0.91,0.22,8.9,1.4,7.2,1.0,Pro-inflammatory
Cell_009,Lung,M2-skewed,0.22,0.81,6.9,7.5,1.4,5.2,Anti-inflammatory
Cell_010,Lung,Intermediate,0.48,0.53,7.2,4.5,2.9,3.8,Transitioning`
  }
};

export default function DataAnalysisPanel({ workspacePapers = [], darkMode, onSendToChat }) {
  const { t, language } = useLanguage();
  const isEn = language === 'en';

  const [messages, setMessages] = useState(() => [
    {
      sender: 'ai',
      text: isEn
        ? "Welcome to DataVoyager Analytics! Upload an Excel/CSV dataset to perform in-depth statistical synthesis, hypothesis testing, and exploratory data analysis (EDA)."
        : "Chào mừng bạn đến với DataVoyager Analytics! Tải lên tệp Excel/CSV để chạy phân tích thống kê định lượng, kiểm định giả thuyết và phân tích dữ liệu khám phá (EDA).",
      chart: null,
      kpis: null,
    }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [attachedFile, setAttachedFile] = useState(null);
  const [datasetProfile, setDatasetProfile] = useState(null);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [showExampleQueries, setShowExampleQueries] = useState(true);
  
  // History State
  const [sessions, setSessions] = useState(() => {
    try {
      const saved = localStorage.getItem('workspace_eda_sessions');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  React.useEffect(() => {
    if (messages.length <= 1) return;
    
    setSessions(prev => {
      let newSessions = [...prev];
      const existingIdx = newSessions.findIndex(s => s.id === activeSessionId);
      
      const sessionData = {
        id: activeSessionId || Date.now().toString(),
        timestamp: Date.now(),
        title: attachedFile?.name || datasetProfile?.filename || messages[1]?.text?.slice(0, 30) || 'Phân tích mới',
        messages: messages,
        profile: datasetProfile
      };

      if (existingIdx >= 0) {
        newSessions[existingIdx] = sessionData;
      } else {
        newSessions = [sessionData, ...newSessions];
        if (!activeSessionId) {
          setTimeout(() => setActiveSessionId(sessionData.id), 0);
        }
      }
      
      localStorage.setItem('workspace_eda_sessions', JSON.stringify(newSessions));
      return newSessions;
    });
  }, [messages, datasetProfile, activeSessionId, attachedFile]);

  const handleNewSession = () => {
    setActiveSessionId(null);
    setDatasetProfile(null);
    setAttachedFile(null);
    setMessages([{
      sender: 'ai',
      text: isEn
        ? "Welcome to DataVoyager Analytics! Upload an Excel/CSV dataset to perform in-depth statistical synthesis, hypothesis testing, and exploratory data analysis (EDA)."
        : "Chào mừng bạn đến với DataVoyager Analytics! Tải lên tệp Excel/CSV để chạy phân tích thống kê định lượng, kiểm định giả thuyết và phân tích dữ liệu khám phá (EDA).",
      chart: null,
      kpis: null,
    }]);
    setIsSidebarOpen(false);
  };

  const loadSession = (session) => {
    setActiveSessionId(session.id);
    setMessages(session.messages || []);
    setDatasetProfile(session.profile || null);
    setAttachedFile(null);
    setIsSidebarOpen(false);
  };

  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);

  // ASTA 4-Category Example Queries Matrix
  const exampleQueryCategories = [
    {
      icon: <Sparkles className="w-4 h-4 text-emerald-500" />,
      title: isEn ? "Explore Tabula Sapiens & Biological Datasets" : "Khám phá Tập dữ liệu Y sinh & Tabula Sapiens",
      subtitle: isEn ? "Analyze cell types, compare across organs, and uncover biological insights." : "Phân tích loại tế bào, so sánh các cơ quan và trích xuất hiểu biết sinh học.",
      datasetKey: 'cell_biology',
      queries: [
        isEn 
          ? "Test whether kidney macrophages contain distinct subpopulations along the M1-M2 spectrum rather than being a homogeneous M2-skewed population." 
          : "Kiểm tra xem đại thực bào thận (kidney macrophages) có các phân nhóm riêng biệt dọc theo phổ M1-M2 hay là một quần thể thuần nhất thiên về M2.",
        isEn 
          ? "Compare M1 vs M2 expression scores across Kidney, Heart, and Lung tissues." 
          : "So sánh điểm biểu hiện M1 và M2 giữa các mô Thận (Kidney), Tim (Heart) và Phổi (Lung)."
      ]
    },
    {
      icon: <FolderOpen className="w-4 h-4 text-blue-500" />,
      title: isEn ? "Understand your Data & Seasonal Variations" : "Khám phá Dữ liệu Môi trường & Khí tượng",
      subtitle: isEn ? "Spot patterns, seasonal shifts, key variables, and data issues at a glance." : "Nhận diện quy luật, biến thiên theo mùa và các chất ô nhiễm nổi bật.",
      datasetKey: 'air_quality',
      queries: [
        isEn 
          ? "Investigate how air quality indicators (AQI, PM2.5, PM10, SO2, NO2) vary across different seasons and identify peak pollution periods." 
          : "Phân tích xu hướng chỉ số không khí (AQI, PM2.5, PM10, SO2, NO2) biến thiên theo 4 mùa và chỉ ra mùa nào ô nhiễm cao nhất.",
        isEn 
          ? "Calculate the ratio of PM2.5 to PM10 over time and plot the correlation with temperature." 
          : "Tính tỉ lệ đóng góp của PM2.5 / PM10 theo thời gian và vẽ biểu đồ tương quan với nhiệt độ."
      ]
    },
    {
      icon: <Microscope className="w-4 h-4 text-amber-500" />,
      title: isEn ? "Ask Scientific Questions & Test Hypotheses" : "Đặt câu hỏi Khoa học & Kiểm định Giả thuyết",
      subtitle: isEn ? "Compare groups, test hypotheses, and evaluate demographic or statistical differences." : "So sánh nhóm, kiểm định giả định và phân tích nhân tố tác động.",
      datasetKey: 'titanic',
      queries: [
        isEn 
          ? "What features differ most between survivors and non-survivors in the Titanic dataset? Analyze by Class, Sex and Age." 
          : "Những đặc trưng nào khác biệt rõ nhất giữa người sống sót và không sống sót? Phân tích theo Hạng vé, Giới tính và Độ tuổi.",
        isEn 
          ? "Who was most likely to survive the Titanic, and why? Please calculate percentages and visualize the results." 
          : "Nhóm hành khách nào có xác suất sống sót cao nhất và tại sao? Hãy tính tỉ lệ % và trực quan hóa kết quả."
      ]
    }
  ];

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });



  const handleSelectDemoDataset = (key) => {
    if (DEMO_DATASETS[key]) {
      setAttachedFile({
        name: DEMO_DATASETS[key].name,
        content: DEMO_DATASETS[key].content
      });
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const fileName = file.name.toLowerCase();

    // Support Excel binary files (.xlsx, .xls) by converting to clean CSV text
    if (fileName.endsWith('.xlsx') || fileName.endsWith('.xls')) {
      const reader = new FileReader();
      reader.onload = (ev) => {
        try {
          const data = new Uint8Array(ev.target.result);
          const workbook = XLSX.read(data, { type: 'array' });
          const firstSheetName = workbook.SheetNames[0];
          const worksheet = workbook.Sheets[firstSheetName];
          const csvText = XLSX.utils.sheet_to_csv(worksheet);
          setAttachedFile({ name: file.name, content: csvText });
        } catch (err) {
          console.error('Error parsing Excel file in browser:', err);
          alert('Không thể đọc file Excel. Vui lòng kiểm tra lại định dạng.');
        }
      };
      reader.readAsArrayBuffer(file);
    } else {
      // Plain text CSV / TSV / JSON
      const reader = new FileReader();
      reader.onload = (ev) => {
        setAttachedFile({ name: file.name, content: ev.target.result });
      };
      reader.readAsText(file, 'utf-8');
    }
    e.target.value = null;
  };

  const handleSend = async (e, customText = null, customFile = null) => {
    if (e) e.preventDefault();
    const question = (customText || input).trim();
    if (!question) return;

    const fileToUse = customFile || attachedFile;
    const userMsg = { 
      sender: 'user', 
      text: question, 
      attachment: fileToUse ? fileToUse.name : null 
    };
    
    setMessages((prev) => [...prev, userMsg]);
    if (!customText) setInput('');
    
    const fileSnapshot = fileToUse;
    setAttachedFile(null);
    setIsTyping(true);
    setTimeout(scrollToBottom, 50);

    try {
      const res = await safeFetch('/workspace/analyze-data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          question, 
          csv_text: fileSnapshot?.content ?? '', 
          filename: fileSnapshot?.name ?? '' 
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Lỗi máy chủ (${res.status})`);
      }
      
      const data = await res.json();

      if (data.dataset_profile) {
        setDatasetProfile(data.dataset_profile);
      }

      setMessages((prev) => [
        ...prev, 
        { 
          sender: 'ai', 
          text: data.answer ?? data.detail ?? 'Hoàn tất phân tích dữ liệu.',
          charts: data.charts ?? (data.chart ? [data.chart] : null),
          kpis: data.kpis ?? null,
          profile: data.dataset_profile ?? null,
        }
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev, 
        { 
          sender: 'ai', 
          text: `❌ Lỗi khi phân tích dữ liệu: ${err.message}. Vui lòng thử lại.` 
        }
      ]);
    } finally {
      setIsTyping(false);
      setTimeout(scrollToBottom, 50);
    }
  };

  const handleAutoEDA = () => {
    if (!attachedFile) return;
    const promptText = isEn
      ? "Perform a comprehensive Exploratory Data Analysis (EDA) on this dataset: evaluate descriptive statistics, data distribution, identify key trends, correlations, and outliers. Generate visual charts and key KPIs."
      : "Hãy thực hiện Phân tích Dữ liệu Khám phá (EDA) toàn diện trên tập dữ liệu này: thống kê mô tả, phân bố dữ liệu, tìm ra các xu hướng nổi bật, mối tương quan và các điểm ngoại lai. Hãy sinh biểu đồ trực quan và các chỉ số KPIs quan trọng.";
    
    handleSend(null, promptText, attachedFile);
  };

  const handleCopy = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const dm = darkMode;

  return (
    <div className="flex-1 min-h-0 flex relative bg-transparent overflow-hidden">
      
      {/* Sidebar Backdrop Overlay */}
      {isSidebarOpen && (
        <div 
          className="absolute inset-0 bg-slate-900/20 backdrop-blur-sm z-40 transition-opacity"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* History Sidebar */}
      <div className={`absolute top-0 left-0 h-full w-72 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 z-50 transform transition-transform duration-300 shadow-xl flex flex-col ${
        isSidebarOpen ? 'translate-x-0' : '-translate-x-full'
      }`}>
        <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-blue-500" />
            <h3 className="font-bold text-sm text-slate-800 dark:text-slate-200">
              {isEn ? 'Analysis History' : 'Lịch sử phân tích'}
            </h3>
          </div>
          <button 
            onClick={() => setIsSidebarOpen(false)}
            className="p-1 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        
        <div className="p-3 border-b border-slate-200 dark:border-slate-800 shrink-0">
          <button
            onClick={handleNewSession}
            className="w-full py-2 bg-blue-50 hover:bg-blue-100 dark:bg-blue-900/30 dark:hover:bg-blue-900/50 text-blue-600 dark:text-blue-400 rounded-lg text-xs font-bold transition-colors flex items-center justify-center gap-2 cursor-pointer"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>{isEn ? 'New Analysis' : 'Phiên phân tích mới'}</span>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1 custom-scrollbar">
          {sessions.length === 0 ? (
            <div className="text-center p-4 text-xs text-slate-500">
              {isEn ? 'No history yet.' : 'Chưa có lịch sử phân tích.'}
            </div>
          ) : (
            sessions.map(s => (
              <button
                key={s.id}
                onClick={() => loadSession(s)}
                className={`w-full text-left p-3 rounded-xl transition-all flex flex-col gap-1 cursor-pointer ${
                  activeSessionId === s.id 
                    ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800/50 border shadow-sm' 
                    : 'hover:bg-slate-50 dark:hover:bg-slate-800/50 border border-transparent'
                }`}
              >
                <div className="text-xs font-semibold text-slate-700 dark:text-slate-300 truncate">
                  {s.title}
                </div>
                <div className="text-[10px] text-slate-400">
                  {new Date(s.timestamp).toLocaleString(isEn ? 'en-US' : 'vi-VN')}
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col relative w-full h-full">

      {/* Toggle Sidebar Button */}
      <button
        onClick={() => setIsSidebarOpen(true)}
        className={`absolute top-4 left-4 z-40 p-2 rounded-xl border bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 shadow-sm transition-all cursor-pointer ${isSidebarOpen ? 'opacity-0 pointer-events-none' : 'opacity-100'}`}
        title={isEn ? "History" : "Lịch sử"}
      >
        <FolderOpen className="w-4 h-4" />
      </button>

      {/* Main Conversation & Analysis Feed */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        <div className="w-full max-w-4xl mx-auto space-y-6 py-6 px-4 md:px-8">
          
          {/* Active Dataset Profile Health Card */}
          {datasetProfile && (
            <DatasetHealthCard 
              profile={datasetProfile} 
              filename={attachedFile?.name || 'Tập dữ liệu đã phân tích'} 
              darkMode={dm}
              onRunAutoEDA={handleAutoEDA}
            />
          )}

          {messages.map((msg, idx) => (
            <div key={idx} className={`flex gap-3.5 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.sender === 'ai' && (
                <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white flex items-center justify-center shrink-0 shadow-md">
                  <BarChart2 className="w-4 h-4" />
                </div>
              )}

              <div className={`text-[14px] leading-relaxed ${
                msg.sender === 'user'
                  ? 'px-5 py-3.5 rounded-3xl rounded-tr-sm max-w-[85%] md:max-w-[75%] bg-blue-600 text-white font-medium shadow-sm'
                  : dm ? 'py-1.5 w-full max-w-full text-slate-200' : 'py-1.5 w-full max-w-full text-slate-800'
              }`}>
                
                {/* User Attachment Chip */}
                {msg.attachment && (
                  <div className="mb-2 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-[11px] font-semibold border border-blue-200 dark:border-blue-800/50">
                    <Paperclip className="w-3 h-3" />
                    <span>{msg.attachment}</span>
                  </div>
                )}

                {/* Markdown Narrative */}
                <div className={msg.sender === 'user' ? 'whitespace-pre-wrap mb-3' : 'prose prose-slate dark:prose-invert max-w-none prose-p:text-[13.5px] prose-p:leading-relaxed prose-headings:font-bold prose-h1:text-[16px] prose-h2:text-[15px] prose-h3:text-[14px] prose-li:text-[13.5px] prose-pre:bg-slate-900 prose-table:text-[12.5px] mb-3'}>
                  {msg.sender === 'user' ? msg.text : (
                    <ReactMarkdown 
                      remarkPlugins={[remarkGfm]}
                      components={{
                        code({node, inline, className, children, ...props}) {
                          const match = /language-(\w+)/.exec(className || '')
                          const lang = match ? match[1] : ''
                          const codeStr = String(children).replace(/\n$/, '')
                          if (!inline && lang === 'python') {
                            return (
                              <div className="relative group rounded-lg overflow-hidden my-3 border border-slate-700">
                                <div className="flex justify-between items-center bg-slate-800 px-3 py-1.5 border-b border-slate-700">
                                  <span className="text-[11px] font-mono font-bold text-slate-300">Python Script (EDA)</span>
                                  <button
                                    onClick={() => {
                                      const blob = new Blob([codeStr], { type: 'text/plain' });
                                      const url = URL.createObjectURL(blob);
                                      const a = document.createElement('a');
                                      a.href = url;
                                      a.download = 'eda_analysis.py';
                                      a.click();
                                      URL.revokeObjectURL(url);
                                    }}
                                    className="text-[10px] font-bold px-2 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded transition-colors flex items-center gap-1 cursor-pointer"
                                  >
                                    <FileCode className="w-3 h-3" />
                                    <span>Tải code (.py)</span>
                                  </button>
                                </div>
                                <div className="max-h-32 overflow-y-auto bg-slate-900 custom-scrollbar p-3">
                                  <code className="text-xs font-mono text-emerald-400 whitespace-pre-wrap" {...props}>
                                    {children}
                                  </code>
                                </div>
                              </div>
                            )
                          }
                          return <code className={className} {...props}>{children}</code>
                        }
                      }}
                    >
                      {msg.text}
                    </ReactMarkdown>
                  )}
                </div>

                {/* KPI Metrics Cards */}
                {msg.kpis && msg.kpis.length > 0 && (
                  <KPICardsGrid kpis={msg.kpis} darkMode={dm} />
                )}

                {/* Interactive Visual Charts */}
                {msg.charts && msg.charts.length > 0 && (
                  <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 mt-4">
                    {msg.charts.map((chartItem, cIdx) => (
                      <DynamicDataChart key={cIdx} chart={chartItem} darkMode={dm} />
                    ))}
                  </div>
                )}

                {/* AI Footer Actions */}
                {msg.sender === 'ai' && (
                  <div className="flex items-center gap-2 mt-3 pt-3 border-t border-slate-200 dark:border-slate-800">
                    <button
                      onClick={() => handleCopy(msg.text, idx)}
                      className={`px-2 py-1 rounded-md text-xs font-semibold transition-colors flex items-center gap-1 cursor-pointer ${
                        copiedIndex === idx
                          ? 'text-emerald-500 bg-emerald-50 dark:bg-emerald-900/30'
                          : 'text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800'
                      }`}
                      title="Sao chép nội dung phân tích"
                    >
                      {copiedIndex === idx ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copiedIndex === idx ? 'Đã sao chép' : 'Sao chép'}</span>
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Typing Indicator */}
          {isTyping && (
            <div className="flex gap-3.5 justify-start">
              <div className="w-9 h-9 rounded-xl bg-blue-600 text-white flex items-center justify-center shrink-0 shadow-md">
                <BarChart2 className="w-4 h-4" />
              </div>
              <div className={`py-2 px-4 rounded-2xl flex items-center gap-2 ${dm ? 'bg-slate-900 text-slate-300' : 'bg-slate-100 text-slate-700'}`}>
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-blue-500" />
                <span className="text-xs font-semibold">DataVoyager đang tính toán thống kê & phân tích dữ liệu...</span>
              </div>
            </div>
          )}

          {/* ASTA Style Example Queries Matrix Hub */}
          {messages.length === 1 && (
            <div className="pt-2 space-y-3">
              <div className="flex items-center justify-between border-b pb-2 dark:border-slate-800 border-slate-200">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-emerald-500" />
                  <span className="text-xs font-extrabold uppercase tracking-wider text-slate-600 dark:text-slate-300">
                    {isEn ? 'ASTA Scientific Query Library' : 'Thư viện Câu hỏi & Bộ Dữ liệu Mẫu (ASTA Style)'}
                  </span>
                </div>

                <button
                  onClick={() => setShowExampleQueries(!showExampleQueries)}
                  className="text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1 cursor-pointer"
                >
                  <span>{showExampleQueries ? (isEn ? 'Hide example queries' : 'Ẩn câu hỏi mẫu') : (isEn ? 'Show example queries' : 'Hiện câu hỏi mẫu')}</span>
                  {showExampleQueries ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>
              </div>

              {showExampleQueries && (
                <div className="space-y-3 animate-in fade-in duration-200">
                  {exampleQueryCategories.map((cat, catIdx) => (
                    <div 
                      key={catIdx}
                      className={`p-4 rounded-2xl border transition-all ${
                        dm ? 'bg-slate-900/60 border-slate-800/80 hover:border-slate-700' : 'bg-white border-slate-200/90 shadow-2xs hover:border-slate-300'
                      }`}
                    >
                      <div className="flex items-start gap-2.5 mb-2.5">
                        <div className="p-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 shrink-0 mt-0.5">
                          {cat.icon}
                        </div>
                        <div>
                          <h4 className="font-bold text-xs text-slate-800 dark:text-slate-100 flex items-center gap-2">
                            <span>{cat.title}</span>
                          </h4>
                          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                            {cat.subtitle}
                          </p>
                        </div>
                      </div>

                      <div className="space-y-1.5 pl-8">
                        {cat.queries.map((q, qIdx) => (
                          <button
                            key={qIdx}
                            onClick={() => {
                              handleSelectDemoDataset(cat.datasetKey);
                              const fileObj = (DEMO_DATASETS[cat.datasetKey] ? { name: DEMO_DATASETS[cat.datasetKey].name, content: DEMO_DATASETS[cat.datasetKey].content } : null);
                              handleSend(null, q, fileObj);
                            }}
                            className="w-full text-left py-1.5 px-2.5 rounded-lg text-xs transition-colors flex items-start justify-between group text-slate-600 dark:text-slate-300 hover:bg-blue-50 dark:hover:bg-blue-950/40 hover:text-blue-600 dark:hover:text-blue-400 cursor-pointer"
                          >
                            <span className="leading-relaxed pr-2">· {q}</span>
                            <ArrowRight className="w-3.5 h-3.5 text-slate-300 group-hover:text-blue-500 group-hover:translate-x-0.5 transition-all shrink-0 mt-0.5" />
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Form & ASTA-Style Dataset Attachment Pill */}
      <div className="relative mt-2 shrink-0 w-full flex flex-col items-center gap-2 mb-4 px-4">
        
        {/* ASTA Style Attachment Chip */}
        {attachedFile && (
          <div className={`self-start flex items-center gap-2 px-3 py-1.5 rounded-xl border text-[12px] font-semibold shadow-sm animate-in fade-in duration-150 ${
            dm ? 'bg-slate-800 border-slate-700 text-slate-200' : 'bg-slate-50 border-slate-200 text-slate-700'
          }`}>
            <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-500" />
            <span className="max-w-[240px] truncate">{attachedFile.name}</span>
            <button 
              onClick={() => setAttachedFile(null)} 
              className="ml-1 text-slate-400 hover:text-red-500 transition-colors cursor-pointer"
              title="Gỡ bỏ tập dữ liệu"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        <form onSubmit={handleSend} className="relative w-full max-w-4xl mx-auto">
          <input 
            ref={fileInputRef} 
            type="file" 
            accept=".csv,.tsv,.txt,.json,.xlsx,.xls" 
            className="hidden" 
            onChange={handleFileChange} 
          />

          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            title="Đính kèm tập dữ liệu nghiên cứu (Excel .xlsx, .xls, CSV, TSV)"
            className={`absolute left-3 top-1/2 -translate-y-1/2 p-2 rounded-xl transition-colors cursor-pointer ${
              attachedFile ? 'text-blue-500 bg-blue-50 dark:bg-blue-950/40' : dm ? 'text-slate-400 hover:text-slate-200 hover:bg-slate-700' : 'text-slate-400 hover:text-slate-600 hover:bg-slate-100'
            }`}
          >
            <Paperclip className="w-4 h-4" />
          </button>

          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={isEn ? "Ask a scientific question, test hypothesis, analyze trends, or request charts..." : "Đặt câu hỏi khoa học, phân tích xu hướng, kiểm định giả thuyết hoặc yêu cầu vẽ biểu đồ..."}
            className={`w-full pl-12 pr-32 py-3.5 border rounded-2xl text-[13.5px] font-medium focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 shadow-sm transition-all ${
              dm ? 'bg-slate-900 border-slate-700 text-white placeholder-slate-500' : 'bg-white border-slate-200 text-slate-900 placeholder-slate-400'
            }`}
          />

          <button
            type="submit"
            disabled={!input.trim() && !attachedFile}
            className="absolute right-2 top-1/2 -translate-y-1/2 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed text-white px-4 py-2 rounded-xl text-xs font-bold transition-transform active:scale-95 flex items-center gap-1.5 shadow-md cursor-pointer"
          >
            <span>{isEn ? 'Analyze' : 'Phân tích'}</span>
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>
      </div>
      </div>
    </div>
  );
}
