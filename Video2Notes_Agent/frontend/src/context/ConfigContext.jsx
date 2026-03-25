/* eslint-disable react-refresh/only-export-components */
import React, { createContext, useContext, useState, useEffect } from 'react';

const ConfigContext = createContext();

const DEFAULT_CONFIG = {
  provider: 'gemini',
  whisperProvider: 'local',
  whisperModel: 'base',
  language: '',
  detailLevel: 'medium',
  noteStyle: 'study_notes',
  customPromptTemplate: '',
  generateStudyAssets: false,
  keepQa: false,
  keepExamples: true,
  includeTimestamps: true,
  anthropicApiKey: '',
  geminiApiKey: '',
  groqApiKey: '',
  hfToken: '',
  ollamaModel: '',
  ollamaBaseUrl: 'http://localhost:11434',
  startTime: '',
  endTime: '',
  databaseUrl: '',
  playlistProcessingMode: 'parallel',
  playlistWorkerCount: 3,
};

const WHISPER_DEFAULTS = {
  local: 'base',
  groq: 'whisper-large-v3-turbo',
};

export const useConfig = () => useContext(ConfigContext);

export const ConfigProvider = ({ children }) => {
  const [config, setConfig] = useState(() => {
    const saved = localStorage.getItem('video_notes_config');
    return saved ? { ...DEFAULT_CONFIG, ...JSON.parse(saved) } : DEFAULT_CONFIG;
  });

  useEffect(() => {
    localStorage.setItem('video_notes_config', JSON.stringify(config));
  }, [config]);

  const updateConfig = (newConfig) => {
    setConfig((prev) => {
      const next = { ...prev, ...newConfig };
      if (newConfig.whisperProvider && !newConfig.whisperModel) {
        next.whisperModel = WHISPER_DEFAULTS[newConfig.whisperProvider] || prev.whisperModel;
      }
      return next;
    });
  };

  const resetConfig = () => setConfig(DEFAULT_CONFIG);

  return (
    <ConfigContext.Provider value={{ config, updateConfig, resetConfig }}>
      {children}
    </ConfigContext.Provider>
  );
};
