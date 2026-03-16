import { useEffect, useMemo, useState } from 'react'

const DAYS = [
  'monday',
  'tuesday',
  'wednesday',
  'thursday',
  'friday',
  'saturday',
  'sunday',
]

const DEFAULT_TEMPLATE = {
  monday: 'Concept Deep Dive',
  tuesday: 'Tool Spotlight',
  wednesday: 'AI News Highlight',
  thursday: 'Tutorial / How-To',
  friday: 'Opinion / Commentary',
  saturday: 'Case Study',
  sunday: 'Weekly Summary',
}

const channelFormInitialState = {
  name: '',
  description: '',
  audience: '',
  tone: 'Educational',
  platform: 'whatsapp',
  language: 'en',
  timezone: 'UTC',
  prompt_template: '',
  sources_text: '',
}

function App() {
  const apiBaseUrl = useMemo(
    () => import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
    []
  )

  const [activeView, setActiveView] = useState('workspace')
  const [health, setHealth] = useState('checking')
  const [notice, setNotice] = useState(null)
  const [models, setModels] = useState([])
  const [channels, setChannels] = useState([])
  const [selectedChannelId, setSelectedChannelId] = useState('')
  const [reviewQueue, setReviewQueue] = useState([])
  const [refineInputs, setRefineInputs] = useState({})
  const [generateModel, setGenerateModel] = useState('')
  const [generateStartDate, setGenerateStartDate] = useState(
    new Date().toISOString().slice(0, 10)
  )
  const [settings, setSettings] = useState({
    database_url: '',
    ollama_base_url: 'http://localhost:11434',
    default_ollama_model: '',
    searxng_url: 'http://localhost:8080',
  })
  const [channelForm, setChannelForm] = useState(channelFormInitialState)
  const [weeklyTemplateDraft, setWeeklyTemplateDraft] = useState({
    ...DEFAULT_TEMPLATE,
  })
  const [overrideForm, setOverrideForm] = useState({
    date: new Date().toISOString().slice(0, 10),
    pillar: '',
    topic: '',
    special_instructions: '',
  })

  const selectedChannel = channels.find((channel) => channel.id === selectedChannelId)

  const setFeedback = (message, tone = 'info') => {
    setNotice({ message, tone })
  }

  const callApi = async (path, options = {}) => {
    const response = await fetch(`${apiBaseUrl}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    })

    if (!response.ok) {
      const text = await response.text()
      throw new Error(text || `Request failed: ${response.status}`)
    }

    return response.json()
  }

  const loadHealth = async () => {
    try {
      await callApi('/health')
      setHealth('connected')
    } catch {
      setHealth('down')
    }
  }

  const loadSettings = async () => {
    const data = await callApi('/api/v1/settings')
    setSettings(data)
    return data
  }

  const loadModels = async () => {
    const data = await callApi('/api/v1/ollama/models')
    setModels(data.models || [])

    if (data.models?.length > 0 && !settings.default_ollama_model) {
      setSettings((prev) => ({
        ...prev,
        default_ollama_model: data.models[0],
      }))
    }

    return data
  }

  const loadChannels = async () => {
    const data = await callApi('/api/v1/channels')
    setChannels(data)

    if (data.length > 0 && !selectedChannelId) {
      setSelectedChannelId(data[0].id)
    }

    return data
  }

  const loadReviewQueue = async (channelId) => {
    if (!channelId) {
      setReviewQueue([])
      return []
    }

    const data = await callApi(`/api/v1/review-queue?channel_id=${channelId}`)
    setReviewQueue(data)
    return data
  }

  useEffect(() => {
    const boot = async () => {
      await loadHealth()
      await loadSettings()
      await loadModels()
      await loadChannels()
    }

    boot().catch((error) => setFeedback(error.message, 'error'))
  }, [])

  useEffect(() => {
    loadReviewQueue(selectedChannelId).catch((error) =>
      setFeedback(error.message, 'error')
    )
  }, [selectedChannelId])

  useEffect(() => {
    if (!selectedChannel) {
      setWeeklyTemplateDraft({ ...DEFAULT_TEMPLATE })
      return
    }

    setWeeklyTemplateDraft({
      ...DEFAULT_TEMPLATE,
      ...(selectedChannel.weekly_template || {}),
    })
  }, [selectedChannel])

  const saveSettings = async () => {
    await callApi('/api/v1/settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
    })
    await loadModels()
    setFeedback('System settings saved', 'success')
  }

  const testDb = async () => {
    const result = await callApi(
      `/api/v1/settings/test-db?database_url=${encodeURIComponent(settings.database_url)}`
    )
    setFeedback(result.message, result.ok ? 'success' : 'error')
  }

  const createChannel = async () => {
    const payload = {
      ...channelForm,
      sources: channelForm.sources_text
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean),
      weekly_template: weeklyTemplateDraft,
    }

    delete payload.sources_text

    const created = await callApi('/api/v1/channels', {
      method: 'POST',
      body: JSON.stringify(payload),
    })

    await loadChannels()
    setSelectedChannelId(created.id)
    setChannelForm(channelFormInitialState)
    setActiveView('planner')
    setFeedback('Channel saved to PostgreSQL', 'success')
  }

  const saveWeeklyTemplate = async () => {
    if (!selectedChannelId) {
      setFeedback('Select a channel first', 'error')
      return
    }

    await callApi(`/api/v1/channels/${selectedChannelId}/weekly-template`, {
      method: 'POST',
      body: JSON.stringify({ weekly_template: weeklyTemplateDraft }),
    })

    await loadChannels()
    setFeedback('Weekly template updated', 'success')
  }

  const saveOverride = async () => {
    if (!selectedChannelId) {
      setFeedback('Select a channel first', 'error')
      return
    }

    await callApi(`/api/v1/channels/${selectedChannelId}/overrides`, {
      method: 'POST',
      body: JSON.stringify(overrideForm),
    })

    await loadChannels()
    setFeedback('Per-day override saved', 'success')
  }

  const generateWeek = async () => {
    if (!selectedChannelId) {
      setFeedback('Select a channel first', 'error')
      return
    }

    await callApi(`/api/v1/channels/${selectedChannelId}/generate-week`, {
      method: 'POST',
      body: JSON.stringify({
        start_date: generateStartDate,
        model: generateModel || settings.default_ollama_model,
      }),
    })

    await loadReviewQueue(selectedChannelId)
    setActiveView('review')
    setFeedback('Weekly content generated', 'success')
  }

  const saveReviewItem = async (item) => {
    await callApi(`/api/v1/review-queue/${item.id}`, {
      method: 'PUT',
      body: JSON.stringify({
        content: item.content,
        status: item.status,
      }),
    })
    setFeedback('Review item saved', 'success')
  }

  const refineItem = async (itemId) => {
    const instruction = refineInputs[itemId]

    if (!instruction) {
      setFeedback('Enter a refinement instruction', 'error')
      return
    }

    await callApi(`/api/v1/review-queue/${itemId}/refine`, {
      method: 'POST',
      body: JSON.stringify({
        instruction,
        model: settings.default_ollama_model,
      }),
    })

    setRefineInputs((prev) => ({ ...prev, [itemId]: '' }))
    await loadReviewQueue(selectedChannelId)
    setFeedback('AI refinement complete', 'success')
  }

  const copyContent = async (content) => {
    await navigator.clipboard.writeText(content)
    setFeedback('Copied to clipboard', 'success')
  }

  const statusPillClass = {
    connected: 'bg-emerald-100 text-emerald-700',
    down: 'bg-rose-100 text-rose-700',
    checking: 'bg-amber-100 text-amber-700',
  }[health]

  const noticeClass = notice?.tone === 'error'
    ? 'border-rose-200 bg-rose-50 text-rose-700'
    : notice?.tone === 'success'
      ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
      : 'border-slate-200 bg-slate-50 text-slate-700'

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,#eef4ff,transparent_38%),linear-gradient(180deg,#f8fafc,white)] text-slate-900">
      <div className="mx-auto flex min-h-screen max-w-7xl gap-6 px-4 py-6 lg:px-6">
        <aside className="hidden w-80 shrink-0 rounded-3xl border border-slate-200 bg-white/90 p-5 shadow-[0_20px_60px_rgba(15,23,42,0.08)] backdrop-blur lg:flex lg:flex-col">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-indigo-600">
              ContentPilot
            </p>
            <h1 className="mt-3 text-2xl font-semibold tracking-tight text-slate-950">
              Editorial Control Room
            </h1>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Configure models, plan weekly content, and review AI drafts from one workspace.
            </p>
          </div>

          <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="flex items-center justify-between gap-3">
              <span className="text-sm font-medium text-slate-700">Backend status</span>
              <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusPillClass}`}>
                {health}
              </span>
            </div>
            <p className="mt-3 text-xs leading-5 text-slate-500">{apiBaseUrl}</p>
            <p className="mt-3 text-xs leading-5 text-slate-500">
              {models.length} Ollama models detected
            </p>
            <p className="mt-1 text-xs leading-5 text-slate-500">
              {channels.length} channels stored in PostgreSQL
            </p>
          </div>

          <nav className="mt-6 space-y-2">
            {[
              ['workspace', 'Workspace'],
              ['settings', 'System Settings'],
              ['planner', 'Planner'],
              ['review', 'Review Queue'],
            ].map(([view, label]) => (
              <button
                key={view}
                className={`flex w-full items-center justify-between rounded-2xl px-4 py-3 text-left text-sm font-medium transition ${
                  activeView === view
                    ? 'bg-slate-950 text-white shadow-lg shadow-slate-950/15'
                    : 'bg-slate-50 text-slate-700 hover:bg-slate-100'
                }`}
                onClick={() => setActiveView(view)}
              >
                <span>{label}</span>
                <span className="text-xs opacity-70">Open</span>
              </button>
            ))}
          </nav>

          <div className="mt-8 flex-1 overflow-hidden rounded-2xl border border-slate-200">
            <div className="border-b border-slate-200 px-4 py-3">
              <h2 className="text-sm font-semibold text-slate-900">Channels</h2>
            </div>
            <div className="max-h-[28rem] overflow-y-auto p-3">
              {channels.length === 0 && (
                <p className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-500">
                  No channels saved yet.
                </p>
              )}
              <div className="space-y-2">
                {channels.map((channel) => (
                  <button
                    key={channel.id}
                    className={`w-full rounded-2xl border px-4 py-3 text-left transition ${
                      selectedChannelId === channel.id
                        ? 'border-indigo-200 bg-indigo-50'
                        : 'border-slate-200 bg-white hover:border-slate-300'
                    }`}
                    onClick={() => {
                      setSelectedChannelId(channel.id)
                      setActiveView('planner')
                    }}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-medium text-slate-900">{channel.name}</p>
                      <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600">
                        {channel.platform}
                      </span>
                    </div>
                    <p className="mt-1 line-clamp-2 text-sm text-slate-500">
                      {channel.audience || 'No audience defined'}
                    </p>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </aside>

        <main className="min-w-0 flex-1 space-y-6">
          <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-[0_20px_60px_rgba(15,23,42,0.08)] backdrop-blur">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">
                  Phase 1 Delivery
                </p>
                <h2 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">
                  Build, plan, generate, review.
                </h2>
                <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">
                  This workspace now stores channels in PostgreSQL, automatically loads Ollama models, and keeps weekly planning plus review operations in one production-oriented surface.
                </p>
              </div>

              <div className="grid gap-3 sm:grid-cols-3">
                <MetricCard label="Models" value={String(models.length)} hint="Auto-fetched from Ollama" />
                <MetricCard label="Channels" value={String(channels.length)} hint="Persisted in Postgres" />
                <MetricCard label="Drafts" value={String(reviewQueue.length)} hint="Current review queue" />
              </div>
            </div>

            {notice && (
              <div className={`mt-6 rounded-2xl border px-4 py-3 text-sm ${noticeClass}`}>
                {notice.message}
              </div>
            )}
          </section>

          {(activeView === 'workspace' || activeView === 'settings') && (
            <section className="grid gap-6 xl:grid-cols-[1.15fr,0.85fr]">
              <Panel title="System Settings" subtitle="Configure persistence, model access, and search endpoints.">
                <div className="grid gap-4 md:grid-cols-2">
                  <Field label="PostgreSQL URL">
                    <input
                      className={inputClass}
                      value={settings.database_url || ''}
                      onChange={(event) =>
                        setSettings((prev) => ({ ...prev, database_url: event.target.value }))
                      }
                    />
                  </Field>
                  <Field label="Ollama Base URL">
                    <input
                      className={inputClass}
                      value={settings.ollama_base_url || ''}
                      onChange={(event) =>
                        setSettings((prev) => ({ ...prev, ollama_base_url: event.target.value }))
                      }
                    />
                  </Field>
                  <Field label="Default Model">
                    <select
                      className={inputClass}
                      value={settings.default_ollama_model || ''}
                      onChange={(event) =>
                        setSettings((prev) => ({
                          ...prev,
                          default_ollama_model: event.target.value,
                        }))
                      }
                    >
                      <option value="">Select model</option>
                      {models.map((model) => (
                        <option key={model} value={model}>
                          {model}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <Field label="SearXNG URL">
                    <input
                      className={inputClass}
                      value={settings.searxng_url || ''}
                      onChange={(event) =>
                        setSettings((prev) => ({ ...prev, searxng_url: event.target.value }))
                      }
                    />
                  </Field>
                </div>

                <div className="mt-5 flex flex-wrap gap-3">
                  <PrimaryButton onClick={saveSettings}>Save Settings</PrimaryButton>
                  <SecondaryButton onClick={testDb}>Test Database</SecondaryButton>
                  <SecondaryButton onClick={loadModels}>Refresh Models</SecondaryButton>
                </div>
              </Panel>

              <Panel title="Ollama Models" subtitle="Detected automatically from localhost:11434/api/tags.">
                <div className="space-y-3">
                  {models.length === 0 && (
                    <EmptyState text="No models found. Start Ollama and ensure localhost:11434 is reachable." />
                  )}
                  {models.map((model) => (
                    <div
                      key={model}
                      className="flex items-center justify-between rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3"
                    >
                      <span className="text-sm font-medium text-slate-800">{model}</span>
                      {settings.default_ollama_model === model && (
                        <span className="rounded-full bg-indigo-100 px-2 py-1 text-xs font-semibold text-indigo-700">
                          Default
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </Panel>
            </section>
          )}

          {(activeView === 'workspace' || activeView === 'planner') && (
            <section className="grid gap-6 xl:grid-cols-[0.95fr,1.05fr]">
              <Panel title="Create Channel" subtitle="Store profile, sources, and prompt template directly in PostgreSQL.">
                <div className="grid gap-4 md:grid-cols-2">
                  <Field label="Channel Name">
                    <input className={inputClass} value={channelForm.name} onChange={(event) => setChannelForm((prev) => ({ ...prev, name: event.target.value }))} />
                  </Field>
                  <Field label="Audience">
                    <input className={inputClass} value={channelForm.audience} onChange={(event) => setChannelForm((prev) => ({ ...prev, audience: event.target.value }))} />
                  </Field>
                  <Field label="Tone">
                    <input className={inputClass} value={channelForm.tone} onChange={(event) => setChannelForm((prev) => ({ ...prev, tone: event.target.value }))} />
                  </Field>
                  <Field label="Platform">
                    <select className={inputClass} value={channelForm.platform} onChange={(event) => setChannelForm((prev) => ({ ...prev, platform: event.target.value }))}>
                      <option value="whatsapp">whatsapp</option>
                      <option value="telegram">telegram</option>
                      <option value="linkedin">linkedin</option>
                    </select>
                  </Field>
                  <Field label="Language">
                    <input className={inputClass} value={channelForm.language} onChange={(event) => setChannelForm((prev) => ({ ...prev, language: event.target.value }))} />
                  </Field>
                  <Field label="Timezone">
                    <input className={inputClass} value={channelForm.timezone} onChange={(event) => setChannelForm((prev) => ({ ...prev, timezone: event.target.value }))} />
                  </Field>
                </div>

                <Field label="Description" className="mt-4">
                  <textarea className={textareaClass} rows={4} value={channelForm.description} onChange={(event) => setChannelForm((prev) => ({ ...prev, description: event.target.value }))} />
                </Field>
                <Field label="Sources" help="One URL or query per line." className="mt-4">
                  <textarea className={textareaClass} rows={5} value={channelForm.sources_text} onChange={(event) => setChannelForm((prev) => ({ ...prev, sources_text: event.target.value }))} />
                </Field>
                <Field label="Prompt Template" className="mt-4">
                  <textarea className={textareaClass} rows={5} value={channelForm.prompt_template} onChange={(event) => setChannelForm((prev) => ({ ...prev, prompt_template: event.target.value }))} />
                </Field>

                <div className="mt-5 flex gap-3">
                  <PrimaryButton onClick={createChannel}>Create Channel</PrimaryButton>
                </div>
              </Panel>

              <Panel title="Planning Workspace" subtitle="Weekly themes and per-day overrides stay separate so template logic remains intact.">
                {!selectedChannel && <EmptyState text="Select a channel from the left rail to edit planning details." />}

                {selectedChannel && (
                  <>
                    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                      <div className="flex flex-wrap items-start justify-between gap-4">
                        <div>
                          <h3 className="text-lg font-semibold text-slate-950">{selectedChannel.name}</h3>
                          <p className="mt-1 text-sm text-slate-600">{selectedChannel.description || 'No description provided yet.'}</p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-700">{selectedChannel.platform}</span>
                          <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-700">{selectedChannel.language}</span>
                          <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-700">{selectedChannel.timezone}</span>
                        </div>
                      </div>
                    </div>

                    <div className="mt-5 grid gap-4 md:grid-cols-2">
                      {DAYS.map((day) => (
                        <Field key={day} label={day}>
                          <input
                            className={inputClass}
                            value={weeklyTemplateDraft[day] || ''}
                            onChange={(event) =>
                              setWeeklyTemplateDraft((prev) => ({
                                ...prev,
                                [day]: event.target.value,
                              }))
                            }
                          />
                        </Field>
                      ))}
                    </div>

                    <div className="mt-5 flex gap-3">
                      <PrimaryButton onClick={saveWeeklyTemplate}>Save Weekly Template</PrimaryButton>
                    </div>

                    <div className="mt-8 grid gap-4 rounded-2xl border border-slate-200 bg-slate-50 p-4 md:grid-cols-2">
                      <Field label="Override Date">
                        <input className={inputClass} type="date" value={overrideForm.date} onChange={(event) => setOverrideForm((prev) => ({ ...prev, date: event.target.value }))} />
                      </Field>
                      <Field label="Pillar Override">
                        <input className={inputClass} value={overrideForm.pillar} onChange={(event) => setOverrideForm((prev) => ({ ...prev, pillar: event.target.value }))} />
                      </Field>
                      <Field label="Topic Override">
                        <input className={inputClass} value={overrideForm.topic} onChange={(event) => setOverrideForm((prev) => ({ ...prev, topic: event.target.value }))} />
                      </Field>
                      <Field label="Special Instructions">
                        <input className={inputClass} value={overrideForm.special_instructions} onChange={(event) => setOverrideForm((prev) => ({ ...prev, special_instructions: event.target.value }))} />
                      </Field>
                    </div>

                    <div className="mt-4 flex flex-wrap gap-3">
                      <SecondaryButton onClick={saveOverride}>Save Override</SecondaryButton>
                    </div>

                    <div className="mt-8 rounded-2xl border border-slate-200 bg-slate-950 p-5 text-white">
                      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-indigo-300">
                            Pre-generated Mode
                          </p>
                          <h3 className="mt-2 text-xl font-semibold">Generate a full week of content</h3>
                          <p className="mt-2 text-sm leading-6 text-slate-300">
                            Uses weekly template plus per-day overrides and runs draft generation through the selected Ollama model.
                          </p>
                        </div>
                        <div className="grid gap-3 sm:grid-cols-2">
                          <Field label="Week Start" dark>
                            <input className={darkInputClass} type="date" value={generateStartDate} onChange={(event) => setGenerateStartDate(event.target.value)} />
                          </Field>
                          <Field label="Model" dark>
                            <select className={darkInputClass} value={generateModel} onChange={(event) => setGenerateModel(event.target.value)}>
                              <option value="">Use default model</option>
                              {models.map((model) => (
                                <option key={model} value={model}>{model}</option>
                              ))}
                            </select>
                          </Field>
                        </div>
                      </div>
                      <div className="mt-5">
                        <PrimaryButton onClick={generateWeek}>Generate Week</PrimaryButton>
                      </div>
                    </div>
                  </>
                )}
              </Panel>
            </section>
          )}

          {(activeView === 'workspace' || activeView === 'review') && (
            <Panel title="Review Queue" subtitle="Inline editing, WhatsApp formatting, AI refinement, and clipboard-ready publishing.">
              {reviewQueue.length === 0 && (
                <EmptyState text="No generated drafts yet. Generate a week for the selected channel to populate the queue." />
              )}

              <div className="space-y-5">
                {reviewQueue.map((item) => (
                  <article key={item.id} className="rounded-3xl border border-slate-200 bg-slate-50 p-5">
                    <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-700">
                            {item.date}
                          </span>
                          <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-700">
                            {item.pillar}
                          </span>
                          <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-slate-700">
                            {item.status}
                          </span>
                        </div>
                        <h3 className="mt-3 text-lg font-semibold text-slate-950">{item.topic}</h3>
                      </div>

                      <div className="flex flex-wrap gap-3">
                        <select
                          className={inputClass}
                          value={item.status}
                          onChange={(event) =>
                            setReviewQueue((prev) =>
                              prev.map((entry) =>
                                entry.id === item.id
                                  ? { ...entry, status: event.target.value }
                                  : entry
                              )
                            )
                          }
                        >
                          <option value="draft">draft</option>
                          <option value="ready">ready</option>
                        </select>
                        <SecondaryButton onClick={() => saveReviewItem(item)}>Save</SecondaryButton>
                        <PrimaryButton onClick={() => copyContent(item.content)}>Copy</PrimaryButton>
                      </div>
                    </div>

                    <textarea
                      className={`${textareaClass} mt-4 min-h-[220px] bg-white`}
                      value={item.content}
                      onChange={(event) =>
                        setReviewQueue((prev) =>
                          prev.map((entry) =>
                            entry.id === item.id
                              ? { ...entry, content: event.target.value }
                              : entry
                          )
                        )
                      }
                    />

                    <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4">
                      <p className="text-sm font-semibold text-slate-900">Refinement Chat</p>
                      <div className="mt-3 flex flex-col gap-3 lg:flex-row">
                        <input
                          className={`${inputClass} flex-1`}
                          placeholder="Example: tighten the opening hook and reduce to 180 words"
                          value={refineInputs[item.id] || ''}
                          onChange={(event) =>
                            setRefineInputs((prev) => ({
                              ...prev,
                              [item.id]: event.target.value,
                            }))
                          }
                        />
                        <PrimaryButton onClick={() => refineItem(item.id)}>Refine with AI</PrimaryButton>
                      </div>

                      {item.chat_history?.length > 0 && (
                        <div className="mt-4 space-y-2 rounded-2xl bg-slate-50 p-3">
                          {item.chat_history.map((entry, index) => (
                            <div key={`${item.id}-${index}`} className="text-sm text-slate-600">
                              <span className="font-medium text-slate-900">Instruction:</span> {entry.instruction}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </article>
                ))}
              </div>
            </Panel>
          )}
        </main>
      </div>
    </div>
  )
}

function MetricCard({ label, value, hint }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-slate-950">{value}</p>
      <p className="mt-1 text-xs text-slate-500">{hint}</p>
    </div>
  )
}

function Panel({ title, subtitle, children }) {
  return (
    <section className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-[0_20px_60px_rgba(15,23,42,0.08)] backdrop-blur">
      <div className="mb-5">
        <h2 className="text-xl font-semibold tracking-tight text-slate-950">{title}</h2>
        <p className="mt-1 text-sm text-slate-600">{subtitle}</p>
      </div>
      {children}
    </section>
  )
}

function Field({ label, help, children, className = '', dark = false }) {
  return (
    <label className={`block text-sm ${className}`}>
      <span className={`mb-2 block font-medium ${dark ? 'text-slate-200' : 'text-slate-700'}`}>
        {label}
      </span>
      {children}
      {help && <span className={`mt-2 block text-xs ${dark ? 'text-slate-400' : 'text-slate-500'}`}>{help}</span>}
    </label>
  )
}

function EmptyState({ text }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
      {text}
    </div>
  )
}

function PrimaryButton({ children, onClick }) {
  return (
    <button
      className="rounded-2xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800"
      onClick={onClick}
    >
      {children}
    </button>
  )
}

function SecondaryButton({ children, onClick }) {
  return (
    <button
      className="rounded-2xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-800 transition hover:bg-slate-50"
      onClick={onClick}
    >
      {children}
    </button>
  )
}

const inputClass = 'w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-slate-950'
const textareaClass = 'w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-slate-950'
const darkInputClass = 'w-full rounded-2xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-white outline-none transition focus:border-indigo-400'

export default App
