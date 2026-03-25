import React, { useState, useEffect, useRef } from 'react';
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import NotesWorkspace from '../components/NotesWorkspace';

const API_BASE = "http://localhost:8000/api";

const ResultView = () => {
    const { taskId } = useParams();
    const location = useLocation();
    const navigate = useNavigate();
    
    const [data, setData] = useState(location.state?.notes || null);
    const [messages, setMessages] = useState([]);
    const [currentQuestion, setCurrentQuestion] = useState('');
    const [isChatting, setIsChatting] = useState(false);
    const chatEndRef = useRef(null);

    useEffect(() => {
        if (!data && taskId) {
            axios.get(`${API_BASE}/status/${taskId}`)
                .then(res => {
                    if (res.data.status === 'completed') {
                        setData(res.data);
                    } else {
                        navigate(`/process/${taskId}`);
                    }
                })
                .catch(() => navigate('/'));
        }
    }, [taskId, data, navigate]);

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isChatting]);

    const handleSendMessage = async (e) => {
        e.preventDefault();
        if (!currentQuestion.trim() || isChatting || !data) return;

        const userMsg = { id: Date.now(), role: 'user', text: currentQuestion };
        setMessages(prev => [...prev, userMsg]);
        const question = currentQuestion;
        setCurrentQuestion('');
        setIsChatting(true);

        try {
            const res = await axios.post(`${API_BASE}/chat`, {
                task_id: taskId,
                question: question
            });
            const botMsg = { id: Date.now() + 1, role: 'assistant', text: res.data.answer };
            setMessages(prev => [...prev, botMsg]);
        } catch {
            setMessages(prev => [...prev, { 
                id: Date.now() + 1, 
                role: 'assistant', 
                text: "Sorry, I encountered an error connecting to the RAG engine." 
            }]);
        } finally {
            setIsChatting(false);
        }
    };

    if (!data) return null;

    return (
            <div className="space-y-6">
                <div className="app-hero rounded-[36px] p-6 sm:p-8">
                    <div className="relative z-10 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                        <div className="space-y-3">
                            <div className="app-kicker">Completed run</div>
                            <h2 className="app-display text-[clamp(2.3rem,3vw,4rem)]">{data.video_title || 'Generated notes'}</h2>
                            <p className="app-lead max-w-3xl">
                                Review the note structure, export options, study assets, and grounded chat in one workspace.
                            </p>
                        </div>
                        <div className="app-chip app-chip--solid w-fit">Task {taskId}</div>
                    </div>
                </div>

                <NotesWorkspace
                    data={{ ...data, task_id: taskId, url: location.state?.url || data.url }}
                    messages={messages}
                    currentQuestion={currentQuestion}
                    setCurrentQuestion={setCurrentQuestion}
                    onSendMessage={handleSendMessage}
                    isChatting={isChatting}
                    chatEndRef={chatEndRef}
                />
            </div>
    );
};

export default ResultView;
