import React from 'react';

export default function HistoryTab() {
  return (
    <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
      <h2 className="font-bold text-slate-900 text-base">Export & Query History</h2>
      <p className="text-xs text-slate-500">Track all dataset downloads and previous literature review sessions.</p>
      
      <div className="divide-y divide-slate-100 text-xs">
        <div className="py-3 flex items-center justify-between">
          <div>
            <p className="font-bold text-slate-800">LitReview_Dataset_2026-08-03.xlsx</p>
            <p className="text-slate-500">5 Papers exported to Excel format</p>
          </div>
          <span className="px-2 py-1 bg-emerald-100 text-emerald-700 font-bold rounded">Completed</span>
        </div>
        <div className="py-3 flex items-center justify-between">
          <div>
            <p className="font-bold text-slate-800">scopus_dataset_full.csv</p>
            <p className="text-slate-500">550 Scopus & Web of Science records crawled</p>
          </div>
          <span className="px-2 py-1 bg-blue-100 text-blue-700 font-bold rounded">In Vector DB</span>
        </div>
      </div>
    </div>
  );
}
