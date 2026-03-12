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

    const printWindow = window.open('', '_blank', 'noopener,noreferrer,width=1100,height=900');
    if (!printWindow) {
      return;
    }

    const title = data?.video_title || 'Notes';
    const description = data?.video_description
      ? `<p class="print-description">${data.video_description.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</p>`
      : '';

    printWindow.document.open();
    printWindow.document.write(`
      <!doctype html>
      <html>
        <head>
          <meta charset="utf-8" />
          <title>${title}</title>
          <style>${PRINT_STYLES}</style>
        </head>
        <body>
          <div class="print-shell">
            <h1>${title}</h1>
            ${description}
            ${exportRef.current.innerHTML}
          </div>
        </body>
      </html>
    `);
    printWindow.document.close();
    printWindow.focus();

    const runPrint = () => {
      printWindow.print();
    };

    if (printWindow.document.readyState === 'complete') {
      runPrint();
    } else {
      printWindow.onload = runPrint;
    }
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