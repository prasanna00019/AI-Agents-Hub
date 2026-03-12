import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Database, RefreshCw, SlidersHorizontal, Waves, Waypoints } from 'lucide-react';
import { useConfig } from '../context/ConfigContext';

const API_BASE = 'http://localhost:8000/api';
const LOCAL_WHISPER_MODELS = ['tiny', 'base', 'small', 'medium', 'large-v3'];
const GROQ_WHISPER_MODELS = ['whisper-large-v3-turbo', 'whisper-large-v3'];

const Field = ({ label, helper, children }) => (
  <label className="flex flex-col gap-2">
    <span className="text-[11px] font-bold uppercase tracking-[0.24em] text-slate-500">{label}</span>
    {children}
    {helper ? <span className="text-xs leading-relaxed text-slate-500">{helper}</span> : null}
  </label>
);

const Toggle = ({ label, helper, checked, onChange, disabled }) => (
  <label className="flex items-start gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm transition-colors hover:border-slate-300">
    <input
      type="checkbox"
      checked={checked}
      disabled={disabled}
      onChange={(event) => onChange(event.target.checked)}
      className="mt-1 h-4 w-4 rounded border-slate-300 text-teal-700 focus:ring-teal-500"
    />
    <span className="flex flex-col gap-1">
      <span className="text-sm font-semibold text-slate-900">{label}</span>
      <span className="text-xs leading-relaxed text-slate-500">{helper}</span>
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
  }, [config.provider, config.ollamaBaseUrl]);

  const whisperModels = config.whisperProvider === 'groq' ? GROQ_WHISPER_MODELS : LOCAL_WHISPER_MODELS;

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <section className="rounded-[28px] border border-slate-200/80 bg-[rgba(255,255,255,0.82)] p-6 shadow-[0_20px_50px_rgba(15,23,42,0.08)] backdrop-blur-xl">
        <div className="mb-5 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-900 text-white">
            <SlidersHorizontal className="h-5 w-5" />
          </div>
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.24em] text-slate-500">LLM and storage</p>
            <h3 className="text-lg font-black text-slate-900">Runtime controls</h3>
          </div>
        </div>

        <div className="grid gap-5">
          <Field label="AI provider">
            <select
              value={config.provider}
              disabled={disabled}
              onChange={(event) => updateConfig({ provider: event.target.value })}
              className="field-shell"
            >
              <option value="gemini">Google Gemini</option>
              <option value="anthropic">Anthropic Claude</option>
              <option value="ollama">Ollama</option>
            </select>
          </Field>

          {config.provider === 'gemini' ? (
            <Field label="Gemini API key">
              <input
                type="password"
                value={config.geminiApiKey}
                disabled={disabled}
                onChange={(event) => updateConfig({ geminiApiKey: event.target.value })}
                placeholder="AIza..."
                className="field-shell"
              />
            </Field>
          ) : null}

          {config.provider === 'anthropic' ? (
            <Field label="Anthropic API key">
              <input
                type="password"
                value={config.anthropicApiKey}
                disabled={disabled}
                onChange={(event) => updateConfig({ anthropicApiKey: event.target.value })}
                placeholder="sk-ant-..."
                className="field-shell"
              />
            </Field>
          ) : null}

          {config.provider === 'ollama' ? (
            <div className="grid gap-4 rounded-[24px] border border-slate-200 bg-slate-50/80 p-5">
              <Field label="Ollama base URL">
                <input
                  type="text"
                  value={config.ollamaBaseUrl}
                  disabled={disabled}
                  onChange={(event) => updateConfig({ ollamaBaseUrl: event.target.value })}
                  placeholder="http://localhost:11434"
                  className="field-shell"
                />
              </Field>
              <Field label="Ollama model">
                <div className="flex gap-2">
                  <select
                    value={config.ollamaModel}
                    disabled={disabled || loadingModels}
                    onChange={(event) => updateConfig({ ollamaModel: event.target.value })}
                    className="field-shell"
                  >
                    <option value="">Select a discovered model</option>
                    {ollamaModels.map((model) => (
                      <option key={model.name} value={model.name}>{model.name}</option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={fetchOllamaModels}
                    disabled={disabled || loadingModels}
                    className="inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    <RefreshCw className={`h-4 w-4 ${loadingModels ? 'animate-spin' : ''}`} />
                  </button>
                </div>
              </Field>
            </div>
          ) : null}

          <Field
            label="Postgres database URL"
            helper="Optional, but required if you want caching and the Library view. This replaces the old hardcoded backend value."
          >
            <textarea
              rows="3"
              value={config.databaseUrl}
              disabled={disabled}
              onChange={(event) => updateConfig({ databaseUrl: event.target.value })}
              placeholder="postgresql://user:password@host:5432/database"
              className="field-shell min-h-24 resize-y"
            />
          </Field>
        </div>
      </section>

      <section className="rounded-[28px] border border-slate-200/80 bg-[rgba(255,255,255,0.82)] p-6 shadow-[0_20px_50px_rgba(15,23,42,0.08)] backdrop-blur-xl">
        <div className="mb-5 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-teal-700 text-white">
            <Waves className="h-5 w-5" />
          </div>
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.24em] text-slate-500">Transcription and output</p>
            <h3 className="text-lg font-black text-slate-900">Whisper and notes</h3>
          </div>
        </div>

        <div className="grid gap-5">
          <Field label="Whisper provider">
            <select
              value={config.whisperProvider}
              disabled={disabled}
              onChange={(event) => updateConfig({ whisperProvider: event.target.value })}
              className="field-shell"
            >
              <option value="local">Local Whisper</option>
              <option value="groq">Groq Whisper</option>
            </select>
          </Field>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Whisper model">
              <select
                value={config.whisperModel}
                disabled={disabled}
                onChange={(event) => updateConfig({ whisperModel: event.target.value })}
                className="field-shell"
              >
                {whisperModels.map((model) => (
                  <option key={model} value={model}>{model}</option>
                ))}
              </select>
            </Field>

            <Field label="Transcription language" helper="Leave blank for auto-detect.">
              <input
                type="text"
                value={config.language}
                disabled={disabled}
                onChange={(event) => updateConfig({ language: event.target.value })}
                placeholder="en"
                className="field-shell"
              />
            </Field>
          </div>

          {config.whisperProvider === 'groq' ? (
            <Field label="Groq API key">
              <input
                type="password"
                value={config.groqApiKey}
                disabled={disabled}
                onChange={(event) => updateConfig({ groqApiKey: event.target.value })}
                placeholder="gsk_..."
                className="field-shell"
              />
            </Field>
          ) : null}

          <Field label="Hugging Face token" helper="Needed only if your local transcription stack or model download requires it.">
            <input
              type="password"
              value={config.hfToken}
              disabled={disabled}
              onChange={(event) => updateConfig({ hfToken: event.target.value })}
              placeholder="hf_..."
              className="field-shell"
            />
          </Field>

          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="Detail level">
              <select
                value={config.detailLevel}
                disabled={disabled}
                onChange={(event) => updateConfig({ detailLevel: event.target.value })}
                className="field-shell"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </Field>
            <Field label="Start time">
              <input
                type="text"
                value={config.startTime}
                disabled={disabled}
                onChange={(event) => updateConfig({ startTime: event.target.value })}
                placeholder="00:00"
                className="field-shell"
              />
            </Field>
            <Field label="End time">
              <input
                type="text"
                value={config.endTime}
                disabled={disabled}
                onChange={(event) => updateConfig({ endTime: event.target.value })}
                placeholder="Leave blank for full video"
                className="field-shell"
              />
            </Field>
          </div>

          <div className="grid gap-3">
            <div className="mb-1 flex items-center gap-2">
              <Waypoints className="h-4 w-4 text-slate-500" />
              <span className="text-[11px] font-bold uppercase tracking-[0.24em] text-slate-500">Rendered note shape</span>
            </div>

            <Toggle
              label="Include timestamps"
              helper="Adds [MM:SS] references in the notes and makes them clickable when the source is YouTube."
              checked={config.includeTimestamps}
              disabled={disabled}
              onChange={(value) => updateConfig({ includeTimestamps: value })}
            />
            <Toggle
              label="Keep Q and A sections"
              helper="Preserves audience questions and answers when the video includes them."
              checked={config.keepQa}
              disabled={disabled}
              onChange={(value) => updateConfig({ keepQa: value })}
            />
            <Toggle
              label="Keep examples and analogies"
              helper="Useful for study notes when the video explains concepts through stories or examples."
              checked={config.keepExamples}
              disabled={disabled}
              onChange={(value) => updateConfig({ keepExamples: value })}
            />
          </div>

          <div className="rounded-[22px] border border-slate-200 bg-slate-50/80 px-4 py-3 text-sm leading-relaxed text-slate-600">
            <div className="mb-2 flex items-center gap-2 font-semibold text-slate-900">
              <Database className="h-4 w-4 text-teal-700" />
              Current persistence mode
            </div>
            {config.databaseUrl ? 'Configured. Generated notes will be cached and available in the Library view.' : 'Disabled until you provide a Postgres URL.'}
          </div>
        </div>
      </section>
    </div>
  );
};

export default SettingsSection;
