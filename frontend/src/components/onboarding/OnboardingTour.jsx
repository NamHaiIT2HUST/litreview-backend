import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Sparkles, ArrowRight, ArrowLeft, X, Check, BookOpen,
  Target, Search, Layers, Download, HelpCircle, Compass
} from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';

export const TOUR_STEPS = [
  {
    id: 'overview-center',
    tab: 'overview',
    targetSelector: '#tour-dashboard-hero',
    fallbackSelector: '.app-content',
    icon: Compass,
    titleKey: 'tour.step1_title',
    descKey: 'tour.step1_desc',
    placement: 'bottom',
    badge: 'STAGE 01'
  },
  {
    id: 'sidebar-workflow',
    tab: 'overview',
    targetSelector: '#tour-sidebar-workflow',
    fallbackSelector: '.app-sidebar',
    icon: BookOpen,
    titleKey: 'tour.step2_title',
    descKey: 'tour.step2_desc',
    placement: 'right',
    badge: 'STAGE 02'
  },
  {
    id: 'setup-pico',
    tab: 'setup',
    targetSelector: '#tour-setup-pico',
    fallbackSelector: '.app-content',
    icon: Target,
    titleKey: 'tour.step3_title',
    descKey: 'tour.step3_desc',
    placement: 'bottom',
    badge: 'STAGE 03'
  },
  {
    id: 'search-discovery',
    tab: 'search',
    targetSelector: '#tour-search-bar',
    fallbackSelector: '.app-content',
    icon: Search,
    titleKey: 'tour.step4_title',
    descKey: 'tour.step4_desc',
    placement: 'bottom',
    badge: 'STAGE 04'
  },
  {
    id: 'workspace-rag',
    tab: 'synthesis',
    targetSelector: '#tour-workspace-tabs',
    fallbackSelector: '.app-content',
    icon: Layers,
    titleKey: 'tour.step5_title',
    descKey: 'tour.step5_desc',
    placement: 'bottom',
    badge: 'STAGE 05'
  },
  {
    id: 'export-publish',
    tab: 'export',
    targetSelector: '#tour-export-formats',
    fallbackSelector: '.app-content',
    icon: Download,
    titleKey: 'tour.step6_title',
    descKey: 'tour.step6_desc',
    placement: 'top',
    badge: 'STAGE 06'
  },
];

export default function OnboardingTour({
  isOpen,
  onClose,
  activeTab,
  setActiveTab,
}) {
  const { t, language } = useLanguage();
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [targetRect, setTargetRect] = useState(null);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const tooltipRef = useRef(null);

  const currentStep = TOUR_STEPS[currentStepIndex] || TOUR_STEPS[0];
  const totalSteps = TOUR_STEPS.length;
  const isFirstStep = currentStepIndex === 0;
  const isLastStep = currentStepIndex === totalSteps - 1;

  // Measure target element position
  const updateTargetRect = useCallback(() => {
    if (!isOpen) return;
    
    let el = document.querySelector(currentStep.targetSelector);
    if (!el && currentStep.fallbackSelector) {
      el = document.querySelector(currentStep.fallbackSelector);
    }

    if (el) {
      const rect = el.getBoundingClientRect();
      // Scroll into view if outside viewport
      const isInViewport =
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth);

      if (!isInViewport) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        setTimeout(() => {
          const updated = el.getBoundingClientRect();
          setTargetRect({
            top: updated.top,
            left: updated.left,
            width: updated.width,
            height: updated.height,
            right: updated.right,
            bottom: updated.bottom,
          });
        }, 300);
      } else {
        setTargetRect({
          top: rect.top,
          left: rect.left,
          width: rect.width,
          height: rect.height,
          right: rect.right,
          bottom: rect.bottom,
        });
      }
    } else {
      // Fallback center box
      const w = Math.min(window.innerWidth * 0.8, 640);
      const h = Math.min(window.innerHeight * 0.5, 360);
      setTargetRect({
        top: (window.innerHeight - h) / 2,
        left: (window.innerWidth - w) / 2,
        width: w,
        height: h,
        right: (window.innerWidth + w) / 2,
        bottom: (window.innerHeight + h) / 2,
      });
    }
  }, [isOpen, currentStep]);

  // Ensure active tab matches current step
  useEffect(() => {
    if (!isOpen) return;
    if (currentStep.tab && activeTab !== currentStep.tab) {
      setIsTransitioning(true);
      setActiveTab(currentStep.tab);
      const timer = setTimeout(() => {
        setIsTransitioning(false);
        updateTargetRect();
      }, 400);
      return () => clearTimeout(timer);
    } else {
      const timer = setTimeout(updateTargetRect, 150);
      return () => clearTimeout(timer);
    }
  }, [isOpen, currentStepIndex, currentStep.tab, activeTab, setActiveTab, updateTargetRect]);

  // Window resize & scroll listener
  useEffect(() => {
    if (!isOpen) return;
    const handleResizeOrScroll = () => {
      requestAnimationFrame(updateTargetRect);
    };

    window.addEventListener('resize', handleResizeOrScroll);
    window.addEventListener('scroll', handleResizeOrScroll, true);
    return () => {
      window.removeEventListener('resize', handleResizeOrScroll);
      window.removeEventListener('scroll', handleResizeOrScroll, true);
    };
  }, [isOpen, updateTargetRect]);

  // Keyboard navigation
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        handleSkip();
      } else if (e.key === 'ArrowRight' || e.key === 'Enter') {
        handleNext();
      } else if (e.key === 'ArrowLeft') {
        handleBack();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, currentStepIndex]);

  const handleNext = () => {
    if (isLastStep) {
      handleFinish();
    } else {
      setCurrentStepIndex(prev => prev + 1);
    }
  };

  const handleBack = () => {
    if (!isFirstStep) {
      setCurrentStepIndex(prev => prev - 1);
    }
  };

  const handleSkip = () => {
    localStorage.setItem('litreview_tour_completed', 'true');
    onClose();
  };

  const handleFinish = () => {
    localStorage.setItem('litreview_tour_completed', 'true');
    onClose();
  };

  if (!isOpen || !targetRect) return null;

  // Calculate Tooltip Position
  const padding = 12;
  const tooltipWidth = Math.min(380, window.innerWidth - 32);
  let tooltipStyle = {};

  const placement = currentStep.placement || 'bottom';

  if (placement === 'bottom') {
    const top = targetRect.bottom + padding;
    const left = Math.max(16, Math.min(window.innerWidth - tooltipWidth - 16, targetRect.left + targetRect.width / 2 - tooltipWidth / 2));
    tooltipStyle = { top: `${Math.min(window.innerHeight - 280, top)}px`, left: `${left}px`, width: `${tooltipWidth}px` };
  } else if (placement === 'top') {
    const top = targetRect.top - 240 - padding;
    const left = Math.max(16, Math.min(window.innerWidth - tooltipWidth - 16, targetRect.left + targetRect.width / 2 - tooltipWidth / 2));
    tooltipStyle = { top: `${Math.max(16, top)}px`, left: `${left}px`, width: `${tooltipWidth}px` };
  } else if (placement === 'right') {
    const top = Math.max(16, Math.min(window.innerHeight - 280, targetRect.top + 20));
    const left = Math.min(window.innerWidth - tooltipWidth - 16, targetRect.right + padding);
    tooltipStyle = { top: `${top}px`, left: `${left}px`, width: `${tooltipWidth}px` };
  } else {
    // left
    const top = Math.max(16, Math.min(window.innerHeight - 280, targetRect.top + 20));
    const left = Math.max(16, targetRect.left - tooltipWidth - padding);
    tooltipStyle = { top: `${top}px`, left: `${left}px`, width: `${tooltipWidth}px` };
  }

  const StepIcon = currentStep.icon || Sparkles;

  // SVG mask cutout coordinates with padding
  const maskPad = 6;
  const maskX = Math.max(0, targetRect.left - maskPad);
  const maskY = Math.max(0, targetRect.top - maskPad);
  const maskW = targetRect.width + maskPad * 2;
  const maskH = targetRect.height + maskPad * 2;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden pointer-events-auto">
      
      {/* ── 1. SVG Spotlight Dark Mask Cutout ─────────────────────────── */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none transition-all duration-300">
        <defs>
          <mask id="tour-spotlight-mask">
            <rect x="0" y="0" width="100%" height="100%" fill="white" />
            <rect
              x={maskX}
              y={maskY}
              width={maskW}
              height={maskH}
              rx="14"
              ry="14"
              fill="black"
            />
          </mask>
        </defs>
        <rect
          x="0"
          y="0"
          width="100%"
          height="100%"
          fill="rgba(15, 23, 42, 0.65)"
          mask="url(#tour-spotlight-mask)"
        />
      </svg>

      {/* Click outside to skip / backdrop trap */}
      <div
        className="absolute inset-0 z-10 cursor-default"
        onClick={handleSkip}
      />

      {/* ── 2. Glowing Focus Frame around Target Element ───────────────── */}
      <div
        style={{
          position: 'absolute',
          top: `${maskY}px`,
          left: `${maskX}px`,
          width: `${maskW}px`,
          height: `${maskH}px`,
          pointerEvents: 'none',
          transition: 'all 0.35s cubic-bezier(0.16, 1, 0.3, 1)',
        }}
        className="z-20 rounded-2xl ring-2 ring-primary-500 shadow-[0_0_24px_rgba(99,102,241,0.6)]"
      >
        {/* Pulsing Beacon in Top-Left Corner of Target */}
        <div className="absolute -top-2 -left-2 flex items-center justify-center">
          <span className="w-5 h-5 rounded-full bg-primary-500/40 animate-ping absolute" />
          <span className="w-3.5 h-3.5 rounded-full bg-primary-600 border-2 border-white shadow-md relative" />
        </div>
      </div>

      {/* ── 3. Floating Tooltip Coach Mark Card ───────────────────────── */}
      <div
        ref={tooltipRef}
        style={tooltipStyle}
        onClick={(e) => e.stopPropagation()}
        className="fixed z-30 transition-all duration-300 animate-slide-up"
      >
        <div className="card p-5 sm:p-6 shadow-2xl border-primary-500/50 bg-white/95 dark:bg-surface-900/95 backdrop-blur-2xl space-y-4 ring-1 ring-primary-500/30 rounded-2xl">
          
          {/* Header Bar */}
          <div className="flex items-center justify-between gap-3 pb-2 border-b border-surface-100 dark:border-surface-800 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-primary-50 dark:bg-primary-950/70 border border-primary-200 dark:border-primary-800 text-primary-600 dark:text-primary-400 flex items-center justify-center font-bold">
                <StepIcon className="w-4 h-4" />
              </div>
              <span className="badge badge-primary text-[9.5px] font-mono font-bold uppercase tracking-wider">
                {currentStep.badge}
              </span>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-[11px] font-mono font-semibold text-surface-500 dark:text-surface-400">
                {t('tour.step_counter', { current: currentStepIndex + 1, total: totalSteps })}
              </span>
              <button
                onClick={handleSkip}
                className="p-1 rounded-lg text-surface-400 hover:text-surface-700 dark:hover:text-surface-200 hover:bg-surface-100 dark:hover:bg-surface-800 transition-colors cursor-pointer"
                title={t('tour.btn_skip')}
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Title & Description */}
          <div className="space-y-1.5">
            <h3 className="font-display font-bold text-base text-surface-900 dark:text-white leading-snug">
              {t(currentStep.titleKey)}
            </h3>
            <p className="text-xs text-surface-600 dark:text-surface-300 leading-relaxed">
              {t(currentStep.descKey)}
            </p>
          </div>

          {/* Progress Indicators */}
          <div className="flex items-center gap-1.5 pt-1">
            {TOUR_STEPS.map((_, idx) => (
              <div
                key={idx}
                className={`h-1.5 rounded-full transition-all duration-300 ${
                  idx === currentStepIndex
                    ? 'w-6 bg-primary-600'
                    : idx < currentStepIndex
                    ? 'w-2 bg-primary-300 dark:bg-primary-800'
                    : 'w-2 bg-surface-200 dark:bg-surface-700'
                }`}
              />
            ))}
          </div>

          {/* Action Button Controls */}
          <div className="flex items-center justify-between gap-2 pt-2 border-t border-surface-100 dark:border-surface-800">
            
            {/* Skip / Dismiss */}
            <button
              onClick={handleSkip}
              className="text-xs font-semibold text-surface-400 hover:text-surface-700 dark:hover:text-surface-200 transition-colors px-1 cursor-pointer"
            >
              {t('tour.btn_skip')}
            </button>

            <div className="flex items-center gap-2">
              {/* Back Button */}
              {!isFirstStep && (
                <button
                  onClick={handleBack}
                  className="btn btn-secondary btn-sm px-3 flex items-center gap-1.5 cursor-pointer"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>{t('tour.btn_back')}</span>
                </button>
              )}

              {/* Next / Finish Button */}
              <button
                onClick={handleNext}
                className="btn btn-primary btn-sm px-3.5 shadow-primary-sm flex items-center gap-1.5 cursor-pointer font-bold"
              >
                <span>{isLastStep ? t('tour.btn_finish') : t('tour.btn_next')}</span>
                {isLastStep ? <Check className="w-3.5 h-3.5" /> : <ArrowRight className="w-3.5 h-3.5" />}
              </button>
            </div>

          </div>

        </div>
      </div>

    </div>
  );
}
