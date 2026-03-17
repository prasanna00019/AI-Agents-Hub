import React from 'react';

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

export function AgentProgress({ logs = [], isRunning = false, currentDate = '' }) {
  const stepStatus = {};
  const stepMessages = {};

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
    <div className="animate-fade-in rounded-2xl border border-indigo-100 bg-gradient-to-br from-indigo-50/80 to-violet-50/50 p-5 shadow-lg shadow-indigo-100/50">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className={`h-2.5 w-2.5 rounded-full ${isRunning ? 'bg-indigo-500 animate-pulse-dot' : 'bg-emerald-500'}`} />
          <h3 className="text-sm font-bold text-slate-900">
            {isRunning ? 'Pipeline Running' : 'Pipeline Complete'}
          </h3>
        </div>
        {currentDate && (
          <span className="rounded-lg bg-white px-2.5 py-1 text-xs font-semibold text-slate-600 shadow-sm">
            {currentDate}
          </span>
        )}
      </div>

      {pipelineMessage && (
        <p className="mb-4 text-xs font-medium text-indigo-700/80">{pipelineMessage}</p>
      )}

      <div className="space-y-2">
        {STEPS.map(({ key, label, icon }) => {
          const status = stepStatus[key] || 'pending'
          const message = stepMessages[key] || ''

          return (
            <div
              key={key}
              className={`flex items-center gap-3 rounded-xl border px-4 py-2.5 transition-all duration-300 ${STATUS_STYLES[status] || STATUS_STYLES.pending}`}
            >
              <span className="shrink-0 text-base">{icon}</span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold">{label}</p>
                {message && <p className="mt-0.5 text-[11px] opacity-80">{message}</p>}
              </div>
              <span className="shrink-0 text-[10px] font-bold uppercase tracking-wider">
                {status === 'running' ? '…' : status === 'done' ? 'OK' : status === 'error' ? 'ERR' : status === 'warning' ? 'WARN' : 'WAIT'}
              </span>
            </div>
          )
        })}
      </div>

      {logs.length > 0 && (
        <div className="mt-5 rounded-2xl border border-white/80 bg-white/80 p-4">
          <div className="mb-3 flex items-center justify-between">
            <h4 className="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">Pipeline Events</h4>
            <span className="text-[11px] text-slate-400">{logs.length} event(s)</span>
          </div>
          <div className="max-h-72 space-y-2 overflow-y-auto pr-1">
            {logs.map((log, index) => (
              <div
                key={`${log.timestamp || index}-${log.step || 'event'}`}
                className={`rounded-xl border px-3 py-2 text-xs ${TIMELINE_STYLES[log.status] || 'border-slate-200 bg-slate-50 text-slate-600'}`}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-bold uppercase tracking-wider">{log.step || 'event'}</span>
                  <span className="rounded bg-white/80 px-2 py-0.5 text-[10px] font-semibold">{log.status || 'info'}</span>
                  {log.date && <span className="text-[10px] opacity-70">{log.date}</span>}
                </div>
                {log.message && <p className="mt-1 whitespace-pre-wrap break-words leading-relaxed">{log.message}</p>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
