import React, { useMemo, useState, useEffect, useRef } from 'react';
import { ShieldCheck, X } from 'lucide-react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/TextLayer.css';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import { useLanguage } from '../../contexts/LanguageContext';

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

import { API_BASE } from '../../utils/apiConfig';

export default function VerificationPanel({ activeCitation, onClose, darkMode }) {
  const { t } = useLanguage();
  const [rects, setRects] = useState([]);
  const [loadingCoords, setLoadingCoords] = useState(false);
  const pageContainerRef = useRef(null);

  useEffect(() => {
    if (rects.length > 0 && pageContainerRef.current) {
      setTimeout(() => {
        const firstHighlight = pageContainerRef.current.querySelector('.pdf-highlight-rect');
        if (firstHighlight) {
          firstHighlight.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }, 500);
    }
  }, [rects]);

  const pdfUrl = useMemo(() => {
    if (!activeCitation?.filename) return null;
    return `${API_BASE}/workspace/uploads/papers/${activeCitation.filename}`;
  }, [activeCitation]);

  const pageNumber = useMemo(() => {
    return parseInt(activeCitation?.source_page_display || 1, 10);
  }, [activeCitation]);

  useEffect(() => {
    let active = true;
    if (activeCitation?.filename && activeCitation?.quoted_snippet) {
      setLoadingCoords(true);
      fetch(`${API_BASE}/workspace/evidence-coords`, {
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

  const pages = useMemo(() => {
    if (rects.length === 0) return [pageNumber];
    const uniquePages = [...new Set(rects.map(r => r.page))].sort((a, b) => a - b);
    return uniquePages.length > 0 ? uniquePages : [pageNumber];
  }, [rects, pageNumber]);

  const [pdfWidth, setPdfWidth] = useState(320);
  const pdfWrapperRef = useRef(null);

  useEffect(() => {
    if (!pdfWrapperRef.current) return;
    const observer = new ResizeObserver(entries => {
      for (let entry of entries) {
        setPdfWidth(Math.max(280, entry.contentRect.width - 32));
      }
    });
    observer.observe(pdfWrapperRef.current);
    return () => observer.disconnect();
  }, [pdfUrl, pages]);

  return (
    <div className="flex flex-col h-full w-full">
      <div className={`flex items-center justify-between px-5 h-[56px] border-b shrink-0 ${'border-slate-100 dark:border-slate-800'}`}>
        <div className="flex items-center gap-2 overflow-hidden mr-2">
          <ShieldCheck className="w-4 h-4 shrink-0 text-emerald-500" />
          <h3 className={`font-bold text-[14px] truncate ${'text-slate-700 dark:text-slate-200'}`} title={t('verification.title')}>{t('verification.title')}</h3>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-[10px] font-bold bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 px-2 py-0.5 rounded border border-emerald-200 dark:border-emerald-800">
            {t('verification.grounded_evidence')}
          </span>
          {onClose && (
            <button 
              onClick={onClose}
              className="p-1 rounded-md hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-500 transition-colors shrink-0"
              title={t('verification.close')}
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 flex flex-col min-h-0 overflow-y-auto p-5">
      {activeCitation ? (
        <div className="flex flex-col flex-1 min-h-0 space-y-4 text-sm">
          <div className="shrink-0 space-y-3">
            <div>
              <span className={`font-mono text-[11px] px-2 py-0.5 rounded font-bold ${'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'}`}>
                {activeCitation.marker_display}
              </span>
              <h4 className={`font-bold text-[14px] mt-1.5 leading-snug line-clamp-2 ${'text-slate-800 dark:text-white'}`} title={activeCitation.title}>
                {activeCitation.title}
              </h4>
            </div>

            <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 font-medium">
              <p><strong>{t('verification.pdf_page')}:</strong> {pages.join(', ')}</p>
              <p><strong>{t('verification.raw_chars')}:</strong> {activeCitation.source_char_start ?? '?'}–{activeCitation.source_char_end ?? '?'}</p>
            </div>
          </div>

          {/* PDF Viewer */}
          {pdfUrl && (
            <div 
              ref={pdfWrapperRef}
              className="flex-1 min-h-0 mt-2 rounded-xl overflow-auto border border-slate-200 dark:border-slate-700 bg-slate-100 dark:bg-slate-950 relative shadow-inner custom-scrollbar"
            >
              <div className="min-w-fit flex justify-center p-2">
                <Document
                  file={pdfUrl}
                  loading={<div className="p-4 text-center text-sm text-slate-500">{t('verification.loading_pdf')}</div>}
                  error={<div className="p-4 text-center text-sm text-red-500">{t('verification.pdf_error')}</div>}
                >
                  <div className="relative flex flex-col gap-4 items-center" ref={pageContainerRef}>
                    {pages.map((pNum) => (
                      <div key={pNum} className="relative shadow-md shrink-0 bg-white">
                        <Page 
                          pageNumber={pNum} 
                          width={pdfWidth}
                          renderTextLayer={true}
                          renderAnnotationLayer={true}
                          loading={<div className="p-4 text-center text-sm text-slate-500">{t('verification.loading_page')}</div>}
                        />
                        
                        {/* Bounding box highlights for THIS page */}
                        {rects.filter(r => r.page === pNum).map((r, i) => (
                          <div 
                            key={`${pNum}-${i}`}
                            className="pdf-highlight-rect"
                            style={{
                              left: `${r.x * 100}%`,
                              top: `${r.y * 100}%`,
                              width: `${r.width * 100}%`,
                              height: `${r.height * 100}%`
                            }}
                          />
                        ))}
                      </div>
                    ))}
                    
                    {/* Missing coords indicator */}
                    {rects.length === 0 && !loadingCoords && (
                      <div className="absolute top-2 left-1/2 -translate-x-1/2 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 text-[10px] px-2 py-1 rounded shadow-sm opacity-90 pointer-events-none whitespace-nowrap">
                        {t('verification.no_coords')}
                      </div>
                    )}
                  </div>
                </Document>
              </div>
            </div>
          )}

            {/* Fallback Text excerpt if no coords */}
            {rects.length === 0 && !loadingCoords && activeCitation.quoted_snippet && (
              <div className="shrink-0 mt-3 p-3 bg-amber-50 dark:bg-slate-900 border border-amber-200 dark:border-slate-700 rounded-lg text-xs shadow-inner">
                <p className="text-amber-800 dark:text-amber-400 font-semibold mb-1 flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3" />
                  Đoạn văn bản trích dẫn (Không tìm thấy tọa độ trên trang {activeCitation.source_page_display ?? 'N/A'})
                </p>
                <p className="italic text-slate-700 dark:text-slate-300">"{activeCitation.quoted_snippet}"</p>
              </div>
            )}
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center">
          <p className="text-slate-400 text-sm italic text-center max-w-[200px]">
            {t('verification.empty_desc')}
          </p>
        </div>
      )}
      </div>
    </div>
  );
}
