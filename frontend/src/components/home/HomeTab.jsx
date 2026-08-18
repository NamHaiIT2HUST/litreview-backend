import React, { useState } from 'react';
import { 
  Search, BrainCircuit, FileDown, ArrowRight, Settings, CheckCircle2, 
  Layers, ShieldCheck, Database, Cpu, Compass, BookOpen, ChevronRight,
  TrendingUp, Sparkles, Activity, FileText, Check, Zap, Eye
} from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';
import InteractiveHeroBackground from './InteractiveHeroBackground';

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
    <div className="space-y-16 pb-20 font-sans relative overflow-hidden">
      
      {/* 🚀 HERO SECTION WITH DYNAMIC VINDYNAMICS-STYLE BACKGROUND */}
      <section className="relative pt-12 pb-16 px-4 max-w-6xl mx-auto text-center space-y-8 min-h-[560px] flex flex-col justify-center items-center">
        
        {/* Interactive Neural Canvas Background */}
        <InteractiveHeroBackground darkMode={darkMode} />

        {/* Live System Badge with Ripple Effect */}
        <div className="relative inline-flex items-center gap-2.5 px-5 py-2 rounded-full text-xs font-display font-black bg-white/80 dark:bg-slate-900/90 text-blue-700 dark:text-sky-300 border border-blue-200/90 dark:border-blue-800 shadow-lg shadow-blue-500/10 backdrop-blur-md animate-in fade-in zoom-in duration-500 hover:scale-105 transition-transform cursor-default">
          <span className="relative flex h-2.5 w-2.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-blue-600"></span>
          </span>
          <span className="tracking-wider uppercase">LITREVIEW AGENT · NEXT-GEN LITERATURE WORKSPACE</span>
        </div>

        {/* Main Hero Headline */}
        <div className="space-y-4 max-w-4xl mx-auto">
          <h1 className="text-4xl sm:text-5xl md:text-6xl font-display font-black tracking-tight leading-[1.12] text-slate-900 dark:text-white">
            Tăng Tốc Tổng Quan Y Văn Với <br className="hidden sm:block" />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 via-indigo-600 to-sky-500 dark:from-blue-400 dark:via-indigo-300 dark:to-sky-300">
              Multi-Agent Intelligence
            </span>
          </h1>

          <p className="text-sm sm:text-base md:text-lg text-slate-600 dark:text-slate-300 max-w-2xl mx-auto font-normal leading-relaxed">
            Hệ thống hỗ trợ nghiên cứu khép kín: Tự động cố vấn phạm vi, thiết lập tiêu chí PRISMA, đối chiếu dữ liệu Scopus và tổng hợp báo cáo y văn học thuật chuẩn xác.
          </p>
        </div>

        {/* Floating Telemetry Micro-Badges */}
        <div className="hidden lg:flex items-center justify-center gap-3 pt-1">
          <span className="px-3 py-1 rounded-xl bg-slate-900/5 dark:bg-white/5 border border-slate-200 dark:border-slate-800 text-[11px] font-mono text-slate-600 dark:text-slate-400 flex items-center gap-1.5 backdrop-blur-sm shadow-sm">
            <Activity className="w-3.5 h-3.5 text-blue-500 animate-pulse" />
            <span>Agent Consensus: Synced</span>
          </span>
          <span className="px-3 py-1 rounded-xl bg-slate-900/5 dark:bg-white/5 border border-slate-200 dark:border-slate-800 text-[11px] font-mono text-slate-600 dark:text-slate-400 flex items-center gap-1.5 backdrop-blur-sm shadow-sm">
            <Check className="w-3.5 h-3.5 text-emerald-500" />
            <span>PRISMA 2020: Compliant</span>
          </span>
          <span className="px-3 py-1 rounded-xl bg-slate-900/5 dark:bg-white/5 border border-slate-200 dark:border-slate-800 text-[11px] font-mono text-slate-600 dark:text-slate-400 flex items-center gap-1.5 backdrop-blur-sm shadow-sm">
            <Zap className="w-3.5 h-3.5 text-amber-500" />
            <span>Flash Engine: 1.45s</span>
          </span>
        </div>

        {/* CTA Action Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-2 w-full max-w-md mx-auto">
          <button
            onClick={() => setActiveTab('setup')}
            className="w-full sm:w-auto px-8 py-4 bg-blue-600 hover:bg-blue-700 text-white rounded-2xl font-display font-black text-xs md:text-sm shadow-xl shadow-blue-600/30 transition-all hover:scale-[1.03] active:scale-95 flex items-center justify-center gap-2 group"
          >
            <span>Bắt đầu thiết lập đề tài</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </button>
          
          <button
            onClick={() => setActiveTab('search')}
            className={`w-full sm:w-auto px-7 py-4 rounded-2xl font-display font-bold text-xs md:text-sm transition-all border backdrop-blur-md ${
              darkMode 
                ? 'bg-slate-900/80 hover:bg-slate-800 text-slate-200 border-slate-700' 
                : 'bg-white/90 hover:bg-white text-slate-800 border-slate-200 shadow-md shadow-slate-200/50'
            } flex items-center justify-center gap-2`}
          >
            <Search className="w-4 h-4 text-blue-600" />
            <span>Khám phá dữ liệu bài báo</span>
          </button>
        </div>

        {/* 📊 LIVE METRICS TICKER */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-6 max-w-4xl mx-auto w-full">
          {stats.map((item, idx) => (
            <div 
              key={idx}
              className={`p-4 md:p-5 rounded-2xl border text-center transition-all backdrop-blur-md ${
                darkMode ? 'bg-slate-900/80 border-slate-800 hover:border-blue-500/50' : 'bg-white/90 border-slate-200 shadow-sm hover:border-blue-400'
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

      {/* 🔄 INTERACTIVE 4-STEP PIPELINE */}
      <section className="max-w-5xl mx-auto px-4 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3 pb-3 border-b border-slate-200 dark:border-slate-800">
          <div>
            <span className="text-xs font-display font-extrabold text-blue-600 dark:text-sky-400 uppercase tracking-widest block">
              QUY TRÌNH HỌC THUẬT TOÀN DIỆN
            </span>
            <h2 className="text-2xl md:text-3xl font-display font-black text-slate-900 dark:text-white tracking-tight mt-1">
              Luồng Nghiên Cứu 4 Giai Đoạn
            </h2>
          </div>
          <p className="text-xs text-slate-500 font-medium max-w-xs">
            Được thiết kế để tối ưu hóa từng bước từ ý tưởng ban đầu đến bài báo hoàn chỉnh.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {workflowSteps.map((step, idx) => {
            const Icon = step.icon;
            return (
              <div
                key={idx}
                onMouseEnter={() => setHoveredCard(idx)}
                onMouseLeave={() => setHoveredCard(null)}
                onClick={() => setActiveTab(step.tab)}
                className={`p-6 rounded-3xl border transition-all cursor-pointer flex flex-col justify-between space-y-5 group relative overflow-hidden ${
                  darkMode 
                    ? 'bg-slate-900 border-slate-800 hover:border-blue-500/60' 
                    : 'bg-white border-slate-200 hover:border-blue-400 hover:shadow-xl hover:shadow-blue-500/10'
                }`}
              >
                {/* Step Top Bar */}
                <div className="flex items-center justify-between">
                  <span className="text-xs font-display font-black text-blue-600 dark:text-sky-400 bg-blue-50 dark:bg-blue-950 px-2.5 py-1 rounded-xl border border-blue-100 dark:border-blue-900">
                    STEP {step.step}
                  </span>
                  <div className="w-10 h-10 rounded-2xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-600 dark:text-slate-300 group-hover:bg-blue-600 group-hover:text-white transition-colors shadow-sm">
                    <Icon className="w-5 h-5" />
                  </div>
                </div>

                {/* Content */}
                <div className="space-y-2">
                  <h3 className="font-display font-bold text-base text-slate-900 dark:text-white leading-snug group-hover:text-blue-600 dark:group-hover:text-sky-400 transition-colors">
                    {step.title}
                  </h3>
                  <p className="text-xs text-slate-500 leading-relaxed font-normal">
                    {step.desc}
                  </p>
                </div>

                {/* Bottom Action Link */}
                <div className="pt-2 flex items-center justify-between text-xs font-display font-extrabold text-blue-600 dark:text-sky-400 border-t border-slate-100 dark:border-slate-800/80">
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
          <span className="text-xs font-display font-extrabold text-blue-600 dark:text-sky-400 uppercase tracking-widest">
            KIẾN TRÚC ĐỘT PHÁ
          </span>
          <h2 className="text-2xl md:text-3xl font-display font-black text-slate-900 dark:text-white tracking-tight">
            Nền Tảng Tự Động Hóa Chuyên Sâu
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {coreCapabilities.map((cap, i) => {
            const Icon = cap.icon;
            return (
              <div 
                key={i} 
                className={`p-7 rounded-3xl border transition-all ${
                  darkMode ? 'bg-slate-900 border-slate-800 hover:border-blue-600/50' : 'bg-white border-slate-200/90 shadow-sm hover:border-blue-400 hover:shadow-lg'
                } space-y-4 transition-all`}
              >
                <div className="w-12 h-12 rounded-2xl bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-sky-400 flex items-center justify-center shadow-sm">
                  <Icon className="w-6 h-6" />
                </div>
                <h3 className="font-display font-bold text-base text-slate-900 dark:text-white">
                  {cap.title}
                </h3>
                <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed font-normal">
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
              Bắt đầu dự án tổng quan y văn của bạn
            </h3>
            <p className="text-xs md:text-sm text-blue-100 max-w-xl font-normal leading-relaxed">
              Khởi tạo cấu hình nghiên cứu và để các Agent chuyên trách đồng hành cùng bạn ở từng bước.
            </p>
          </div>

          <button
            onClick={() => setActiveTab('setup')}
            className="px-8 py-4 bg-white text-blue-700 hover:bg-blue-50 rounded-2xl font-display font-black text-xs md:text-sm shadow-xl transition-transform hover:scale-105 active:scale-95 shrink-0 z-10"
          >
            Vào Tab Cấu hình →
          </button>
        </div>
      </section>

    </div>
  );
}
