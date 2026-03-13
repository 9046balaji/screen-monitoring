import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, Clock, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { getInterventions, resolveIntervention } from '../../api/digiwell';
import use2020Timer from '../../hooks/use2020Timer';

export default function InterventionPopup() {
  const [activeIntervention, setActiveIntervention] = useState(null);
  const navigate = useNavigate();
  // Using use2020Timer to have access to timers if needed or just navigate

  useEffect(() => {
    // Poll every 10 seconds
    const interval = setInterval(async () => {
      try {
        const interventions = await getInterventions();
        const pending = interventions.find(i => i.status === 'pending');
        if (pending) {
          setActiveIntervention(pending);
        } else {
          setActiveIntervention(null);
        }
      } catch (e) {
        console.error("Failed fetching interventions", e);
      }
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  const handleStartFocus = async () => {
    if (activeIntervention) {
      await resolveIntervention(activeIntervention.id);
      setActiveIntervention(null);
      navigate('/focus');
    }
  };

  const handleIgnore = async () => {
    if (activeIntervention) {
      await resolveIntervention(activeIntervention.id);
      setActiveIntervention(null);
    }
  };

  return (
    <AnimatePresence>
      {activeIntervention && (
        <motion.div
          initial={{ opacity: 0, scale: 0.9, y: 50 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.9, y: 50 }}
          className="fixed bottom-10 right-10 z-50 w-96 rounded-2xl bg-slate-100 dark:bg-slate-900 border border-red-500/50 shadow-2xl p-6 overflow-hidden"
        >
          {/* Animated red glow background */}
          <div className="absolute inset-0 bg-red-500/10 animate-pulse pointer-events-none" />
          
          <div className="relative z-10 flex items-start gap-4">
            <div className="bg-red-500/20 p-3 rounded-full text-red-400">
              <AlertTriangle size={28} />
            </div>
            <div className="flex-1">
              <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2">⚠️ DigiWell Intervention</h3>
              <p className="text-slate-700 dark:text-slate-300 leading-relaxed mb-4">
                Doomscrolling detected on <span className="font-semibold text-slate-900 dark:text-white">{activeIntervention.app_name}</span>. Start Focus Mode?
              </p>
              
              <div className="flex gap-3 mt-4">
                <button
                  onClick={handleStartFocus}
                  className="flex-1 bg-red-500 hover:bg-red-600 text-white font-medium py-2 px-4 rounded-lg flex items-center justify-center gap-2 transition-colors shadow-lg"
                >
                  <Clock size={18} />
                  Start Focus
                </button>
                <button
                  onClick={handleIgnore}
                  className="bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-700 py-2 px-4 rounded-lg flex items-center justify-center transition-colors"
                >
                  Ignore
                </button>
              </div>
            </div>
            
            <button 
              onClick={handleIgnore}
              className="absolute -top-2 -right-2 p-1 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200 dark:hover:bg-slate-800 rounded-full transition-colors"
            >
              <X size={20} />
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
