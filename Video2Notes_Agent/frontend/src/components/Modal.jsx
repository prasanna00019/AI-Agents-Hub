import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';

const Modal = ({ open, onClose, title, children, widthClass = 'max-w-5xl' }) => {
  useEffect(() => {
    if (!open) return undefined;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  if (!open) return null;

  return createPortal(
    <div className="fixed inset-0 z-[1000] flex items-center justify-center px-4 py-8">
      <button
        type="button"
        aria-label="Close modal overlay"
        className="absolute inset-0 z-[1001] bg-black/55 backdrop-blur-md"
        onClick={onClose}
      />
      <div className={`relative z-[1010] max-h-[90vh] w-full overflow-hidden rounded-[32px] app-card-strong ${widthClass}`}>
        <div className="flex items-center justify-between border-b px-6 py-5" style={{ borderColor: 'var(--border)', background: 'linear-gradient(135deg, color-mix(in srgb, var(--card-strong) 96%, white), color-mix(in srgb, var(--card) 92%, white))' }}>
          <div className="space-y-1">
            <p className="app-eyebrow">Studio panel</p>
            <h3 className="text-xl font-black app-gradient-text">{title}</h3>
          </div>
          <button type="button" onClick={onClose} className="inline-flex h-11 w-11 items-center justify-center rounded-2xl app-surface-strong">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="max-h-[calc(90vh-84px)] overflow-y-auto px-6 py-6" style={{ background: 'linear-gradient(180deg, color-mix(in srgb, var(--card) 98%, white), color-mix(in srgb, var(--card-soft) 92%, white))' }}>
          {children}
        </div>
      </div>
    </div>,
    document.body,
  );
};

export default Modal;
