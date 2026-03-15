import React, { useState } from 'react';
import { ArrowRight, Database, Play, Settings2, Sparkles, Youtube } from 'lucide-react';
import SettingsSection from './SettingsSection';
import ProcessingSteps from './ProcessingSteps';
import { useConfig } from '../context/ConfigContext';

const ProcessSection = ({ 
  url, setUrl, 
  onGenerate, 
  status, progress, 
  currentSteps 
}) => {
  const [showSettings, setShowSettings] = useState(false);
  const { config } = useConfig();

  return (
    <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_320px]">
      <section className="space-y-8">
        <div className="space-y-5 pt-8">
          <div className="inline-flex items-center gap-2 rounded-full border border-cyan-200 bg-white/80 px-4 py-2 text-[11px] font-bold uppercase tracking-[0.28em] text-cyan-700 shadow-sm">
            <Sparkles className="h-3.5 w-3.5" />
            Video to structured notes
          </div>
          <h2 className="max-w-4xl text-5xl font-black tracking-tight text-slate-900 sm:text-6xl lg:text-7xl">
            Turn long videos into study-ready notes you can search, save, and revisit.
          </h2>
          <p className="max-w-3xl text-lg leading-relaxed text-slate-600 sm:text-xl">
            Video2Notes extracts speech, organizes the important ideas into readable markdown notes, saves them to your database if you want, and lets you ask follow-up questions with RAG.
          </p>
        </div>

        <div className="rounded-[32px] border border-white/80 bg-[rgba(255,255,255,0.78)] p-5 shadow-[0_28px_80px_rgba(15,23,42,0.10)] backdrop-blur-xl sm:p-8">
          <form onSubmit={onGenerate} className="space-y-6">
            <label className="flex flex-col gap-3">
              <span className="text-[11px] font-bold uppercase tracking-[0.28em] text-slate-500">Video URL</span>
              <div className="flex items-center gap-3 rounded-[26px] border border-slate-200 bg-white px-5 py-4 shadow-sm transition-colors focus-within:border-cyan-300 focus-within:ring-4 focus-within:ring-cyan-100">
                <Youtube className="h-5 w-5 shrink-0 text-rose-500" />
                <input
                  type="url"
                  placeholder="https://youtube.com/watch?v=..."
                  className="w-full border-none bg-transparent text-lg font-medium text-slate-900 outline-none placeholder:text-slate-400"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  disabled={status === 'processing'}
                  required
                />
              </div>
            </label>

            <div className="flex flex-col gap-3 rounded-[26px] border border-slate-200 bg-slate-50/80 p-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-900">Advanced runtime settings</p>
                <p className="text-sm leading-relaxed text-slate-500">Whisper model, database URL, note detail, timestamps, and provider keys now live here.</p>
              </div>
              <button
                type="button"
                onClick={() => setShowSettings((value) => !value)}
                className="inline-flex items-center justify-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-100"
              >
                <Settings2 className={`h-4 w-4 transition-transform ${showSettings ? 'rotate-90' : ''}`} />
                {showSettings ? 'Hide settings' : 'Show settings'}
              </button>
            </div>

            {showSettings ? (
              <div className="rounded-[28px] border border-slate-200 bg-[rgba(248,250,252,0.9)] p-3 sm:p-4">
                <SettingsSection disabled={status === 'processing'} />
              </div>
            ) : null}

            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-3 text-sm text-slate-500">
                <Database className="h-4 w-4 text-teal-700" />
                {config.databaseUrl ? 'Saved notes will be written to your configured database.' : 'No database URL set. Processing still works, but library and caching stay disabled.'}
              </div>

              <button
                type="submit"
                disabled={status === 'processing' || !url}
                className="inline-flex items-center justify-center gap-3 rounded-full bg-slate-900 px-6 py-3 text-base font-bold text-white shadow-lg transition-transform hover:-translate-y-0.5 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {status === 'processing' ? <Play className="h-5 w-5 animate-pulse" /> : <ArrowRight className="h-5 w-5" />}
                {status === 'processing' ? 'Submitting request...' : 'Generate notes'}
              </button>
            </div>

            {status === 'error' ? (
              <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">
                {progress}
              </div>
            ) : null}
          </form>
        </div>

        {status === 'processing' ? (
          <section className="rounded-[30px] border border-cyan-100 bg-white/80 p-6 shadow-[0_24px_70px_rgba(14,165,233,0.08)] backdrop-blur-xl">
            <div className="mb-6 flex items-center justify-between gap-4">
              <div>
                <p className="text-[11px] font-bold uppercase tracking-[0.28em] text-cyan-700">Pipeline</p>
                <h3 className="mt-2 text-2xl font-black text-slate-900">{progress}</h3>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-cyan-50 text-cyan-700">
                <Play className="h-5 w-5 animate-pulse" />
              </div>
            </div>
            <ProcessingSteps currentSteps={currentSteps} />
          </section>
        ) : null}
      </section>

      <aside className="space-y-4 pt-8">
        <div className="rounded-[28px] border border-slate-200/80 bg-white/80 p-6 shadow-[0_20px_50px_rgba(15,23,42,0.08)] backdrop-blur-xl">
          <p className="text-[11px] font-bold uppercase tracking-[0.28em] text-slate-500">What this app does</p>
          <div className="mt-4 space-y-3 text-sm leading-relaxed text-slate-600">
            <p>Process a video URL into structured markdown notes with timestamps, topic grouping, and action items.</p>
            <p>Choose your LLM, whisper engine, note detail level, and transcription settings directly from the UI.</p>
            <p>Connect your own Postgres database to cache notes and reopen them later from the library.</p>
          </div>
        </div>

        <div className="rounded-[28px] border border-slate-200/80 bg-[linear-gradient(180deg,rgba(15,23,42,0.95),rgba(15,118,110,0.88))] p-6 text-white shadow-[0_24px_70px_rgba(15,23,42,0.16)]">
          <p className="text-[11px] font-bold uppercase tracking-[0.28em] text-cyan-100">Workflow</p>
          <div className="mt-4 space-y-3 text-sm leading-relaxed text-slate-100/90">
            <p>Generate notes from a video, review the markdown in a scrollable reader, and save a PDF from the print dialog.</p>
            <p>When a database URL is configured, every saved note can be reopened and queried again from the library view.</p>
          </div>
        </div>
      </aside>
    </div>
  );
};

export default ProcessSection;
