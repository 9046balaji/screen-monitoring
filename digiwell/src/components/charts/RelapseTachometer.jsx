import React from 'react';
import { motion } from 'framer-motion';
import { AlertOctagon } from 'lucide-react';

export default function RelapseTachometer({ risk, topFeatures, onStartFocus }) {
  const percentage = Math.round(risk * 100);
  
  // Calculate dial color based on risk
  let color = 'text-green-500';
  let bgColor = 'bg-green-50 z-[1]';
  let message = 'Low Risk';
  if (risk > 0.4) { color = 'text-yellow-500'; bgColor = 'bg-yellow-50 z-[1]'; message = 'Moderate Risk'; }
  if (risk > 0.7) { color = 'text-red-500'; bgColor = 'bg-red-50 z-[1]'; message = 'Critical Risk'; }

  return (
    <div className={`p-6 rounded-2xl border ${risk > 0.7 ? 'border-red-200 dark:border-red-900/50' : 'border-slate-200 dark:border-slate-800'} ${bgColor} shadow-sm flex flex-col items-center justify-center relative overflow-hidden mb-8`}>
      <h3 className="text-lg font-bold text-slate-800 dark:text-slate-200 mb-2 flex items-center gap-2">
        <AlertOctagon className={color} />
        Relapse & Doomscroll Predictor
      </h3>
      
      <div className="flex flex-col md:flex-row items-center gap-6 mt-4 w-full justify-center">
        {/* Tachometer Visual */}
        <div className="relative w-48 h-24 overflow-hidden flex-shrink-0">
          <div className="absolute top-0 left-0 w-48 h-48 rounded-full border-[1.5rem] border-slate-200 dark:border-slate-700 pointer-events-none"></div>
          <motion.div 
            className="absolute top-0 left-0 w-48 h-48 rounded-full border-[1.5rem] border-transparent border-t-[currentcolor] border-l-[currentcolor] rotate-45"
            style={{ color: risk > 0.7 ? '#ef4444' : risk > 0.4 ? '#eab308' : '#22c55e' }}
            initial={{ rotate: -135 }}
            animate={{ rotate: -135 + (percentage / 100) * 180 }}
            transition={{ duration: 1.5, ease: "easeOut" }}
          ></motion.div>
          <div className="absolute bottom-0 left-0 right-0 text-center pb-2">
            <span className={`text-3xl font-black ${color}`}>{percentage}%</span>
          </div>
        </div>

        {/* Info & CTA */}
        <div className="flex flex-col items-center md:items-start text-center md:text-left gap-3">
          <p className={`font-semibold ${color}`}>{message}</p>
          {topFeatures && topFeatures.length > 0 && (
            <div className="text-sm text-slate-600 dark:text-slate-400">
              <span className="font-medium">Trigger Factors:</span> {topFeatures.join(', ')}
            </div>
          )}
          
          {risk > 0.7 && (
            <div className="mt-2">
              <p className="text-sm text-red-600 dark:text-red-400 font-medium mb-2">
                You usually doomscroll at this time.
              </p>
              <button 
                onClick={onStartFocus}
                className="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-6 rounded-lg transition-colors shadow-md"
              >
                Start Focus Mode Now
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
