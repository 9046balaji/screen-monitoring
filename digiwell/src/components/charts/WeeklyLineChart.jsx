import { ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { motion } from 'framer-motion';

export default function WeeklyLineChart({ data, delay = 0 }) {
  // Add computed fields for red/green area fill
  const enriched = data.map(d => ({
    ...d,
    overGoal: d.minutes > d.goal ? d.minutes : d.goal,
    underGoal: d.minutes <= d.goal ? d.minutes : d.goal,
  }));

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="rounded-2xl border border-slate-700 bg-surface p-6 shadow-lg flex flex-col gap-4 h-[400px]"
    >
      <h3 className="text-lg font-semibold text-white">Weekly Trend vs Goal</h3>
      <div className="flex-1 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={enriched} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
            <XAxis dataKey="day" stroke="#94A3B8" fontSize={12} tickLine={false} axisLine={false} />
            <YAxis stroke="#94A3B8" fontSize={12} tickLine={false} axisLine={false} />
            <Tooltip
              contentStyle={{ backgroundColor: '#1E293B', borderColor: '#334155', color: '#fff', borderRadius: '8px' }}
            />
            <Legend verticalAlign="top" height={36} iconType="circle" wrapperStyle={{ fontSize: '12px', color: '#94A3B8' }} />
            <Area type="monotone" dataKey="overGoal" stroke="none" fill="#EF4444" fillOpacity={0.2} legendType="none" />
            <Area type="monotone" dataKey="underGoal" stroke="none" fill="#10B981" fillOpacity={0.1} legendType="none" />
            <Line type="monotone" dataKey="minutes" name="Actual Usage" stroke="#6366F1" strokeWidth={3} dot={{ r: 4, fill: '#6366F1' }} activeDot={{ r: 6 }} />
            <Line type="monotone" dataKey="goal" name="Daily Goal" stroke="#10B981" strokeWidth={2} strokeDasharray="5 5" dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}
