import React, { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { ChevronDown, Database, FileStack, FolderPlus, Loader2, RefreshCw, Search } from 'lucide-react';
import Modal from '../components/Modal';
import NotesWorkspace from '../components/NotesWorkspace';
import { useConfig } from '../context/ConfigContext';

const API_BASE = 'http://localhost:8000/api';

const LibraryView = () => {
  const { config } = useConfig();
  const [notes, setNotes] = useState([]);
  const [playlistRuns, setPlaylistRuns] = useState([]);
  const [expandedRuns, setExpandedRuns] = useState([]);
  const [collections, setCollections] = useState([]);
  const [selectedCollectionId, setSelectedCollectionId] = useState('');
  const [query, setQuery] = useState('');
  const [newCollectionName, setNewCollectionName] = useState('');
  const [listState, setListState] = useState('idle');
  const [showBrowser, setShowBrowser] = useState(false);
  const [openState, setOpenState] = useState('idle');
  const [error, setError] = useState('');
  const [activeNoteId, setActiveNoteId] = useState(null);
  const [activeNote, setActiveNote] = useState(null);
  const [messages, setMessages] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState('');
  const [isChatting, setIsChatting] = useState(false);
  const chatEndRef = useRef(null);

  const loadCollections = async () => {
    if (!config.databaseUrl.trim()) return;
    const response = await axios.get(`${API_BASE}/collections`, {
      params: { database_url: config.databaseUrl },
    });
    setCollections(response.data.collections || []);
  };

  const loadNotes = async () => {
    if (!config.databaseUrl.trim()) {
      setNotes([]);
      setPlaylistRuns([]);
      setActiveNote(null);
      setActiveNoteId(null);
      setError('Enter a Postgres URL in settings to browse saved notes.');
      return;
    }

    setListState('loading');
    setError('');

    try {
      const response = await axios.get(`${API_BASE}/notes`, {
        params: {
          database_url: config.databaseUrl,
          q: query || undefined,
          collection_id: selectedCollectionId || undefined,
        },
      });
      setNotes(response.data.notes || []);
      setPlaylistRuns(response.data.playlist_runs || []);
      setListState('ready');
    } catch (err) {
      setListState('error');
      setError(err.response?.data?.detail || 'Failed to load saved notes.');
    }
  };

  useEffect(() => {
    loadCollections().catch(console.error);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config.databaseUrl]);

  useEffect(() => {
    loadNotes();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config.databaseUrl, query, selectedCollectionId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isChatting]);

  const createCollection = async (event) => {
    event.preventDefault();
    if (!newCollectionName.trim()) return;
    await axios.post(`${API_BASE}/collections`, {
      name: newCollectionName.trim(),
      database_url: config.databaseUrl,
    });
    setNewCollectionName('');
    await loadCollections();
  };

  const openSavedNote = async (noteId) => {
    setShowBrowser(false);
    setActiveNoteId(noteId);
    setOpenState('loading');
    setMessages([]);
    setCurrentQuestion('');
    setError('');

    try {
      const response = await axios.post(`${API_BASE}/notes/${noteId}/open`, {
        provider: config.provider,
        anthropic_api_key: config.anthropicApiKey || null,
        gemini_api_key: config.geminiApiKey || null,
        ollama_model: config.ollamaModel || null,
        ollama_base_url: config.ollamaBaseUrl || null,
        database_url: config.databaseUrl,
      });
      setActiveNote(response.data);
      setOpenState('ready');
    } catch (err) {
      setOpenState('error');
      setError(err.response?.data?.detail || 'Failed to open the selected note.');
    }
  };

  const toggleRun = (runId) => {
    setExpandedRuns((previous) =>
      previous.includes(runId) ? previous.filter((id) => id !== runId) : [...previous, runId]
    );
  };

  const updateNoteCollection = async (noteId, collectionId) => {
    await axios.patch(`${API_BASE}/notes/${noteId}`, {
      collection_id: collectionId || null,
      database_url: config.databaseUrl,
    });
    await loadNotes();
    if (activeNote?.id === noteId) {
      setActiveNote((previous) => ({ ...previous, collection_id: collectionId || null }));
    }
  };

  const totalSavedCount = notes.length + playlistRuns.reduce((sum, run) => sum + run.children.length, 0);

  const renderSavedNotesList = () => (
    <div className="scrollbar-surface max-h-[68vh] space-y-3 overflow-y-auto pr-1">
      {listState === 'loading' ? (
        <div className="flex items-center gap-3 rounded-2xl px-4 py-3 text-sm app-card-strong app-muted">
          <Loader2 className="h-4 w-4 animate-spin" style={{ color: 'var(--accent)' }} />
          Loading saved notes...
        </div>
      ) : null}

      {playlistRuns.map((run) => {
        const expanded = expandedRuns.includes(run.id);
        return (
          <div key={run.id} className="rounded-[22px] p-4 app-card-strong">
            <button type="button" onClick={() => toggleRun(run.id)} className="flex w-full items-center justify-between gap-3 text-left">
              <div className="min-w-0">
                <p className="truncate text-sm font-bold app-title">{run.title}</p>
                <p className="mt-1 text-xs app-muted">{run.children.length} processed videos</p>
              </div>
              <ChevronDown className={`h-4 w-4 transition-transform ${expanded ? 'rotate-180' : ''}`} />
            </button>
            {expanded ? (
              <div className="mt-4 space-y-3">
                {run.children.map((child) => (
                  <button
                    key={child.id}
                    type="button"
                    onClick={() => openSavedNote(child.id)}
                    className={`w-full rounded-[18px] px-4 py-3 text-left transition-colors ${activeNoteId === child.id ? 'app-primary-btn' : 'app-soft'}`}
                  >
                    <p className="line-clamp-2 text-sm font-semibold">{child.title || 'Untitled child note'}</p>
                    <p className="mt-1 line-clamp-2 text-xs opacity-80">{child.description || child.url}</p>
                  </button>
                ))}
              </div>
            ) : null}
          </div>
        );
      })}

      {notes.map((note) => (
        <div key={note.id} className={`rounded-[22px] p-4 transition-colors ${activeNoteId === note.id ? 'app-primary-btn' : 'app-card-strong'}`}>
          <button type="button" onClick={() => openSavedNote(note.id)} className="w-full text-left">
            <p className="line-clamp-2 text-sm font-bold leading-relaxed">{note.title || 'Untitled note'}</p>
            <p className="mt-2 line-clamp-3 text-xs leading-relaxed opacity-80">
              {note.description || note.url || 'Saved note'}
            </p>
          </button>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em]">
            {note.note_style ? <span className="rounded-full px-2 py-1" style={{ background: 'rgba(255,255,255,0.18)' }}>{note.note_style.replaceAll('_', ' ')}</span> : null}
            {note.collection_name ? <span className="rounded-full px-2 py-1" style={{ background: 'rgba(255,255,255,0.18)' }}>{note.collection_name}</span> : null}
          </div>
          <select value={note.collection_id || ''} onChange={(event) => updateNoteCollection(note.id, event.target.value ? Number(event.target.value) : null)} className="field-shell mt-3 text-sm" onClick={(event) => event.stopPropagation()}>
            <option value="">No collection</option>
            {collections.map((collection) => (
              <option key={collection.id} value={collection.id}>{collection.name}</option>
            ))}
          </select>
        </div>
      ))}

      {listState === 'ready' && totalSavedCount === 0 ? (
        <div className="rounded-[22px] border border-dashed px-4 py-6 text-sm leading-relaxed app-muted" style={{ borderColor: 'var(--border)' }}>
          No saved notes match your current search and collection filter.
        </div>
      ) : null}
    </div>
  );

  const handleSendMessage = async (event) => {
    event.preventDefault();
    if (!currentQuestion.trim() || !activeNote?.task_id || isChatting) return;

    const question = currentQuestion;
    setMessages((previous) => [...previous, { id: Date.now(), role: 'user', text: question }]);
    setCurrentQuestion('');
    setIsChatting(true);

    try {
      const response = await axios.post(`${API_BASE}/chat`, {
        task_id: activeNote.task_id,
        question,
      });
      setMessages((previous) => [...previous, { id: Date.now() + 1, role: 'assistant', text: response.data.answer }]);
    } catch (err) {
      setMessages((previous) => [...previous, {
        id: Date.now() + 1,
        role: 'assistant',
        text: err.response?.data?.detail || 'The RAG chat request failed.',
      }]);
    } finally {
      setIsChatting(false);
    }
  };

  return (
    <div className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
      <aside className="rounded-[30px] p-5 app-card">
        <div className="mb-5 flex items-center justify-between gap-3">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.28em] app-muted">Library</p>
            <h2 className="mt-1 text-2xl font-black app-title">Saved notes</h2>
          </div>
          <div className="flex items-center gap-2">
            <button type="button" onClick={loadNotes} className="inline-flex h-10 w-10 items-center justify-center rounded-2xl app-card-strong">
              <RefreshCw className={`h-4 w-4 ${listState === 'loading' ? 'animate-spin' : ''}`} />
            </button>
            <button type="button" onClick={() => setShowBrowser(true)} className="rounded-full px-4 py-2 text-sm font-semibold app-primary-btn">
              Browse all
            </button>
          </div>
        </div>

        <div className="mb-5 rounded-[24px] p-4 text-sm leading-relaxed app-soft">
          <div className="mb-2 flex items-center gap-2 app-title">
            <Database className="h-4 w-4" style={{ color: 'var(--accent)' }} />
            <span className="font-semibold">Database source</span>
          </div>
          {config.databaseUrl ? <p className="break-all text-xs app-muted">{config.databaseUrl}</p> : <p className="app-muted">No database URL configured yet.</p>}
        </div>

        <div className="mb-4 grid gap-3">
          <form onSubmit={createCollection} className="flex gap-2">
            <input value={newCollectionName} onChange={(event) => setNewCollectionName(event.target.value)} placeholder="New collection name" className="field-shell" />
            <button type="submit" className="inline-flex h-12 w-12 items-center justify-center rounded-2xl app-primary-btn">
              <FolderPlus className="h-4 w-4" />
            </button>
          </form>
        </div>

        <div className="space-y-3">
          <div className="rounded-[22px] p-4 app-card-strong">
            <p className="text-xs font-bold uppercase tracking-[0.24em] app-muted">Saved entries</p>
            <p className="mt-2 text-3xl font-black app-title">{totalSavedCount}</p>
            <p className="mt-2 text-sm app-muted">Open the note browser modal to inspect playlist groups and individual saved notes with more room.</p>
          </div>
          <button type="button" onClick={() => setShowBrowser(true)} className="w-full rounded-[22px] px-4 py-4 text-sm font-semibold app-card-strong">
            View saved notes list
          </button>
          {error ? <p className="text-sm font-medium app-title">{error}</p> : null}
        </div>
      </aside>

      <section>
        {activeNote ? (
          <NotesWorkspace
            data={activeNote}
            messages={messages}
            currentQuestion={currentQuestion}
            setCurrentQuestion={setCurrentQuestion}
            onSendMessage={handleSendMessage}
            isChatting={isChatting}
            chatEndRef={chatEndRef}
          />
        ) : (
          <div className="flex min-h-[32rem] flex-col items-center justify-center rounded-[32px] border border-dashed px-8 text-center app-card" style={{ borderColor: 'var(--border)' }}>
            <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-full" style={{ background: 'color-mix(in srgb, var(--accent) 14%, white)', color: 'var(--accent)' }}>
              <FileStack className="h-8 w-8" />
            </div>
            <h3 className="text-2xl font-black app-title">Open a saved note</h3>
            <p className="mt-3 max-w-xl text-sm leading-relaxed app-muted">
              Search your saved notes, filter by collection, and reopen any entry with its study assets and RAG chat flow intact.
            </p>
            {openState === 'loading' ? (
              <div className="mt-5 inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold app-primary-btn">
                <Loader2 className="h-4 w-4 animate-spin" />
                Opening note...
              </div>
            ) : null}
            {error ? <p className="mt-4 text-sm font-medium app-title">{error}</p> : null}
          </div>
        )}
      </section>

      <Modal open={showBrowser} onClose={() => setShowBrowser(false)} title="Saved Video Notes" widthClass="max-w-6xl">
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm app-muted">
              Browse {totalSavedCount} saved entries with hybrid search, collection filters, and playlist-group drill-in.
            </p>
            <button type="button" onClick={loadNotes} className="rounded-full px-4 py-2 text-sm font-semibold app-card-strong">
              Refresh list
            </button>
          </div>
          <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_240px]">
            <label className="flex items-center gap-3 rounded-[24px] px-4 py-3 app-card-strong">
              <Search className="h-4 w-4" style={{ color: 'var(--accent)' }} />
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search notes, concepts, actions..." className="w-full border-none bg-transparent outline-none app-title" />
            </label>
            <select value={selectedCollectionId} onChange={(event) => setSelectedCollectionId(event.target.value)} className="field-shell">
              <option value="">All collections</option>
              {collections.map((collection) => (
                <option key={collection.id} value={collection.id}>{collection.name}</option>
              ))}
            </select>
          </div>
          <p className="text-xs leading-relaxed app-muted">Hybrid search is active in this modal: keyword ranking plus vector similarity filters the note browser results.</p>
          {renderSavedNotesList()}
        </div>
      </Modal>
    </div>
  );
};

export default LibraryView;
