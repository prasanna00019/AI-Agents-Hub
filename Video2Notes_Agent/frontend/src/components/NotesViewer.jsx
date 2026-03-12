import React from 'react';
import { Download, FileCode2, FileText } from 'lucide-react';
import MarkdownRenderer from './MarkdownRenderer';

const NotesViewer = ({ videoTitle, videoDescription, notes, onDownloadMarkdown, onDownloadPDF, exportRef }) => {
  return (
    <>
      <div className="lg:col-span-8 flex min-w-0 flex-col gap-6">
        <section className="rounded-[30px] border border-white/80 bg-[rgba(255,255,255,0.84)] p-6 shadow-[0_24px_70px_rgba(15,23,42,0.08)] backdrop-blur-xl sm:p-8">
          <div className="flex flex-col gap-6 border-b border-slate-200 pb-6 md:flex-row md:items-start md:justify-between">
            <div className="min-w-0 flex-1">
              <div className="mb-4 flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-900 text-white shadow-sm">
                  <FileText className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-[11px] font-bold uppercase tracking-[0.28em] text-slate-500">Notes</p>
                  <h2 className="mt-1 break-words text-3xl font-black text-slate-900">{videoTitle}</h2>
                </div>
              </div>
              {videoDescription ? (
                <details className="group max-w-3xl rounded-2xl border border-slate-200 bg-slate-50/85 px-4 py-3 text-sm text-slate-600">
                  <summary className="cursor-pointer list-none font-semibold text-slate-800">
                    <span className="inline-flex items-center gap-2">
                      Video description
                      <span className="text-xs font-medium text-slate-500 transition-transform group-open:rotate-180">v</span>
                    </span>
                  </summary>
                  <p className="mt-3 whitespace-pre-wrap leading-relaxed text-slate-600">
                    {videoDescription}
                  </p>
                </details>
              ) : null}
            </div>

            <div className="flex shrink-0 flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={onDownloadMarkdown}
                className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-100"
              >
                <FileCode2 className="h-4 w-4 text-cyan-700" />
                Markdown
              </button>
              <button
                type="button"
                onClick={onDownloadPDF}
                className="inline-flex items-center gap-2 rounded-full bg-slate-900 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-slate-800"
              >
                <Download className="h-4 w-4" />
                Save PDF
              </button>
            </div>
          </div>

          <div className="mt-6 rounded-[26px] border border-slate-200 bg-[linear-gradient(180deg,rgba(255,255,255,0.92),rgba(248,250,252,0.96))] p-5 sm:p-7">
            <div className="scrollbar-surface max-h-[70vh] overflow-y-auto pr-2 sm:pr-3">
              <MarkdownRenderer content={notes} />
            </div>
          </div>
        </section>
      </div>

      <div ref={exportRef} className="note-export-sheet">
        <MarkdownRenderer content={notes} variant="print" />
      </div>
    </>
  );
};

export default NotesViewer;
