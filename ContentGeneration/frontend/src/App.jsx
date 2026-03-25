import { useEffect, useMemo, useState, useCallback } from 'react'
import { Modal } from './components/Modal'
import { PrimaryButton, SecondaryButton, DangerButton } from './components/Buttons'
import { Field, EmptyState } from './components/Field'
import { MetricCard, Panel } from './components/MetricCard'
import { SourceInbox } from './components/SourceInbox'
import { ContentCalendar } from './components/ContentCalendar'
import { SkeletonCard, InlineLoader } from './components/Loading'
import { AgentProgress } from './components/AgentProgress'
import { Sidebar, MobileHeader } from './components/Sidebar'
import { FormattedPreview } from './components/FormattedPreview'

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
  searxng_categories: 'general',
  searxng_max_results: 4,
  searxng_time_range: 'any',
  gemini_api_key: '',
}

const normalizeUrlInput = (value) => value.trim().replace(/\/+$/, '')

const THEMES = {
  indigo: {
    label: 'Indigo (Default)',
    brand: {
      50: '#eef2ff',
      100: '#e0e7ff',
      200: '#c7d2fe',
      300: '#a5b4fc',
      400: '#818cf8',
      500: '#6366f1',
      600: '#4f46e5',
      700: '#4338ca',
      800: '#3730a3',
      900: '#312e81',
    },
  },
  sky: {
    label: 'Sky',
    brand: {
      50: '#f0f9ff',
      100: '#e0f2fe',
      200: '#bae6fd',
      300: '#7dd3fc',
      400: '#38bdf8',
      500: '#0ea5e9',
      600: '#0284c7',
      700: '#0369a1',
      800: '#075985',
      900: '#0c4a6e',
    },
  },
  emerald: {
    label: 'Emerald',
    brand: {
      50: '#ecfdf5',
      100: '#d1fae5',
      200: '#a7f3d0',
      300: '#6ee7b7',
      400: '#34d399',
      500: '#10b981',
      600: '#059669',
      700: '#047857',
      800: '#065f46',
      900: '#064e3b',
    },
  },
  teal: {
    label: 'Teal',
    brand: {
      50: '#f0fdfa',
      100: '#ccfbf1',
      200: '#99f6e4',
      300: '#5eead4',
      400: '#2dd4bf',
      500: '#14b8a6',
      600: '#0d9488',
      700: '#0f766e',
      800: '#115e59',
      900: '#134e4a',
    },
  },
  violet: {
    label: 'Violet',
    brand: {
      50: '#f5f3ff',
      100: '#ede9fe',
      200: '#ddd6fe',
      300: '#c4b5fd',
      400: '#a78bfa',
      500: '#8b5cf6',
      600: '#7c3aed',
      700: '#6d28d9',
      800: '#5b21b6',
      900: '#4c1d95',
    },
  },
  rose: {
    label: 'Rose',
    brand: {
      50: '#fff1f2',
      100: '#ffe4e6',
      200: '#fecdd3',
      300: '#fda4af',
      400: '#fb7185',
      500: '#f43f5e',
      600: '#e11d48',
      700: '#be123c',
      800: '#9f1239',
      900: '#881337',
    },
  },
  amber: {
    label: 'Amber',
    brand: {
      50: '#fffbeb',
      100: '#fef3c7',
      200: '#fde68a',
      300: '#fcd34d',
      400: '#fbbf24',
      500: '#f59e0b',
      600: '#d97706',
      700: '#b45309',
      800: '#92400e',
      900: '#78350f',
    },
  },
  lime: {
    label: 'Lime',
    brand: {
      50: '#f7fee7',
      100: '#ecfccb',
      200: '#d9f99d',
      300: '#bef264',
      400: '#a3e635',
      500: '#84cc16',
      600: '#65a30d',
      700: '#4d7c0f',
      800: '#3f6212',
      900: '#365314',
    },
  },
  slate: {
    label: 'Slate',
    brand: {
      50: '#f8fafc',
      100: '#f1f5f9',
      200: '#e2e8f0',
      300: '#cbd5e1',
      400: '#94a3b8',
      500: '#64748b',
      600: '#475569',
      700: '#334155',
      800: '#1f2937',
      900: '#0f172a',
    },
  },
}

function applyTheme(themeKey) {
  const theme = THEMES[themeKey] || THEMES.indigo
  const root = document.documentElement
  Object.entries(theme.brand || {}).forEach(([scale, value]) => {
    root.style.setProperty(`--color-brand-${scale}`, String(value))
  })
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

  // Theme selection (frontend-only)
  const [themeKey, setThemeKey] = useState(() => localStorage.getItem('contentpilot_theme') || 'indigo')

  useEffect(() => {
    localStorage.setItem('contentpilot_theme', themeKey)
    applyTheme(themeKey)
  }, [themeKey])

  const [channelForm, setChannelForm] = useState(CHANNEL_INIT)
  const [weeklyTemplateDraft, setWeeklyTemplateDraft] = useState({ ...DEFAULT_TEMPLATE })
  const [overrideForm, setOverrideForm] = useState({ date: '', pillar: '', topic: '', special_instructions: '', mode: 'pre_generated', search_additional: true, suggest_new_topic: false })
  const [sourceDumps, setSourceDumps] = useState([])
  const [newSourceDump, setNewSourceDump] = useState({ type: 'url', label: '', raw_content: '' })

  // Channel editing
  const [editingChannel, setEditingChannel] = useState(null)

  // Memory
  const [channelMemories, setChannelMemories] = useState([])
  const [newContextNote, setNewContextNote] = useState('')

  // Source dump counts for calendar
  const [sourceDumpCounts, setSourceDumpCounts] = useState({})
  const [isMobileOpen, setMobileOpen] = useState(false)
  const [servicesStatus, setServicesStatus] = useState({
    running: false,
    docker_running: false,
    searxng_url: '',
    postgres: { running: false, status: 'missing' },
    searxng: { running: false, status: 'missing', url: '' },
  })

  // Loading states
  const [generating, setGenerating] = useState(false)
  const [loadingChannels, setLoadingChannels] = useState(true)
  const [loadingModels, setLoadingModels] = useState(true)
  const [loadingReview, setLoadingReview] = useState(false)
  const [savingSettings, setSavingSettings] = useState(false)
  const [creatingChannel, setCreatingChannel] = useState(false)
  const [agentLogs, setAgentLogs] = useState([])
  const [togglingServices, setTogglingServices] = useState(false)
  const [testingDb, setTestingDb] = useState(false)
  const [refiningId, setRefiningId] = useState(null)
  const [generatingDay, setGeneratingDay] = useState(false)
  const [reviewImages, setReviewImages] = useState({})
  const [generatingImageId, setGeneratingImageId] = useState(null)

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

  const loadServicesStatus = useCallback(async () => {
    try { const d = await callApi('/api/v1/services/status'); setServicesStatus(d) } catch { }
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
        loadServicesStatus()
      }
    }
    boot()
    return () => { mounted = false }
  }, [loadHealth, loadSettings, loadModels, loadChannels, loadServicesStatus, feedback]) // eslint-disable-line

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
        gemini_api_key: settings.gemini_api_key === 'configured' ? undefined : settings.gemini_api_key,
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
      await loadServicesStatus()
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

  const openEditChannel = (ch) => {
    setEditingChannel({
      id: ch.id,
      name: ch.name,
      description: ch.description || '',
      audience: ch.audience || '',
      tone: ch.tone || 'Educational',
      platform: ch.platform || 'whatsapp',
      language: ch.language || 'en',
      timezone: ch.timezone || 'UTC',
      sources_text: (ch.sources || []).join('\n'),
      prompt_template: ch.prompt_template || '',
      context_notes: ch.context_notes || '',
    })
  }

  const saveEditChannel = async () => {
    if (!editingChannel) return
    try {
      const payload = {
        ...editingChannel,
        sources: editingChannel.sources_text.split('\n').map(l => l.trim()).filter(Boolean),
      }
      delete payload.sources_text
      delete payload.id
      await callApi(`/api/v1/channels/${editingChannel.id}`, { method: 'PUT', body: JSON.stringify(payload) })
      await loadChannels()
      setEditingChannel(null)
      feedback('Channel updated', 'success')
    } catch (e) { feedback(e.message, 'error') }
  }

  // ── Memory ──────────────────────────────────────────────────────
  const loadMemories = useCallback(async (chId) => {
    if (!chId) return
    try { const d = await callApi(`/api/v1/channels/${chId}/memory`); setChannelMemories(d) } catch { }
  }, [callApi])

  const addContextNote = async () => {
    if (!selectedChannelId || !newContextNote.trim()) return
    try {
      await callApi(`/api/v1/channels/${selectedChannelId}/memory`, {
        method: 'POST',
        body: JSON.stringify({ type: 'contextual', content: newContextNote.trim() }),
      })
      setNewContextNote('')
      await loadMemories(selectedChannelId)
      feedback('Context note added', 'success')
    } catch (e) { feedback(e.message, 'error') }
  }

  const deleteMemory = async (memId) => {
    if (!selectedChannelId) return
    try {
      await callApi(`/api/v1/channels/${selectedChannelId}/memory/${memId}`, { method: 'DELETE' })
      await loadMemories(selectedChannelId)
      feedback('Memory removed', 'success')
    } catch (e) { feedback(e.message, 'error') }
  }

  // Load memories when channel changes
  useEffect(() => { if (selectedChannelId) loadMemories(selectedChannelId) }, [selectedChannelId]) // eslint-disable-line

  // Load source dump counts for calendar
  const loadSourceDumpCounts = useCallback(async (chId) => {
    if (!chId) return
    try { const d = await callApi(`/api/v1/channels/${chId}/source-dump-counts`); setSourceDumpCounts(d) } catch { }
  }, [callApi])

  useEffect(() => { if (selectedChannelId) loadSourceDumpCounts(selectedChannelId) }, [selectedChannelId]) // eslint-disable-line

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
      setNewSourceDump({ type: 'url', label: '', raw_content: '' })
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

  const connectGenerationStream = useCallback((runId, { onComplete, onDisconnect }) => {
    const es = new EventSource(`${api}/api/v1/generation/stream/${runId}`)
    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        setAgentLogs(prev => [...prev, data])
        if (data.status === 'done' && data.step === 'pipeline') {
          es.close()
          onComplete?.(data)
        }
      } catch { }
    }
    es.onerror = () => {
      es.close()
      onDisconnect?.()
    }
    return es
  }, [api])

  const generateDay = async () => {
    if (!selectedChannelId || !overrideForm.date) return
    if (overrideForm.mode === 'source_dump' && sourceDumps.length === 0) {
      return feedback('Add at least one dumped source before generating this roundup', 'error')
    }
    setGeneratingDay(true); setAgentLogs([])
    try {
      const targetDate = overrideForm.date
      await callApi(`/api/v1/channels/${selectedChannelId}/overrides`, {
        method: 'POST',
        body: JSON.stringify(overrideForm),
      })
      const result = await callApi(`/api/v1/channels/${selectedChannelId}/generate-day`, {
        method: 'POST',
        body: JSON.stringify({
          date: targetDate,
          model: generateModel || settings.default_ollama_model,
          search_additional: overrideForm.search_additional !== false,
          suggest_new_topic: overrideForm.suggest_new_topic === true,
        }),
      })

      if (result.run_id) {
        connectGenerationStream(result.run_id, {
          onComplete: async () => {
            setGeneratingDay(false)
            await loadChannels()
            await loadReviewQueue(selectedChannelId)
            await loadSourceDumpCounts(selectedChannelId)
            setOverrideForm(p => ({ ...p, date: '' }))
            setActiveView('review')
            feedback(`Content generated for ${targetDate}`, 'success')
          },
          onDisconnect: () => {
            setGeneratingDay(false)
            feedback('Generation stream disconnected', 'error')
          },
        })
      } else {
        setGeneratingDay(false)
      }
    } catch (e) {
      setGeneratingDay(false)
      feedback(e.message, 'error')
    }
  }

  const generateWeek = async () => {
    if (!selectedChannelId) return feedback('Select a channel first', 'error')
    setGenerating(true); setAgentLogs([])
    try {
      const result = await callApi(`/api/v1/channels/${selectedChannelId}/generate-week`, { method: 'POST', body: JSON.stringify({ start_date: generateStartDate, model: generateModel || settings.default_ollama_model }) })

      if (result.run_id) {
        connectGenerationStream(result.run_id, {
          onComplete: async () => {
            setGenerating(false)
            await loadChannels()
            await loadReviewQueue(selectedChannelId)
            setActiveView('review')
            feedback('Week generation complete', 'success')
          },
          onDisconnect: () => {
            setGenerating(false)
            feedback('Generation stream disconnected', 'error')
          },
        })
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

  const loadReviewImage = useCallback(async (itemId) => {
    try {
      const data = await callApi(`/api/v1/review-queue/${itemId}/image`)
      setReviewImages(prev => ({ ...prev, [itemId]: data }))
    } catch {
      setReviewImages(prev => {
        const next = { ...prev }
        delete next[itemId]
        return next
      })
    }
  }, [callApi])

  useEffect(() => {
    reviewQueue.forEach(item => {
      loadReviewImage(item.id)
    })
  }, [reviewQueue, loadReviewImage])

  const generateReviewImage = async (itemId) => {
    setGeneratingImageId(itemId)
    try {
      const data = await callApi(`/api/v1/review-queue/${itemId}/generate-image`, { method: 'POST' })
      setReviewImages(prev => ({ ...prev, [itemId]: data }))
      feedback('Image generated', 'success')
    } catch (e) {
      feedback(e.message, 'error')
    } finally {
      setGeneratingImageId(null)
    }
  }

  const copyContent = async (content) => { await navigator.clipboard.writeText(content); feedback('Copied to clipboard', 'success') }

  const toggleServices = async () => {
    const savedSearxngUrl = normalizeUrlInput(servicesStatus.searxng_url || '')
    const currentSearxngUrl = normalizeUrlInput(settings.searxng_url || '')
    if (savedSearxngUrl !== currentSearxngUrl) {
      feedback('Save Settings before changing the Docker service state', 'error')
      return
    }

    setTogglingServices(true)
    try {
      const path = servicesStatus.running ? '/api/v1/services/stop' : '/api/v1/services/start'
      const r = await callApi(path, { method: 'POST' })
      feedback(r.message, r.ok ? 'success' : 'error')
      await loadServicesStatus()
    } catch (e) { 
      feedback(e.message, 'error') 
    } finally {
      setTogglingServices(false)
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
        search_additional: dayData.search_additional !== false,
        suggest_new_topic: dayData.suggest_new_topic === true,
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
  const savedSearxngUrl = normalizeUrlInput(servicesStatus.searxng_url || '')
  const currentSearxngUrl = normalizeUrlInput(settings.searxng_url || '')
  const servicesSettingsDirty = savedSearxngUrl !== currentSearxngUrl
  const canToggleServices = !servicesSettingsDirty
  const servicesStatusText = servicesStatus.running
    ? `Running. Postgres is ${servicesStatus.postgres?.status || 'unknown'} and SearXNG is ${servicesStatus.searxng?.status || 'unknown'}.`
    : `Stopped. Postgres is ${servicesStatus.postgres?.status || 'missing'} and SearXNG is ${servicesStatus.searxng?.status || 'missing'}.`
  const geminiConfigured = Boolean(settings.gemini_api_key)
  const filteredReviewQueue = reviewQueue.filter((item) => {
    const matchesDate = !reviewFilterDate || item.date === reviewFilterDate
    const matchesStatus = reviewFilterStatus === 'all' || item.status === reviewFilterStatus
    return matchesDate && matchesStatus
  })
  // renderFormattedPreview replaced by FormattedPreview component

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
                  label="Infra"
                  value={servicesStatus.running ? 'Online' : 'Offline'}
                  hint={`Postgres: ${servicesStatus.postgres?.status || 'missing'} | SearXNG: ${servicesStatus.searxng?.status || 'missing'}`}
                  icon={servicesStatus.running ? '🟢' : '🔴'}
                />
              </div>

              {/* Quick actions */}
              <Panel title="Quick Actions" subtitle="Jump to common tasks">
                <div className="flex flex-wrap gap-3">
                  <PrimaryButton onClick={() => setActiveView('channels')}>+ New Channel</PrimaryButton>
                  <SecondaryButton onClick={() => setActiveView('calendar')}>View Calendar</SecondaryButton>
                  <SecondaryButton onClick={() => setActiveView('review')}>Review Queue ({reviewQueue.length})</SecondaryButton>
                  <SecondaryButton onClick={toggleServices}>
                    {servicesStatus.running ? '⏹ Stop Services' : '▶ Start Services'}
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
                          <SecondaryButton onClick={(e) => { e.stopPropagation(); openEditChannel(ch) }} className="!py-1 !px-2.5 !text-[11px]">Edit</SecondaryButton>
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
                    <AgentProgress logs={agentLogs} isRunning={generating} onClose={() => setAgentLogs([])} />
                  )}

                  {/* Channel Memory */}
                  <Panel title="Channel Memory" subtitle="Persistent context notes and learned preferences injected into every generation.">
                    <div className="space-y-4">
                      {/* Add context note */}
                      <div className="flex flex-col gap-2 sm:flex-row">
                        <input
                          className={`${inputClass} flex-1`}
                          placeholder="Add a persistent context note (e.g., 'Always mention our focus on privacy')..."
                          value={newContextNote}
                          onChange={e => setNewContextNote(e.target.value)}
                          onKeyDown={e => { if (e.key === 'Enter') addContextNote() }}
                        />
                        <PrimaryButton onClick={addContextNote}>Add Note</PrimaryButton>
                      </div>

                      {/* Memory list */}
                      {channelMemories.length === 0 ? (
                        <EmptyState text="No memories yet. Context notes you add will be injected into every generation. Approved posts and refinements are auto-remembered." icon="🧠" />
                      ) : (
                        <div className="space-y-2 max-h-72 overflow-y-auto">
                          {channelMemories.map(mem => (
                            <div key={mem.id} className={`flex items-start justify-between rounded-xl border px-4 py-3 ${
                              mem.type === 'contextual' ? 'border-indigo-100 bg-indigo-50/50'
                              : mem.type === 'episodic' ? 'border-emerald-100 bg-emerald-50/50'
                              : 'border-amber-100 bg-amber-50/50'
                            }`}>
                              <div className="min-w-0 flex-1">
                                <div className="flex items-center gap-2 mb-1">
                                  <span className={`rounded-md px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                                    mem.type === 'contextual' ? 'bg-indigo-100 text-indigo-700'
                                    : mem.type === 'episodic' ? 'bg-emerald-100 text-emerald-700'
                                    : 'bg-amber-100 text-amber-700'
                                  }`}>{mem.type}</span>
                                  <span className="text-[10px] text-slate-400">{new Date(mem.created_at).toLocaleDateString()}</span>
                                </div>
                                <p className="text-sm text-slate-700 truncate">{mem.content}</p>
                              </div>
                              <DangerButton onClick={() => deleteMemory(mem.id)} className="!py-1 !px-2 !text-[10px] ml-2 shrink-0">×</DangerButton>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </Panel>
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
                    sourceDumpCounts={sourceDumpCounts}
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
              {(generating || generatingDay || agentLogs.length > 0) && (
                <AgentProgress logs={agentLogs} isRunning={generating || generatingDay} onClose={() => setAgentLogs([])} />
              )}
              <Panel title="Review Queue" subtitle="Edit, refine with AI, and copy-paste ready content.">
                <div className="mb-5 flex flex-wrap items-end gap-3 rounded-2xl border border-slate-100 bg-slate-50/70 p-4">
                  <Field label="Filter by Date">
                    <input className={inputClass} type="date" value={reviewFilterDate} onChange={e => setReviewFilterDate(e.target.value)} />
                  </Field>
                  <Field label="Filter by Status">
                    <select className={inputClass} value={reviewFilterStatus} onChange={e => setReviewFilterStatus(e.target.value)}>
                      <option value="all">All statuses</option>
                      <option value="draft">Draft</option>
                      <option value="ready">Ready</option>
                    </select>
                  </Field>
                  <SecondaryButton onClick={() => { setReviewFilterDate(''); setReviewFilterStatus('all') }}>Clear Filters</SecondaryButton>
                </div>

                {loadingReview ? <InlineLoader text="Loading review queue..." /> :
                  reviewQueue.length === 0 ? <EmptyState text="No drafts yet. Generate content to populate the queue." icon="◎" /> :
                    filteredReviewQueue.length === 0 ? <EmptyState text="No drafts match the current filters." icon="◌" /> : (
                      <div className="space-y-4 max-h-[calc(100vh-240px)] overflow-y-auto pr-1">
                        {filteredReviewQueue.map(item => (
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

                            <div className="mt-4 grid gap-4 xl:grid-cols-2">
                              <div className="rounded-xl border border-slate-100 bg-white p-4">
                                <p className="mb-3 text-xs font-bold uppercase tracking-wider text-slate-500">Formatted Preview</p>
                                <div className="max-h-[420px] overflow-y-auto"><FormattedPreview content={item.content} platform={item.platform || selectedChannel?.platform || 'whatsapp'} /></div>
                              </div>

                              <div className="space-y-4 rounded-xl border border-slate-100 bg-white p-4">
                                <div>
                                  <p className="mb-3 text-xs font-bold uppercase tracking-wider text-slate-500">Editable Content</p>
                                  <textarea
                                    className={`${textareaClass} min-h-[220px] max-h-[420px] bg-white resize-y`}
                                    value={item.content}
                                    onChange={e => setReviewQueue(p => p.map(r => r.id === item.id ? { ...r, content: e.target.value } : r))}
                                  />
                                </div>

                                <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-4">
                                  <p className="mb-3 text-xs font-bold uppercase tracking-wider text-slate-500">Refinement Chat</p>
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
                                    <div className="mt-3 space-y-1.5 max-h-32 overflow-y-auto rounded-lg bg-white p-3">
                                      {item.chat_history.map((entry, i) => (
                                        <div key={i} className="flex items-start gap-2 text-xs">
                                          <span className="shrink-0 text-indigo-500 font-bold">→</span>
                                          <span className="text-slate-600">{entry.instruction}</span>
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                </div>

                                <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-4">
                                  <div className="flex flex-wrap items-center justify-between gap-3">
                                    <div>
                                      <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Post Image</p>
                                      <p className="mt-1 text-xs text-slate-500">Generate an optional Gemini image based on this post.</p>
                                    </div>
                                    <div className="flex flex-wrap gap-2">
                                      <PrimaryButton onClick={() => generateReviewImage(item.id)} loading={generatingImageId === item.id} disabled={!geminiConfigured}>
                                        Generate Image
                                      </PrimaryButton>
                                      {reviewImages[item.id]?.download_url && (
                                        <a href={`${api}${reviewImages[item.id].download_url}`} target="_blank" rel="noreferrer" className="inline-flex items-center justify-center rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-300 hover:bg-slate-50">
                                          Download Image
                                        </a>
                                      )}
                                    </div>
                                  </div>
                                  {!geminiConfigured && (
                                    <p className="mt-3 text-xs text-amber-600">Save a Gemini API key in Settings to enable image generation.</p>
                                  )}
                                  {reviewImages[item.id]?.download_url && (
                                    <div className="mt-4 overflow-hidden rounded-xl border border-slate-100 bg-white p-3">
                                      <img src={`${api}${reviewImages[item.id].download_url}`} alt={`Generated illustration for ${item.topic}`} className="w-full rounded-lg object-cover" />
                                    </div>
                                  )}
                                </div>
                              </div>
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
              <Panel title="Theme" subtitle="Pick an accent palette for buttons and brand highlights.">
                <div className="flex flex-wrap items-center gap-3">
                  <Field label="Accent Theme">
                    <select
                      className={inputClass}
                      value={themeKey}
                      onChange={e => setThemeKey(e.target.value)}
                    >
                      {Object.entries(THEMES).map(([key, t]) => (
                        <option key={key} value={key}>{t.label}</option>
                      ))}
                    </select>
                  </Field>

                  <div className="flex items-end gap-2 pb-1">
                    <span className="text-xs font-semibold text-slate-600">Preview:</span>
                    <span className="inline-flex h-6 w-6 rounded-lg bg-brand-600 shadow-sm border border-black/5" title="brand-600" />
                    <span className="inline-flex h-6 w-6 rounded-lg bg-brand-700 shadow-sm border border-black/5" title="brand-700" />
                    <span className="inline-flex h-6 w-6 rounded-lg bg-brand-200 shadow-sm border border-black/5" title="brand-200" />
                  </div>
                </div>
              </Panel>

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
                  <Field label="Gemini API Key" help="Optional. Needed only for post image generation.">
                    <input className={inputClass} type="password" value={settings.gemini_api_key || ''} onChange={e => setSettings(p => ({ ...p, gemini_api_key: e.target.value }))} placeholder="AIza..." />
                  </Field>
                </div>
                <div className="mt-4">
                  <p className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">SearXNG Search Preferences</p>
                  <div className="grid gap-4 md:grid-cols-3">
                    <Field label="Search Categories" help="Comma-separated: general, news, science, it">
                      <input className={inputClass} value={settings.searxng_categories || 'general'} onChange={e => setSettings(p => ({ ...p, searxng_categories: e.target.value }))} placeholder="general, news" />
                    </Field>
                    <Field label="Max Results">
                      <input className={inputClass} type="number" min={1} max={20} value={settings.searxng_max_results || 4} onChange={e => setSettings(p => ({ ...p, searxng_max_results: parseInt(e.target.value) || 4 }))} />
                    </Field>
                    <Field label="Time Range">
                      <select className={inputClass} value={settings.searxng_time_range || 'any'} onChange={e => setSettings(p => ({ ...p, searxng_time_range: e.target.value }))}>
                        <option value="any">Any time</option>
                        <option value="day">Past day</option>
                        <option value="week">Past week</option>
                        <option value="month">Past month</option>
                        <option value="year">Past year</option>
                      </select>
                    </Field>
                  </div>
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

              {/* Infra control */}
              <Panel title="Docker Services" subtitle="Starts or stops the local Postgres and SearXNG infrastructure together.">
                <div className="flex items-center justify-between rounded-xl border border-slate-100 bg-slate-50 px-5 py-4">
                  <div>
                    <p className="text-sm font-semibold text-slate-900">Infrastructure Status</p>
                    <p className="mt-0.5 text-xs text-slate-500">
                      {servicesStatusText}
                    </p>
                    {servicesSettingsDirty && (
                      <p className="mt-1 text-xs text-amber-600">Save Settings to apply the edited SearXNG URL before starting or stopping services.</p>
                    )}
                  </div>
                  {servicesStatus.running ? (
                    <DangerButton onClick={toggleServices} loading={togglingServices} disabled={!canToggleServices}>Stop Services</DangerButton>
                  ) : (
                    <PrimaryButton onClick={toggleServices} loading={togglingServices} disabled={!canToggleServices}>Start Services</PrimaryButton>
                  )}
                </div>
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  <div className="rounded-xl border border-slate-100 bg-white px-4 py-3 text-sm text-slate-600">
                    <strong className="text-slate-900">Postgres</strong>: {servicesStatus.postgres?.status || 'missing'}
                  </div>
                  <div className="rounded-xl border border-slate-100 bg-white px-4 py-3 text-sm text-slate-600">
                    <strong className="text-slate-900">SearXNG</strong>: {servicesStatus.searxng?.status || 'missing'}
                  </div>
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
            <p className="text-xs text-slate-500"><strong>Content Pillar</strong> lets you replace the weekly template pillar for this specific date. Leave it blank to keep the default for that day.</p>
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <button
              type="button"
              onClick={() => setOverrideForm(p => ({ ...p, mode: 'pre_generated' }))}
              className={`rounded-2xl border p-4 text-left transition ${overrideForm.mode === 'pre_generated' ? 'border-indigo-400 bg-indigo-50 shadow-sm' : 'border-slate-200 bg-white hover:border-slate-300'}`}
            >
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-indigo-500">Daily Research Generation</p>
              <h4 className="mt-2 text-base font-bold text-slate-900">Topic + your sources + SearXNG</h4>
              <p className="mt-2 text-sm text-slate-600">Use this for a normal day. You can add links or text below, and the pipeline will scrape those sources, search for more sources with SearXNG, then run RAG before writing the final post.</p>
              {overrideForm.mode === 'pre_generated' && (
                <label className="mt-3 flex items-center gap-2 cursor-pointer" onClick={e => e.stopPropagation()}>
                  <input
                    type="checkbox"
                    checked={overrideForm.search_additional !== false}
                    onChange={e => setOverrideForm(p => ({ ...p, search_additional: e.target.checked }))}
                    className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  <span className="text-xs text-slate-600">Search SearXNG for additional sources</span>
                </label>
              )}
            </button>
            <button
              type="button"
              onClick={() => setOverrideForm(p => ({ ...p, mode: 'source_dump' }))}
              className={`rounded-2xl border p-4 text-left transition ${overrideForm.mode === 'source_dump' ? 'border-amber-400 bg-amber-50 shadow-sm' : 'border-slate-200 bg-white hover:border-slate-300'}`}
            >
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-amber-500">Source Dump / Roundup</p>
              <h4 className="mt-2 text-base font-bold text-slate-900">Curated weekly or special-source summary</h4>
              <p className="mt-2 text-sm text-slate-600">Use this when you want to keep dumping links, notes, or text into one date bucket, like a Sunday AI news recap. Generation will use the dumped sources and run RAG across the full collection.</p>
            </button>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="Content Pillar" help="Leave blank to use weekly template default"><input className={inputClass} value={overrideForm.pillar} onChange={e => setOverrideForm(p => ({ ...p, pillar: e.target.value }))} placeholder="Override template pillar" /></Field>
            <Field label="Topic"><input className={inputClass} value={overrideForm.topic} onChange={e => setOverrideForm(p => ({ ...p, topic: e.target.value }))} placeholder={overrideForm.mode === 'source_dump' ? 'e.g. Weekly AI news summary' : 'Specific subject for this day'} /></Field>
            <Field label="Special Instructions"><input className={inputClass} value={overrideForm.special_instructions} onChange={e => setOverrideForm(p => ({ ...p, special_instructions: e.target.value }))} placeholder="e.g. Keep under 300 words" /></Field>
            <div className="rounded-xl border border-slate-100 bg-white p-4">
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={overrideForm.suggest_new_topic === true}
                  onChange={e => setOverrideForm(p => ({ ...p, suggest_new_topic: e.target.checked }))}
                  className="mt-0.5 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                />
                <div>
                  <p className="text-sm font-semibold text-slate-900">Suggest new topic</p>
                  <p className="mt-1 text-xs text-slate-500">Use channel memory and live search to avoid repeating older themes for this pillar.</p>
                </div>
              </label>
            </div>
            <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-4">
              <p className="text-xs font-bold uppercase tracking-wider text-slate-500">How This Run Works</p>
              <p className="mt-2 text-sm text-slate-600">
                {overrideForm.mode === 'source_dump'
                  ? 'This date acts like a source bucket. Keep adding links, notes, or raw text here. When you generate, the app will fetch the dumped sources and run RAG over the combined material.'
                  : 'This run starts with your topic, adds any links or text you provide below, searches SearXNG for extra coverage, scrapes the discovered URLs, and then runs RAG before content generation.'}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <SecondaryButton onClick={async () => { await saveOverride(); setOverrideForm(p => ({ ...p, date: '' })) }}>Save Plan</SecondaryButton>
            <PrimaryButton onClick={generateDay} loading={generatingDay}>{overrideForm.mode === 'source_dump' ? 'Generate From Dump' : 'Generate This Day'}</PrimaryButton>
          </div>

          <SourceInbox
            title={overrideForm.mode === 'source_dump' ? 'Roundup Source Dump' : 'Optional Seed Sources'}
            description={overrideForm.mode === 'source_dump'
              ? 'Add links, notes, or pasted text to build up this roundup over time. When you generate, the dumped sources will be fetched and sent through the RAG pipeline.'
              : 'Add any links or source text you already have. The pipeline will combine these with SearXNG discovery, scrape the sources, and use RAG to build the final context.'}
            sourceDumps={sourceDumps}
            newSourceDump={newSourceDump}
            setNewSourceDump={setNewSourceDump}
            addSourceDump={addSourceDump}
            deleteSourceDump={deleteSourceDump}
            inputClass={inputClass}
          />
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
                  search_additional: true,
                  suggest_new_topic: false,
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
                  search_additional: true,
                  suggest_new_topic: false,
                })
              }}>Plan This Day</PrimaryButton>
            </div>
          </div>
        )}
      </Modal>

      {/* ── Edit Channel Modal ────────────────────────────────────── */}
      <Modal
        isOpen={!!editingChannel}
        onClose={() => setEditingChannel(null)}
        title={`Edit Channel: ${editingChannel?.name || ''}`}
        wide
      >
        {editingChannel && (
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <Field label="Channel Name"><input className={inputClass} value={editingChannel.name} onChange={e => setEditingChannel(p => ({ ...p, name: e.target.value }))} /></Field>
              <Field label="Audience"><input className={inputClass} value={editingChannel.audience} onChange={e => setEditingChannel(p => ({ ...p, audience: e.target.value }))} /></Field>
              <Field label="Tone"><input className={inputClass} value={editingChannel.tone} onChange={e => setEditingChannel(p => ({ ...p, tone: e.target.value }))} /></Field>
              <Field label="Platform">
                <select className={inputClass} value={editingChannel.platform} onChange={e => setEditingChannel(p => ({ ...p, platform: e.target.value }))}>
                  <option value="whatsapp">WhatsApp</option>
                  <option value="telegram">Telegram</option>
                  <option value="linkedin">LinkedIn</option>
                  <option value="twitter">Twitter/X</option>
                </select>
              </Field>
              <Field label="Language"><input className={inputClass} value={editingChannel.language} onChange={e => setEditingChannel(p => ({ ...p, language: e.target.value }))} /></Field>
              <Field label="Timezone"><input className={inputClass} value={editingChannel.timezone} onChange={e => setEditingChannel(p => ({ ...p, timezone: e.target.value }))} /></Field>
            </div>
            <Field label="Description"><textarea className={textareaClass} rows={3} value={editingChannel.description} onChange={e => setEditingChannel(p => ({ ...p, description: e.target.value }))} /></Field>
            <Field label="Sources" help="One URL or search query per line."><textarea className={textareaClass} rows={4} value={editingChannel.sources_text} onChange={e => setEditingChannel(p => ({ ...p, sources_text: e.target.value }))} /></Field>
            <Field label="Prompt Template"><textarea className={textareaClass} rows={4} value={editingChannel.prompt_template} onChange={e => setEditingChannel(p => ({ ...p, prompt_template: e.target.value }))} /></Field>
            <Field label="Context Notes" help="Persistent notes injected into every generation prompt."><textarea className={textareaClass} rows={3} value={editingChannel.context_notes} onChange={e => setEditingChannel(p => ({ ...p, context_notes: e.target.value }))} /></Field>
            <div className="flex gap-3">
              <PrimaryButton onClick={saveEditChannel}>Save Changes</PrimaryButton>
              <SecondaryButton onClick={() => setEditingChannel(null)}>Cancel</SecondaryButton>
            </div>
          </div>
        )}
      </Modal>

    </div>
  )
}

export default App
