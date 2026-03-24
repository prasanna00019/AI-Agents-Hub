import React from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import Header from './components/Header';
import HomeView from './views/HomeView';
import LibraryView from './views/LibraryView';
import ProcessingView from './views/ProcessingView';
import ResultView from './views/ResultView';
import BatchView from './views/BatchView';

const App = () => {
  return (
    <div className="min-h-screen overflow-x-hidden selection:bg-cyan-200 selection:text-slate-900" style={{ color: 'var(--ink)' }}>
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -left-24 top-10 h-72 w-72 rounded-full blur-3xl" style={{ background: 'color-mix(in srgb, var(--accent-3) 24%, transparent)' }} />
        <div className="absolute right-0 top-0 h-[28rem] w-[28rem] rounded-full blur-3xl" style={{ background: 'color-mix(in srgb, var(--accent) 16%, transparent)' }} />
        <div className="absolute bottom-0 left-1/3 h-96 w-96 rounded-full blur-3xl" style={{ background: 'color-mix(in srgb, var(--accent-2) 14%, transparent)' }} />
        <div className="absolute inset-0" style={{ background: 'linear-gradient(135deg, var(--page-bg-alt), var(--page-bg))' }} />
      </div>

      <Header />

      <main className="relative z-10 mx-auto max-w-[1700px] px-4 py-8 sm:px-6 lg:px-8 xl:px-10">
        <Routes>
          <Route path="/" element={<HomeView />} />
          <Route path="/library" element={<LibraryView />} />
          <Route path="/process/:taskId" element={<ProcessingView />} />
          <Route path="/batch/:batchId" element={<BatchView />} />
          <Route path="/result/:taskId" element={<ResultView />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>

      <footer className="relative z-10 mt-20 border-t backdrop-blur-xl" style={{ borderColor: 'var(--border)', background: 'var(--header)' }}>
        <div className="mx-auto flex max-w-[1700px] flex-col gap-3 px-4 py-8 text-sm sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8 xl:px-10">
          <p className="max-w-2xl leading-relaxed app-muted">
            Turn long-form videos into structured notes, study assets, and searchable library entries with reusable caching and theme-aware workflows.
          </p>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] app-muted">
            Video2Notes Workspace
          </p>
        </div>
      </footer>
    </div>
  );
};

export default App;
