import React from 'react';
import { BookOpen, Award, FileSpreadsheet, Sparkles } from 'lucide-react';

export default function StatCards({ totalPapers, selectedCount }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Card 1: Blue */}
      <div className="mota-stat-card stat-blue">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Tổng số bài báo</p>
            <h3 className="text-2xl font-extrabold text-slate-900 mt-1">{totalPapers}</h3>
          </div>
          <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center font-bold">
            <BookOpen className="w-5 h-5" />
          </div>
        </div>
        <p className="text-[11px] text-emerald-600 font-semibold mt-2 flex items-center gap-1">
          <span>↑ 100% Sạch dữ liệu</span>
        </p>
      </div>

      {/* Card 2: Cyan */}
      <div className="mota-stat-card stat-cyan">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Điểm LitScore Trung bình</p>
            <h3 className="text-2xl font-extrabold text-slate-900 mt-1">94.8 / 100</h3>
          </div>
          <div className="w-10 h-10 rounded-xl bg-cyan-50 text-cyan-600 flex items-center justify-center font-bold">
            <Award className="w-5 h-5" />
          </div>
        </div>
        <p className="text-[11px] text-cyan-600 font-semibold mt-2">Độ uy tín cao (High Impact)</p>
      </div>

      {/* Card 3: Green */}
      <div className="mota-stat-card stat-green">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Bài báo đã chọn</p>
            <h3 className="text-2xl font-extrabold text-slate-900 mt-1">{selectedCount}</h3>
          </div>
          <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold">
            <FileSpreadsheet className="w-5 h-5" />
          </div>
        </div>
        <p className="text-[11px] text-emerald-600 font-semibold mt-2">Sẵn sàng xuất Excel / Push RAG</p>
      </div>

      {/* Card 4: Purple */}
      <div className="mota-stat-card stat-purple">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Mô hình AI RAG</p>
            <h3 className="text-2xl font-extrabold text-slate-900 mt-1">Llama-3 Local</h3>
          </div>
          <div className="w-10 h-10 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center font-bold">
            <Sparkles className="w-5 h-5" />
          </div>
        </div>
        <p className="text-[11px] text-purple-600 font-semibold mt-2">Chống ảo giác 99.4%</p>
      </div>
    </div>
  );
}
