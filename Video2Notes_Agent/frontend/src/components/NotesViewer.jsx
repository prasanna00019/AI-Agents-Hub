import React, { useState } from 'react';
import { Download, FileText, GraduationCap, Layers3, Settings2 } from 'lucide-react';
import MarkdownRenderer from './MarkdownRenderer';
import Modal from './Modal';

const ExportToggle = ({ label, checked, onChange, disabled = false }) => (
  <label className="flex items-center gap-3 rounded-2xl px-4 py-3 app-surface-strong">
    <input type="checkbox" checked={checked} disabled={disabled} onChange={(event) => onChange(event.target.checked)} className="h-4 w-4" />
    <span className="text-sm font-semibold app-title">{label}</span>
  </label>
);

const hasStudyAssets = (studyAssets) => {
  if (!studyAssets) return false;
  return Boolean(
    (studyAssets.flashcards || []).length
    || (studyAssets.quiz || []).length
    || (studyAssets.glossary || []).length
    || (studyAssets.revision_sheet || '').trim()
  );
};

const StudyAssetsPanel = ({ studyAssets, activeTab, setActiveTab }) => {
  const tabs = [
    { id: 'flashcards', label: 'Flashcards' },
    { id: 'quiz', label: 'Quiz' },
    { id: 'revision', label: 'Revision' },
    { id: 'glossary', label: 'Glossary' },
  ];

  const renderTab = () => {
    if (activeTab === 'flashcards') {
      return (
        <div className="grid gap-3 md:grid-cols-2">
          {(studyAssets?.flashcards || []).map((card, index) => (
            <div key={`${card.front}-${index}`} className="rounded-2xl p-4 app-soft">
              <p className="text-sm font-semibold app-title">{card.front}</p>
              <p className="mt-2 text-sm app-muted">{card.back}</p>
            </div>
          ))}
        </div>
      );
    }
    if (activeTab === 'quiz') {
      return (
        <div className="space-y-3">
          {(studyAssets?.quiz || []).map((item, index) => (
            <details key={`${item.question}-${index}`} className="rounded-2xl p-4 app-soft">
              <summary className="cursor-pointer text-sm font-semibold app-title">{item.question}</summary>
              <p className="mt-2 text-sm app-muted">{item.answer}</p>
            </details>
          ))}
        </div>
      );
    }
    if (activeTab === 'revision') {
      return (
        <div className="rounded-2xl p-4 app-soft">
          <MarkdownRenderer content={studyAssets?.revision_sheet || ''} />
        </div>
      );
    }
    return (
      <div className="grid gap-3 md:grid-cols-2">
        {(studyAssets?.glossary || []).map((item, index) => (
          <div key={`${item.term}-${index}`} className="rounded-2xl p-4 app-soft">
            <p className="text-sm font-semibold app-title">{item.term}</p>
            <p className="mt-2 text-sm app-muted">{item.definition}</p>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-2">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={`rounded-full px-4 py-2 text-sm font-semibold ${activeTab === tab.id ? 'app-primary-btn' : 'app-card-strong'}`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {renderTab()}
    </div>
  );
};

const NotesViewer = ({
  videoTitle,
  videoDescription,
  notes,
  noteStyle,
  studyAssets,
  exportFormat,
  setExportFormat,
  exportTemplate,
  setExportTemplate,
  includeNotes,
  setIncludeNotes,
  includeDescription,
  setIncludeDescription,
  includeStudyAssets,
  setIncludeStudyAssets,
  appliedSettings,
  onExport,
}) => {
  const [showStudyAssets, setShowStudyAssets] = useState(false);
  const [activeAssetTab, setActiveAssetTab] = useState('flashcards');

  return (
    <div className="lg:col-span-8 flex min-w-0 flex-col gap-6">
      <section className="rounded-[34px] p-6 sm:p-8 app-card">
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
          <div className="min-w-0">
            <div className="mb-4 flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl text-white shadow-sm" style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-2))' }}>
                <FileText className="h-5 w-5" />
              </div>
              <div>
                <p className="app-eyebrow">Notes</p>
                <h2 className="mt-1 break-words text-3xl font-black app-title">{videoTitle}</h2>
              </div>
            </div>

            <div className="mb-4 flex flex-wrap items-center gap-2">
              {noteStyle ? <span className="rounded-full px-3 py-1 text-xs font-bold uppercase tracking-[0.18em] app-pill">{noteStyle.replaceAll('_', ' ')}</span> : null}
              {hasStudyAssets(studyAssets) ? (
                <button type="button" onClick={() => setShowStudyAssets(true)} className="rounded-full px-3 py-1 text-xs font-bold uppercase tracking-[0.18em] app-pill">
                  study assets
                </button>
              ) : null}
            </div>

            {videoDescription ? (
              <details className="group max-w-4xl rounded-2xl px-4 py-3 text-sm app-soft">
                <summary className="cursor-pointer list-none font-semibold app-title">
                  <span className="inline-flex items-center gap-2">
                    Video description
                    <span className="text-xs font-medium app-muted transition-transform group-open:rotate-180">v</span>
                  </span>
                </summary>
                <p className="mt-3 whitespace-pre-wrap leading-relaxed app-muted">{videoDescription}</p>
              </details>
            ) : null}
          </div>

          <div className="space-y-4 rounded-[28px] p-4 app-soft">
            <div className="flex items-center gap-2">
              <Settings2 className="h-4 w-4" style={{ color: 'var(--accent)' }} />
              <span className="text-xs font-bold uppercase tracking-[0.24em] app-muted">Export options</span>
            </div>
            <select value={exportFormat} onChange={(event) => setExportFormat(event.target.value)} className="field-shell">
              <option value="pdf">PDF (print preview)</option>
              <option value="docx">DOCX</option>
              <option value="html">HTML</option>
              <option value="markdown_notion">Notion Markdown</option>
              <option value="markdown_obsidian">Obsidian Markdown</option>
            </select>
            <select value={exportTemplate} onChange={(event) => setExportTemplate(event.target.value)} className="field-shell">
              <option value="default">Default template</option>
              <option value="academic">Academic template</option>
            </select>
            <div className="grid gap-3">
              <ExportToggle label="Notes" checked={includeNotes} onChange={setIncludeNotes} />
              <ExportToggle label="Video description" checked={includeDescription} onChange={setIncludeDescription} />
              <ExportToggle label="Study assets" checked={includeStudyAssets} onChange={setIncludeStudyAssets} />
            </div>
            <button type="button" onClick={onExport} className="inline-flex w-full items-center justify-center gap-2 rounded-full px-4 py-3 text-sm font-semibold app-primary-btn">
              <Download className="h-4 w-4" />
              Export selected format
            </button>
          </div>
        </div>

        {appliedSettings ? (
          <div className="mt-6 rounded-[24px] p-4 app-soft">
            <p className="text-[11px] font-bold uppercase tracking-[0.24em] app-muted">Applied settings</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <span className="rounded-full px-3 py-1 text-xs font-semibold app-card-strong">{appliedSettings.provider || 'provider'}</span>
              <span className="rounded-full px-3 py-1 text-xs font-semibold app-card-strong">{appliedSettings.whisper_provider || 'whisper'}</span>
              <span className="rounded-full px-3 py-1 text-xs font-semibold app-card-strong">{appliedSettings.detail_level || 'detail'}</span>
              <span className="rounded-full px-3 py-1 text-xs font-semibold app-card-strong">{appliedSettings.note_style || 'style'}</span>
              <span className="rounded-full px-3 py-1 text-xs font-semibold app-card-strong">
                {appliedSettings.generate_study_assets ? 'study assets on' : 'study assets off'}
              </span>
              {appliedSettings.custom_prompt_template ? <span className="rounded-full px-3 py-1 text-xs font-semibold app-card-strong">custom prompt enabled</span> : null}
            </div>
          </div>
        ) : null}

        <div className="mt-6 rounded-[30px] p-5 sm:p-7 app-soft">
          <div className="mb-4 flex items-center gap-2">
            <Layers3 className="h-4 w-4" style={{ color: 'var(--accent)' }} />
            <span className="text-xs font-bold uppercase tracking-[0.24em] app-muted">Structured notes</span>
          </div>
          <div className="scrollbar-surface max-h-[72vh] overflow-y-auto pr-2 sm:pr-3">
            <MarkdownRenderer content={notes} />
          </div>
        </div>
      </section>

      <Modal open={showStudyAssets} onClose={() => setShowStudyAssets(false)} title="Study Assets" widthClass="max-w-6xl">
        <div className="mb-5 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl text-white" style={{ background: 'linear-gradient(135deg, var(--accent-2), var(--accent-3))' }}>
            <GraduationCap className="h-5 w-5" />
          </div>
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.28em] app-muted">Study assets</p>
            <h3 className="text-xl font-black app-title">Flashcards, quiz, revision, glossary</h3>
          </div>
        </div>
        <StudyAssetsPanel studyAssets={studyAssets} activeTab={activeAssetTab} setActiveTab={setActiveAssetTab} />
      </Modal>
    </div>
  );
};

export default NotesViewer;
