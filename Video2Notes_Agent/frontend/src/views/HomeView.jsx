import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import ProcessSection from '../components/ProcessSection';
import { useConfig } from '../context/ConfigContext';

const API_BASE = "http://localhost:8000/api";

const HomeView = () => {
    const { config } = useConfig();
    const [url, setUrl] = useState('');
    const [error, setError] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const navigate = useNavigate();

    const handleGenerate = async (e) => {
        e.preventDefault();
        if (!url.trim()) return;

        setIsSubmitting(true);
        setError('');

        try {
            const payload = {
                url,
                provider: config.provider,
                anthropic_api_key: config.anthropicApiKey || null,
                gemini_api_key: config.geminiApiKey || null,
                hf_token: config.hfToken || null,
                ollama_model: config.ollamaModel,
                ollama_base_url: config.ollamaBaseUrl,
                start_time: config.startTime || null,
                end_time: config.endTime || null,
                whisper_provider: config.whisperProvider,
                whisper_model: config.whisperModel || null,
                language: config.language || null,
                detail_level: config.detailLevel,
                keep_qa: config.keepQa,
                keep_examples: config.keepExamples,
                include_timestamps: config.includeTimestamps,
                groq_api_key: config.groqApiKey || null,
                database_url: config.databaseUrl || null,
            };
            
            const res = await axios.post(`${API_BASE}/process`, payload);
            navigate(`/process/${res.data.task_id}`, { state: { url }});
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to connect to backend.');
            setIsSubmitting(false);
        }
    };

    return (
        <ProcessSection 
            url={url} 
            setUrl={setUrl} 
            onGenerate={handleGenerate} 
            status={isSubmitting ? 'processing' : error ? 'error' : 'idle'}
            progress={isSubmitting ? 'Submitting...' : error}
        />
    );
};

export default HomeView;
