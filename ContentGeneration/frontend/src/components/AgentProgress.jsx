import React, { useEffect, useRef } from 'react';

const STEPS = [
  { key: 'research', label: 'Research', icon: '🔎' },
  { key: 'summarize', label: 'RAG + Summary', icon: '🧠' },
  { key: 'writer', label: 'Draft', icon: '✍️' },
  { key: 'formatter', label: 'Format', icon: '🎨' },
  { key: 'quality', label: 'Quality Check', icon: '✅' },
];

const STATUS_STYLES = {
  pending: 'bg-slate-100 text-slate-400 border-slate-200',
  running: 'bg-indigo-50 text-indigo-600 border-indigo-200 animate-pulse',
  done: 'bg-emerald-50 text-emerald-600 border-emerald-200',
  warning: 'bg-amber-50 text-amber-600 border-amber-200',
  error: 'bg-rose-50 text-rose-600 border-rose-200',
};

const TIMELINE_STYLES = {
  running: 'border-indigo-200 bg-indigo-50 text-indigo-700',
  done: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  warning: 'border-amber-200 bg-amber-50 text-amber-700',
  error: 'border-rose-200 bg-rose-50 text-rose-700',
};

export function AgentProgress({ logs = [], isRunning = false, currentDate = '', onClose }) {
  const stepStatus = {};
  const stepMessages = {};
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  for (const log of logs) {
    if (log.step && STEPS.some((step) => step.key === log.step)) {
      stepStatus[log.step] = log.status
      stepMessages[log.step] = log.message || ''
    }
  }

  const pipelineLog = [...logs].reverse().find((log) => log.step === 'pipeline')
  const pipelineMessage = pipelineLog?.message || ''

  if (!isRunning && logs.length === 0) return null

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/70 p-4 backdrop-blur-sm transition-all duration-300 animate-fade-in">
      <div className="flex h-full max-h-[85vh] w-full max-w-5xl flex-col overflow-hidden rounded-3xl bg-white shadow-2xl animate-slide-in xl:flex-row">
        
        {/* Left/Top: Steps Overview */}
        <div className="w-full shrink-0 border-b border-slate-100 bg-gradient-to-br from-indigo-50/50 to-violet-50/30 p-6 xl:w-[340px] xl:border-b-0 xl:border-r">
          <div className="mb-6 flex items-start justify-between">
            <div>
              <div className="flex items-center gap-3">
                <div className={`h-3 w-3 rounded-full ${isRunning ? 'bg-indigo-500 animate-pulse-dot' : 'bg-emerald-500'}`} />
                <h3 className="text-xl font-bold text-slate-900">
                  {isRunning ? 'Pipeline Running' : 'Pipeline Complete'}
                </h3>
              </div>
              {currentDate && (
                <span className="mt-3 inline-block rounded-lg bg-white px-2.5 py-1 text-xs font-semibold text-slate-600 shadow-sm border border-slate-100">
                  Target Date: {currentDate}
                </span>
              )}
            </div>
          </div>

          {pipelineMessage && (
            <div className="mb-6 rounded-xl bg-indigo-100/50 p-3">
              <p className="text-xs font-medium text-indigo-800 leading-relaxed">{pipelineMessage}</p>
            </div>
          )}

          <div className="space-y-2.5">
            {STEPS.map(({ key, label, icon }) => {
              const status = stepStatus[key] || 'pending'
              const message = stepMessages[key] || ''

              return (
                <div
                  key={key}
                  className={`flex items-center gap-3 rounded-xl border px-4 py-3 transition-all duration-300 ${STATUS_STYLES[status] || STATUS_STYLES.pending}`}
                >
                  <span className="shrink-0 text-lg sm:text-xl">{icon}</span>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-bold">{label}</p>
                    {message && <p className="mt-0.5 text-xs opacity-80 leading-snug">{message}</p>}
                  </div>
                  <span className="shrink-0 text-[10px] font-extrabold uppercase tracking-widest opacity-70">
                    {status === 'running' ? '…' : status === 'done' ? 'OK' : status === 'error' ? 'ERR' : status === 'warning' ? 'WARN' : 'WAIT'}
                  </span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Right/Bottom: detailed logs */}
        <div className="flex flex-1 flex-col overflow-hidden bg-slate-50/50 p-6">
          <div className="mb-4 flex items-center justify-between">
            <h4 className="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Execution Logs</h4>
            <span className="rounded-full bg-slate-200 px-3 py-1 text-[11px] font-bold text-slate-500">{logs.length} events</span>
          </div>
          
          <div 
            ref={scrollRef} 
            className="flex-1 space-y-3 overflow-y-auto pr-3 scroll-smooth rounded-2xl border border-slate-200 bg-white p-4 shadow-inner"
          >
            {logs.length === 0 ? (
              <p className="text-center text-sm text-slate-400 mt-10 font-medium">Waiting for pipeline to start...</p>
            ) : (
              logs.map((log, index) => (
                <div
                  key={`${log.timestamp || index}-${log.step || 'event'}`}
                  className={`rounded-xl border px-4 py-3 text-sm transition-all duration-300 ${TIMELINE_STYLES[log.status] || 'border-slate-100 bg-slate-50 text-slate-600'}`}
                >
                  <div className="mb-1.5 flex flex-wrap items-center gap-2">
                    <span className="font-extrabold uppercase tracking-wider text-[11px]">{log.step || 'system'}</span>
                    <span className="rounded-md bg-white/80 px-2 py-0.5 text-[10px] font-bold shadow-sm">{log.status || 'info'}</span>
                    {log.date && <span className="text-[10px] font-medium opacity-60 ml-auto">{log.date}</span>}
                  </div>
                  {log.message && <div className="mt-2 text-[13px] leading-relaxed whitespace-pre-wrap font-medium">{log.message}</div>}
                </div>
              ))
            )}
          </div>

          {!isRunning && (
            <div className="mt-6 flex justify-end shrink-0">
              <button 
                onClick={onClose} 
                className="rounded-xl bg-slate-900 px-8 py-3 text-sm font-bold text-white shadow-lg transition-transform hover:scale-105 active:scale-95"
              >
                Close & View Results
              </button>
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
