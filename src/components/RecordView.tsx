import { useState, useRef, useEffect } from 'react';
import { format } from 'date-fns';
import { useStore } from '../store';
import { Mic2, Square, Pause, FileAudio, Settings } from 'lucide-react';
import { cn } from '../lib/utils';
import { db } from '../lib/db';

export default function RecordView() {
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [duration, setDuration] = useState(0);
  const [dbfs, setDbfs] = useState(-100);
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const intervalRef = useRef<number | undefined>(undefined);
  const meterIntervalRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    if (isRecording && !isPaused) {
      intervalRef.current = window.setInterval(() => setDuration(d => d + 1), 1000);
    }
    
    return () => {
      clearInterval(intervalRef.current);
    };
  }, [isRecording, isPaused]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      
      const audioContext = new AudioContext();
      audioContextRef.current = audioContext;
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;

      const dataArray = new Uint8Array(analyser.frequencyBinCount);

      meterIntervalRef.current = window.setInterval(() => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i];
        }
        const average = sum / dataArray.length;
        // Map 0-255 to roughly -100 to 0 dBFS
        const db = average === 0 ? -100 : 20 * Math.log10(average / 255);
        setDbfs(db);
      }, 50);

      mediaRecorder.start();
      setIsRecording(true);
      setIsPaused(false);
      setDuration(0);
    } catch (err) {
      console.error("Error accessing microphone:", err);
      alert("Could not access microphone.");
    }
  };

  const stopRecording = async () => {
    try {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
        await audioContextRef.current.close().catch(console.error);
      }
    } catch (err) {
      console.error("Error stopping recording: ", err);
    }

    clearInterval(meterIntervalRef.current);
    clearInterval(intervalRef.current);
    setDbfs(-100);

    try {
      // Save mocked meeting record
      await db.meetings.add({
        id: Math.random().toString(36).substring(2, 9),
        title: `Meeting ${format(new Date(), 'MMM do, h:mm a')}`,
        createdAt: Date.now(),
        duration: duration,
        transcript: "This is a placeholder transcript from the local recording.",
        summary: "Local recording completed."
      });
    } catch (err) {
      console.error("Error saving meeting: ", err);
    }

    setIsRecording(false);
    setIsPaused(false);
    setDuration(0);
  };

  const togglePause = () => {
    if (isPaused) {
      mediaRecorderRef.current?.resume();
      setIsPaused(false);
    } else {
      mediaRecorderRef.current?.pause();
      setIsPaused(true);
      setDbfs(-100);
    }
  };

  const toggleRecord = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  const formatHhMmSs = (secs: number) => {
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    const s = Math.floor(secs % 60);
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const volumePercent = Math.max(0, Math.min(100, (dbfs + 100) * 1.5));

  return (
    <div className="h-full flex flex-col animate-in fade-in zoom-in-95 duration-300">
      <header className="mb-6">
        <h2 className="text-2xl font-semibold tracking-tight text-white">Live Recording</h2>
        <p className="text-slate-400 mt-1 text-sm">Capture audio, generate transcripts, and extract action items.</p>
      </header>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Telemetry/Control Column */}
        <div className="lg:col-span-1 space-y-4">
          <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl flex flex-col items-center justify-center text-center space-y-6 relative overflow-hidden">
            {/* Pulsing background effect when recording */}
            {isRecording && !isPaused && (
              <div className="absolute inset-0 bg-red-500/5 animate-pulse"></div>
            )}
            
            <div>
              <p className="text-sm text-slate-400 font-medium tracking-wide uppercase">Session Timer</p>
              <h1 className="text-5xl font-mono tracking-tight text-slate-100 mt-2">{formatHhMmSs(duration)}</h1>
            </div>

            <div className="flex gap-4">
              {isRecording && (
                <button 
                  onClick={togglePause}
                  className="w-14 h-14 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 hover:text-white hover:bg-slate-700 transition-colors"
                >
                  <Pause size={24} className={isPaused ? 'fill-current' : ''} />
                </button>
              )}
              <button 
                onClick={toggleRecord}
                className={cn(
                  "w-16 h-16 rounded-full flex items-center justify-center transition-all duration-300 shadow-xl",
                  isRecording 
                    ? "bg-slate-800 hover:bg-slate-700 text-red-500 shadow-slate-900/50" 
                    : "bg-red-500 hover:bg-red-400 text-white shadow-red-900/30"
                )}
              >
                {isRecording ? <Square size={24} className="fill-current" /> : <Mic2 size={28} className="fill-current" />}
              </button>
            </div>

            {/* Audio Meter */}
            <div className="w-full space-y-2 mt-4 relative z-10">
              <div className="flex justify-between text-xs font-mono text-slate-500">
                <span>L</span>
                <span>{Math.round(dbfs)} dBFS</span>
                <span>R</span>
              </div>
              <div className="h-2 w-full bg-slate-950 rounded-full overflow-hidden flex items-center ring-1 ring-inset ring-slate-800/50">
                <div 
                  className={cn(
                    "h-full rounded-full transition-all duration-75",
                    dbfs > -10 ? "bg-red-500" : dbfs > -30 ? "bg-emerald-400" : "bg-indigo-500"
                  )}
                  style={{ width: `${volumePercent}%` }}
                ></div>
              </div>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl space-y-4">
            <h3 className="font-medium text-slate-200 text-sm flex items-center gap-2">
              <Settings size={16} className="text-slate-500" />
              Capture Settings
            </h3>
            
            <div className="space-y-3">
               <div>
                 <label className="text-xs text-slate-500 font-medium">Input Source</label>
                 <select className="mt-1 block w-full bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-300 py-2 px-3 outline-none focus:border-indigo-500">
                   <option>Default Microphone array (WASAPI)</option>
                   <option>System Loopback (Speakers)</option>
                 </select>
               </div>
               <div>
                 <label className="text-xs text-slate-500 font-medium">Transcription Profile</label>
                 <select className="mt-1 block w-full bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-300 py-2 px-3 outline-none focus:border-indigo-500">
                   <option>Balanced (Local Whisper Small)</option>
                   <option>Fast (Local Whisper Tiny)</option>
                   <option>Cloud (Gemini Native Audio)</option>
                 </select>
               </div>
            </div>
          </div>
        </div>

        {/* Live Transcript / Notes Column */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl flex flex-col p-6 shadow-sm relative">
           {isRecording ? (
             <div className="flex-1 flex flex-col items-center justify-center text-center space-y-4" style={{ opacity: Math.max(0.2, volumePercent/100) }}>
                <div className="w-16 h-16 rounded-full border-4 border-slate-800 flex items-center justify-center animate-[spin_3s_linear_infinite]">
                  <FileAudio className="text-indigo-500" size={24} />
                </div>
                <p className="text-slate-400 font-medium">Listening for speech...</p>
                <div className="max-w-md mx-auto p-4 bg-slate-950 rounded-xl border border-slate-800 text-left w-full mt-4">
                   <div className="h-2 w-16 bg-slate-800 rounded-full mb-3"></div>
                   <div className="h-2 w-3/4 bg-slate-800 rounded-full mb-2"></div>
                   <div className="h-2 w-1/2 bg-slate-800 rounded-full"></div>
                </div>
             </div>
           ) : (
             <div className="flex-1 flex flex-col items-center justify-center text-center max-w-sm mx-auto">
                <Mic2 className="text-slate-700/50 mb-4" size={48} />
                <h3 className="text-lg font-medium text-slate-300">Ready to transcribe</h3>
                <p className="text-sm text-slate-500 mt-2">
                  Press the record button to begin capturing your meeting. The audio will stay on-device unless configured otherwise.
                </p>
             </div>
           )}
        </div>

      </div>
    </div>
  );
}

