import React from 'react';
import { Sparkles, Brain, Wind, Clock } from 'lucide-react';
import { motion } from 'framer-motion';

export default function AIInsightCard({ analysis, onStartMicrotask }) {
  if (!analysis) return null;

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-indigo-50 border border-indigo-200 dark:bg-indigo-900/20 dark:border-indigo-800 rounded-xl p-6 shadow-sm mb-6"
    >
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2 bg-indigo-100 dark:bg-indigo-800 text-indigo-600 dark:text-indigo-300 rounded-lg">
          <Sparkles className="w-6 h-6" />
        </div>
        <div>
          <h3 className="text-lg font-bold text-indigo-900 dark:text-indigo-100">AI Reflection Insight</h3>
          <p className="text-sm text-indigo-700 dark:text-indigo-300">
            Primary Emotion: <strong>{analysis.ai_primary_emotion || 'Analyzing'}</strong>
          </p>
        </div>
      </div>

      <div className="space-y-4">
        {analysis.ai_distortion && analysis.ai_distortion.length > 0 && (
          <div className="flex items-start gap-2">
            <Brain className="w-5 h-5 text-indigo-500 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm font-semibold text-indigo-800 dark:text-indigo-200">Cognitive Distortions Detected</p>
              <div className="flex flex-wrap gap-2 mt-1">
                {analysis.ai_distortion.map((d, i) => (
                  <span key={i} className="text-xs bg-white dark:bg-indigo-950 text-indigo-600 dark:text-indigo-300 px-2 py-1 rounded-md border border-indigo-200 dark:border-indigo-700">
                    {d}
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}

        {analysis.ai_reframe && (
          <div className="bg-white/60 dark:bg-indigo-950/50 p-3 rounded-lg border border-indigo-100 dark:border-indigo-800">
            <p className="text-sm text-indigo-900 dark:text-indigo-100 italic">
              "{analysis.ai_reframe}"
            </p>
          </div>
        )}

        {analysis.ai_microtask && analysis.ai_microtask.instruction && (
          <div className="flex items-center justify-between bg-white dark:bg-indigo-950 p-4 rounded-xl border border-indigo-200 dark:border-indigo-700 mt-2">
            <div className="flex items-center gap-3">
              <div className="text-indigo-500">
                {analysis.ai_microtask.type === 'breathing' ? <Wind className="w-6 h-6" /> : <Clock className="w-6 h-6" />}
              </div>
              <div>
                <p className="text-sm font-bold text-indigo-900 dark:text-indigo-100">Recommended Micro-task</p>
                <p className="text-xs text-indigo-700 dark:text-indigo-300">{analysis.ai_microtask.instruction}</p>
              </div>
            </div>
            <button 
              onClick={onStartMicrotask}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors whitespace-nowrap"
            >
              Start {analysis.ai_microtask.duration_minutes}m
            </button>
          </div>
        )}
      </div>
    </motion.div>
  );
}
