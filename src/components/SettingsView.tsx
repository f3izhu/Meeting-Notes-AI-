import { useStore } from '../store';
import { Settings, Shield, HardDrive, Cpu, Mic2, Download } from 'lucide-react';

export default function SettingsView() {
  const { micDevice, setMicDevice } = useStore();

  return (
    <div className="h-full flex flex-col animate-in fade-in zoom-in-95 duration-300 max-w-4xl">
      <header className="mb-8">
        <h2 className="text-2xl font-semibold tracking-tight text-white">App Settings</h2>
        <p className="text-slate-400 mt-1 text-sm">Configure AI models, storage, and audio devices.</p>
      </header>

      <div className="space-y-6">
        
        {/* Device Settings */}
        <section className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
          <div className="flex items-center gap-2 mb-6">
            <Mic2 className="text-indigo-400" size={20} />
            <h3 className="text-lg font-medium text-slate-200">Audio Devices</h3>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="text-sm font-medium text-slate-400 block mb-2">Default Microphone</label>
              <select 
                value={micDevice}
                onChange={(e) => setMicDevice(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-300 py-3 px-4 outline-none focus:border-indigo-500 transition-colors"
              >
                <option value="default">Default System Audio Interface</option>
                <option value="loopback">Windows WASAPI Loopback (Speakers)</option>
              </select>
              <p className="text-xs text-slate-500 mt-2">Use loopback strictly for capturing online meetings (Zoom, Teams, etc).</p>
            </div>
          </div>
        </section>

        {/* AI Inference Settings */}
        <section className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
          <div className="flex items-center gap-2 mb-6">
            <Cpu className="text-emerald-400" size={20} />
            <h3 className="text-lg font-medium text-slate-200">Processing Engine (Transcription & Summary)</h3>
          </div>
          
          <div className="space-y-4 max-w-2xl">
            <div className="flex items-start gap-4 p-4 rounded-xl border border-indigo-500/30 bg-indigo-500/5 cursor-pointer hover:bg-indigo-500/10 transition-colors">
               <div className="w-5 h-5 rounded-full border-4 border-indigo-500 bg-slate-950 mt-0.5 shrink-0"></div>
               <div>
                 <h4 className="font-medium text-slate-200">Cloud Intelligence (Gemini API)</h4>
                 <p className="text-sm text-slate-400 mt-1">High-quality transcription and detailed summaries powered by Gemini. Fastest inference with highest accuracy.</p>
               </div>
            </div>
            
            <div className="flex items-start gap-4 p-4 rounded-xl border border-slate-800 bg-slate-950/50 cursor-pointer hover:border-slate-700 transition-colors opacity-60 pointer-events-none">
               <div className="w-5 h-5 rounded-full border-2 border-slate-700 bg-transparent mt-0.5 shrink-0"></div>
               <div>
                 <h4 className="font-medium text-slate-300">Local Hardware (Ollama / WebGPU)</h4>
                 <p className="text-sm text-slate-500 mt-1">Offline-first local network processing. Currently unavailable in web environment.</p>
               </div>
            </div>
          </div>
        </section>

        {/* Privacy & Storage */}
        <section className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-6">
             <div className="flex items-center gap-2">
                <HardDrive className="text-blue-400" size={20} />
                <h3 className="text-lg font-medium text-slate-200">Local Storage</h3>
             </div>
             <button className="text-xs font-medium bg-slate-800 text-slate-300 px-3 py-1.5 rounded-lg hover:bg-slate-700 flex items-center gap-1.5 transition-colors">
               <Download size={14} />
               Export DB
             </button>
          </div>
          
          <div className="flex items-start gap-4">
            <Shield className="text-emerald-500 shrink-0 mt-0.5" size={18} />
            <div>
              <h4 className="text-sm font-medium text-slate-200">End-to-End Privacy</h4>
              <p className="text-sm text-slate-400 mt-1 max-w-2xl">
                All meeting histories and daily todos are stored locally in your browser's IndexedDB. 
                Clearing your browser site data will permanently delete all records unless you export them first.
              </p>
            </div>
          </div>
        </section>

      </div>
    </div>
  );
}
