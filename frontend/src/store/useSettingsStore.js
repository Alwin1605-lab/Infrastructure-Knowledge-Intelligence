import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export const useSettingsStore = create(
  persist(
    (set) => ({
      theme: 'light',
      engineeringUnits: 'metric', // metric or imperial
      language: 'en',
      notificationsEnabled: true,
      
      setTheme: (theme) => set({ theme }),
      setEngineeringUnits: (units) => set({ engineeringUnits: units }),
      setLanguage: (lang) => set({ language: lang }),
      toggleNotifications: () => set((state) => ({ notificationsEnabled: !state.notificationsEnabled })),
    }),
    {
      name: 'engineering-settings-storage',
    }
  )
);
