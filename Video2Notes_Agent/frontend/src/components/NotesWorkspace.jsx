import React, { useState } from 'react';
import axios from 'axios';
import ChatSection from './ChatSection';
import NotesViewer from './NotesViewer';

const API_BASE = 'http://localhost:8000/api';

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
  const [exportFormat, setExportFormat] = useState('pdf');
  const [exportTemplate, setExportTemplate] = useState('default');
  const renderedNotes = attachTimestampLinks(data?.notes, data?.url);

  const handleExport = async () => {
    const response = await axios.post(
      `${API_BASE}/export`,
      {
        title: data?.video_title || 'Notes',
        description: data?.video_description || '',
        notes: data?.notes || '',
        study_assets: data?.study_assets || {},
        format: exportFormat,
        template: exportTemplate,
      },
      {
        responseType: 'blob',
      },
    );

    const blob = new Blob([response.data], { type: response.headers['content-type'] });
    const blobUrl = URL.createObjectURL(blob);

    if (exportFormat === 'pdf') {
      const previewWindow = window.open(blobUrl, '_blank');
      previewWindow?.focus();
      setTimeout(() => URL.revokeObjectURL(blobUrl), 60_000);
      return;
    }

    const disposition = response.headers['content-disposition'] || '';
    const match = disposition.match(/filename="(.+?)"/);
    const filename = match?.[1] || 'notes-export';
    const link = document.createElement('a');
    link.href = blobUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(blobUrl);
  };

  return (
    <div className="grid items-start gap-6 lg:grid-cols-12">
      <NotesViewer
        videoTitle={data?.video_title}
        videoDescription={data?.video_description}
        notes={renderedNotes}
        noteStyle={data?.note_style}
        studyAssets={data?.study_assets}
        exportFormat={exportFormat}
        setExportFormat={setExportFormat}
        exportTemplate={exportTemplate}
        setExportTemplate={setExportTemplate}
        onExport={handleExport}
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
