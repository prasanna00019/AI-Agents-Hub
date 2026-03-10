import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import { Youtube, Settings2, Play, MessageSquare, Loader2, FileText, Send, Clock, Bot, Sparkles } from 'lucide-react';

const API_BASE = "http://localhost:8000/api";

function App() {
  // Form State
  const [url, setUrl] = useState('');
  const [provider, setProvider] = useState('gemini');
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');
  const [showSettings, setShowSettings] = useState(false);

  // Process State
  const [status, setStatus] = useState('idle'); // idle, processing, completed, error
  const [taskId, setTaskId] = useState(null);
  const [progress, setProgress] = useState('');

  // Result State
  const [notes, setNotes] = useState('');
  const [videoTitle, setVideoTitle] = useState('');
  const [videoDescription, setVideoDescription] = useState('');

  // Chat State
  const [chatMessages, setChatMessages] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState('');
  const [isChatting, setIsChatting] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    let interval;
    if (status === 'processing' && taskId) {
      interval = setInterval(async () => {
        try {
          const res = await axios.get(`${API_BASE}/status/${taskId}`);
          setProgress(res.data.progress);
          if (res.data.status === 'completed') {
            setStatus('completed');
            setNotes(res.data.notes);
            setVideoTitle(res.data.video_title);
            setVideoDescription(res.data.video_description);
            clearInterval(interval);
          } else if (res.data.status === 'error') {
            setStatus('error');
            setProgress(res.data.progress || 'An error occurred during processing.');
            clearInterval(interval);
          }
        } catch (error) {
          console.error("Polling error", error);
        }
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [status, taskId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  const handleGenerate = async (e) => {
    e.preventDefault();
    if (!url.trim()) return;

    setStatus('processing');
    setProgress('Submitting job...');
    setNotes('');
    setChatMessages([]);

    try {
      const payload = {
        url,
        provider,
        start_time: startTime || null,
        end_time: endTime || null
      };
      
      const res = await axios.post(`${API_BASE}/process`, payload);
      setTaskId(res.data.task_id);
    } catch (err) {
      setStatus('error');
      setProgress('Failed to connect to backend.');
      console.error(err);
    }
  };

  const handleChat = async (e) => {
    e.preventDefault();
    if (!currentQuestion.trim() || !taskId) return;

    const newMsg = { id: Date.now(), role: 'user', text: currentQuestion };
    setChatMessages(prev => [...prev, newMsg]);
    setCurrentQuestion('');
    setIsChatting(true);

    try {
      const res = await axios.post(`${API_BASE}/chat`, {
        task_id: taskId,
        question: newMsg.text
      });
      setChatMessages(prev => [...prev, { id: Date.now(), role: 'assistant', text: res.data.answer }]);
    } catch (err) {
      setChatMessages(prev => [...prev, { id: Date.now(), role: 'assistant', text: 'Sorry, I encountered an error connecting to the RAG engine.' }]);
    } finally {
      setIsChatting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 font-sans selection:bg-indigo-500/30">
      {/* Navbar */}
      <nav className="border-b border-white/5 bg-slate-900/50 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-500 to-purple-500 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
            VideoNotes Agent
          </h1>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Input Section */}
        {status !== 'completed' && (
          <div className="max-w-2xl mx-auto mt-12 mb-20 animate-in fade-in slide-in-from-bottom-4 duration-700">
            <div className="text-center mb-10">
              <h2 className="text-4xl md:text-5xl font-extrabold tracking-tight mb-4 leading-tight">
                Turn any long video into <br />
                <span className="bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
                  Intelligent Notes.
                </span>
              </h2>
              <p className="text-slate-400 text-lg max-w-xl mx-auto">
                Paste a YouTube URL, extract exactly what you need, and ask follow-up questions directly to the video.
              </p>
            </div>

            <form onSubmit={handleGenerate} className="bg-slate-800/50 border border-white/10 rounded-2xl p-6 shadow-2xl backdrop-blur-md">
              <div className="relative mb-4">
                <Youtube className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 w-5 h-5" />
                <input
                  type="url"
                  placeholder="https://youtube.com/watch?v=..."
                  className="w-full bg-slate-900/50 border border-white/5 rounded-xl py-4 pl-12 pr-4 text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all text-lg"
                  value={url}
                  onChange={e => setUrl(e.target.value)}
                  disabled={status === 'processing'}
                  required
                />
              </div>

              <div className="mb-6">
                <button
                  type="button"
                  onClick={() => setShowSettings(!showSettings)}
                  className="flex items-center gap-2 text-sm text-slate-400 hover:text-slate-200 transition-colors"
                >
                  <Settings2 className="w-4 h-4" />
                  {showSettings ? 'Hide Advanced Settings' : 'Advanced Settings (Timestamps, Models)'}
                </button>

                {showSettings && (
                  <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4 animate-in slide-in-from-top-2 duration-300">
                    <div className="space-y-4">
                      <div>
                        <label className="block text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">AI Model</label>
                        <select
                          value={provider}
                          onChange={e => setProvider(e.target.value)}
                          className="w-full bg-slate-900 border border-white/10 rounded-lg p-3 text-sm focus:ring-2 focus:ring-indigo-500/50 outline-none"
                        >
                          <option value="gemini">Google Gemini 2.5 Flash</option>
                          <option value="anthropic">Anthropic Claude 3.5 Sonnet</option>
                          <option value="ollama">Ollama (Local)</option>
                        </select>
                      </div>
                    </div>
                    
                    <div className="space-y-4">
                      <div>
                        <label className="block flex items-center gap-2 text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">
                          <Clock className="w-3 h-3" /> Timestamp Range (Optional)
                        </label>
                        <div className="flex items-center gap-2">
                          <input
                            type="text"
                            placeholder="00:00"
                            className="w-full bg-slate-900 border border-white/10 rounded-lg p-3 text-sm focus:ring-2 focus:ring-indigo-500/50 outline-none text-center placeholder:text-slate-600"
                            value={startTime}
                            onChange={e => setStartTime(e.target.value)}
                          />
                          <span className="text-slate-500">to</span>
                          <input
                            type="text"
                            placeholder="05:30"
                            className="w-full bg-slate-900 border border-white/10 rounded-lg p-3 text-sm focus:ring-2 focus:ring-indigo-500/50 outline-none text-center placeholder:text-slate-600"
                            value={endTime}
                            onChange={e => setEndTime(e.target.value)}
                          />
                        </div>
                        <p className="text-[10px] text-slate-500 mt-2">Use MM:SS format to process only a specific part of the video.</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <button
                type="submit"
                disabled={status === 'processing'}
                className="w-full bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-400 hover:to-purple-500 text-white font-semibold py-4 px-6 rounded-xl flex items-center justify-center gap-2 transition-all shadow-lg shadow-indigo-500/25 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {status === 'processing' ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>Processing ({progress})...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-5 h-5 fill-current" />
                    <span>Generate Intelligent Notes</span>
                  </>
                )}
              </button>

              {status === 'error' && (
                <div className="mt-4 p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
                  {progress}
                </div>
              )}
            </form>
          </div>
        )}

        {/* Results Section */}
        {status === 'completed' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start fade-in duration-700">
            
            {/* Left Column: Metadata & Notes */}
            <div className="lg:col-span-8 space-y-6">
              
              {/* Video Header Card */}
              <div className="bg-slate-800/40 border border-white/10 rounded-2xl p-6 backdrop-blur-md">
                <div className="flex items-start gap-4">
                  <div className="p-3 bg-indigo-500/10 rounded-xl border border-indigo-500/20 mt-1">
                    <FileText className="w-6 h-6 text-indigo-400" />
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold text-white mb-2 leading-tight">{videoTitle}</h2>
                    <p className="text-sm text-slate-400 line-clamp-3 leading-relaxed">
                      {videoDescription || "No description provided."}
                    </p>
                  </div>
                </div>
              </div>

              {/* Notes Content */}
              <div className="bg-slate-900 border border-white/10 rounded-2xl p-8 shadow-xl prose prose-invert prose-indigo max-w-none">
                <ReactMarkdown>{notes}</ReactMarkdown>
              </div>
            </div>

            {/* Right Column: AI Chat for RAG */}
            <div className="lg:col-span-4 sticky top-24 bg-slate-800/80 border border-white/10 rounded-2xl flex flex-col h-[600px] shadow-xl backdrop-blur-xl overflow-hidden">
              <div className="p-5 border-b border-white/10 bg-slate-800/50 flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-purple-500/20 flex items-center justify-center border border-purple-500/30">
                  <Bot className="w-4 h-4 text-purple-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-white tracking-tight">Q&A Chat</h3>
                  <p className="text-xs text-slate-400">Ask questions about the video</p>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto p-5 space-y-4">
                {chatMessages.length === 0 && (
                  <div className="h-full flex flex-col items-center justify-center text-center text-slate-500 space-y-3">
                    <MessageSquare className="w-8 h-8 opacity-50" />
                    <p className="text-sm px-4">Don't understand a concept? Ask follow-up questions to query the video directly.</p>
                  </div>
                )}
                {chatMessages.map((msg) => (
                  <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[85%] rounded-2xl p-4 text-sm leading-relaxed ${
                      msg.role === 'user' 
                        ? 'bg-indigo-600 text-white rounded-tr-sm' 
                        : 'bg-slate-700/50 text-slate-200 border border-white/5 rounded-tl-sm'
                    }`}>
                      {msg.role === 'assistant' ? <ReactMarkdown>{msg.text}</ReactMarkdown> : msg.text}
                    </div>
                  </div>
                ))}
                {isChatting && (
                  <div className="flex justify-start">
                    <div className="bg-slate-700/50 border border-white/5 rounded-2xl rounded-tl-sm p-4 w-16 flex items-center justify-center gap-1.5 h-[52px]">
                      <div className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                      <div className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                      <div className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce"></div>
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              <div className="p-4 bg-slate-800/90 border-t border-white/10">
                <form onSubmit={handleChat} className="relative">
                  <input
                    type="text"
                    placeholder="Ask about timestamps, concepts, etc..."
                    value={currentQuestion}
                    onChange={(e) => setCurrentQuestion(e.target.value)}
                    disabled={isChatting}
                    className="w-full bg-slate-900 border border-white/10 rounded-xl py-3 pl-4 pr-12 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 disabled:opacity-50"
                  />
                  <button 
                    type="submit" 
                    disabled={isChatting || !currentQuestion.trim()}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-purple-500/20 text-purple-400 hover:bg-purple-500/30 hover:text-purple-300 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </form>
              </div>
            </div>
            
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
