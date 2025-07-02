import { useState, useEffect } from 'react';
import { isServer, storage } from '../utils/ssr';

export function useTheme() {
  const [darkMode, setDarkMode] = useState(() => {
    if (isServer) return false;
    const savedTheme = storage.getItem('theme');
    return savedTheme ? savedTheme === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    if (isServer) return;
    
    if (darkMode) {
      document.documentElement.classList.add('dark');
      storage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      storage.setItem('theme', 'light');
    }
  }, [darkMode]);

  return { darkMode, setDarkMode };
}