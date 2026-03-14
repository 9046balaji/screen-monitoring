import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { Award, CalendarDays, Mail, Trophy } from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { getProfileSummary } from '../api/digiwell';

const CHART_COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#14B8A6'];

function MetricCard({ label, value, hint }) {
  return (
    <div className="rounded-xl border border-slate-300 dark:border-slate-700 bg-base p-4">
      <p className="text-xs text-slate-600 dark:text-slate-400">{label}</p>
      <p className="mt-1 text-2xl font-bold text-slate-900 dark:text-white">{value}</p>
      {hint ? <p className="mt-1 text-xs text-slate-500 dark:text-slate-500">{hint}</p> : null}
    </div>
  );
}

function AchievementCard({ item }) {
  const progress = item.target > 0 ? Math.min(100, Math.round((item.progress / item.target) * 100)) : 0;
  return (
    <div className={`rounded-xl border p-4 ${item.unlocked ? 'border-emerald-500/40 bg-emerald-500/10' : 'border-slate-300 dark:border-slate-700 bg-base'}`}>
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-slate-900 dark:text-white">{item.title}</h4>
        <Trophy size={16} className={item.unlocked ? 'text-emerald-500' : 'text-slate-500'} />
      </div>
      <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">{item.description}</p>
      <div className="mt-3 h-2 rounded-full bg-slate-200 dark:bg-slate-800">
        <div className="h-2 rounded-full bg-primary" style={{ width: `${progress}%` }} />
      </div>
      <p className="mt-2 text-xs text-slate-600 dark:text-slate-400">{item.progress} / {item.target}</p>
    </div>
  );
}

export default function Profile() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    getProfileSummary()
      .then((data) => {
        if (mounted) setSummary(data);
      })
      .catch((err) => {
        console.error('Failed to load profile summary:', err);
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, []);

  const user = summary?.user_info || {};
  const product = summary?.productivity_summary || {};
  const streak = summary?.streak_statistics || {};
  const tasks = summary?.task_completion_stats || {};
  const focus = summary?.focus_mode_stats || {};
  const mood = summary?.mood_journal_summary || {};
  const apps = summary?.app_usage_summary || {};

  const initials = useMemo(() => {
    const name = user?.name || 'User';
    return name.split(' ').map((n) => n[0]).slice(0, 2).join('').toUpperCase();
  }, [user]);

  return (
    <div className="flex flex-col gap-6">
      <motion.section initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="rounded-2xl border border-slate-300 dark:border-slate-700 bg-surface p-6 shadow-sm">
        <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-4">
            {user?.profile_picture ? (
              <img src={user.profile_picture} alt="profile" className="h-16 w-16 rounded-full object-cover border border-slate-300 dark:border-slate-700" />
            ) : (
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary text-xl font-bold text-white">{initials}</div>
            )}
            <div>
              <h1 className="text-2xl font-bold text-slate-900 dark:text-white">{user?.name || 'User Profile'}</h1>
              <div className="mt-1 flex flex-wrap gap-3 text-xs text-slate-600 dark:text-slate-400">
                <span className="inline-flex items-center gap-1"><Mail size={14} /> {user?.email || '-'}</span>
                <span className="inline-flex items-center gap-1"><CalendarDays size={14} /> Joined {user?.join_date || '-'}</span>
              </div>
            </div>
          </div>
          <div className="rounded-xl border border-primary/40 bg-primary/10 px-4 py-3">
            <p className="text-xs text-slate-600 dark:text-slate-300">Weekly Productivity Score</p>
            <p className="text-3xl font-extrabold text-primary">{product?.weekly_productivity_score ?? '--'}</p>
          </div>
        </div>
      </motion.section>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <MetricCard label="Avg Daily Screen Time" value={`${product?.average_daily_screen_time_hours ?? 0}h`} />
        <MetricCard label="Total Focus Hours" value={`${product?.total_focus_hours ?? 0}h`} />
        <MetricCard label="Task Completion" value={`${tasks?.weekly_completion_percentage ?? 0}%`} hint="This week" />
      </section>

      <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-300 dark:border-slate-700 bg-surface p-5">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Streak Statistics</h3>
          <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
            <MetricCard label="Current Streak" value={streak?.current_streak ?? 0} />
            <MetricCard label="Longest Streak" value={streak?.longest_streak ?? 0} />
            <MetricCard label="Successful Days" value={streak?.total_successful_days ?? 0} />
          </div>
        </div>

        <div className="rounded-2xl border border-slate-300 dark:border-slate-700 bg-surface p-5">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Task Completion Stats</h3>
          <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
            <MetricCard label="Total Tasks Created" value={tasks?.total_tasks_created ?? 0} />
            <MetricCard label="Completed This Week" value={tasks?.tasks_completed_this_week ?? 0} />
            <MetricCard label="Completion %" value={`${tasks?.weekly_completion_percentage ?? 0}%`} />
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-300 dark:border-slate-700 bg-surface p-5">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Focus Mode Stats</h3>
          <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
            <MetricCard label="Total Focus Sessions" value={focus?.total_focus_sessions ?? 0} />
            <MetricCard label="Websites Blocked" value={focus?.websites_blocked ?? 0} />
            <MetricCard label="Focus Hours This Week" value={`${focus?.focus_hours_this_week ?? 0}h`} />
          </div>
        </div>

        <div className="rounded-2xl border border-slate-300 dark:border-slate-700 bg-surface p-5">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white">App Usage Summary</h3>
          <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
            <MetricCard label="Most Used App" value={apps?.most_used_app || '-'} />
            <MetricCard label="Most Productive App" value={apps?.most_productive_app || '-'} />
            <MetricCard label="Most Distracting App" value={apps?.most_distracting_app || '-'} />
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-300 dark:border-slate-700 bg-surface p-5">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Mood Journal Summary</h3>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <MetricCard label="Total Entries" value={mood?.total_journal_entries ?? 0} />
            <MetricCard label="Average Mood" value={mood?.average_mood_score ?? 0} />
          </div>
          <div className="mt-4 h-56">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={mood?.mood_trend_graph || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.2} />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 5]} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Line type="monotone" dataKey="avg_mood" stroke="#10B981" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-300 dark:border-slate-700 bg-surface p-5">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Weekly Screen Time</h3>
          <div className="mt-4 h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={summary?.charts?.weekly_screen_time_graph || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.2} />
                <XAxis dataKey="day" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="hours" radius={[8, 8, 0, 0]}>
                  {(summary?.charts?.weekly_screen_time_graph || []).map((_, index) => (
                    <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-300 dark:border-slate-700 bg-surface p-5">
        <h3 className="inline-flex items-center gap-2 text-lg font-semibold text-slate-900 dark:text-white">
          <Award size={18} /> Achievements
        </h3>
        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          {(summary?.achievements || []).map((item) => (
            <AchievementCard key={item.id} item={item} />
          ))}
        </div>
      </section>

      {loading ? <p className="text-sm text-slate-500">Loading profile summary...</p> : null}
    </div>
  );
}
