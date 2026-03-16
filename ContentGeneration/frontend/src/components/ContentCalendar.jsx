import React, { useState, useMemo } from 'react';

const STATUS_BADGES = {
  ready:      { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-700', dot: 'bg-emerald-500', label: 'Ready' },
  draft:      { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-700', dot: 'bg-amber-500', label: 'Draft' },
  collecting: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700', dot: 'bg-blue-500', label: 'Collecting' },
  empty:      { bg: 'bg-slate-50', border: 'border-slate-200', text: 'text-slate-400', dot: 'bg-slate-300', label: 'Empty' },
};

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const WEEKDAY_FULL = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];

export function ContentCalendar({
  selectedChannel,
  weeklyTemplateDraft,
  reviewQueue,
  setOverrideForm,
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

  const today = new Date().toISOString().slice(0, 10);

  if (!selectedChannel) return null;

  return (
    <div className="mt-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-bold text-slate-900">Content Calendar</h3>
          <p className="mt-0.5 text-xs text-slate-500">Click any day to plan or override content</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={prevMonth} className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 transition text-sm">‹</button>
          <span className="min-w-[140px] text-center text-sm font-semibold text-slate-800">{monthLabel}</span>
          <button onClick={nextMonth} className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 transition text-sm">›</button>
        </div>
      </div>

      {/* Weekday headers */}
      <div className="grid grid-cols-7 gap-1 mb-1">
        {WEEKDAYS.map((d) => (
          <div key={d} className="py-2 text-center text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            {d}
          </div>
        ))}
      </div>

      {/* Calendar grid */}
      <div className="grid grid-cols-7 gap-1">
        {calendarDays.map(({ date, isCurrentMonth }, idx) => {
          const dateStr = date.toISOString().slice(0, 10);
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
                  : 'bg-slate-25 border-slate-100 text-slate-300'
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
