import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Play, Pause, RotateCcw } from 'lucide-react';
import toast from 'react-hot-toast';

export default function Timer2020() {
  const [timeLeft, setTimeLeft] = useState(20 * 60); // 20 minutes
  const [isActive, setIsActive] = useState(false);
  const [isFlashing, setIsFlashing] = useState(false);

  useEffect(() => {
    let interval = null;
    if (isActive && timeLeft > 0) {
      interval = setInterval(() => {
        setTimeLeft(time => time - 1);
      }, 1000);
    } else if (isActive && timeLeft === 0) {
      setIsActive(false);
      setIsFlashing(true);
      toast.success('Time to look away! 👀', { duration: 5000 });
      setTimeout(() => {
        setIsFlashing(false);
        setTimeLeft(20 * 60);
        setIsActive(true);
      }, 5000);
    }
    return () => clearInterval(interval);
  }, [isActive, timeLeft]);

  const toggle = () => setIsActive(!isActive);
  const reset = () => {
    setIsActive(false);
    setTimeLeft(20 * 60);
  };

  const minutes = Math.floor(timeLeft / 60);
  const seconds = timeLeft % 60;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`rounded-2xl border p-6 shadow-lg flex flex-col items-center gap-4 transition-colors duration-500 ${
        isFlashing ? 'bg-success/20 border-success' : 'bg-surface border-slate-700'
      }`}
    >
      <div className="text-center">
        <h3 className="text-xl font-bold text-white">20-20-20 Eye Rule Timer</h3>
        <p className="text-muted text-sm mt-1">Every 20 minutes, look at something 20 feet away for 20 seconds</p>
      </div>
      
      <div className="text-6xl font-mono font-bold text-white tracking-wider my-4">
        {String(minutes).padStart(2, '0')}:{String(seconds).padStart(2, '0')}
      </div>

      <div className="flex gap-4">
        <button
          onClick={toggle}
          className="flex items-center gap-2 px-6 py-3 bg-primary hover:bg-primary/90 text-white rounded-xl font-medium transition-colors"
        >
          {isActive ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
          {isActive ? 'Pause' : 'Start'}
        </button>
        <button
          onClick={reset}
          className="flex items-center gap-2 px-6 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-xl font-medium transition-colors"
        >
          <RotateCcw className="w-5 h-5" />
          Reset
        </button>
      </div>
    </motion.div>
  );
}
