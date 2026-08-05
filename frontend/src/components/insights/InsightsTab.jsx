import React from 'react';
import { Lightbulb, Layers, Download } from 'lucide-react';

export default function InsightsTab({ workspacePapers, darkMode }) {
  return (
    <div className="space-y-8 max-w-5xl mx-auto py-4">
      {/* Page Title */}
      <div className="text-center space-y-3">
        <h2 className={`text-3xl md:text-4xl font-extrabold tracking-tight ${darkMode ? 'text-white' : 'text-slate-900'}`}>
          4. Phân tích Multi-Agent & Báo cáo
        </h2>
        <p className={`text-base max-w-2xl mx-auto font-medium ${darkMode ? 'text-slate-400' : 'text-slate-600'}`}>
          Những tính năng nâng cao do biệt đội Agents hỗ trợ: Tự động phát hiện Khoảng trống nghiên cứu & Lập Ma trận so sánh.
        </p>
      </div>

      {/* Feature 1: Research Gap Detector Card */}
      <div className={`p-6 md:p-8 rounded-3xl border space-y-5 shadow-sm transition-colors ${
        darkMode ? 'bg-slate-900 border-slate-800 text-slate-200' : 'bg-white border-slate-200'
      }`}>
        <div className="flex items-center gap-3 border-b pb-4 border-slate-100 dark:border-slate-800">
          <div className="p-3 bg-amber-100 dark:bg-amber-950/80 text-amber-600 dark:text-amber-300 rounded-2xl">
            <Lightbulb className="w-6 h-6" />
          </div>
          <div>
            <h3 className={`font-extrabold text-lg md:text-xl ${darkMode ? 'text-white' : 'text-slate-900'}`}>
              💡 Phát hiện Khoảng trống Nghiên cứu (Research Gap Detector)
            </h3>
            <p className="text-xs text-slate-500 font-medium">SynthesizerAgent tự động phân tích những mặt chưa được giải quyết của các công trình đã nạp.</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs md:text-sm">
          <div className={`p-5 rounded-2xl border ${darkMode ? 'bg-slate-800/80 border-slate-700' : 'bg-amber-50/50 border-amber-100'}`}>
            <h4 className="font-bold text-amber-700 dark:text-amber-300 mb-1.5 text-sm">1. Vấn đề về Mẫu dữ liệu (Sample Bias)</h4>
            <p className="text-slate-700 dark:text-slate-300 leading-relaxed">
              Các bài báo hiện tại chủ yếu thử nghiệm trên dữ liệu bệnh nhân tiếng Anh tại Mỹ. Chưa có nghiên cứu nào đánh giá độ chính xác trên dữ liệu y tế đa ngôn ngữ khu vực Đông Nam Á.
            </p>
          </div>

          <div className={`p-5 rounded-2xl border ${darkMode ? 'bg-slate-800/80 border-slate-700' : 'bg-amber-50/50 border-amber-100'}`}>
            <h4 className="font-bold text-amber-700 dark:text-amber-300 mb-1.5 text-sm">2. Thách thức về Latency & Chi phí</h4>
            <p className="text-slate-700 dark:text-slate-300 leading-relaxed">
              Model GPT-4 cho kết quả tốt nhưng chi phí API cao và thời gian phản hồi 2-3 giây không phù hợp cho ca cấp cứu khẩn cấp. Hướng đi khả thi: Fine-tune mô hình nhỏ Llama-3-8B local.
            </p>
          </div>
        </div>
      </div>

      {/* Feature 2: Automated Comparison Matrix */}
      <div className={`p-6 md:p-8 rounded-3xl border space-y-5 shadow-sm transition-colors ${
        darkMode ? 'bg-slate-900 border-slate-800 text-slate-200' : 'bg-white border-slate-200'
      }`}>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b pb-4 border-slate-100 dark:border-slate-800">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-blue-100 dark:bg-blue-950/80 text-blue-600 dark:text-sky-400 rounded-2xl">
              <Layers className="w-6 h-6" />
            </div>
            <div>
              <h3 className={`font-extrabold text-lg md:text-xl ${darkMode ? 'text-white' : 'text-slate-900'}`}>
                📊 Ma trận So sánh Phương pháp Nghiên cứu
              </h3>
              <p className="text-xs text-slate-500 font-medium">Tự động tổng hợp bảng so sánh các công trình đã tải lên</p>
            </div>
          </div>

          <button className="px-5 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-2xl text-xs font-bold flex items-center justify-center gap-2 shadow-md transition-all">
            <Download className="w-4 h-4" />
            <span>Xuất Báo cáo PDF</span>
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className={`w-full text-left text-xs md:text-sm border-collapse rounded-2xl overflow-hidden border ${
            darkMode ? 'bg-slate-800 border-slate-700' : 'bg-white border-slate-200'
          }`}>
            <thead>
              <tr className={`font-bold border-b ${
                darkMode ? 'bg-slate-900 text-slate-300 border-slate-700' : 'bg-slate-100 text-slate-700 border-slate-200'
              }`}>
                <th className="p-4">Bài báo</th>
                <th className="p-4">Phương pháp chính</th>
                <th className="p-4">Độ chính xác</th>
                <th className="p-4">Hạn chế chính</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${darkMode ? 'divide-slate-700' : 'divide-slate-100'}`}>
              {workspacePapers.map((paper, idx) => (
                <tr key={idx} className="hover:bg-blue-50/20">
                  <td className="p-4 font-bold text-blue-600 dark:text-sky-400">[{idx+1}] {paper.id}</td>
                  <td className="p-4">{paper.title.slice(0, 45)}...</td>
                  <td className="p-4 font-bold text-emerald-600 dark:text-emerald-400">89.4% Accuracy</td>
                  <td className="p-4 text-slate-500 dark:text-slate-400">Cần thẩm định với tập dữ liệu rộng hơn</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
