import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import ProcessSection from '../components/ProcessSection';
import { useConfig } from '../context/ConfigContext';

const API_BASE = 'http://localhost:8000/api';

const isPlaylistUrl = (value) => {
  try {
    const url = new URL(value);
    return url.hostname.includes('youtube') && url.searchParams.has('list') && url.pathname.includes('/watch');
  } catch {
    return false;
  }
};

const HomeView = () => {
  const { config } = useConfig();
  const [mode, setMode] = useState('url');
  const [url, setUrl] = useState('');
  const [file, setFile] = useState(null);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null);
  const [playlistPreview, setPlaylistPreview] = useState(null);
  const [selectedVideoIds, setSelectedVideoIds] = useState([]);
  const navigate = useNavigate();

  const buildPayload = () => ({
    url,
    provider: config.provider,
    anthropic_api_key: config.anthropicApiKey || null,
    gemini_api_key: config.geminiApiKey || null,
    hf_token: config.hfToken || null,
    ollama_model: config.ollamaModel || null,
    ollama_base_url: config.ollamaBaseUrl || null,
    start_time: config.startTime || null,
    end_time: config.endTime || null,
    whisper_provider: config.whisperProvider,
    whisper_model: config.whisperModel || null,
    language: config.language || null,
    detail_level: config.detailLevel,
    note_style: config.noteStyle,
    custom_prompt_template: config.customPromptTemplate || null,
    keep_qa: config.keepQa,
    keep_examples: config.keepExamples,
    include_timestamps: config.includeTimestamps,
    groq_api_key: config.groqApiKey || null,
    database_url: config.databaseUrl || null,
  });

  const handleGenerate = async (event) => {
    event.preventDefault();
    setError('');
    setIsSubmitting(true);
    setUploadProgress(null);

    try {
      if (mode === 'upload') {
        if (!file) {
          throw new Error('Choose a local file before submitting.');
        }

        const formData = new FormData();
        formData.append('file', file);
        formData.append('payload_json', JSON.stringify({ ...buildPayload(), url: '' }));
        const response = await axios.post(`${API_BASE}/process/upload`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: (progressEvent) => {
            if (!progressEvent.total) return;
            setUploadProgress(Math.round((progressEvent.loaded * 100) / progressEvent.total));
          },
        });
        navigate(`/process/${response.data.task_id}`, { state: { sourceMode: 'upload', fileName: file.name } });
        return;
      }

      if (!url.trim()) {
        throw new Error('Paste a video or playlist URL.');
      }

      const payload = buildPayload();
      if (isPlaylistUrl(url)) {
        const preview = await axios.post(`${API_BASE}/process/playlist/preview`, payload);
        const ids = (preview.data.entries || []).map((entry) => entry.id);
        setPlaylistPreview(preview.data);
        setSelectedVideoIds(ids);
        setIsSubmitting(false);
        return;
      }

      const response = await axios.post(`${API_BASE}/process`, payload);
      navigate(`/process/${response.data.task_id}`, { state: { url } });
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to connect to backend.');
      setIsSubmitting(false);
    }
  };

  const handleProcessPlaylist = async (processAll = false) => {
    if (!playlistPreview) return;
    setError('');
    setIsSubmitting(true);
    try {
      const payload = {
        ...buildPayload(),
        selected_video_ids: processAll ? (playlistPreview.entries || []).map((entry) => entry.id) : selectedVideoIds,
      };
      const response = await axios.post(`${API_BASE}/process/playlist`, payload);
      setPlaylistPreview(null);
      navigate(`/batch/${response.data.batch_id}`, { state: { url } });
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to start playlist processing.');
      setIsSubmitting(false);
    }
  };

  return (
    <ProcessSection
      mode={mode}
      setMode={setMode}
      url={url}
      setUrl={setUrl}
      file={file}
      setFile={setFile}
      onGenerate={handleGenerate}
      status={isSubmitting ? 'processing' : error ? 'error' : 'idle'}
      progress={isSubmitting ? 'Submitting...' : error}
      uploadProgress={uploadProgress}
      playlistPreview={playlistPreview}
      selectedVideoIds={selectedVideoIds}
      setSelectedVideoIds={setSelectedVideoIds}
      onClosePlaylistPreview={() => setPlaylistPreview(null)}
      onProcessPlaylist={handleProcessPlaylist}
    />
  );
};

export default HomeView;
