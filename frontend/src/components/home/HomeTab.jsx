import React from 'react';
import { 
  Search, FileDown, ArrowRight, Settings, 
  Layers, ShieldCheck, Database, Check, CheckCheck
} from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';

export default function HomeTab({ setActiveTab, darkMode }) {
  const { t } = useLanguage();

  const workflowSteps = [
    {
      step: '01',
      title: 'Định hình Đề tài & Tiêu chí',
      desc: 'Cố vấn phạm vi câu hỏi nghiên cứu, tự động gợi ý tiêu chí chọn/loại (Inclusion/Exclusion) chuẩn PRISMA.',
      tab: 'setup',
      icon: Settings
    },
    {
      step: '02',
      title: 'Thu thập & Xác minh Nguồn',
      desc: 'Tra cứu đa nguồn học thuật, lọc trùng lặp tự động và xếp hạng bài báo theo mức độ uy tín trích dẫn.',
      tab: 'search',
      icon: Search
    },
    {
      step: '03',
      title: 'Sàng lọc PRISMA & Đối chiếu',
      desc: 'Phân tích toàn văn, đánh giá độ phù hợp và dựng ma trận tổng hợp so sánh phương pháp.',
      tab: 'synthesis',
      icon: Layers
    },
    {
      step: '04',
      title: 'Phát hiện Khoảng trống & Xuất Báo cáo',
      desc: 'Phát hiện Research Gap, tổng hợp dữ liệu ban đầu và xuất bản dự thảo Literature Review hoàn chỉnh.',
      tab: 'export',
      icon: FileDown
    }
  ];

  return (
    <div className="space-y-16 pb-28 font-sans text-slate-900 dark:text-white">
      
      {/* 🎬 1. HERO FULL-BLEED STAGE — VinDynamics Style with Live Dynamic Academic Background */}
      <section className="relative w-full rounded-3xl overflow-hidden shadow-2xl border border-slate-800 bg-slate-950 min-h-[580px] md:min-h-[640px] flex items-center justify-center group">
        
        {/* Full-bleed Dynamic Academic Knowledge Graph Background with Continuous Cinematic Motion */}
        <div className="absolute inset-0 overflow-hidden">
          <img 
            src="/assets/academic_knowledge_graph.jpg"
            alt="Academic Literature Knowledge Graph"
            className="w-full h-full object-cover opacity-50 filter brightness-90 animate-ken-burns scale-110"
          />
        </div>

        {/* Ambient Dark Gradient Overlays (VinDynamics Stage Dim & Shade) */}
        <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/50 to-slate-950/75 pointer-events-none" />
        <div className="absolute inset-0 bg-radial from-transparent via-black/20 to-slate-950/85 pointer-events-none" />

        {/* Hero Content Shell Overlaid on Top */}
        <div className="relative z-10 max-w-4xl mx-auto px-6 py-16 text-center space-y-8">
          
          <div className="space-y-4">
            <span className="font-display font-bold text-xs uppercase tracking-[0.25em] text-blue-400 block animate-in fade-in slide-in-from-top-3 duration-500">
              ACADEMIC SYSTEMATIC REVIEW PLATFORM
            </span>

            <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-display font-black tracking-tight leading-[1.08] text-white drop-shadow-2xl">
              Tự Động Hóa Tổng Quan Y Văn<br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-sky-300 to-white">
                Chuẩn Xác & Khép Kín Trong Từng Luận Điểm
              </span>
            </h1>

            <p className="text-sm sm:text-base md:text-lg text-slate-300 max-w-2xl mx-auto font-normal leading-relaxed drop-shadow-md">
              Hỗ trợ nghiên cứu viên và sinh viên giải phóng hàng tuần đọc tài liệu thủ công, tự động hóa từ khâu tìm kiếm, sàng lọc PRISMA, phát hiện khoảng trống nghiên cứu đến dựng bảng so sánh phương pháp.
            </p>
          </div>

          {/* Action CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-2">
            <button
              onClick={() => setActiveTab('setup')}
              className="w-full sm:w-auto px-9 py-4 bg-blue-600 hover:bg-blue-500 text-white rounded-2xl font-display font-black text-xs md:text-sm tracking-wider uppercase shadow-xl shadow-blue-600/40 transition-all hover:scale-105 active:scale-95 flex items-center justify-center gap-3"
            >
              <span>BẮT ĐẦU CẤU HÌNH ĐỀ TÀI</span>
              <ArrowRight className="w-4 h-4" />
            </button>
            
            <button
              onClick={() => setActiveTab('search')}
              className="w-full sm:w-auto px-8 py-4 rounded-2xl font-display font-bold text-xs md:text-sm tracking-wider uppercase transition-all bg-white/10 hover:bg-white/20 text-white border border-white/20 backdrop-blur-md flex items-center justify-center gap-2.5 hover:scale-105 active:scale-95 shadow-md"
            >
              <Search className="w-4 h-4 text-sky-400" />
              <span>KHÁM PHÁ NGUỒN BÀI BÁO</span>
            </button>
          </div>

          {/* Trust Guarantees */}
          <div className="flex flex-wrap items-center justify-center gap-3 pt-4 text-[11px] font-mono text-slate-400">
            <span className="px-3.5 py-1.5 rounded-full bg-slate-900/80 border border-slate-700/80 flex items-center gap-2 backdrop-blur-md">
              <Check className="w-3.5 h-3.5 text-blue-400" />
              <span>100% Grounded trên bài báo thật</span>
            </span>
            <span className="px-3.5 py-1.5 rounded-full bg-slate-900/80 border border-slate-700/80 flex items-center gap-2 backdrop-blur-md">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>Human-in-the-Loop Governance</span>
            </span>
            <span className="px-3.5 py-1.5 rounded-full bg-slate-900/80 border border-slate-700/80 flex items-center gap-2 backdrop-blur-md">
              <CheckCheck className="w-3.5 h-3.5 text-amber-400" />
              <span>Chuẩn PRISMA 2020</span>
            </span>
          </div>
        </div>
      </section>

      {/* 📌 2. BỘ 3 TRỤ CỘT NGUYÊN TẮC: THỰC TRẠNG — VẤN ĐỀ — RÀNG BUỘC CHẶT CHẼ */}
      <section className="max-w-6xl mx-auto px-2 space-y-6">
        <div className="text-center max-w-2xl mx-auto space-y-2">
          <span className="text-xs font-display font-extrabold text-blue-600 dark:text-sky-400 uppercase tracking-widest">
            BÀI TOÁN & GIẢI PHÁP THỰC TIỄN
          </span>
          <h2 className="text-2xl md:text-3xl font-display font-black tracking-tight">
            Khung Giải Pháp Hỗ Trợ Nghiên Cứu
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          {/* Card 1: Thực Trạng */}
          <div className={`p-8 rounded-3xl border transition-all flex flex-col justify-between space-y-5 hover:border-amber-400/50 hover:shadow-lg ${
            darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200 shadow-sm'
          }`}>
            <div className="space-y-4">
              <div className="w-12 h-12 rounded-2xl bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 flex items-center justify-center font-black text-xl shadow-sm">
                📍
              </div>
              <h3 className="font-display font-black text-lg text-slate-900 dark:text-white">
                Thực Trạng Nghiên Cứu
              </h3>
              <p className="text-xs md:text-sm text-slate-600 dark:text-slate-400 leading-relaxed font-normal">
                Nghiên cứu viên và sinh viên nghiên cứu tại các trường đại học thường tốn <strong>nhiều tuần lễ</strong> chỉ để làm tổng quan tài liệu (literature review) và bước đầu xử lý dữ liệu. Các thao tác tìm kiếm, lọc bài thủ công lặp đi lặp lại rất dễ dẫn đến <strong>bỏ sót các nguồn trích dẫn cốt lõi</strong>.
              </p>
            </div>
            <div className="pt-3 border-t border-slate-100 dark:border-slate-800 text-[11px] font-bold text-amber-600 dark:text-amber-400">
              Thách thức: Tốn thời gian & rủi ro thiếu sót tài liệu
            </div>
          </div>

          {/* Card 2: Mục Tiêu & Vấn Đề */}
          <div className={`p-8 rounded-3xl border-2 transition-all flex flex-col justify-between space-y-5 border-blue-500/50 hover:border-blue-400 hover:shadow-xl ${
            darkMode ? 'bg-slate-900/90' : 'bg-blue-50/30 shadow-md'
          }`}>
            <div className="space-y-4">
              <div className="w-12 h-12 rounded-2xl bg-blue-600 text-white flex items-center justify-center font-black text-xl shadow-md shadow-blue-500/20">
                🎯
              </div>
              <h3 className="font-display font-black text-lg text-blue-900 dark:text-blue-200">
                Mục Tiêu & Giải Pháp AI
              </h3>
              <p className="text-xs md:text-sm text-slate-700 dark:text-slate-300 leading-relaxed font-normal">
                Xây dựng trợ lý AI hỗ trợ toàn trình: <strong>Tìm kiếm, sàng lọc PRISMA, tóm tắt, tổng hợp chủ đề, phát hiện khoảng trống nghiên cứu (Gap Discovery), dựng bảng so sánh</strong> và bước đầu phân tích dữ liệu.
              </p>
              <div className="p-3 bg-white dark:bg-slate-800 rounded-xl border border-blue-200 dark:border-blue-800/80 text-xs font-bold text-blue-700 dark:text-sky-300 space-y-1 shadow-sm">
                <div>⚡ Giảm ≥50% thời gian ra bản dự thảo đầu tiên</div>
                <div>🎯 Đảm bảo ≥80% độ chính xác thông tin</div>
              </div>
            </div>
            <div className="pt-3 border-t border-blue-200/60 dark:border-slate-800 text-[11px] font-bold text-blue-600 dark:text-sky-400">
              KPI: Tốc độ vượt trội & Độ chuẩn xác cao
            </div>
          </div>

          {/* Card 3: Ràng Buộc & Cam Kết */}
          <div className={`p-8 rounded-3xl border transition-all flex flex-col justify-between space-y-5 hover:border-emerald-400/50 hover:shadow-lg ${
            darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200 shadow-sm'
          }`}>
            <div className="space-y-4">
              <div className="w-12 h-12 rounded-2xl bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 flex items-center justify-center font-black text-xl shadow-sm">
                🔒
              </div>
              <h3 className="font-display font-black text-lg text-slate-900 dark:text-white">
                Ràng Buộc & Bảo Chứng Học Thuật
              </h3>
              <ul className="text-xs text-slate-600 dark:text-slate-400 space-y-2 leading-relaxed">
                <li className="flex items-start gap-2">
                  <span className="text-emerald-600 font-bold">✓</span>
                  <span><strong>Chống bịa nguồn:</strong> 100% luận điểm phải neo trên bài báo thật có DOI trích dẫn.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-emerald-600 font-bold">✓</span>
                  <span><strong>Human-in-the-Loop (HITL):</strong> Nghiên cứu viên rà soát, duyệt và chịu trách nhiệm nội dung cuối.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-emerald-600 font-bold">✓</span>
                  <span><strong>Minh bạch & Cảnh báo:</strong> Cảnh báo giới hạn khi thiếu dữ liệu và tối ưu chi phí xử lý văn bản dài.</span>
                </li>
              </ul>
            </div>
            <div className="pt-3 border-t border-slate-100 dark:border-slate-800 text-[11px] font-bold text-emerald-600 dark:text-emerald-400">
              Nguyên tắc: Trung thực học thuật & Con người làm chủ
            </div>
          </div>

        </div>
      </section>

      {/* 🎬 3. BANNER SECTION A: DỰNG BẢNG SO SÁNH & QUÉT MA TRẬN DỮ LIỆU — Full-Bleed Dynamic Backdrop */}
      <section className="max-w-6xl mx-auto rounded-3xl overflow-hidden shadow-2xl border border-slate-800 bg-slate-950 relative min-h-[440px] md:min-h-[480px] flex items-center group">
        
        {/* Full-bleed Dynamic Matrix Background with Continuous Cinematic Motion */}
        <div className="absolute inset-0 overflow-hidden">
          <img 
            src="/assets/literature_synthesis_matrix.jpg"
            alt="AI Literature Synthesis and Comparison Matrix"
            className="w-full h-full object-cover opacity-55 filter brightness-90 animate-ken-burns scale-110"
          />
        </div>

        {/* Gradient Overlay for Text Readability */}
        <div className="absolute inset-0 bg-gradient-to-r from-slate-950 via-slate-950/80 to-transparent" />

        {/* Content */}
        <div className="relative z-10 max-w-xl p-8 md:p-14 space-y-4 text-white">
          <span className="font-display font-bold text-xs uppercase tracking-[0.2em] text-blue-400 block">
            &gt; COMPARISON MATRIX & GAP DISCOVERY
          </span>
          <h2 className="text-3xl md:text-4xl font-display font-black tracking-tight leading-tight">
            Dựng Bảng So Sánh Phương Pháp & Phát Hiện Khoảng Trống Nghiên Cứu
          </h2>
          <p className="text-xs md:text-sm text-slate-300 font-normal leading-relaxed">
            Hệ thống tự động phân tích ma trận dữ liệu: So sánh thuật toán, tập dữ liệu thực nghiệm, kết quả đánh giá giữa các công trình, và chỉ ra những điểm nghẽn mà các nghiên cứu trước chưa giải quyết.
          </p>
          <div className="pt-2">
            <button
              onClick={() => setActiveTab('synthesis')}
              className="px-7 py-3.5 bg-blue-600 hover:bg-blue-500 text-white rounded-2xl font-display font-bold text-xs uppercase tracking-wider transition-all hover:scale-105 active:scale-95 flex items-center gap-2 shadow-lg shadow-blue-600/30"
            >
              <span>XEM MA TRẬN TỔNG HỢP</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </section>

      {/* 🔄 4. 4-STEP PIPELINE CARDS */}
      <section className="max-w-6xl mx-auto space-y-6 px-2">
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

      {/* 🎬 5. BANNER SECTION B: HUMAN-IN-THE-LOOP & CITATION VERIFICATION — Full-Bleed Dynamic Backdrop */}
      <section className="max-w-6xl mx-auto rounded-3xl overflow-hidden shadow-2xl border border-slate-800 bg-slate-950 relative min-h-[440px] md:min-h-[480px] flex items-center justify-end text-right group">
        
        {/* Full-bleed Dynamic Workstation Background with Continuous Cinematic Motion */}
        <div className="absolute inset-0 overflow-hidden">
          <img 
            src="/assets/hitl_research_governance.jpg"
            alt="Human-in-the-Loop Researcher Verification"
            className="w-full h-full object-cover opacity-55 filter brightness-90 animate-ken-burns scale-110"
          />
        </div>

        {/* Gradient Overlay for Text Readability */}
        <div className="absolute inset-0 bg-gradient-to-l from-slate-950 via-slate-950/80 to-transparent" />

        {/* Content */}
        <div className="relative z-10 max-w-xl p-8 md:p-14 space-y-4 text-white">
          <span className="font-display font-bold text-xs uppercase tracking-[0.2em] text-blue-400 block">
            &gt; HUMAN-IN-THE-LOOP & CITATION VERIFICATION
          </span>
          <h2 className="text-3xl md:text-4xl font-display font-black tracking-tight leading-tight">
            Mọi Luận Điểm Đều Neo Vào Văn Bản Gốc — Con Người Phê Duyệt Cuối
          </h2>
          <p className="text-xs md:text-sm text-slate-300 font-normal leading-relaxed">
            Nói không với ảo giác thông tin. Từng trích dẫn đều có liên kết kiểm chứng trực tiếp. Nhà nghiên cứu giữ toàn quyền kiểm soát, tinh chỉnh và phê duyệt ở từng cổng trước khi hoàn thiện dự thảo.
          </p>
          <div className="pt-2 flex justify-end">
            <button
              onClick={() => setActiveTab('setup')}
              className="px-7 py-3.5 bg-white text-slate-950 hover:bg-slate-100 rounded-2xl font-display font-bold text-xs uppercase tracking-wider transition-all hover:scale-105 active:scale-95 flex items-center gap-2 shadow-xl"
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
