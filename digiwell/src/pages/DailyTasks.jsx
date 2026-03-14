import React, { useState, useEffect } from 'react';
import { getDailyTasks, startDailyTask, completeDailyTask, skipDailyTask, getPlannerAdherence } from '../api/digiwell';
import { CheckSquare, Play, FastForward, Square, ListTodo, Activity } from 'lucide-react';
import toast from 'react-hot-toast';

export default function DailyTasks({ initialDate }) {
  const [date, setDate] = useState(initialDate || new Date().toISOString().split('T')[0]);
  const [tasks, setTasks] = useState([]);
  const [adherence, setAdherence] = useState(null);

  useEffect(() => {
    load();
  }, [date]);

  const load = async () => {
    try {
      const data = await getDailyTasks(date);
      setTasks(data || []);
      const ad = await getPlannerAdherence(date);
      setAdherence(ad);
    } catch (e) {
      console.error(e);
    }
  };

  const handleAction = async (action, id) => {
    try {
      if (action === 'start') {
        const t = tasks.find(t=>t.id===id);
        const meta = t.metadata;
        if (meta?.auto_focus) {
          toast.success("Focus Session auto-started by Agent!");
        }
        await startDailyTask(id);
      }
      else if (action === 'complete') await completeDailyTask(id);
      else if (action === 'skip') await skipDailyTask(id);
      load();
    } catch(e) {
      toast.error('Action failed');
    }
  };

  const formatTime = (ts) => {
    if (!ts) return '--:--';
    return new Date(ts).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center bg-surface p-4 rounded-xl shadow-sm">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <ListTodo className="text-indigo-500" /> Daily Plan
          </h1>
          <p className="text-sm text-slate-500">Execute your daily tasks efficiently.</p>
        </div>
        <div className="flex items-center gap-3">
          <input type="date" value={date} onChange={e=>setDate(e.target.value)} className="p-2 rounded border dark:bg-slate-800" />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <h2 className="font-bold text-lg border-b pb-2 dark:border-slate-700">Tasks for {date}</h2>
          {tasks.length === 0 ? (
           <p className="text-slate-500 py-10 text-center border-2 border-dashed rounded-xl dark:border-slate-700">No tasks generated for this date. Go to Weekly Timetable.</p>
          ) : (
            tasks.map(t => (
              <div key={t.id} className={`p-4 rounded-xl border flex flex-col gap-3 transition-all ${
                t.status === 'completed' ? 'bg-emerald-50/50 border-emerald-200 dark:bg-emerald-900/10 dark:border-emerald-800/30 opacity-70' :
                t.status === 'running' ? 'bg-indigo-50/50 border-indigo-300 dark:bg-indigo-900/20 dark:border-indigo-700 shadow-md transform scale-[1.01]' :
                t.status === 'skipped' ? 'opacity-50 grayscale' :
                'bg-surface border-slate-200 dark:border-slate-700'
              }`}>
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className={`font-bold text-lg ${t.status === 'completed' ? 'line-through text-slate-500' : ''}`}>{t.title}</h3>
                    <div className="flex items-center gap-2 mt-1 text-xs text-slate-500">
                      <span className="bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded uppercase">{t.category}</span>
                      <span>Scheduled: {formatTime(t.planned_start)} - {formatTime(t.planned_end)} ({t.duration_planned_minutes}m)</span>
                      {t.metadata?.auto_focus && <span className="text-emerald-600 font-semibold bg-emerald-100 px-2 rounded">🎯 Focus Mode Event</span>}
                    </div>
                  </div>
                  <div>
                    <span className={`px-2 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                      t.status === 'completed' ? 'bg-emerald-100 text-emerald-700' :
                      t.status === 'running' ? 'bg-indigo-100 text-indigo-700 animate-pulse' :
                      'bg-slate-100 text-slate-600'
                    }`}>
                      {t.status}
                    </span>
                  </div>
                </div>

                <div className="flex justify-between items-center border-t dark:border-slate-700 pt-3 mt-1">
                  <div className="text-xs text-slate-500">
                    {t.actual_start && <span>Started: {formatTime(t.actual_start)}</span>}
                    {t.actual_end && <span className="ml-3">Ended: {formatTime(t.actual_end)} ({t.duration_actual_minutes}m log)</span>}
                  </div>
                  <div className="flex items-center gap-2">
                    {t.status === 'scheduled' && (
                      <>
                        <button onClick={() => handleAction('skip', t.id)} className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1 px-3 py-1.5"><FastForward size={14}/> Skip</button>
                        <button onClick={() => handleAction('start', t.id)} className="text-xs bg-indigo-600 text-white hover:bg-indigo-700 rounded-lg flex items-center gap-1 px-4 py-1.5 shadow-sm transition-transform active:scale-95"><Play size={14}/> Start Task</button>
                      </>
                    )}
                    {t.status === 'running' && (
                      <button onClick={() => handleAction('complete', t.id)} className="text-xs bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg flex items-center gap-1 px-4 py-1.5 shadow-sm transition-transform active:scale-95"><CheckSquare size={14}/> Complete Task</button>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        <div className="space-y-4">
          <div className="bg-surface rounded-xl border dark:border-slate-700 p-5 shadow-sm sticky top-6">
            <h3 className="font-bold flex items-center gap-2 mb-4">
              <Activity className="text-indigo-500" /> Daily Adherence
            </h3>
            {adherence ? (
              <div className="space-y-4">
                <div className="flex justify-center mb-6">
                  <div className="relative w-32 h-32 rounded-full border-8 border-indigo-100 dark:border-indigo-900/30 flex items-center justify-center">
                    <div className={`absolute inset-0 rounded-full border-8 border-transparent text-center`} style={{ borderTopColor: adherence.adherence_score > 70 ? '#10b981' : '#6366f1', transform: `rotate(${Math.min(adherence.adherence_score * 3.6, 360)}deg)` }}></div>
                    <div className="text-center absolute inset-0 flex flex-col items-center justify-center">
                      <span className="text-3xl font-black">{adherence.adherence_score || 0}</span>
                      <span className="text-[10px] text-slate-500 uppercase tracking-widest">Score</span>
                    </div>
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-2 text-center text-sm">
                  <div className="bg-slate-50 dark:bg-slate-800 p-2 rounded-lg">
                    <div className="text-slate-500 text-xs mb-1">Tasks</div>
                    <div className="font-semibold">{adherence.completed_tasks} / {adherence.scheduled_tasks}</div>
                  </div>
                  <div className="bg-slate-50 dark:bg-slate-800 p-2 rounded-lg">
                    <div className="text-slate-500 text-xs mb-1">Time Logged</div>
                    <div className="font-semibold">{adherence.actual_total_minutes} / {adherence.planned_total_minutes}m</div>
                  </div>
                </div>

                {adherence.adherence_score < 100 && adherence.scheduled_tasks > 0 && (
                  <div className="mt-4 p-3 bg-indigo-50/50 dark:bg-indigo-900/20 border border-indigo-100 dark:border-indigo-800 rounded-lg text-sm text-indigo-800 dark:text-indigo-300">
                    <strong className="block mb-1">💡 Smart Suggestion</strong>
                    Based on today, consider reducing task duration or moving uncompleted tasks to a morning slot when you have more energy!
                  </div>
                )}
              </div>
            ) : (
                <div className="text-center text-slate-500 py-6 text-sm">Complete tasks to see your adherence score.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}