import React, { useState } from 'react';
import { 
  BarChart2, 
  TrendingUp, 
  PieChart, 
  Table as TableIcon, 
  CheckCircle2, 
  AlertCircle, 
  FileSpreadsheet, 
  BrainCircuit, 
  ChevronRight,
  Database,
  Layers,
  Percent
} from 'lucide-react';

const CHART_COLORS = [
  { bg: 'bg-blue-500', fill: '#3b82f6', text: 'text-blue-500', from: '#3b82f6', to: '#60a5fa' },
  { bg: 'bg-emerald-500', fill: '#10b981', text: 'text-emerald-500', from: '#10b981', to: '#34d399' },
  { bg: 'bg-violet-500', fill: '#8b5cf6', text: 'text-violet-500', from: '#8b5cf6', to: '#a78bfa' },
  { bg: 'bg-amber-500', fill: '#f59e0b', text: 'text-amber-500', from: '#f59e0b', to: '#fbbf24' },
  { bg: 'bg-rose-500', fill: '#f43f5e', text: 'text-rose-500', from: '#f43f5e', to: '#fb7185' },
  { bg: 'bg-cyan-500', fill: '#06b6d4', text: 'text-cyan-500', from: '#06b6d4', to: '#38bdf8' },
  { bg: 'bg-indigo-500', fill: '#6366f1', text: 'text-indigo-500', from: '#6366f1', to: '#818cf8' },
];

/**
 * Interactive SVG Bar Chart
 */
export function SimpleBarChart({ data = [], title = '', xLabel = '', yLabel = '', darkMode = false }) {
  const [hoverIndex, setHoverIndex] = useState(null);

  if (!data || data.length === 0) return null;

  const numericValues = data.map(d => Number(d.value) || 0);
  const maxVal = Math.max(...numericValues, 1);
  const totalVal = numericValues.reduce((a, b) => a + b, 0);

  const chartHeight = 180;
  const paddingBottom = 40;
  const paddingTop = 25;
  const usableHeight = chartHeight - paddingBottom - paddingTop;

  return (
    <div className={`p-4 rounded-2xl border transition-all my-3 ${
      'bg-white border-slate-200/90 shadow-xs dark:bg-slate-900/90 dark:border-slate-800 dark:shadow-md'
    }`}>
      {/* Chart Header */}
      <div className="flex items-center justify-between gap-2 mb-3 pb-2 border-b dark:border-slate-800 border-slate-100">
        <div className="flex items-center gap-2">
          <BarChart2 className="w-4 h-4 text-blue-500" />
          <h4 className="font-bold text-xs text-slate-800 dark:text-slate-100">
            {title || 'Biểu đồ phân bố định lượng'}
          </h4>
        </div>
        <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400">
          {data.length} {data.length === 1 ? 'mục' : 'nhóm/chỉ số'}
        </span>
      </div>

      {/* SVG Container */}
      <div className="relative">
        <div className="flex items-end justify-between gap-2 pt-6 pb-2 h-[190px] px-2">
          {data.map((item, idx) => {
            const val = Number(item.value) || 0;
            const pctHeight = Math.max(Math.round((val / maxVal) * 100), 4);
            const colorObj = CHART_COLORS[idx % CHART_COLORS.length];
            const isHover = hoverIndex === idx;

            return (
              <div 
                key={idx}
                className="flex-1 flex flex-col items-center h-full justify-end group relative cursor-pointer"
                onMouseEnter={() => setHoverIndex(idx)}
                onMouseLeave={() => setHoverIndex(null)}
              >
                {/* Hover Tooltip */}
                {isHover && (
                  <div className="absolute -top-7 z-20 px-2.5 py-1 rounded-md text-[10px] font-bold bg-slate-900 text-white shadow-lg whitespace-nowrap animate-in fade-in duration-100">
                    {item.name}: {val.toLocaleString()}
                  </div>
                )}


                {/* Bar */}
                <div 
                  className={`w-full max-w-[42px] rounded-t-lg transition-all duration-300 ${
                    isHover ? 'brightness-110 scale-y-[1.02]' : ''
                  }`}
                  style={{
                    height: `${pctHeight}%`,
                    background: `linear-gradient(180deg, ${colorObj.to} 0%, ${colorObj.from} 100%)`,
                    boxShadow: isHover ? `0 4px 12px ${colorObj.from}40` : 'none',
                  }}
                />

                {/* Category Label */}
                <div className="mt-2 text-center w-full">
                  <span className={`text-[10.5px] font-medium block truncate ${
                    isHover ? 'font-bold text-blue-500' : 'text-slate-600 dark:text-slate-400'
                  }`} title={item.name}>
                    {item.name}
                  </span>
                  <span className="text-[10px] font-semibold text-slate-400 dark:text-slate-500 block">
                    {val.toLocaleString()}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {(xLabel || yLabel) && (
        <div className="flex justify-between items-center text-[10px] text-slate-400 pt-2 border-t dark:border-slate-800/60 border-slate-100">
          <span>{yLabel && `Trục đứng: ${yLabel}`}</span>
          <span>{xLabel && `Trục ngang: ${xLabel}`}</span>
        </div>
      )}
    </div>
  );
}

/**
 * Interactive SVG Line Trend Chart
 */
export function SimpleLineChart({ data = [], title = '', xLabel = '', yLabel = '', darkMode = false }) {
  const [hoverIndex, setHoverIndex] = useState(null);

  if (!data || data.length === 0) return null;

  const numericValues = data.map(d => Number(d.value) || 0);
  const maxVal = Math.max(...numericValues, 1);
  const minVal = Math.min(...numericValues, 0);
  const range = maxVal - minVal || 1;

  const width = 500;
  const height = 150;
  const paddingX = 35;
  const paddingY = 20;
  const usableW = width - paddingX * 2;
  const usableH = height - paddingY * 2;

  const points = data.map((item, idx) => {
    const x = paddingX + (idx / Math.max(data.length - 1, 1)) * usableW;
    const val = Number(item.value) || 0;
    const y = height - paddingY - ((val - minVal) / range) * usableH;
    return { x, y, val, name: item.name };
  });

  const pathD = points.reduce((acc, pt, idx) => {
    return idx === 0 ? `M ${pt.x} ${pt.y}` : `${acc} L ${pt.x} ${pt.y}`;
  }, '');

  const areaD = `${pathD} L ${points[points.length - 1].x} ${height - paddingY} L ${points[0].x} ${height - paddingY} Z`;

  return (
    <div className={`p-4 rounded-2xl border transition-all my-3 ${
      'bg-white border-slate-200/90 shadow-xs dark:bg-slate-900/90 dark:border-slate-800 dark:shadow-md'
    }`}>
      {/* Header */}
      <div className="flex items-center justify-between gap-2 mb-3 pb-2 border-b dark:border-slate-800 border-slate-100">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-emerald-500" />
          <h4 className="font-bold text-xs text-slate-800 dark:text-slate-100">
            {title || 'Biểu đồ xu hướng tiến trình (Trend Analysis)'}
          </h4>
        </div>
      </div>

      {/* SVG Line */}
      <div className="w-full overflow-x-auto">
        <svg viewBox={`0 0 ${width} ${height + 25}`} className="w-full h-[180px]">
          <defs>
            <linearGradient id="lineGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10b981" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Area Fill */}
          <path d={areaD} fill="url(#lineGrad)" />

          {/* Line Stroke */}
          <path d={pathD} fill="none" stroke="#10b981" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />

          {/* Data Points */}
          {points.map((pt, idx) => {
            const isHover = hoverIndex === idx;
            return (
              <g 
                key={idx} 
                onMouseEnter={() => setHoverIndex(idx)} 
                onMouseLeave={() => setHoverIndex(null)}
                className="cursor-pointer"
              >
                <circle 
                  cx={pt.x} 
                  cy={pt.y} 
                  r={isHover ? 6 : 4} 
                  fill={isHover ? '#34d399' : '#10b981'} 
                  stroke={'#ffffff dark:#0f172a'} 
                  strokeWidth="2"
                  className="transition-all duration-150"
                />

                {/* X Axis Label */}
                <text 
                  x={pt.x} 
                  y={height + 15} 
                  textAnchor="middle" 
                  fontSize="10" 
                  fill={isHover ? '#10b981' : '#64748b dark:#94a3b8'}
                  fontWeight={isHover ? 'bold' : 'normal'}
                >
                  {pt.name}
                </text>

                {/* Value on Hover */}
                {isHover && (
                  <text 
                    x={pt.x} 
                    y={pt.y - 10} 
                    textAnchor="middle" 
                    fontSize="11" 
                    fontWeight="bold" 
                    fill={'#0f172a dark:#ffffff'}
                  >
                    {pt.val}
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}

/**
 * Interactive SVG Donut / Pie Chart
 */
export function SimpleDonutChart({ data = [], title = '', darkMode = false }) {
  const [hoverIndex, setHoverIndex] = useState(null);

  if (!data || data.length === 0) return null;

  const total = data.reduce((sum, item) => sum + (Number(item.value) || 0), 0);
  if (total === 0) return null;

  let cumulativeAngle = 0;
  const radius = 60;
  const innerRadius = 38;
  const cx = 80;
  const cy = 80;

  const slices = data.map((item, idx) => {
    const val = Number(item.value) || 0;
    const angle = (val / total) * 360;
    const startAngle = cumulativeAngle;
    const endAngle = cumulativeAngle + angle;
    cumulativeAngle += angle;

    const radStart = (startAngle - 90) * (Math.PI / 180);
    const radEnd = (endAngle - 90) * (Math.PI / 180);

    const x1 = cx + radius * Math.cos(radStart);
    const y1 = cy + radius * Math.sin(radStart);
    const x2 = cx + radius * Math.cos(radEnd);
    const y2 = cy + radius * Math.sin(radEnd);

    const ix1 = cx + innerRadius * Math.cos(radEnd);
    const iy1 = cy + innerRadius * Math.sin(radEnd);
    const ix2 = cx + innerRadius * Math.cos(radStart);
    const iy2 = cy + innerRadius * Math.sin(radStart);

    const largeArc = angle > 180 ? 1 : 0;
    const pathD = `M ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} L ${ix1} ${iy1} A ${innerRadius} ${innerRadius} 0 ${largeArc} 0 ${ix2} ${iy2} Z`;

    const color = CHART_COLORS[idx % CHART_COLORS.length];
    const pct = Math.round((val / total) * 100);

    return { ...item, pathD, color, pct, val, idx };
  });

  return (
    <div className={`p-4 rounded-2xl border transition-all my-3 ${
      'bg-white border-slate-200/90 shadow-xs dark:bg-slate-900/90 dark:border-slate-800 dark:shadow-md'
    }`}>
      <div className="flex items-center gap-2 mb-3 pb-2 border-b dark:border-slate-800 border-slate-100">
        <PieChart className="w-4 h-4 text-violet-500" />
        <h4 className="font-bold text-xs text-slate-800 dark:text-slate-100">
          {title || 'Phân bố tỷ lệ danh mục'}
        </h4>
      </div>

      <div className="flex flex-col sm:flex-row items-center justify-around gap-6 py-2">
        {/* SVG Donut */}
        <div className="relative w-[160px] h-[160px] shrink-0">
          <svg viewBox="0 0 160 160" className="w-full h-full transform rotate-0">
            {slices.map((slice) => {
              const isHover = hoverIndex === slice.idx;
              return (
                <path
                  key={slice.idx}
                  d={slice.pathD}
                  fill={slice.color.fill}
                  className={`transition-all duration-200 cursor-pointer ${
                    isHover ? 'opacity-100 scale-105 origin-center' : 'opacity-90 hover:opacity-100'
                  }`}
                  onMouseEnter={() => setHoverIndex(slice.idx)}
                  onMouseLeave={() => setHoverIndex(null)}
                />
              );
            })}
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none text-center">
            <span className="text-[10px] text-slate-400 uppercase font-bold">Tổng số</span>
            <span className="text-sm font-extrabold text-slate-800 dark:text-slate-100">{total}</span>
          </div>
        </div>

        {/* Legend */}
        <div className="flex-1 space-y-1.5 w-full">
          {slices.map((slice) => {
            const isHover = hoverIndex === slice.idx;
            return (
              <div 
                key={slice.idx}
                onMouseEnter={() => setHoverIndex(slice.idx)}
                onMouseLeave={() => setHoverIndex(null)}
                className={`flex items-center justify-between p-1.5 rounded-lg text-xs transition-colors cursor-pointer ${
                  isHover ? ('bg-slate-100 font-bold dark:bg-slate-800') : ''
                }`}
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: slice.color.fill }} />
                  <span className="truncate text-slate-700 dark:text-slate-300 text-[11.5px]">{slice.name}</span>
                </div>
                <div className="flex items-center gap-2 font-mono text-[11.5px] text-slate-500 dark:text-slate-400 shrink-0">
                  <span>{slice.val}</span>
                  <span className="font-bold text-slate-800 dark:text-slate-200">({slice.pct}%)</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

/**
 * Key Performance Indicators (KPIs) Cards Grid
 */
export function KPICardsGrid({ kpis = [], darkMode = false }) {
  if (!kpis || kpis.length === 0) return null;

  const sanitizeKpi = (str) => {
    if (!str) return '';
    return String(str);
  };

  return (
    <div className="flex flex-wrap gap-2.5 my-3">
      {kpis.map((kpi, idx) => {
        const color = CHART_COLORS[idx % CHART_COLORS.length];
        return (
          <div 
            key={idx}
            className="flex-1 min-w-[170px] p-3.5 rounded-2xl border transition-all shadow-2xs flex flex-col justify-between bg-white border-slate-200/80 dark:bg-slate-900/70 dark:border-slate-800/80"
          >
            <div className="flex items-center justify-between gap-1 mb-1">
              <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 truncate" title={sanitizeKpi(kpi.label)}>
                {sanitizeKpi(kpi.label)}
              </span>
              <span className={`w-2 h-2 rounded-full ${color.bg}`} />
            </div>

            <div className="text-base font-black text-slate-800 dark:text-slate-100 tracking-tight my-0.5">
              {sanitizeKpi(kpi.value)}
            </div>

            {kpi.subtext && (
              <div className="text-[10px] text-slate-400 dark:text-slate-500 truncate mt-0.5" title={sanitizeKpi(kpi.subtext)}>
                {sanitizeKpi(kpi.subtext)}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

/**
 * Dataset Health & Profiling Card
 */
export function DatasetHealthCard({ profile, filename, darkMode = false, onRunAutoEDA }) {
  if (!profile) return null;

  const hasEmptyCols = profile.completely_empty_cols && profile.completely_empty_cols.length > 0;
  const hasConstCols = profile.constant_cols && profile.constant_cols.length > 0;

  return (
    <div className={`p-4 rounded-2xl border transition-all ${
      'bg-slate-50 border-slate-200 shadow-xs dark:bg-slate-900/80 dark:border-slate-800 dark:shadow-md'
    }`}>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b dark:border-slate-800 border-slate-200">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-blue-100 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400">
            <Database className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-1.5 mb-1">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Cấu trúc Dataset (Data Profile)
              </span>
              <span className="text-[9px] px-1.5 py-0.5 rounded font-mono font-bold bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300 leading-none">
                Pandas Verified
              </span>
            </div>
            <h4 className="font-extrabold text-xs text-slate-800 dark:text-slate-100 flex items-center gap-1.5">
              <span>{filename || 'Tập dữ liệu nghiên cứu'}</span>
            </h4>
            <p className="text-[10.5px] text-slate-500 mt-0.5 font-medium">
              Kích thước: {profile.row_count?.toLocaleString()} dòng · {profile.column_count} cột {profile.duplicate_rows ? `· ${profile.duplicate_rows} dòng trùng` : ''}
            </p>
          </div>
        </div>

        {onRunAutoEDA && (
          <button
            onClick={onRunAutoEDA}
            className="px-3 py-1.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs flex items-center gap-1.5 shadow-sm active:scale-95 transition-all cursor-pointer shrink-0"
          >
            <BrainCircuit className="w-3.5 h-3.5" />
            <span>Auto-EDA (Chuẩn 7 Phần)</span>
          </button>
        )}
      </div>

      {/* Quality Audit Badges */}
      {(hasEmptyCols || hasConstCols) && (
        <div className="mt-3 p-2.5 rounded-xl bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900/50 flex flex-wrap items-center gap-2 text-xs">
          <AlertCircle className="w-4 h-4 text-rose-500 shrink-0" />
          <span className="font-semibold text-rose-700 dark:text-rose-300 text-[11px]">
            Cần loại bỏ trước khi mô hình hóa (DROP):
          </span>
          {hasEmptyCols && (
            <span className="px-2 py-0.5 rounded-md font-mono text-[10px] bg-rose-100 dark:bg-rose-900/50 text-rose-700 dark:text-rose-300 font-bold border border-rose-300 dark:border-rose-800">
              {profile.completely_empty_cols.length} cột rỗng 100% ({profile.completely_empty_cols.join(', ')})
            </span>
          )}
          {hasConstCols && (
            <span className="px-2 py-0.5 rounded-md font-mono text-[10px] bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300 font-bold border border-amber-300 dark:border-amber-800">
              {profile.constant_cols.length} cột hằng số 0 ({profile.constant_cols.join(', ')})
            </span>
          )}
        </div>
      )}

      {/* Columns Tag Cloud */}
      {profile.columns && profile.columns.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pt-3">
          {profile.columns.map((c, i) => {
            const is100Empty = profile.completely_empty_cols?.includes(c.name);
            const isConst = profile.constant_cols?.includes(c.name);

            return (
              <span 
                key={i} 
                className={`text-[10px] px-2 py-0.5 rounded-lg border font-mono flex items-center gap-1 ${
                  is100Empty
                    ? 'bg-rose-50 text-rose-700 border-rose-300 dark:bg-rose-950/50 dark:text-rose-300 line-through opacity-80'
                    : isConst
                    ? 'bg-amber-50 text-amber-700 border-amber-300 dark:bg-amber-950/50 dark:text-amber-300'
                    : c.type === 'numeric' 
                    ? 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-900' 
                    : c.type === 'datetime'
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-900'
                    : 'bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700'
                }`}
                title={`${c.name} (${c.type}): ${c.null_count} ô rỗng (${c.null_pct}%), ${c.unique_count} giá trị phân biệt`}
              >
                <span className="font-semibold">{c.name}</span>
                <span className="opacity-60 text-[9px]">
                  {is100Empty ? '[100% NaN - DROP]' : isConst ? '[Hằng số - DROP]' : `[${c.type}]`}
                </span>
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
}

/**
 * Universal Chart Renderer
 */
export default function DynamicDataChart({ chart, darkMode }) {
  if (!chart || !chart.data || chart.data.length === 0) return null;

  switch (chart.type) {
    case 'line':
      return <SimpleLineChart data={chart.data} title={chart.title} xLabel={chart.x_label} yLabel={chart.y_label} darkMode={darkMode} />;
    case 'donut':
    case 'pie':
      return <SimpleDonutChart data={chart.data} title={chart.title} darkMode={darkMode} />;
    case 'bar':
    default:
      return <SimpleBarChart data={chart.data} title={chart.title} xLabel={chart.x_label} yLabel={chart.y_label} darkMode={darkMode} />;
  }
}
