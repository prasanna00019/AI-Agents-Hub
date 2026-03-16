import React from 'react';

export function LoadingOverlay({ active, message = "Generating content...", logs = [] }) {
  if (!active) return null;
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/70 backdrop-blur-md p-4 animate-fade-in">
      <div className="w-full max-w-md rounded-3xl bg-white p-8 shadow-2xl animate-slide-in">
        <div className="flex flex-col items-center">
          {/* Spinner */}
          <div className="relative">
            <div className="h-14 w-14 rounded-full border-[3px] border-slate-200" />
            <div className="absolute inset-0 h-14 w-14 animate-spin rounded-full border-[3px] border-transparent border-t-indigo-600" />
          </div>
          <p className="mt-5 text-base font-bold text-slate-900">{message}</p>
          <p className="mt-1.5 text-xs text-slate-500">Executing multi-agent pipeline…</p>

          {/* Step indicators */}
          {logs.length > 0 && (
            <div className="mt-5 w-full max-h-40 overflow-y-auto space-y-1.5 rounded-xl bg-slate-50 p-3">
              {logs.slice(-8).map((log, i) => (
                <div key={i} className="flex items-center gap-2 text-[11px]">
                  <span className={`inline-block h-1.5 w-1.5 rounded-full shrink-0 ${
                    log.status === 'done' ? 'bg-emerald-500' :
                    log.status === 'running' ? 'bg-indigo-500 animate-pulse-dot' :
                    log.status === 'error' ? 'bg-rose-500' : 'bg-slate-300'
                  }`} />
                  <span className="font-semibold text-slate-600 capitalize">{log.step}</span>
                  <span className="text-slate-400 truncate">{log.message}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function SkeletonBlock({ className = '' }) {
  return <div className={`skeleton ${className}`} />;
}

export function SkeletonCard() {
  return (
    <div className="rounded-2xl border border-slate-100 bg-white p-5 space-y-3">
      <SkeletonBlock className="h-4 w-1/3" />
      <SkeletonBlock className="h-3 w-full" />
      <SkeletonBlock className="h-3 w-2/3" />
    </div>
  );
}

export function ButtonSpinner() {
  return (
    <svg className="inline-block h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}

export function InlineLoader({ text = 'Loading...' }) {
  return (
    <div className="flex items-center justify-center gap-2 py-8 text-sm text-slate-400">
      <ButtonSpinner />
      <span>{text}</span>
    </div>
  );
}
