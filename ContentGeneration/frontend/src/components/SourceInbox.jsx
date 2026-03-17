import React from 'react';
import { SecondaryButton } from './Buttons';

const TYPE_ICONS = {
  url: '🔗',
  text: '📝',
  note: '📌',
};

export function SourceInbox({
  title = 'Source Inbox',
  description = 'Collect URLs, notes, and raw text for this run.',
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
      <div className="mb-1 flex items-center gap-2">
        <span className="text-base">📥</span>
        <h4 className="text-sm font-bold text-slate-900">{title}</h4>
      </div>
      <p className="mb-4 text-[11px] text-slate-500">{description}</p>

      <div className="mb-4 space-y-2 max-h-48 overflow-y-auto">
        {sourceDumps.map((source) => (
          <div
            key={source.id}
            className="flex items-center justify-between gap-3 rounded-lg border border-white bg-white px-3 py-2.5 shadow-sm transition hover:shadow-md"
          >
            <div className="min-w-0 flex items-center gap-2">
              <span className="shrink-0 text-sm">{TYPE_ICONS[source.type] || '📄'}</span>
              <div className="min-w-0">
                {source.label && (
                  <p className="truncate text-xs font-semibold text-slate-700">{source.label}</p>
                )}
                <p className="max-w-[360px] truncate text-[11px] text-slate-500">{source.raw_content}</p>
              </div>
            </div>
            <button
              onClick={() => {
                if (window.confirm('Remove this source?')) deleteSourceDump(source.id)
              }}
              className="shrink-0 rounded-md px-2 py-1 text-[11px] font-semibold text-slate-400 transition hover:bg-rose-50 hover:text-rose-600"
            >
              Remove
            </button>
          </div>
        ))}
        {sourceDumps.length === 0 && (
          <div className="rounded-lg border border-dashed border-slate-200 bg-white/60 py-5 text-center text-xs text-slate-400">
            No sources added yet. Add URLs, notes, or raw source text below.
          </div>
        )}
      </div>

      <div className="space-y-3 rounded-lg border border-slate-100 bg-white p-3">
        <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
          <select
            className={inputClass}
            value={newSourceDump.type}
            onChange={(e) => setNewSourceDump((prev) => ({ ...prev, type: e.target.value }))}
          >
            <option value="url">URL</option>
            <option value="text">Text</option>
            <option value="note">Note</option>
          </select>
          <input
            className={inputClass}
            placeholder="Label (optional)"
            value={newSourceDump.label || ''}
            onChange={(e) => setNewSourceDump((prev) => ({ ...prev, label: e.target.value }))}
          />
        </div>

        <textarea
          className={`${inputClass} min-h-[120px] resize-y`}
          placeholder={
            newSourceDump.type === 'url'
              ? 'Paste one URL or a list of URLs.'
              : newSourceDump.type === 'note'
                ? 'Add notes or angle ideas for later generation.'
                : 'Paste source text, article excerpts, or summaries.'
          }
          value={newSourceDump.raw_content}
          onChange={(e) => setNewSourceDump((prev) => ({ ...prev, raw_content: e.target.value }))}
        />

        <SecondaryButton
          onClick={addSourceDump}
          loading={loading}
          disabled={!newSourceDump.raw_content.trim()}
        >
          Add Source
        </SecondaryButton>
      </div>
    </div>
  )
}
