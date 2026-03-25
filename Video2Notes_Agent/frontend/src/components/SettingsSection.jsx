import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Database, RefreshCw, SlidersHorizontal, Sparkles, Waves, Waypoints } from 'lucide-react';
import { useConfig } from '../context/ConfigContext';

const API_BASE = 'http://localhost:8000/api';
const LOCAL_WHISPER_MODELS = ['tiny', 'base', 'small', 'medium', 'large-v3'];
const GROQ_WHISPER_MODELS = ['whisper-large-v3-turbo', 'whisper-large-v3'];
const NOTE_STYLE_OPTIONS = [
  { value: 'study_notes', label: 'Study Notes' },
  { value: 'executive_summary', label: 'Executive Summary' },
  { value: 'meeting_notes', label: 'Meeting Notes' },
  { value: 'tutorial_breakdown', label: 'Tutorial Breakdown' },
  { value: 'actionable_checklist', label: 'Actionable Checklist' },
  { value: 'revision_notes', label: 'Revision Notes' },
];

const Field = ({ label, helper, children }) => (
  <label className="flex flex-col gap-2">
    <span className="app-eyebrow">{label}</span>
    {children}
    {helper ? <span className="text-xs leading-relaxed app-muted">{helper}</span> : null}
  </label>
);

const Toggle = ({ label, helper, checked, onChange, disabled }) => (
  <label className="flex items-start gap-3 rounded-2xl px-4 py-3 shadow-sm transition-colors app-surface-strong">
    <input
      type="checkbox"
      checked={checked}
      disabled={disabled}
      onChange={(event) => onChange(event.target.checked)}
      className="mt-1 h-4 w-4 rounded border-slate-300 text-teal-700 focus:ring-teal-500"
    />
    <span className="flex flex-col gap-1">
      <span className="text-sm font-semibold app-title">{label}</span>
      <span className="text-xs leading-relaxed app-muted">{helper}</span>
    </span>
  </label>
);

const SettingsSection = ({ disabled }) => {
  const { config, updateConfig } = useConfig();
  const [ollamaModels, setOllamaModels] = useState([]);
  const [loadingModels, setLoadingModels] = useState(false);

  const fetchOllamaModels = async () => {
    setLoadingModels(true);
    try {
      const response = await axios.get(`${API_BASE}/ollama/models`, {
        params: { base_url: config.ollamaBaseUrl },
      });
      setOllamaModels(response.data.models || []);
    } catch (error) {
      console.error('Failed to fetch Ollama models', error);
    } finally {
      setLoadingModels(false);
    }
  };

  useEffect(() => {
    if (config.provider === 'ollama') {
      fetchOllamaModels();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config.provider, config.ollamaBaseUrl]);

  const whisperModels = config.whisperProvider === 'groq' ? GROQ_WHISPER_MODELS : LOCAL_WHISPER_MODELS;

  return (
    <div className="grid gap-6 xl:grid-cols-3">
      <section className="rounded-[32px] p-6 app-card">
        <div className="mb-5 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl text-white" style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-2))' }}>
            <SlidersHorizontal className="h-5 w-5" />
          </div>
          <div>
            <p className="app-eyebrow">LLM and storage</p>
            <h3 className="text-lg font-black app-title">Runtime controls</h3>
          </div>
        </div>

        <div className="grid gap-5">
          <Field label="AI provider">
            <select value={config.provider} disabled={disabled} onChange={(event) => updateConfig({ provider: event.target.value })} className="field-shell">
              <option value="gemini">Google Gemini</option>
              <option value="anthropic">Anthropic Claude</option>
              <option value="ollama">Ollama</option>
            </select>
          </Field>

          {config.provider === 'gemini' ? (
            <Field label="Gemini API key">
              <input type="password" value={config.geminiApiKey} disabled={disabled} onChange={(event) => updateConfig({ geminiApiKey: event.target.value })} placeholder="AIza..." className="field-shell" />
            </Field>
          ) : null}

          {config.provider === 'anthropic' ? (
            <Field label="Anthropic API key">
              <input type="password" value={config.anthropicApiKey} disabled={disabled} onChange={(event) => updateConfig({ anthropicApiKey: event.target.value })} placeholder="sk-ant-..." className="field-shell" />
            </Field>
          ) : null}

          {config.provider === 'ollama' ? (
            <div className="grid gap-4 rounded-[24px] p-5 app-soft">
              <Field label="Ollama base URL">
                <input type="text" value={config.ollamaBaseUrl} disabled={disabled} onChange={(event) => updateConfig({ ollamaBaseUrl: event.target.value })} placeholder="http://localhost:11434" className="field-shell" />
              </Field>
              <Field label="Ollama model">
                <div className="flex gap-2">
                  <select value={config.ollamaModel} disabled={disabled || loadingModels} onChange={(event) => updateConfig({ ollamaModel: event.target.value })} className="field-shell">
                    <option value="">Select a discovered model</option>
                    {ollamaModels.map((model) => (
                      <option key={model.name} value={model.name}>{model.name}</option>
                    ))}
                  </select>
                  <button type="button" onClick={fetchOllamaModels} disabled={disabled || loadingModels} className="inline-flex h-12 w-12 items-center justify-center rounded-2xl app-card-strong">
                    <RefreshCw className={`h-4 w-4 ${loadingModels ? 'animate-spin' : ''}`} />
                  </button>
                </div>
              </Field>
            </div>
          ) : null}

          <Field label="Postgres database URL" helper="Optional for generation, required for caching, library search, collections, and reopening notes.">
            <textarea rows="3" value={config.databaseUrl} disabled={disabled} onChange={(event) => updateConfig({ databaseUrl: event.target.value })} placeholder="postgresql://user:password@host:5432/database" className="field-shell min-h-24 resize-y" />
          </Field>
        </div>
      </section>

      <section className="rounded-[32px] p-6 app-card">
        <div className="mb-5 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl text-white" style={{ background: 'linear-gradient(135deg, var(--accent-2), var(--accent-3))' }}>
            <Waves className="h-5 w-5" />
          </div>
          <div>
            <p className="app-eyebrow">Transcription and output</p>
            <h3 className="text-lg font-black app-title">Whisper and notes</h3>
          </div>
        </div>

        <div className="grid gap-5">
          <Field label="Whisper provider">
            <select value={config.whisperProvider} disabled={disabled} onChange={(event) => updateConfig({ whisperProvider: event.target.value })} className="field-shell">
              <option value="local">Local Whisper</option>
              <option value="groq">Groq Whisper</option>
            </select>
          </Field>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Whisper model">
              <select value={config.whisperModel} disabled={disabled} onChange={(event) => updateConfig({ whisperModel: event.target.value })} className="field-shell">
                {whisperModels.map((model) => (
                  <option key={model} value={model}>{model}</option>
                ))}
              </select>
            </Field>
            <Field label="Transcription language" helper="Leave blank for auto-detect.">
              <input type="text" value={config.language} disabled={disabled} onChange={(event) => updateConfig({ language: event.target.value })} placeholder="en" className="field-shell" />
            </Field>
          </div>

          {config.whisperProvider === 'groq' ? (
            <Field label="Groq API key">
              <input type="password" value={config.groqApiKey} disabled={disabled} onChange={(event) => updateConfig({ groqApiKey: event.target.value })} placeholder="gsk_..." className="field-shell" />
            </Field>
          ) : null}

          <Field label="Hugging Face token" helper="Needed only if your local transcription stack or model download requires it.">
            <input type="password" value={config.hfToken} disabled={disabled} onChange={(event) => updateConfig({ hfToken: event.target.value })} placeholder="hf_..." className="field-shell" />
          </Field>

          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="Detail level">
              <select value={config.detailLevel} disabled={disabled} onChange={(event) => updateConfig({ detailLevel: event.target.value })} className="field-shell">
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </Field>
            <Field label="Start time">
              <input type="text" value={config.startTime} disabled={disabled} onChange={(event) => updateConfig({ startTime: event.target.value })} placeholder="00:00" className="field-shell" />
            </Field>
            <Field label="End time">
              <input type="text" value={config.endTime} disabled={disabled} onChange={(event) => updateConfig({ endTime: event.target.value })} placeholder="Leave blank for full video" className="field-shell" />
            </Field>
          </div>

          <div className="grid gap-3">
            <div className="mb-1 flex items-center gap-2">
              <Waypoints className="h-4 w-4" style={{ color: 'var(--accent)' }} />
              <span className="text-[11px] font-bold uppercase tracking-[0.24em] app-muted">Rendered note shape</span>
            </div>
            <Toggle label="Include timestamps" helper="Adds [MM:SS] references in the notes and makes them clickable when the source supports timestamp links." checked={config.includeTimestamps} disabled={disabled} onChange={(value) => updateConfig({ includeTimestamps: value })} />
            <Toggle label="Keep Q and A sections" helper="Preserves audience questions and answers when the video includes them." checked={config.keepQa} disabled={disabled} onChange={(value) => updateConfig({ keepQa: value })} />
            <Toggle label="Keep examples and analogies" helper="Useful for study notes when the video explains concepts through examples or stories." checked={config.keepExamples} disabled={disabled} onChange={(value) => updateConfig({ keepExamples: value })} />
          </div>
        </div>
      </section>

      <section className="rounded-[32px] p-6 app-card">
        <div className="mb-5 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl text-white" style={{ background: 'linear-gradient(135deg, var(--accent-3), var(--accent))' }}>
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <p className="app-eyebrow">Output style</p>
            <h3 className="text-lg font-black app-title">Notes and prompts</h3>
          </div>
        </div>

        <div className="grid gap-5">
          <Field label="Note style">
            <select value={config.noteStyle} disabled={disabled} onChange={(event) => updateConfig({ noteStyle: event.target.value })} className="field-shell">
              {NOTE_STYLE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </Field>

          <Field label="Custom prompt template" helper="Optional. This is added on top of the selected note style to guide the final notes.">
            <textarea rows="8" value={config.customPromptTemplate} disabled={disabled} onChange={(event) => updateConfig({ customPromptTemplate: event.target.value })} placeholder="Example: explain like a teacher, surface all technical terms, and end with a quick revision drill." className="field-shell min-h-36 resize-y" />
          </Field>

          <Toggle
            label="Generate study assets"
            helper="Optional. When off, the flashcards/quiz/revision/glossary step is skipped entirely for faster runs."
            checked={config.generateStudyAssets}
            disabled={disabled}
            onChange={(value) => updateConfig({ generateStudyAssets: value })}
          />

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Playlist processing">
              <select
                value={config.playlistProcessingMode}
                disabled={disabled}
                onChange={(event) =>
                  updateConfig({
                    playlistProcessingMode: event.target.value,
                    playlistWorkerCount: event.target.value === 'sequential' ? 1 : Math.max(2, config.playlistWorkerCount || 3),
                  })
                }
                className="field-shell"
              >
                <option value="parallel">Parallel</option>
                <option value="sequential">One by one</option>
              </select>
            </Field>
            <Field label="Playlist workers" helper="Used only in parallel mode.">
              <input
                type="number"
                min="1"
                max="6"
                value={config.playlistProcessingMode === 'sequential' ? 1 : config.playlistWorkerCount}
                disabled={disabled || config.playlistProcessingMode === 'sequential'}
                onChange={(event) => updateConfig({ playlistWorkerCount: Number(event.target.value || 1) })}
                className="field-shell"
              />
            </Field>
          </div>

          <div className="rounded-[22px] px-4 py-3 text-sm leading-relaxed app-soft app-muted">
            <div className="mb-2 flex items-center gap-2 font-semibold app-title">
              <Database className="h-4 w-4" style={{ color: 'var(--accent)' }} />
              Current persistence mode
            </div>
            {config.databaseUrl ? 'Configured. Notes, transcript reuse, library search, and collections are available.' : 'Disabled until you provide a Postgres URL.'}
          </div>
        </div>
      </section>
    </div>
  );
};

export default SettingsSection;
