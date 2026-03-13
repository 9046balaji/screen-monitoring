import { motion } from 'framer-motion';
import RiskBadge from '../ui/RiskBadge';

export default function PersonaCard({ persona, isUser, delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className={`rounded-2xl border p-4 flex flex-col gap-3 relative transition-all ${
        isUser ? 'border-primary bg-primary/10 shadow-[0_0_15px_rgba(99,102,241,0.3)]' : 'border-slate-700 bg-surface'
      }`}
    >
      {isUser && (
        <span className="absolute -top-3 -right-3 bg-primary text-white text-[10px] font-bold px-2 py-1 rounded-full">
          YOU
        </span>
      )}
      <div className="text-3xl">{persona.emoji}</div>
      <h4 className="text-white font-semibold">{persona.name}</h4>
      <RiskBadge risk={persona.risk} />
      <p className="text-xs text-muted leading-relaxed">{persona.description}</p>
    </motion.div>
  );
}
