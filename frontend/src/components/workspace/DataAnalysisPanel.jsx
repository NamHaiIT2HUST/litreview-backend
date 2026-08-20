import React, { useRef, useState } from 'react';
import { Send, Paperclip, X, BarChart2, Copy, Check } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { API_BASE } from '../../utils/apiConfig';

const WELCOME_MSG = {
  sender: 'ai',
  text: 'T\u1ea3i l\u00ean t\u1eadp d\u1eef li\u1ec7u (**CSV/TSV**), m\u00f4 t\u1ea3 c\u00e1c c\u1ed9t ch\u00ednh v\u00e0 \u0111\u1eb7t c\u00e2u h\u1ecfi ph\u00e2n t\u00edch. V\u00ed d\u1ee5: *Ph\u00e2n ph\u1ed1i n\u0103m xu\u1ea5t b\u1ea3n c\u00f3 l\u1ec7ch kh\u00f4ng? T\u00ecm c\u00e1c c\u1ed9t t\u01b0\u01a1ng quan cao v\u1edbi s\u1ed1 l\u01b0\u1ee3t tr\u00edch d\u1eabn.*',
};

export default function DataAnalysisPanel({ darkMode }) {
  const [messages, setMessages] = useState([WELCOME_MSG]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [attachedFile, setAttachedFile] = useState(null);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => setAttachedFile({ name: file.name, content: ev.target.result });
    reader.readAsText(file, 'utf-8');
    e.target.value = null;
  };

  const handleSend = async (e) => {
    e.preventDefault();
    const question = input.trim();
    if (!question) return;
    const userMsg = { sender: 'user', text: question, attachment: attachedFile ? attachedFile.name : null };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    const fileSnapshot = attachedFile;
    setAttachedFile(null);
    setIsTyping(true);
    setTimeout(scrollToBottom, 50);
    try {
      const res = await fetch(API_BASE + '/workspace/analyze-data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, csv_text: fileSnapshot?.content ?? '', filename: fileSnapshot?.name ?? '' }),
      });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const data = await res.json();
      setMessages((prev) => [...prev, { sender: 'ai', text: data.answer ?? data.detail ?? 'Kh\u00f4ng c\u00f3 k\u1ebft qu\u1ea3.' }]);
    } catch (err) {
      setMessages((prev) => [...prev, { sender: 'ai', text: '\u274c L\u1ed7i k\u1ebft n\u1ed1i: ' + err.message }]);
    } finally {
      setIsTyping(false);
      setTimeout(scrollToBottom, 50);
    }
  };

  const handleCopy = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const dm = darkMode;

  return (
    <div className="flex-1 min-h-0 flex flex-col relative bg-transparent">
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        <div className="w-full max-w-4xl mx-auto space-y-8 py-6 px-4 md:px-8">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex gap-4 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.sender === 'ai' && (
                <div className="w-10 h-10 rounded-2xl bg-blue-600 text-white flex items-center justify-center shrink-0 shadow-md">
                  <BarChart2 className="w-5 h-5" />
                </div>
              )}
              <div className={`text-[14px] leading-relaxed ${
                msg.sender === 'user'
                  ? 'px-5 py-3.5 rounded-3xl rounded-tr-sm max-w-[85%] md:max-w-[75%] bg-blue-600 text-white font-medium shadow-sm'
                  : dm ? 'py-1.5 w-full max-w-full text-slate-200' : 'py-1.5 w-full max-w-full text-slate-800'
              }`}>
                {msg.attachment && (
                  <div className="mb-2 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-[11px] font-semibold border border-blue-200 dark:border-blue-800/50">
                    <Paperclip className="w-3 h-3" />{msg.attachment}
                  </div>
                )}
                <div className={msg.sender === 'user' ? 'whitespace-pre-wrap' : 'prose prose-slate dark:prose-invert max-w-none prose-p:text-[14px] prose-p:leading-relaxed prose-headings:font-bold prose-h1:text-[16px] prose-h2:text-[15px] prose-h3:text-[14px] prose-li:text-[14px] prose-pre:bg-slate-800 prose-table:text-[13px]'}>
                  {msg.sender === 'user' ? msg.text : (
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.text}</ReactMarkdown>
                  )}
                </div>
                {msg.sender === 'ai' && (
                  <div className="flex items-center gap-1.5 mt-3 pt-3 border-t border-slate-200 dark:border-slate-700/60">
                    <button
                      onClick={() => handleCopy(msg.text, idx)}
                      className={`p-1.5 rounded-md transition-colors flex items-center justify-center ${
                        copiedIndex === idx
                          ? 'text-emerald-500 bg-emerald-50 dark:bg-emerald-900/30'
                          : 'text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-800'
                      }`}
                    >
                      {copiedIndex === idx ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}

          {isTyping && (
            <div className="flex gap-4 justify-start">
              <div className="w-10 h-10 rounded-2xl bg-blue-600 text-white flex items-center justify-center shrink-0 shadow-md">
                <BarChart2 className="w-5 h-5" />
              </div>
              <div className={`py-2.5 flex items-center gap-1.5 ${dm ? 'text-slate-200' : 'text-slate-900'}`}>
                <div className="w-2.5 h-2.5 rounded-full bg-slate-400 animate-bounce" />
                <div className="w-2.5 h-2.5 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '0.2s' }} />
                <div className="w-2.5 h-2.5 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '0.4s' }} />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="relative mt-2 shrink-0 w-full flex flex-col items-center gap-2 mb-4 px-4">
        {attachedFile && (
          <div className={`self-start flex items-center gap-2 px-3 py-1.5 rounded-xl border text-[12px] font-semibold shadow-sm ${
            dm ? 'bg-slate-800 border-slate-700 text-slate-200' : 'bg-slate-50 border-slate-200 text-slate-700'
          }`}>
            <Paperclip className="w-3.5 h-3.5 text-blue-500" />
            <span className="max-w-[220px] truncate">{attachedFile.name}</span>
            <button onClick={() => setAttachedFile(null)} className="ml-1 text-slate-400 hover:text-red-500 transition-colors">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        <form onSubmit={handleSend} className="relative w-full max-w-4xl mx-auto">
          <input ref={fileInputRef} type="file" accept=".csv,.tsv,.txt,.json" className="hidden" onChange={handleFileChange} />

          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            title="\u0110\u00ednh k\u00e8m t\u1eadp d\u1eef li\u1ec7u (CSV, TSV)"
            className={`absolute left-3 top-1/2 -translate-y-1/2 p-1.5 rounded-lg transition-colors ${
              attachedFile ? 'text-blue-500' : dm ? 'text-slate-500 hover:text-slate-300' : 'text-slate-400 hover:text-slate-600'
            }`}
          >
            <Paperclip className="w-4 h-4" />
          </button>

          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="T\u1ea3i l\u00ean d\u1eef li\u1ec7u, m\u00f4 t\u1ea3 c\u00e1c c\u1ed9t ch\u00ednh, v\u00e0 \u0111\u1eb7t c\u00e2u h\u1ecfi..."
            className={`w-full pl-11 pr-32 py-4 border rounded-[2rem] text-[14px] font-medium focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 shadow-sm transition-all ${
              dm ? 'bg-slate-800 border-slate-700 text-white placeholder-slate-500' : 'bg-white border-slate-200 text-slate-900 placeholder-slate-400'
            }`}
          />

          <button
            type="submit"
            disabled={!input.trim() && !attachedFile}
            className="absolute right-2 top-1/2 -translate-y-1/2 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed text-white px-5 py-2.5 rounded-[1.5rem] text-sm font-bold transition-transform active:scale-95 flex items-center gap-1.5 shadow-md"
          >
            <span>G\u1eedi</span><Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
