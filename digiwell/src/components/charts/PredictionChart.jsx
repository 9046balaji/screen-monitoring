import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, ReferenceArea } from 'recharts';
import { motion } from 'framer-motion';

export default function PredictionChart({ data, delay = 0 }) {
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const val = payload[0].value;
      const risk = val > 60 ? 'High' : 'Low';
      const riskColor = val > 60 ? 'text-danger' : 'text-success';
      return (
        <div className="bg-surface border border-slate-700 p-3 rounded-lg shadow-lg">
          <p className="text-white font-medium">{label}</p>
          <p className="text-muted text-sm">{`Predicted: ${val} mins`}</p>
          <p className={`text-sm font-bold ${riskColor}`}>Risk: {risk}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="rounded-2xl border border-slate-700 bg-surface p-6 shadow-lg flex flex-col gap-4 h-[400px]"
    >
      <h3 className="text-lg font-semibold text-white">Next 6 Hours Prediction</h3>
      <div className="flex-1 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
            <XAxis dataKey="hour" stroke="#94A3B8" fontSize={12} tickLine={false} axisLine={false} />
            <YAxis stroke="#94A3B8" fontSize={12} tickLine={false} axisLine={false} />
            <Tooltip content={<CustomTooltip />} />
            
            {/* Risk Zone Area */}
            <ReferenceArea y1={60} y2={120} fill="#EF4444" fillOpacity={0.1} />
            <ReferenceLine y={60} stroke="#EF4444" strokeDasharray="3 3" label={{ position: 'insideTopLeft', value: 'Risk Threshold', fill: '#EF4444', fontSize: 12 }} />
            <ReferenceLine x="Now" stroke="#94A3B8" strokeDasharray="3 3" label={{ position: 'insideTopRight', value: 'NOW', fill: '#94A3B8', fontSize: 12 }} />
            
            <Line type="monotone" dataKey="actual" name="Actual" stroke="#6366F1" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 6 }} connectNulls />
            <Line type="monotone" dataKey="predicted" name="Predicted" stroke="#F59E0B" strokeWidth={3} strokeDasharray="5 5" dot={{ r: 4 }} activeDot={{ r: 6 }} connectNulls />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}
