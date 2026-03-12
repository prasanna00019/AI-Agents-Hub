import React, { useRef } from 'react';
import html2pdf from 'html2pdf.js';
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

    await html2pdf()
      .set({
        filename: `${data?.video_title || 'notes'}.pdf`,
        margin: [0.35, 0.35, 0.5, 0.35],
        pagebreak: { mode: ['css', 'legacy'] },
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: {
          scale: 2,
          useCORS: true,
          backgroundColor: '#ffffff',
          logging: false,
        },
        jsPDF: { unit: 'in', format: 'a4', orientation: 'portrait' },
      })
      .from(exportRef.current)
      .save();
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