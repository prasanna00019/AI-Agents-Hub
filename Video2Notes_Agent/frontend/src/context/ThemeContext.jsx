/* eslint-disable react-refresh/only-export-components */
import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';

const ThemeContext = createContext();

export const THEME_OPTIONS = [
  { id: 'sunrise', label: 'Sunrise' },
  { id: 'sage', label: 'Sage' },
  { id: 'midnight', label: 'Midnight' },
  { id: 'paper', label: 'Paper' },
];

export const useTheme = () => useContext(ThemeContext);

export const ThemeProvider = ({ children }) => {
  const [theme, setTheme] = useState(() => localStorage.getItem('video_notes_theme') || 'sunrise');

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem('video_notes_theme', theme);
  }, [theme]);

  const value = useMemo(() => ({ theme, setTheme, themes: THEME_OPTIONS }), [theme]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};
