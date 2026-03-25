import React from 'react';
import { NavLink } from 'react-router-dom';
import { BookOpenText, Layers3, Palette, Sparkles } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

const Header = () => {
  const { theme, setTheme, themes } = useTheme();

  const navItemClass = ({ isActive }) => [
    'app-nav-link',
    isActive
      ? 'app-nav-link--active'
      : '',
  ].join(' ');

  return (
    <nav
      className="sticky top-0 z-50 border-b backdrop-blur-2xl"
      style={{ borderColor: 'var(--border)', background: 'linear-gradient(180deg, color-mix(in srgb, var(--header) 96%, white), var(--header))' }}
    >
      <div className="mx-auto flex max-w-[1720px] flex-col gap-3 px-4 py-4 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8 xl:px-10">
        <div className="flex items-center justify-between gap-4">
          <NavLink to="/" className="group flex items-center gap-4">
            <div
              className="flex h-12 w-12 items-center justify-center rounded-[1.15rem] shadow-[0_18px_38px_rgba(15,23,42,0.18)] transition-transform duration-300 group-hover:scale-105"
              style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-2))' }}
            >
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.32em] app-muted">Workspace</p>
              <h1 className="text-lg font-black tracking-tight app-gradient-text sm:text-xl">Video2Notes</h1>
            </div>
          </NavLink>

          <div className="hidden rounded-full px-3 py-1 text-[11px] font-bold uppercase tracking-[0.26em] lg:block app-chip">
            Runtime controlled
          </div>
        </div>

        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-end">
          <div className="flex items-center gap-2 rounded-full p-1 app-surface-strong" style={{ background: 'linear-gradient(135deg, color-mix(in srgb, var(--card-strong) 96%, white), color-mix(in srgb, var(--card) 92%, white))' }}>
            <NavLink to="/" className={navItemClass}>
              <Layers3 className="h-4 w-4" />
              Generate
            </NavLink>
            <NavLink to="/library" className={navItemClass}>
              <BookOpenText className="h-4 w-4" />
              Library
            </NavLink>
          </div>

          <label className="flex items-center gap-3 rounded-full px-4 py-2 app-surface-strong" style={{ background: 'linear-gradient(135deg, color-mix(in srgb, var(--card-strong) 96%, white), color-mix(in srgb, var(--card) 90%, white))' }}>
            <Palette className="h-4 w-4" style={{ color: 'var(--accent)' }} />
            <select
              value={theme}
              onChange={(event) => setTheme(event.target.value)}
              className="theme-select rounded-full px-3 py-2 text-sm font-semibold outline-none"
            >
              {themes.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>
    </nav>
  );
};

export default Header;
