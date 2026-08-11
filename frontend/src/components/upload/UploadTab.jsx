import React, { useEffect, useMemo, useState } from 'react';
import { UploadCloud, FileText, Trash2, Sparkles, Link, CheckCircle2 } from 'lucide-react';

export default function UploadTab({ selectedPapers, workspacePapers, setWorkspacePapers, setActiveTab, darkMode }) {
  const [pastedUrl, setPastedUrl] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [targetPaperId, setTargetPaperId] = useState(selectedPapers[0]?.id || '');

  useEffect(() => {
    if (!selectedPapers.some((paper) => paper.id === targetPaperId)) {
      setTargetPaperId(selectedPapers[0]?.id || '');
    }
  }, [selectedPapers, targetPaperId]);

  const targetPaper = useMemo(
    () => selectedPapers.find((paper) => paper.id === targetPaperId) || null,
    [selectedPapers, targetPaperId],
  );

  const removeFile = (id) => {
    setWorkspacePapers((prev) => prev.filter((file) => file.id !== id));
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file || !targetPaper) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('paper_id', targetPaper.id);
    if (targetPaper.doi && targetPaper.doi !== 'N/A') {
      formData.append('doi', targetPaper.doi);
    }

    try {
      const response = await fetch('http://localhost:8000/api/v1/workspace/upload', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Upload failed');
      }

      const uploadedPaper = {
        ...targetPaper,
        uploadFilename: data.filename,
        totalPages: data.total_pages,
        totalChunks: data.total_chunks,
        ingestionMessage: data.message,
      };

      setWorkspacePapers((prev) => [
        uploadedPaper,
        ...prev.filter((paper) => paper.id !== targetPaper.id),
      ]);
    } catch (error) {
      console.error('Lỗi khi upload:', error);
      alert(error.message || 'Đã có lỗi xảy ra khi tải file lên hệ thống.');
    } finally {
      setIsUploading(false);
      event.target.value = null;
    }
  };

  const handleAddUrl = (event) => {
    event.preventDefault();
    if (!pastedUrl.trim()) return;
    alert('URL/DOI import chưa tạo PageText provenance nên chưa được đưa vào Synthesis. Hãy upload PDF cho paper đã chọn.');
  };

  const uploadedIds = new Set(workspacePapers.map((paper) => paper.id));

  return (
    <div className="space-y-8 max-w-4xl mx-auto py-4">
      <div className="text-center space-y-3">
        <h2 className={`text-3xl md:text-4xl font-extrabold tracking-tight ${darkMode ? 'text-white' : 'text-slate-900'}`}>
          2. Nạp toàn văn cho các paper đã chọn
        </h2>
        <p className={`text-base max-w-2xl mx-auto font-medium ${darkMode ? 'text-slate-400' : 'text-slate-600'}`}>
          Mỗi PDF phải gắn với đúng paper trong thư viện để hệ thống lưu PageText, chunk offset và provenance dùng cho bước tổng hợp.
        </p>
      </div>

      <div className={`p-6 md:p-8 border rounded-3xl space-y-5 ${darkMode ? 'bg-slate-900 border-slate-700' : 'bg-white border-slate-200'}`}>
        <div>
          <label className="block text-xs font-bold uppercase tracking-wide text-slate-500 mb-2">
            Paper nhận PDF
          </label>
          <select
            value={targetPaperId}
            onChange={(event) => setTargetPaperId(event.target.value)}
            disabled={selectedPapers.length === 0 || isUploading}
            className={`w-full px-4 py-3 rounded-xl border text-sm ${
              darkMode ? 'bg-slate-800 border-slate-700 text-white' : 'bg-slate-50 border-slate-300 text-slate-900'
            }`}
          >
            {selectedPapers.length === 0 && <option value="">Chưa có paper nào được Keep</option>}
            {selectedPapers.map((paper) => (
              <option key={paper.id} value={paper.id}>
                {paper.title}
              </option>
            ))}
          </select>
        </div>

        <div className={`p-8 text-center space-y-4 border-2 border-dashed rounded-3xl ${darkMode ? 'bg-slate-950/40 border-slate-700' : 'bg-slate-50 border-blue-200'}`}>
          {isUploading ? (
            <div className="flex flex-col items-center gap-3">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" />
              <p className="font-bold text-blue-600">Đang parse PDF, lưu PageText và index Chroma...</p>
            </div>
          ) : (
            <>
              <UploadCloud className="w-10 h-10 mx-auto text-blue-600" />
              <p className="text-sm font-semibold text-slate-600 dark:text-slate-300">
                {targetPaper ? `Upload PDF cho: ${targetPaper.title}` : 'Hãy Keep paper ở bước Search trước.'}
              </p>
              <label className={`font-bold px-6 py-3 rounded-xl text-xs inline-block ${
                targetPaper ? 'bg-blue-600 hover:bg-blue-700 text-white cursor-pointer' : 'bg-slate-300 text-slate-500 cursor-not-allowed'
              }`}>
                Chọn file PDF
                <input
                  type="file"
                  accept=".pdf"
                  className="hidden"
                  disabled={!targetPaper}
                  onChange={handleFileUpload}
                />
              </label>
            </>
          )}
        </div>
      </div>

      <form onSubmit={handleAddUrl} className={`p-5 rounded-2xl border flex gap-3 items-center ${darkMode ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'}`}>
        <Link className="w-5 h-5 text-slate-400 shrink-0" />
        <input
          type="text"
          value={pastedUrl}
          onChange={(event) => setPastedUrl(event.target.value)}
          placeholder="URL/DOI import sẽ được hỗ trợ khi có provenance parser tương ứng..."
          className={`flex-1 border-none bg-transparent text-sm focus:outline-none ${darkMode ? 'text-white' : 'text-slate-900'}`}
        />
        <button type="submit" className="px-4 py-2 rounded-xl text-xs font-bold bg-slate-200 dark:bg-slate-800 text-slate-500">
          Chưa hỗ trợ
        </button>
      </form>

      <div className={`p-6 md:p-8 rounded-3xl border space-y-5 ${darkMode ? 'bg-slate-900 border-slate-800 text-slate-200' : 'bg-white border-slate-200'}`}>
        <div className="flex items-center justify-between border-b pb-4 border-slate-100 dark:border-slate-800">
          <h3 className="font-bold text-base flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-600" />
            <span>Paper đã có provenance ({workspacePapers.length})</span>
          </h3>
        </div>

        {selectedPapers.length > 0 && (
          <div className="grid gap-2">
            {selectedPapers.map((paper) => (
              <div key={paper.id} className="flex items-center justify-between gap-3 text-xs p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60">
                <span className="truncate font-medium">{paper.title}</span>
                {uploadedIds.has(paper.id) ? (
                  <span className="flex items-center gap-1 text-emerald-600 font-bold shrink-0">
                    <CheckCircle2 className="w-4 h-4" /> Đã ingest
                  </span>
                ) : (
                  <span className="text-amber-600 font-bold shrink-0">Chưa có PDF</span>
                )}
              </div>
            ))}
          </div>
        )}

        {workspacePapers.map((paper) => (
          <div key={paper.id} className={`p-4 rounded-2xl border flex items-center justify-between gap-4 text-sm ${darkMode ? 'bg-slate-800/60 border-slate-700' : 'bg-slate-50 border-slate-200'}`}>
            <div className="min-w-0">
              <p className="font-bold truncate">{paper.title}</p>
              <p className="text-xs text-slate-500 mt-1">
                {paper.totalPages ?? '?'} trang • {paper.totalChunks ?? '?'} chunks • Paper ID {paper.id}
              </p>
            </div>
            <button onClick={() => removeFile(paper.id)} className="p-2 text-slate-400 hover:text-red-500" title="Bỏ khỏi workspace">
              <Trash2 className="w-5 h-5" />
            </button>
          </div>
        ))}
      </div>

      {workspacePapers.length > 0 && (
        <div className="text-center">
          <button
            onClick={() => setActiveTab('synthesis')}
            className="bg-blue-600 hover:bg-blue-700 text-white font-bold px-8 py-4 rounded-2xl text-sm inline-flex items-center gap-2 shadow-xl transition-all"
          >
            <Sparkles className="w-5 h-5 text-amber-300" />
            <span>Sang Evidence-first Synthesis →</span>
          </button>
        </div>
      )}
    </div>
  );
}
