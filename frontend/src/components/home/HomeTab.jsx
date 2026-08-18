import React, { useState } from 'react';
import { 
  Search, BrainCircuit, FileDown, ArrowRight, Settings, CheckCircle2, 
  Layers, ShieldCheck, Database, Cpu, Compass, BookOpen, ChevronRight,
  TrendingUp, Sparkles, Activity, FileText
} from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';

export default function HomeTab({ setActiveTab, darkMode }) {
  const { t } = useLanguage();
  const [hoveredCard, setHoveredCard] = useState(null);

  const stats = [
    { label: 'Cơ sở dữ liệu học thuật', value: '50M+', desc: 'Google Scholar & Scopus' },
    { label: 'Thời gian phân tích AI', value: '< 1.5s', desc: 'Gemini 3.1 Flash-Lite Engine' },
    { label: 'Quy chuẩn y văn', value: 'PRISMA', desc: 'Tuân thủ tiêu chuẩn 2020' },
    { label: 'Quyền kiểm soát', value: '100% HITL', desc: 'Human-in-the-Loop Governance' },
  ];

  const workflowSteps = [
    {
      step: '01',
      title: 'Định hình Đề tài & Tiêu chí',
      desc: 'Cố vấn phạm vi câu hỏi nghiên cứu, tự động sinh tiêu chí chọn/loại và khung PICO chuẩn xác.',
      tab: 'setup',
      badge: 'Multi-Agent Setup',
      icon: Settings
    },
    {
      step: '02',
      title: 'Thu thập & Xác minh Nguồn',
      desc: 'Tra cứu đa nguồn, lọc trùng lặp tự động và xếp hạng bài báo theo uy tín trích dẫn.',
      tab: 'search',
      badge: 'Live Discovery',
      icon: Search
    },
    {
      step: '03',
      title: 'Sàng lọc PRISMA & Đối chiếu',
      desc: 'Phân tích toàn văn, đánh giá độ phù hợp và tạo sơ đồ luồng dữ liệu minh bạch.',
      tab: 'synthesis',
      badge: 'Evidence Matrix',
      icon: Layers
    },
    {
      step: '04',
      title: 'Tổng hợp & Xuất Báo cáo',
      desc: 'Trích xuất dữ liệu đa chiều, tạo báo cáo tổng quan y văn hoàn chỉnh chỉ với 1 click.',
      tab: 'export',
      badge: 'Academic Export',
      icon: FileDown
    }
  ];

  const coreCapabilities = [
    {
      icon: Cpu,
      title: 'Kiến Trúc Multi-Agent Swarm',
      desc: 'Phân rã bài toán nghiên cứu phức tạp cho nhiều tác nhân AI chuyên biệt (Scope Advisor, Criteria Generator, PICO Synthesizer) phối hợp nhịp nhàng.',
      color: 'blue'
    },
    {
      icon: ShieldCheck,
      title: 'Human-in-the-Loop (HITL) 3 Cổng Duyệt',
      desc: 'Không bao giờ để AI tự động một cách mất kiểm soát. Nhà nghiên cứu luôn giữ quyền quyết định cao nhất ở từng giai đoạn then chốt.',
      color: 'indigo'
    },
    {
      icon: Database,
      title: 'Closed-Domain RAG & Trích dẫn Thật',
      desc: 'Mọi luận điểm tổng hợp đều được neo trực tiếp vào văn bản gốc của các công trình học thuật đã xác minh, loại bỏ triệt để ảo giác thông tin.',
      color: 'sky'
    }
  ];

  return (
    <div className="space-y-16 pb-20 font-sans">
      
      {/* 🚀 HERO SECTION WITH DYNAMIC GRADIENT & DEPTH */}
      <section className="relative pt-8 pb-12 px-4 max-w-5xl mx-auto text-center space-y-6">
        
        {/* Subtle Ambient Background Light */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[300px] bg-blue-500/10 dark:bg-blue-600/15 blur-[100px] rounded-full pointer-events-none -z-10" />

        {/* Live System Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-display font-bold bg-blue-50 text-blue-700 dark:bg-blue-950/70 dark:text-sky-300 border border-blue-200/80 dark:border-blue-800 shadow-sm animate-in fade-in zoom-in duration-500">
          <span className="w-2 h-2 rounded-full bg-blue-600 animate-pulse" />
          <span>HỆ THỐNG TỔNG QUAN Y VĂN THÔNG MINH THẾ HỆ MỚI</span>
        </div>

        {/* Main Hero Headline */}
        <h1 className="text-4xl sm:text-5xl md:text-6xl font-display font-black tracking-tight leading-[1.15] text-slate-900 dark:text-white max-w-4xl mx-auto">
          Tăng Tốc Nghiên Cứu Với <span className="text-blue-600 dark:text-sky-400">Multi-Agent Intelligence</span>
        </h1>

        {/* Subtitle */}
        <p className="text-base sm:text-lg text-slate-600 dark:text-slate-300 max-w-2xl mx-auto font-normal leading-relaxed">
          Nền tảng hỗ trợ tổng quan tài liệu khoa học khép kín, tự động hóa từ khâu thiết lập đề tài, sàng lọc PRISMA đến trích xuất ma trận dữ liệu theo chuẩn quốc tế.
        </p>

        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
          <button
            onClick={() => setActiveTab('setup')}
            className="w-full sm:w-auto px-8 py-4 bg-blue-600 hover:bg-blue-700 text-white rounded-2xl font-display font-black text-sm shadow-xl shadow-blue-600/25 transition-all hover:scale-[1.03] active:scale-95 flex items-center justify-center gap-2 group"
          >
            <span>Bắt đầu thiết lập đề tài</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </button>
          
          <button
            onClick={() => setActiveTab('search')}
            className={`w-full sm:w-auto px-7 py-4 rounded-2xl font-display font-bold text-sm transition-all border ${
              darkMode 
                ? 'bg-slate-900 hover:bg-slate-800 text-slate-200 border-slate-700' 
                : 'bg-white hover:bg-slate-50 text-slate-700 border-slate-200 shadow-sm'
            } flex items-center justify-center gap-2`}
          >
            <Search className="w-4 h-4 text-blue-600" />
            <span>Khám phá dữ liệu bài báo</span>
          </button>
        </div>

        {/* 📊 LIVE METRICS TICKER */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-8 max-w-4xl mx-auto">
          {stats.map((item, idx) => (
            <div 
              key={idx}
              className={`p-4 rounded-2xl border text-center transition-all ${
                darkMode ? 'bg-slate-900/80 border-slate-800' : 'bg-white border-slate-200/90 shadow-sm'
              }`}
            >
              <div className="text-2xl md:text-3xl font-display font-black text-blue-600 dark:text-sky-400">
                {item.value}
              </div>
              <div className="text-xs font-display font-bold text-slate-800 dark:text-slate-200 mt-1">
                {item.label}
              </div>
              <div className="text-[11px] text-slate-500 font-medium mt-0.5">
                {item.desc}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 🔄 INTERACTIVE 4-STEP PIPELINE (HOẠT ẢNH TIẾN TRÌNH) */}
      <section className="max-w-5xl mx-auto px-4 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3 pb-2 border-b border-slate-200 dark:border-slate-800">
          <div>
            <span className="text-xs font-display font-bold text-blue-600 dark:text-sky-400 uppercase tracking-widest block">
              QUY TRÌNH KHOA HỌC CHUẨN MỰC
            </span>
            <h2 className="text-2xl md:text-3xl font-display font-black text-slate-900 dark:text-white tracking-tight mt-1">
              Luồng Làm Việc 4 Giai Đoạn
            </h2>
          </div>
          <p className="text-xs text-slate-500 font-medium max-w-xs">
            Hỗ trợ toàn diện từ giai đoạn lên ý tưởng đến khi hoàn thiện bài báo cáo.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {workflowSteps.map((step, idx) => {
            const Icon = step.icon;
            const isHovered = hoveredCard === idx;
            return (
              <div
                key={idx}
                onMouseEnter={() => setHoveredCard(idx)}
                onMouseLeave={() => setHoveredCard(null)}
                onClick={() => setActiveTab(step.tab)}
                className={`p-6 rounded-3xl border transition-all cursor-pointer flex flex-col justify-between space-y-5 group relative overflow-hidden ${
                  darkMode 
                    ? 'bg-slate-900 border-slate-800 hover:border-blue-500/60 hover:bg-slate-850' 
                    : 'bg-white border-slate-200 hover:border-blue-400 hover:shadow-lg hover:shadow-blue-500/5'
                }`}
              >
                {/* Step Top Bar */}
                <div className="flex items-center justify-between">
                  <span className="text-xs font-display font-black text-blue-600 dark:text-sky-400 bg-blue-50 dark:bg-blue-950 px-2.5 py-1 rounded-lg border border-blue-100 dark:border-blue-900">
                    STEP {step.step}
                  </span>
                  <div className="w-9 h-9 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-600 dark:text-slate-300 group-hover:bg-blue-600 group-hover:text-white transition-colors shadow-sm">
                    <Icon className="w-4 h-4" />
                  </div>
                </div>

                {/* Content */}
                <div className="space-y-2">
                  <h3 className="font-display font-bold text-base text-slate-900 dark:text-white leading-snug group-hover:text-blue-600 dark:group-hover:text-sky-400 transition-colors">
                    {step.title}
                  </h3>
                  <p className="text-xs text-slate-500 leading-relaxed">
                    {step.desc}
                  </p>
                </div>

                {/* Bottom Action Link */}
                <div className="pt-2 flex items-center justify-between text-xs font-display font-bold text-blue-600 dark:text-sky-400 border-t border-slate-100 dark:border-slate-800/80">
                  <span>Trải nghiệm ngay</span>
                  <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1.5 transition-transform" />
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* 🛡️ CORE CAPABILITIES & ARCHITECTURE */}
      <section className="max-w-5xl mx-auto px-4 space-y-6">
        <div className="text-center max-w-2xl mx-auto space-y-2">
          <span className="text-xs font-display font-bold text-blue-600 dark:text-sky-400 uppercase tracking-widest">
            TẠI SAO LỰA CHỌN LITREVIEW PRO
          </span>
          <h2 className="text-2xl md:text-3xl font-display font-black text-slate-900 dark:text-white tracking-tight">
            Nền Tảng Đột Phá Cho Nghiên Cứu Viên
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {coreCapabilities.map((cap, i) => {
            const Icon = cap.icon;
            return (
              <div 
                key={i} 
                className={`p-7 rounded-3xl border transition-all ${
                  darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200/90 shadow-sm'
                } space-y-4 hover:border-blue-300 dark:hover:border-blue-700 transition-colors`}
              >
                <div className="w-12 h-12 rounded-2xl bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-sky-400 flex items-center justify-center shadow-sm">
                  <Icon className="w-6 h-6" />
                </div>
                <h3 className="font-display font-bold text-base text-slate-900 dark:text-white">
                  {cap.title}
                </h3>
                <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                  {cap.desc}
                </p>
              </div>
            );
          })}
        </div>
      </section>

      {/* 🚀 BOTTOM CALL TO ACTION BANNER */}
      <section className="max-w-5xl mx-auto px-4">
        <div className="p-8 md:p-12 rounded-3xl bg-gradient-to-r from-blue-600 via-blue-700 to-indigo-800 text-white shadow-2xl relative overflow-hidden flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="space-y-2 text-center md:text-left z-10">
            <h3 className="text-2xl md:text-3xl font-display font-black tracking-tight">
              Sẵn sàng bắt đầu dự án nghiên cứu của bạn?
            </h3>
            <p className="text-xs md:text-sm text-blue-100 max-w-xl font-normal leading-relaxed">
              Thiết lập đề tài ngay bây giờ để được Agent Cố vấn phạm vi và tự động sinh khung tiêu chí chuẩn PRISMA trong vài giây.
            </p>
          </div>

          <button
            onClick={() => setActiveTab('setup')}
            className="px-8 py-4 bg-white text-blue-700 hover:bg-blue-50 rounded-2xl font-display font-black text-xs md:text-sm shadow-lg transition-transform hover:scale-105 active:scale-95 shrink-0 z-10"
          >
            Vào Tab Cấu hình →
          </button>
        </div>
      </section>

    </div>
  );
}
