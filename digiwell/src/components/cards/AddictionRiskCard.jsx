import React from 'react';
import { motion } from 'framer-motion';
import { CircularProgressbar, buildStyles } from 'react-circular-progressbar';
import 'react-circular-progressbar/dist/styles.css';
import { BrainCircuit } from 'lucide-react';

export default function AddictionRiskCard({ score, riskLevel, socialHours, totalHours, projectedScore, delay = 0 }) {
  let color = '#10B981'; // success / low risk
  if (riskLevel === 'High') color = '#EF4444'; // danger
  else if (riskLevel === 'Moderate') color = '#F59E0B'; // warning

  // Normalize score for UI: we usually think of a "Risk Score", but the API returns "score" where lower is higher risk. Wait, 
  // API logic: base 100, -10 for social, -5 for total screens. So 100 = Great Wellness, Low Risk. 0 = Terrible Wellness, High Risk.
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="rounded-2xl border border-slate-300 dark:border-slate-700 bg-surface p-6 shadow-lg flex flex-col h-full"
    >
      <div className="flex items-center gap-2 mb-4">
        <BrainCircuit className="text-primary" size={24} />
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Digital Wellness Score</h3>
      </div>
      
      <div className="flex-1 flex flex-col items-center justify-center">
        <div className="flex justify-between w-full mb-4">
            <div className="w-32 h-32 mx-auto">
              <CircularProgressbar
                value={score}
                text={`${score}`}
                styles={buildStyles({
                  pathColor: color,
                  textColor: color,
                  trailColor: '#334155',
                  textSize: '28px',
                })}
              />
            </div>
            {projectedScore !== undefined && (
               <div className="flex flex-col items-center justify-center text-center p-2 rounded-lg bg-base border border-slate-300 dark:border-slate-700 w-24">
                 <span className="text-xs text-slate-600 dark:text-slate-400">30-Day Twin</span>
                 <span className={`text-xl font-bold mt-1 ${projectedScore > score ? 'text-green-400' : 'text-red-400'}`}>
                    {projectedScore}
                 </span>
               </div>
            )}
        </div>
        
        <div className="text-center w-full">
          <p className="text-lg font-medium text-slate-900 dark:text-white mb-1">
            Risk: <span style={{ color }}>{riskLevel}</span>
          </p>
          <div className="flex justify-between mt-4 bg-base rounded-lg p-3 text-sm">
            <div className="text-center">
              <p className="text-muted mb-1">Social</p>
              <p className="font-semibold text-slate-900 dark:text-white">{socialHours}h</p>
            </div>
            <div className="border-l border-slate-300 dark:border-slate-700 mx-2"></div>
            <div className="text-center">
              <p className="text-muted mb-1">Total</p>
              <p className="font-semibold text-slate-900 dark:text-white">{totalHours}h</p>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
