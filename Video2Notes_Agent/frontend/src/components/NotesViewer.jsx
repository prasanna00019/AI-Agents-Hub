import React from 'react';
import { Download, FileText, GraduationCap, Layers3 } from 'lucide-react';
import MarkdownRenderer from './MarkdownRenderer';

const StudyAssets = ({ studyAssets }) => {
  if (!studyAssets) return null;

  return (
    <section className="mt-6 rounded-[26px] p-5 sm:p-7 app-soft">
      <div className="mb-5 flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl text-white" style={{ background: 'linear-gradient(135deg, var(--accent-2), var(--accent-3))' }}>
          <GraduationCap className="h-5 w-5" />
        </div>
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.28em] app-muted">Study assets</p>
          <h3 className="text-xl font-black app-title">Flashcards, quiz, glossary</h3>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-[22px] p-4 app-card-strong">
          <h4 className="text-sm font-bold uppercase tracking-[0.2em] app-muted">Flashcards</h4>
          <div className="mt-3 space-y-3">
            {(studyAssets.flashcards || []).slice(0, 6).map((card, index) => (
              <div key={`${card.front}-${index}`} className="rounded-2xl p-3 app-soft">
                <p className="text-sm font-semibold app-title">{card.front}</p>
                <p className="mt-2 text-sm app-muted">{card.back}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-[22px] p-4 app-card-strong">
          <h4 className="text-sm font-bold uppercase tracking-[0.2em] app-muted">Quiz</h4>
          <div className="mt-3 space-y-3">
            {(studyAssets.quiz || []).slice(0, 5).map((item, index) => (
              <details key={`${item.question}-${index}`} className="rounded-2xl p-3 app-soft">
                <summary className="cursor-pointer text-sm font-semibold app-title">{item.question}</summary>
                <p className="mt-2 text-sm app-muted">{item.answer}</p>
              </details>
            ))}
          </div>
        </div>

        <div className="rounded-[22px] p-4 app-card-strong">
          <h4 className="text-sm font-bold uppercase tracking-[0.2em] app-muted">Revision Sheet</h4>
          <div className="mt-3 max-h-80 overflow-y-auto pr-2">
            <MarkdownRenderer content={studyAssets.revision_sheet || ''} compact />
          </div>
        </div>

        <div className="rounded-[22px] p-4 app-card-strong">
          <h4 className="text-sm font-bold uppercase tracking-[0.2em] app-muted">Glossary</h4>
          <div className="mt-3 space-y-3">
            {(studyAssets.glossary || []).slice(0, 10).map((item, index) => (
              <div key={`${item.term}-${index}`} className="rounded-2xl p-3 app-soft">
                <p className="text-sm font-semibold app-title">{item.term}</p>
                <p className="mt-1 text-sm app-muted">{item.definition}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
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
  onExport,
}) => {
  return (
    <div className="lg:col-span-8 flex min-w-0 flex-col gap-6">
      <section className="rounded-[30px] p-6 sm:p-8 app-card">
        <div className="flex flex-col gap-6 border-b pb-6 md:flex-row md:items-start md:justify-between" style={{ borderColor: 'var(--border)' }}>
          <div className="min-w-0 flex-1">
            <div className="mb-4 flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl text-white shadow-sm" style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-2))' }}>
                <FileText className="h-5 w-5" />
              </div>
              <div>
                <p className="text-[11px] font-bold uppercase tracking-[0.28em] app-muted">Notes</p>
                <h2 className="mt-1 break-words text-3xl font-black app-title">{videoTitle}</h2>
              </div>
            </div>
            <div className="mb-4 flex flex-wrap items-center gap-2">
              {noteStyle ? <span className="rounded-full px-3 py-1 text-xs font-bold uppercase tracking-[0.18em] app-pill">{noteStyle.replaceAll('_', ' ')}</span> : null}
              {studyAssets ? <span className="rounded-full px-3 py-1 text-xs font-bold uppercase tracking-[0.18em] app-pill">study assets ready</span> : null}
            </div>
            {videoDescription ? (
              <details className="group max-w-3xl rounded-2xl px-4 py-3 text-sm app-soft">
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

          <div className="flex shrink-0 flex-col gap-2 md:w-72">
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
            <button type="button" onClick={onExport} className="inline-flex items-center justify-center gap-2 rounded-full px-4 py-3 text-sm font-semibold app-primary-btn">
              <Download className="h-4 w-4" />
              Export selected format
            </button>
          </div>
        </div>

        <div className="mt-6 rounded-[26px] p-5 sm:p-7 app-soft">
          <div className="mb-4 flex items-center gap-2">
            <Layers3 className="h-4 w-4" style={{ color: 'var(--accent)' }} />
            <span className="text-xs font-bold uppercase tracking-[0.24em] app-muted">Structured notes</span>
          </div>
          <div className="scrollbar-surface max-h-[70vh] overflow-y-auto pr-2 sm:pr-3">
            <MarkdownRenderer content={notes} />
          </div>
        </div>

        <StudyAssets studyAssets={studyAssets} />
      </section>
    </div>
  );
};

export default NotesViewer;
