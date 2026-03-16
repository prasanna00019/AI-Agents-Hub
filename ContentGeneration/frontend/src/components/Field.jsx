import React from 'react';

export function Field({ label, help, children, className = '', dark = false }) {
  return (
    <label className={`block text-sm ${className}`}>
      <span className={`mb-1.5 block text-xs font-semibold uppercase tracking-wider ${dark ? 'text-slate-300' : 'text-slate-500'}`}>
        {label}
      </span>
      {children}
      {help && <span className={`mt-1.5 block text-[11px] ${dark ? 'text-slate-500' : 'text-slate-400'}`}>{help}</span>}
    </label>
  );
}

export function EmptyState({ text, icon = '◇' }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-200 bg-gradient-to-br from-slate-50 to-white px-6 py-10 text-center">
      <p className="text-2xl text-slate-300 mb-2">{icon}</p>
      <p className="text-sm text-slate-400">{text}</p>
    </div>
  );
}
