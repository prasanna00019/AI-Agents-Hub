import { useEffect, useMemo, useState, useCallback } from 'react'
import { Modal } from './components/Modal'
import { PrimaryButton, SecondaryButton, DangerButton } from './components/Buttons'
import { Field, EmptyState } from './components/Field'
import { MetricCard, Panel } from './components/MetricCard'
import { SourceInbox } from './components/SourceInbox'
import { ContentCalendar } from './components/ContentCalendar'
import { LoadingOverlay, SkeletonCard, InlineLoader } from './components/Loading'
import { AgentProgress } from './components/AgentProgress'
import { Sidebar, MobileHeader } from './components/Sidebar'

const DAYS = ['monday','tuesday','wednesday','thursday','friday','saturday','sunday']
const DEFAULT_TEMPLATE = {
  monday: 'Concept Deep Dive',
  tuesday: 'Tool Spotlight',
  wednesday: 'AI News Highlight',
  thursday: 'Tutorial / How-To',
  friday: 'Opinion / Commentary',
  saturday: 'Case Study',
  sunday: 'Weekly Summary',
}
const CHANNEL_INIT = {
  name: '', description: '', audience: '', tone: 'Educational',
  platform: 'whatsapp', language: 'en', timezone: 'UTC',
  prompt_template: '', sources_text: '',
}

function App() {
  const api = useMemo(() => import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000', [])

  // ── State ──────────────────────────────────────────────────────────
  const [activeView, setActiveView] = useState('dashboard')
  const [health, setHealth] = useState('checking')
  const [notice, setNotice] = useState(null)
  const [models, setModels] = useState([])
  const [channels, setChannels] = useState([])
  const [selectedChannelId, setSelectedChannelId] = useState('')
  const [reviewQueue, setReviewQueue] = useState([])
  const [refineInputs, setRefineInputs] = useState({})
  const [generateModel, setGenerateModel] = useState('')
  const [generateStartDate, setGenerateStartDate] = useState(new Date().toISOString().slice(0, 10))
  const [settings, setSettings] = useState({
    database_url: '', ollama_base_url: 'http://localhost:11434',
    default_ollama_model: '', searxng_url: 'http://localhost:8080',
  })
  const [channelForm, setChannelForm] = useState(CHANNEL_INIT)
  const [weeklyTemplateDraft, setWeeklyTemplateDraft] = useState({ ...DEFAULT_TEMPLATE })
  const [overrideForm, setOverrideForm] = useState({ date: '', pillar: '', topic: '', special_instructions: '', mode: 'pre_generated' })
  const [sourceDumps, setSourceDumps] = useState([])
  const [newSourceDump, setNewSourceDump] = useState({ type: 'text', label: '', raw_content: '' })
  const [isMobileOpen, setMobileOpen] = useState(false)
  const [searxngStatus, setSearxngStatus] = useState({ running: false })

  // Loading states
  const [generating, setGenerating] = useState(false)
  const [loadingChannels, setLoadingChannels] = useState(true)
  const [loadingModels, setLoadingModels] = useState(true)
  const [loadingReview, setLoadingReview] = useState(false)
  const [savingSettings, setSavingSettings] = useState(false)
  const [creatingChannel, setCreatingChannel] = useState(false)
  const [refiningId, setRefiningId] = useState(null)
  const [generatingDay, setGeneratingDay] = useState(false)
  const [agentLogs, setAgentLogs] = useState([])

  const selectedChannel = channels.find(c => c.id === selectedChannelId)

  const feedback = useCallback((message, tone = 'info') => {
    setNotice({ message, tone })
    setTimeout(() => setNotice(null), 5000)
  }, [])

  // ── API helper ─────────────────────────────────────────────────────
  const callApi = useCallback(async (path, opts = {}) => {
    const resp = await fetch(`${api}${path}`, { headers: { 'Content-Type': 'application/json' }, ...opts })
    if (!resp.ok) { const t = await resp.text(); throw new Error(t || `Request failed: ${resp.status}`) }
    return resp.json()
  }, [api])

  // ── Boot ───────────────────────────────────────────────────────────
  const loadHealth = useCallback(async () => {
    try { await callApi('/health'); setHealth('connected') } catch { setHealth('down') }
  }, [callApi])

  const loadSettings = useCallback(async () => {
    const d = await callApi('/api/v1/settings'); setSettings(d); return d
  }, [callApi])

  const loadModels = useCallback(async () => {
    setLoadingModels(true)
    try {
      const d = await callApi('/api/v1/ollama/models')
      setModels(d.models || [])
      if (d.models?.length > 0 && !settings.default_ollama_model)
        setSettings(p => ({ ...p, default_ollama_model: d.models[0] }))
    } finally { setLoadingModels(false) }
  }, [callApi, settings.default_ollama_model])

  const loadChannels = useCallback(async () => {
    setLoadingChannels(true)
    try {
      const d = await callApi('/api/v1/channels')
      setChannels(d)
      if (d.length > 0 && !selectedChannelId) setSelectedChannelId(d[0].id)
    } finally { setLoadingChannels(false) }
  }, [callApi, selectedChannelId])

  const loadReviewQueue = useCallback(async (chId) => {
    if (!chId) { setReviewQueue([]); return }
    setLoadingReview(true)
    try { const d = await callApi(`/api/v1/review-queue?channel_id=${chId}`); setReviewQueue(d) }
    finally { setLoadingReview(false) }
  }, [callApi])

  const loadSearxngStatus = useCallback(async () => {
    try { const d = await callApi('/api/v1/searxng/status'); setSearxngStatus(d) } catch {}
  }, [callApi])

  useEffect(() => {
    (async () => {
      await loadHealth()
      await loadSettings()
      await loadModels()
      await loadChannels()
      await loadSearxngStatus()
    })().catch(e => feedback(e.message, 'error'))
  }, []) // eslint-disable-line

  useEffect(() => { loadReviewQueue(selectedChannelId).catch(e => feedback(e.message, 'error')) }, [selectedChannelId]) // eslint-disable-line

  const loadSourceDumps = useCallback(async (chId, dateKey) => {
    if (!chId || !dateKey) return
    try { const d = await callApi(`/api/v1/channels/${chId}/source-dumps?date=${dateKey}`); setSourceDumps(d) } catch {}
  }, [callApi])

  useEffect(() => { if (selectedChannelId && overrideForm.date) loadSourceDumps(selectedChannelId, overrideForm.date) }, [selectedChannelId, overrideForm.date]) // eslint-disable-line
  useEffect(() => {
    if (!selectedChannel) { setWeeklyTemplateDraft({ ...DEFAULT_TEMPLATE }); return }
    setWeeklyTemplateDraft({ ...DEFAULT_TEMPLATE, ...(selectedChannel.weekly_template || {}) })
  }, [selectedChannel])

  // ── Actions ────────────────────────────────────────────────────────
  const saveSettings = async () => {
    setSavingSettings(true)
    try {
      await callApi('/api/v1/settings', { method: 'PUT', body: JSON.stringify(settings) })
      await loadModels()
      feedback('Settings saved', 'success')
    } catch (e) { feedback(e.message, 'error') }
    finally { setSavingSettings(false) }
  }

  const testDb = async () => {
    try {
      const r = await callApi(`/api/v1/settings/test-db?database_url=${encodeURIComponent(settings.database_url)}`)
      feedback(r.message, r.ok ? 'success' : 'error')
    } catch (e) { feedback(e.message, 'error') }
  }

  const createChannel = async () => {
    setCreatingChannel(true)
    try {
      const payload = { ...channelForm, sources: channelForm.sources_text.split('\n').map(l => l.trim()).filter(Boolean), weekly_template: weeklyTemplateDraft }
      delete payload.sources_text
      const created = await callApi('/api/v1/channels', { method: 'POST', body: JSON.stringify(payload) })
      await loadChannels()
      setSelectedChannelId(created.id)
      setChannelForm(CHANNEL_INIT)
      setActiveView('planner')
      feedback('Channel created', 'success')
    } catch (e) { feedback(e.message, 'error') }
    finally { setCreatingChannel(false) }
  }

  const deleteChannel = async (id) => {
    if (!window.confirm('Delete this channel? This cannot be undone.')) return
    try {
      await callApi(`/api/v1/channels/${id}`, { method: 'DELETE' })
      if (selectedChannelId === id) setSelectedChannelId('')
      await loadChannels()
      feedback('Channel deleted', 'success')
    } catch (e) { feedback(e.message, 'error') }
  }

  const saveWeeklyTemplate = async () => {
    if (!selectedChannelId) return feedback('Select a channel first', 'error')
    try {
      await callApi(`/api/v1/channels/${selectedChannelId}/weekly-template`, { method: 'POST', body: JSON.stringify({ weekly_template: weeklyTemplateDraft }) })
      await loadChannels()
      feedback('Weekly template updated', 'success')
    } catch (e) { feedback(e.message, 'error') }
  }

  const saveOverride = async () => {
    if (!selectedChannelId) return feedback('Select a channel first', 'error')
    try {
      await callApi(`/api/v1/channels/${selectedChannelId}/overrides`, { method: 'POST', body: JSON.stringify(overrideForm) })
      await loadChannels()
      feedback('Override saved', 'success')
    } catch (e) { feedback(e.message, 'error') }
  }

  const addSourceDump = async () => {
    if (!selectedChannelId || !overrideForm.date) return
    try {
      await callApi(`/api/v1/channels/${selectedChannelId}/source-dumps?date=${overrideForm.date}`, { method: 'POST', body: JSON.stringify(newSourceDump) })
      setNewSourceDump({ type: 'text', label: '', raw_content: '' })
      loadSourceDumps(selectedChannelId, overrideForm.date)
      feedback('Source added', 'success')
    } catch (e) { feedback(e.message, 'error') }
  }

  const deleteSourceDump = async (dumpId) => {
    if (!selectedChannelId || !overrideForm.date) return
    try {
      await callApi(`/api/v1/channels/${selectedChannelId}/source-dumps/${dumpId}`, { method: 'DELETE' })
      loadSourceDumps(selectedChannelId, overrideForm.date)
      feedback('Source removed', 'success')
    } catch (e) { feedback(e.message, 'error') }
  }

  const generateDay = async () => {
    if (!selectedChannelId || !overrideForm.date) return
    setGeneratingDay(true); setAgentLogs([])
    try {
      await callApi(`/api/v1/channels/${selectedChannelId}/generate-day`, { method: 'POST', body: JSON.stringify({ date: overrideForm.date }) })
      await loadReviewQueue(selectedChannelId)
      setOverrideForm(p => ({ ...p, date: '' }))
      setActiveView('review')
      feedback('Content generated for ' + overrideForm.date, 'success')
    } catch (e) { feedback(e.message, 'error') }
    finally { setGeneratingDay(false) }
  }

  const generateWeek = async () => {
    if (!selectedChannelId) return feedback('Select a channel first', 'error')
    setGenerating(true); setAgentLogs([])
    try {
      const result = await callApi(`/api/v1/channels/${selectedChannelId}/generate-week`, { method: 'POST', body: JSON.stringify({ start_date: generateStartDate, model: generateModel || settings.default_ollama_model }) })

      // Connect SSE stream
      if (result.run_id) {
        const es = new EventSource(`${api}/api/v1/generation/stream/${result.run_id}`)
        es.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            setAgentLogs(prev => [...prev, data])
            if (data.status === 'done' && data.step === 'pipeline') {
              es.close()
              setGenerating(false)
              loadReviewQueue(selectedChannelId)
              setActiveView('review')
              feedback('Week generation complete', 'success')
            }
          } catch {}
        }
        es.onerror = () => { es.close(); setGenerating(false); feedback('Generation stream disconnected', 'error') }
      }
    } catch (e) { feedback(e.message, 'error'); setGenerating(false) }
  }

  const saveReviewItem = async (item) => {
    try {
      await callApi(`/api/v1/review-queue/${item.id}`, { method: 'PUT', body: JSON.stringify({ content: item.content, status: item.status }) })
      feedback('Saved', 'success')
    } catch (e) { feedback(e.message, 'error') }
  }

  const deleteReviewItem = async (id) => {
    if (!window.confirm('Delete this draft?')) return
    try {
      await callApi(`/api/v1/review-queue/${id}`, { method: 'DELETE' })
      await loadReviewQueue(selectedChannelId)
      feedback('Draft deleted', 'success')
    } catch (e) { feedback(e.message, 'error') }
  }

  const refineItem = async (itemId) => {
    const instruction = refineInputs[itemId]
    if (!instruction) return feedback('Enter a refinement instruction', 'error')
    setRefiningId(itemId)
    try {
      await callApi(`/api/v1/review-queue/${itemId}/refine`, { method: 'POST', body: JSON.stringify({ instruction, model: settings.default_ollama_model }) })
      setRefineInputs(p => ({ ...p, [itemId]: '' }))
      await loadReviewQueue(selectedChannelId)
      feedback('AI refinement complete', 'success')
    } catch (e) { feedback(e.message, 'error') }
    finally { setRefiningId(null) }
  }

  const copyContent = async (content) => { await navigator.clipboard.writeText(content); feedback('Copied to clipboard', 'success') }

  const toggleSearxng = async () => {
    try {
      if (searxngStatus.running) {
        const r = await callApi('/api/v1/searxng/stop', { method: 'POST' })
        feedback(r.message, r.ok ? 'success' : 'error')
      } else {
        const r = await callApi('/api/v1/searxng/start', { method: 'POST' })
        feedback(r.message, r.ok ? 'success' : 'error')
      }
      await loadSearxngStatus()
    } catch (e) { feedback(e.message, 'error') }
  }

  // ── Render ──────────────────────────────────────────────────────────
  const inputClass = 'w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100'
  const textareaClass = inputClass
  const darkInputClass = 'w-full rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2.5 text-sm text-white outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-900'

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50/30 font-sans text-slate-800 antialiased">
      <MobileHeader setMobileOpen={setMobileOpen} activeView={activeView} />

      <div className="flex min-h-screen gap-0 lg:gap-5 lg:p-4">
        <Sidebar
          activeView={activeView} setActiveView={setActiveView}
          channels={channels} selectedChannelId={selectedChannelId}
          setSelectedChannelId={setSelectedChannelId}
          health={health} modelsCount={models.length}
          isMobileOpen={isMobileOpen} setMobileOpen={setMobileOpen}
        />

        <main className="min-w-0 flex-1 space-y-5 px-4 py-5 lg:px-0 lg:py-0">

          {/* ── Toast ───────────────────────────────────────────── */}
          {notice && (
            <div className={`animate-slide-in fixed right-4 top-4 z-[70] rounded-xl px-5 py-3 text-sm font-semibold shadow-lg ${
              notice.tone === 'error' ? 'bg-rose-600 text-white' :
              notice.tone === 'success' ? 'bg-emerald-600 text-white' :
              'bg-slate-800 text-white'
            }`}>
              {notice.message}
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════
              DASHBOARD VIEW
          ═══════════════════════════════════════════════════════ */}
          {activeView === 'dashboard' && (
            <div className="space-y-5 animate-fade-in">
              <div className="rounded-2xl border border-slate-100 bg-white p-6">
                <p className="text-xs font-bold uppercase tracking-[0.2em] text-indigo-600">ContentPilot</p>
                <h2 className="mt-2 text-2xl font-bold text-slate-900">Welcome to your Content Hub</h2>
                <p className="mt-2 text-sm text-slate-500 max-w-2xl">Manage channels, plan weekly content, generate with AI agents, and review drafts — all from one place.</p>
              </div>

              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <MetricCard label="Channels" value={String(channels.length)} hint="Active channels" icon="◈" />
                <MetricCard label="Models" value={String(models.length)} hint="Ollama models" icon="⬡" />
                <MetricCard label="Drafts" value={String(reviewQueue.length)} hint="In review queue" icon="◎" />
                <MetricCard
                  label="SearXNG"
                  value={searxngStatus.running ? 'Online' : 'Offline'}
                  hint={`Port ${searxngStatus.port || 8080}`}
                  icon={searxngStatus.running ? '🟢' : '🔴'}
                />
              </div>

              {/* Quick actions */}
              <Panel title="Quick Actions" subtitle="Jump to common tasks">
                <div className="flex flex-wrap gap-3">
                  <PrimaryButton onClick={() => setActiveView('channels')}>+ New Channel</PrimaryButton>
                  <SecondaryButton onClick={() => setActiveView('calendar')}>View Calendar</SecondaryButton>
                  <SecondaryButton onClick={() => setActiveView('review')}>Review Queue ({reviewQueue.length})</SecondaryButton>
                  <SecondaryButton onClick={toggleSearxng}>
                    {searxngStatus.running ? '⏹ Stop SearXNG' : '▶ Start SearXNG'}
                  </SecondaryButton>
                </div>
              </Panel>

              {/* Today's ready posts */}
              {reviewQueue.filter(r => r.status === 'ready').length > 0 && (
                <Panel title="Ready to Publish" subtitle="These posts are approved and ready for copy-paste.">
                  <div className="space-y-3">
                    {reviewQueue.filter(r => r.status === 'ready').map(item => (
                      <div key={item.id} className="flex items-center justify-between rounded-xl border border-emerald-100 bg-emerald-50/50 px-4 py-3">
                        <div>
                          <p className="text-sm font-semibold text-slate-900">{item.topic}</p>
                          <p className="text-xs text-slate-500">{item.date} · {item.pillar}</p>
                        </div>
                        <PrimaryButton onClick={() => copyContent(item.content)} className="!py-1.5 !px-3 !text-xs">Copy</PrimaryButton>
                      </div>
                    ))}
                  </div>
                </Panel>
              )}
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════
              CHANNELS VIEW
          ═══════════════════════════════════════════════════════ */}
          {activeView === 'channels' && (
            <div className="space-y-5 animate-fade-in">
              <Panel title="Create Channel" subtitle="Set up a new content channel with profile, sources, and prompt template.">
                <div className="grid gap-4 md:grid-cols-2">
                  <Field label="Channel Name"><input className={inputClass} value={channelForm.name} onChange={e => setChannelForm(p => ({ ...p, name: e.target.value }))} placeholder="e.g. AI News Daily" /></Field>
                  <Field label="Audience"><input className={inputClass} value={channelForm.audience} onChange={e => setChannelForm(p => ({ ...p, audience: e.target.value }))} placeholder="e.g. Indian AI enthusiasts, 22-40" /></Field>
                  <Field label="Tone"><input className={inputClass} value={channelForm.tone} onChange={e => setChannelForm(p => ({ ...p, tone: e.target.value }))} /></Field>
                  <Field label="Platform">
                    <select className={inputClass} value={channelForm.platform} onChange={e => setChannelForm(p => ({ ...p, platform: e.target.value }))}>
                      <option value="whatsapp">WhatsApp</option>
                      <option value="telegram">Telegram</option>
                      <option value="linkedin">LinkedIn</option>
                      <option value="twitter">Twitter/X</option>
                    </select>
                  </Field>
                  <Field label="Language"><input className={inputClass} value={channelForm.language} onChange={e => setChannelForm(p => ({ ...p, language: e.target.value }))} /></Field>
                  <Field label="Timezone"><input className={inputClass} value={channelForm.timezone} onChange={e => setChannelForm(p => ({ ...p, timezone: e.target.value }))} /></Field>
                </div>
                <Field label="Description" className="mt-4"><textarea className={textareaClass} rows={3} value={channelForm.description} onChange={e => setChannelForm(p => ({ ...p, description: e.target.value }))} placeholder="What is this channel about?" /></Field>
                <Field label="Sources" help="One URL or search query per line." className="mt-4"><textarea className={textareaClass} rows={4} value={channelForm.sources_text} onChange={e => setChannelForm(p => ({ ...p, sources_text: e.target.value }))} placeholder="https://techcrunch.com&#10;AI news this week&#10;..." /></Field>
                <Field label="Prompt Template" className="mt-4"><textarea className={textareaClass} rows={4} value={channelForm.prompt_template} onChange={e => setChannelForm(p => ({ ...p, prompt_template: e.target.value }))} placeholder="Custom instructions for content generation..." /></Field>
                <div className="mt-5"><PrimaryButton onClick={createChannel} loading={creatingChannel}>Create Channel</PrimaryButton></div>
              </Panel>

              {/* Existing channels */}
              {loadingChannels ? <SkeletonCard /> : channels.length > 0 && (
                <Panel title="Your Channels" subtitle="Select a channel to plan content.">
                  <div className="space-y-3">
                    {channels.map(ch => (
                      <div key={ch.id} className={`flex items-center justify-between rounded-xl border px-4 py-3 transition cursor-pointer hover:shadow-md ${selectedChannelId === ch.id ? 'border-indigo-200 bg-indigo-50/50' : 'border-slate-100 bg-slate-50/50'}`} onClick={() => { setSelectedChannelId(ch.id); setActiveView('planner') }}>
                        <div className="min-w-0">
                          <p className="font-semibold text-slate-900">{ch.name}</p>
                          <p className="mt-0.5 text-xs text-slate-500 truncate">{ch.audience || ch.description || 'No description'}</p>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <span className="rounded-lg bg-white px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-500 border border-slate-100">{ch.platform}</span>
                          <DangerButton onClick={(e) => { e.stopPropagation(); deleteChannel(ch.id) }} className="!py-1 !px-2.5 !text-[11px]">Delete</DangerButton>
                        </div>
                      </div>
                    ))}
                  </div>
                </Panel>
              )}
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════
              PLANNER VIEW
          ═══════════════════════════════════════════════════════ */}
          {activeView === 'planner' && (
            <div className="space-y-5 animate-fade-in">
              {!selectedChannel ? (
                <EmptyState text="Select a channel from the sidebar to start planning." icon="◇" />
              ) : (
                <>
                  {/* Channel info */}
                  <div className="rounded-2xl border border-slate-100 bg-white p-5">
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div>
                        <h2 className="text-xl font-bold text-slate-900">{selectedChannel.name}</h2>
                        <p className="mt-1 text-sm text-slate-500">{selectedChannel.description || 'No description'}</p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {[selectedChannel.platform, selectedChannel.language, selectedChannel.tone].map(tag => (
                          <span key={tag} className="rounded-lg border border-slate-100 bg-slate-50 px-2.5 py-1 text-[11px] font-semibold text-slate-600">{tag}</span>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Weekly template */}
                  <Panel title="Weekly Template" subtitle="Default content pillar for each day. Overrides are per-date.">
                    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                      {DAYS.map(day => (
                        <Field key={day} label={day}>
                          <input className={inputClass} value={weeklyTemplateDraft[day] || ''} onChange={e => setWeeklyTemplateDraft(p => ({ ...p, [day]: e.target.value }))} />
                        </Field>
                      ))}
                    </div>
                    <div className="mt-4"><PrimaryButton onClick={saveWeeklyTemplate}>Save Template</PrimaryButton></div>
                  </Panel>

                  {/* Generate week */}
                  <div className="rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900 to-indigo-950 p-6 text-white">
                    <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-indigo-300">Pre-Generated Mode</p>
                    <h3 className="mt-2 text-lg font-bold">Generate a Full Week</h3>
                    <p className="mt-1 text-sm text-slate-400 max-w-xl">Uses weekly template + per-day overrides to generate 7 days of content through the 5-agent pipeline.</p>
                    <div className="mt-5 flex flex-wrap gap-4 items-end">
                      <Field label="Week Start" dark><input className={darkInputClass} type="date" value={generateStartDate} onChange={e => setGenerateStartDate(e.target.value)} /></Field>
                      <Field label="Model" dark>
                        <select className={darkInputClass} value={generateModel} onChange={e => setGenerateModel(e.target.value)}>
                          <option value="">Use default</option>
                          {models.map(m => <option key={m} value={m}>{m}</option>)}
                        </select>
                      </Field>
                      <PrimaryButton onClick={generateWeek} loading={generating}>Generate Week</PrimaryButton>
                    </div>
                  </div>

                  {/* Agent progress */}
                  {(generating || agentLogs.length > 0) && (
                    <AgentProgress logs={agentLogs} isRunning={generating} />
                  )}
                </>
              )}
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════
              CALENDAR VIEW
          ═══════════════════════════════════════════════════════ */}
          {activeView === 'calendar' && (
            <div className="space-y-5 animate-fade-in">
              {!selectedChannel ? (
                <EmptyState text="Select a channel to view its content calendar." icon="▦" />
              ) : (
                <Panel title={`${selectedChannel.name} — Calendar`} subtitle="Click any day to plan or override.">
                  <ContentCalendar
                    selectedChannel={selectedChannel}
                    weeklyTemplateDraft={weeklyTemplateDraft}
                    reviewQueue={reviewQueue}
                    setOverrideForm={setOverrideForm}
                  />
                </Panel>
              )}
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════
              REVIEW QUEUE VIEW
          ═══════════════════════════════════════════════════════ */}
          {activeView === 'review' && (
            <div className="space-y-5 animate-fade-in">
              <Panel title="Review Queue" subtitle="Edit, refine with AI, and copy-paste ready content.">
                {loadingReview ? <InlineLoader text="Loading review queue..." /> :
                  reviewQueue.length === 0 ? <EmptyState text="No drafts yet. Generate content to populate the queue." icon="◎" /> : (
                  <div className="space-y-4">
                    {reviewQueue.map(item => (
                      <article key={item.id} className="rounded-xl border border-slate-100 bg-slate-50/50 p-5 transition hover:shadow-sm">
                        <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
                          <div>
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="rounded-lg bg-white px-2.5 py-1 text-[11px] font-bold text-slate-600 border border-slate-100">{item.date}</span>
                              <span className="rounded-lg bg-white px-2.5 py-1 text-[11px] font-bold text-slate-600 border border-slate-100">{item.pillar}</span>
                              <span className={`rounded-lg px-2.5 py-1 text-[11px] font-bold ${item.status === 'ready' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>{item.status}</span>
                            </div>
                            <h3 className="mt-2 text-base font-bold text-slate-900">{item.topic}</h3>
                          </div>
                          <div className="flex flex-wrap gap-2">
                            <select
                              className={`${inputClass} !w-auto`}
                              value={item.status}
                              onChange={e => setReviewQueue(p => p.map(r => r.id === item.id ? { ...r, status: e.target.value } : r))}
                            >
                              <option value="draft">Draft</option>
                              <option value="ready">Ready</option>
                            </select>
                            <SecondaryButton onClick={() => saveReviewItem(item)}>Save</SecondaryButton>
                            <PrimaryButton onClick={() => copyContent(item.content)}>Copy</PrimaryButton>
                            <DangerButton onClick={() => deleteReviewItem(item.id)} className="!py-1.5 !px-3 !text-xs">Delete</DangerButton>
                          </div>
                        </div>

                        <textarea
                          className={`${textareaClass} mt-4 min-h-[200px] bg-white`}
                          value={item.content}
                          onChange={e => setReviewQueue(p => p.map(r => r.id === item.id ? { ...r, content: e.target.value } : r))}
                        />

                        {/* Refinement chat */}
                        <div className="mt-4 rounded-xl border border-slate-100 bg-white p-4">
                          <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">Refinement Chat</p>
                          <div className="flex flex-col gap-3 lg:flex-row">
                            <input
                              className={`${inputClass} flex-1`}
                              placeholder="e.g. tighten the hook, reduce to 180 words"
                              value={refineInputs[item.id] || ''}
                              onChange={e => setRefineInputs(p => ({ ...p, [item.id]: e.target.value }))}
                              onKeyDown={e => { if (e.key === 'Enter') refineItem(item.id) }}
                            />
                            <PrimaryButton onClick={() => refineItem(item.id)} loading={refiningId === item.id}>Refine with AI</PrimaryButton>
                          </div>
                          {item.chat_history?.length > 0 && (
                            <div className="mt-3 space-y-1.5 max-h-32 overflow-y-auto rounded-lg bg-slate-50 p-3">
                              {item.chat_history.map((entry, i) => (
                                <div key={i} className="flex items-start gap-2 text-xs">
                                  <span className="shrink-0 text-indigo-500 font-bold">→</span>
                                  <span className="text-slate-600">{entry.instruction}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </article>
                    ))}
                  </div>
                )}
              </Panel>
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════
              SETTINGS VIEW
          ═══════════════════════════════════════════════════════ */}
          {activeView === 'settings' && (
            <div className="space-y-5 animate-fade-in">
              <Panel title="System Settings" subtitle="Configure database, model access, and search endpoints.">
                <div className="grid gap-4 md:grid-cols-2">
                  <Field label="PostgreSQL URL"><input className={inputClass} value={settings.database_url || ''} onChange={e => setSettings(p => ({ ...p, database_url: e.target.value }))} /></Field>
                  <Field label="Ollama Base URL"><input className={inputClass} value={settings.ollama_base_url || ''} onChange={e => setSettings(p => ({ ...p, ollama_base_url: e.target.value }))} /></Field>
                  <Field label="Default Model">
                    <select className={inputClass} value={settings.default_ollama_model || ''} onChange={e => setSettings(p => ({ ...p, default_ollama_model: e.target.value }))}>
                      <option value="">Select model</option>
                      {models.map(m => <option key={m} value={m}>{m}</option>)}
                    </select>
                  </Field>
                  <Field label="SearXNG URL"><input className={inputClass} value={settings.searxng_url || ''} onChange={e => setSettings(p => ({ ...p, searxng_url: e.target.value }))} /></Field>
                </div>
                <div className="mt-5 flex flex-wrap gap-3">
                  <PrimaryButton onClick={saveSettings} loading={savingSettings}>Save Settings</PrimaryButton>
                  <SecondaryButton onClick={testDb}>Test Database</SecondaryButton>
                  <SecondaryButton onClick={loadModels} loading={loadingModels}>Refresh Models</SecondaryButton>
                </div>
              </Panel>

              {/* Models list */}
              <Panel title="Ollama Models" subtitle="Auto-detected from local Ollama instance.">
                {loadingModels ? <InlineLoader text="Fetching models..." /> : models.length === 0 ? (
                  <EmptyState text="No models found. Ensure Ollama is running on localhost:11434." icon="⬡" />
                ) : (
                  <div className="space-y-2">
                    {models.map(m => (
                      <div key={m} className="flex items-center justify-between rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
                        <span className="text-sm font-medium text-slate-800">{m}</span>
                        {settings.default_ollama_model === m && (
                          <span className="rounded-lg bg-indigo-100 px-2 py-0.5 text-[10px] font-bold text-indigo-700">Default</span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </Panel>

              {/* SearXNG control */}
              <Panel title="SearXNG Engine" subtitle="Control the local SearXNG Docker container for web search.">
                <div className="flex items-center justify-between rounded-xl border border-slate-100 bg-slate-50 px-5 py-4">
                  <div>
                    <p className="text-sm font-semibold text-slate-900">Container Status</p>
                    <p className="mt-0.5 text-xs text-slate-500">
                      {searxngStatus.running ? '🟢 Running on port ' + (searxngStatus.port || 8080) : '🔴 Not running'}
                    </p>
                  </div>
                  {searxngStatus.running ? (
                    <DangerButton onClick={toggleSearxng}>Stop SearXNG</DangerButton>
                  ) : (
                    <PrimaryButton onClick={toggleSearxng}>Start SearXNG</PrimaryButton>
                  )}
                </div>
              </Panel>
            </div>
          )}
        </main>
      </div>

      {/* ── Override Modal ──────────────────────────────────────── */}
      <Modal
        isOpen={!!overrideForm.date}
        onClose={() => setOverrideForm(p => ({ ...p, date: '' }))}
        title={`Day Plan: ${overrideForm.date}`}
        wide
      >
        <div className="space-y-5">
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="Content Pillar"><input className={inputClass} value={overrideForm.pillar} onChange={e => setOverrideForm(p => ({ ...p, pillar: e.target.value }))} placeholder="Override template pillar" /></Field>
            <Field label="Topic"><input className={inputClass} value={overrideForm.topic} onChange={e => setOverrideForm(p => ({ ...p, topic: e.target.value }))} placeholder="Specific subject for this day" /></Field>
            <Field label="Special Instructions"><input className={inputClass} value={overrideForm.special_instructions} onChange={e => setOverrideForm(p => ({ ...p, special_instructions: e.target.value }))} placeholder="e.g. Keep under 300 words" /></Field>
            <Field label="Generation Mode">
              <select className={inputClass} value={overrideForm.mode} onChange={e => setOverrideForm(p => ({ ...p, mode: e.target.value }))}>
                <option value="pre_generated">Pre-Generated</option>
                <option value="source_dump">Source Dump</option>
              </select>
            </Field>
          </div>

          <div className="flex flex-wrap gap-3">
            <SecondaryButton onClick={async () => { await saveOverride(); setOverrideForm(p => ({ ...p, date: '' })) }}>Save Override</SecondaryButton>
            <PrimaryButton onClick={generateDay} loading={generatingDay}>Generate This Day</PrimaryButton>
          </div>

          {overrideForm.mode === 'source_dump' && (
            <SourceInbox
              sourceDumps={sourceDumps}
              newSourceDump={newSourceDump}
              setNewSourceDump={setNewSourceDump}
              addSourceDump={addSourceDump}
              deleteSourceDump={deleteSourceDump}
              inputClass={inputClass}
            />
          )}
        </div>
      </Modal>

      {/* ── Loading overlay ─────────────────────────────────────── */}
      <LoadingOverlay active={generatingDay} message="Generating content…" logs={agentLogs} />
    </div>
  )
}

export default App
