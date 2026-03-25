import React from 'react';
import { Bot, Loader2, MessageSquare, Send } from 'lucide-react';
import MarkdownRenderer from './MarkdownRenderer';

const ChatSection = ({
  messages,
  currentQuestion,
  setCurrentQuestion,
  onSendMessage,
  isChatting,
  chatEndRef,
}) => {
  return (
    <section className="lg:col-span-4 sticky top-24 flex h-[calc(100vh-8rem)] min-h-[30rem] flex-col overflow-hidden rounded-[34px] max-lg:h-[32rem] app-card">
      <header className="border-b px-6 py-5" style={{ borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl text-white" style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-2))' }}>
            <MessageSquare className="h-5 w-5" />
          </div>
          <div>
            <p className="app-eyebrow">RAG chat</p>
            <h3 className="text-lg font-black app-title">Ask the saved note</h3>
          </div>
        </div>
      </header>

      <div className="scrollbar-surface flex-1 space-y-5 overflow-y-auto px-5 py-6">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center space-y-4 px-4 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full" style={{ background: 'color-mix(in srgb, var(--accent) 10%, white)', color: 'var(--accent)' }}>
              <Bot className="h-8 w-8" />
            </div>
            <p className="max-w-xs text-sm font-medium leading-relaxed app-muted">
              Ask about concepts, timestamps, or summaries. The answer is grounded in the stored note content and rebuilt vector context.
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[88%] rounded-3xl p-4 text-sm leading-relaxed shadow-sm ${
                msg.role === 'user' ? 'rounded-br-md app-primary-btn' : 'rounded-bl-md app-surface-strong'
              }`}
            >
              {msg.role === 'assistant' ? <MarkdownRenderer content={msg.text} compact /> : <p>{msg.text}</p>}
            </div>
          </div>
        ))}

        {isChatting && (
          <div className="flex justify-start">
            <div className="flex items-center gap-3 rounded-3xl rounded-bl-md p-4 shadow-sm app-card-strong app-muted">
              <Loader2 className="h-4 w-4 animate-spin" style={{ color: 'var(--accent)' }} />
              <span className="text-xs font-bold uppercase tracking-[0.24em]">Generating answer</span>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      <div className="border-t p-5 app-soft" style={{ borderColor: 'var(--border)' }}>
        <form onSubmit={onSendMessage} className="relative">
          <input
            placeholder="Ask anything..."
            className="field-shell w-full rounded-[24px] py-4 pl-4 pr-14 text-sm font-medium outline-none transition-colors"
            value={currentQuestion}
            onChange={(event) => setCurrentQuestion(event.target.value)}
            disabled={isChatting}
          />
          <button type="submit" className="absolute right-2 top-1/2 inline-flex h-10 w-10 -translate-y-1/2 items-center justify-center rounded-2xl app-primary-btn disabled:cursor-not-allowed disabled:opacity-60" disabled={isChatting || !currentQuestion.trim()}>
            <Send className="h-4 w-4" />
          </button>
        </form>
      </div>
    </section>
  );
};

export default ChatSection;
