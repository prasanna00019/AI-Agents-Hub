import React, { useState, useMemo } from 'react';

const STATUS_BADGES = {
  ready:      { bg: 'bg-emerald-100', border: 'border-emerald-300', text: 'text-emerald-900', dot: 'bg-emerald-600', label: 'Ready' },
  draft:      { bg: 'bg-amber-100', border: 'border-amber-300', text: 'text-amber-900', dot: 'bg-amber-600', label: 'Draft' },
  collecting: { bg: 'bg-blue-100', border: 'border-blue-300', text: 'text-blue-900', dot: 'bg-blue-600', label: 'Collecting' },
  empty:      { bg: 'bg-slate-100', border: 'border-slate-300', text: 'text-slate-700', dot: 'bg-slate-500', label: 'Empty' },
};

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const WEEKDAY_FULL = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];

// Helper to get local YYYY-MM-DD string
function getLocalDateString(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

export function ContentCalendar({
  selectedChannel,
  weeklyTemplateDraft,
  reviewQueue,
  setOverrideForm,
  sourceDumpCounts = {},
}) {
  const [currentMonth, setCurrentMonth] = useState(() => {
    const now = new Date();
    return { year: now.getFullYear(), month: now.getMonth() };
  });

  const calendarDays = useMemo(() => {
    const { year, month } = currentMonth;
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);

    // Monday-based: 0=Mon, 6=Sun
    let startPad = (firstDay.getDay() + 6) % 7;

    const days = [];

    // Padding from previous month
    for (let i = startPad - 1; i >= 0; i--) {
      const d = new Date(year, month, -i);
      days.push({ date: d, isCurrentMonth: false });
    }

    // Current month
    for (let d = 1; d <= lastDay.getDate(); d++) {
      days.push({ date: new Date(year, month, d), isCurrentMonth: true });
    }

    // Fill remaining to complete grid (up to 42 cells = 6 rows)
    while (days.length < 42) {
      const d = new Date(year, month + 1, days.length - startPad - lastDay.getDate() + 1);
      days.push({ date: d, isCurrentMonth: false });
    }

    return days;
  }, [currentMonth]);

  const monthLabel = new Date(currentMonth.year, currentMonth.month).toLocaleDateString('en-US', {
    month: 'long',
    year: 'numeric',
  });

  const prevMonth = () => setCurrentMonth((prev) => {
    const m = prev.month - 1;
    return m < 0 ? { year: prev.year - 1, month: 11 } : { year: prev.year, month: m };
  });

  const nextMonth = () => setCurrentMonth((prev) => {
    const m = prev.month + 1;
    return m > 11 ? { year: prev.year + 1, month: 0 } : { year: prev.year, month: m };
  });

  const today = getLocalDateString(new Date());

  if (!selectedChannel) return null;

  return (
    <div className="mt-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-bold text-slate-900">Content Calendar</h3>
          <p className="mt-0.5 text-xs text-slate-600">Click any day to plan or override content</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={prevMonth} className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 transition text-sm">‹</button>
          <span className="min-w-[140px] text-center text-sm font-semibold text-slate-800">{monthLabel}</span>
          <button onClick={nextMonth} className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 transition text-sm">›</button>
        </div>
      </div>

      {/* Weekday headers */}
      <div className="grid grid-cols-7 gap-1 mb-1">
        {WEEKDAYS.map((d) => (
          <div key={d} className="py-2 text-center text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            {d}
          </div>
        ))}
      </div>

      {/* Calendar grid */}
      <div className="grid grid-cols-7 gap-1">
        {calendarDays.map(({ date, isCurrentMonth }, idx) => {
          const dateStr = getLocalDateString(date);
          const dayIndex = (date.getDay() + 6) % 7; // Monday=0, Sunday=6
          const dayKey = WEEKDAY_FULL[dayIndex];
          const isToday = dateStr === today;

          const override = selectedChannel.overrides?.[dateStr] || {};
          const templatePillar = weeklyTemplateDraft[dayKey] || 'General';
          const pillar = override.pillar || templatePillar;
          const hasOverride = !!override.pillar || !!override.topic;

          const reviewItem = reviewQueue.find((r) => r.date === dateStr);
          const status = reviewItem?.status || (override.mode === 'source_dump' ? 'collecting' : 'empty');
          const badge = STATUS_BADGES[status] || STATUS_BADGES.empty;

          const dumpCount = sourceDumpCounts[dateStr] || 0;

          return (
            <button
              key={dateStr + idx}
              onClick={() => {
                setOverrideForm({
                  date: dateStr,
                  pillar: override.pillar || '',
                  topic: override.topic || '',
                  special_instructions: override.special_instructions || '',
                  mode: override.mode || 'pre_generated',
                });
              }}
              className={`group relative flex min-h-[80px] flex-col rounded-xl border p-2 text-left transition-all duration-200 hover:shadow-md hover:scale-[1.02] ${
                isCurrentMonth
                  ? `${badge.bg} ${badge.border} ${badge.text}`
                  : 'bg-slate-50 border-slate-200 text-slate-500'
              } ${isToday ? 'ring-2 ring-indigo-400 ring-offset-1' : ''}`}
            >
              {/* Day number */}
              <span className={`text-xs font-bold ${isToday ? 'text-indigo-600' : ''}`}>
                {date.getDate()}
              </span>

              {/* Pillar label */}
              {isCurrentMonth && (
                <span className="mt-1 text-[10px] font-medium leading-tight line-clamp-2">
                  {pillar}
                </span>
              )}

              {/* Status dot */}
              {isCurrentMonth && status !== 'empty' && (
                <span className={`mt-auto inline-flex items-center gap-1 text-[9px] font-bold uppercase tracking-wider`}>
                  <span className={`h-1.5 w-1.5 rounded-full ${badge.dot}`} />
                  {badge.label}
                </span>
              )}

              {/* Source dump count badge */}
              {isCurrentMonth && dumpCount > 0 && (
                <span className="absolute left-1.5 bottom-1.5 inline-flex items-center gap-0.5 rounded-md bg-indigo-200 px-1.5 py-0.5 text-[9px] font-bold text-indigo-800" title={`${dumpCount} source(s) dumped`}>
                  📎 {dumpCount}
                </span>
              )}

              {/* Override indicator */}
              {hasOverride && isCurrentMonth && (
                <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-violet-500" title="Has override" />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
