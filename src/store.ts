import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { format } from 'date-fns';

export interface Task {
  id: string;
  title: string;
  completed: boolean;
  completedAt?: number;
  priority: 'low' | 'medium' | 'high';
  createdAt: number;
  dueDate: number;
}

export interface Meeting {
  id: string;
  title: string;
  createdAt: number;
  duration: number; // in seconds
  transcript: string;
  summary: string;
  actionItems: Task[];
}

interface AppState {
  tasks: Record<string, Task[]>; // Keyed by year-month-day string e.g. "2024-02-14"
  meetings: Record<string, Meeting>;
  
  // State mutations
  addTask: (dayKey: string, task: Task) => void;
  toggleTask: (dayKey: string, taskId: string) => void;
  deleteTask: (dayKey: string, taskId: string) => void;
  saveMeeting: (meeting: Meeting) => void;
  
  // Preferences
  micDevice: string;
  setMicDevice: (id: string) => void;
}

export function getTasksForDate(tasks: Record<string, Task[]>, targetDate: Date) {
  const targetDayKey = format(targetDate, 'yyyy-MM-dd');
  const result: (Task & { originalDayKey: string; isCarriedOver: boolean })[] = [];

  for (const [dayKey, dayTasks] of Object.entries(tasks)) {
    if (dayKey < targetDayKey) {
      for (const t of dayTasks) {
        if (!t.completed) {
          result.push({ ...t, originalDayKey: dayKey, isCarriedOver: true });
        } else if (t.completedAt && format(t.completedAt, 'yyyy-MM-dd') === targetDayKey) {
          result.push({ ...t, originalDayKey: dayKey, isCarriedOver: true });
        }
      }
    } else if (dayKey === targetDayKey) {
      for (const t of dayTasks) {
        result.push({ ...t, originalDayKey: dayKey, isCarriedOver: false });
      }
    }
  }

  return result.sort((a, b) => a.createdAt - b.createdAt);
}

export const useStore = create<AppState>()(
  persist(
    (set) => ({
      tasks: {},
      meetings: {},
      
      addTask: (dayKey, task) => set((state) => {
        const dayTasks = state.tasks[dayKey] || [];
        return {
          tasks: {
            ...state.tasks,
            [dayKey]: [...dayTasks, task]
          }
        };
      }),
      
      toggleTask: (dayKey, taskId) => set((state) => {
        const dayTasks = state.tasks[dayKey] || [];
        return {
          tasks: {
            ...state.tasks,
            [dayKey]: dayTasks.map(t => 
              t.id === taskId ? { 
                ...t, 
                completed: !t.completed,
                completedAt: !t.completed ? Date.now() : undefined
              } : t
            )
          }
        };
      }),
      
      deleteTask: (dayKey, taskId) => set((state) => {
        const dayTasks = state.tasks[dayKey] || [];
        return {
          tasks: {
            ...state.tasks,
            [dayKey]: dayTasks.filter(t => t.id !== taskId)
          }
        };
      }),
      
      saveMeeting: (meeting) => set((state) => ({
        meetings: {
          ...state.meetings,
          [meeting.id]: meeting
        }
      })),
      
      micDevice: 'default',
      setMicDevice: (id) => set({ micDevice: id }),
    }),
    {
      name: 'meeting-notes-ai-storage',
    }
  )
);
