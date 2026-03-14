import React, { useState, useEffect } from 'react';
import { getTimetables, createTimetable, createTimetableSlot, generateDailyTasks } from '../api/digiwell';
import { Plus, Play, Calendar } from 'lucide-react';
import toast from 'react-hot-toast';
import { useNavigate } from 'react-router-dom';

export default function WeeklyTimetable() {
  const [timetables, setTimetables] = useState([]);
  const [activeTable, setActiveTable] = useState(null);
  const [showAddSlot, setShowAddSlot] = useState(false);
  const [newSlot, setNewSlot] = useState({ day_of_week: 0, start_time: '09:00', end_time: '10:00', title: '', category: 'deep_work', focus_mode: false });
  const navigate = useNavigate();

  useEffect(() => {
    load();
  }, []);

  const load = async () => {
    try {
      const data = await getTimetables();
      setTimetables(data);
      if (data.length > 0 && !activeTable) setActiveTable(data[0]);
    } catch (e) {
      console.error(e);
    }
  };

  const handleCreateNew = async () => {
    await createTimetable({ name: 'My New Timetable', timezone: 'UTC' });
    load();
  };

  const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  const handleAddSlot = async () => {
    if (!activeTable) return;
    try {
      await createTimetableSlot(activeTable.id, newSlot);
      setShowAddSlot(false);
      load();
      toast.success('Slot added!');
    } catch (e) {
      toast.error('Failed to add slot');
    }
  };

  const handleGenerateToday = async () => {
    if (!activeTable) return;
    const today = new Date().toISOString().split('T')[0];
    try {
      await generateDailyTasks(activeTable.id, today);
      toast.success('Generated tasks for today!');
      navigate('/daily-tasks');
    } catch(e) {
      toast.error('Failed to generate tasks');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Calendar className="text-indigo-500" /> Weekly Timetable
          </h1>
          <p className="text-slate-500 text-sm">Plan your ideal week to automatically generate daily tasks.</p>
        </div>
        <div className="flex gap-2">
          <button onClick={handleCreateNew} className="btn-secondary">New Timetable</button>
          <button onClick={handleGenerateToday} className="btn-primary flex items-center gap-2">
            <Play size={16} /> Generate Today
          </button>
        </div>
      </div>

      {!activeTable ? (
        <div className="p-8 text-center text-slate-500">No timetables yet. Click "New Timetable".</div>
      ) : (
        <div className="bg-surface rounded-xl border border-slate-200 dark:border-slate-700 p-6 flex flex-col items-start gap-4">
          <div className="flex items-center justify-between w-full">
            <h2 className="text-xl font-semibold">{activeTable.name}</h2>
            <button onClick={() => setShowAddSlot(true)} className="flex items-center gap-1 text-sm bg-indigo-500/10 text-indigo-600 px-3 py-1.5 rounded-lg hover:bg-indigo-500/20">
              <Plus size={16} /> Add Slot
            </button>
          </div>

          <div className="grid grid-cols-7 gap-4 w-full">
            {dayNames.map((d, i) => (
              <div key={d} className="flex flex-col gap-2">
                <div className="font-semibold text-center border-b pb-2 mb-2 dark:border-slate-700">{d}</div>
                {activeTable.slots?.filter(s => s.day_of_week === i).map(s => (
                  <div key={s.id} className="p-2 text-xs rounded-md bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex flex-col gap-1 shadow-sm">
                    <span className="font-bold text-indigo-600 dark:text-indigo-400">{s.start_time} - {s.end_time}</span>
                    <span className="font-medium text-slate-800 dark:text-slate-200">{s.title || 'Untitled task'}</span>
                    <span className="text-[10px] text-slate-500 uppercase">{s.category}</span>
                    {!!s.focus_mode && <span className="text-[10px] text-emerald-500 mt-1 font-semibold flex items-center gap-1">🎯 Auto Focus</span>}
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}

      {showAddSlot && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-surface w-full max-w-md p-6 rounded-xl border dark:border-slate-700 shadow-xl">
            <h3 className="text-lg font-bold mb-4">Add Weekly Slot</h3>
            <div className="grid gap-4 mb-6">
              <label>Day
                <select value={newSlot.day_of_week} onChange={e => setNewSlot({...newSlot, day_of_week: parseInt(e.target.value)})} className="w-full mt-1 p-2 rounded border dark:bg-slate-800">
                  {dayNames.map((n, i) => <option key={n} value={i}>{n}</option>)}
                </select>
              </label>
              <div className="grid grid-cols-2 gap-4">
                <label>Start<input type="time" value={newSlot.start_time} onChange={e=>setNewSlot({...newSlot, start_time: e.target.value})} className="w-full mt-1 p-2 rounded border dark:bg-slate-800" /></label>
                <label>End<input type="time" value={newSlot.end_time} onChange={e=>setNewSlot({...newSlot, end_time: e.target.value})} className="w-full mt-1 p-2 rounded border dark:bg-slate-800" /></label>
              </div>
              <label>Title<input type="text" value={newSlot.title} onChange={e=>setNewSlot({...newSlot, title: e.target.value})} className="w-full mt-1 p-2 rounded border dark:bg-slate-800" placeholder="E.g. Deep Work" /></label>
              <label>Category
                <select value={newSlot.category} onChange={e=>setNewSlot({...newSlot, category: e.target.value})} className="w-full mt-1 p-2 rounded border dark:bg-slate-800">
                  {["deep_work", "study", "exercise", "social", "leisure", "chores"].map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </label>
              <label className="flex items-center gap-2 cursor-pointer mt-2">
                <input type="checkbox" checked={newSlot.focus_mode} onChange={e=>setNewSlot({...newSlot, focus_mode: e.target.checked})} className="rounded text-emerald-500" />
                <span className="text-sm font-medium">Enable Auto-Focus Mode</span>
              </label>
            </div>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setShowAddSlot(false)} className="btn-secondary">Cancel</button>
              <button onClick={handleAddSlot} className="btn-primary">Save Slot</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}