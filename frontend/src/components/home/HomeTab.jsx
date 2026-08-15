import React from 'react';
import { Search, BrainCircuit, FileDown, ArrowRight, Settings, CheckCircle2, MessageSquare, Zap } from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';

export default function HomeTab({ setActiveTab, darkMode }) {
  const { t } = useLanguage();

  return (
    <div className={`space-y-16 pb-16 animate-in fade-in duration-500 ${darkMode ? 'text-slate-200' : 'text-slate-800'}`}>
      
      {/* Hero Section */}
      <section className="text-center pt-12 pb-8 px-4 max-w-4xl mx-auto space-y-6">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-bold bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-sky-400 mb-2 border border-blue-100 dark:border-blue-800 animate-in fade-in zoom-in duration-500 hover:scale-105 transition-transform cursor-default">
          <Zap className="w-4 h-4 text-amber-500 animate-bounce" />
          <span>LitReview Agent</span>
        </div>
        
        <h1 className="text-4xl md:text-5xl font-black tracking-tight leading-tight">
          {t('home.title')}
        </h1>
        
        <p className={`text-lg md:text-xl font-medium max-w-2xl mx-auto ${darkMode ? 'text-slate-400' : 'text-slate-600'}`}>
          {t('home.subtitle')}
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-6">
          <button
            onClick={() => setActiveTab('setup')}
            className="flex items-center gap-2 px-8 py-3.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold text-lg shadow-lg shadow-blue-500/20 transition-all w-full sm:w-auto justify-center"
          >
            {t('home.start_now')} <ArrowRight className="w-5 h-5" />
          </button>
          <a
            href="#features"
            className={`flex items-center gap-2 px-8 py-3.5 rounded-xl font-bold text-lg transition-all w-full sm:w-auto justify-center ${
              darkMode 
                ? 'bg-slate-800 hover:bg-slate-700 text-slate-300' 
                : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
            }`}
          >
            {t('home.learn_more')}
          </a>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="max-w-5xl mx-auto px-4 space-y-10">
        <div className="text-center space-y-3">
          <h2 className="text-3xl font-black">{t('home.features_title')}</h2>
          <p className={darkMode ? 'text-slate-400' : 'text-slate-500'}>
            {t('home.features_subtitle')}
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {[
            {
              icon: Search,
              title: t('home.feature1_title'),
              desc: t('home.feature1_desc')
            },
            {
              icon: BrainCircuit,
              title: t('home.feature2_title'),
              desc: t('home.feature2_desc')
            },
            {
              icon: FileDown,
              title: t('home.feature3_title'),
              desc: t('home.feature3_desc')
            }
          ].map((feat, i) => (
            <div key={i} className={`p-8 rounded-3xl border transition-all ${
              darkMode ? 'bg-slate-900 border-slate-800 hover:border-slate-700' : 'bg-white border-slate-200 hover:border-slate-300'
            } text-center group`}>
              <div className="w-16 h-16 mx-auto rounded-2xl bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-sky-400 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                <feat.icon className="w-8 h-8" />
              </div>
              <h3 className="text-xl font-bold mb-3">{feat.title}</h3>
              <p className={`text-sm leading-relaxed ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>{feat.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className={`max-w-5xl mx-auto rounded-3xl p-8 md:p-12 border ${darkMode ? 'bg-slate-900 border-slate-800' : 'bg-slate-50 border-slate-200'}`}>
        <div className="text-center space-y-3 mb-10">
          <h2 className="text-3xl font-black">{t('home.how_it_works')}</h2>
          <p className={darkMode ? 'text-slate-400' : 'text-slate-500'}>{t('home.how_it_works_subtitle')}</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 relative">
          {[
            { icon: Settings, title: t('home.step1_title'), desc: t('home.step1_desc') },
            { icon: Search, title: t('home.step2_title'), desc: t('home.step2_desc') },
            { icon: CheckCircle2, title: t('home.step3_title'), desc: t('home.step3_desc') },
            { icon: MessageSquare, title: t('home.step4_title'), desc: t('home.step4_desc') }
          ].map((step, i) => (
            <div key={i} className="text-center relative z-10">
              <div className="w-14 h-14 mx-auto rounded-full bg-white dark:bg-slate-800 border-2 border-blue-500 text-blue-600 dark:text-sky-400 flex items-center justify-center font-bold text-xl mb-4 shadow-sm relative z-10">
                {i + 1}
              </div>
              <h3 className="font-bold text-lg mb-2">{step.title}</h3>
              <p className={`text-sm ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>{step.desc}</p>
            </div>
          ))}
          {/* Connecting Line (hidden on mobile) */}
          <div className="hidden md:block absolute top-7 left-[12%] right-[12%] h-0.5 bg-blue-200 dark:bg-blue-900/50 -z-0"></div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="text-center max-w-2xl mx-auto pt-8">
        <h2 className="text-3xl font-black mb-6">{t('home.ready_title')}</h2>
        <button
          onClick={() => setActiveTab('setup')}
          className="px-10 py-4 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold text-lg shadow-lg shadow-blue-500/20 transition-all hover:-translate-y-1"
        >
          {t('home.ready_btn')}
        </button>
      </section>

    </div>
  );
}
