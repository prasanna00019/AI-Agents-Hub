import React from 'react';
import { X } from 'lucide-react';

const Modal = ({ open, onClose, title, children, widthClass = 'max-w-5xl' }) => {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center px-4 py-8">
      <button
        type="button"
        aria-label="Close modal overlay"
        className="absolute inset-0 bg-black/45 backdrop-blur-sm"
        onClick={onClose}
      />
      <div className={`relative z-10 max-h-[90vh] w-full overflow-hidden rounded-[30px] app-card-strong ${widthClass}`}>
        <div className="flex items-center justify-between border-b px-6 py-5" style={{ borderColor: 'var(--border)' }}>
          <h3 className="text-xl font-black app-title">{title}</h3>
          <button type="button" onClick={onClose} className="inline-flex h-11 w-11 items-center justify-center rounded-2xl app-card">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="max-h-[calc(90vh-84px)] overflow-y-auto px-6 py-6">
          {children}
        </div>
      </div>
    </div>
  );
};

export default Modal;
