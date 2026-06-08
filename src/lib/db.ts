import Dexie, { type Table } from 'dexie';

export interface DbTask {
  id: string;
  title: string;
  completed: boolean;
  completedAt?: number;
  priority: 'low' | 'medium' | 'high';
  createdAt: number;
  dueDate: number;
  dayKey: string;
}

export interface DbMeeting {
  id: string;
  title: string;
  createdAt: number;
  duration: number; // in seconds
  transcript: string;
  summary: string;
}

export class LocalDatabase extends Dexie {
  tasks!: Table<DbTask, string>;
  meetings!: Table<DbMeeting, string>;

  constructor() {
    super('MeetingNotesAIData');
    this.version(1).stores({
      tasks: 'id, dayKey, completed, dueDate, createdAt',
      meetings: 'id, createdAt'
    });
  }
}

export const db = new LocalDatabase();
