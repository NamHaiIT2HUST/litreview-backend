import React, { useState, useEffect, useRef } from 'react';
import { X, Plus, Sparkles, BookOpen, ArrowRight, Lightbulb, Compass } from 'lucide-react';
import { useProject } from '../../contexts/ProjectContext';
import { useLanguage } from '../../contexts/LanguageContext';

const QUICK_TOPICS = [
  { label: 'Y sinh & Tín hiệu', field: 'Y sinh & Chẩn đoán Y tế', example: 'Ứng dụng Deep Learning trong Phân loại Tín hiệu ECG' },
  { label: 'Trí tuệ Nhân tạo & LLM', field: 'Trí tuệ Nhân tạo & LLM', example: 'Khảo sát Chuỗi Tư duy (Chain-of-Thought) trong LLMs' },
  { label: 'Robotics & Tự hành', field: 'Robotics & Hệ thống Tự hành', example: 'Học tăng cường sâu và SLAM trong Điều hướng Robot' },
  { label: 'Khoa học Môi trường', field: 'Khoa học Môi trường & Năng lượng', example: 'Mô hình Dự báo Năng lượng Tái tạo & Lưới điện Thông minh' },
  { label: 'Khoa học Dữ liệu', field: 'Khoa học Dữ liệu & Hệ thống', example: 'Kiến trúc Multimodal RAG và Tìm kiếm Tri thức Ngữ nghĩa' },
  { label: 'Kinh tế & Tài chính', field: 'Kinh tế, Tài chính & Quản trị', example: 'Mô hình GNN trong Đánh giá Rủi ro Tín dụng & Thị trường' },
];

export default function NewProjectModal({ isOpen, onClose, onCreated }) {
  const { createProject, switchProject } = useProject();
  const { language } = useLanguage();
  const isVi = language === 'vi';

  const [name, setName] = useState('');
  const [researchField, setResearchField] = useState('Trí tuệ Nhân tạo & LLM');
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);

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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md animate-fade-in">
      <div 
        className="w-full max-w-lg flex flex-col overflow-hidden shadow-2xl bg-[#141A26] border border-slate-700/80 rounded-3xl animate-slide-up text-slate-100"
        onClick={e => e.stopPropagation()}
      >
        
        {/* Modal Header */}
        <div className="flex items-center justify-between p-5 sm:p-6 border-b border-slate-800 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/25">
              <Plus className="w-5 h-5 stroke-[2.8]" />
            </div>
            <div>
              <h3 className="font-display font-extrabold text-base sm:text-lg text-white">
                {isVi ? 'Tạo Đề tài Nghiên cứu Mới' : 'Create New Research Project'}
              </h3>
              <p className="text-xs text-slate-400">
                {isVi ? 'Khởi tạo đề tài Tổng quan Tài liệu (SLR) theo chuẩn PRISMA' : 'Start Systematic Literature Review grounded on real DOIs'}
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
              <span>{isVi ? 'Gợi ý chủ đề nhanh (Click để chọn):' : 'Quick Topic Suggestions:'}</span>
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
              {isVi ? 'Tên Đề tài Nghiên cứu *' : 'Research Topic / Project Name *'}
            </label>
            <input
              ref={inputRef}
              type="text"
              required
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder={isVi ? 'vd: Ứng dụng Deep Learning trong Phân loại Tín hiệu ECG...' : 'e.g., Deep Learning in Cardiac Arrhythmia ECG Detection...'}
              className="w-full px-4 py-3 rounded-2xl bg-[#1E2536] border border-slate-700 text-white placeholder-slate-400 text-xs sm:text-sm font-medium focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all shadow-inner"
            />
          </div>

          {/* Research Domain */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-200 block">
              {isVi ? 'Lĩnh vực Chuyên ngành' : 'Research Domain'}
            </label>
            <select
              value={researchField}
              onChange={e => setResearchField(e.target.value)}
              className="w-full px-4 py-2.5 rounded-2xl bg-[#1E2536] border border-slate-700 text-slate-200 text-xs sm:text-sm font-medium focus:outline-none focus:border-blue-500 cursor-pointer"
            >
              <option value="Trí tuệ Nhân tạo & LLM">{isVi ? '🧠 Trí tuệ Nhân tạo & LLM' : '🧠 Artificial Intelligence & LLM'}</option>
              <option value="Y sinh & Chẩn đoán Y tế">{isVi ? '🩺 Y sinh & Chẩn đoán Y tế' : '🩺 Biomedical & Healthcare AI'}</option>
              <option value="Robotics & Hệ thống Tự hành">{isVi ? '🤖 Robotics & Hệ thống Tự hành' : '🤖 Robotics & Autonomous Systems'}</option>
              <option value="Khoa học Dữ liệu & Hệ thống">{isVi ? '⚡ Khoa học Dữ liệu & Hệ thống' : '⚡ Data Science & Systems'}</option>
              <option value="Khoa học Môi trường & Năng lượng">{isVi ? '🌱 Khoa học Môi trường & Năng lượng' : '🌱 Environmental & Energy Science'}</option>
              <option value="Kinh tế, Tài chính & Quản trị">{isVi ? '📊 Kinh tế, Tài chính & Quản trị' : '📊 Economics, Finance & Management'}</option>
              <option value="Khoa học Xã hội & Giáo dục">{isVi ? '📚 Khoa học Xã hội & Giáo dục' : '📚 Social Sciences & Education'}</option>
              <option value="Nghiên cứu Liên ngành Khác">{isVi ? '🔬 Nghiên cứu Liên ngành Khác' : '🔬 Other Interdisciplinary Fields'}</option>
            </select>
          </div>

          {/* Helpful Footnote */}
          <div className="p-3 rounded-2xl bg-blue-500/10 border border-blue-500/20 text-[11px] text-blue-300 leading-relaxed flex items-start gap-2">
            <Sparkles className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
            <span>
              {isVi 
                ? 'Bạn có thể thiết lập chi tiết Câu hỏi PICO, Giai đoạn năm & Tiêu chí sàng lọc PRISMA ở Bước 1 sau khi vào Không gian làm việc.'
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
              <span>{loading ? (isVi ? 'Đang tạo...' : 'Creating...') : (isVi ? 'Tạo & Vào Không gian làm việc' : 'Create & Open Workspace')}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>

        </form>

      </div>
    </div>
  );
}
