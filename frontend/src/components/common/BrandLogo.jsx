import React from 'react';
import logoSvg from '../../assets/logo.svg';

/**
 * Reusable Brand Logo component representing the Authentic Origami Emerald symbol
 * with high-end, modern typography designed for academic/research SaaS branding.
 * 
 * Props:
 * - size: 'xs', 'sm', 'md', 'lg', 'xl', '2xl'
 * - withText: boolean (shows 'LitReview' name next to the logo)
 * - withTagline: boolean (shows subtitle under the name)
 * - isEn: boolean (controls language for tagline)
 * - className: custom wrapper class
 * - imgClassName: custom inner image class
 * - onClick: click callback
 */
export default function BrandLogo({
  size = 'md',
  withText = false,
  withTagline = false,
  isEn = false,
  className = '',
  imgClassName = '',
  badgeStyle = false,
  onClick = null,
}) {
  const sizeMap = {
    xs: {
      img: 'h-6 w-auto max-w-[30px]',
      title: 'text-sm font-bold tracking-tight',
      tagline: 'text-[9.5px]',
      gap: 'gap-2',
      dot: 'w-1 h-1 mb-1',
    },
    sm: {
      img: 'h-8 w-auto max-w-[38px]',
      title: 'text-base font-bold tracking-tight',
      tagline: 'text-[10px]',
      gap: 'gap-2.5',
      dot: 'w-1.5 h-1.5 mb-1',
    },
    md: {
      img: 'h-10 sm:h-11 w-auto max-w-[52px]',
      title: 'text-xl sm:text-[22px] font-extrabold tracking-[-0.025em]',
      tagline: 'text-[11px] sm:text-[11.5px]',
      gap: 'gap-3',
      dot: 'w-1.5 h-1.5 mb-1.5',
    },
    lg: {
      img: 'h-13 sm:h-14 w-auto max-w-[66px]',
      title: 'text-2xl sm:text-3xl font-extrabold tracking-[-0.03em]',
      tagline: 'text-xs sm:text-[13px]',
      gap: 'gap-3.5',
      dot: 'w-2 h-2 mb-2',
    },
    xl: {
      img: 'h-16 sm:h-18 w-auto max-w-[86px]',
      title: 'text-3xl sm:text-4xl font-black tracking-[-0.035em]',
      tagline: 'text-sm sm:text-base',
      gap: 'gap-4',
      dot: 'w-2.5 h-2.5 mb-2.5',
    },
    '2xl': {
      img: 'h-24 sm:h-28 w-auto max-w-[130px]',
      title: 'text-4xl sm:text-5xl font-black tracking-[-0.04em]',
      tagline: 'text-base sm:text-lg',
      gap: 'gap-5',
      dot: 'w-3 h-3 mb-3',
    },
  };

  const currentSize = sizeMap[size] || sizeMap.md;

  const logoGraphic = (
    <div className="relative flex items-center justify-center shrink-0">
      {/* Subtle ambient hover back-glow */}
      <div className="absolute inset-0 rounded-full bg-emerald-500/0 group-hover:bg-emerald-500/15 dark:group-hover:bg-emerald-400/20 blur-md transition-all duration-300 pointer-events-none scale-75 group-hover:scale-125" />
      <img
        src={logoSvg}
        alt="LitReview Origami Logo"
        className={`${currentSize.img} relative z-10 object-contain shrink-0 logo-origami transition-all duration-300 ease-[cubic-bezier(0.34,1.56,0.64,1)] group-hover:scale-110 group-hover:-rotate-3 group-hover:-translate-y-0.5 group-active:scale-95 ${imgClassName}`}
      />
    </div>
  );

  if (!withText) {
    return (
      <div className={`inline-flex items-center justify-center select-none cursor-pointer group ${className}`} onClick={onClick}>
        {logoGraphic}
      </div>
    );
  }

  return (
    <div
      className={`inline-flex items-center ${currentSize.gap} cursor-pointer select-none group shrink-0 transition-transform duration-150 active:scale-[0.98] ${className}`}
      onClick={onClick}
    >
      {logoGraphic}
      <div className="flex flex-col justify-center">
        <div className="flex items-baseline leading-none">
          <span className={`font-brand ${currentSize.title} text-slate-900 dark:text-white group-hover:text-slate-950 dark:group-hover:text-emerald-100 transition-colors duration-200`}>
            Lit
          </span>
          <span className={`font-brand ${currentSize.title} font-black text-emerald-600 dark:text-emerald-400 group-hover:text-emerald-500 dark:group-hover:text-emerald-300 ml-px transition-colors duration-200`}>
            Review
          </span>
          <span className={`inline-block ${currentSize.dot} rounded-full bg-emerald-500 group-hover:bg-emerald-400 dark:group-hover:bg-emerald-300 ml-1 shadow-xs shadow-emerald-500/50 group-hover:shadow-md group-hover:shadow-emerald-400/60 transition-all duration-300 group-hover:scale-135 shrink-0`}></span>
        </div>
        {withTagline && (
          <p className={`font-sans font-medium text-slate-500 dark:text-slate-400 group-hover:text-slate-700 dark:group-hover:text-slate-300 ${currentSize.tagline} mt-1 leading-tight tracking-normal whitespace-nowrap transition-colors duration-200`}>
            {isEn ? 'Academic Literature Review Platform' : 'Nền tảng Nghiên cứu & Tổng quan Tài liệu'}
          </p>
        )}
      </div>
    </div>
  );
}
