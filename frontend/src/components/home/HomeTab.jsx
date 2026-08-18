import React, { useState } from 'react';
import { 
  Search, BrainCircuit, FileDown, ArrowRight, Settings, CheckCircle2, 
  Layers, ShieldCheck, Database, Cpu, Compass, BookOpen, ChevronRight,
  TrendingUp, Activity, FileText, Check, Zap, Play, ExternalLink
} from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';

export default function HomeTab({ setActiveTab, darkMode }) {
  const { t } = useLanguage();
  const [hoveredCard, setHoveredCard] = useState(null);

  const stats = [
    { label: 'Cơ sở dữ liệu học thuật', value: '50M+', desc: 'Google Scholar & Scopus Verified' },
    { label: 'Tốc độ phản hồi AI', value: '< 1.5s', desc: 'Gemini 3.1 Flash-Lite Engine' },
    { label: 'Quy chuẩn y văn', value: 'PRISMA', desc: 'Tiêu chuẩn quốc tế 2020' },
    { label: 'Quyền kiểm soát', value: '100% HITL', desc: 'Human-in-the-Loop 3 Cổng Duyệt' },
  ];

  const workflowSteps = [
    {
      step: '01',
      title: 'Định hình Đề tài & Tiêu chí',
      desc: 'Cố vấn phạm vi câu hỏi nghiên cứu, tự động sinh tiêu chí chọn/loại và khung PICO chuẩn xác.',
      tab: 'setup',
      icon: Settings
    },
    {
      step: '02',
      title: 'Thu thập & Xác minh Nguồn',
      desc: 'Tra cứu đa nguồn, lọc trùng lặp tự động và xếp hạng bài báo theo uy tín trích dẫn.',
      tab: 'search',
      icon: Search
    },
    {
      step: '03',
      title: 'Sàng lọc PRISMA & Đối chiếu',
      desc: 'Phân tích toàn văn, đánh giá độ phù hợp và tạo sơ đồ luồng dữ liệu minh bạch.',
      tab: 'synthesis',
      icon: Layers
    },
    {
      step: '04',
      title: 'Tổng hợp & Xuất Báo cáo',
      desc: 'Trích xuất dữ liệu đa chiều, tạo báo cáo tổng quan y văn hoàn chỉnh chỉ với 1 click.',
      tab: 'export',
      icon: FileDown
    }
  ];

  return (
    <div className="space-y-12 pb-24 font-sans text-slate-900 dark:text-white">
      
      {/* 🎬 1. FULL-BLEED CINEMATIC HERO VIDEO — VinDynamics Style */}
      <section className="relative w-full rounded-3xl overflow-hidden shadow-2xl border border-slate-800 bg-black min-h-[560px] md:min-h-[640px] flex items-center justify-center">
        
        {/* VinDynamics Robot Background Video */}
        <video 
          className="absolute inset-0 w-full h-full object-cover opacity-65 scale-105 filter brightness-90"
          src="https://vindynamics.net/api/v2/file/view?fileId=mwp-prod%2Fpublic%2F2026%2F08%2F07%2F019fdbf24ee77a8791cceab252e3b198_D050F5FCA2A8E3427EE3B8AC81AEFD3F.mp4&site=000006"
          poster="https://vindynamics.net/api/v2/file/view?fileId=mwp-prod%2Fpublic%2F2026%2F08%2F07%2F019fdc00d5af7aa5a5f001bc773ee36d_2C3F027FB9D6AACEF873C026AA2CCF98.png&site=000006"
          autoPlay 
          muted 
          loop 
          playsInline 
        />

        {/* Ambient Dark Overlay Gradients */}
        <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/40 to-slate-950/70" />
        <div className="absolute inset-0 bg-radial from-transparent via-black/20 to-slate-950/80" />

        {/* Hero Content Shell */}
        <div className="relative z-10 max-w-4xl mx-auto px-6 py-16 text-center space-y-8">
          
          <div className="space-y-4">
            <span className="font-display font-bold text-xs uppercase tracking-[0.25em] text-blue-400 block animate-in fade-in slide-in-from-top-3 duration-500">
              ACADEMIC SYSTEMATIC REVIEW PLATFORM
            </span>

            <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-display font-black tracking-tight leading-[1.08] text-white drop-shadow-lg">
              Tự Động Hóa Y Văn<br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-sky-300 to-white">
                Chính Xác Trong Từng Luận Điểm
              </span>
            </h1>

            <p className="text-base sm:text-lg text-slate-300 max-w-2xl mx-auto font-normal leading-relaxed drop-shadow-md">
              Hệ thống tổng quan tài liệu khoa học thế hệ mới với Multi-Agent Swarm, tự động cố vấn phạm vi, thiết lập tiêu chí PRISMA và đối chiếu bài báo học thuật theo thời gian thực.
            </p>
          </div>

          {/* Action CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
            <button
              onClick={() => setActiveTab('setup')}
              className="w-full sm:w-auto px-9 py-4 bg-blue-600 hover:bg-blue-500 text-white rounded-2xl font-display font-black text-xs md:text-sm tracking-wider uppercase shadow-xl shadow-blue-600/40 transition-all hover:scale-105 active:scale-95 flex items-center justify-center gap-3"
            >
              <span>THIẾT LẬP ĐỀ TÀI NGHIÊN CỨU</span>
              <ArrowRight className="w-4 h-4" />
            </button>
            
            <button
              onClick={() => setActiveTab('search')}
              className="w-full sm:w-auto px-8 py-4 rounded-2xl font-display font-bold text-xs md:text-sm tracking-wider uppercase transition-all bg-white/10 hover:bg-white/20 text-white border border-white/20 backdrop-blur-md flex items-center justify-center gap-2.5 hover:scale-105 active:scale-95"
            >
              <Search className="w-4 h-4 text-sky-400" />
              <span>KHÁM PHÁ NGUỒN BÀI BÁO</span>
            </button>
          </div>

          {/* Telemetry Pills */}
          <div className="flex flex-wrap items-center justify-center gap-3 pt-6 text-[11px] font-mono text-slate-400">
            <span className="px-3.5 py-1.5 rounded-full bg-slate-900/80 border border-slate-700/80 flex items-center gap-2 backdrop-blur-md">
              <span className="w-2 h-2 rounded-full bg-blue-400 animate-ping" />
              <span>Closed-Domain RAG: Active</span>
            </span>
            <span className="px-3.5 py-1.5 rounded-full bg-slate-900/80 border border-slate-700/80 flex items-center gap-2 backdrop-blur-md">
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              <span>PRISMA 2020: Verified</span>
            </span>
            <span className="px-3.5 py-1.5 rounded-full bg-slate-900/80 border border-slate-700/80 flex items-center gap-2 backdrop-blur-md">
              <Zap className="w-3.5 h-3.5 text-amber-400" />
              <span>Gemini 3.1 Flash-Lite Engine</span>
            </span>
          </div>
        </div>
      </section>

      {/* 📊 2. METRICS STRIP */}
      <section className="max-w-6xl mx-auto px-2">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {stats.map((item, idx) => (
            <div 
              key={idx}
              className={`p-6 rounded-3xl border text-center transition-all ${
                darkMode 
                  ? 'bg-slate-900 border-slate-800 hover:border-blue-500/50' 
                  : 'bg-white border-slate-200 shadow-sm hover:border-blue-400'
              }`}
            >
              <div className="text-3xl md:text-4xl font-display font-black text-blue-600 dark:text-sky-400">
                {item.value}
              </div>
              <div className="text-xs font-display font-extrabold text-slate-900 dark:text-slate-100 mt-2 tracking-wide">
                {item.label}
              </div>
              <div className="text-[11px] text-slate-500 font-medium mt-1">
                {item.desc}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 🎬 3. BANNER VIDEO SECTION A: DATA & LITERATURE FACTORY */}
      <section className="max-w-6xl mx-auto rounded-3xl overflow-hidden shadow-xl border border-slate-800 bg-black relative min-h-[380px] md:min-h-[440px] flex items-center">
        {/* Video Background */}
        <video 
          className="absolute inset-0 w-full h-full object-cover opacity-60 filter brightness-90"
          src="https://vindynamics.net/api/v2/file/view?fileId=mwp-prod%2Fpublic%2F2026%2F08%2F07%2F019fdc0608017e4baa6b9ef096cb9081_69773710B111EC68F0CB2CA13B136F1C.mp4&site=000006"
          poster="https://vindynamics.net/api/v2/file/view?fileId=mwp-prod%2Fpublic%2F2026%2F08%2F04%2F019fcd162fe67cd39e62bd2829322100_41FB427A939D56ED07A0894CFF198CBF.jpg&site=000006"
          autoPlay 
          muted 
          loop 
          playsInline 
        />
        <div className="absolute inset-0 bg-gradient-to-r from-slate-950 via-slate-950/70 to-transparent" />

        {/* Content */}
        <div className="relative z-10 max-w-xl p-8 md:p-14 space-y-4 text-white">
          <span className="font-display font-bold text-xs uppercase tracking-[0.2em] text-blue-400 block">
            &gt; LITERATURE DATA FACTORY
          </span>
          <h2 className="text-3xl md:text-4xl font-display font-black tracking-tight leading-tight">
            Khai thác kho tàng tri thức khoa học với dữ liệu xác minh chất lượng cao
          </h2>
          <p className="text-xs md:text-sm text-slate-300 font-normal leading-relaxed">
            Hệ thống tự động tra cứu, trích lọc dữ liệu và đối chiếu chéo với cơ sở dữ liệu Scopus nhằm đảm bảo tính chính xác tuyệt đối cho bài tổng quan y văn.
          </p>
          <div className="pt-2">
            <button
              onClick={() => setActiveTab('search')}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-display font-bold text-xs uppercase tracking-wider transition-all hover:scale-105 active:scale-95 flex items-center gap-2 shadow-lg"
            >
              <span>TRUY CẬP TÌM KIẾM NGAY</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </section>

      {/* 🔄 4. 4-STEP PIPELINE CARDS */}
      <section className="max-w-6xl mx-auto space-y-6">
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
            Hỗ trợ toàn diện từ khâu lên ý tưởng, sàng lọc đến khi hoàn thiện bài báo cáo.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          {workflowSteps.map((step, idx) => {
            const Icon = step.icon;
            return (
              <div
                key={idx}
                onClick={() => setActiveTab(step.tab)}
                className={`p-7 rounded-3xl border transition-all cursor-pointer flex flex-col justify-between space-y-6 group relative overflow-hidden ${
                  darkMode 
                    ? 'bg-slate-900 border-slate-800 hover:border-blue-500 hover:bg-slate-850 shadow-md' 
                    : 'bg-white border-slate-200 hover:border-blue-400 hover:shadow-xl hover:shadow-blue-500/10'
                }`}
              >
                {/* Step Top Bar */}
                <div className="flex items-center justify-between">
                  <span className="text-xs font-display font-black text-blue-600 dark:text-sky-400 bg-blue-50 dark:bg-blue-950/80 px-3 py-1 rounded-xl border border-blue-100 dark:border-blue-900">
                    STEP {step.step}
                  </span>
                  <div className="w-10 h-10 rounded-2xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-700 dark:text-slate-200 group-hover:bg-blue-600 group-hover:text-white transition-colors shadow-sm">
                    <Icon className="w-5 h-5" />
                  </div>
                </div>

                {/* Content */}
                <div className="space-y-2">
                  <h3 className="font-display font-black text-base text-slate-900 dark:text-white leading-snug group-hover:text-blue-600 dark:group-hover:text-sky-400 transition-colors">
                    {step.title}
                  </h3>
                  <p className="text-xs text-slate-500 leading-relaxed font-normal">
                    {step.desc}
                  </p>
                </div>

                {/* Bottom Action Link */}
                <div className="pt-2 flex items-center justify-between text-xs font-display font-bold text-blue-600 dark:text-sky-400 border-t border-slate-100 dark:border-slate-800">
                  <span>Trải nghiệm ngay</span>
                  <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1.5 transition-transform" />
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* 🎬 5. BANNER VIDEO SECTION B: MULTI-AGENT SWARM */}
      <section className="max-w-6xl mx-auto rounded-3xl overflow-hidden shadow-xl border border-slate-800 bg-black relative min-h-[380px] md:min-h-[440px] flex items-center justify-end text-right">
        {/* Video Background */}
        <video 
          className="absolute inset-0 w-full h-full object-cover opacity-60 filter brightness-90"
          src="https://vindynamics.net/api/v2/file/view?fileId=mwp-prod%2Fpublic%2F2026%2F08%2F07%2F019fdc0511537e3da40b09b6d6a2cc89_F5B4B12B36E58B58BEBA71D555C9A57B.mp4&site=000006"
          poster="https://vindynamics.net/api/v2/file/view?fileId=mwp-prod%2Fpublic%2F2026%2F08%2F04%2F019fcd16317a7d69b1ebea86d928fd2a_0F2C020B2D6A492E341D3A876CFD5ED5.jpg&site=000006"
          autoPlay 
          muted 
          loop 
          playsInline 
        />
        <div className="absolute inset-0 bg-gradient-to-l from-slate-950 via-slate-950/70 to-transparent" />

        {/* Content */}
        <div className="relative z-10 max-w-xl p-8 md:p-14 space-y-4 text-white">
          <span className="font-display font-bold text-xs uppercase tracking-[0.2em] text-blue-400 block">
            &gt; MULTI-AGENT SWARM GOVERNANCE
          </span>
          <h2 className="text-3xl md:text-4xl font-display font-black tracking-tight leading-tight">
            Đưa AI chuyên sâu vào quy trình tổng quan y văn thực tế
          </h2>
          <p className="text-xs md:text-sm text-slate-300 font-normal leading-relaxed">
            Phân tách nhiệm vụ độc lập cho từng tác nhân chuyên trách: Cố vấn phạm vi, Sinh tiêu chí PRISMA, Xếp hạng uy tín nguồn bài báo, và Trích xuất ma trận bằng chứng.
          </p>
          <div className="pt-2 flex justify-end">
            <button
              onClick={() => setActiveTab('setup')}
              className="px-6 py-3 bg-white text-slate-950 hover:bg-slate-100 rounded-xl font-display font-bold text-xs uppercase tracking-wider transition-all hover:scale-105 active:scale-95 flex items-center gap-2 shadow-lg"
            >
              <span>BẮT ĐẦU CẤU HÌNH NGAY</span>
              <ArrowRight className="w-4 h-4 text-blue-600" />
            </button>
          </div>
        </div>
      </section>

    </div>
  );
}
