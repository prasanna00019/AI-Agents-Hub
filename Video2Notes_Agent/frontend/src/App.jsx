import React from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import Header from './components/Header';
import HomeView from './views/HomeView';
import LibraryView from './views/LibraryView';
import ProcessingView from './views/ProcessingView';
import ResultView from './views/ResultView';

const App = () => {
  return (
    <div className="min-h-screen overflow-x-hidden text-slate-900 selection:bg-cyan-200 selection:text-slate-900">
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -left-24 top-10 h-72 w-72 rounded-full bg-[rgba(255,123,84,0.22)] blur-3xl" />
        <div className="absolute right-0 top-0 h-[28rem] w-[28rem] rounded-full bg-[rgba(15,118,110,0.15)] blur-3xl" />
        <div className="absolute bottom-0 left-1/3 h-96 w-96 rounded-full bg-[rgba(14,165,233,0.13)] blur-3xl" />
        <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(255,255,255,0.72),rgba(247,244,236,0.92))]" />
      </div>

      <Header />

      <main className="relative z-10 mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <Routes>
          <Route path="/" element={<HomeView />} />
          <Route path="/library" element={<LibraryView />} />
          <Route path="/process/:taskId" element={<ProcessingView />} />
          <Route path="/result/:taskId" element={<ResultView />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>

      <footer className="relative z-10 mt-20 border-t border-slate-200/70 bg-white/50 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-8 text-sm text-slate-600 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
          <p className="max-w-2xl leading-relaxed">
            Turn long-form videos into structured notes, keep them in your own Postgres database, and reopen any saved note for RAG chat without touching backend source files.
          </p>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">
            Video2Notes Workspace
          </p>
        </div>
      </footer>
    </div>
  );
};

export default App;
