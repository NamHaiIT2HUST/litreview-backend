import React, { useState } from 'react';
import { X, Plus, Sparkles, BookOpen, Layers, CheckCircle2, ArrowRight } from 'lucide-react';
import { useProject } from '../../contexts/ProjectContext';

const TEMPLATES = [
  {
    title: 'Medical / Healthcare AI',
    field: 'Y tế & Chẩn đoán Y sinh',
    question: 'Ứng dụng các kiến trúc Transformer và Vision-Language Models trong phân tích hình ảnh và chẩn đoán y sinh học.',
    include: ['Bài báo xuất bản bằng tiếng Anh trong 5 năm gần nhất', 'Mô hình có thử nghiệm định lượng trên tập dữ liệu lâm sàng'],
    exclude: ['Bài tổng quan không có mã nguồn hoặc dữ liệu thực tế'],
  },
  {
    title: 'LLM Reasoning & Agents',
    field: 'Toán học & Tối ưu hóa',
    question: 'Cơ chế kích hoạt tư duy (Chain-of-Thought) và multi-agent reasoning trong giải quyết bài toán phức tạp trên mô hình ngôn ngữ lớn.',
    include: ['Đánh giá trên benchmark chuẩn (GSM8K, MATH, HumanEval)', 'Xuất bản tại các hội nghị đầu ngành (NeurIPS, ICML, ICLR)'],
    exclude: ['Các ứng dụng chatbot thông thường không đánh giá độ chính xác logic'],
  },
  {
    title: 'Robotics & Autonomous Systems',
    field: 'Robotics & Tự hành',
    question: 'Thuật toán học tăng cường sâu (Deep RL) và SLAM trong điều hướng tự chủ môi trường phức tạp.',
    include: ['Nghiên cứu có thử nghiệm trên robot thật hoặc simulator chuẩn (Gazebo, Isaac Sim)'],
    exclude: ['Mô phỏng 2D đơn giản'],
  },
];

export default function NewProjectModal({ isOpen, onClose }) {
  const { createProject } = useProject();

  const [name, setName] = useState('');
  const [researchQuestion, setResearchQuestion] = useState('');
  const [researchField, setResearchField] = useState('Y tế & Chẩn đoán Y sinh');
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
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-md animate-fade-in">
      <div className="card w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden shadow-2xl animate-slide-up bg-white dark:bg-surface-900 border-surface-200 dark:border-surface-800">
        
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-surface-100 dark:border-surface-800 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-primary-600 flex items-center justify-center text-white">
              <Plus className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-display font-bold text-sm text-surface-900 dark:text-white">Khởi tạo Đề tài Nghiên cứu Mới</h3>
              <p className="text-[10px] text-surface-400">Thiết lập phạm vi dự án SLR theo chuẩn PRISMA 2020</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-surface-400 hover:text-surface-600 dark:hover:text-surface-200 hover:bg-surface-100 dark:hover:bg-surface-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto space-y-4 flex-1">
          
          {/* Quick Templates */}
          <div>
            <span className="section-label block mb-2">⚡ Gợi ý Mẫu Đề tài Nhanh:</span>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              {TEMPLATES.map((tmpl, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => handleApplyTemplate(tmpl)}
                  className="p-2.5 text-left rounded-xl border border-surface-200 dark:border-surface-700 hover:border-primary-400 dark:hover:border-primary-600 bg-surface-50 dark:bg-surface-800/40 hover:bg-primary-50/50 dark:hover:bg-primary-950/20 transition-all text-xs group"
                >
                  <p className="font-semibold text-surface-900 dark:text-white group-hover:text-primary-600 dark:group-hover:text-primary-400 truncate">{tmpl.title}</p>
                  <p className="text-[10px] text-surface-400 truncate mt-0.5">{tmpl.field}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Project Name */}
          <div>
            <label className="section-label block mb-1">Tên Đề tài / Dự án Nghiên cứu *</label>
            <input
              type="text"
              required
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="vd: Tổng quan về Mô hình Vision-Language trong Chẩn đoán Y tế"
              className="input input-sm"
            />
          </div>

          {/* Research Question & Field */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="section-label block mb-1">Lĩnh vực chuyên ngành</label>
              <select
                value={researchField}
                onChange={e => setResearchField(e.target.value)}
                className="input input-sm appearance-none"
              >
                <option value="Y tế & Chẩn đoán Y sinh">Y tế & Chẩn đoán Y sinh</option>
                <option value="Toán học & Tối ưu hóa">Toán học & Tối ưu hóa</option>
                <option value="Robotics & Tự hành">Robotics & Tự hành</option>
                <option value="Xử lý Ngôn ngữ Tự nhiên (NLP)">Xử lý Ngôn ngữ Tự nhiên (NLP)</option>
                <option value="Khoa học Xã hội & Giáo dục">Khoa học Xã hội & Giáo dục</option>
                <option value="Khác">Khác (General Academic)</option>
              </select>
            </div>

            <div className="flex gap-2">
              <div className="flex-1">
                <label className="section-label block mb-1">Từ năm</label>
                <input
                  type="number"
                  value={yearFrom}
                  onChange={e => setYearFrom(e.target.value)}
                  className="input input-sm"
                />
              </div>
              <div className="flex-1">
                <label className="section-label block mb-1">Đến năm</label>
                <input
                  type="number"
                  value={yearTo}
                  onChange={e => setYearTo(e.target.value)}
                  className="input input-sm"
                />
              </div>
            </div>
          </div>

          {/* Research Question */}
          <div>
            <label className="section-label block mb-1">Câu hỏi nghiên cứu cốt lõi (Research Question)</label>
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
