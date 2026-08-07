import React, { useState } from 'react';
import { UploadCloud, FileText, Trash2, Sparkles, Link } from 'lucide-react';

export default function UploadTab({ selectedPapers, workspacePapers, setWorkspacePapers, setActiveTab, darkMode }) {
  const [pastedUrl, setPastedUrl] = useState('');
  const [isUploading, setIsUploading] = useState(false);

  const removeFile = (id) => {
    setWorkspacePapers(workspacePapers.filter(f => f.id !== id));
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    const paperId = `PDF-${Date.now().toString().slice(-4)}`;
    
    const formData = new FormData();
    formData.append("file", file);
    formData.append("paper_id", paperId);

    try {
      const response = await fetch("http://localhost:8000/api/v1/workspace/upload", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Upload failed");
      }

      const data = await response.json();
      
      const newPaper = {
        id: paperId,
        title: data.filename,
        authors: 'User Uploaded Source',
        journal: `Tài liệu PDF (${data.total_pages} trang)`,
        year: new Date().getFullYear(),
        citations: 0,
        litScore: 100,
        doi: 'Local File',
        url: '#',
        abstract: data.message,
        tldr: `Đã nạp ${data.total_chunks} chunks vào Vector DB.`
      };
      
      setWorkspacePapers([newPaper, ...workspacePapers]);
    } catch (error) {
      console.error("Lỗi khi upload:", error);
      alert("Đã có lỗi xảy ra khi tải file lên hệ thống.");
    } finally {
      setIsUploading(false);
      // Reset input value to allow uploading the same file again if needed
      e.target.value = null;
    }
  };

  const handleAddUrl = (e) => {
    e.preventDefault();
    if (!pastedUrl.trim()) return;
    const newPaper = {
      id: `CUSTOM-${Date.now().toString().slice(-4)}`,
      title: `Tài liệu vừa nạp từ Link: ${pastedUrl}`,
      authors: 'User Uploaded Source',
      journal: 'Custom PDF / Abstract Source',
      year: 2024,
      citations: 0,
      litScore: 90,
      doi: pastedUrl,
      url: pastedUrl,
      abstract: 'Nội dung toàn văn bài báo vừa được trích xuất từ link PDF do người dùng cung cấp.',
      tldr: 'Nạp qua URL'
    };
    setWorkspacePapers([newPaper, ...workspacePapers]);
    setPastedUrl('');
  };

  return (
    <div className="space-y-8 max-w-4xl mx-auto py-4">
      {/* Page Header */}
      <div className="text-center space-y-3">
        <h2 className={`text-3xl md:text-4xl font-extrabold tracking-tight ${darkMode ? 'text-white' : 'text-slate-900'}`}>
          2. Tải lên Hệ thống (NotebookLM Source Manager)
        </h2>
        <p className={`text-base max-w-xl mx-auto font-medium ${darkMode ? 'text-slate-400' : 'text-slate-600'}`}>
          Đưa file PDF bài báo vừa tải về (hoặc dán Link DOI/PDF) vào hệ thống AI để làm nguồn tri thức cho RAG Agent.
        </p>
      </div>

      {/* Drag & Drop Card */}
      <div className={`p-8 md:p-12 text-center space-y-4 border-2 border-dashed rounded-3xl transition-colors relative ${
        darkMode ? 'bg-slate-900 border-slate-700 text-slate-300' : 'bg-white border-blue-200'
      }`}>
        {isUploading ? (
          <div className="flex flex-col items-center justify-center space-y-4">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <p className="font-bold text-blue-600 animate-pulse">Đang băm nhỏ văn bản và nhúng Vector...</p>
          </div>
        ) : (
          <>
            <div className="w-16 h-16 rounded-2xl bg-blue-50 dark:bg-blue-950/80 text-blue-600 dark:text-sky-400 flex items-center justify-center mx-auto shadow-inner">
              <UploadCloud className="w-8 h-8" />
            </div>
            <div className="space-y-1">
              <h3 className={`font-bold text-lg ${darkMode ? 'text-white' : 'text-slate-900'}`}>
                Kéo & Thả File PDF bài báo vào đây
              </h3>
              <p className="text-xs text-slate-500 font-medium">Chỉ hỗ trợ định dạng .PDF (Tối đa 50MB/file)</p>
            </div>
            
            <label className="bg-blue-600 hover:bg-blue-700 text-white font-bold px-8 py-3 rounded-2xl text-xs shadow-md transition-all cursor-pointer inline-block">
              Chọn File Từ Máy Tính
              <input type="file" accept=".pdf" className="hidden" onChange={handleFileUpload} />
            </label>
          </>
        )}
      </div>

      {/* Dán Link Option */}
      <form onSubmit={handleAddUrl} className={`p-5 rounded-2xl border flex gap-3 items-center ${
        darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'
      }`}>
        <Link className="w-5 h-5 text-blue-600 shrink-0 ml-2" />
        <input
          type="text"
          value={pastedUrl}
          onChange={(e) => setPastedUrl(e.target.value)}
          placeholder="Dán đường dẫn Link PDF hoặc Mã DOI bài báo vào đây..."
          className={`flex-1 border-none bg-transparent text-sm font-medium focus:outline-none ${
            darkMode ? 'text-white placeholder-slate-500' : 'text-slate-900 placeholder-slate-400'
          }`}
        />
        <button type="submit" className="bg-slate-900 dark:bg-slate-700 hover:bg-slate-800 text-white font-bold px-5 py-2.5 rounded-xl text-xs">
          Thêm Nguồn
        </button>
      </form>

      {/* Uploaded Sources List */}
      <div className={`p-6 md:p-8 rounded-3xl border space-y-5 ${
        darkMode ? 'bg-slate-900 border-slate-800 text-slate-200' : 'bg-white border-slate-200'
      }`}>
        <div className="flex items-center justify-between border-b pb-4 border-slate-100 dark:border-slate-800">
          <h3 className="font-bold text-base flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-600 dark:text-sky-400" />
            <span>Danh sách Tài liệu Nguồn ({workspacePapers.length} bài)</span>
          </h3>
          <span className="text-xs text-emerald-600 dark:text-emerald-400 font-bold bg-emerald-50 dark:bg-emerald-950/60 px-3 py-1 rounded-lg">
            ✓ Đã sẵn sàng Vectorize
          </span>
        </div>

        {workspacePapers.length === 0 ? (
          <p className="text-sm text-slate-400 italic text-center py-8">
            Chưa có tài liệu nào được nạp. Hãy chọn bài báo ở Bước 1 hoặc tải file PDF lên.
          </p>
        ) : (
          <div className="space-y-3">
            {workspacePapers.map((file, idx) => (
              <div
                key={file.id}
                className={`p-4 rounded-2xl border flex items-center justify-between gap-4 text-sm ${
                  darkMode ? 'bg-slate-800/60 border-slate-700' : 'bg-slate-50 border-slate-200'
                }`}
              >
                <div className="flex items-center gap-3 overflow-hidden">
                  <span className="w-7 h-7 rounded-xl bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-sky-300 font-bold flex items-center justify-center text-xs shrink-0">
                    {idx + 1}
                  </span>
                  <div className="truncate">
                    <p className="font-bold truncate">{file.title}</p>
                    <p className="text-xs text-slate-500 font-medium">Nguồn: {file.journal} ({file.year}) • DOI: {file.doi}</p>
                    <p className="text-xs text-emerald-600 font-bold mt-1">{file.abstract}</p>
                  </div>
                </div>

                <button
                  onClick={() => removeFile(file.id)}
                  className="p-2 text-slate-400 hover:text-red-500 transition-colors"
                  title="Xóa tài liệu này"
                >
                  <Trash2 className="w-5 h-5" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Start AI Workspace Button */}
      {workspacePapers.length > 0 && (
        <div className="text-center pt-2">
          <button
            onClick={() => setActiveTab('workspace')}
            className="bg-blue-600 hover:bg-blue-700 text-white font-bold px-8 py-4 rounded-2xl text-sm inline-flex items-center gap-2 shadow-xl transition-all"
          >
            <Sparkles className="w-5 h-5 text-amber-300" />
            <span>Kích hoạt AI Workspace (Bắt đầu Tra cứu như NotebookLM) →</span>
          </button>
        </div>
      )}

    </div>
  );
}
