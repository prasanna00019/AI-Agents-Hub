import React from 'react';
import { SecondaryButton, DangerButton } from './Buttons';
import { Field } from './Field';

const TYPE_ICONS = {
  url:  '🔗',
  text: '📝',
  note: '📌',
  file: '📎',
};

export function SourceInbox({
  sourceDumps,
  newSourceDump,
  setNewSourceDump,
  addSourceDump,
  deleteSourceDump,
  inputClass,
  loading = false,
}) {
  return (
    <div className="mt-5 animate-fade-in rounded-xl border border-blue-100 bg-gradient-to-br from-blue-50/60 to-indigo-50/40 p-5">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-base">📥</span>
        <h4 className="text-sm font-bold text-slate-900">Source Inbox</h4>
      </div>
      <p className="text-[11px] text-slate-500 mb-4">
        Collect articles, URLs, and notes for this day's generation.
      </p>

      {/* Existing sources */}
      <div className="space-y-2 max-h-48 overflow-y-auto mb-4">
        {sourceDumps.map((sd) => (
          <div
            key={sd.id}
            className="flex items-center justify-between gap-3 rounded-lg border border-white bg-white px-3 py-2.5 shadow-sm transition hover:shadow-md"
          >
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-sm shrink-0">{TYPE_ICONS[sd.type] || '📄'}</span>
              <div className="min-w-0">
                {sd.label && (
                  <p className="text-xs font-semibold text-slate-700 truncate">{sd.label}</p>
                )}
                <p className="text-[11px] text-slate-500 truncate max-w-[280px]">{sd.raw_content}</p>
              </div>
            </div>
            <button
              onClick={() => {
                if (window.confirm('Remove this source?')) deleteSourceDump(sd.id);
              }}
              className="shrink-0 rounded-md px-2 py-1 text-[11px] font-semibold text-slate-400 transition hover:bg-rose-50 hover:text-rose-600"
            >
              Remove
            </button>
          </div>
        ))}
        {sourceDumps.length === 0 && (
          <div className="rounded-lg border border-dashed border-slate-200 bg-white/60 py-5 text-center text-xs text-slate-400">
            No sources added yet. Add URLs or text below.
          </div>
        )}
      </div>

      {/* Add new source */}
      <div className="space-y-3 rounded-lg border border-slate-100 bg-white p-3">
        <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
          <input
            className={inputClass}
            placeholder="Paste URL or enter text content…"
            value={newSourceDump.raw_content}
            onChange={(e) => setNewSourceDump((p) => ({ ...p, raw_content: e.target.value }))}
          />
          <select
            className={inputClass}
            value={newSourceDump.type}
            onChange={(e) => setNewSourceDump((p) => ({ ...p, type: e.target.value }))}
          >
            <option value="text">Text</option>
            <option value="url">URL</option>
            <option value="note">Note</option>
          </select>
        </div>
        <input
          className={inputClass}
          placeholder="Label (optional)"
          value={newSourceDump.label || ''}
          onChange={(e) => setNewSourceDump((p) => ({ ...p, label: e.target.value }))}
        />
        <SecondaryButton
          onClick={addSourceDump}
          loading={loading}
          disabled={!newSourceDump.raw_content}
        >
          Add Source
        </SecondaryButton>
      </div>
    </div>
  );
}
