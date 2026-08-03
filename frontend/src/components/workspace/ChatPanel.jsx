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

  const handleSendMessage = (e) => {
    e.preventDefault();
    if (!inputQuestion.trim()) return;

    const userMsg = { sender: 'user', text: inputQuestion };
    setChatMessages(prev => [...prev, userMsg]);
    setInputQuestion('');

    setTimeout(() => {
      const aiReply = {
        sender: 'ai',
        text: `SynthesizerAgent trả lời cho câu hỏi "${inputQuestion}": Dựa trên ${workspacePapers.length} bài báo bạn vừa upload, việc kết hợp RetrieverAgent với LLM local giúp giảm thiểu rủi ro ảo giác đáng kể [2]. Đối với thử nghiệm lâm sàng, mô hình GPT-4 vẫn yêu cầu bác sĩ thẩm định lại [1].`
      };
      setChatMessages(prev => [...prev, aiReply]);
    }, 800);
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

              {/* Render Citation Clickable Buttons if AI message */}
              {msg.sender === 'ai' && (
                <div className={`pt-3 mt-3 border-t flex items-center gap-2 flex-wrap ${
                  darkMode ? 'border-slate-700' : 'border-slate-200'
                }`}>
                  <span className="text-xs font-bold text-slate-400 uppercase">Click để xem gốc:</span>
                  {workspacePapers.map((paper, pIdx) => (
                    <button
                      key={pIdx}
                      onClick={() => setActiveCitation(paper)}
                      className={`px-2.5 py-1 text-xs font-bold rounded-lg transition-all ${
                        activeCitation?.id === paper.id
                          ? 'bg-blue-600 text-white shadow-sm'
                          : darkMode
                            ? 'bg-slate-700 text-slate-300 hover:bg-slate-600'
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
      <div className={`p-4 rounded-2xl border space-y-3 ${
        darkMode ? 'bg-slate-800/80 border-slate-700' : 'bg-slate-50 border-slate-200'
      }`}>
        <div className="flex items-center justify-between">
          <h4 className="font-bold text-xs md:text-sm flex items-center gap-2">
            <Layers className="w-4 h-4 text-blue-600 dark:text-sky-400" />
            <span>Bảng So Sánh Tự Động (Multi-Agent Synthesis)</span>
          </h4>
          <span className="text-xs bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-sky-300 px-2 py-0.5 rounded-md font-bold">Auto-Generated</span>
        </div>

        <div className="overflow-x-auto">
          <table className={`w-full text-left text-xs border-collapse rounded-xl overflow-hidden border ${
            darkMode ? 'bg-slate-900 border-slate-700' : 'bg-white border-slate-200'
          }`}>
            <thead>
              <tr className={`font-bold border-b ${
                darkMode ? 'bg-slate-800 text-slate-300 border-slate-700' : 'bg-slate-100 text-slate-700 border-slate-200'
              }`}>
                <th className="p-3">Bài báo</th>
                <th className="p-3">Trọng tâm Nghiên cứu</th>
                <th className="p-3">Hạn chế / Research Gap</th>
              </tr>
            </thead>
            <tbody className={`divide-y ${darkMode ? 'divide-slate-700' : 'divide-slate-100'}`}>
              {workspacePapers.map((paper, idx) => (
                <tr key={idx} className="hover:bg-blue-50/20">
                  <td className="p-3 font-bold text-blue-600 dark:text-sky-400">[{idx+1}] {paper.id}</td>
                  <td className="p-3">{paper.tldr.slice(7, 60)}...</td>
                  <td className="p-3 text-slate-400">Cần mở rộng thử nghiệm lâm sàng</td>
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
