import React from 'react';
import {
  ArrowRight, Search, Settings, Library, Download,
  ShieldCheck, CheckCircle2, Zap, BookOpen,
  Target, Layers, BarChart2, FileText, ChevronRight
} from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';

const WORKFLOW_STEPS = [
  {
    num: '01',
    tab: 'setup',
    icon: Settings,
    color: 'indigo',
    titleKey: 'home.step1_title',
    descKey: 'home.step1_desc',
  },
  {
    num: '02',
    tab: 'search',
    icon: Search,
    color: 'blue',
    titleKey: 'home.step2_title',
    descKey: 'home.step2_desc',
  },
  {
    num: '03',
    tab: 'synthesis',
    icon: Layers,
    color: 'violet',
    titleKey: 'home.step3_title',
    descKey: 'home.step3_desc',
  },
  {
    num: '04',
    tab: 'export',
    icon: Download,
    color: 'teal',
    titleKey: 'home.step4_title',
    descKey: 'home.step4_desc',
  },
];

const FEATURE_CARDS = [
  {
    icon: Target,
    color: 'indigo',
    titleKey: 'home.card1_title',
    descKey: 'home.card1_desc',
  },
  {
    icon: ShieldCheck,
    color: 'emerald',
    titleKey: 'home.card3_title',
    descKey: 'home.card3_list1',
  },
  {
    icon: BarChart2,
    color: 'blue',
    titleKey: 'home.matrix_title',
    descKey: 'home.matrix_desc',
  },
];

const COLOR_MAP = {
  indigo: {
    bg: 'bg-indigo-50 dark:bg-indigo-950/40',
    icon: 'text-indigo-600 dark:text-indigo-400',
    badge: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/60 dark:text-indigo-300',
    border: 'border-indigo-200 dark:border-indigo-800',
    step: 'bg-indigo-600',
  },
  blue: {
    bg: 'bg-blue-50 dark:bg-blue-950/40',
    icon: 'text-blue-600 dark:text-blue-400',
    badge: 'bg-blue-100 text-blue-700 dark:bg-blue-900/60 dark:text-blue-300',
    border: 'border-blue-200 dark:border-blue-800',
    step: 'bg-blue-600',
  },
  violet: {
    bg: 'bg-violet-50 dark:bg-violet-950/40',
    icon: 'text-violet-600 dark:text-violet-400',
    badge: 'bg-violet-100 text-violet-700 dark:bg-violet-900/60 dark:text-violet-300',
    border: 'border-violet-200 dark:border-violet-800',
    step: 'bg-violet-600',
  },
  teal: {
    bg: 'bg-teal-50 dark:bg-teal-950/40',
    icon: 'text-teal-600 dark:text-teal-400',
    badge: 'bg-teal-100 text-teal-700 dark:bg-teal-900/60 dark:text-teal-300',
    border: 'border-teal-200 dark:border-teal-800',
    step: 'bg-teal-600',
  },
  emerald: {
    bg: 'bg-emerald-50 dark:bg-emerald-950/40',
    icon: 'text-emerald-600 dark:text-emerald-400',
    badge: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/60 dark:text-emerald-300',
    border: 'border-emerald-200 dark:border-emerald-800',
    step: 'bg-emerald-600',
  },
};

export default function HomeTab({ setActiveTab }) {
  const { t } = useLanguage();

  return (
    <div className="min-h-screen bg-surface-50 dark:bg-surface-950">

      {/* ── Hero Section ───────────────────────────────────────────────── */}
      <section className="relative overflow-hidden">
        {/* Subtle grid background */}
        <div
          className="absolute inset-0 opacity-40 dark:opacity-20"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%234F46E5' fill-opacity='0.08'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
          }}
        />

        {/* Gradient blobs */}
        <div className="absolute -top-24 -right-24 w-96 h-96 bg-primary-200/30 dark:bg-primary-900/20 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-12 -left-24 w-80 h-80 bg-accent-200/30 dark:bg-accent-900/20 rounded-full blur-3xl pointer-events-none" />

        <div className="relative max-w-6xl mx-auto px-6 md:px-8 pt-16 pb-20 text-center">

          {/* Platform badge */}
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary-50 dark:bg-primary-950/60 border border-primary-200 dark:border-primary-800 mb-8">
            <BookOpen className="w-3.5 h-3.5 text-primary-600 dark:text-primary-400" />
            <span className="text-xs font-semibold text-primary-700 dark:text-primary-300 tracking-wide uppercase">
              {t('home.hero_badge')}
            </span>
          </div>

          {/* Headline */}
          <h1 className="font-display font-bold text-3xl sm:text-4xl md:text-5xl lg:text-6xl text-surface-900 dark:text-white tracking-tight leading-[1.18] sm:leading-[1.15] mb-6 [text-wrap:balance]">
            {t('home.hero_title_1')}
            <br />
            <span className="gradient-text">{t('home.hero_title_2')}</span>
          </h1>

          {/* Subtext */}
          <p className="text-base md:text-lg text-surface-500 dark:text-surface-400 max-w-2xl mx-auto leading-relaxed mb-10">
            {t('home.hero_desc')}
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mb-12">
            <button
              onClick={() => setActiveTab('setup')}
              className="btn btn-primary btn-lg shadow-primary-sm hover:shadow-primary-md"
            >
              <span>{t('home.cta_start')}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={() => setActiveTab('search')}
              className="btn btn-secondary btn-lg"
            >
              <Search className="w-4 h-4" />
              <span>{t('home.cta_explore')}</span>
            </button>
          </div>

          {/* Trust Pills */}
          <div className="flex flex-wrap items-center justify-center gap-2">
            {[
              { icon: CheckCircle2, text: t('home.trust_1'), color: 'text-primary-600 dark:text-primary-400' },
              { icon: ShieldCheck,  text: t('home.trust_2'), color: 'text-emerald-600 dark:text-emerald-400' },
              { icon: Zap,          text: t('home.trust_3'), color: 'text-amber-600 dark:text-amber-400' },
            ].map((pill, i) => {
              const Icon = pill.icon;
              return (
                <span
                  key={i}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white dark:bg-surface-900 border border-surface-200 dark:border-surface-800 text-xs font-medium text-surface-600 dark:text-surface-400 shadow-xs"
                >
                  <Icon className={`w-3 h-3 ${pill.color}`} />
                  {pill.text}
                </span>
              );
            })}
          </div>
        </div>
      </section>

      {/* ── Feature Cards ──────────────────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-6 md:px-8 py-12">
        <div className="text-center mb-8">
          <p className="section-label mb-2">{t('home.section1_badge')}</p>
          <h2 className="font-display font-bold text-2xl md:text-3xl text-surface-900 dark:text-white">
            {t('home.section1_title')}
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {FEATURE_CARDS.map((card, i) => {
            const Icon = card.icon;
            const colors = COLOR_MAP[card.color];
            return (
              <div
                key={i}
                className="card p-6 flex flex-col gap-4 hover:border-primary-200 dark:hover:border-primary-800 transition-all"
              >
                <div className={`w-10 h-10 rounded-xl ${colors.bg} flex items-center justify-center`}>
                  <Icon className={`w-5 h-5 ${colors.icon}`} />
                </div>
                <div>
                  <h3 className="font-display font-semibold text-base text-surface-900 dark:text-white mb-1">
                    {t(card.titleKey)}
                  </h3>
                  <p className="text-sm text-surface-500 dark:text-surface-400 leading-relaxed">
                    {t(card.descKey)}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* ── 4-Step Workflow ─────────────────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-6 md:px-8 py-12">
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3 mb-8 pb-4 border-b border-surface-200 dark:border-surface-800">
          <div>
            <p className="section-label mb-1">{t('home.workflow_badge')}</p>
            <h2 className="font-display font-bold text-2xl md:text-3xl text-surface-900 dark:text-white">
              {t('home.workflow_title')}
            </h2>
          </div>
          <p className="text-sm text-surface-400 max-w-xs">{t('home.workflow_desc')}</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {WORKFLOW_STEPS.map((step, idx) => {
            const Icon = step.icon;
            const colors = COLOR_MAP[step.color];
            return (
              <button
                key={step.tab}
                onClick={() => setActiveTab(step.tab)}
                className="card card-interactive p-5 flex flex-col gap-4 text-left group cursor-pointer"
              >
                <div className="flex items-center justify-between">
                  <span className={`text-[10px] font-bold px-2 py-1 rounded-lg ${colors.badge} tracking-wider`}>
                    STEP {step.num}
                  </span>
                  <div className={`w-9 h-9 rounded-xl ${colors.bg} flex items-center justify-center group-hover:scale-105 transition-transform`}>
                    <Icon className={`w-4.5 h-4.5 ${colors.icon}`} />
                  </div>
                </div>
                <div>
                  <h3 className="font-display font-semibold text-sm text-surface-900 dark:text-white mb-1 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
                    {t(step.titleKey)}
                  </h3>
                  <p className="text-xs text-surface-400 leading-relaxed">
                    {t(step.descKey)}
                  </p>
                </div>
                <div className="flex items-center gap-1 text-xs font-semibold text-primary-600 dark:text-primary-400">
                  <span>{t('home.step_action')}</span>
                  <ChevronRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                </div>
              </button>
            );
          })}
        </div>
      </section>

      {/* ── Academic Trust Banner ────────────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-6 md:px-8 py-12">
        <div className="card overflow-hidden">
          <div className="grid grid-cols-1 md:grid-cols-2">
            {/* Left: Content */}
            <div className="p-8 md:p-10 space-y-5">
              <div>
                <p className="section-label mb-2">{t('home.hitl_badge')}</p>
                <h2 className="font-display font-bold text-xl md:text-2xl text-surface-900 dark:text-white leading-tight">
                  {t('home.hitl_title')}
                </h2>
              </div>
              <p className="text-sm text-surface-500 dark:text-surface-400 leading-relaxed">
                {t('home.hitl_desc')}
              </p>
              <ul className="space-y-2">
                {[t('home.card3_list1'), t('home.card3_list2'), t('home.card3_list3')].map((item, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-surface-600 dark:text-surface-400">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
              <button
                onClick={() => setActiveTab('setup')}
                className="btn btn-primary"
              >
                {t('home.hitl_btn')}
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>

            {/* Right: Stats Grid */}
            <div className="bg-primary-600 dark:bg-primary-800 p-8 md:p-10 grid grid-cols-2 gap-4 content-center">
              {[
                { value: '≥50%', label: t('home.card2_kpi1').replace('⚡ ', '') },
                { value: '≥80%', label: t('home.card2_kpi2').replace('🎯 ', '') },
                { value: 'PRISMA', label: '2020 Compliant' },
                { value: 'HITL', label: t('home.trust_2') },
              ].map((stat, i) => (
                <div key={i} className="p-4 rounded-xl bg-white/10 backdrop-blur-sm">
                  <p className="font-display font-bold text-2xl text-white mb-1">{stat.value}</p>
                  <p className="text-xs text-primary-100 leading-tight">{stat.label}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Final CTA ────────────────────────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-6 md:px-8 pb-20">
        <div className="text-center space-y-4 py-10 border-t border-surface-200 dark:border-surface-800">
          <h3 className="font-display font-bold text-xl text-surface-900 dark:text-white">
            {t('home.ready_title')}
          </h3>
          <button
            onClick={() => setActiveTab('setup')}
            className="btn btn-primary btn-lg mx-auto shadow-primary-sm"
          >
            {t('home.ready_btn')}
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </section>
    </div>
  );
}
