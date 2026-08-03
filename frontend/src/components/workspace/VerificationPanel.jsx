import React from 'react';
import { ShieldCheck, ExternalLink } from 'lucide-react';

export default function VerificationPanel({ activeCitation }) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4 sticky top-20">
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-emerald-600" />
          <h3 className="font-bold text-slate-900 text-sm">Source Verification Panel</h3>
        </div>
        <span className="text-[10px] font-bold bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full">
          Zero-Hallucination
        </span>
      </div>

      {activeCitation ? (
        <div className="space-y-4 text-xs">
          <div>
            <span className="font-mono text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
              Selected Citation: {activeCitation.id}
            </span>
            <h4 className="font-bold text-slate-900 text-sm mt-2 leading-snug">
              {activeCitation.title}
            </h4>
          </div>

          <div className="space-y-1 text-slate-600">
            <p><strong>Authors:</strong> {activeCitation.authors}</p>
            <p><strong>Source:</strong> {activeCitation.journal} ({activeCitation.year})</p>
            <p><strong>DOI:</strong> <a href={activeCitation.url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">{activeCitation.doi}</a></p>
          </div>

          {/* Highlighted Abstract Snippet */}
          <div className="space-y-2">
            <h5 className="font-bold text-slate-800 text-xs">Full Abstract Grounding:</h5>
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl leading-relaxed text-slate-700 text-xs">
              {activeCitation.abstract}
            </div>
          </div>

          <a
            href={activeCitation.url}
            target="_blank"
            rel="noreferrer"
            className="w-full flex items-center justify-center gap-2 py-2.5 bg-slate-900 hover:bg-slate-800 text-white rounded-xl font-bold transition-all text-xs"
          >
            <ExternalLink className="w-4 h-4" />
            <span>Download Full Paper PDF (Publisher Source)</span>
          </a>
        </div>
      ) : (
        <p className="text-slate-400 text-xs italic">
          Click a citation tag like [1] in the chat to inspect its ground truth abstract.
        </p>
      )}
    </div>
  );
}
