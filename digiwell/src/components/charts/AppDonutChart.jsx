import React, { useEffect, useState } from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { motion } from 'framer-motion';
import { getDailyUsage } from '../../api/digiwell';

export default function AppDonutChart({ data: initialData, delay = 0 }) {
  const [data, setData] = useState(initialData || []);

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await getDailyUsage();
        if (res && res.top_apps) {
          const formatted = res.top_apps.map(app => ({
            name: app.app_name,
            minutes: Math.round((app.total_seconds || 0) / 60),
          }));
          // Add predefined colors to formatted
          const COLORS = ['#ef4444', '#f59e0b', '#f97316', '#3b82f6', '#10b981', '#8b5cf6', '#6366f1'];
          formatted.forEach((d, i) => d.color = COLORS[i % COLORS.length]);
          setData(formatted);
        }
      } catch (e) {
        console.error("Failed to load daily usage", e);
      }
    }
    fetchData();
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="rounded-2xl border border-slate-300 dark:border-slate-700 bg-surface p-6 shadow-lg flex flex-col gap-4 h-[400px]"
    >
      <h3 className="text-lg font-semibold text-slate-900 dark:text-white">App Breakdown</h3>
      <div className="flex-1 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={80}
              outerRadius={110}
              paddingAngle={2}
              dataKey="minutes"
              stroke="none"
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{ backgroundColor: '#1E293B', borderColor: '#334155', color: '#fff', borderRadius: '8px' }}
              itemStyle={{ color: '#fff' }}
            />
            <Legend verticalAlign="bottom" height={36} iconType="circle" wrapperStyle={{ fontSize: '12px', color: '#94A3B8' }} />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}
