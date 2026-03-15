import React from 'react';
import { NavLink } from 'react-router-dom';
import { BookOpenText, Layers3, Sparkles } from 'lucide-react';

const Header = () => {
  const navItemClass = ({ isActive }) => [
    'inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition-colors',
    isActive ? 'bg-slate-900 text-white shadow-sm' : 'text-slate-600 hover:bg-white hover:text-slate-900',
  ].join(' ');

  return (
    <nav className="sticky top-0 z-50 border-b border-white/50 bg-[rgba(255,252,247,0.78)] backdrop-blur-xl">
      <div className="mx-auto flex h-18 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <NavLink to="/" className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[linear-gradient(135deg,#0f172a,#0f766e)] shadow-[0_12px_32px_rgba(15,23,42,0.18)]">
            <Sparkles className="h-5 w-5 text-white" />
          </div>
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.32em] text-teal-700">Workspace</p>
            <h1 className="text-lg font-black tracking-tight text-slate-900">Video2Notes</h1>
          </div>
        </NavLink>

        <div className="hidden items-center gap-2 rounded-full border border-slate-200 bg-white/80 p-1 shadow-sm md:flex">
          <NavLink to="/" className={navItemClass}>
            <Layers3 className="h-4 w-4" />
            Generate
          </NavLink>
          <NavLink to="/library" className={navItemClass}>
            <BookOpenText className="h-4 w-4" />
            Library
          </NavLink>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden rounded-full border border-cyan-200 bg-cyan-50 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.26em] text-cyan-700 lg:block">
            User-controlled runtime
          </div>
          <div className="flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-white shadow-sm">
            <div className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Header;
