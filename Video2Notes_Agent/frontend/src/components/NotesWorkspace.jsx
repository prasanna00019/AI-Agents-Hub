import React, { useRef } from 'react';
import ChatSection from './ChatSection';
import NotesViewer from './NotesViewer';

const getYouTubeId = (url) => {
  const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*/;
  const match = url?.match(regExp);
  return match && match[2].length === 11 ? match[2] : null;
};

const attachTimestampLinks = (notes, url) => {
  const videoId = getYouTubeId(url || '');
  if (!videoId || !notes) {
    return notes || '';
  }

  return notes.replace(/\[(\d{1,2}):(\d{2})\]/g, (match, mins, secs) => {
    const totalSeconds = Number.parseInt(mins, 10) * 60 + Number.parseInt(secs, 10);
    const link = `https://www.youtube.com/watch?v=${videoId}&t=${totalSeconds}s`;
    return `[${match}](${link})`;
  });
};

const escapeHtml = (value) =>
  (value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

const PRINT_STYLES = `
  :root {
    color-scheme: light;
    font-family: "Segoe UI", Arial, sans-serif;
  }

  * {
    box-sizing: border-box;
  }

  body {
    margin: 0;
    background: #ffffff;
    color: #111827;
    font-family: "Segoe UI", Arial, sans-serif;
  }

  .print-shell {
    max-width: 960px;
    margin: 0 auto;
    padding: 36px 40px 48px;
  }

  .print-shell h1 {
    margin: 0 0 12px;
    font-size: 32px;
    line-height: 1.15;
  }

  .print-description {
    margin: 0 0 24px;
    color: #475569;
    font-size: 14px;
    line-height: 1.7;
  }

  .print-toolbar {
    position: sticky;
    top: 0;
    z-index: 10;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    margin: 0 0 20px;
    padding: 14px 18px;
    border: 1px solid #dbe3ea;
    border-radius: 16px;
    background: rgba(248, 250, 252, 0.96);
    backdrop-filter: blur(8px);
  }

  .print-toolbar p {
    margin: 0;
    color: #475569;
    font-size: 13px;
    line-height: 1.6;
  }

  .print-toolbar button {
    border: 0;
    border-radius: 999px;
    background: #0f172a;
    color: #ffffff;
    padding: 10px 16px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
  }

  .print-toolbar button:hover {
    background: #1e293b;
  }

  .markdown-body {
    color: #111827;
    font-size: 14px;
    line-height: 1.8;
  }

  .markdown-body h1,
  .markdown-body h2,
  .markdown-body h3,
  .markdown-body h4 {
    color: #111827;
    line-height: 1.2;
    margin: 1.4em 0 0.65em;
  }

  .markdown-body h1 { font-size: 30px; }
  .markdown-body h2 {
    font-size: 24px;
    padding-bottom: 6px;
    border-bottom: 1px solid #dbe3ea;
  }
  .markdown-body h3 { font-size: 18px; }

  .markdown-body p,
  .markdown-body ul,
  .markdown-body ol,
  .markdown-body blockquote,
  .markdown-body pre,
  .markdown-body table {
    margin: 0 0 14px;
  }

  .markdown-body ul,
  .markdown-body ol {
    padding-left: 20px;
  }

  .markdown-body strong {
    font-weight: 700;
    color: #0f172a;
  }

  .markdown-body a {
    color: #0f766e;
    text-decoration: none;
    border-bottom: 1px solid rgba(15, 118, 110, 0.24);
  }

  .markdown-body blockquote {
    border-left: 4px solid #0f766e;
    background: #f8fafc;
    padding: 12px 14px;
  }

  .markdown-body pre {
    white-space: pre-wrap;
    background: #0f172a;
    color: #e2e8f0;
    border-radius: 12px;
    padding: 14px;
    overflow: hidden;
  }

  .markdown-body :not(pre) > code {
    background: #eef2f7;
    border-radius: 6px;
    padding: 2px 6px;
  }

  .markdown-body table {
    width: 100%;
    border-collapse: collapse;
  }

  .markdown-body th,
  .markdown-body td {
    border: 1px solid #dbe3ea;
    padding: 8px 10px;
    text-align: left;
  }

  @page {
    margin: 12mm;
    size: A4;
  }
`;

const NotesWorkspace = ({
  data,
  messages,
  currentQuestion,
  setCurrentQuestion,
  onSendMessage,
  isChatting,
  chatEndRef,
}) => {
  const exportRef = useRef(null);
  const renderedNotes = attachTimestampLinks(data?.notes, data?.url);

  const downloadMarkdown = () => {
    const element = document.createElement('a');
    const file = new Blob([data?.notes || ''], { type: 'text/markdown;charset=utf-8' });
    element.href = URL.createObjectURL(file);
    element.download = `${data?.video_title || 'notes'}.md`;
    document.body.appendChild(element);
    element.click();
    element.remove();
    URL.revokeObjectURL(element.href);
  };

  const downloadPDF = async () => {
    if (!exportRef.current) {
      return;
    }

    const title = data?.video_title || 'Notes';
    const description = data?.video_description
      ? `<p class="print-description">${escapeHtml(data.video_description)}</p>`
      : '';

    const html = `
      <!doctype html>
      <html>
        <head>
          <meta charset="utf-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1" />
          <title>${escapeHtml(title)}</title>
          <style>${PRINT_STYLES}</style>
        </head>
        <body>
          <div class="print-shell">
            <div class="print-toolbar">
              <p>Use your browser print dialog and choose <strong>Save as PDF</strong>.</p>
              <button type="button" onclick="window.print()">Print / Save PDF</button>
            </div>
            <h1>${escapeHtml(title)}</h1>
            ${description}
            ${exportRef.current.innerHTML}
          </div>
        </body>
      </html>
    `;

    const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
    const blobUrl = URL.createObjectURL(blob);
    const previewWindow = window.open(blobUrl, '_blank');

    if (!previewWindow) {
      URL.revokeObjectURL(blobUrl);
      return;
    }

    previewWindow.focus();
    setTimeout(() => URL.revokeObjectURL(blobUrl), 60_000);
  };

  return (
    <div className="grid items-start gap-6 lg:grid-cols-12">
      <NotesViewer
        videoTitle={data?.video_title}
        videoDescription={data?.video_description}
        notes={renderedNotes}
        onDownloadMarkdown={downloadMarkdown}
        onDownloadPDF={downloadPDF}
        exportRef={exportRef}
      />
      <ChatSection
        messages={messages}
        currentQuestion={currentQuestion}
        setCurrentQuestion={setCurrentQuestion}
        onSendMessage={onSendMessage}
        isChatting={isChatting}
        chatEndRef={chatEndRef}
        taskId={data?.task_id}
      />
    </div>
  );
};

export default NotesWorkspace;