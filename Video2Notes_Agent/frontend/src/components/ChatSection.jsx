import React from 'react';
import { Bot, Loader2, MessageSquare, Send } from 'lucide-react';
import MarkdownRenderer from './MarkdownRenderer';

const ChatSection = ({ 
  messages, 
  currentQuestion, 
  setCurrentQuestion, 
  onSendMessage, 
  isChatting, 
  chatEndRef
}) => {
  return (
    <section className="lg:col-span-4 sticky top-24 flex h-[calc(100vh-8rem)] min-h-[30rem] flex-col overflow-hidden rounded-[30px] border border-white/80 bg-[rgba(255,255,255,0.86)] shadow-[0_24px_70px_rgba(15,23,42,0.08)] backdrop-blur-xl max-lg:h-[32rem]">
      <header className="border-b border-slate-200 px-6 py-5">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-900 text-white">
            <MessageSquare className="h-5 w-5" />
          </div>
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.24em] text-slate-500">RAG chat</p>
            <h3 className="text-lg font-black text-slate-900">Ask the saved note</h3>
          </div>
        </div>
      </header>

      <div className="scrollbar-surface flex-1 space-y-5 overflow-y-auto px-5 py-6">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center space-y-4 px-4 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-slate-100 text-slate-400">
                <Bot className="h-8 w-8" />
            </div>
            <p className="max-w-xs text-sm font-medium leading-relaxed text-slate-500">
              Ask about concepts, timestamps, or summaries. The answer is grounded in the stored note content and rebuilt vector context.
            </p>
          </div>
        )}
        
        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[88%] rounded-3xl p-4 text-sm leading-relaxed shadow-sm ${
              msg.role === 'user' 
                ? 'rounded-br-md bg-slate-900 text-white' 
                : 'rounded-bl-md border border-slate-200 bg-white text-slate-700'
            }`}>
              {msg.role === 'assistant' ? <MarkdownRenderer content={msg.text} compact /> : <p>{msg.text}</p>}
            </div>
          </div>
        ))}

        {isChatting && (
          <div className="flex justify-start">
            <div className="flex items-center gap-3 rounded-3xl rounded-bl-md border border-slate-200 bg-white p-4 text-slate-500 shadow-sm">
              <Loader2 className="h-4 w-4 animate-spin text-cyan-700" />
              <span className="text-xs font-bold uppercase tracking-[0.24em]">Generating answer</span>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      <div className="border-t border-slate-200 bg-slate-50/80 p-5">
        <form onSubmit={onSendMessage} className="relative">
          <input
            placeholder="Ask anything..."
            className="w-full rounded-[24px] border border-slate-200 bg-white py-4 pl-4 pr-14 text-sm font-medium text-slate-900 outline-none transition-colors placeholder:text-slate-400 focus:border-cyan-300 focus:ring-4 focus:ring-cyan-100"
            value={currentQuestion}
            onChange={(e) => setCurrentQuestion(e.target.value)}
            disabled={isChatting}
          />
          <button 
            type="submit" 
            className="absolute right-2 top-1/2 inline-flex h-10 w-10 -translate-y-1/2 items-center justify-center rounded-2xl bg-slate-900 text-white shadow-sm transition-colors hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isChatting || !currentQuestion.trim()}
          >
            <Send className="h-4 w-4" />
          </button>
        </form>
      </div>
    </section>
  );
};

export default ChatSection;
