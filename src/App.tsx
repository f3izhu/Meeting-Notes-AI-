/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState } from 'react';
import { 
  Mic2, 
  ListTodo, 
  History, 
  Settings, 
  LayoutDashboard 
} from 'lucide-react';
import { cn } from './lib/utils';
import DashboardView from './components/DashboardView';
import RecordView from './components/RecordView';
import TodosView from './components/TodosView';
import SettingsView from './components/SettingsView';

type ViewState = 'dashboard' | 'record' | 'todos' | 'settings';

export default function App() {
  const [activeView, setActiveView] = useState<ViewState>('dashboard');

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'record', label: 'Record', icon: Mic2 },
    { id: 'todos', label: 'Daily Todos', icon: ListTodo },
    { id: 'settings', label: 'Settings', icon: Settings },
  ] as const;

  return (
    <div className="flex h-screen w-full bg-slate-950 text-slate-200 font-sans selection:bg-indigo-500/30 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 border-r border-slate-800/60 bg-slate-950/50 flex flex-col p-4 space-y-8 relative z-10 backdrop-blur-sm">
        <div className="px-2">
          <h1 className="text-xl font-medium tracking-tight text-white flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-indigo-500/20 text-indigo-400 flex items-center justify-center">
              <Mic2 size={14} />
            </div>
            NotesAI
          </h1>
          <p className="text-xs text-slate-500 mt-1">Local Meeting Assistant</p>
        </div>

        <nav className="flex-1 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeView === item.id;
            
            return (
              <button
                key={item.id}
                onClick={() => setActiveView(item.id)}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all group outline-none",
                  isActive 
                    ? "bg-indigo-500/10 text-indigo-300" 
                    : "text-slate-400 hover:bg-slate-800/40 hover:text-slate-200"
                )}
              >
                <Icon size={18} className={cn(
                  "transition-colors",
                  isActive ? "text-indigo-400" : "text-slate-500 group-hover:text-slate-400"
                )} />
                {item.label}
              </button>
            );
          })}
        </nav>

        {/* Minimal Audio Meter Placeholder for global monitoring (visual only right now) */}
        <div className="mt-auto px-4 py-4 rounded-xl bg-slate-900/50 border border-slate-800/50 space-y-2">
           <div className="flex justify-between items-center text-xs">
              <span className="text-slate-400">Audio Level</span>
              <span className="text-slate-600 font-mono">-100dB</span>
           </div>
           <div className="w-full h-1 bg-slate-800 rounded-full overflow-hidden">
             <div className="h-full w-0 bg-indigo-500/50 rounded-full transition-all duration-75"></div>
           </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 min-w-0 relative bg-slate-950">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(99,102,241,0.05),rgba(255,255,255,0))]"></div>
        
        <div className="relative h-full overflow-y-auto px-8 py-8 w-full max-w-5xl mx-auto">
          {activeView === 'dashboard' && <DashboardView onStartMeeting={() => setActiveView('record')} />}
          {activeView === 'record' && <RecordView />}
          {activeView === 'todos' && <TodosView />}
          {activeView === 'settings' && <SettingsView />}
        </div>
      </main>
    </div>
  );
}

