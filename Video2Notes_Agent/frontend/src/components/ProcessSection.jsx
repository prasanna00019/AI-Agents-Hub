import React, { useRef, useState } from 'react';
import { ArrowRight, Database, Play, Settings2, Sparkles, Upload, Youtube } from 'lucide-react';
import SettingsSection from './SettingsSection';
import ProcessingSteps from './ProcessingSteps';
import { useConfig } from '../context/ConfigContext';

const ProcessSection = ({
  mode,
  setMode,
  url,
  setUrl,
  file,
  setFile,
  onGenerate,
  status,
  progress,
  currentSteps,
  uploadProgress,
}) => {
  const fileInputRef = useRef(null);
  const [showSettings, setShowSettings] = useState(false);
  const { config } = useConfig();

  const isProcessing = status === 'processing';
  const handleDrop = (event) => {
    event.preventDefault();
    const droppedFile = event.dataTransfer?.files?.[0];
    if (droppedFile) {
      setFile(droppedFile);
    }
  };

  return (
    <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_320px]">
      <section className="space-y-8">
        <div className="space-y-5 pt-8">
          <div className="inline-flex items-center gap-2 rounded-full px-4 py-2 text-[11px] font-bold uppercase tracking-[0.28em] shadow-sm app-pill">
            <Sparkles className="h-3.5 w-3.5" />
            Video to structured notes
          </div>
          <h2 className="max-w-4xl text-5xl font-black tracking-tight app-title sm:text-6xl lg:text-7xl">
            Turn videos, uploads, and playlists into notes you can search, save, and study.
          </h2>
          <p className="max-w-3xl text-lg leading-relaxed app-muted sm:text-xl">
            Video2Notes now supports local uploads, Google Drive shared videos, YouTube playlists, reusable transcript caching, and richer note outputs without giving up the current single-video workflow.
          </p>
        </div>

        <div className="rounded-[32px] p-5 sm:p-8 app-card">
          <div className="mb-5 grid gap-3 sm:grid-cols-2">
            <button
              type="button"
              onClick={() => setMode('url')}
              className={`rounded-[24px] px-5 py-4 text-left transition-colors ${mode === 'url' ? 'app-primary-btn' : 'app-card-strong'}`}
            >
              <div className="flex items-center gap-3">
                <Youtube className="h-5 w-5" />
                <div>
                  <p className="text-sm font-bold">URL or playlist</p>
                  <p className="text-xs opacity-80">YouTube, Google Drive shared files, and YouTube playlists.</p>
                </div>
              </div>
            </button>
            <button
              type="button"
              onClick={() => setMode('upload')}
              className={`rounded-[24px] px-5 py-4 text-left transition-colors ${mode === 'upload' ? 'app-primary-btn' : 'app-card-strong'}`}
            >
              <div className="flex items-center gap-3">
                <Upload className="h-5 w-5" />
                <div>
                  <p className="text-sm font-bold">Local upload</p>
                  <p className="text-xs opacity-80">Drop a single video or audio file and process it directly.</p>
                </div>
              </div>
            </button>
          </div>

          <form onSubmit={onGenerate} className="space-y-6">
            {mode === 'url' ? (
              <label className="flex flex-col gap-3">
                <span className="text-[11px] font-bold uppercase tracking-[0.28em] app-muted">Video URL or playlist</span>
                <div className="flex items-center gap-3 rounded-[26px] px-5 py-4 shadow-sm transition-colors app-card-strong">
                  <Youtube className="h-5 w-5 shrink-0" style={{ color: 'var(--accent-3)' }} />
                  <input
                    type="url"
                    placeholder="https://youtube.com/watch?v=... or https://drive.google.com/file/d/..."
                    className="w-full border-none bg-transparent text-lg font-medium outline-none placeholder:opacity-70 app-title"
                    value={url}
                    onChange={(event) => setUrl(event.target.value)}
                    disabled={isProcessing}
                    required
                  />
                </div>
              </label>
            ) : (
              <div className="space-y-3">
                <span className="text-[11px] font-bold uppercase tracking-[0.28em] app-muted">Upload a local file</span>
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  onDragOver={(event) => event.preventDefault()}
                  onDrop={handleDrop}
                  className="flex min-h-48 w-full flex-col items-center justify-center gap-4 rounded-[28px] border-2 border-dashed px-6 py-8 text-center transition-colors app-card-strong"
                  style={{ borderColor: 'color-mix(in srgb, var(--accent) 24%, var(--border))' }}
                >
                  <div className="flex h-16 w-16 items-center justify-center rounded-full" style={{ background: 'color-mix(in srgb, var(--accent) 14%, white)', color: 'var(--accent)' }}>
                    <Upload className="h-8 w-8" />
                  </div>
                  <div>
                    <p className="text-base font-bold app-title">{file ? file.name : 'Drop or choose a video/audio file'}</p>
                    <p className="mt-2 text-sm app-muted">Supported: mp4, mov, mkv, mp3, wav, m4a, ogg, flac, aac</p>
                  </div>
                </button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".mp4,.mov,.mkv,.mp3,.wav,.m4a,.ogg,.flac,.aac"
                  className="hidden"
                  onChange={(event) => setFile(event.target.files?.[0] || null)}
                />
                {typeof uploadProgress === 'number' ? (
                  <div className="space-y-2">
                    <div className="h-2 rounded-full" style={{ background: 'color-mix(in srgb, var(--accent) 12%, white)' }}>
                      <div className="h-full rounded-full" style={{ width: `${uploadProgress}%`, background: 'linear-gradient(135deg, var(--accent), var(--accent-2))' }} />
                    </div>
                    <p className="text-xs font-semibold app-muted">Upload progress: {uploadProgress}%</p>
                  </div>
                ) : null}
              </div>
            )}

            <div className="flex flex-col gap-3 rounded-[26px] p-4 sm:flex-row sm:items-center sm:justify-between app-soft">
              <div>
                <p className="text-sm font-semibold app-title">Advanced runtime settings</p>
                <p className="text-sm leading-relaxed app-muted">Whisper options, note style, custom prompt templates, provider keys, timestamps, and database connectivity live here.</p>
              </div>
              <button
                type="button"
                onClick={() => setShowSettings((value) => !value)}
                className="inline-flex items-center justify-center gap-2 rounded-full px-4 py-2 text-sm font-semibold app-card-strong"
              >
                <Settings2 className={`h-4 w-4 transition-transform ${showSettings ? 'rotate-90' : ''}`} />
                {showSettings ? 'Hide settings' : 'Show settings'}
              </button>
            </div>

            {showSettings ? (
              <div className="rounded-[28px] p-3 sm:p-4 app-soft">
                <SettingsSection disabled={isProcessing} />
              </div>
            ) : null}

            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-3 text-sm app-muted">
                <Database className="h-4 w-4" style={{ color: 'var(--accent)' }} />
                {config.databaseUrl ? 'Caching, collections, and library features are enabled for this run.' : 'No database URL set. Generation still works, but caching and library features stay off.'}
              </div>

              <button
                type="submit"
                disabled={isProcessing || (mode === 'url' ? !url : !file)}
                className="inline-flex items-center justify-center gap-3 rounded-full px-6 py-3 text-base font-bold transition-transform hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60 app-primary-btn"
              >
                {isProcessing ? <Play className="h-5 w-5 animate-pulse" /> : <ArrowRight className="h-5 w-5" />}
                {isProcessing ? 'Submitting request...' : mode === 'upload' ? 'Upload and generate' : 'Generate notes'}
              </button>
            </div>

            {status === 'error' ? (
              <div className="rounded-2xl border px-4 py-3 text-sm font-medium" style={{ borderColor: 'color-mix(in srgb, var(--accent-3) 34%, var(--border))', background: 'color-mix(in srgb, var(--accent-3) 10%, white)', color: 'var(--ink)' }}>
                {progress}
              </div>
            ) : null}
          </form>
        </div>

        {isProcessing ? (
          <section className="rounded-[30px] p-6 app-card">
            <div className="mb-6 flex items-center justify-between gap-4">
              <div>
                <p className="text-[11px] font-bold uppercase tracking-[0.28em]" style={{ color: 'var(--accent)' }}>Pipeline</p>
                <h3 className="mt-2 text-2xl font-black app-title">{progress}</h3>
              </div>
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl" style={{ background: 'color-mix(in srgb, var(--accent) 14%, white)', color: 'var(--accent)' }}>
                <Play className="h-5 w-5 animate-pulse" />
              </div>
            </div>
            <ProcessingSteps currentSteps={currentSteps} />
          </section>
        ) : null}
      </section>

      <aside className="space-y-4 pt-8">
        <div className="rounded-[28px] p-6 app-card">
          <p className="text-[11px] font-bold uppercase tracking-[0.28em] app-muted">What this app does</p>
          <div className="mt-4 space-y-3 text-sm leading-relaxed app-muted">
            <p>Process one video, a local upload, or an entire playlist into structured markdown notes with timestamps, concepts, and action items.</p>
            <p>Choose note styles, add custom prompt instructions, and generate study assets like flashcards, quiz questions, revision sheets, and glossary terms.</p>
            <p>Connect your own Postgres database to unlock caching, search, collections, and saved-note reopen flows.</p>
          </div>
        </div>

        <div className="rounded-[28px] p-6 text-white" style={{ background: 'linear-gradient(180deg, color-mix(in srgb, var(--accent) 78%, black), color-mix(in srgb, var(--accent-2) 72%, black))', boxShadow: 'var(--shadow)' }}>
          <p className="text-[11px] font-bold uppercase tracking-[0.28em] text-white/70">Workflow</p>
          <div className="mt-4 space-y-3 text-sm leading-relaxed text-white/90">
            <p>Use single-video mode for a focused note session or feed a playlist to queue a batch with per-video status and retry support.</p>
            <p>Themed UI, transcript reuse, and export formats keep the workflow smooth whether you are studying, revising, or building a reusable notes library.</p>
          </div>
        </div>
      </aside>
    </div>
  );
};

export default ProcessSection;
