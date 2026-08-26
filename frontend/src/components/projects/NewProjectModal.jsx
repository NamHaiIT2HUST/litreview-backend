import React, { useState } from 'react';
import { X, Plus, Sparkles, BookOpen, Layers, CheckCircle2, ArrowRight } from 'lucide-react';
import { useProject } from '../../contexts/ProjectContext';

const TEMPLATES = [
  {
    title: 'Medical & Healthcare AI',
    field: 'Y sinh & Chẩn đoán Y tế',
    question: 'Ứng dụng các kiến trúc Vision-Language Models và Deep Learning trong phân tích hình ảnh và chẩn đoán y sinh học.',
    include: ['Bài báo xuất bản bằng tiếng Anh trong giai đoạn 2020-2026', 'Mô hình có thử nghiệm định lượng trên tập dữ liệu lâm sàng'],
    exclude: ['Bài tổng quan thuần túy không có thực nghiệm', 'Cỡ mẫu dưới 50 bệnh nhân'],
  },
  {
    title: 'LLM Reasoning & Agents',
    field: 'Xử lý Ngôn ngữ Tự nhiên & LLM',
    question: 'Cơ chế kích hoạt tư duy (Chain-of-Thought) và multi-agent reasoning trong giải quyết bài toán phức tạp trên mô hình ngôn ngữ lớn.',
    include: ['Đánh giá trên benchmark chuẩn (GSM8K, MATH, HumanEval)', 'Xuất bản tại các hội nghị đầu ngành (NeurIPS, ICML, ICLR, ACL)'],
    exclude: ['Các ứng dụng chatbot thông thường không đánh giá độ chính xác logic'],
  },
  {
    title: 'Robotics & Autonomous Systems',
    field: 'Robotics & Hệ thống Tự hành',
    question: 'Thuật toán học tăng cường sâu (Deep RL) và SLAM trong điều hướng tự chủ và thao tác robot trong môi trường không xác định.',
    include: ['Nghiên cứu có thử nghiệm trên robot thật hoặc simulator chuẩn (Gazebo, Isaac Sim)', 'Có đối sánh độ trễ thời gian thực'],
    exclude: ['Mô phỏng 2D đơn giản không tính động lực học vật lý'],
  },
  {
    title: 'Climate & Renewable Energy',
    field: 'Khoa học Môi trường & Năng lượng',
    question: 'Ứng dụng học máy và mô hình dự báo chuỗi thời gian trong tối ưu hóa lưới điện thông minh và năng lượng tái tạo.',
    include: ['Dữ liệu khí tượng hoặc lưới điện thực tế', 'Có phân tích sai số RMSE/MAE định lượng'],
    exclude: ['Các nghiên cứu lý thuyết không có kiểm chứng dữ liệu thực'],
  },
  {
    title: 'Computer Vision & Multimodal',
    field: 'Khoa học Máy tính & Trí tuệ Nhân tạo',
    question: 'Kiến trúc Multimodal RAG và Zero-shot Object Detection trong giám sát không gian 3D và xử lý video tốc độ cao.',
    include: ['Thử nghiệm trên bộ dữ liệu chuẩn COCO, ImageNet, nuScenes', 'Công bố mã nguồn hoặc kiến trúc chi tiết'],
    exclude: ['Nghiên cứu chất lượng thấp không công bố tham số huấn luyện'],
  },
  {
    title: 'Fintech & Risk Modeling',
    field: 'Kinh tế, Tài chính & Quản trị',
    question: 'Mô hình Graph Neural Networks kết hợp Sentiment Analysis trong dự báo rủi ro tín dụng và biến động thị trường tài chính.',
    include: ['Dữ liệu giao dịch thị trường thực tế', 'Có backtesting với các chỉ số Sharpe Ratio, Max Drawdown'],
    exclude: ['Nghiên cứu không có kiểm định thống kê'],
  },
];

export default function NewProjectModal({ isOpen, onClose, onCreated }) {
  const { createProject } = useProject();

  const [name, setName] = useState('');
  const [researchQuestion, setResearchQuestion] = useState('');
  const [researchField, setResearchField] = useState('Khoa học Máy tính & Trí tuệ Nhân tạo');
  const [yearFrom, setYearFrom] = useState(2020);
  const [yearTo, setYearTo] = useState(new Date().getFullYear());
  const [includeText, setIncludeText] = useState('');
  const [excludeText, setExcludeText] = useState('');
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleApplyTemplate = (tmpl) => {
    setName(`Tổng quan về ${tmpl.title}`);
    setResearchField(tmpl.field);
    setResearchQuestion(tmpl.question);
    setIncludeText(tmpl.include.join('\n'));
    setExcludeText(tmpl.exclude.join('\n'));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;

    setLoading(true);
    const criteria_include = includeText.split('\n').map(s => s.trim()).filter(Boolean);
    const criteria_exclude = excludeText.split('\n').map(s => s.trim()).filter(Boolean);

    await createProject({
      name,
      research_question: researchQuestion,
      research_field: researchField,
      year_from: parseInt(yearFrom) || 2020,
      year_to: parseInt(yearTo) || new Date().getFullYear(),
      criteria_include,
      criteria_exclude,
    });

    setLoading(false);
    onClose();
    if (onCreated) onCreated();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="card w-full max-w-3xl max-h-[92vh] flex flex-col overflow-hidden shadow-2xl animate-slide-up bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 rounded-2xl">
        
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-100 dark:border-slate-800 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
              <Plus className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-display font-bold text-base text-slate-900 dark:text-white">Khởi tạo Đề tài Nghiên cứu Mới</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">Hỗ trợ mọi chủ đề khoa học — Thiết lập phạm vi theo chuẩn PRISMA</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto space-y-4 flex-1">
          
          {/* Quick Starter Templates */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-slate-700 dark:text-slate-300">💡 Gợi ý Mẫu Tham khảo Nhanh (Tuỳ chọn):</span>
              <span className="text-[11px] text-slate-400">Click để tự động điền mẫu</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {TEMPLATES.map((tmpl, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => handleApplyTemplate(tmpl)}
                  className="p-2.5 text-left rounded-xl border border-slate-200 dark:border-slate-700/80 hover:border-blue-500 dark:hover:border-blue-400 bg-slate-50/70 dark:bg-slate-800/40 hover:bg-blue-50/50 dark:hover:bg-blue-950/20 transition-all text-xs group cursor-pointer"
                >
                  <p className="font-bold text-slate-800 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 truncate">{tmpl.title}</p>
                  <p className="text-[10.5px] text-slate-500 dark:text-slate-400 truncate mt-0.5">{tmpl.field}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Project Name */}
          <div>
            <label className="text-xs font-bold text-slate-700 dark:text-slate-300 block mb-1">Tên Đề tài / Dự án Nghiên cứu *</label>
            <input
              type="text"
              required
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="Nhập bất kỳ đề tài nào, ví dụ: Tổng quan về Mô hình Vision-Language trong Chẩn đoán Y tế..."
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-all"
            />
          </div>

          {/* Research Question & Field */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-bold text-slate-700 dark:text-slate-300 block mb-1">Lĩnh vực chuyên ngành</label>
              <select
                value={researchField}
                onChange={e => setResearchField(e.target.value)}
                className="w-full px-3 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-all appearance-none cursor-pointer"
              >
                <option value="Khoa học Máy tính & Trí tuệ Nhân tạo">Khoa học Máy tính & Trí tuệ Nhân tạo</option>
                <option value="Y sinh & Chẩn đoán Y tế">Y sinh & Chẩn đoán Y tế</option>
                <option value="Robotics & Hệ thống Tự hành">Robotics & Hệ thống Tự hành</option>
                <option value="Xử lý Ngôn ngữ Tự nhiên & LLM">Xử lý Ngôn ngữ Tự nhiên & LLM</option>
                <option value="Toán học, Thống kê & Tối ưu hóa">Toán học, Thống kê & Tối ưu hóa</option>
                <option value="Khoa học Môi trường & Năng lượng">Khoa học Môi trường & Năng lượng</option>
                <option value="Kinh tế, Tài chính & Quản trị">Kinh tế, Tài chính & Quản trị</option>
                <option value="Khoa học Xã hội & Giáo dục">Khoa học Xã hội & Giáo dục</option>
                <option value="Nghiên cứu Liên ngành Khác">Nghiên cứu Liên ngành Khác</option>
              </select>
            </div>

            <div className="flex gap-2">
              <div className="flex-1">
                <label className="text-xs font-bold text-slate-700 dark:text-slate-300 block mb-1">Từ năm</label>
                <input
                  type="number"
                  value={yearFrom}
                  onChange={e => setYearFrom(e.target.value)}
                  className="w-full px-3 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-all"
                />
              </div>
              <div className="flex-1">
                <label className="text-xs font-bold text-slate-700 dark:text-slate-300 block mb-1">Đến năm</label>
                <input
                  type="number"
                  value={yearTo}
                  onChange={e => setYearTo(e.target.value)}
                  className="w-full px-3 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition-all"
                />
              </div>
            </div>
          </div>

          {/* Research Question */}
          <div>
            <label className="text-xs font-bold text-slate-700 dark:text-slate-300 block mb-1">Câu hỏi nghiên cứu cốt lõi (Research Question)</label>
            <textarea
              rows="2.5"
              value={researchQuestion}
              onChange={e => setResearchQuestion(e.target.value)}
              placeholder="vd: Hiệu năng và độ tin cậy của các mô hình học sâu trong phát hiện bất thường..."
              className="input input-sm resize-none"
            />
          </div>

          {/* Screening Criteria */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="section-label block mb-1 text-emerald-600 dark:text-emerald-400">Tiêu chí Đưa vào (Mỗi dòng 1 tiêu chí)</label>
              <textarea
                rows="3"
                value={includeText}
                onChange={e => setIncludeText(e.target.value)}
                placeholder="Bài báo tiếng Anh giai đoạn 2020-2026&#10;Có thực nghiệm định lượng"
                className="input input-sm resize-none text-xs"
              />
            </div>
            <div>
              <label className="section-label block mb-1 text-rose-600 dark:text-rose-400">Tiêu chí Loại trừ (Mỗi dòng 1 tiêu chí)</label>
              <textarea
                rows="3"
                value={excludeText}
                onChange={e => setExcludeText(e.target.value)}
                placeholder="Bài tổng quan lý thuyết không có thực nghiệm&#10;Dữ liệu mẫu dưới 50"
                className="input input-sm resize-none text-xs"
              />
            </div>
          </div>

          {/* Footer Submit */}
          <div className="pt-3 border-t border-surface-100 dark:border-surface-800 flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="btn btn-secondary btn-sm"
            >
              Hủy
            </button>
            <button
              type="submit"
              disabled={loading || !name.trim()}
              className="btn btn-primary btn-sm shadow-primary-sm"
            >
              <span>{loading ? 'Đang tạo...' : 'Tạo Đề tài & Vào Không gian làm việc'}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </form>

      </div>
    </div>
  );
}
