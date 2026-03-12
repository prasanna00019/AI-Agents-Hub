import React from 'react';
import { CheckCircle2, Loader2 } from 'lucide-react';

const steps = [
  { id: 'extraction', label: 'Audio Extraction' },
  { id: 'transcription', label: 'Transcription' },
  { id: 'analysis', label: 'Semantic Analysis' },
  { id: 'synthesis', label: 'Note Synthesis' },
  { id: 'rag', label: 'Knowledge Base' },
];

const ProcessingSteps = ({ currentSteps }) => {
  return (
    <div className="relative flex flex-col gap-6 px-2">
      <div className="absolute bottom-4 left-[21px] top-4 w-px bg-gradient-to-b from-cyan-300 via-slate-200 to-transparent" />
      
      {steps.map((step, index) => {
        const status = currentSteps?.[step.id] || 'pending';
        return (
          <div key={step.id} className="group relative flex items-center gap-6">
            <div className={`relative z-10 flex h-7 w-7 items-center justify-center rounded-full transition-all duration-500 ${
              status === 'completed' ? 'bg-teal-700 shadow-[0_0_15px_rgba(15,118,110,0.25)]' : 
              status === 'active' ? 'scale-110 border border-cyan-300 bg-white shadow-[0_0_0_6px_rgba(34,211,238,0.12)]' : 
              'border border-slate-300 bg-white'
            }`}>
              {status === 'completed' ? (
                <CheckCircle2 className="h-4 w-4 text-white" />
              ) : status === 'active' ? (
                <div className="relative">
                  <div className="absolute inset-0 rounded-full bg-cyan-200 blur-md animate-pulse" />
                  <Loader2 className="relative z-10 h-3.5 w-3.5 animate-spin text-cyan-700" />
                </div>
              ) : (
                <div className="h-1.5 w-1.5 rounded-full bg-slate-400 transition-colors group-hover:bg-slate-500" />
              )}
            </div>
            
            <div className="flex flex-col">
              <span className={`text-xs font-black uppercase tracking-[0.2em] transition-all duration-500 ${
                status === 'completed' ? 'text-slate-500' : 
                status === 'active' ? 'text-cyan-700 animate-pulse' : 'text-slate-500'
              }`}>
                {step.label}
              </span>
              <span className="text-[10px] font-medium text-slate-400 transition-colors group-hover:text-slate-500">
                {status === 'completed' ? 'Completed Successfully' : 
                 status === 'active' ? 'Processing current step...' : 
                 'Waiting for previous step'}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default ProcessingSteps;
