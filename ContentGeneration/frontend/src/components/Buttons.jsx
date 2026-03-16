import React from 'react';
import { ButtonSpinner } from './Loading';

export function PrimaryButton({ children, onClick, disabled, loading = false, className = '' }) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-600/20 transition-all duration-200 hover:from-indigo-700 hover:to-violet-700 hover:shadow-xl hover:shadow-indigo-600/30 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98] ${className}`}
      onClick={onClick}
      disabled={disabled || loading}
    >
      {loading && <ButtonSpinner />}
      {children}
    </button>
  );
}

export function SecondaryButton({ children, onClick, disabled, loading = false, className = '' }) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition-all duration-200 hover:bg-slate-50 hover:border-slate-300 hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98] ${className}`}
      onClick={onClick}
      disabled={disabled || loading}
    >
      {loading && <ButtonSpinner />}
      {children}
    </button>
  );
}

export function DangerButton({ children, onClick, disabled, loading = false, className = '' }) {
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-rose-500 to-red-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-rose-600/20 transition-all duration-200 hover:from-rose-600 hover:to-red-700 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98] ${className}`}
      onClick={onClick}
      disabled={disabled || loading}
    >
      {loading && <ButtonSpinner />}
      {children}
    </button>
  );
}
