import { create } from 'zustand';
import { persist } from 'zustand/middleware';

const applyThemeToDOM = (theme) => {
  if (typeof document !== 'undefined') {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }
};

export const useSettingsStore = create(
  persist(
    (set) => ({
      theme: 'light',
      engineeringUnits: 'metric', // metric or imperial
      language: 'en',
      notificationsEnabled: true,
      
      setTheme: (theme) => {
        applyThemeToDOM(theme);
        set({ theme });
      },
      setEngineeringUnits: (units) => set({ engineeringUnits: units }),
      setLanguage: (lang) => set({ language: lang }),
      toggleNotifications: () => set((state) => ({ notificationsEnabled: !state.notificationsEnabled })),
    }),
    {
      name: 'engineering-settings-storage',
      onRehydrateStorage: () => (state) => {
        if (state && state.theme) {
          applyThemeToDOM(state.theme);
        }
      }
    }
  )
);
