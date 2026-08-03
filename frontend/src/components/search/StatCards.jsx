import React from 'react';
import { BookOpen, Award, FileSpreadsheet, Bot } from 'lucide-react';

export default function StatCards({ totalPapers, selectedCount, darkMode }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Card 1: Blue */}
      <div className={`mota-stat-card stat-blue ${darkMode ? 'bg-slate-800 border-slate-700 text-white' : 'bg-white'}`}>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Tổng số bài báo</p>
            <h3 className="text-2xl font-extrabold mt-1">{totalPapers}</h3>
          </div>
          <div className="w-10 h-10 rounded-xl bg-blue-50 dark:bg-blue-950 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold">
            <BookOpen className="w-5 h-5" />
          </div>
        </div>
        <p className="text-[11px] text-emerald-500 font-semibold mt-2">
          ScraperAgent đã lọc trùng
        </p>
      </div>

      {/* Card 2: Cyan */}
      <div className={`mota-stat-card stat-cyan ${darkMode ? 'bg-slate-800 border-slate-700 text-white' : 'bg-white'}`}>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Điểm LitScore TB</p>
            <h3 className="text-2xl font-extrabold mt-1">94.8 / 100</h3>
          </div>
          <div className="w-10 h-10 rounded-xl bg-cyan-50 dark:bg-cyan-950 text-cyan-600 dark:text-cyan-400 flex items-center justify-center font-bold">
            <Award className="w-5 h-5" />
          </div>
        </div>
        <p className="text-[11px] text-cyan-500 font-semibold mt-2">Xếp hạng uy tín (Impact Factor)</p>
      </div>

      {/* Card 3: Green */}
      <div className={`mota-stat-card stat-green ${darkMode ? 'bg-slate-800 border-slate-700 text-white' : 'bg-white'}`}>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Bài báo đã chọn</p>
            <h3 className="text-2xl font-extrabold mt-1">{selectedCount}</h3>
          </div>
          <div className="w-10 h-10 rounded-xl bg-emerald-50 dark:bg-emerald-950 text-emerald-600 dark:text-emerald-400 flex items-center justify-center font-bold">
            <FileSpreadsheet className="w-5 h-5" />
          </div>
        </div>
        <p className="text-[11px] text-emerald-500 font-semibold mt-2">Sẵn sàng xuất Excel / Push RAG</p>
      </div>

      {/* Card 4: Purple */}
      <div className={`mota-stat-card stat-purple ${darkMode ? 'bg-slate-800 border-slate-700 text-white' : 'bg-white'}`}>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Multi-Agent System</p>
            <h3 className="text-2xl font-extrabold mt-1">4 Active</h3>
          </div>
          <div className="w-10 h-10 rounded-xl bg-purple-50 dark:bg-purple-950 text-purple-600 dark:text-purple-400 flex items-center justify-center font-bold">
            <Bot className="w-5 h-5" />
          </div>
        </div>
        <p className="text-[11px] text-purple-500 font-semibold mt-2">Synthesizer & Verifier Agent</p>
      </div>
    </div>
  );
}
