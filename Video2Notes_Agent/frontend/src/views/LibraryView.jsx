import React, { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { Database, FileStack, Loader2, RefreshCw } from 'lucide-react';
import NotesWorkspace from '../components/NotesWorkspace';
import { useConfig } from '../context/ConfigContext';

const API_BASE = 'http://localhost:8000/api';

const LibraryView = () => {
  const { config } = useConfig();
  const [notes, setNotes] = useState([]);
  const [listState, setListState] = useState('idle');
  const [openState, setOpenState] = useState('idle');
  const [error, setError] = useState('');
  const [activeNoteId, setActiveNoteId] = useState(null);
  const [activeNote, setActiveNote] = useState(null);
  const [messages, setMessages] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState('');
  const [isChatting, setIsChatting] = useState(false);
  const chatEndRef = useRef(null);

  const loadNotes = async () => {
    if (!config.databaseUrl.trim()) {
      setNotes([]);
      setActiveNote(null);
      setActiveNoteId(null);
      setError('Enter a Postgres URL in settings to browse saved notes.');
      return;
    }

    setListState('loading');
    setError('');

    try {
      const response = await axios.get(`${API_BASE}/notes`, {
        params: { database_url: config.databaseUrl },
      });
      setNotes(response.data.notes || []);
      setListState('ready');
    } catch (err) {
      setListState('error');
      setError(err.response?.data?.detail || 'Failed to load saved notes.');
    }
  };

  useEffect(() => {
    loadNotes();
  }, [config.databaseUrl]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isChatting]);

  const openSavedNote = async (noteId) => {
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

  const handleSendMessage = async (event) => {
    event.preventDefault();
    if (!currentQuestion.trim() || !activeNote?.task_id || isChatting) {
      return;
    }

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
    <div className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)]">
      <aside className="rounded-[30px] border border-white/80 bg-[rgba(255,255,255,0.84)] p-5 shadow-[0_24px_70px_rgba(15,23,42,0.08)] backdrop-blur-xl">
        <div className="mb-5 flex items-center justify-between gap-3">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.28em] text-slate-500">Library</p>
            <h2 className="mt-1 text-2xl font-black text-slate-900">Saved notes</h2>
          </div>
          <button
            type="button"
            onClick={loadNotes}
            className="inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-100"
          >
            <RefreshCw className={`h-4 w-4 ${listState === 'loading' ? 'animate-spin' : ''}`} />
          </button>
        </div>

        <div className="mb-5 rounded-[24px] border border-slate-200 bg-slate-50/80 p-4 text-sm leading-relaxed text-slate-600">
          <div className="mb-2 flex items-center gap-2 text-slate-900">
            <Database className="h-4 w-4 text-teal-700" />
            <span className="font-semibold">Database source</span>
          </div>
          {config.databaseUrl ? <p className="break-all text-xs text-slate-500">{config.databaseUrl}</p> : <p>No database URL configured yet.</p>}
        </div>

        <div className="scrollbar-surface max-h-[60vh] space-y-3 overflow-y-auto pr-1">
          {listState === 'loading' ? (
            <div className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600">
              <Loader2 className="h-4 w-4 animate-spin text-cyan-700" />
              Loading saved notes...
            </div>
          ) : null}

          {notes.map((note) => (
            <button
              key={note.id}
              type="button"
              onClick={() => openSavedNote(note.id)}
              className={[
                'w-full rounded-[22px] border px-4 py-4 text-left transition-colors',
                activeNoteId === note.id
                  ? 'border-slate-900 bg-slate-900 text-white shadow-sm'
                  : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50',
              ].join(' ')}
            >
              <p className="line-clamp-2 text-sm font-bold leading-relaxed">{note.title || 'Untitled note'}</p>
              <p className={`mt-2 line-clamp-3 text-xs leading-relaxed ${activeNoteId === note.id ? 'text-slate-300' : 'text-slate-500'}`}>
                {note.description || note.url || 'Saved note'}
              </p>
            </button>
          ))}

          {listState === 'ready' && notes.length === 0 ? (
            <div className="rounded-[22px] border border-dashed border-slate-300 bg-white/70 px-4 py-6 text-sm leading-relaxed text-slate-500">
              No saved notes were found in this database yet.
            </div>
          ) : null}
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
          <div className="flex min-h-[32rem] flex-col items-center justify-center rounded-[32px] border border-dashed border-slate-300 bg-white/60 px-8 text-center shadow-[0_20px_50px_rgba(15,23,42,0.06)]">
            <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-slate-100 text-slate-500">
              <FileStack className="h-8 w-8" />
            </div>
            <h3 className="text-2xl font-black text-slate-900">Open a saved note</h3>
            <p className="mt-3 max-w-xl text-sm leading-relaxed text-slate-500">
              Pick any entry from the library to render the saved markdown, download it again, and start a new RAG chat session from the stored content.
            </p>
            {openState === 'loading' ? (
              <div className="mt-5 inline-flex items-center gap-2 rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white">
                <Loader2 className="h-4 w-4 animate-spin" />
                Opening note...
              </div>
            ) : null}
            {error ? <p className="mt-4 text-sm font-medium text-rose-700">{error}</p> : null}
          </div>
        )}
      </section>
    </div>
  );
};

export default LibraryView;