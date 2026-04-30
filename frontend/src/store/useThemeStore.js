import { create } from 'zustand';

/**
 * Theme is now hardcoded to 'light' as per user request.
 */
function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
}

const useThemeStore = create((set, get) => ({
  theme: 'light',

  toggleTheme: () => {
    // Theme toggle is disabled
  },

  setTheme: (theme) => {
    applyTheme('light');
    set({ theme: 'light' });
  },

  loadTheme: () => {
    applyTheme('light');
    set({ theme: 'light' });
    return () => {}; // No cleanup needed
  },
}));

export default useThemeStore;
