import { useEffect, useMemo, useState } from 'react';
import {
  BarChart,
  Bar,
  CartesianGrid,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import {
  getAnalyticsDaily,
  getAnalyticsWeekly,
  getAnalyticsHeatmap,
  getAnalyticsTopApps,
  getAnalyticsInsights,
  getWeeklyAppUsageReport,
} from '../api/digiwell';

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const COLORS = ['#0ea5e9', '#10b981', '#f59e0b', '#ef4444', '#a855f7'];

const formatMinutes = (minutes) => {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h <= 0) return `${m}m`;
  return `${h}h ${m}m`;
};

const heatColor = (value) => {
  if (value >= 20) return '#1d4ed8';
  if (value >= 12) return '#2563eb';
  if (value >= 6) return '#60a5fa';
  if (value > 0) return '#bfdbfe';
  return '#e2e8f0';
};

export default function Analytics() {
  const [daily, setDaily] = useState({ apps: [], summary: {}, battery: { available: false } });
  const [weekly, setWeekly] = useState({ timeline: [] });
  const [heatmap, setHeatmap] = useState([]);
  const [topApps, setTopApps] = useState([]);
  const [insights, setInsights] = useState([]);
  const [weeklyReport, setWeeklyReport] = useState({
    total_screen_time: 0,
    total_screen_time_hours: 0,
    average_daily_usage: 0,
    average_daily_usage_hours: 0,
    apps: [],
    categories: [],
    top_apps: [],
    insights: [],
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    async function loadAnalytics() {
      try {
        const [dailyRes, weeklyRes, heatRes, topRes, insightRes, weeklyAppReportRes] = await Promise.all([
          getAnalyticsDaily(),
          getAnalyticsWeekly(),
          getAnalyticsHeatmap(),
          getAnalyticsTopApps(),
          getAnalyticsInsights(),
          getWeeklyAppUsageReport(),
        ]);

        if (!active) return;

        setDaily(dailyRes || { apps: [], summary: {}, battery: { available: false } });
        setWeekly(weeklyRes || { timeline: [] });
        setHeatmap(Array.isArray(heatRes) ? heatRes : []);
        setTopApps(Array.isArray(topRes) ? topRes : []);
        setInsights(Array.isArray(insightRes?.insights) ? insightRes.insights : []);
        setWeeklyReport(weeklyAppReportRes || {
          total_screen_time: 0,
          total_screen_time_hours: 0,
          average_daily_usage: 0,
          average_daily_usage_hours: 0,
          apps: [],
          categories: [],
          top_apps: [],
          insights: [],
        });
      } catch (e) {
        if (active) {
          setDaily({ apps: [], summary: {}, battery: { available: false } });
          setWeekly({ timeline: [] });
          setHeatmap([]);
          setTopApps([]);
          setInsights(['Unable to load analytics data. Ensure backend tracker is running.']);
          setWeeklyReport({
            total_screen_time: 0,
            total_screen_time_hours: 0,
            average_daily_usage: 0,
            average_daily_usage_hours: 0,
            apps: [],
            categories: [],
            top_apps: [],
            insights: [],
          });
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    loadAnalytics();
    return () => {
      active = false;
    };
  }, []);

  const dailyBarData = useMemo(() => {
    return (daily.apps || []).slice(0, 8).map((a) => ({
      app: a.app,
      minutes: a.minutes,
    }));
  }, [daily]);

  const weeklyLineData = useMemo(() => {
    return (weekly.timeline || []).map((d) => ({ day: d.day, minutes: d.minutes }));
  }, [weekly]);

  const weeklyAppBarData = useMemo(() => {
    return (weeklyReport.apps || []).map((a) => ({
      app: a.app,
      minutes: a.minutes,
      percentage: a.percentage,
    }));
  }, [weeklyReport]);

  const weeklyCategoryPie = useMemo(() => {
    return (weeklyReport.categories || []).map((c) => ({
      category: c.category,
      minutes: c.minutes,
      percentage: c.percentage,
    }));
  }, [weeklyReport]);

  const heatRows = useMemo(() => {
    const map = new Map();
    (heatmap || []).forEach((c) => {
      map.set(`${c.hour}-${c.day}`, c.value || 0);
    });

    return Array.from({ length: 24 }, (_, hour) => ({
      hour,
      values: DAYS.map((day) => map.get(`${hour}-${day}`) || 0),
    }));
  }, [heatmap]);

  return (
    <div className="flex flex-col gap-6">
      <div className="rounded-2xl border border-slate-300 dark:border-slate-700 bg-surface p-5 shadow-sm">
        <h2 className="text-xl font-semibold text-slate-900 dark:text-white">Screen Time Summary</h2>
        <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="rounded-xl bg-slate-100 dark:bg-slate-800 p-4">
            <div className="text-xs text-slate-500">Total Today</div>
            <div className="text-2xl font-semibold">{formatMinutes(daily.summary?.total_minutes || 0)}</div>
          </div>
          <div className="rounded-xl bg-slate-100 dark:bg-slate-800 p-4">
            <div className="text-xs text-slate-500">Productive</div>
            <div className="text-2xl font-semibold">{formatMinutes(daily.summary?.productive_minutes || 0)}</div>
          </div>
          <div className="rounded-xl bg-slate-100 dark:bg-slate-800 p-4">
            <div className="text-xs text-slate-500">Distracting</div>
            <div className="text-2xl font-semibold">{formatMinutes(daily.summary?.distracting_minutes || 0)}</div>
          </div>
          <div className="rounded-xl bg-slate-100 dark:bg-slate-800 p-4">
            <div className="text-xs text-slate-500">Productivity Ratio</div>
            <div className="text-2xl font-semibold">{Math.round((daily.summary?.productivity_ratio || 0) * 100)}%</div>
          </div>
        </div>
        {daily.battery?.available ? (
          <div className="mt-4 text-sm text-slate-600 dark:text-slate-300">
            Battery: screen on {daily.battery.screen_on_time}, active {daily.battery.system_active_time}
          </div>
        ) : (
          <div className="mt-4 text-sm text-slate-500">Battery report unavailable on this device/session.</div>
        )}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="rounded-2xl border border-slate-300 dark:border-slate-700 bg-surface p-5 shadow-sm h-[360px]">
          <h3 className="font-semibold mb-4">Daily App Usage</h3>
          <ResponsiveContainer width="100%" height="90%">
            <BarChart data={dailyBarData} margin={{ top: 8, right: 8, left: 0, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="app" interval={0} angle={-20} textAnchor="end" height={60} />
              <YAxis />
              <Tooltip />
              <Bar dataKey="minutes" fill="#0284c7" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-2xl border border-slate-300 dark:border-slate-700 bg-surface p-5 shadow-sm h-[360px]">
          <h3 className="font-semibold mb-4">Weekly App Usage</h3>
          <ResponsiveContainer width="100%" height="90%">
            <LineChart data={weeklyLineData} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="minutes" stroke="#16a34a" strokeWidth={3} dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-300 dark:border-slate-700 bg-surface p-5 shadow-sm">
        <h3 className="text-lg font-semibold mb-4">Weekly Usage Report</h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="rounded-xl bg-slate-100 dark:bg-slate-800 p-4">
            <div className="text-xs text-slate-500">Total Screen Time (Week)</div>
            <div className="text-2xl font-semibold">{weeklyReport.total_screen_time_hours || 0}h</div>
          </div>
          <div className="rounded-xl bg-slate-100 dark:bg-slate-800 p-4">
            <div className="text-xs text-slate-500">Average Daily Usage</div>
            <div className="text-2xl font-semibold">{formatMinutes(Math.round(weeklyReport.average_daily_usage || 0))}</div>
          </div>
          <div className="rounded-xl bg-slate-100 dark:bg-slate-800 p-4">
            <div className="text-xs text-slate-500">Most Used App</div>
            <div className="text-xl font-semibold">{weeklyReport.top_apps?.[0]?.app || 'N/A'}</div>
          </div>
          <div className="rounded-xl bg-slate-100 dark:bg-slate-800 p-4">
            <div className="text-xs text-slate-500">Top Category</div>
            <div className="text-xl font-semibold">{weeklyReport.categories?.[0]?.category || 'N/A'}</div>
          </div>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <div className="h-[320px] rounded-xl border border-slate-200 dark:border-slate-700 p-4 overflow-x-auto">
            <h4 className="font-medium mb-3">Weekly App Usage (All Apps)</h4>
            <div style={{ minWidth: `${Math.max(640, weeklyAppBarData.length * 80)}px`, height: '90%' }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={weeklyAppBarData} margin={{ top: 8, right: 8, left: 0, bottom: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="app" interval={0} angle={-20} textAnchor="end" height={60} />
                  <YAxis />
                  <Tooltip formatter={(value) => `${value} min`} />
                  <Bar dataKey="minutes" fill="#2563eb" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="h-[320px] rounded-xl border border-slate-200 dark:border-slate-700 p-4">
            <h4 className="font-medium mb-3">Category Usage Breakdown</h4>
            <ResponsiveContainer width="100%" height="90%">
              <PieChart>
                <Pie data={weeklyCategoryPie} dataKey="minutes" nameKey="category" outerRadius={95} label={(d) => `${d.category} ${Math.round(d.percentage || 0)}%`}>
                  {weeklyCategoryPie.map((entry, index) => (
                    <Cell key={`weekly-cat-${entry.category}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => `${value} min`} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mt-6">
          <div className="rounded-xl border border-slate-200 dark:border-slate-700 p-4">
            <h4 className="font-medium mb-3">All Apps This Week</h4>
            <div className="space-y-2 max-h-[260px] overflow-y-auto pr-1">
              {(weeklyReport.apps || []).map((app, idx) => (
                <div key={`top-week-${app.app}-${idx}`} className="flex items-center justify-between text-sm">
                  <span>{idx + 1}. {app.app}</span>
                  <span className="font-medium">{formatMinutes(app.minutes)} ({Math.round(app.percentage || 0)}%)</span>
                </div>
              ))}
              {(weeklyReport.apps || []).length === 0 && (
                <div className="text-sm text-slate-500">No weekly app data yet.</div>
              )}
            </div>
          </div>

          <div className="rounded-xl border border-slate-200 dark:border-slate-700 p-4">
            <h4 className="font-medium mb-3">Weekly AI Insights</h4>
            <ul className="list-disc pl-5 space-y-2 text-sm text-slate-700 dark:text-slate-200">
              {(weeklyReport.insights || []).map((text, idx) => (
                <li key={`weekly-insight-${idx}`}>{text}</li>
              ))}
              {(weeklyReport.insights || []).length === 0 && (
                <li>No weekly insights yet. Keep tracker running for a few days.</li>
              )}
            </ul>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div className="rounded-2xl border border-slate-300 dark:border-slate-700 bg-surface p-5 shadow-sm overflow-x-auto">
          <h3 className="font-semibold mb-4">AI Productivity Heatmap (Hour x Day)</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '55px repeat(7, minmax(30px, 1fr))', gap: '4px', minWidth: '460px' }}>
            <div />
            {DAYS.map((d) => (
              <div key={d} className="text-xs text-center text-slate-500">{d}</div>
            ))}
            {heatRows.map((r) => (
              <div key={`row-${r.hour}`} style={{ display: 'contents' }}>
                <div key={`h-${r.hour}`} className="text-xs text-right pr-1 text-slate-500">{`${String(r.hour).padStart(2, '0')}:00`}</div>
                {r.values.map((v, idx) => (
                  <div key={`${r.hour}-${DAYS[idx]}`} title={`${DAYS[idx]} ${r.hour}:00 - ${v}`} style={{ height: '18px', borderRadius: '4px', backgroundColor: heatColor(v) }} />
                ))}
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-300 dark:border-slate-700 bg-surface p-5 shadow-sm">
          <h3 className="font-semibold mb-4">Most Used Apps (Top 5)</h3>
          <div className="h-[220px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={topApps} dataKey="minutes" nameKey="app" outerRadius={80} label>
                  {topApps.map((entry, index) => (
                    <Cell key={`cell-${entry.app}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-2 space-y-1">
            {topApps.map((app) => (
              <div key={app.rank} className="text-sm text-slate-700 dark:text-slate-200">
                {app.rank}. {app.app} - {formatMinutes(app.minutes)}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-slate-300 dark:border-slate-700 bg-surface p-5 shadow-sm">
        <h3 className="font-semibold mb-3">AI Insights</h3>
        {loading ? (
          <div className="text-sm text-slate-500">Loading analytics insights...</div>
        ) : (
          <ul className="list-disc pl-5 space-y-2 text-sm text-slate-700 dark:text-slate-200">
            {insights.length > 0 ? insights.map((ins, idx) => <li key={`${idx}-${ins}`}>{ins}</li>) : <li>No insights yet. Keep tracker running to gather data.</li>}
          </ul>
        )}
      </div>

      {!loading && dailyBarData.length === 0 && (
        <div className="text-sm text-slate-500 text-center border border-dashed border-slate-300 dark:border-slate-700 rounded-xl p-4">
          No app usage records found yet. Start the backend and keep apps active for a few minutes to populate analytics.
        </div>
      )}
    </div>
  );
}
