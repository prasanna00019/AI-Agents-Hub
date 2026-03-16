import React from 'react';

export function MetricCard({ label, value, hint, icon }) {
  return (
    <div className="rounded-xl border border-slate-100 bg-gradient-to-br from-white to-slate-50 px-4 py-3.5 shadow-sm transition hover:shadow-md">
      <div className="flex items-center justify-between">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">{label}</p>
        {icon && <span className="text-sm text-slate-400">{icon}</span>}
      </div>
      <p className="mt-2 text-2xl font-bold text-slate-900">{value}</p>
      <p className="mt-1 text-[11px] text-slate-400">{hint}</p>
    </div>
  );
}

export function Panel({ title, subtitle, children, className = '' }) {
  return (
    <section className={`rounded-2xl border border-slate-100 bg-white p-6 shadow-sm ${className}`}>
      <div className="mb-5">
        <h2 className="text-lg font-bold text-slate-900">{title}</h2>
        {subtitle && <p className="mt-1 text-xs text-slate-500">{subtitle}</p>}
      </div>
      {children}
    </section>
  );
}
