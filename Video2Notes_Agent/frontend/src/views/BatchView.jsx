import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import axios from 'axios';
import { ExternalLink, Loader2, RotateCcw } from 'lucide-react';

const API_BASE = 'http://localhost:8000/api';

const statusBadge = (status) => {
  if (status === 'completed') return 'app-chip app-chip--solid';
  if (status === 'error') return 'app-chip';
  return 'app-chip';
};

const BatchView = () => {
  const { batchId } = useParams();
  const navigate = useNavigate();
  const [batch, setBatch] = useState(null);

  useEffect(() => {
    if (!batchId) return undefined;

    const source = new EventSource(`${API_BASE}/batches/${batchId}/events`);
    const syncPayload = (payload) => setBatch(payload);
    source.addEventListener('created', (event) => syncPayload(JSON.parse(event.data)));
    source.addEventListener('update', (event) => syncPayload(JSON.parse(event.data)));
    source.onerror = async () => {
      try {
        const response = await axios.get(`${API_BASE}/batches/${batchId}`);
        syncPayload(response.data);
      } catch (error) {
        console.error(error);
      }
    };
    return () => source.close();
  }, [batchId]);

  const retryTask = async (taskId) => {
    await axios.post(`${API_BASE}/batches/${batchId}/tasks/${taskId}/retry`);
  };

  if (!batch) {
    return (
      <div className="rounded-[32px] p-8 app-card">
        <div className="flex items-center gap-3" style={{ color: 'var(--accent)' }}>
          <Loader2 className="h-5 w-5 animate-spin" />
          Loading playlist batch...
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="rounded-[36px] p-8 app-card">
        <p className="app-eyebrow">Playlist batch</p>
        <div className="mt-3 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-3xl font-black app-title">{batch.title || 'Playlist batch'}</h2>
            <p className="mt-2 app-muted">{batch.progress}</p>
          </div>
          <div className={`inline-flex rounded-full px-4 py-2 text-sm font-bold ${statusBadge(batch.status)}`}>
            {batch.status}
          </div>
        </div>
        {batch.applied_settings ? (
          <div className="mt-4 flex flex-wrap gap-2">
            <span className="rounded-full px-3 py-1 text-xs font-semibold app-surface-strong">{batch.applied_settings.note_style}</span>
            <span className="rounded-full px-3 py-1 text-xs font-semibold app-surface-strong">{batch.applied_settings.detail_level}</span>
            <span className="rounded-full px-3 py-1 text-xs font-semibold app-surface-strong">{batch.selected_video_ids?.length || batch.children?.length || 0} selected</span>
            <span className="rounded-full px-3 py-1 text-xs font-semibold app-surface-strong">
              {batch.playlist_processing_mode === 'sequential' ? 'one by one' : `parallel x${batch.playlist_worker_count || 1}`}
            </span>
            <span className="rounded-full px-3 py-1 text-xs font-semibold app-surface-strong">
              {batch.applied_settings.generate_study_assets ? 'study assets on' : 'study assets off'}
            </span>
          </div>
        ) : null}
      </section>

      <section className="rounded-[36px] p-6 app-card">
        <div className="grid gap-4">
          {(batch.children || []).map((child) => (
            <article key={child.task_id} className="rounded-[24px] p-5 app-soft">
              <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div className="min-w-0">
                  <h3 className="truncate text-lg font-bold app-title">{child.title || child.video_title}</h3>
                  <p className="mt-1 text-sm app-muted">{child.progress}</p>
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  <span className={`inline-flex rounded-full px-3 py-1 text-xs font-bold uppercase ${statusBadge(child.status)}`}>
                    {child.status}
                  </span>
                  {child.status === 'completed' ? (
                    <button type="button" onClick={() => navigate(`/result/${child.task_id}`)} className="inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold app-primary-btn">
                      <ExternalLink className="h-4 w-4" />
                      Open
                    </button>
                  ) : null}
                  {child.status === 'error' ? (
                    <button type="button" onClick={() => retryTask(child.task_id)} className="inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold app-surface-strong">
                      <RotateCcw className="h-4 w-4" />
                      Retry
                    </button>
                  ) : null}
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
};

export default BatchView;
