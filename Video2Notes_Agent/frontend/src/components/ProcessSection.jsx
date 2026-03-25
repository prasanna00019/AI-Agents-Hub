import React, { useRef, useState } from 'react';
import { ArrowRight, CheckSquare, Database, Play, Settings2, Sparkles, Square, Upload, Youtube } from 'lucide-react';
import SettingsSection from './SettingsSection';
import ProcessingSteps from './ProcessingSteps';
import Modal from './Modal';
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
  playlistPreview,
  selectedVideoIds,
  setSelectedVideoIds,
  onClosePlaylistPreview,
  onProcessPlaylist,
}) => {
  const fileInputRef = useRef(null);
  const [showSettings, setShowSettings] = useState(false);
  const { config } = useConfig();

  const isProcessing = status === 'processing';
  const capabilityBadges = ['Timestamp-aware notes', 'Playlist batches', 'Searchable library', 'Study assets'];

  const handleDrop = (event) => {
    event.preventDefault();
    const droppedFile = event.dataTransfer?.files?.[0];
    if (droppedFile) {
      setFile(droppedFile);
    }
  };

  return (
    <div className="grid gap-8 xl:grid-cols-[minmax(0,1.35fr)_380px]">
      <section className="space-y-8">
        <div className="app-hero rounded-[36px] p-6 sm:p-8 lg:p-10">
          <div className="relative z-10 space-y-6">
            <div className="app-kicker">
              <Sparkles className="h-3.5 w-3.5" />
              Video to structured notes
            </div>

            <div className="max-w-4xl space-y-5">
              <h2 className="app-display app-gradient-text max-w-4xl">
                Turn videos, uploads, and playlists into notes you can search, save, and study.
              </h2>
              <p className="app-lead max-w-3xl">
                Video2Notes supports local uploads, Google Drive shared videos, YouTube playlists, reusable transcript caching, and richer note outputs without giving up the current single-video workflow.
              </p>
            </div>

            <div className="app-grid-metrics max-w-4xl">
              <div className="app-metric">
                <div className="app-metric__label">Input modes</div>
                <div className="app-metric__value">URL, file, playlist</div>
              </div>
              <div className="app-metric">
                <div className="app-metric__label">Output</div>
                <div className="app-metric__value">Notes, assets, RAG</div>
              </div>
              <div className="app-metric">
                <div className="app-metric__label">Storage</div>
                <div className="app-metric__value">Cache + collections</div>
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              {capabilityBadges.map((badge) => (
                <span key={badge} className="app-chip">
                  {badge}
                </span>
              ))}
            </div>
          </div>
        </div>

        <div className="rounded-[36px] p-5 sm:p-8 app-card" style={{ background: 'linear-gradient(135deg, color-mix(in srgb, var(--card) 94%, white), color-mix(in srgb, var(--card-strong) 96%, white))' }}>
          <div className="mb-5 flex items-center justify-between gap-4">
            <div>
              <p className="app-eyebrow">Generate</p>
              <h3 className="mt-2 text-2xl font-black app-section-title">Choose your source</h3>
            </div>
            <div className="hidden rounded-full px-3 py-2 text-xs font-bold uppercase tracking-[0.26em] app-chip lg:inline-flex">
              Live pipeline
            </div>
          </div>

          <div className="mb-5 grid gap-3 sm:grid-cols-2">
            <button
              type="button"
              onClick={() => setMode('url')}
              className={`rounded-[28px] px-5 py-4 text-left transition-transform duration-300 hover:-translate-y-0.5 ${mode === 'url' ? 'app-primary-btn' : 'app-surface-strong'}`}
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
              className={`rounded-[28px] px-5 py-4 text-left transition-transform duration-300 hover:-translate-y-0.5 ${mode === 'upload' ? 'app-primary-btn' : 'app-surface-strong'}`}
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
                <span className="app-eyebrow">Video URL or playlist</span>
                <div className="flex items-center gap-3 rounded-[28px] px-5 py-4 app-surface-strong" style={{ background: 'linear-gradient(135deg, color-mix(in srgb, var(--card-strong) 96%, white), color-mix(in srgb, var(--card) 92%, white))' }}>
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
                <span className="app-eyebrow">Upload a local file</span>
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  onDragOver={(event) => event.preventDefault()}
                  onDrop={handleDrop}
                  className="flex min-h-52 w-full flex-col items-center justify-center gap-4 rounded-[30px] border-2 border-dashed px-6 py-8 text-center transition-transform duration-300 hover:-translate-y-0.5 app-surface-strong"
                  style={{ borderColor: 'color-mix(in srgb, var(--accent) 24%, var(--border))', background: 'linear-gradient(135deg, color-mix(in srgb, var(--card-strong) 96%, white), color-mix(in srgb, var(--card-soft) 94%, white))' }}
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

            <div className="flex flex-col gap-3 rounded-[28px] p-4 sm:flex-row sm:items-center sm:justify-between app-soft" style={{ background: 'linear-gradient(135deg, color-mix(in srgb, var(--card-soft) 92%, white), color-mix(in srgb, var(--card-strong) 92%, white))' }}>
              <div>
                <p className="text-sm font-semibold app-title">Advanced runtime settings</p>
                <p className="text-sm leading-relaxed app-muted">Whisper options, note style, custom prompt templates, provider keys, timestamps, and database connectivity live here.</p>
              </div>
              <button
                type="button"
                onClick={() => setShowSettings((value) => !value)}
                className="inline-flex items-center justify-center gap-2 rounded-full px-4 py-2 text-sm font-semibold app-surface-strong"
              >
                <Settings2 className={`h-4 w-4 transition-transform ${showSettings ? 'rotate-90' : ''}`} />
                {showSettings ? 'Hide settings' : 'Show settings'}
              </button>
            </div>

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
          <section className="rounded-[32px] p-6 app-card">
            <div className="mb-6 flex items-center justify-between gap-4">
              <div>
                <p className="app-eyebrow" style={{ color: 'var(--accent)' }}>Pipeline</p>
                <h3 className="mt-2 text-2xl font-black app-section-title">{progress}</h3>
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
        <div className="rounded-[30px] p-6 app-card" style={{ background: 'linear-gradient(135deg, color-mix(in srgb, var(--card-strong) 95%, white), color-mix(in srgb, var(--card) 90%, white))' }}>
          <p className="app-eyebrow">What this app does</p>
          <div className="mt-4 space-y-3 text-sm leading-relaxed app-muted">
            <p>Process one video, a local upload, or an entire playlist into structured markdown notes with timestamps, concepts, and action items.</p>
            <p>Choose note styles, add custom prompt instructions, and optionally generate study assets like flashcards, quiz questions, revision sheets, and glossary terms.</p>
            <p>Connect your own Postgres database to unlock caching, search, collections, and saved-note reopen flows.</p>
          </div>
        </div>

        <div className="rounded-[30px] p-6 text-white" style={{ background: 'linear-gradient(160deg, color-mix(in srgb, var(--accent) 82%, black), color-mix(in srgb, var(--accent-2) 72%, black) 52%, color-mix(in srgb, var(--accent-3) 58%, black))', boxShadow: 'var(--shadow)' }}>
          <p className="text-[11px] font-bold uppercase tracking-[0.28em] text-white/70">Workflow</p>
          <div className="mt-4 space-y-3 text-sm leading-relaxed text-white/90">
            <p>Use single-video mode for a focused note session or feed a playlist to queue a batch with per-video status and retry support.</p>
            <p>Playlist batches can run in parallel with a chosen worker count or one by one, depending on the settings you pick.</p>
            <p>Themed UI, transcript reuse, and export formats keep the workflow smooth whether you are studying, revising, or building a reusable notes library.</p>
          </div>
        </div>
      </aside>

      <Modal open={showSettings} onClose={() => setShowSettings(false)} title="Advanced Runtime Settings" widthClass="max-w-7xl">
        <SettingsSection disabled={isProcessing} />
      </Modal>

      <Modal open={Boolean(playlistPreview)} onClose={onClosePlaylistPreview} title={playlistPreview?.title || 'Select Playlist Videos'} widthClass="max-w-4xl">
        <div className="space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm app-muted">
              Choose which playlist videos to process. Current mode: {config.playlistProcessingMode === 'sequential' ? 'one by one' : `parallel with ${Math.max(1, config.playlistWorkerCount)} workers`}.
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setSelectedVideoIds((playlistPreview?.entries || []).map((entry) => entry.id))}
                className="inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold app-surface-strong"
              >
                <CheckSquare className="h-4 w-4" />
                Select all
              </button>
              <button
                type="button"
                onClick={() => setSelectedVideoIds([])}
                className="inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold app-surface-strong"
              >
                <Square className="h-4 w-4" />
                Clear
              </button>
            </div>
          </div>

          <div className="grid max-h-[52vh] gap-3 overflow-y-auto pr-2">
            {(playlistPreview?.entries || []).map((entry, index) => {
              const checked = selectedVideoIds.includes(entry.id);
              return (
                <label key={entry.id} className="flex items-center gap-4 rounded-[22px] px-4 py-4 app-surface">
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={(event) => {
                      if (event.target.checked) {
                        setSelectedVideoIds((previous) => [...previous, entry.id]);
                      } else {
                        setSelectedVideoIds((previous) => previous.filter((id) => id !== entry.id));
                      }
                    }}
                    className="h-4 w-4"
                  />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-bold app-title">
                      {index + 1}. {entry.title}
                    </p>
                    <p className="mt-1 truncate text-xs app-muted">{entry.url}</p>
                  </div>
                </label>
              );
            })}
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm app-muted">
              Selected {selectedVideoIds.length} of {(playlistPreview?.entries || []).length} videos.
            </p>
            <div className="flex flex-wrap gap-3">
              <button type="button" onClick={() => onProcessPlaylist(true)} className="rounded-full px-4 py-3 text-sm font-semibold app-surface-strong">
                Process all
              </button>
              <button
                type="button"
                disabled={selectedVideoIds.length === 0}
                onClick={() => onProcessPlaylist(false)}
                className="rounded-full px-5 py-3 text-sm font-semibold app-primary-btn disabled:cursor-not-allowed disabled:opacity-60"
              >
                Process selected
              </button>
            </div>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default ProcessSection;
