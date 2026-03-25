import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import ProcessingSteps from '../components/ProcessingSteps';
import { AlertCircle, Loader2 } from 'lucide-react';

const API_BASE = 'http://localhost:8000/api';

const ProcessingView = () => {
  const { taskId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [status, setStatus] = useState('processing');
  const [progress, setProgress] = useState('Starting...');
  const [steps, setSteps] = useState({});
  const [error, setError] = useState('');

  useEffect(() => {
    if (!taskId) return undefined;

    let isClosed = false;
    const source = new EventSource(`${API_BASE}/tasks/${taskId}/events`);

    const applyPayload = (payload) => {
      setSteps(payload.steps || {});
      setProgress(payload.progress || 'Working...');

      if (payload.status === 'completed') {
        setStatus('completed');
        source.close();
        if (!isClosed) {
          navigate(`/result/${taskId}`, { state: { notes: payload, url: location.state?.url } });
        }
      } else if (payload.status === 'error') {
        setStatus('error');
        setError(payload.error || payload.progress || 'An error occurred during processing.');
        source.close();
      }
    };

    source.addEventListener('created', (event) => applyPayload(JSON.parse(event.data)));
    source.addEventListener('update', (event) => applyPayload(JSON.parse(event.data)));
    source.onerror = async () => {
      try {
        const response = await axios.get(`${API_BASE}/status/${taskId}`);
        applyPayload(response.data);
      } catch {
        setStatus('error');
        setError('Live updates disconnected and the task could not be refreshed.');
      }
    };

    return () => {
      isClosed = true;
      source.close();
    };
  }, [taskId, navigate, location.state?.url]);

  return (
    <div className="mx-auto mt-12 max-w-5xl animate-in fade-in slide-in-from-bottom-4 duration-700">
      <section className="app-hero rounded-[36px] p-6 sm:p-8 lg:p-10">
        <div className="relative z-10 grid gap-8 lg:grid-cols-[minmax(0,1.1fr)_360px] lg:items-center">
          <div className="space-y-5">
            <div className="app-kicker">Live pipeline</div>
            <h2 className="app-display text-[clamp(2.6rem,4vw,4.5rem)]">
              {status === 'processing' ? 'Processing your video...' : 'Something went wrong'}
            </h2>
            <p className="app-lead max-w-2xl">
              {status === 'processing' ? 'Live progress updates are streaming in as each stage completes.' : 'Analysis halted. The current run needs a retry or a clean restart.'}
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
            <div className="app-metric">
              <div className="app-metric__label">Status</div>
              <div className="app-metric__value">{status}</div>
            </div>
            <div className="app-metric">
              <div className="app-metric__label">Current step</div>
              <div className="app-metric__value">{progress}</div>
            </div>
          </div>
        </div>
      </section>

      <section className="mt-6 rounded-[36px] p-6 sm:p-8 app-card">
        {status === 'error' ? (
          <div className="space-y-6 py-8 text-center">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full" style={{ background: 'color-mix(in srgb, var(--accent-3) 14%, white)' }}>
              <AlertCircle className="h-8 w-8" style={{ color: 'var(--accent-3)' }} />
            </div>
            <p className="font-medium app-title">{error}</p>
            <button onClick={() => navigate('/')} className="text-sm font-semibold underline underline-offset-4 app-muted">
              Go back and try again
            </button>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <span className="text-xs font-bold uppercase tracking-[0.28em] app-muted">Active pipeline</span>
              <div className="flex items-center gap-2 text-sm font-medium" style={{ color: 'var(--accent)' }}>
                <Loader2 className="h-4 w-4 animate-spin" />
                {progress}
              </div>
            </div>
            <div className="rounded-[32px] p-6 app-soft">
              <ProcessingSteps currentSteps={steps} />
            </div>
            <p className="text-center text-[11px] font-medium app-muted">
              Tip: live progress is now streamed over SSE, with status fallback preserved for refreshes.
            </p>
          </div>
        )}
      </section>
    </div>
  );
};

export default ProcessingView;
