import React from 'react';
import { Award, ExternalLink, FileText } from 'lucide-react';

export default function PaperTable({ papers, selectedPaperIds, toggleSelectPaper }) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200 text-xs font-bold text-slate-600 uppercase tracking-wider">
              <th className="p-4 w-12 text-center">Select</th>
              <th className="p-4">Paper Title & Source</th>
              <th className="p-4 w-28">LitScore 🎖️</th>
              <th className="p-4">Authors & Journal</th>
              <th className="p-4 w-24">Citations</th>
              <th className="p-4">TL;DR AI Summary</th>
              <th className="p-4 w-28 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-xs">
            {papers.map((paper) => {
              const isSelected = selectedPaperIds.includes(paper.id);
              return (
                <tr 
                  key={paper.id}
                  className={`hover:bg-slate-50 transition-colors ${isSelected ? 'bg-blue-50/50' : ''}`}
                >
                  <td className="p-4 text-center">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleSelectPaper(paper.id)}
                      className="w-4 h-4 rounded text-blue-600 focus:ring-blue-500 border-slate-300 cursor-pointer"
                    />
                  </td>
                  <td className="p-4">
                    <div className="space-y-1">
                      <a
                        href={paper.url}
                        target="_blank"
                        rel="noreferrer"
                        className="font-bold text-slate-900 hover:text-blue-600 text-sm line-clamp-2 flex items-center gap-1.5"
                      >
                        <span>{paper.title}</span>
                        <ExternalLink className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                      </a>
                      <div className="flex items-center gap-2 text-[11px] text-slate-500">
                        <span className="font-mono bg-slate-100 px-1.5 py-0.5 rounded text-slate-600">{paper.id}</span>
                        <span>DOI: {paper.doi}</span>
                      </div>
                    </div>
                  </td>
                  <td className="p-4">
                    <span className="badge-litscore text-xs">
                      <Award className="w-3.5 h-3.5 text-amber-600" />
                      <span>{paper.litScore}/100</span>
                    </span>
                  </td>
                  <td className="p-4">
                    <div className="space-y-0.5">
                      <p className="font-medium text-slate-800 line-clamp-1">{paper.authors}</p>
                      <p className="text-slate-500 italic">{paper.journal} ({paper.year})</p>
                    </div>
                  </td>
                  <td className="p-4">
                    <span className="font-bold text-slate-900 bg-slate-100 px-2 py-1 rounded-md">
                      {paper.citations.toLocaleString()}
                    </span>
                  </td>
                  <td className="p-4 max-w-xs">
                    <p className="text-slate-600 text-[11px] line-clamp-2 bg-amber-50/60 p-2 rounded-lg border border-amber-100">
                      {paper.tldr}
                    </p>
                  </td>
                  <td className="p-4 text-right">
                    <a
                      href={paper.url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-lg transition-all"
                    >
                      <FileText className="w-3.5 h-3.5" />
                      <span>PDF Link</span>
                    </a>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
