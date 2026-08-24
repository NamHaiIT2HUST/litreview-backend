import React, { useState } from 'react';
import { Layers, Bot, Send, Copy, ThumbsUp, ThumbsDown, Check, ShieldCheck, Sparkles } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import remarkGfm from 'remark-gfm';
import rehypeKatex from 'rehype-katex';
import CitationChip from './CitationChip';
import { useLanguage } from '../../contexts/LanguageContext';
import { formatMathAndMarkdown } from '../../utils/mathUtils';
import { safeFetch } from '../../utils/apiConfig';



export default function ChatPanel({ 
  workspacePapers,
  selectedSourceIds,
  chatMessages, 
  setChatMessages, 
  activeCitation, 
  setActiveCitation,
  onOpenHarness,
  darkMode
}) {
  const { t } = useLanguage();
  const [inputQuestion, setInputQuestion] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const messagesEndRef = React.useRef(null);

  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, isTyping]);

  const handleCopy = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputQuestion.trim()) return;

    const question = inputQuestion;
    const userMsg = { sender: 'user', text: question };
    setChatMessages(prev => [...prev, userMsg]);
    setInputQuestion('');
    setIsTyping(true);

    try {
      const paperIds = selectedSourceIds && selectedSourceIds.length > 0 
        ? selectedSourceIds 
        : (workspacePapers ? workspacePapers.map(p => p.id) : []);
        
      const response = await safeFetch('/workspace/chat', {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: question, paper_ids: paperIds }),
      });

      if (!response.ok) {
        throw new Error("Chat request failed");
      }

      const data = await response.json();
      
      const aiReply = {
        sender: 'ai',
        text: data.answer,
        context_used: data.context_used,
        citations: data.citations,
        guardrail: data.guardrail
      };
      setChatMessages(prev => [...prev, aiReply]);
    } catch (error) {
      console.error("Chat error:", error);
      setChatMessages(prev => [...prev, {
        sender: 'ai',
        text: t('chat.error_msg')
      }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className={`flex-1 min-h-0 flex flex-col relative bg-transparent`}>
      {/* Chat Messages List */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        <div className="w-full max-w-4xl mx-auto space-y-8 py-6 px-4 md:px-8">
          {chatMessages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex gap-4 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {msg.sender === 'ai' && (
              <div className="w-10 h-10 rounded-2xl overflow-hidden shrink-0 shadow-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 flex items-center justify-center p-0.5">
                <img src="/AI.png" alt="AI Assistant" className="w-full h-full object-cover rounded-[14px]" />
              </div>
            )}
            <div
              className={`text-[14px] leading-relaxed ${
                msg.sender === 'user'
                  ? 'px-5 py-3.5 rounded-3xl rounded-tr-sm max-w-[85%] md:max-w-[75%] bg-blue-600 text-white font-medium shadow-sm'
                  : 'py-1.5 w-full max-w-full text-slate-800 dark:py-1.5 dark:w-full dark:max-w-full dark:text-slate-200'
              }`}
            >
              <div className={msg.sender === 'user' ? 'whitespace-pre-wrap' : 'prose prose-slate dark:prose-invert max-w-none prose-p:text-[14px] prose-p:leading-relaxed prose-headings:font-bold prose-h1:text-[16px] prose-h2:text-[15px] prose-h3:text-[14px] prose-li:text-[14px] prose-pre:bg-slate-800'}>
                {msg.sender === 'user' ? (
                  msg.text
                ) : (
                  <ReactMarkdown
                    remarkPlugins={[remarkMath, remarkGfm]}
                    rehypePlugins={[rehypeKatex]}
                    components={{
                      a: ({node, href, children, ...props}) => {
                        if (href?.startsWith('#cite-')) {
                          const citeId = href.replace('#cite-', '');
                          const citeObj = msg.citations?.find(c => String(c.key) === String(citeId)) || msg.context_used?.find(c => String(c.key) === String(citeId));
                          return (
                              <CitationChip
                                key={citeId}
                                citeId={citeId}
                                citeObj={citeObj}
                                darkMode={darkMode}
                                onClick={(e) => {
                                  e.preventDefault();
                                  if (citeObj) {
                                    setActiveCitation({
                                      marker_display: `[${citeId}]`,
                                      title: citeObj.paper_title,
                                      filename: citeObj.filename,
                                      source_page_display: citeObj.page || citeObj.page_display,
                                      source_char_start: citeObj.page_char_start,
                                      source_char_end: citeObj.page_char_end,
                                      quoted_snippet: citeObj.raw_text || citeObj.snippet
                                    });
                                  }
                                }}
                              >
                                {children}
                              </CitationChip>
                          );
                        }
                        return <a href={href} {...props}>{children}</a>;
                      }
                    }}
                  >
                    {formatMathAndMarkdown(msg.text)}
                  </ReactMarkdown>

                )}
              </div>
              {/* Render Unified Context Used if available */}
              {msg.sender === 'ai' && msg.context_used && msg.context_used.length > 0 && (
                <details className="mt-6 group border dark:border-slate-700/60 rounded-2xl overflow-hidden bg-slate-50/50 dark:bg-slate-800/30">
                  <summary className="cursor-pointer p-3.5 text-xs font-semibold text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors flex items-center gap-2 select-none outline-none">
                    <Layers className="w-4 h-4 text-blue-500" />
                    <span>{t('chat.context_used')} ({msg.context_used.length} {t('chat.sources')})</span>
                  </summary>
                  <div className="p-4 bg-white dark:bg-slate-900 border-t dark:border-slate-700/60 max-h-64 overflow-y-auto space-y-4 custom-scrollbar">
                    {msg.context_used.map((ctx, pIdx) => {
                      return (
                        <div key={pIdx} className="text-xs">
                          <button
                            type="button"
                            onClick={() => setActiveCitation({
                                marker_display: `[${ctx.key}]`,
                                title: ctx.paper_title,
                                filename: ctx.filename,
                                source_page_display: ctx.page_display,
                                source_char_start: ctx.page_char_start,
                                source_char_end: ctx.page_char_end,
                                quoted_snippet: ctx.raw_text || ctx.snippet
                            })}
                            className="font-bold text-blue-600 dark:text-blue-400 hover:underline mb-1.5 flex items-center gap-1.5 text-left"
                          >
                             <span className="px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-900 text-[10px]">[{ctx.key}]</span>
                             {ctx.paper_title} ({t('chat.page')} {ctx.page_display})
                          </button>
                          <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-xl text-slate-600 dark:text-slate-400 leading-relaxed border dark:border-slate-700/50 shadow-sm whitespace-pre-wrap">
                            {ctx.snippet}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </details>
              )}

              {/* Action Buttons */}

              {msg.sender === 'ai' && (
                <div className="flex items-center justify-between gap-1.5 mt-3 pt-3 border-t border-slate-200 dark:border-slate-700/60">
                  <div className="flex items-center gap-1.5">
                    <button 
                      onClick={() => handleCopy(msg.text, idx)}
                      className={`p-1.5 rounded-md transition-colors flex items-center justify-center group relative ${
                        copiedIndex === idx 
                          ? 'text-emerald-500 bg-emerald-50 dark:bg-emerald-900/30' 
                          : 'text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-800'
                      }`}
                    >
                      {copiedIndex === idx ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                      <span className="absolute -top-8 bg-slate-800 text-white text-[10px] px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                        {copiedIndex === idx ? t('chat.copied') : t('chat.copy')}
                      </span>
                    </button>
                    <button 
                      className="p-1.5 text-slate-400 hover:text-emerald-600 dark:hover:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-900/30 rounded-md transition-colors flex items-center justify-center group relative"
                    >
                      <ThumbsUp className="w-4 h-4" />
                      <span className="absolute -top-8 bg-slate-800 text-white text-[10px] px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">{t('chat.good_response')}</span>
                    </button>
                    <button 
                      className="p-1.5 text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-900/30 rounded-md transition-colors flex items-center justify-center group relative"
                    >
                      <ThumbsDown className="w-4 h-4" />
                      <span className="absolute -top-8 bg-slate-800 text-white text-[10px] px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">{t('chat.bad_response')}</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
        
        {isTyping && (
          <div className="flex gap-4 justify-start">
            <div className="w-10 h-10 rounded-2xl overflow-hidden shrink-0 shadow-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 flex items-center justify-center p-0.5">
              <img src="/AI.png" alt="AI Assistant" className="w-full h-full object-cover rounded-[14px]" />
            </div>
            <div className={`py-2.5 w-full max-w-full text-sm leading-relaxed flex items-center gap-1.5 ${
              'text-slate-900 dark:text-slate-200'
            }`}>
              <div className="w-2.5 h-2.5 rounded-full bg-slate-400 animate-bounce"></div>
              <div className="w-2.5 h-2.5 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              <div className="w-2.5 h-2.5 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '0.4s' }}></div>
            </div>
          </div>
        )}
          <div ref={messagesEndRef} />
        </div>
      </div>



      {/* Chat Input Bar */}
      <div className="relative mt-2 shrink-0 w-full flex flex-col items-center gap-2 mb-4 px-4">
        <form onSubmit={handleSendMessage} className="relative w-full max-w-4xl mx-auto">
        <input
          type="text"
          value={inputQuestion}
          onChange={e => setInputQuestion(e.target.value)}
          placeholder={t('chat.input_placeholder')}
          className={`w-full pl-6 pr-32 py-4 border rounded-[2rem] text-[14px] font-medium focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 shadow-sm transition-all ${
            'bg-white border-slate-200 text-slate-900 placeholder-slate-400 dark:bg-slate-800 dark:border-slate-700 dark:text-white dark:placeholder-slate-500'
          }`}
        />
        <button
          type="submit"
          className="absolute right-2 top-1/2 -translate-y-1/2 bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-[1.5rem] text-sm font-bold transition-transform active:scale-95 flex items-center gap-1.5 shadow-md"
        >
          <span>{t('chat.send')}</span>
          <Send className="w-4 h-4" />
        </button>
        </form>
      </div>
    </div>
  );
}
