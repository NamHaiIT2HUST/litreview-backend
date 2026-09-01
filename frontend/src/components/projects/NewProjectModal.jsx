import React, { useState, useEffect, useRef } from 'react';
import { X, Plus, Sparkles, BookOpen, ArrowRight, Lightbulb, Compass } from 'lucide-react';
import { useProject } from '../../contexts/ProjectContext';
import { useLanguage } from '../../contexts/LanguageContext';

const QUICK_TOPICS = [
  { label: 'Y sinh & Tín hiệu', field: 'Y sinh & Chẩn đoán y tế', example: 'Ứng dụng Deep Learning trong phân loại tín hiệu ECG' },
  { label: 'Trí tuệ nhân tạo & LLM', field: 'Trí tuệ nhân tạo & LLM', example: 'Khảo sát chuỗi tư duy (Chain-of-Thought) trong LLMs' },
  { label: 'Robotics & Tự hành', field: 'Robotics & Hệ thống tự hành', example: 'Học tăng cường sâu và SLAM trong điều hướng robot' },
  { label: 'Khoa học môi trường', field: 'Khoa học môi trường & Năng lượng', example: 'Mô hình dự báo năng lượng tái tạo & Lưới điện thông minh' },
  { label: 'Khoa học dữ liệu', field: 'Khoa học dữ liệu & Hệ thống', example: 'Kiến trúc Multimodal RAG và tìm kiếm tri thức ngữ nghĩa' },
  { label: 'Kinh tế & Tài chính', field: 'Kinh tế, tài chính & Quản trị', example: 'Mô hình GNN trong đánh giá rủi ro tín dụng & Thị trường' },
];

export default function NewProjectModal({ isOpen, onClose, onCreated }) {
  const { createProject, switchProject } = useProject();
  const { language } = useLanguage();
  const isVi = language === 'vi';

  const [name, setName] = useState('');
  const [researchField, setResearchField] = useState('Trí tuệ nhân tạo & LLM');
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);
  // Tracks whether the mousedown that started this click also began on the
  // backdrop itself -- without it, selecting text inside the modal and
  // releasing the mouse outside its bounds fires a click on the backdrop
  // and closes the modal, silently discarding whatever was typed.
  const mouseDownOnBackdrop = useRef(false);

  useEffect(() => {
    if (isOpen) {
      setName('');
      setTimeout(() => {
        if (inputRef.current) inputRef.current.focus();
      }, 100);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSelectQuick = (item) => {
    setName(item.example);
    setResearchField(item.field);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;

    setLoading(true);
    try {
      const newProj = await createProject({
        name: name.trim(),
        research_field: researchField,
        research_question: '',
        year_from: 2020,
        year_to: new Date().getFullYear(),
        criteria_include: [],
        criteria_exclude: [],
      });
      if (newProj && newProj.id) {
        switchProject(newProj.id);
      }
      onClose();
      if (onCreated) onCreated();
    } catch (err) {
      console.error('Failed to create project:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/70 backdrop-blur-md animate-fade-in overflow-y-auto"
      onMouseDown={(e) => { mouseDownOnBackdrop.current = e.target === e.currentTarget; }}
      onClick={(e) => {
        if (mouseDownOnBackdrop.current && e.target === e.currentTarget && !loading) onClose();
        mouseDownOnBackdrop.current = false;
      }}
    >
      <div 
        className="w-full max-w-lg max-h-[90dvh] overflow-y-auto custom-scrollbar flex flex-col shadow-2xl bg-[#141A26] border border-slate-700/80 rounded-3xl animate-slide-up text-slate-100"
        onClick={e => e.stopPropagation()}
      >
        
        {/* Modal Header */}
        <div className="flex items-center justify-between p-4 sm:p-6 border-b border-slate-800 shrink-0 sticky top-0 bg-[#141A26]/95 backdrop-blur-md z-10">
          <div className="flex items-center gap-2.5 sm:gap-3">
            <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/25 shrink-0">
              <Plus className="w-4 h-4 sm:w-5 sm:h-5 stroke-[2.8]" />
            </div>
            <div>
              <h3 className="font-display font-extrabold text-sm sm:text-lg text-white">
                {isVi ? 'Tạo đề tài nghiên cứu mới' : 'Create New Research Project'}
              </h3>
              <p className="text-xs text-slate-400">
                {isVi ? 'Khởi tạo đề tài tổng quan tài liệu (SLR) theo chuẩn PRISMA' : 'Start Systematic Literature Review grounded on real DOIs'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Form */}
        <form onSubmit={handleSubmit} className="p-5 sm:p-6 space-y-5">
          
          {/* Quick Starter Suggestions */}
          <div>
            <div className="flex items-center gap-1.5 text-xs font-bold text-slate-300 mb-2">
              <Lightbulb className="w-3.5 h-3.5 text-amber-400" />
              <span>{isVi ? 'Gợi ý chủ đề nhanh (nhấp để chọn):' : 'Quick Topic Suggestions:'}</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {QUICK_TOPICS.map((item, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleSelectQuick(item)}
                  className="px-2.5 py-1.5 rounded-xl bg-slate-800/80 hover:bg-blue-600/20 border border-slate-700 hover:border-blue-500/50 text-[11px] font-semibold text-slate-300 hover:text-blue-300 transition-all cursor-pointer truncate"
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>

          {/* Project Name */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-200 block">
              {isVi ? 'Tên đề tài nghiên cứu *' : 'Research Topic / Project Name *'}
            </label>
            <input
              ref={inputRef}
              type="text"
              required
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder={isVi ? 'Ví dụ: Ứng dụng Deep Learning trong phân loại tín hiệu ECG...' : 'e.g., Deep Learning in Cardiac Arrhythmia ECG Detection...'}
              className="w-full px-4 py-3 rounded-2xl bg-[#1E2536] border border-slate-700 text-white placeholder-slate-400 text-xs sm:text-sm font-medium focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all shadow-inner"
            />
          </div>

          {/* Research Domain */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-200 block">
              {isVi ? 'Lĩnh vực chuyên ngành' : 'Research Domain'}
            </label>
            <select
              value={researchField}
              onChange={e => setResearchField(e.target.value)}
              className="w-full px-4 py-2.5 rounded-2xl bg-[#1E2536] border border-slate-700 text-slate-200 text-xs sm:text-sm font-medium focus:outline-none focus:border-blue-500 cursor-pointer"
            >
              <option value="Trí tuệ nhân tạo & LLM">{isVi ? '🧠 Trí tuệ nhân tạo & LLM' : '🧠 Artificial Intelligence & LLM'}</option>
              <option value="Y sinh & Chẩn đoán y tế">{isVi ? '🩺 Y sinh & Chẩn đoán y tế' : '🩺 Biomedical & Healthcare AI'}</option>
              <option value="Robotics & Hệ thống tự hành">{isVi ? '🤖 Robotics & Hệ thống tự hành' : '🤖 Robotics & Autonomous Systems'}</option>
              <option value="Khoa học dữ liệu & Hệ thống">{isVi ? '⚡ Khoa học dữ liệu & Hệ thống' : '⚡ Data Science & Systems'}</option>
              <option value="Khoa học môi trường & Năng lượng">{isVi ? '🌱 Khoa học môi trường & Năng lượng' : '🌱 Environmental & Energy Science'}</option>
              <option value="Kinh tế, tài chính & Quản trị">{isVi ? '📊 Kinh tế, tài chính & Quản trị' : '📊 Economics, Finance & Management'}</option>
              <option value="Khoa học xã hội & Giáo dục">{isVi ? '📚 Khoa học xã hội & Giáo dục' : '📚 Social Sciences & Education'}</option>
              <option value="Nghiên cứu liên ngành khác">{isVi ? '🔬 Nghiên cứu liên ngành khác' : '🔬 Other Interdisciplinary Fields'}</option>
            </select>
          </div>

          {/* Helpful Footnote */}
          <div className="p-3 rounded-2xl bg-blue-500/10 border border-blue-500/20 text-[11px] text-blue-300 leading-relaxed flex items-start gap-2">
            <Sparkles className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
            <span>
              {isVi 
                ? 'Bạn có thể thiết lập chi tiết câu hỏi PICO, giai đoạn năm & Tiêu chí sàng lọc PRISMA ở bước 1 sau khi vào không gian làm việc.'
                : 'You will configure the PICO framework, year bounds, and PRISMA screening criteria inside the workspace.'}
            </span>
          </div>

          {/* Action Buttons */}
          <div className="pt-2 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 rounded-full text-xs font-bold text-slate-300 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
            >
              {isVi ? 'Hủy' : 'Cancel'}
            </button>
            <button
              type="submit"
              disabled={loading || !name.trim()}
              className="px-5 py-2.5 rounded-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-extrabold text-xs sm:text-sm flex items-center gap-2 shadow-lg shadow-blue-600/30 hover:scale-105 transition-all cursor-pointer"
            >
              <span>{loading ? (isVi ? 'Đang tạo...' : 'Creating...') : (isVi ? 'Tạo & Vào không gian làm việc' : 'Create & Open Workspace')}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>

        </form>

      </div>
    </div>
  );
}
