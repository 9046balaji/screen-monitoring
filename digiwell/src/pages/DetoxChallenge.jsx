import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { CheckCircle, Circle, Trophy, Calendar, Sparkles } from 'lucide-react';
import toast from 'react-hot-toast';
import { getDetoxChallenge, completeDetoxTask } from '../api/digiwell';

export default function DetoxChallenge() {
  const [challenge, setChallenge] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchChallenge();
  }, []);

  const fetchChallenge = async () => {
    try {
      const data = await getDetoxChallenge();
      setChallenge(data);
    } catch (err) {
      console.error(err);
      toast.error('Failed to load detox challenge');
    } finally {
      setLoading(false);
    }
  };

  const toggleTask = async (day, currentStatus) => {
    try {
      // Optimistic update
      setChallenge((prev) =>
        prev.map((t) => (t.day === day ? { ...t, completed: !currentStatus } : t))
      );
      
      const newStatus = !currentStatus;
      await completeDetoxTask(day, newStatus);
      
      if (newStatus) {
        toast.success(`Day ${day} Completed! Keep it up! 🎉`);
      }
    } catch (err) {
      console.error(err);
      toast.error('Failed to update task');
      // Revert optimism if failed
      fetchChallenge();
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64 text-slate-400">
        <p>Loading your challenge...</p>
      </div>
    );
  }

  const completedCount = challenge.filter((t) => t.completed).length;
  const progress = Math.round((completedCount / challenge.length) * 100) || 0;

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-12">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <Trophy className="w-8 h-8 text-warning" />
            7-Day Digital Detox
          </h1>
          <p className="text-muted mt-2">
            Build healthier habits one day at a time. Complete these small daily missions to rewire your brain.
          </p>
        </div>
      </div>

      {/* Progress Header */}
      <div className="bg-surface border border-slate-700 rounded-3xl p-8 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Sparkles className="w-6 h-6 text-primary" />
            Your Progress
          </h2>
          <span className="text-lg font-semibold text-primary">{progress}%</span>
        </div>
        <div className="w-full bg-slate-800 rounded-full h-4 overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className={`h-full ${progress === 100 ? 'bg-success' : 'bg-primary'}`}
          />
        </div>
        <p className="text-muted mt-4 font-medium">
          {completedCount} of 7 days completed.{' '}
          {progress === 100 ? "Amazing job! You've finished the challenge!" : "Keep going, you can do this!"}
        </p>
      </div>

      {/* Challenge List */}
      <div className="space-y-4">
        {challenge.map((task, idx) => (
          <motion.div
            key={task.day}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.1 }}
            onClick={() => toggleTask(task.day, task.completed)}
            className={`group cursor-pointer p-6 rounded-2xl border transition-all duration-300 flex items-center justify-between gap-4 ${
              task.completed
                ? 'bg-success/5 border-success/30 hover:border-success/50'
                : 'bg-surface border-slate-700 hover:border-primary/50'
            }`}
          >
            <div className="flex items-center gap-5">
              <div className="flex-shrink-0">
                {task.completed ? (
                  <CheckCircle className="w-8 h-8 text-success" />
                ) : (
                  <Circle className="w-8 h-8 text-slate-500 group-hover:text-primary transition-colors" />
                )}
              </div>
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <Calendar className="w-4 h-4 text-slate-400" />
                  <span className={`text-sm font-semibold uppercase tracking-wider ${task.completed ? 'text-success' : 'text-slate-400'}`}>
                    Day {task.day}
                  </span>
                </div>
                <h3 className={`text-lg font-medium ${task.completed ? 'text-slate-300 line-through' : 'text-white'}`}>
                  {task.task}
                </h3>
              </div>
            </div>
            {task.date_completed && task.completed && (
              <div className="text-xs text-slate-500 hidden sm:block">
                Done: {new Date(task.date_completed).toLocaleDateString()}
              </div>
            )}
          </motion.div>
        ))}
      </div>
    </div>
  );
}
