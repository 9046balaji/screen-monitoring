import React, { useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import { CheckCircle2, Circle, SkipForward, BarChart3, Flame, PlusCircle, ArrowRightLeft } from 'lucide-react';
import {
  getDailyPlan,
  setDailyPlanTaskStatus,
  moveDailyPlanTask,
  createWeeklyPlanTask,
  updateWeeklyPlanTask,
  getPlannerStreak,
  getPlannerAnalysis,
  getPlannerDashboard,
} from '../api/digiwell';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const COLORS = ['#22c55e', '#e2e8f0', '#f97316'];

const defaultEdit = {
  id: null,
  task_title: '',
  task_description: '',
  day_of_week: 0,
  start_time: '09:00',
  end_time: '10:00',
  category: 'Work',
  priority: 'Medium',
};

export default function DailyPlanPage() {
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [daily, setDaily] = useState({ tasks: [], summary: { planned: 0, completed: 0, skipped: 0, pending: 0, execution_rate: 0 } });
  const [streak, setStreak] = useState({ current_streak: 0, weekly_success_days: 0, monthly_success_days: 0 });
  const [analysis, setAnalysis] = useState({ suggestions: [], skipped_tasks: [], day_breakdown: [] });
  const [dashboard, setDashboard] = useState({ weekly_completion: [] });
  const [showEdit, setShowEdit] = useState(false);
  const [editTask, setEditTask] = useState(defaultEdit);
  const [showAdd, setShowAdd] = useState(false);

  const load = async () => {
    try {
      const [dailyRes, streakRes, analysisRes, dashboardRes] = await Promise.all([
        getDailyPlan(date),
        getPlannerStreak(30),
        getPlannerAnalysis({ endDate: date }),
        getPlannerDashboard(date),
      ]);
      setDaily(dailyRes || { tasks: [], summary: {} });
      setStreak(streakRes || {});
      setAnalysis(analysisRes || {});
      setDashboard(dashboardRes || {});
    } catch (err) {
      console.error(err);
      toast.error('Failed to load daily plan');
    }
  };

  useEffect(() => {
    load();
  }, [date]);

  const pieData = useMemo(() => {
    const s = daily.summary || {};
    return [
      { name: 'Completed', value: s.completed || 0 },
      { name: 'Pending', value: s.pending || 0 },
      { name: 'Skipped', value: s.skipped || 0 },
    ];
  }, [daily]);

  const updateStatus = async (taskId, status) => {
    try {
      await setDailyPlanTaskStatus({ task_id: taskId, date, status });
      load();
    } catch (err) {
      console.error(err);
      toast.error('Failed to update status');
    }
  };

  const openEdit = (task) => {
    setEditTask({
      ...defaultEdit,
      ...task,
      task_title: task.task_title,
      task_description: task.task_description || '',
    });
    setShowEdit(true);
  };

  const saveEdit = async () => {
    try {
      await updateWeeklyPlanTask(editTask.id, editTask);
      setShowEdit(false);
      load();
      toast.success('Task updated');
    } catch (err) {
      console.error(err);
      toast.error('Failed to update task');
    }
  };

  const moveTask = async (taskId, newDay) => {
    try {
      await moveDailyPlanTask({ task_id: taskId, new_day_of_week: Number(newDay) });
      load();
      toast.success('Task moved');
    } catch (err) {
      console.error(err);
      toast.error('Failed to move task');
    }
  };

  const addTask = async () => {
    if (!editTask.task_title.trim()) {
      toast.error('Task title required');
      return;
    }
    try {
      await createWeeklyPlanTask(editTask);
      setShowAdd(false);
      setEditTask(defaultEdit);
      load();
      toast.success('Task added');
    } catch (err) {
      console.error(err);
      toast.error('Failed to add task');
    }
  };

  const weeklyChartData = (dashboard.weekly_completion || []).map((d) => ({
    date: d.date?.slice(5) || '',
    execution: d.execution_rate || 0,
  }));

  return (
    <div className="space-y-6">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold">Daily Plan</h1>
          <p className="text-sm text-slate-500">Execution mode for today with AI feedback and streak tracking.</p>
        </div>
        <div className="flex items-center gap-2">
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="p-2 rounded border dark:bg-slate-800" />
          <button
            onClick={() => {
              const d = new Date(date);
              setEditTask({ ...defaultEdit, day_of_week: (d.getDay() + 6) % 7 });
              setShowAdd(true);
            }}
            className="btn-primary flex items-center gap-2"
          >
            <PlusCircle className="w-4 h-4" /> Add Task
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="xl:col-span-2 bg-surface border border-slate-200 dark:border-slate-700 rounded-xl p-4 space-y-3">
          <h2 className="font-semibold">Tasks for {date}</h2>
          {(daily.tasks || []).length === 0 && (
            <div className="text-sm text-slate-500 border border-dashed border-slate-300 dark:border-slate-700 rounded-lg p-4">
              No tasks for this day. Add one or move tasks from weekly plan.
            </div>
          )}

          {(daily.tasks || []).map((task) => (
            <div key={task.id} className="rounded-lg border border-slate-200 dark:border-slate-700 p-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-medium">{task.task_title}</p>
                  <p className="text-xs text-slate-500">{task.start_time} - {task.end_time} · {task.category} · {task.priority}</p>
                  <p className="text-xs text-slate-500 mt-1">{task.task_description || 'No description'}</p>
                </div>
                <div className="text-xs px-2 py-1 rounded-full bg-slate-100 dark:bg-slate-800 uppercase">{task.status}</div>
              </div>

              <div className="flex flex-wrap gap-2 mt-3 items-center">
                <button onClick={() => updateStatus(task.id, 'completed')} className="text-xs px-3 py-1.5 rounded bg-emerald-100 text-emerald-700 hover:bg-emerald-200">
                  <CheckCircle2 className="w-3 h-3 inline mr-1" /> Complete
                </button>
                <button onClick={() => updateStatus(task.id, 'pending')} className="text-xs px-3 py-1.5 rounded bg-slate-100 text-slate-700 hover:bg-slate-200">
                  <Circle className="w-3 h-3 inline mr-1" /> Pending
                </button>
                <button onClick={() => updateStatus(task.id, 'skipped')} className="text-xs px-3 py-1.5 rounded bg-orange-100 text-orange-700 hover:bg-orange-200">
                  <SkipForward className="w-3 h-3 inline mr-1" /> Skip
                </button>
                <button onClick={() => openEdit(task)} className="text-xs px-3 py-1.5 rounded bg-indigo-100 text-indigo-700 hover:bg-indigo-200">Edit</button>
                <label className="text-xs flex items-center gap-1 ml-auto">
                  <ArrowRightLeft className="w-3 h-3" /> Move to
                  <select className="p-1 rounded border dark:bg-slate-800" defaultValue={task.day_of_week} onChange={(e) => moveTask(task.id, e.target.value)}>
                    {DAYS.map((d, i) => <option key={d} value={i}>{d}</option>)}
                  </select>
                </label>
              </div>
            </div>
          ))}
        </div>

        <div className="space-y-4">
          <div className="bg-surface border border-slate-200 dark:border-slate-700 rounded-xl p-4">
            <h3 className="font-semibold flex items-center gap-2 mb-2"><Flame className="w-4 h-4 text-orange-500" /> Streak</h3>
            <p className="text-2xl font-bold">{streak.current_streak || 0} days</p>
            <p className="text-xs text-slate-500">Weekly success: {streak.weekly_success_days || 0} / 7</p>
            <p className="text-xs text-slate-500">Monthly success: {streak.monthly_success_days || 0} / 30</p>
          </div>

          <div className="bg-surface border border-slate-200 dark:border-slate-700 rounded-xl p-4">
            <h3 className="font-semibold flex items-center gap-2 mb-2"><BarChart3 className="w-4 h-4 text-indigo-500" /> Daily Completion Ring</h3>
            <div className="h-44">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={40} outerRadius={68}>
                    {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <p className="text-xs text-slate-500 text-center">Execution rate: {daily.summary?.execution_rate || 0}%</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="bg-surface border border-slate-200 dark:border-slate-700 rounded-xl p-4">
          <h3 className="font-semibold mb-2">Weekly Execution Chart</h3>
          <div className="h-60">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={weeklyChartData}>
                <XAxis dataKey="date" />
                <YAxis domain={[0, 100]} />
                <Tooltip />
                <Line type="monotone" dataKey="execution" stroke="#4f46e5" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-surface border border-slate-200 dark:border-slate-700 rounded-xl p-4">
          <h3 className="font-semibold mb-2">AI Behavioral Analysis</h3>
          <ul className="space-y-2 text-sm text-slate-700 dark:text-slate-200">
            {(analysis.suggestions || []).map((s, i) => <li key={i} className="p-2 rounded bg-indigo-50/50 dark:bg-indigo-900/20">{s}</li>)}
          </ul>
          <div className="mt-4 text-xs text-slate-500">
            <p>Most productive window: {analysis.most_productive_window || 'N/A'}</p>
            <p>Avg mood: {analysis.avg_mood ?? 'N/A'}</p>
            <p>Avg screen time (hours): {analysis.avg_screen_time_hours ?? 'N/A'}</p>
            <p>Frequently skipped: {(analysis.skipped_tasks || []).map((t) => t.task_title).join(', ') || 'None'}</p>
          </div>
        </div>
      </div>

      {(showEdit || showAdd) && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-lg bg-surface border border-slate-200 dark:border-slate-700 rounded-xl p-5">
            <h3 className="font-semibold text-lg mb-4">{showEdit ? 'Edit Task' : 'Add Task'}</h3>
            <div className="space-y-3">
              <input value={editTask.task_title} onChange={(e) => setEditTask({ ...editTask, task_title: e.target.value })} placeholder="Task title" className="w-full p-2 rounded border dark:bg-slate-800" />
              <textarea value={editTask.task_description} onChange={(e) => setEditTask({ ...editTask, task_description: e.target.value })} placeholder="Description" className="w-full p-2 rounded border dark:bg-slate-800" rows={3} />
              <div className="grid grid-cols-2 gap-3">
                <label className="text-sm">Day
                  <select value={editTask.day_of_week} onChange={(e) => setEditTask({ ...editTask, day_of_week: Number(e.target.value) })} className="w-full mt-1 p-2 rounded border dark:bg-slate-800">
                    {DAYS.map((d, i) => <option key={d} value={i}>{d}</option>)}
                  </select>
                </label>
                <label className="text-sm">Category
                  <select value={editTask.category} onChange={(e) => setEditTask({ ...editTask, category: e.target.value })} className="w-full mt-1 p-2 rounded border dark:bg-slate-800">
                    {['Health', 'Study', 'Work', 'Mindfulness', 'Break'].map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                </label>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <input type="time" value={editTask.start_time} onChange={(e) => setEditTask({ ...editTask, start_time: e.target.value })} className="p-2 rounded border dark:bg-slate-800" />
                <input type="time" value={editTask.end_time} onChange={(e) => setEditTask({ ...editTask, end_time: e.target.value })} className="p-2 rounded border dark:bg-slate-800" />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => { setShowEdit(false); setShowAdd(false); }} className="btn-secondary">Cancel</button>
              {showEdit ? (
                <button onClick={saveEdit} className="btn-primary">Save</button>
              ) : (
                <button onClick={addTask} className="btn-primary">Add</button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
