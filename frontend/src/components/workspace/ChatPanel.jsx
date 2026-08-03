import React, { useState } from 'react';
import { Layers } from 'lucide-react';

export default function ChatPanel({ 
  workspacePapers, 
  chatMessages, 
  setChatMessages, 
  activeCitation, 
  setActiveCitation 
}) {
  const [inputQuestion, setInputQuestion] = useState('');

  const handleSendMessage = (e) => {
    e.preventDefault();
    if (!inputQuestion.trim()) return;

    const userMsg = { sender: 'user', text: inputQuestion };
    setChatMessages(prev => [...prev, userMsg]);
    setInputQuestion('');

    setTimeout(() => {
      const aiReply = {
        sender: 'ai',
        text: `Regarding your query "${inputQuestion}": Research indicates that combining Vector DB retrieval with citation enforcement reduces hallucination risks significantly [2]. In clinical trials, models like GPT-4 required human validation prior to record insertion [1].`
      };
      setChatMessages(prev => [...prev, aiReply]);
    }, 800);
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4 min-h-[500px] flex flex-col justify-between">
      {/* Chat Messages */}
      <div className="space-y-4">
        {chatMessages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex gap-3 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {msg.sender === 'ai' && (
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-purple-600 text-white flex items-center justify-center font-bold text-xs shrink-0">
                AI
              </div>
            )}
            <div
              className={`p-4 rounded-2xl max-w-xl text-xs leading-relaxed ${
                msg.sender === 'user'
                  ? 'bg-blue-600 text-white font-medium'
                  : 'bg-slate-50 border border-slate-200 text-slate-800 space-y-2'
              }`}
            >
              <div dangerouslySetInnerHTML={{ __html: msg.text.replace(/\n/g, '<br/>') }} />

              {/* Render Citation Clickable Buttons if AI message */}
              {msg.sender === 'ai' && (
                <div className="pt-2 border-t border-slate-200 flex items-center gap-2">
                  <span className="text-[10px] font-bold text-slate-400 uppercase">Click to Verify:</span>
                  {workspacePapers.map((paper, pIdx) => (
                    <button
                      key={pIdx}
                      onClick={() => setActiveCitation(paper)}
                      className={`px-2 py-0.5 text-[10px] font-bold rounded ${
                        activeCitation?.id === paper.id
                          ? 'bg-purple-600 text-white'
                          : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
                      }`}
                    >
                      [{pIdx + 1}] {paper.id}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Auto-Generated Comparison Table Widget */}
      <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-2">
        <div className="flex items-center justify-between">
          <h4 className="font-bold text-xs text-slate-800 flex items-center gap-1.5">
            <Layers className="w-4 h-4 text-purple-600" />
            <span>Auto-Generated Literature Comparison Table</span>
          </h4>
          <span className="text-[10px] bg-purple-100 text-purple-700 px-2 py-0.5 rounded font-bold">Auto-Synthesized</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-[11px] border-collapse bg-white rounded-lg overflow-hidden border border-slate-200">
            <thead>
              <tr className="bg-slate-100 text-slate-700 font-bold border-b border-slate-200">
                <th className="p-2">Paper</th>
                <th className="p-2">Core Focus</th>
                <th className="p-2">Limitation / Gap</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {workspacePapers.map((paper, idx) => (
                <tr key={idx} className="hover:bg-slate-50">
                  <td className="p-2 font-bold text-blue-600">[{idx+1}] {paper.id}</td>
                  <td className="p-2 text-slate-800">{paper.tldr.slice(7, 60)}...</td>
                  <td className="p-2 text-slate-500">Requires validation on larger patient cohorts</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Chat Input Bar */}
      <form onSubmit={handleSendMessage} className="relative pt-2">
        <input
          type="text"
          value={inputQuestion}
          onChange={e => setInputQuestion(e.target.value)}
          placeholder="Ask AI assistant about limitations, methodology, or future research gaps..."
          className="w-full pl-4 pr-24 py-3 bg-slate-100 border border-slate-200 rounded-xl text-xs focus:bg-white focus:outline-none focus:ring-2 focus:ring-purple-500"
        />
        <button
          type="submit"
          className="absolute right-2 top-1/2 -translate-y-1/2 bg-purple-600 hover:bg-purple-700 text-white px-4 py-1.5 rounded-lg text-xs font-bold transition-all"
        >
          Send
        </button>
      </form>
    </div>
  );
}
