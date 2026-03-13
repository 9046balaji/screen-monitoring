import { motion } from 'framer-motion';

export default function StatCard({ title, value, subtitle, icon: Icon, delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="rounded-2xl border border-slate-300 dark:border-slate-700 bg-surface p-6 shadow-lg flex flex-col gap-2"
    >
      <div className="flex items-center justify-between">
        <h3 className="text-muted text-sm font-medium">{title}</h3>
        {Icon && <Icon className="w-5 h-5 text-muted" />}
      </div>
      <div className="text-3xl font-bold text-slate-900 dark:text-white">{value}</div>
      {subtitle && <div className="text-sm">{subtitle}</div>}
    </motion.div>
  );
}
