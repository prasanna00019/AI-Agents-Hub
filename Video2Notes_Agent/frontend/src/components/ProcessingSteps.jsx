import React from 'react';
import { CheckCircle2, Loader2 } from 'lucide-react';

const steps = [
  { id: 'extraction', label: 'Audio Extraction' },
  { id: 'transcription', label: 'Transcription' },
  { id: 'analysis', label: 'Semantic Analysis' },
  { id: 'structuring', label: 'Section Structuring' },
  { id: 'synthesis', label: 'Note Synthesis' },
  { id: 'assets', label: 'Study Assets' },
  { id: 'rag', label: 'Knowledge Base' },
  { id: 'export', label: 'Exports Ready' },
];

const ProcessingSteps = ({ currentSteps }) => {
  return (
    <div className="relative flex flex-col gap-4 px-2 py-1">
      <div className="absolute bottom-4 left-[21px] top-4 w-px" style={{ background: 'linear-gradient(to bottom, color-mix(in srgb, var(--accent-2) 54%, transparent), color-mix(in srgb, var(--border) 80%, transparent), transparent)' }} />

      {steps.map((step) => {
        const status = currentSteps?.[step.id] || 'pending';
        return (
          <div key={step.id} className="group relative flex items-center gap-5 rounded-[24px] border border-transparent px-3 py-3 transition-colors duration-300 hover:border-[color-mix(in_srgb,var(--border)_86%,white)] hover:bg-[color-mix(in_srgb,var(--card-strong)_92%,white)]">
            <div
              className={`relative z-10 flex h-7 w-7 items-center justify-center rounded-full transition-all duration-500 ${
                status === 'completed'
                  ? 'shadow-[0_0_15px_rgba(15,118,110,0.25)]'
                  : status === 'active'
                    ? 'scale-110 border'
                    : 'border'
              }`}
              style={{
                background:
                  status === 'completed'
                    ? 'linear-gradient(135deg, var(--accent), var(--accent-2))'
                    : 'var(--card-strong)',
                borderColor: status === 'active' ? 'color-mix(in srgb, var(--accent-2) 44%, var(--border))' : 'var(--border)',
                boxShadow: status === 'active' ? '0 0 0 6px color-mix(in srgb, var(--accent-2) 12%, transparent)' : undefined,
              }}
            >
              {status === 'completed' ? (
                <CheckCircle2 className="h-4 w-4 text-white" />
              ) : status === 'active' ? (
                <div className="relative">
                  <div className="absolute inset-0 rounded-full blur-md animate-pulse" style={{ background: 'color-mix(in srgb, var(--accent-2) 24%, transparent)' }} />
                  <Loader2 className="relative z-10 h-3.5 w-3.5 animate-spin" style={{ color: 'var(--accent-2)' }} />
                </div>
              ) : (
                <div className="h-1.5 w-1.5 rounded-full" style={{ background: 'color-mix(in srgb, var(--muted) 64%, white)' }} />
              )}
            </div>

            <div className="flex flex-col">
              <span className={`text-xs font-black uppercase tracking-[0.2em] transition-all duration-500 ${status === 'active' ? 'animate-pulse' : ''}`} style={{ color: status === 'active' ? 'var(--accent)' : 'var(--muted)' }}>
                {step.label}
              </span>
              <span className="text-[10px] font-medium transition-colors app-muted">
                {status === 'completed'
                  ? 'Completed successfully'
                  : status === 'active'
                    ? 'Processing current step...'
                    : 'Waiting for previous step'}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default ProcessingSteps;
