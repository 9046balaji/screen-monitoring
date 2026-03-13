import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { motion } from 'framer-motion';

export default function FeatureImportanceChart({ data, title, delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="rounded-2xl border border-slate-700 bg-surface p-6 shadow-lg flex flex-col gap-4 h-[400px]"
    >
      <h3 className="text-lg font-semibold text-white">{title}</h3>
      <div className="flex-1 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 10, right: 30, left: 40, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={true} vertical={false} />
            <XAxis type="number" stroke="#94A3B8" fontSize={12} tickLine={false} axisLine={false} />
            <YAxis dataKey="feature" type="category" stroke="#94A3B8" fontSize={12} tickLine={false} axisLine={false} />
            <Tooltip
              cursor={{ fill: '#334155', opacity: 0.4 }}
              contentStyle={{ backgroundColor: '#1E293B', borderColor: '#334155', color: '#fff', borderRadius: '8px' }}
            />
            <Bar dataKey="importance" fill="#6366F1" radius={[0, 4, 4, 0]} barSize={20} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}
