import React from 'react';

export default function CommitmentModal({ isOpen, onClose, onStart, onSchedule }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-surface backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6 relative animate-in fade-in zoom-in duration-200">
        <button 
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-600 dark:text-slate-400 hover:text-slate-600"
        >
          ✕
        </button>
        
        <h2 className="text-2xl font-bold text-slate-800 mb-2">Start Your Commitment</h2>
        <p className="text-slate-600 mb-6">
          Commit to a 60-minute screen-free block or dedicated focus session. We'll block distracting apps and remind you to take breaks.
        </p>

        <div className="space-y-4">
          <div className="p-4 bg-indigo-50 rounded-xl border border-indigo-100 flex gap-3">
            <span className="text-2xl">🎯</span>
            <div>
              <h4 className="font-semibold text-indigo-900">Auto Focus Mode</h4>
              <p className="text-sm text-indigo-700">Distractions blocked automatically</p>
            </div>
          </div>
          
          <div className="p-4 bg-teal-50 rounded-xl border border-teal-100 flex gap-3">
            <span className="text-2xl">👀</span>
            <div>
              <h4 className="font-semibold text-teal-900">20-20-20 Reminders</h4>
              <p className="text-sm text-teal-700">Eye-strain breaks every 20 minutes</p>
            </div>
          </div>
        </div>

        <div className="mt-8 flex gap-3">
          <button 
            onClick={() => onStart()}
            className="flex-1 bg-indigo-600 text-white rounded-lg py-3 font-semibold hover:bg-indigo-700 transition"
          >
            Start Now
          </button>
          <button 
            onClick={() => onSchedule()}
            className="flex-1 bg-white border border-slate-300 text-slate-700 rounded-lg py-3 font-semibold hover:bg-slate-50 transition"
          >
            Schedule
          </button>
        </div>
      </div>
    </div>
  );
}