import { useEffect, useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Brain, Download, FileBarChart2, FileText, Sparkles } from 'lucide-react';
import {
  downloadWeeklyReport,
  downloadWeeklySummaryReport,
  downloadMonthlySummaryReport,
  getMonthlyReport,
  getReportsProductivityScore,
  getWeeklyReport,
} from '../api/digiwell';

const PIE_COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#14B8A6'];

function TinyCard({ label, value, note }) {
  return (
    <div className="rounded-xl border border-slate-300 dark:border-slate-700 bg-base p-4">
      <p className="text-xs text-slate-600 dark:text-slate-400">{label}</p>
      <p className="mt-1 text-2xl font-bold text-slate-900 dark:text-white">{value}</p>
      {note ? <p className="mt-1 text-xs text-slate-500 dark:text-slate-500">{note}</p> : null}
    </div>
  );
}

function Heatmap({ data }) {
  const rows = useMemo(() => {
    const dayMap = {};
    (data || []).forEach((cell) => {
      if (!dayMap[cell.day]) dayMap[cell.day] = [];
      dayMap[cell.day].push(cell);
    });
    return Object.entries(dayMap).map(([day, cells]) => ({ day, cells: cells.sort((a, b) => a.hour - b.hour) }));
  }, [data]);

  const colorFor = (value) => {
    if (value >= 20) return 'bg-red-500';
    if (value >= 12) return 'bg-amber-500';
    if (value >= 6) return 'bg-cyan-500';
    if (value > 0) return 'bg-emerald-500';
    return 'bg-slate-200 dark:bg-slate-800';
  };

  return (
    <div className="overflow-x-auto">
      <div className="min-w-[760px] space-y-2">
        {rows.map((row) => (
          <div key={row.day} className="flex items-center gap-2">
            <div className="w-10 text-xs text-slate-600 dark:text-slate-400">{row.day}</div>
            <div className="grid gap-1" style={{ gridTemplateColumns: 'repeat(24, minmax(0, 1fr))' }}>
              {row.cells.map((cell) => (
                <div key={`${row.day}-${cell.hour}`} className={`h-4 w-4 rounded-sm ${colorFor(cell.value)}`} title={`${row.day} ${cell.hour}:00 - ${cell.value}`} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Reports() {
  const [period, setPeriod] = useState('weekly');
  const [weekly, setWeekly] = useState(null);
  const [monthly, setMonthly] = useState(null);
  const [score, setScore] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    Promise.all([getWeeklyReport(), getMonthlyReport(), getReportsProductivityScore('weekly')])
      .then(([w, m, s]) => {
        if (!mounted) return;
        setWeekly(w);
        setMonthly(m);
        setScore(s);
      })
      .catch((err) => {
        console.error('Failed to load reports:', err);
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, []);

  const active = period === 'weekly' ? weekly : monthly;

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-300 dark:border-slate-700 bg-surface p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-indigo-500/20 p-2 text-indigo-500">
              <FileText size={22} />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Reports & Insights Hub</h1>
              <p className="text-sm text-slate-600 dark:text-slate-400">Weekly and monthly behavioral analytics across all DigiWell modules.</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button onClick={downloadWeeklyReport} className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90">
              <Download size={16} /> Weekly PDF
            </button>
            <button onClick={downloadWeeklySummaryReport} className="inline-flex items-center gap-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-base px-4 py-2 text-sm font-semibold text-slate-800 dark:text-slate-200">
              <FileBarChart2 size={16} /> Weekly Summary
            </button>
            <button onClick={downloadMonthlySummaryReport} className="inline-flex items-center gap-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-base px-4 py-2 text-sm font-semibold text-slate-800 dark:text-slate-200">
              <FileBarChart2 size={16} /> Monthly Summary
            </button>
          </div>
        </div>
      </section>

      <section className="flex gap-2">
        <button onClick={() => setPeriod('weekly')} className={`rounded-lg px-4 py-2 text-sm font-semibold ${period === 'weekly' ? 'bg-primary text-white' : 'bg-base text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-700'}`}>Weekly Report</button>
        <button onClick={() => setPeriod('monthly')} className={`rounded-lg px-4 py-2 text-sm font-semibold ${period === 'monthly' ? 'bg-primary text-white' : 'bg-base text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-700'}`}>Monthly Report</button>
      </section>

      <section className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <TinyCard label="Total Screen Time" value={`${active?.totals?.screen_time_hours ?? 0}h`} note={period === 'weekly' ? 'Last 7 days' : 'Last 30 days'} />
        <TinyCard label="Task Completion" value={`${active?.totals?.task_completion_rate ?? 0}%`} />
        <TinyCard label="Focus Mode Usage" value={`${active?.totals?.focus_hours ?? 0}h`} />
        <TinyCard label="Productivity Score" value={`${score?.score ?? active?.productivity_score?.score ?? 0}/100`} />
      </section>

      <section className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <div className="rounded-2xl border border-slate-300 dark:border-slate-700 bg-surface p-5">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Weekly Screen Time Graph</h3>
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={active?.charts?.screen_time_series || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.2} />
                <XAxis dataKey="day" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="hours" stroke="#3B82F6" strokeWidth={2.5} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-300 dark:border-slate-700 bg-surface p-5">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white">App Usage Pie Chart</h3>
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={active?.usage?.category_breakdown || []} dataKey="hours" nameKey="category" outerRadius={90} label>
                  {(active?.usage?.category_breakdown || []).map((entry, index) => (
                    <Cell key={`pie-${entry.category}-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <div className="rounded-2xl border border-slate-300 dark:border-slate-700 bg-surface p-5">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Task Completion Graph</h3>
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={active?.charts?.task_completion_series || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.2} />
                <XAxis dataKey="day" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="planned" fill="#94A3B8" radius={[6, 6, 0, 0]} />
                <Bar dataKey="completed" fill="#10B981" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-300 dark:border-slate-700 bg-surface p-5">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Mood Trend Line Chart</h3>
          <div className="mt-4 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={active?.charts?.mood_trend || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.2} />
                <XAxis dataKey="date" />
                <YAxis domain={[0, 5]} />
                <Tooltip />
                <Line type="monotone" dataKey="avg_mood" stroke="#F59E0B" strokeWidth={2.5} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-300 dark:border-slate-700 bg-surface p-5">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Productivity Heatmap</h3>
        <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">Higher intensity indicates denser activity windows during the selected period.</p>
        <div className="mt-4">
          <Heatmap data={active?.charts?.productivity_heatmap || []} />
        </div>
      </section>

      <section className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <div className="rounded-2xl border border-slate-300 dark:border-slate-700 bg-surface p-5">
          <h3 className="inline-flex items-center gap-2 text-lg font-semibold text-slate-900 dark:text-white">
            <Brain size={18} /> Productivity Score Formula
          </h3>
          <div className="mt-4 rounded-lg bg-base p-4 text-sm text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-700">
            <p>productivity_score = (focus_hours * 0.4) + (task_completion_rate * 0.3) + (low_entertainment_usage * 0.2) + (mood_score * 0.1)</p>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <TinyCard label="Focus Component" value={Math.round(score?.components?.focus_component ?? active?.productivity_score?.components?.focus_component ?? 0)} />
            <TinyCard label="Task Component" value={Math.round(score?.components?.task_completion_rate ?? active?.productivity_score?.components?.task_completion_rate ?? 0)} />
            <TinyCard label="Low Entertainment" value={Math.round(score?.components?.low_entertainment_usage ?? active?.productivity_score?.components?.low_entertainment_usage ?? 0)} />
            <TinyCard label="Mood Component" value={Math.round(score?.components?.mood_score_component ?? active?.productivity_score?.components?.mood_score_component ?? 0)} />
          </div>
        </div>

        <div className="rounded-2xl border border-slate-300 dark:border-slate-700 bg-surface p-5">
          <h3 className="inline-flex items-center gap-2 text-lg font-semibold text-slate-900 dark:text-white">
            <Sparkles size={18} /> AI Insights
          </h3>
          <div className="mt-4 space-y-3">
            {(active?.ai_insights || []).map((insight, idx) => (
              <div key={`insight-${idx}`} className="rounded-lg border border-slate-300 dark:border-slate-700 bg-base p-3 text-sm text-slate-700 dark:text-slate-300">
                {insight}
              </div>
            ))}
          </div>
        </div>
      </section>

      {loading ? <p className="text-sm text-slate-500">Loading report analytics...</p> : null}
    </div>
  );
}
