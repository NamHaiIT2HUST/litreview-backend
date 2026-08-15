import React from 'react';
import { ExternalLink, Quote, ShieldCheck, Sparkles, X } from 'lucide-react';

function popupPosition(anchor) {
  if (!anchor || typeof window === 'undefined') return { top: 96, right: 24 };
  const width = 390;
  const margin = 16;
  const left = anchor.right + width + margin <= window.innerWidth
    ? anchor.right + 10
    : Math.max(margin, anchor.left - width - 10);
  const top = Math.min(Math.max(margin, anchor.top - 18), window.innerHeight - 520);
  return { left, top: Math.max(margin, top), width };
}

export default function VerificationPanel({ activeCitation, darkMode, onClose }) {
  if (!activeCitation) return null;
  const isSentence = activeCitation.kind === 'sentence';
  const citations = isSentence ? activeCitation.citations : [activeCitation];
  const isDiscourse = isSentence && activeCitation.sentence_type === 'discourse';

  return (
    <div
      role="dialog"
      aria-label="Xác minh nguồn câu"
      style={popupPosition(activeCitation.anchor)}
      className={`fixed z-[80] max-h-[72vh] overflow-y-auto p-5 rounded-2xl border shadow-2xl ${darkMode ? 'bg-slate-900 border-slate-700 text-slate-200' : 'bg-white border-slate-200 text-slate-800'}`}
    >
      <div className={`flex items-start justify-between gap-3 border-b pb-3 mb-4 ${darkMode ? 'border-slate-800' : 'border-slate-100'}`}>
        <div className="flex items-center gap-2">
          {isDiscourse ? <Sparkles className="w-5 h-5 text-violet-500" /> : <ShieldCheck className="w-5 h-5 text-emerald-500" />}
          <div>
            <h3 className="font-bold text-sm">{isDiscourse ? 'Câu nối do AI tạo' : 'Nguồn xác minh câu'}</h3>
            <p className="text-[10px] text-slate-500">{isDiscourse ? 'Không thêm dữ kiện mới' : `${citations.length} nguồn bằng chứng`}</p>
          </div>
        </div>
        <button type="button" onClick={onClose} className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800" aria-label="Đóng"><X className="w-4 h-4" /></button>
      </div>

      {isSentence && <p className="text-xs leading-5 font-medium mb-4 p-3 rounded-xl bg-blue-50 dark:bg-blue-950/30">{activeCitation.sentence}</p>}

      {isDiscourse ? (
        <div className="text-xs leading-5 text-slate-500">
          Đây là câu chuyển ý/tổng hợp do AI viết từ các claim đã kiểm chứng. Câu này không được dùng để đưa thêm một fact mới.
          {activeCitation.claim_ids?.length > 0 && <p className="mt-2 font-mono text-[10px]">Truy vết claim: {activeCitation.claim_ids.join(', ')}</p>}
        </div>
      ) : citations.map((citation, index) => (
        <article key={citation.id || index} className="mb-5 last:mb-0 text-xs">
          <div className="flex gap-2 items-center mb-2">
            <span className="font-mono font-bold text-blue-600">{citation.marker_display || `[${index + 1}]`}</span>
            <h4 className="font-extrabold leading-snug">{citation.title}</h4>
          </div>
          <p className="text-slate-500 mb-2">{citation.authors}{citation.year ? ` · ${citation.year}` : ''}{citation.source_page_display ? ` · trang ${citation.source_page_display}` : ''}</p>
          <div className={`p-3 rounded-xl leading-5 border ${darkMode ? 'bg-slate-800 border-slate-700' : 'bg-slate-50 border-slate-200'}`}>
            <Quote className="inline w-3.5 h-3.5 mr-1 text-blue-500" />
            {citation.quoted_snippet || 'Không có đoạn trích nguồn.'}
          </div>
          {citation.url && citation.url !== '#' && <a href={citation.url} target="_blank" rel="noreferrer" className="inline-flex mt-2 items-center gap-1 text-blue-600 font-bold"><ExternalLink className="w-3.5 h-3.5" />Mở paper</a>}
        </article>
      ))}
    </div>
  );
}
