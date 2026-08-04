import React from 'react';
import { Search, Upload, Sparkles, PieChart, ArrowRight, ShieldCheck, Zap, Users } from 'lucide-react';

export default function HomeTab({ setActiveTab, darkMode }) {
  const features = [
    {
      icon: Search,
      title: 'Tra cứu Thông minh',
      description: 'Tìm kiếm hàng triệu bài báo khoa học từ Scopus & Web of Science với độ chính xác cao.',
      color: 'text-blue-500',
      bg: 'bg-blue-500/10'
    },
    {
      icon: Upload,
      title: 'Không gian NotebookLM',
      description: 'Upload các bài báo PDF của riêng bạn và quản lý chúng dễ dàng như NotebookLM của Google.',
      color: 'text-emerald-500',
      bg: 'bg-emerald-500/10'
    },
    {
      icon: Sparkles,
      title: 'Chat RAG Chuyên sâu',
      description: 'Hỏi đáp trực tiếp với tài liệu. AI sẽ trích xuất chính xác dẫn chứng từ bài báo của bạn.',
      color: 'text-amber-500',
      bg: 'bg-amber-500/10'
    },
    {
      icon: Users,
      title: 'Multi-Agent Phân tích',
      description: 'Đội ngũ chuyên gia AI ảo tự động tóm tắt, tìm điểm mới và đánh giá chất lượng bài báo.',
      color: 'text-purple-500',
      bg: 'bg-purple-500/10'
    }
  ];

  return (
    <div className={`space-y-12 pb-12 animate-in fade-in zoom-in-95 duration-500`}>
      {/* Hero Section */}
      <section className={`relative overflow-hidden rounded-3xl p-8 md:p-16 text-center ${
        darkMode ? 'bg-slate-900 border border-slate-800' : 'bg-white border border-slate-200'
      } shadow-sm`}>
        {/* Background Decorative Blobs */}
        <div className="absolute top-0 left-1/4 w-72 h-72 bg-blue-400 rounded-full mix-blend-multiply filter blur-[100px] opacity-30 dark:opacity-20 animate-blob"></div>
        <div className="absolute top-0 right-1/4 w-72 h-72 bg-sky-400 rounded-full mix-blend-multiply filter blur-[100px] opacity-30 dark:opacity-20 animate-blob animation-delay-2000"></div>
        <div className="absolute -bottom-8 left-1/3 w-72 h-72 bg-indigo-400 rounded-full mix-blend-multiply filter blur-[100px] opacity-30 dark:opacity-20 animate-blob animation-delay-4000"></div>
        
        <div className="relative z-10 max-w-3xl mx-auto space-y-6">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-bold bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-sky-400 mb-4 border border-blue-100 dark:border-blue-800/50 animate-float">
            <Sparkles className="w-4 h-4 text-amber-500 animate-pulse" />
            <span>Nền tảng Review Bài báo Khoa học bằng AI</span>
          </div>
          
          <h1 className="text-4xl md:text-6xl font-black tracking-tight leading-tight">
            Nghiên cứu nhanh hơn với <br className="hidden md:block"/>
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 via-sky-400 to-indigo-600 animate-gradient-x">LitReview Agent</span>
          </h1>
          
          <p className={`text-lg md:text-xl font-medium ${darkMode ? 'text-slate-400' : 'text-slate-600'} leading-relaxed`}>
            Khám phá, tổng hợp và phân tích hàng ngàn bài báo khoa học trong tích tắc với sức mạnh của Multi-Agent RAG System. Giao diện trực quan, thân thiện và mạnh mẽ.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
            <button
              onClick={() => setActiveTab('search')}
              className="flex items-center gap-2 px-8 py-4 bg-blue-600 hover:bg-blue-700 text-white rounded-2xl font-bold text-lg shadow-lg shadow-blue-500/30 transition-all hover:scale-105 active:scale-95 w-full sm:w-auto justify-center"
            >
              Bắt đầu Tra cứu ngay
              <ArrowRight className="w-5 h-5" />
            </button>
            <button
              onClick={() => setActiveTab('upload')}
              className={`flex items-center gap-2 px-8 py-4 rounded-2xl font-bold text-lg transition-all hover:scale-105 active:scale-95 w-full sm:w-auto justify-center ${
                darkMode 
                  ? 'bg-slate-800 hover:bg-slate-700 text-white border border-slate-700' 
                  : 'bg-slate-100 hover:bg-slate-200 text-slate-900 border border-slate-200'
              }`}
            >
              Upload PDF của bạn
            </button>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="space-y-8">
        <div className="text-center space-y-4">
          <h2 className="text-3xl md:text-4xl font-black">Tính năng Nổi bật</h2>
          <p className={`text-lg font-medium max-w-2xl mx-auto ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
            Được thiết kế chuyên biệt cho sinh viên, giảng viên và các nhà nghiên cứu để tối ưu hóa thời gian đọc hiểu tài liệu.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {features.map((feat, idx) => {
            const Icon = feat.icon;
            return (
              <div 
                key={idx}
                className={`group p-6 rounded-3xl border transition-all duration-300 hover:-translate-y-2 hover:shadow-2xl ${
                  darkMode 
                    ? 'bg-slate-900 border-slate-800 hover:shadow-blue-900/20 hover:border-slate-700' 
                    : 'bg-white border-slate-200 hover:shadow-slate-300 hover:border-slate-300'
                }`}
              >
                <div className={`w-14 h-14 rounded-2xl flex items-center justify-center mb-6 ${feat.bg} ${feat.color} group-hover:scale-110 group-hover:-rotate-3 transition-transform duration-300`}>
                  <Icon className="w-7 h-7" />
                </div>
                <h3 className="text-xl font-bold mb-3 group-hover:text-blue-600 dark:group-hover:text-sky-400 transition-colors">{feat.title}</h3>
                <p className={`text-sm font-medium leading-relaxed ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
                  {feat.description}
                </p>
              </div>
            );
          })}
        </div>
      </section>
      
      {/* Footer Banner */}
      <section className={`p-8 rounded-3xl flex flex-col md:flex-row items-center justify-between gap-6 border ${
        darkMode ? 'bg-gradient-to-r from-blue-900/40 to-slate-900 border-blue-900/50' : 'bg-gradient-to-r from-blue-50 to-white border-blue-100'
      }`}>
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-blue-600 text-white flex items-center justify-center shadow-lg shadow-blue-500/20">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <h4 className="font-bold text-lg">Bảo mật & Riêng tư</h4>
            <p className={`text-sm font-medium ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
              Tài liệu của bạn chỉ được lưu trữ cho mục đích tra cứu cá nhân.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-amber-500 text-white flex items-center justify-center shadow-lg shadow-amber-500/20">
            <Zap className="w-6 h-6" />
          </div>
          <div>
            <h4 className="font-bold text-lg">Tốc độ & Hiệu suất</h4>
            <p className={`text-sm font-medium ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
              Truy vấn và trả lời trong vài giây nhờ hệ thống RAG tối ưu.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
