import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import ProcessingSteps from '../components/ProcessingSteps';
import { Loader2, AlertCircle } from 'lucide-react';

const API_BASE = "http://localhost:8000/api";

const ProcessingView = () => {
    const { taskId } = useParams();
    const navigate = useNavigate();
    const location = useLocation();
    const [status, setStatus] = useState('processing');
    const [progress, setProgress] = useState('Starting...');
    const [steps, setSteps] = useState({});
    const [error, setError] = useState('');

    useEffect(() => {
        let interval;
        if (taskId) {
            interval = setInterval(async () => {
                try {
                    const res = await axios.get(`${API_BASE}/status/${taskId}`);
                    setSteps(res.data.steps || {});
                    setProgress(res.data.progress);
                    
                    if (res.data.status === 'completed') {
                        clearInterval(interval);
                        navigate(`/result/${taskId}`, { state: { notes: res.data, url: location.state?.url } });
                    } else if (res.data.status === 'error') {
                        setStatus('error');
                        setError(res.data.progress || 'An error occurred during processing.');
                        clearInterval(interval);
                    }
                } catch (error) {
                    console.error("Polling error", error);
                }
            }, 2000);
        }
        return () => clearInterval(interval);
    }, [taskId, navigate]);

    return (
        <div className="mx-auto mt-12 max-w-3xl animate-in fade-in slide-in-from-bottom-4 duration-700">
            <div className="mb-10 text-center">
                <h2 className="mb-4 text-4xl font-black tracking-tight text-slate-900">
                    {status === 'processing' ? 'Processing your video...' : 'Something went wrong'}
                </h2>
                <p className="text-lg leading-relaxed text-slate-600">
                    {status === 'processing' ? 'Our AI agents are analyzing your content. This usually takes 1-3 minutes.' : 'Analysis halted.'}
                </p>
            </div>

            <section className="rounded-[32px] border border-white/80 bg-[rgba(255,255,255,0.84)] p-8 shadow-[0_28px_80px_rgba(15,23,42,0.10)] backdrop-blur-xl">
                    {status === 'error' ? (
                        <div className="space-y-6 py-6 text-center">
                            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full border border-rose-200 bg-rose-50">
                                <AlertCircle className="h-8 w-8 text-rose-500" />
                            </div>
                            <p className="font-medium text-rose-700">{error}</p>
                            <button 
                                onClick={() => navigate('/')}
                                className="text-sm font-semibold text-slate-600 underline underline-offset-4 hover:text-slate-900"
                            >
                                Go back and try again
                            </button>
                        </div>
                    ) : (
                        <div className="space-y-6">
                            <div className="mb-4 flex items-center justify-between">
                                <span className="text-xs font-bold uppercase tracking-[0.28em] text-slate-500">Active pipeline</span>
                                <div className="flex items-center gap-2 text-sm font-medium text-cyan-700">
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                    {progress}
                                </div>
                            </div>
                            <div className="rounded-[28px] border border-slate-200 bg-slate-50/80 p-6">
                                <ProcessingSteps currentSteps={steps} />
                            </div>
                            <p className="text-center text-[11px] font-medium text-slate-500">
                                Tip: You can leave this page and come back later with the URL or task ID.
                            </p>
                        </div>
                    )}
            </section>
        </div>
    );
};

export default ProcessingView;
