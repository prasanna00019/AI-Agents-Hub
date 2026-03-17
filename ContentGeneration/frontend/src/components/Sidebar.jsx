import React from 'react';

// ── Sidebar ─────────────────────────────────────────────────────────────
const NAV_ITEMS = [
  { key: 'dashboard', label: 'Dashboard', icon: '⬡' },
  { key: 'channels',  label: 'Channels',  icon: '◈' },
  { key: 'planner',   label: 'Planner',   icon: '◇' },
  { key: 'calendar',  label: 'Calendar',  icon: '▦' },
  { key: 'review',    label: 'Review',    icon: '◎' },
  { key: 'settings',  label: 'Settings',  icon: '⚙' },
]

export function Sidebar({
  activeView,
  setActiveView,
  channels,
  selectedChannelId,
  setSelectedChannelId,
  health,
  modelsCount,
  isMobileOpen,
  setMobileOpen,
}) {
  return (
    <>
      {/* Mobile overlay */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside
        className={`
          fixed inset-y-0 left-0 z-50 flex w-72 flex-col bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950
          shadow-2xl transition-transform duration-300 lg:static lg:translate-x-0 lg:rounded-2xl
          ${isMobileOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        {/* Brand */}
        <div className="px-6 pt-7 pb-2">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 text-sm font-bold text-white shadow-lg shadow-brand-600/30">
              CP
            </div>
            <div>
              <h1 className="text-base font-bold tracking-tight text-white">ContentPilot</h1>
              <p className="text-[11px] font-medium text-brand-200/70">Agentic Content Platform</p>
            </div>
          </div>
        </div>

        {/* Status */}
        <div className="mx-5 mt-4 rounded-xl border border-white/5 bg-white/5 px-4 py-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-300">Backend</span>
            <span className={`flex items-center gap-1.5 text-[11px] font-semibold ${
              health === 'connected' ? 'text-emerald-400' : health === 'down' ? 'text-rose-400' : 'text-amber-400'
            }`}>
              <span className={`inline-block h-1.5 w-1.5 rounded-full ${
                health === 'connected' ? 'bg-emerald-400 animate-pulse-dot' : health === 'down' ? 'bg-rose-400' : 'bg-amber-400 animate-pulse-dot'
              }`} />
              {health}
            </span>
          </div>
          <p className="mt-1.5 text-[11px] text-slate-500">{modelsCount} models · {channels.length} channels</p>
        </div>

        {/* Navigation */}
        <nav className="mt-6 flex-1 space-y-1 px-3 overflow-y-auto">
          {NAV_ITEMS.map(({ key, label, icon }) => (
            <button
              key={key}
              onClick={() => { setActiveView(key); setMobileOpen(false); }}
              className={`flex w-full items-center gap-3 rounded-xl px-4 py-2.5 text-sm font-medium transition-all duration-200 ${
                activeView === key
                  ? 'bg-gradient-to-r from-brand-600/80 to-brand-700/60 text-white shadow-lg shadow-brand-700/20'
                  : 'text-slate-300 hover:bg-white/5 hover:text-white'
              }`}
            >
              <span className="text-base">{icon}</span>
              <span>{label}</span>
            </button>
          ))}
        </nav>

        {/* Channels */}
        <div className="mx-3 mb-3 rounded-xl border border-white/5 bg-white/[0.03]">
          <div className="flex items-center justify-between border-b border-white/5 px-4 py-2.5">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Channels</h3>
            <button
              onClick={() => { setActiveView('channels'); setMobileOpen(false); }}
              className="text-[11px] font-semibold text-brand-300 hover:text-brand-200 transition"
            >
              + New
            </button>
          </div>
          <div className="max-h-52 overflow-y-auto p-2 space-y-1">
            {channels.length === 0 && (
              <p className="px-3 py-4 text-center text-xs text-slate-600">No channels yet</p>
            )}
            {channels.map((ch) => (
              <button
                key={ch.id}
                onClick={() => {
                  setSelectedChannelId(ch.id);
                  setActiveView('planner');
                  setMobileOpen(false);
                }}
                className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-left transition ${
                  selectedChannelId === ch.id
                    ? 'bg-brand-600/20 text-brand-200'
                    : 'text-slate-300 hover:bg-white/5 hover:text-slate-200'
                }`}
              >
                <span className="truncate text-sm font-medium">{ch.name}</span>
                <span className="ml-2 shrink-0 rounded-md bg-white/10 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-300">
                  {ch.platform}
                </span>
              </button>
            ))}
          </div>
        </div>
      </aside>
    </>
  );
}

// ── Mobile hamburger ────────────────────────────────────────────────────
export function MobileHeader({ setMobileOpen, activeView }) {
  return (
    <div className="sticky top-0 z-30 flex items-center justify-between border-b border-slate-200 bg-white/80 px-4 py-3 backdrop-blur-xl lg:hidden">
      <button
        onClick={() => setMobileOpen(true)}
        className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200 transition"
      >
        ☰
      </button>
      <span className="text-sm font-semibold text-slate-900 capitalize">{activeView}</span>
      <div className="w-9" />
    </div>
  );
}
