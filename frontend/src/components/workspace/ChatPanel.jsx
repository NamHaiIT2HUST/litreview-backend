import React, { useState } from 'react';
import { Layers, Bot, Send } from 'lucide-react';

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
    <div className={`p-6 rounded-3xl border transition-colors min-h-[550px] flex flex-col justify-between space-y-4 shadow-sm ${
      darkMode ? 'bg-slate-900 border-slate-800 text-white' : 'bg-white border-slate-200 text-slate-800'
    }`}>
      {/* Chat Messages List */}
      <div className="space-y-4">
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
              className={`p-5 rounded-2xl max-w-xl text-sm leading-relaxed ${
                msg.sender === 'user'
                  ? 'bg-blue-600 text-white font-medium'
                  : darkMode
                    ? 'bg-slate-800 border border-slate-700 text-slate-200'
                    : 'bg-slate-50 border border-slate-200 text-slate-800'
              }`}
            >
              <div dangerouslySetInnerHTML={{ __html: msg.text.replace(/\n/g, '<br/>') }} />

              {/* Render Context Used if available */}
              {msg.sender === 'ai' && msg.context_used && msg.context_used.length > 0 && (
                <div className={`pt-3 mt-3 border-t space-y-2 ${
                  darkMode ? 'border-slate-700' : 'border-slate-200'
                }`}>
                  <span className="text-xs font-bold text-slate-400 uppercase">Trích dẫn (Context):</span>
                  <div className="flex flex-col gap-2">
                    {msg.context_used.map((ctx, pIdx) => (
                      <details key={pIdx} className="text-xs">
                        <summary className="cursor-pointer text-blue-600 dark:text-sky-400 font-medium">
                          Nguồn #{pIdx + 1}
                        </summary>
                        <p className="mt-1 p-2 bg-slate-100 dark:bg-slate-900 rounded text-slate-600 dark:text-slate-400">
                          {ctx}
                        </p>
                      </details>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
        
        {isTyping && (
          <div className="flex gap-3 justify-start">
            <div className="w-9 h-9 rounded-2xl bg-blue-600 text-white flex items-center justify-center font-bold text-sm shrink-0 shadow-md">
              <Bot className="w-5 h-5" />
            </div>
            <div className={`p-5 rounded-2xl max-w-xl text-sm leading-relaxed flex items-center gap-1 ${
              darkMode ? 'bg-slate-800 border border-slate-700 text-slate-200' : 'bg-slate-50 border border-slate-200 text-slate-800'
            }`}>
              <div className="w-2 h-2 rounded-full bg-slate-400 animate-bounce"></div>
              <div className="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              <div className="w-2 h-2 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: '0.4s' }}></div>
            </div>
          </div>
        )}
      </div>

      {/* Workspace source registry — no synthetic findings are shown here. */}
      <div className={`p-4 rounded-2xl border space-y-3 ${
        darkMode ? 'bg-slate-800/80 border-slate-700' : 'bg-slate-50 border-slate-200'
      }`}>
        <h4 className="font-bold text-xs md:text-sm flex items-center gap-2">
          <Layers className="w-4 h-4 text-blue-600 dark:text-sky-400" />
          <span>Nguồn đã ingest ({workspacePapers.length})</span>
        </h4>
        {workspacePapers.length === 0 ? (
          <p className="text-xs text-slate-400">Chưa có PDF có provenance.</p>
        ) : (
          <div className="space-y-2">
            {workspacePapers.map((paper, idx) => (
              <div key={paper.id} className="text-xs flex gap-2">
                <span className="font-bold text-blue-600 dark:text-sky-400">[{idx + 1}]</span>
                <span className="truncate">{paper.title}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Chat Input Bar */}
      <form onSubmit={handleSendMessage} className="relative pt-2">
        <input
          type="text"
          value={inputQuestion}
          onChange={e => setInputQuestion(e.target.value)}
          placeholder="Hỏi AI assistant về phương pháp, hạn chế hoặc hướng nghiên cứu..."
          className={`w-full pl-5 pr-28 py-4 border rounded-2xl text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-600 ${
            darkMode 
              ? 'bg-slate-800 border-slate-700 text-white placeholder-slate-500' 
              : 'bg-slate-100 border-slate-200 text-slate-900 placeholder-slate-400'
          }`}
        />
        <button
          type="submit"
          className="absolute right-2 top-1/2 -translate-y-1/2 bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center gap-1 shadow-md"
        >
          <span>Gửi</span>
          <Send className="w-3.5 h-3.5" />
        </button>
      </form>
    </div>
  );
}
