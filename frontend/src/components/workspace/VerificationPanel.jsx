import React, { useMemo, useState, useEffect } from 'react';
import { ShieldCheck, Quote } from 'lucide-react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/TextLayer.css';
import 'react-pdf/dist/Page/AnnotationLayer.css';

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

export default function VerificationPanel({ activeCitation, darkMode }) {
  const [rects, setRects] = useState([]);
  const [loadingCoords, setLoadingCoords] = useState(false);

  const pdfUrl = useMemo(() => {
    if (!activeCitation?.filename) return null;
    return `http://localhost:8000/api/v1/workspace/uploads/papers/${activeCitation.filename}`;
  }, [activeCitation]);
  
  const pageNumber = useMemo(() => {
    return parseInt(activeCitation?.source_page_display || 1, 10);
  }, [activeCitation]);

  useEffect(() => {
    let active = true;
    if (activeCitation?.filename && activeCitation?.quoted_snippet) {
      setLoadingCoords(true);
      fetch('http://localhost:8000/api/v1/workspace/evidence-coords', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: activeCitation.filename,
          page: pageNumber,
          snippet: activeCitation.quoted_snippet
        })
      })
      .then(r => r.json())
      .then(data => {
        if (active) {
          setRects(data.rects || []);
          setLoadingCoords(false);
        }
      })
      .catch(e => {
        console.error(e);
        if (active) {
          setRects([]);
          setLoadingCoords(false);
        }
      });
    } else {
      setRects([]);
    }
    return () => { active = false; };
  }, [activeCitation, pageNumber]);

  return (
    <div className={`p-6 rounded-3xl border transition-colors flex flex-col space-y-5 sticky top-24 shadow-sm h-[calc(100vh-8rem)] overflow-hidden ${
      darkMode ? 'bg-slate-900 border-slate-800 text-slate-200' : 'bg-white border-slate-200 text-slate-800'
    }`}>
      <div className={`flex items-center justify-between border-b pb-4 shrink-0 ${darkMode ? 'border-slate-800' : 'border-slate-100'}`}>
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-6 h-6 text-emerald-500" />
          <h3 className="font-bold text-base">Xác minh nguồn gốc</h3>
        </div>
        <span className="text-xs font-bold bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 px-3 py-1 rounded-full border border-emerald-200 dark:border-emerald-800">
          Grounded evidence
        </span>
      </div>

      {activeCitation ? (
        <div className="flex flex-col flex-1 min-h-0 space-y-4 text-sm">
          <div className="shrink-0 space-y-3">
            <div>
              <span className={`font-mono text-xs px-2.5 py-1 rounded-md font-bold ${darkMode ? 'bg-slate-800 text-slate-300' : 'bg-slate-100 text-slate-700'}`}>
                {activeCitation.marker_display}
              </span>
              <h4 className={`font-extrabold text-base mt-2 leading-snug line-clamp-2 ${darkMode ? 'text-white' : 'text-slate-900'}`} title={activeCitation.title}>
                {activeCitation.title}
              </h4>
            </div>

            <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 font-medium">
              <p><strong>Trang PDF:</strong> {activeCitation.source_page_display ?? 'N/A'}</p>
              <p><strong>Raw chars:</strong> {activeCitation.source_char_start ?? '?'}–{activeCitation.source_char_end ?? '?'}</p>
            </div>
          </div>

          <div className="shrink-0 space-y-2">
            <h5 className="font-bold text-xs flex items-center gap-1.5 text-slate-800 dark:text-slate-200">
              <Quote className="w-4 h-4 text-blue-600" />
              Evidence nguyên văn đã grounding
            </h5>
            <div className={`p-3 rounded-xl leading-relaxed text-xs border max-h-24 overflow-y-auto custom-scrollbar ${
              darkMode ? 'bg-slate-800 border-slate-700 text-slate-300' : 'bg-slate-50 border-slate-200 text-slate-700'
            }`}>
              {activeCitation.quoted_snippet || 'Không có snippet.'}
            </div>
          </div>

          {/* PDF Viewer */}
          {pdfUrl && (
            <div className="flex-1 min-h-0 mt-2 rounded-xl overflow-auto border border-slate-200 dark:border-slate-700 bg-slate-100 dark:bg-slate-950 relative shadow-inner custom-scrollbar">
              <div className="min-w-fit flex justify-center p-4">
                <Document
                  file={pdfUrl}
                  loading={<div className="p-4 text-center text-sm text-slate-500">Đang tải PDF...</div>}
                  error={<div className="p-4 text-center text-sm text-red-500">Lỗi không thể tải PDF.</div>}
                >
                  <div className="relative shadow-md">
                    <Page 
                      pageNumber={pageNumber} 
                      width={450}
                      renderTextLayer={true}
                      renderAnnotationLayer={true}
                      loading={<div className="p-4 text-center text-sm text-slate-500">Đang tải trang...</div>}
                    />
                    
                    {/* Bounding box highlights */}
                    {rects.map((r, i) => (
                      <div 
                        key={i}
                        className="absolute bg-yellow-400/50 dark:bg-yellow-400/40 mix-blend-multiply dark:mix-blend-screen pointer-events-none rounded-[2px]"
                        style={{
                          left: `${r.x * 100}%`,
                          top: `${r.y * 100}%`,
                          width: `${r.width * 100}%`,
                          height: `${r.height * 100}%`
                        }}
                      />
                    ))}
                    
                    {/* Missing coords indicator */}
                    {rects.length === 0 && !loadingCoords && (
                      <div className="absolute top-2 left-1/2 -translate-x-1/2 bg-red-100 text-red-700 text-[10px] px-2 py-1 rounded shadow-sm opacity-80 pointer-events-none whitespace-nowrap">
                        Không thể tìm toạ độ chính xác cho đoạn trích dẫn.
                      </div>
                    )}
                  </div>
                </Document>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center">
          <p className="text-slate-400 text-sm italic text-center max-w-[200px]">
            Chạy RAG query rồi click marker [1], [2] để xem PDF tại đúng trang chứa evidence.
          </p>
        </div>
      )}
    </div>
  );
}
