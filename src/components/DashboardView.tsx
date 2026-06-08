import { format } from 'date-fns';
import { useLiveQuery } from 'dexie-react-hooks';
import { db } from '../lib/db';
import { Mic2, Calendar, FileText, Plus, Bell, CheckCircle2, Circle, History, ArrowRight } from 'lucide-react';

export default function DashboardView({ onStartMeeting }: { onStartMeeting: () => void }) {
  const targetDayKey = format(new Date(), 'yyyy-MM-dd');

  // Query tasks for today and any incomplete tasks from the past
  const todayTasks = useLiveQuery(async () => {
    const allTasks = await db.tasks.toArray();
    return allTasks.filter(t => {
      if (t.dayKey < targetDayKey) {
        if (!t.completed) return true;
        if (t.completedAt && format(t.completedAt, 'yyyy-MM-dd') === targetDayKey) return true;
        return false;
      }
      return t.dayKey === targetDayKey;
    }).sort((a, b) => a.createdAt - b.createdAt);
  }, [targetDayKey]) || [];

  const meetingsList = useLiveQuery(() => 
    db.meetings.orderBy('createdAt').reverse().limit(5).toArray()
  ) || [];

  const toggleTask = async (id: string, currentlyCompleted: boolean) => {
    await db.tasks.update(id, {
      completed: !currentlyCompleted,
      completedAt: !currentlyCompleted ? Date.now() : undefined
    });
  };

  return (
    <div className="space-y-8 animate-in fade-in zoom-in-95 duration-300">
      <header className="flex justify-between items-end">
        <div>
          <h2 className="text-3xl font-semibold tracking-tight text-white">Good Morning</h2>
          <p className="text-slate-400 mt-1">Here is what's on your agenda today, {format(new Date(), 'EEEE, MMMM do')}.</p>
        </div>
        <button 
          onClick={onStartMeeting}
          className="bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-lg font-medium flex items-center gap-2 transition-colors focus:ring-2 ring-indigo-500/50 outline-none shadow-lg shadow-indigo-900/20"
        >
          <Mic2 size={18} />
          Record Meeting
        </button>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Today's Focus Action Items */}
        <div className="md:col-span-2 space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm">
            <div className="flex justify-between items-center mb-6">
              <h3 className="font-medium text-lg text-slate-200 flex items-center gap-2">
                <CheckCircle2 className="text-indigo-400" size={20} />
                Today's Action Items
              </h3>
              <span className="text-xs font-medium px-2.5 py-1 bg-slate-800 text-slate-300 rounded-full">
                {todayTasks.filter(t => t.completed).length} / {todayTasks.length} Done
              </span>
            </div>

            {todayTasks.length === 0 ? (
              <div className="text-center py-8 text-slate-500 border border-dashed border-slate-800 rounded-xl">
                <p>No action items scheduled for today.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {todayTasks.map(task => {
                  const isCarriedOver = task.dayKey < targetDayKey;
                  return (
                    <div key={task.id} className="flex gap-3 p-3 hover:bg-slate-800/50 rounded-xl transition-colors group">
                      <button 
                        onClick={() => toggleTask(task.id, task.completed)}
                        className="mt-0.5 text-slate-500 hover:text-indigo-400 transition-colors"
                      >
                        {task.completed ? <CheckCircle2 className="text-indigo-400" size={18} /> : <Circle size={18} />}
                      </button>
                      <div>
                        <p className={`text-sm ${task.completed ? 'text-slate-500 line-through' : 'text-slate-200'}`}>
                          {task.title}
                        </p>
                        <div className="flex gap-2 mt-1">
                          {isCarriedOver && (
                            <span className="flex items-center gap-1 text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-orange-500/10 text-orange-400">
                              Carried Over
                            </span>
                          )}
                          <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                            {task.priority || 'Medium'}
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
            <button className="w-full mt-4 py-2 border border-dashed border-slate-700 text-slate-400 rounded-xl text-sm font-medium hover:text-slate-200 hover:border-slate-600 hover:bg-slate-800/30 transition-colors flex items-center justify-center gap-2">
              <Plus size={16} /> Quick Add Task
            </button>
          </div>
        </div>

        {/* Recent Meetings Side Panel */}
        <div className="space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-sm">
            <h3 className="font-medium text-lg text-slate-200 flex items-center gap-2 mb-6">
              <History className="text-slate-400" size={20} />
              Recent Meetings
            </h3>
            
            {meetingsList.length === 0 ? (
              <div className="text-center py-6 text-slate-500">
                <p className="text-sm">No recent meetings logs found.</p>
              </div>
            ) : (
               <div className="space-y-4">
                 {meetingsList.map(meeting => (
                   <div key={meeting.id} className="group cursor-pointer">
                     <p className="text-sm font-medium text-slate-200 group-hover:text-indigo-400 transition-colors">{meeting.title}</p>
                     <div className="flex items-center gap-2 text-xs text-slate-500 mt-1">
                       <Calendar size={12} />
                       {format(meeting.createdAt, 'MMM do, h:mm a')}
                       <span>•</span>
                       <span>{Math.round(meeting.duration / 60)} min</span>
                     </div>
                   </div>
                 ))}
               </div>
            )}
            
            <button className="w-full mt-6 py-2 bg-slate-800 text-slate-300 rounded-xl text-sm font-medium hover:bg-slate-700 transition-colors">
              View All History
            </button>
          </div>
          
          {/* Status Panel simulating original app telemetry minimal */}
          <div className="bg-slate-900/50 border border-slate-800/50 rounded-2xl p-4 shadow-sm flex items-start gap-3">
             <div className="w-2 h-2 rounded-full bg-emerald-500 mt-1.5 animate-pulse rounded-full shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
             <div>
               <p className="text-sm font-medium text-slate-300">System Ready</p>
               <p className="text-xs text-slate-500 mt-0.5">Microphone and speech engine are available.</p>
             </div>
          </div>
        </div>

      </div>
    </div>
  );
}
