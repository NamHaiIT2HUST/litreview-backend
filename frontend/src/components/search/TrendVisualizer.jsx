import React from 'react';
import { BarChart3 } from 'lucide-react';

export default function TrendVisualizer({ searchQuery }) {
  const trendData = [
    { year: '2021', count: 20 },
    { year: '2022', count: 45 },
    { year: '2023', count: 120 },
    { year: '2024', count: 280 },
    { year: '2025', count: 85 }
  ];

  return (
    <div className="bg-gradient-to-r from-blue-900 to-indigo-900 rounded-2xl p-5 text-white flex flex-col md:flex-row items-center justify-between gap-4 shadow-lg">
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-blue-400" />
          <h3 className="font-bold text-base">Research Momentum Visualizer</h3>
        </div>
        <p className="text-xs text-blue-200">
          Publication growth for "{searchQuery}" surged 340% between 2023 and 2024.
        </p>
      </div>
      
      {/* Visual Bar Graph */}
      <div className="flex items-end gap-3 h-12 bg-white/10 p-2 rounded-xl border border-white/10">
        {trendData.map((item, idx) => (
          <div key={idx} className="flex flex-col items-center gap-1">
            <div 
              style={{ height: `${(item.count / 280) * 32}px` }} 
              className="w-6 bg-gradient-to-t from-blue-400 to-cyan-300 rounded-t-sm"
            ></div>
            <span className="text-[10px] text-blue-200">{item.year}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
