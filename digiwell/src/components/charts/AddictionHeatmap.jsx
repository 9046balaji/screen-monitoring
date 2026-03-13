import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { getAddictionHeatmap } from '../../api/digiwell';

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const HOURS = Array.from({ length: 24 }, (_, i) => i);

const getRiskColor = (riskLevel) => {
  switch (riskLevel) {
    case 'None': return '#1E293B'; // slate-800
    case 'Low': return '#22c55e'; // green-500
    case 'Medium': return '#eab308'; // yellow-500
    case 'High': return '#f97316'; // orange-500
    case 'Very High': return '#ef4444'; // red-500
    default: return '#1E293B';
  }
};

const formatHour = (h) => {
  if (h === 0) return '12a';
  if (h < 12) return `${h}a`;
  if (h === 12) return '12p';
  return `${h - 12}p`;
};

export default function AddictionHeatmap({ delay = 0 }) {
  const [data, setData] = useState([]);
  const [tooltip, setTooltip] = useState(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const res = await getAddictionHeatmap();
        setData(res);
      } catch (err) {
        console.error('Failed to fetch addiction heatmap:', err);
      }
    }
    fetchData();
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="rounded-2xl border border-slate-300 dark:border-slate-700 bg-surface p-6 shadow-lg flex flex-col gap-4"
    >
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white">AI Addiction Heatmap</h3>
      </div>

      <div className="overflow-x-auto">
        <div style={{ display: 'grid', gridTemplateColumns: '36px repeat(24, 1fr)', gap: '4px', minWidth: '600px' }}>
          {/* Header row: hour labels */}
          <div />
          {HOURS.map(h => (
            <div key={`hdr-${h}`} className="text-center text-muted" style={{ fontSize: '10px', paddingBottom: '4px' }}>
              {h % 3 === 0 ? formatHour(h) : ''}
            </div>
          ))}

          {/* Data rows: one per day */}
          {DAYS.map(day => (
            <React.Fragment key={day}>
              <div className="flex items-center justify-end pr-2 text-muted" style={{ fontSize: '12px' }}>
                {day}
              </div>
              {HOURS.map(h => {
                const cell = data.find(c => c.day === day && c.hour === h);
                const riskLevel = cell?.riskLevel || 'None';
                const val = cell?.value || 0;
                
                return (
                  <div
                    key={`${day}-${h}`}
                    onMouseEnter={() => setTooltip({ day, hour: h, risk: riskLevel, value: val })}
                    onMouseLeave={() => setTooltip(null)}
                    style={{
                      height: '24px',
                      borderRadius: '4px',
                      backgroundColor: getRiskColor(riskLevel),
                      cursor: 'pointer',
                      transition: 'transform 0.1s',
                    }}
                    onMouseOver={(e) => e.target.style.transform = 'scale(1.1)'}
                    onMouseOut={(e) => e.target.style.transform = 'scale(1)'}
                  />
                );
              })}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Tooltip display */}
      <div className="h-6 flex items-center justify-center">
        {tooltip ? (
          <div className="text-sm text-slate-900 dark:text-white">
            <span className="text-muted">{tooltip.day} {formatHour(tooltip.hour)}</span>
            <span className="mx-2">—</span>
            <span className="font-semibold" style={{ color: getRiskColor(tooltip.risk) }}>{tooltip.risk} Level</span>
            <span className="text-muted ml-2">({tooltip.value} min)</span>
          </div>
        ) : (
          <div className="text-sm text-transparent select-none">Hover over a square</div>
        )}
      </div>

      {/* Legend */}
      <div className="flex gap-4 items-center justify-center mt-2">
        {[
          ['None', 'None'],
          ['Low', 'Low'],
          ['Medium', 'Medium'],
          ['High', 'High'],
          ['Very High', 'Very High'],
        ].map(([label, risk]) => (
          <div key={label} className="flex items-center gap-1.5">
            <div style={{ width: '14px', height: '14px', borderRadius: '3px', backgroundColor: getRiskColor(risk) }} />
            <span className="text-muted" style={{ fontSize: '12px' }}>{label}</span>
          </div>
        ))}
      </div>
    </motion.div>
  );
}
