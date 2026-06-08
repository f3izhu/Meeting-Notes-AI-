import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AppState {
  micDevice: string;
  setMicDevice: (id: string) => void;
  // Visual preference or any non-database states can be added here
}

export const useStore = create<AppState>()(
  persist(
    (set) => ({
      micDevice: 'default',
      setMicDevice: (id) => set({ micDevice: id }),
    }),
    {
      name: 'notes-ai-settings',
    }
  )
);

