import { motion } from 'framer-motion';
import ProgressBar from '../ui/ProgressBar';

export default function MentalHealthCard({ scores, delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="rounded-2xl border border-slate-300 dark:border-slate-700 bg-surface p-6 shadow-lg flex flex-col gap-6"
    >
      <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Mental Health Risk Factors</h3>
      <div className="flex flex-col gap-4">
        <ProgressBar label="Distraction" value={scores.distractionScore} colorClass={scores.distractionScore >= 4 ? 'bg-danger' : scores.distractionScore === 3 ? 'bg-warning' : 'bg-success'} />
        <ProgressBar label="Restlessness" value={scores.restlessnessScore} colorClass={scores.restlessnessScore >= 4 ? 'bg-danger' : scores.restlessnessScore === 3 ? 'bg-warning' : 'bg-success'} />
        <ProgressBar label="Depression Risk" value={scores.depressionScore} colorClass={scores.depressionScore >= 4 ? 'bg-danger' : scores.depressionScore === 3 ? 'bg-warning' : 'bg-success'} />
        <ProgressBar label="Sleep Issues" value={scores.sleepIssuesScore} colorClass={scores.sleepIssuesScore >= 4 ? 'bg-danger' : scores.sleepIssuesScore === 3 ? 'bg-warning' : 'bg-success'} />
        <ProgressBar label="Concentration" value={scores.concentrationScore} colorClass={scores.concentrationScore >= 4 ? 'bg-danger' : scores.concentrationScore === 3 ? 'bg-warning' : 'bg-success'} />
      </div>
    </motion.div>
  );
}
