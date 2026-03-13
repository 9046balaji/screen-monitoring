import { motion } from 'framer-motion';
import { AlertTriangle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function AlertBanner({ message, buttonText, route, delay = 0, variant = "danger" }) {
  const navigate = useNavigate();
  
  const styles = {
    danger: {
      bg: "border-danger/50 bg-danger/10",
      text: "text-danger",
      btn: "bg-danger hover:bg-danger/90"
    },
    warning: {
      bg: "border-warning/50 bg-warning/10",
      text: "text-warning",
      btn: "bg-warning hover:bg-warning/90 text-slate-900"
    }
  };
  
  const currentStyle = styles[variant] || styles.danger;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className={`rounded-2xl border p-6 shadow-lg flex flex-col gap-4 ${currentStyle.bg}`}
    >
      <div className="flex items-start gap-3">
        <AlertTriangle className={`w-6 h-6 shrink-0 ${currentStyle.text}`} />
        <p className="text-white font-medium">{message}</p>
      </div>
      {buttonText && route && (
        <button
          onClick={() => navigate(route)}
          className={`self-start px-4 py-2 text-white rounded-lg text-sm font-medium transition-colors ${currentStyle.btn}`}
        >
          {buttonText}
        </button>
      )}
    </motion.div>
  );
}
