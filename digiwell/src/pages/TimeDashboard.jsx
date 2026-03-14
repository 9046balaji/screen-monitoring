import React, { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import DetoxChallenge from './DetoxChallenge';
import WeeklyPlanPage from './WeeklyPlanPage';
import DailyPlanPage from './DailyPlanPage';
import { Calendar, CheckCircle2, Trophy } from 'lucide-react';

export default function TimeDashboard() {
  const [searchParams] = useSearchParams();
  const tabFromUrl = searchParams.get('tab');
  const initialTab = useMemo(
    () => (tabFromUrl === 'daily' || tabFromUrl === 'weekly' || tabFromUrl === 'timetable' || tabFromUrl === 'detox' ? tabFromUrl : 'detox'),
    [tabFromUrl]
  );
  const [activeTab, setActiveTab] = useState(initialTab);

  useEffect(() => {
    setActiveTab(initialTab);
  }, [initialTab]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 dark:text-white">Time Management</h1>
          <p className="text-slate-600 dark:text-slate-400 mt-1">
            Master your schedule, complete daily tasks, and maintain streaks.
          </p>
        </div>
      </div>

      <div className="bg-surface rounded-2xl border border-slate-200 dark:border-slate-800 p-2 inline-flex items-center gap-2 overflow-x-auto w-full sm:w-auto">
        <button
          onClick={() => setActiveTab('detox')}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-medium transition-all whitespace-nowrap ${
            activeTab === 'detox'
              ? 'bg-primary text-white shadow-md'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <Trophy className="w-5 h-5" />
          <span>7-Day Streak</span>
        </button>
        <button
          onClick={() => setActiveTab('weekly')}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-medium transition-all whitespace-nowrap ${
            activeTab === 'weekly' || activeTab === 'timetable'
              ? 'bg-primary text-white shadow-md'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <Calendar className="w-5 h-5" />
          <span>Weekly Planner</span>
        </button>
        <button
          onClick={() => setActiveTab('daily')}
          className={`flex items-center gap-2 px-5 py-2.5 rounded-xl font-medium transition-all whitespace-nowrap ${
            activeTab === 'daily'
              ? 'bg-primary text-white shadow-md'
              : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          }`}
        >
          <CheckCircle2 className="w-5 h-5" />
          <span>Daily Plan</span>
        </button>
      </div>

      <div className="mt-6">
        {activeTab === 'detox' && <DetoxChallenge />}
        {(activeTab === 'weekly' || activeTab === 'timetable') && <WeeklyPlanPage />}
        {activeTab === 'daily' && <DailyPlanPage />}
      </div>
    </div>
  );
}

