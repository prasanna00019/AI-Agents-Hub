import React from 'react';

const STEPS = [
  { key: 'research',  label: 'Research',     icon: '🔍' },
  { key: 'summarize', label: 'Summarize',    icon: '📝' },
  { key: 'writer',    label: 'Write Draft',  icon: '✍️' },
  { key: 'formatter', label: 'Format',       icon: '🎨' },
  { key: 'quality',   label: 'Quality Check', icon: '✅' },
];

const STATUS_STYLES = {
  pending:  'bg-slate-100 text-slate-400 border-slate-200',
  running:  'bg-indigo-50 text-indigo-600 border-indigo-200 animate-pulse',
  done:     'bg-emerald-50 text-emerald-600 border-emerald-200',
  warning:  'bg-amber-50 text-amber-600 border-amber-200',
  error:    'bg-rose-50 text-rose-600 border-rose-200',
};

export function AgentProgress({ logs = [], isRunning = false, currentDate = '' }) {
  // Build status map from logs
  const stepStatus = {};
  const stepMessages = {};

  for (const log of logs) {
    if (log.step && log.step !== 'pipeline' && log.step !== 'error' && log.step !== 'timeout') {
      stepStatus[log.step] = log.status;
      stepMessages[log.step] = log.message || '';
    }
  }

  // Get latest pipeline message
  const pipelineLog = [...logs].reverse().find(l => l.step === 'pipeline');
  const pipelineMessage = pipelineLog?.message || '';

  if (!isRunning && logs.length === 0) return null;

  return (
    <div className="animate-fade-in rounded-2xl border border-indigo-100 bg-gradient-to-br from-indigo-50/80 to-violet-50/50 p-5 shadow-lg shadow-indigo-100/50">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2.5">
          <div className={`h-2.5 w-2.5 rounded-full ${isRunning ? 'bg-indigo-500 animate-pulse-dot' : 'bg-emerald-500'}`} />
          <h3 className="text-sm font-bold text-slate-900">
            {isRunning ? 'Agent Pipeline Running' : 'Generation Complete'}
          </h3>
        </div>
        {currentDate && (
          <span className="rounded-lg bg-white px-2.5 py-1 text-xs font-semibold text-slate-600 shadow-sm">
            {currentDate}
          </span>
        )}
      </div>

      {pipelineMessage && (
        <p className="mb-4 text-xs font-medium text-indigo-600/80">{pipelineMessage}</p>
      )}

      <div className="space-y-2">
        {STEPS.map(({ key, label, icon }, idx) => {
          const status = stepStatus[key] || (isRunning ? 'pending' : 'pending');
          const message = stepMessages[key] || '';

          return (
            <div
              key={key}
              className={`flex items-center gap-3 rounded-xl border px-4 py-2.5 transition-all duration-300 ${STATUS_STYLES[status] || STATUS_STYLES.pending}`}
            >
              <span className="text-base shrink-0">{icon}</span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold">{label}</p>
                {message && <p className="mt-0.5 text-[11px] opacity-70 truncate">{message}</p>}
              </div>
              <span className="shrink-0 text-[10px] font-bold uppercase tracking-wider">
                {status === 'running' ? '⟳' : status === 'done' ? '✓' : status === 'error' ? '✗' : '—'}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
