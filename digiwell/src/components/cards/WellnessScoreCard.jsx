import { motion } from 'framer-motion';
import { CircularProgressbar, buildStyles } from 'react-circular-progressbar';
import 'react-circular-progressbar/dist/styles.css';

export default function WellnessScoreCard({ score, projectedScore, label, subtext, delay = 0 }) {
  let color = '#10B981'; // success
  if (score < 50) color = '#EF4444'; // danger
  else if (score <= 75) color = '#F59E0B'; // warning

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="rounded-2xl border border-slate-300 dark:border-slate-700 bg-surface p-6 shadow-lg flex flex-col items-center justify-center text-center gap-4 relative"
    >
      <h3 className="text-lg font-semibold text-slate-900 dark:text-white">{label}</h3>
      <div className="w-48 h-48">
        <CircularProgressbar
          value={score}
          text={`${score}`}
          styles={buildStyles({
            pathColor: color,
            textColor: color,
            trailColor: '#334155',
            textSize: '24px',
          })}
        />
      </div>
      <p className="text-sm text-muted max-w-[200px]">{subtext}</p>
      
      {projectedScore !== undefined && (
        <div className="mt-2 bg-slate-200 dark:bg-slate-800 rounded px-4 py-2 text-xs">
          <span className="text-slate-600 dark:text-slate-400">30-Day Projection (Digital Twin): </span>
          <span className={projectedScore >= score ? "text-green-400 font-bold" : "text-red-400 font-bold"}>
             {projectedScore}
          </span>
        </div>
      )}
    </motion.div>
  );
}
