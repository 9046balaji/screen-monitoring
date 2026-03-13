import { useState, useMemo } from 'react';
import { Moon, AlertTriangle, CheckCircle } from 'lucide-react';
import WeeklyLineChart from '../components/charts/WeeklyLineChart';
import FeatureImportanceChart from '../components/charts/FeatureImportanceChart';
import HeatmapChart from '../components/charts/HeatmapChart';
import AddictionHeatmap from '../components/charts/AddictionHeatmap';
import StatCard from '../components/cards/StatCard';
import { weeklyTrend, featureImportances, usageHeatmap, todayHourlyUsage } from '../data/mockData';

export default function Analytics() {
  const [dateRange, setDateRange] = useState('7 Days');

  const insights = useMemo(() => {
    const peakHour = todayHourlyUsage.reduce((prev, current) => (prev.minutes > current.minutes) ? prev : current);
    const worstDay = weeklyTrend.reduce((prev, current) => (prev.minutes > current.minutes) ? prev : current);
    const bestDay = weeklyTrend.reduce((prev, current) => (prev.minutes < current.minutes) ? prev : current);

    const worstDayPercent = Math.round(((worstDay.minutes - worstDay.goal) / worstDay.goal) * 100);
    const bestDayPercent = Math.round(((bestDay.minutes - bestDay.goal) / bestDay.goal) * 100);

    return {
      peakHour: peakHour.hour,
      worstDay: {
        day: worstDay.day,
        subtitle: worstDayPercent > 0 ? `+${worstDayPercent}% above goal` : `${worstDayPercent}% under goal`,
      },
      bestDay: {
        day: bestDay.day,
        subtitle: bestDayPercent <= 0 ? `✓ ${Math.abs(bestDayPercent)}% under goal` : `+${bestDayPercent}% above goal (best)`,
      }
    };
  }, []);

  return (
    <div className="flex flex-col gap-6">
      {/* Date Range Toggle */}
      <div className="flex gap-2">
        {['7 Days', '30 Days', 'All Time'].map((range) => (
          <button
            key={range}
            onClick={() => setDateRange(range)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              dateRange === range
                ? 'bg-primary text-white'
                : 'bg-surface text-muted hover:bg-slate-300 dark:hover:bg-slate-700 hover:text-slate-900 dark:hover:text-white border border-slate-300 dark:border-slate-700'
            }`}
          >
            {range}
          </button>
        ))}
      </div>

      {/* Row 1: Weekly Trend & Feature Importance */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <WeeklyLineChart data={weeklyTrend} delay={0.1} />
        <FeatureImportanceChart data={featureImportances} title="What drives your usage? (Random Forest)" delay={0.2} />
      </div>

      {/* Row 2: Heatmap */}
      <HeatmapChart data={usageHeatmap} delay={0.3} />
      <AddictionHeatmap delay={0.35} />

      {/* Row 3: Insights */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard
          title="Peak Hour"
          value={insights.peakHour}
          icon={Moon}
          delay={0.4}
        />
        <StatCard
          title="Worst Day"
          value={insights.worstDay.day}
          subtitle={<span className="text-danger">{insights.worstDay.subtitle}</span>}
          icon={AlertTriangle}
          delay={0.5}
        />
        <StatCard
          title="Best Day"
          value={insights.bestDay.day}
          subtitle={<span className="text-success">{insights.bestDay.subtitle}</span>}
          icon={CheckCircle}
          delay={0.6}
        />
      </div>

      {/* Bottom text */}
      <div className="text-sm text-muted text-center italic">
        These features were most predictive of your usage category in our Random Forest model (trained on 1000 users).
      </div>
    </div>
  );
}
