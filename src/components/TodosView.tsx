import React, { useState } from 'react';
import { format, addDays, subDays } from 'date-fns';
import { useLiveQuery } from 'dexie-react-hooks';
import { db, DbTask } from '../lib/db';
import { CheckCircle2, Circle, ChevronLeft, ChevronRight, Calendar, Plus, Trash2 } from 'lucide-react';
import { cn } from '../lib/utils';

export default function TodosView() {
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [newTaskTitle, setNewTaskTitle] = useState('');
  
  const dayKey = format(selectedDate, 'yyyy-MM-dd');
  
  // Use dexie to query tasks with the carry-forward logic
  const dayTasks = useLiveQuery(async () => {
    const allTasks = await db.tasks.toArray();
    return allTasks.filter(t => {
      if (t.dayKey < dayKey) {
        if (!t.completed) return true;
        if (t.completedAt && format(t.completedAt, 'yyyy-MM-dd') === dayKey) return true;
        return false;
      }
      return t.dayKey === dayKey;
    }).sort((a, b) => a.createdAt - b.createdAt);
  }, [dayKey]) || [];

  const handleNextDay = () => setSelectedDate(addDays(selectedDate, 1));
  const handlePrevDay = () => setSelectedDate(subDays(selectedDate, 1));
  const handleToday = () => setSelectedDate(new Date());

  const handleAddTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTaskTitle.trim()) return;
    
    await db.tasks.add({
      id: Math.random().toString(36).substring(2, 9),
      title: newTaskTitle.trim(),
      completed: false,
      priority: 'medium',
      createdAt: Date.now(),
      dueDate: selectedDate.getTime(),
      dayKey,
    });
    
    setNewTaskTitle('');
  };

  const toggleTask = async (id: string, currentlyCompleted: boolean) => {
    await db.tasks.update(id, {
      completed: !currentlyCompleted,
      completedAt: !currentlyCompleted ? Date.now() : undefined
    });
  };

  const deleteTask = async (id: string) => {
    await db.tasks.delete(id);
  };


  return (
    <div className="h-full flex flex-col animate-in fade-in zoom-in-95 duration-300">
      <header className="mb-8 flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-white mb-2">Daily Todos</h2>
          <div className="flex items-center gap-1 bg-slate-900 border border-slate-800 rounded-lg p-1 w-fit">
            <button 
              onClick={handlePrevDay}
              className="p-1.5 hover:bg-slate-800 rounded-md text-slate-400 hover:text-slate-200 transition-colors"
            >
              <ChevronLeft size={18} />
            </button>
            <button 
              onClick={handleToday}
              className="px-3 py-1.5 text-sm font-medium hover:bg-slate-800 rounded-md flex items-center gap-2 text-slate-300 hover:text-slate-100 transition-colors"
            >
              <Calendar size={14} />
              {format(selectedDate, 'MMM do, yyyy')}
            </button>
            <button 
              onClick={handleNextDay}
              className="p-1.5 hover:bg-slate-800 rounded-md text-slate-400 hover:text-slate-200 transition-colors"
            >
              <ChevronRight size={18} />
            </button>
          </div>
        </div>
      </header>

      <div className="flex-1 bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden flex flex-col shadow-sm max-w-3xl">
        <div className="p-4 border-b border-slate-800/60 bg-slate-950/30">
          <form onSubmit={handleAddTask} className="relative flex items-center">
            <Plus className="absolute left-3 text-slate-500" size={18} />
            <input 
              type="text" 
              value={newTaskTitle}
              onChange={(e) => setNewTaskTitle(e.target.value)}
              placeholder="Add a new action item..." 
              className="w-full bg-slate-900 border border-slate-700/50 rounded-xl py-3 pl-10 pr-4 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all shadow-inner"
            />
          </form>
        </div>
        
        <div className="flex-1 overflow-y-auto p-2">
          {dayTasks.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-slate-500 py-12">
              <div className="w-16 h-16 rounded-2xl bg-slate-800/50 flex items-center justify-center mb-4">
                <CheckCircle2 size={24} className="text-slate-700" />
              </div>
              <p className="font-medium text-slate-400">No tasks for this day</p>
              <p className="text-sm mt-1">Add action items manually or extract from meetings.</p>
            </div>
          ) : (
            <ul className="space-y-1">
              {dayTasks.map(task => (
                <li 
                  key={task.id} 
                  className={cn(
                    "flex items-start gap-3 p-3 rounded-xl transition-all group border border-transparent",
                    task.completed ? "bg-slate-900" : "hover:bg-slate-800/50 hover:border-slate-800/50"
                  )}
                >
                  <button 
                    onClick={() => toggleTask(task.id, task.completed)}
                    className="mt-0.5 relative shrink-0"
                  >
                    {task.completed ? (
                      <CheckCircle2 size={20} className="text-indigo-500 scale-100 transition-transform" />
                    ) : (
                      <Circle size={20} className="text-slate-600 hover:text-indigo-400 opacity-100 transition-colors" />
                    )}
                  </button>
                  
                  <div className="flex-1 min-w-0">
                    <p className={cn(
                      "text-sm transition-colors",
                      task.completed ? "text-slate-500 line-through" : "text-slate-200"
                    )}>
                      {task.title}
                    </p>
                    <div className="flex gap-2">
                      {task.dayKey < dayKey && (
                        <span className="inline-block mt-1.5 text-[9px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-orange-500/10 text-orange-400">
                          Carried Over
                        </span>
                      )}
                      {task.priority && !task.completed && (
                        <span className={cn(
                          "inline-block mt-1.5 text-[9px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded",
                          task.priority === 'high' ? "bg-red-500/10 text-red-400" :
                          task.priority === 'medium' ? "bg-amber-500/10 text-amber-400" :
                          "bg-emerald-500/10 text-emerald-400"
                        )}>
                          {task.priority}
                        </span>
                      )}
                    </div>
                  </div>
                  
                  <button 
                    onClick={() => deleteTask(task.id)}
                    className="shrink-0 p-1.5 rounded-md text-slate-600 hover:text-red-400 hover:bg-red-500/10 opacity-0 group-hover:opacity-100 focus:opacity-100 transition-all outline-none"
                    title="Delete task"
                  >
                    <Trash2 size={16} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
