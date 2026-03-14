import React, { useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import { CalendarDays, Plus, Pencil, Trash2, ArrowUp, ArrowDown } from 'lucide-react';
import {
  getWeeklyPlanTasks,
  seedDemoWeeklyPlan,
  generateSmartWeeklyPlan,
  getHabitRecommendations,
  createWeeklyPlanTask,
  updateWeeklyPlanTask,
  deleteWeeklyPlanTask,
  reorderWeeklyPlanTasks,
  getDailyPlan,
  setDailyPlanTaskStatus,
} from '../api/digiwell';

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const CATEGORIES = ['Health', 'Study', 'Work', 'Mindfulness', 'Break'];
const PRIORITIES = ['Low', 'Medium', 'High'];

const EMPTY_FORM = {
  id: null,
  task_title: '',
  task_description: '',
  day_of_week: 0,
  start_time: '09:00',
  end_time: '10:00',
  category: 'Work',
  priority: 'Medium',
};

export default function WeeklyPlanPage() {
  const [tasks, setTasks] = useState([]);
  const [dayCompletion, setDayCompletion] = useState({});
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);
  const [smartLoading, setSmartLoading] = useState(false);
  const [habitCards, setHabitCards] = useState([]);

  const grouped = useMemo(() => {
    const map = Object.fromEntries(DAYS.map((_, i) => [i, []]));
    for (const t of tasks) {
      map[t.day_of_week] = map[t.day_of_week] || [];
      map[t.day_of_week].push(t);
    }
    return map;
  }, [tasks]);

  const formatDate = (dt) => {
    const y = dt.getFullYear();
    const m = String(dt.getMonth() + 1).padStart(2, '0');
    const d = String(dt.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  };

  const getDateForDayOfCurrentWeek = (day) => {
    const now = new Date();
    const mondayOffset = (now.getDay() + 6) % 7;
    const monday = new Date(now);
    monday.setDate(now.getDate() - mondayOffset);
    const target = new Date(monday);
    target.setDate(monday.getDate() + day);
    return formatDate(target);
  };

  const loadDayCompletion = async () => {
    try {
      const daily = await Promise.all(
        DAYS.map((_, day) => getDailyPlan(getDateForDayOfCurrentWeek(day)))
      );
      const statusMap = {};
      daily.forEach((res, day) => {
        const planned = Number(res?.summary?.planned || 0);
        const completed = Number(res?.summary?.completed || 0);
        statusMap[day] = {
          date: getDateForDayOfCurrentWeek(day),
          planned,
          completed,
          isCompleted: planned > 0 && completed === planned,
        };
      });
      setDayCompletion(statusMap);
    } catch (err) {
      console.error(err);
    }
  };

  const load = async () => {
    try {
      setLoading(true);
      const data = await getWeeklyPlanTasks();
      setTasks(Array.isArray(data) ? data : []);
      await loadDayCompletion();
    } catch (err) {
      console.error(err);
      toast.error('Failed to load weekly plan');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const loadHabitCards = async () => {
    try {
      const data = await getHabitRecommendations();
      setHabitCards(Array.isArray(data?.cards) ? data.cards : []);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadHabitCards();
  }, []);

  const openAdd = (day) => {
    setForm({ ...EMPTY_FORM, day_of_week: day });
    setShowForm(true);
  };

  const openEdit = (task) => {
    setForm({
      ...EMPTY_FORM,
      ...task,
      day_of_week: Number(task.day_of_week),
    });
    setShowForm(true);
  };

  const submitForm = async () => {
    if (!form.task_title.trim()) {
      toast.error('Task title is required');
      return;
    }

    const payload = {
      task_title: form.task_title,
      task_description: form.task_description,
      day_of_week: Number(form.day_of_week),
      start_time: form.start_time,
      end_time: form.end_time,
      category: form.category,
      priority: form.priority,
      sort_order: Number(form.sort_order || 0),
    };

    try {
      if (form.id) {
        await updateWeeklyPlanTask(form.id, payload);
        toast.success('Task updated');
      } else {
        await createWeeklyPlanTask(payload);
        toast.success('Task created');
      }
      setShowForm(false);
      setForm(EMPTY_FORM);
      load();
    } catch (err) {
      console.error(err);
      toast.error('Failed to save task');
    }
  };

  const onDelete = async (taskId) => {
    try {
      await deleteWeeklyPlanTask(taskId);
      toast.success('Task deleted');
      load();
    } catch (err) {
      console.error(err);
      toast.error('Failed to delete task');
    }
  };

  const moveTask = async (day, index, direction) => {
    const dayTasks = [...(grouped[day] || [])].sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
    const newIndex = index + direction;
    if (newIndex < 0 || newIndex >= dayTasks.length) return;

    const temp = dayTasks[index];
    dayTasks[index] = dayTasks[newIndex];
    dayTasks[newIndex] = temp;

    try {
      await reorderWeeklyPlanTasks(day, dayTasks.map((t) => t.id));
      load();
    } catch (err) {
      console.error(err);
      toast.error('Failed to reorder task');
    }
  };

  const toggleDayCompletion = async (day) => {
    const dayTasks = grouped[day] || [];
    if (dayTasks.length === 0) {
      toast('No tasks planned for this day');
      return;
    }

    const date = getDateForDayOfCurrentWeek(day);
    const targetStatus = dayCompletion?.[day]?.isCompleted ? 'pending' : 'completed';
    try {
      await Promise.all(
        dayTasks.map((task) =>
          setDailyPlanTaskStatus({
            task_id: task.id,
            date,
            status: targetStatus,
          })
        )
      );
      toast.success(`${DAYS[day]} marked as ${targetStatus === 'completed' ? 'completed' : 'not completed'}`);
      await loadDayCompletion();
    } catch (err) {
      console.error(err);
      toast.error('Failed to update day status');
    }
  };

  const handleSeedDemo = async () => {
    try {
      setSeeding(true);
      await seedDemoWeeklyPlan(true);
      toast.success('Demo weekly plan loaded');
      load();
    } catch (err) {
      console.error(err);
      toast.error('Failed to load demo plan');
    } finally {
      setSeeding(false);
    }
  };

  const handleSmartPlan = async () => {
    try {
      setSmartLoading(true);
      await generateSmartWeeklyPlan(true);
      toast.success('Smart weekly plan generated');
      await load();
      await loadHabitCards();
    } catch (err) {
      console.error(err);
      toast.error('Failed to generate smart weekly plan');
    } finally {
      setSmartLoading(false);
    }
  };

  const addHabitCardToToday = async (card) => {
    const today = (new Date().getDay() + 6) % 7;
    const now = new Date();
    const startHour = Math.max(7, now.getHours() + 1);
    const duration = Number(card.duration_minutes || 30);
    const endHour = Math.min(23, startHour + Math.max(1, Math.floor(duration / 60)));
    const payload = {
      day_of_week: today,
      task_title: card.title,
      task_description: card.reason || 'AI-suggested habit',
      start_time: `${String(startHour).padStart(2, '0')}:00`,
      end_time: `${String(endHour).padStart(2, '0')}:00`,
      category: card.category || 'Work',
      priority: 'Medium',
    };
    try {
      await createWeeklyPlanTask(payload);
      toast.success(`Added "${card.title}" to today`);
      load();
    } catch (err) {
      console.error(err);
      toast.error('Failed to add habit card');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <CalendarDays className="text-indigo-500" /> Weekly Planner
          </h1>
          <p className="text-slate-500 text-sm mt-1">Plan your full week strategy across all 7 days.</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={handleSeedDemo} disabled={seeding} className="btn-secondary">
            {seeding ? 'Loading Demo...' : 'Load Demo Weekly Plan'}
          </button>
          <button onClick={handleSmartPlan} disabled={smartLoading} className="btn-primary">
            {smartLoading ? 'Generating...' : 'Generate Smart Weekly Plan'}
          </button>
        </div>
      </div>

      {loading ? (
        <div className="p-6 rounded-xl border border-slate-200 dark:border-slate-700">Loading weekly plan...</div>
      ) : (
        <div className="space-y-4">
          <div className="overflow-x-auto pb-2">
            <div className="flex flex-row flex-nowrap gap-4 min-w-max">
              {DAYS.map((dayName, day) => {
                const dayTasks = [...(grouped[day] || [])].sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
                return (
                  <div key={dayName} className="w-[280px] shrink-0 bg-surface rounded-xl border border-slate-200 dark:border-slate-700 p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-slate-900 dark:text-white">{dayName}</h3>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => toggleDayCompletion(day)}
                      className={`text-xs px-2 py-1 rounded ${dayCompletion?.[day]?.isCompleted ? 'bg-emerald-100 text-emerald-700 hover:bg-emerald-200' : 'bg-slate-100 text-slate-700 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300'}`}
                    >
                      {dayCompletion?.[day]?.isCompleted ? 'Completed' : 'Mark Complete'}
                    </button>
                    <button onClick={() => openAdd(day)} className="text-xs px-2 py-1 rounded bg-indigo-100 text-indigo-700 hover:bg-indigo-200">
                      <Plus className="w-3 h-3 inline mr-1" /> Add
                    </button>
                  </div>
                </div>
                <p className="text-[10px] text-slate-500">
                  {dayCompletion?.[day]?.completed || 0}/{dayCompletion?.[day]?.planned || 0} completed this week
                </p>
                {!!dayCompletion?.[day]?.isCompleted && (
                  <p className="text-xs rounded-md border border-emerald-200 bg-emerald-50 text-emerald-700 px-2 py-1 dark:border-emerald-700 dark:bg-emerald-900/20 dark:text-emerald-300">
                    Day Completed
                  </p>
                )}

                {dayTasks.length === 0 ? (
                  <p className="text-xs text-slate-500 border border-dashed border-slate-300 dark:border-slate-700 rounded p-3">No tasks planned.</p>
                ) : (
                  dayTasks.map((task, idx) => (
                    <div key={task.id} className="rounded-lg border border-slate-200 dark:border-slate-700 p-2 bg-white/50 dark:bg-slate-900/30">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <p className="font-medium text-sm">{task.task_title}</p>
                          <p className="text-xs text-slate-500">{task.start_time} - {task.end_time}</p>
                          <p className="text-[10px] uppercase tracking-wide text-indigo-600 mt-1">{task.category} · {task.priority}</p>
                        </div>
                        <div className="flex flex-col gap-1">
                          <button onClick={() => moveTask(day, idx, -1)} className="text-slate-500 hover:text-slate-900"><ArrowUp className="w-3 h-3" /></button>
                          <button onClick={() => moveTask(day, idx, 1)} className="text-slate-500 hover:text-slate-900"><ArrowDown className="w-3 h-3" /></button>
                        </div>
                      </div>
                      <div className="flex justify-end gap-2 mt-2">
                        <button onClick={() => openEdit(task)} className="text-xs text-indigo-600 hover:underline"><Pencil className="w-3 h-3 inline mr-1" />Edit</button>
                        <button onClick={() => onDelete(task.id)} className="text-xs text-rose-600 hover:underline"><Trash2 className="w-3 h-3 inline mr-1" />Delete</button>
                      </div>
                    </div>
                  ))
                )}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="bg-surface rounded-xl border border-slate-200 dark:border-slate-700 p-4">
            <h3 className="font-semibold mb-3">AI Habit Recommendation Cards</h3>
            {habitCards.length === 0 ? (
              <p className="text-sm text-slate-500">No recommendations yet. Generate smart plan or complete more daily tasks.</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                {habitCards.map((card, idx) => (
                  <div key={`${card.title}-${idx}`} className="rounded-lg border border-slate-200 dark:border-slate-700 p-3">
                    <p className="font-medium text-sm">{card.title}</p>
                    <p className="text-xs text-slate-500 mt-1">{card.reason}</p>
                    <p className="text-[10px] uppercase tracking-wide text-indigo-600 mt-2">{card.category} · {card.duration_minutes} min</p>
                    <button onClick={() => addHabitCardToToday(card)} className="mt-2 text-xs px-2 py-1 rounded bg-indigo-100 text-indigo-700 hover:bg-indigo-200">
                      Add To Today
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {showForm && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-lg bg-surface border border-slate-200 dark:border-slate-700 rounded-xl p-5">
            <h3 className="font-semibold text-lg mb-4">{form.id ? 'Edit Weekly Task' : 'Add Weekly Task'}</h3>
            <div className="space-y-3">
              <input value={form.task_title} onChange={(e) => setForm({ ...form, task_title: e.target.value })} placeholder="Task title" className="w-full p-2 rounded border dark:bg-slate-800" />
              <textarea value={form.task_description} onChange={(e) => setForm({ ...form, task_description: e.target.value })} placeholder="Description" className="w-full p-2 rounded border dark:bg-slate-800" rows={3} />
              <div className="grid grid-cols-2 gap-3">
                <label className="text-sm">Day
                  <select value={form.day_of_week} onChange={(e) => setForm({ ...form, day_of_week: Number(e.target.value) })} className="w-full mt-1 p-2 rounded border dark:bg-slate-800">
                    {DAYS.map((d, i) => <option key={d} value={i}>{d}</option>)}
                  </select>
                </label>
                <label className="text-sm">Category
                  <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="w-full mt-1 p-2 rounded border dark:bg-slate-800">
                    {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                </label>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <label className="text-sm">Start
                  <input type="time" value={form.start_time} onChange={(e) => setForm({ ...form, start_time: e.target.value })} className="w-full mt-1 p-2 rounded border dark:bg-slate-800" />
                </label>
                <label className="text-sm">End
                  <input type="time" value={form.end_time} onChange={(e) => setForm({ ...form, end_time: e.target.value })} className="w-full mt-1 p-2 rounded border dark:bg-slate-800" />
                </label>
              </div>
              <label className="text-sm">Priority
                <select value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })} className="w-full mt-1 p-2 rounded border dark:bg-slate-800">
                  {PRIORITIES.map((p) => <option key={p} value={p}>{p}</option>)}
                </select>
              </label>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setShowForm(false)} className="btn-secondary">Cancel</button>
              <button onClick={submitForm} className="btn-primary">Save</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
