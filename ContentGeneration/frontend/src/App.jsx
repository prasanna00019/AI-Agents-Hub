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

const DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
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
const EMPTY_SETTINGS = {
  database_url: '',
  ollama_base_url: '',
  default_ollama_model: '',
  searxng_url: '',
}

const normalizeUrlInput = (value) => value.trim().replace(/\/+$/, '')

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
  const [reviewFilterDate, setReviewFilterDate] = useState('')
  const [reviewFilterStatus, setReviewFilterStatus] = useState('all')
  const [refineInputs, setRefineInputs] = useState({})
  const [generateModel, setGenerateModel] = useState('')
  const [generateStartDate, setGenerateStartDate] = useState(new Date().toISOString().slice(0, 10))
  const [settings, setSettings] = useState(() => {
    const saved = localStorage.getItem('contentpilot_settings')
    if (saved) {
      try { 
        return {
          ...EMPTY_SETTINGS,
          ...JSON.parse(saved)
        }
      } catch (e) { }
    }
    return { ...EMPTY_SETTINGS }
  })

  // Persist settings to local storage whenever they change
  useEffect(() => {
    localStorage.setItem('contentpilot_settings', JSON.stringify(settings))
  }, [settings])

  const [channelForm, setChannelForm] = useState(CHANNEL_INIT)
  const [weeklyTemplateDraft, setWeeklyTemplateDraft] = useState({ ...DEFAULT_TEMPLATE })
  const [overrideForm, setOverrideForm] = useState({ date: '', pillar: '', topic: '', special_instructions: '', mode: 'pre_generated' })
  const [sourceDumps, setSourceDumps] = useState([])
  const [newSourceDump, setNewSourceDump] = useState({ type: 'text', label: '', raw_content: '' })
  const [isMobileOpen, setMobileOpen] = useState(false)
  const [searxngStatus, setSearxngStatus] = useState({ running: false, configured: false, controllable: false, url: '', port: null })

  // Loading states
  const [generating, setGenerating] = useState(false)
  const [loadingChannels, setLoadingChannels] = useState(true)
  const [loadingModels, setLoadingModels] = useState(true)
  const [loadingReview, setLoadingReview] = useState(false)
  const [savingSettings, setSavingSettings] = useState(false)
  const [creatingChannel, setCreatingChannel] = useState(false)
  const [agentLogs, setAgentLogs] = useState([])
  const [togglingSearxng, setTogglingSearxng] = useState(false)
  const [testingDb, setTestingDb] = useState(false)
  const [refiningId, setRefiningId] = useState(null)
  const [generatingDay, setGeneratingDay] = useState(false)

  // Calendar day detail modal (separate from override modal)
  const [dayDetailDate, setDayDetailDate] = useState('')

  const selectedChannel = channels.find(c => c.id === selectedChannelId)

  // Derived: find review item for the calendar day detail
  const dayDetailItem = reviewQueue.find(r => r.date === dayDetailDate) || null

  const feedback = useCallback((message, tone = 'info') => {
    setNotice({ message, tone })
    setTimeout(() => setNotice(null), 5000)
  }, [])

  // ── API helper ─────────────────────────────────────────────────────
  const callApi = useCallback(async (path, opts = {}) => {
    const controller = new AbortController()
    const id = setTimeout(() => controller.abort(), 30000) // 30s timeout
    
    try {
      const resp = await fetch(`${api}${path}`, { 
        headers: { 'Content-Type': 'application/json' }, 
        signal: controller.signal,
        ...opts 
      })
      clearTimeout(id)
      if (!resp.ok) { const t = await resp.text(); throw new Error(t || `Request failed: ${resp.status}`) }
      return resp.json()
    } catch (e) {
      clearTimeout(id)
      if (e.name === 'AbortError') throw new Error('Request timed out after 30 seconds')
      throw e
    }
  }, [api])

  // ── Boot ───────────────────────────────────────────────────────────
  const loadHealth = useCallback(async () => {
    try { await callApi('/health'); setHealth('connected') } catch { setHealth('down') }
  }, [callApi])

  const loadSettings = useCallback(async () => {
    const d = await callApi('/api/v1/settings')
    const nextSettings = { ...EMPTY_SETTINGS, ...d }
    setSettings(nextSettings)
    return nextSettings
  }, [callApi])

  const loadModels = useCallback(async ({ baseUrl = '', defaultModel = '', silent = false } = {}) => {
    setLoadingModels(true)
    try {
      const normalizedBaseUrl = normalizeUrlInput(baseUrl)
      if (!normalizedBaseUrl) {
        setModels([])
        return { ok: false, models: [], base_url: '', message: 'Ollama Base URL is not configured.' }
      }

      const d = await callApi(`/api/v1/ollama/models?base_url=${encodeURIComponent(normalizedBaseUrl)}`)
      setModels(d.models || [])

      if (d.ok === false && d.message && !silent) {
        feedback(`Ollama error: ${d.message}`, 'error')
      }

      if (d.models?.length > 0 && !defaultModel) {
        setSettings(p => (p.default_ollama_model ? p : { ...p, default_ollama_model: d.models[0] }))
      }
      return d
    } catch (e) {
      if (!silent) feedback(e.message, 'error')
      return { ok: false, models: [], base_url: normalizeUrlInput(baseUrl), message: e.message }
    } finally { setLoadingModels(false) }
  }, [callApi, feedback])

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
    try { const d = await callApi('/api/v1/searxng/status'); setSearxngStatus(d) } catch { }
  }, [callApi])

  useEffect(() => {
    let mounted = true
    const boot = async () => {
      setHealth('checking')
      try {
        await loadHealth()
        const s = await loadSettings()
        if (s?.ollama_base_url && mounted) {
          await loadModels({
            baseUrl: s.ollama_base_url,
            defaultModel: s.default_ollama_model,
            silent: true,
          })
        } else if (mounted) {
          setModels([])
        }
      } catch (e) {
        if (mounted) feedback(`Boot error: ${e.message}`, 'error')
      }
      
      if (mounted) {
        loadChannels()
        loadSearxngStatus()
      }
    }
    boot()
    return () => { mounted = false }
  }, [loadHealth, loadSettings, loadModels, loadChannels, loadSearxngStatus, feedback]) // eslint-disable-line

  useEffect(() => { loadReviewQueue(selectedChannelId).catch(e => feedback(e.message, 'error')) }, [selectedChannelId]) // eslint-disable-line

  const loadSourceDumps = useCallback(async (chId, dateKey) => {
    if (!chId || !dateKey) return
    try { const d = await callApi(`/api/v1/channels/${chId}/source-dumps?date=${dateKey}`); setSourceDumps(d) } catch { }
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
      const payload = {
        ...settings,
        database_url: settings.database_url.trim(),
        ollama_base_url: normalizeUrlInput(settings.ollama_base_url || ''),
        default_ollama_model: settings.default_ollama_model.trim(),
        searxng_url: normalizeUrlInput(settings.searxng_url || ''),
      }
      const savedSettings = await callApi('/api/v1/settings', { method: 'PUT', body: JSON.stringify(payload) })
      setSettings({ ...EMPTY_SETTINGS, ...savedSettings })
      if (savedSettings.ollama_base_url) {
        await loadModels({
          baseUrl: savedSettings.ollama_base_url,
          defaultModel: savedSettings.default_ollama_model,
        })
      } else {
        setModels([])
      }
      await loadSearxngStatus()
      feedback('Settings saved', 'success')
    } catch (e) { feedback(e.message, 'error') }
    finally { setSavingSettings(false) }
  }

  const testDb = async () => {
    setTestingDb(true)
    try {
      if (!settings.database_url.trim()) {
        feedback('Enter a database URL first', 'error')
        return
      }
      const r = await callApi(`/api/v1/settings/test-db?database_url=${encodeURIComponent(settings.database_url)}`)
      feedback(r.message, r.ok ? 'success' : 'error')
    } catch (e) { feedback(e.message, 'error') }
    finally { setTestingDb(false) }
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
          } catch { }
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
    const savedSearxngUrl = normalizeUrlInput(searxngStatus.url || '')
    const currentSearxngUrl = normalizeUrlInput(settings.searxng_url || '')
    if (savedSearxngUrl !== currentSearxngUrl) {
      feedback('Save Settings before changing the SearXNG container state', 'error')
      return
    }

    setTogglingSearxng(true)
    try {
      const path = searxngStatus.running ? '/api/v1/searxng/stop' : '/api/v1/searxng/start'
      const r = await callApi(path, { method: 'POST' })
      feedback(r.message, r.ok ? 'success' : 'error')
      await loadSearxngStatus()
    } catch (e) { 
      feedback(e.message, 'error') 
    } finally {
      setTogglingSearxng(false)
    }
  }

  // Calendar day detail: save status from the day detail modal
  const saveDayDetailStatus = async (newStatus) => {
    if (!dayDetailItem) return
    try {
      await callApi(`/api/v1/review-queue/${dayDetailItem.id}`, {
        method: 'PUT',
        body: JSON.stringify({ status: newStatus })
      })
      await loadReviewQueue(selectedChannelId)
      feedback(`Status updated to ${newStatus}`, 'success')
    } catch (e) { feedback(e.message, 'error') }
  }

  // Calendar day click handler: opens detail modal if content exists, otherwise opens override form
  const handleCalendarDayClick = (dayData) => {
    const existingItem = reviewQueue.find(r => r.date === dayData.date)
    if (existingItem) {
      // Content exists — open day detail modal to view/edit status
      setDayDetailDate(dayData.date)
    } else {
      // No content — open override form to plan
      setOverrideForm({
        date: dayData.date,
        pillar: dayData.pillar || '',
        topic: dayData.topic || '',
        special_instructions: dayData.special_instructions || '',
        mode: dayData.mode || 'pre_generated',
      })
    }
  }

  // ── Render ──────────────────────────────────────────────────────────
  const inputClass = 'w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100'
  const textareaClass = inputClass
  const darkInputClass = 'w-full rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2.5 text-sm text-white outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-900'
  const canRefreshModels = Boolean(normalizeUrlInput(settings.ollama_base_url || ''))
  const refreshModels = () => loadModels({
    baseUrl: settings.ollama_base_url,
    defaultModel: settings.default_ollama_model,
  })
  const savedSearxngUrl = normalizeUrlInput(searxngStatus.url || '')
  const currentSearxngUrl = normalizeUrlInput(settings.searxng_url || '')
  const searxngSettingsDirty = savedSearxngUrl !== currentSearxngUrl
  const canToggleSearxng = Boolean(searxngStatus.controllable) && !searxngSettingsDirty
  const searxngStatusText = !searxngStatus.configured
    ? 'Save a SearXNG URL first.'
    : !searxngStatus.controllable
      ? `Saved URL ${searxngStatus.url} needs an explicit port for Docker control.`
      : searxngStatus.running
        ? `Running at ${searxngStatus.url}`
        : `Stopped. Ready to start at ${searxngStatus.url}`

  return (
    <div className="h-screen overflow-hidden bg-gradient-to-br from-slate-50 via-white to-indigo-50/30 font-sans text-slate-800 antialiased">
      <MobileHeader setMobileOpen={setMobileOpen} activeView={activeView} />

      <div className="flex h-screen gap-0 lg:gap-5 lg:p-4">
        <Sidebar
          activeView={activeView} setActiveView={setActiveView}
          channels={channels} selectedChannelId={selectedChannelId}
          setSelectedChannelId={setSelectedChannelId}
          health={health} modelsCount={models.length}
          isMobileOpen={isMobileOpen} setMobileOpen={setMobileOpen}
        />

        {/* Main content area — full height with overflow scroll */}
        <main className="min-w-0 flex-1 overflow-y-auto space-y-5 px-4 py-5 lg:px-0 lg:py-0">

          {/* ── Toast ───────────────────────────────────────────── */}
          {notice && (
            <div className={`animate-slide-in fixed right-4 top-4 z-[70] rounded-xl px-5 py-3 text-sm font-semibold shadow-lg ${notice.tone === 'error' ? 'bg-rose-600 text-white' :
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
            <div className="space-y-5 animate-fade-in pb-6">
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

              {/* Explain Override Template Pillar */}
              <Panel title="How It Works" subtitle="Understanding weekly templates, overrides, and modes">
                <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
                  <div className="rounded-xl bg-indigo-50/50 border border-indigo-100 p-4">
                    <p className="font-bold text-indigo-800 text-xs uppercase tracking-wider mb-1.5">Weekly Template</p>
                    <p>The <strong>Weekly Template</strong> sets a default <strong>content pillar</strong> (topic category) for each day of the week — e.g. "Concept Deep Dive" on Mondays, "Tool Spotlight" on Tuesdays. This automates topic selection when generating a full week.</p>
                  </div>
                  <div className="rounded-xl bg-violet-50/50 border border-violet-100 p-4">
                    <p className="font-bold text-violet-800 text-xs uppercase tracking-wider mb-1.5">Override (Per-Date)</p>
                    <p>An <strong>Override</strong> lets you change the pillar, topic, or special instructions for a <strong>specific date</strong>. This takes priority over the weekly template. Click any calendar day to set an override.</p>
                  </div>
                  <div className="rounded-xl bg-blue-50/50 border border-blue-100 p-4">
                    <p className="font-bold text-blue-800 text-xs uppercase tracking-wider mb-1.5">Generation Modes</p>
                    <p><strong>Pre-Generated</strong>: The AI researches via SearXNG, then writes. <strong>Source Dump</strong>: You provide URLs/text manually, the AI skips research and uses your sources directly.</p>
                  </div>
                </div>
              </Panel>

              {/* Today's ready posts */}
              {reviewQueue.filter(r => r.status === 'ready').length > 0 && (
                <Panel title="Ready to Publish" subtitle="These posts are approved and ready for copy-paste.">
                  <div className="space-y-3 max-h-64 overflow-y-auto">
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
            <div className="space-y-5 animate-fade-in pb-6">
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
                <Field label="Sources" help="One URL or search query per line." className="mt-4"><textarea className={textareaClass} rows={4} value={channelForm.sources_text} onChange={e => setChannelForm(p => ({ ...p, sources_text: e.target.value }))} placeholder={"https://techcrunch.com\nAI news this week\n..."} /></Field>
                <Field label="Prompt Template" className="mt-4"><textarea className={textareaClass} rows={4} value={channelForm.prompt_template} onChange={e => setChannelForm(p => ({ ...p, prompt_template: e.target.value }))} placeholder="Custom instructions for content generation..." /></Field>
                <div className="mt-5"><PrimaryButton onClick={createChannel} loading={creatingChannel}>Create Channel</PrimaryButton></div>
              </Panel>

              {/* Existing channels */}
              {loadingChannels ? <SkeletonCard /> : channels.length > 0 && (
                <Panel title="Your Channels" subtitle="Select a channel to plan content.">
                  <div className="space-y-3 max-h-96 overflow-y-auto">
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
            <div className="space-y-5 animate-fade-in pb-6">
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
            <div className="space-y-5 animate-fade-in pb-6">
              {!selectedChannel ? (
                <EmptyState text="Select a channel to view its content calendar." icon="▦" />
              ) : (
                <Panel title={`${selectedChannel.name} — Calendar`} subtitle="Click any day to view content or plan.">
                  <ContentCalendar
                    selectedChannel={selectedChannel}
                    weeklyTemplateDraft={weeklyTemplateDraft}
                    reviewQueue={reviewQueue}
                    setOverrideForm={handleCalendarDayClick}
                  />
                </Panel>
              )}
            </div>
          )}

          {/* ═══════════════════════════════════════════════════════
              REVIEW QUEUE VIEW
          ═══════════════════════════════════════════════════════ */}
          {activeView === 'review' && (
            <div className="space-y-5 animate-fade-in pb-6">
              <Panel title="Review Queue" subtitle="Edit, refine with AI, and copy-paste ready content.">
                {loadingReview ? <InlineLoader text="Loading review queue..." /> :
                  reviewQueue.length === 0 ? <EmptyState text="No drafts yet. Generate content to populate the queue." icon="◎" /> : (
                    <div className="space-y-4 max-h-[calc(100vh-200px)] overflow-y-auto pr-1">
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
                            className={`${textareaClass} mt-4 min-h-[200px] max-h-[400px] bg-white resize-y`}
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
            <div className="space-y-5 animate-fade-in pb-6">
              <Panel title="System Settings" subtitle="Configure database, Ollama, and SearXNG from the UI and save them to the backend.">
                <div className="grid gap-4 md:grid-cols-2">
                  <Field label="PostgreSQL URL"><input className={inputClass} value={settings.database_url || ''} onChange={e => setSettings(p => ({ ...p, database_url: e.target.value }))} placeholder="postgresql://user:password@host:5432/dbname" /></Field>
                  <Field label="Ollama Base URL"><input className={inputClass} value={settings.ollama_base_url || ''} onChange={e => setSettings(p => ({ ...p, ollama_base_url: e.target.value }))} placeholder="http://localhost:11434" /></Field>
                  <Field label="Default Model">
                    <select className={inputClass} value={settings.default_ollama_model || ''} onChange={e => setSettings(p => ({ ...p, default_ollama_model: e.target.value }))}>
                      <option value="">Select model</option>
                      {models.map(m => <option key={m} value={m}>{m}</option>)}
                    </select>
                  </Field>
                  <Field label="SearXNG URL"><input className={inputClass} value={settings.searxng_url || ''} onChange={e => setSettings(p => ({ ...p, searxng_url: e.target.value }))} placeholder="http://localhost:8080" /></Field>
                </div>
                <div className="mt-5 flex flex-wrap gap-3">
                  <PrimaryButton onClick={saveSettings} loading={savingSettings}>Save Settings</PrimaryButton>
                  <SecondaryButton onClick={testDb} loading={testingDb}>Test Database</SecondaryButton>
                  <SecondaryButton onClick={refreshModels} loading={loadingModels} disabled={!canRefreshModels}>Refresh Models</SecondaryButton>
                </div>
              </Panel>

              {/* Models list */}
              <Panel title="Ollama Models" subtitle="Fetched from the saved Ollama Base URL.">
                {loadingModels ? <InlineLoader text="Fetching models..." /> : models.length === 0 ? (
                  <EmptyState text={canRefreshModels ? 'No models found. Check the saved Ollama Base URL and make sure Ollama is reachable.' : 'Save an Ollama Base URL, then refresh models.'} icon="⬡" />
                ) : (
                  <div className="space-y-2 max-h-64 overflow-y-auto">
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
              <Panel title="SearXNG Engine" subtitle="Uses the saved SearXNG URL to control the local Docker container.">
                <div className="flex items-center justify-between rounded-xl border border-slate-100 bg-slate-50 px-5 py-4">
                  <div>
                    <p className="text-sm font-semibold text-slate-900">Container Status</p>
                    <p className="mt-0.5 text-xs text-slate-500">
                      {searxngStatusText}
                    </p>
                    {searxngSettingsDirty && (
                      <p className="mt-1 text-xs text-amber-600">Save Settings to apply the edited SearXNG URL before starting or stopping the container.</p>
                    )}
                  </div>
                  {searxngStatus.running ? (
                    <DangerButton onClick={toggleSearxng} loading={togglingSearxng} disabled={!canToggleSearxng}>Stop SearXNG</DangerButton>
                  ) : (
                    <PrimaryButton onClick={toggleSearxng} loading={togglingSearxng} disabled={!canToggleSearxng}>Start SearXNG</PrimaryButton>
                  )}
                </div>
              </Panel>
            </div>
          )}
        </main>
      </div>

      {/* ── Override Modal (for planning a new day) ──────────────── */}
      <Modal
        isOpen={!!overrideForm.date}
        onClose={() => setOverrideForm(p => ({ ...p, date: '' }))}
        title={`Plan Day: ${overrideForm.date}`}
        wide
      >
        <div className="space-y-5">
          <div className="rounded-xl bg-slate-50 border border-slate-100 p-4">
            <p className="text-xs text-slate-500"><strong>Override Template Pillar</strong> lets you replace the default weekly template pillar with a custom one for this specific date. Leave blank to use the weekly template default.</p>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="Content Pillar" help="Leave blank to use weekly template default"><input className={inputClass} value={overrideForm.pillar} onChange={e => setOverrideForm(p => ({ ...p, pillar: e.target.value }))} placeholder="Override template pillar" /></Field>
            <Field label="Topic"><input className={inputClass} value={overrideForm.topic} onChange={e => setOverrideForm(p => ({ ...p, topic: e.target.value }))} placeholder="Specific subject for this day" /></Field>
            <Field label="Special Instructions"><input className={inputClass} value={overrideForm.special_instructions} onChange={e => setOverrideForm(p => ({ ...p, special_instructions: e.target.value }))} placeholder="e.g. Keep under 300 words" /></Field>
            <Field label="Generation Mode">
              <select className={inputClass} value={overrideForm.mode} onChange={e => setOverrideForm(p => ({ ...p, mode: e.target.value }))}>
                <option value="pre_generated">Pre-Generated (AI researches + writes)</option>
                <option value="source_dump">Source Dump (You provide sources)</option>
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

      {/* ── Day Detail Modal (view/edit content + status from calendar) ── */}
      <Modal
        isOpen={!!dayDetailDate}
        onClose={() => setDayDetailDate('')}
        title={`Day: ${dayDetailDate}`}
        wide
      >
        {dayDetailItem ? (
          <div className="space-y-5">
            {/* Status and meta */}
            <div className="flex flex-wrap items-center gap-3">
              <span className="rounded-lg bg-white px-3 py-1.5 text-xs font-bold text-slate-600 border border-slate-100">{dayDetailItem.pillar}</span>
              <span className={`rounded-lg px-3 py-1.5 text-xs font-bold ${dayDetailItem.status === 'ready' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>{dayDetailItem.status}</span>
              <span className="text-xs text-slate-500">Topic: {dayDetailItem.topic}</span>
            </div>

            {/* Status toggle */}
            <div className="flex items-center gap-3">
              <Field label="Set Status">
                <div className="flex gap-2">
                  <SecondaryButton
                    onClick={() => saveDayDetailStatus('draft')}
                    className={dayDetailItem.status === 'draft' ? '!border-amber-400 !bg-amber-50' : ''}
                  >
                    📝 Draft
                  </SecondaryButton>
                  <PrimaryButton
                    onClick={() => saveDayDetailStatus('ready')}
                    className={dayDetailItem.status === 'ready' ? '!from-emerald-600 !to-green-600' : ''}
                  >
                    ✅ Ready
                  </PrimaryButton>
                </div>
              </Field>
            </div>

            {/* Content viewer */}
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Generated Content</p>
              <div className="max-h-[50vh] overflow-y-auto rounded-xl border border-slate-200 bg-white p-4">
                <pre className="whitespace-pre-wrap text-sm text-slate-800 font-sans leading-relaxed">{dayDetailItem.content}</pre>
              </div>
            </div>

            {/* Actions */}
            <div className="flex flex-wrap gap-3">
              <PrimaryButton onClick={() => copyContent(dayDetailItem.content)}>Copy Content</PrimaryButton>
              <SecondaryButton onClick={() => { setDayDetailDate(''); setActiveView('review') }}>Open in Review Queue</SecondaryButton>
              <SecondaryButton onClick={() => {
                setDayDetailDate('')
                setOverrideForm({
                  date: dayDetailDate,
                  pillar: '',
                  topic: '',
                  special_instructions: '',
                  mode: 'pre_generated',
                })
              }}>Re-Plan This Day</SecondaryButton>
            </div>
          </div>
        ) : (
          <div className="py-8 text-center">
            <p className="text-sm text-slate-500">No content generated for this date yet.</p>
            <div className="mt-4">
              <PrimaryButton onClick={() => {
                setDayDetailDate('')
                setOverrideForm({
                  date: dayDetailDate,
                  pillar: '',
                  topic: '',
                  special_instructions: '',
                  mode: 'pre_generated',
                })
              }}>Plan This Day</PrimaryButton>
            </div>
          </div>
        )}
      </Modal>

      {/* ── Loading overlay ─────────────────────────────────────── */}
      <LoadingOverlay active={generatingDay} message="Generating content…" logs={agentLogs} />
    </div>
  )
}

export default App
