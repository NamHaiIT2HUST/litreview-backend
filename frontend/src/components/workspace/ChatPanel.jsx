import React, { useState } from 'react';
import { Layers, Bot, Send } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import remarkGfm from 'remark-gfm';
import rehypeKatex from 'rehype-katex';

export default function ChatPanel({ 
  workspacePapers, 
  chatMessages, 
  setChatMessages, 
  activeCitation, 
  setActiveCitation,
  darkMode
}) {
  const [inputQuestion, setInputQuestion] = useState('');
  const [isTyping, setIsTyping] = useState(false);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputQuestion.trim()) return;

    const question = inputQuestion;
    const userMsg = { sender: 'user', text: question };
    setChatMessages(prev => [...prev, userMsg]);
    setInputQuestion('');
    setIsTyping(true);

    try {
      const response = await fetch("http://localhost:8000/api/v1/workspace/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: question }),
      });

      if (!response.ok) {
        throw new Error("Chat request failed");
      }

      const data = await response.json();
      
      const aiReply = {
        sender: 'ai',
        text: data.answer,
        context_used: data.context_used
      };
      setChatMessages(prev => [...prev, aiReply]);
    } catch (error) {
      console.error("Chat error:", error);
      setChatMessages(prev => [...prev, {
        sender: 'ai',
        text: "Xin lỗi, đã có lỗi kết nối tới AI Agent. Vui lòng thử lại sau."
      }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className={`p-6 rounded-3xl border transition-colors h-full flex flex-col space-y-4 shadow-sm overflow-hidden relative ${
      darkMode ? 'bg-slate-900 border-slate-800 text-white' : 'bg-white border-slate-200 text-slate-800'
    }`}>
      {/* Chat Messages List */}
      <div className="flex-1 overflow-y-auto pr-2 custom-scrollbar">
        <div className="w-full space-y-8 py-4 px-2">
          {chatMessages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex gap-3 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {msg.sender === 'ai' && (
              <div className="w-9 h-9 rounded-2xl bg-blue-600 text-white flex items-center justify-center font-bold text-sm shrink-0 shadow-md">
                <Bot className="w-5 h-5" />
              </div>
            )}
            <div
              className={`text-sm leading-relaxed ${
                msg.sender === 'user'
                  ? 'p-5 rounded-2xl max-w-[85%] bg-blue-600 text-white font-medium'
                  : darkMode
                    ? 'py-2 w-full max-w-full text-slate-200'
                    : 'py-2 w-full max-w-full text-slate-900'
              }`}
            >
              <div className={msg.sender === 'user' ? 'whitespace-pre-wrap' : 'prose prose-base md:prose-lg prose-slate dark:prose-invert max-w-none prose-p:leading-relaxed prose-pre:bg-slate-800'}>
                {msg.sender === 'user' ? (
                  msg.text
                ) : (
                  <ReactMarkdown
                    remarkPlugins={[remarkMath, remarkGfm]}
                    rehypePlugins={[rehypeKatex]}
                  >
                    {msg.text}
                  </ReactMarkdown>
                )}
              </div>
              {/* Render Context Used if available */}
              {msg.sender === 'ai' && msg.context_used && msg.context_used.length > 0 && (
                <details className="mt-6 group border dark:border-slate-700/60 rounded-2xl overflow-hidden bg-slate-50/50 dark:bg-slate-800/30">
                  <summary className="cursor-pointer p-3.5 text-xs font-semibold text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors flex items-center gap-2 select-none outline-none">
                    <Layers className="w-4 h-4 text-blue-500" />
                    <span>Đã tham khảo {msg.context_used.length} đoạn ngữ cảnh từ tài liệu</span>
                  </summary>
                  <div className="p-4 bg-white dark:bg-slate-900 border-t dark:border-slate-700/60 max-h-64 overflow-y-auto space-y-4 custom-scrollbar">
                    {msg.context_used.map((ctx, pIdx) => (
                      <div key={pIdx} className="text-xs">
                        <div className="font-bold text-slate-700 dark:text-slate-300 mb-1.5 flex items-center gap-1.5">
                           <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span> Nguồn #{pIdx + 1}
                        </div>
                        <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-xl text-slate-600 dark:text-slate-400 leading-relaxed border dark:border-slate-700/50 shadow-sm">
                          {ctx}
                        </div>
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </div>
          </div>
        ))}
        
        {isTyping && (
          <div className="flex gap-3 justify-start">
            <div className="w-9 h-9 rounded-2xl bg-blue-600 text-white flex items-center justify-center font-bold text-sm shrink-0 shadow-md">
              <Bot className="w-5 h-5" />
            </div>
            <div className={`py-2 w-full max-w-full text-sm leading-relaxed flex items-center gap-1 ${
              darkMode ? 'text-slate-200' : 'text-slate-900'
            }`}>
              <div className="w-2 h-2 rounded-full bg-slate-400 animate-bounce"></div>
              <div className="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              <div className="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '0.4s' }}></div>
            </div>
          </div>
        )}
        </div>
      </div>

      {/* Workspace source registry - Floating bottom right */}
      <div className={`absolute bottom-24 right-6 p-3 rounded-2xl border space-y-2 w-56 shadow-lg z-10 backdrop-blur-md opacity-70 hover:opacity-100 transition-opacity ${
        darkMode ? 'bg-slate-800/90 border-slate-700' : 'bg-white/90 border-slate-200'
      }`}>
        <h4 className="font-bold text-xs flex items-center gap-2">
          <Layers className="w-3.5 h-3.5 text-blue-600 dark:text-sky-400" />
          <span>Nguồn đã ingest ({workspacePapers.length})</span>
        </h4>
        {workspacePapers.length === 0 ? (
          <p className="text-[10px] text-slate-400">Chưa có PDF.</p>
        ) : (
          <div className="space-y-1 max-h-32 overflow-y-auto custom-scrollbar pr-1">
            {workspacePapers.map((paper, idx) => (
              <div key={paper.id} className="text-[11px] flex gap-1.5 items-start">
                <span className="font-bold text-blue-600 dark:text-sky-400 shrink-0">[{idx + 1}]</span>
                <span className="truncate leading-tight">{paper.title}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Chat Input Bar */}
      <form onSubmit={handleSendMessage} className="relative mt-2 shrink-0 w-full">
        <input
          type="text"
          value={inputQuestion}
          onChange={e => setInputQuestion(e.target.value)}
          placeholder="Hỏi AI assistant về phương pháp, hạn chế hoặc hướng nghiên cứu..."
          className={`w-full pl-6 pr-32 py-4 border rounded-full text-sm font-medium focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 shadow-sm transition-all ${
            darkMode 
              ? 'bg-slate-800 border-slate-700 text-white placeholder-slate-500' 
              : 'bg-white border-slate-200 text-slate-900 placeholder-slate-400'
          }`}
        />
        <button
          type="submit"
          className="absolute right-2 top-1/2 -translate-y-1/2 bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-full text-sm font-bold transition-transform active:scale-95 flex items-center gap-1.5 shadow-md"
        >
          <span>Gửi</span>
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
}
