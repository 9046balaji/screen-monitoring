import { useState } from 'react';
import { motion } from 'framer-motion';

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const HOURS = Array.from({ length: 24 }, (_, i) => i);

const getColor = (value) => {
  if (value === 0) return '#1E293B';
  if (value < 15) return '#064e3b';
  if (value < 30) return '#166534';
  if (value < 45) return '#854d0e';
  if (value < 60) return '#ea580c';
  return '#dc2626';
};

const formatHour = (h) => {
  if (h === 0) return '12a';
  if (h < 12) return `${h}a`;
  if (h === 12) return '12p';
  return `${h - 12}p`;
};

export default function HeatmapChart({ data, delay = 0 }) {
  const [tooltip, setTooltip] = useState(null);

  // Find the peak cell
  const peak = data.reduce((max, cell) => cell.value > max.value ? cell : max, { value: 0 });

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="rounded-2xl border border-slate-300 dark:border-slate-700 bg-surface p-6 shadow-lg flex flex-col gap-4"
    >
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Weekly Usage Heatmap</h3>
        <span className="text-xs text-muted">Peak: {peak.day} {formatHour(peak.hour)} ({peak.value} mins)</span>
      </div>

      {/* Grid container */}
      <div className="overflow-x-auto">
        <div style={{ display: 'grid', gridTemplateColumns: `36px repeat(24, 1fr)`, gap: '2px', minWidth: '600px' }}>
          {/* Header row: hour labels */}
          <div />
          {HOURS.map(h => (
            <div key={`hdr-${h}`} className="text-center text-muted" style={{ fontSize: '9px', paddingBottom: '2px' }}>
              {h % 3 === 0 ? formatHour(h) : ''}
            </div>
          ))}

          {/* Data rows: one per day */}
          {DAYS.map(day => (
            <>
              <div key={`lbl-${day}`} className="flex items-center justify-end pr-1 text-muted" style={{ fontSize: '11px' }}>
                {day}
              </div>
              {HOURS.map(h => {
                const cell = data.find(c => c.day === day && c.hour === h);
                const val = cell?.value ?? 0;
                return (
                  <div
                    key={`${day}-${h}`}
                    onMouseEnter={() => setTooltip({ day, hour: h, value: val })}
                    onMouseLeave={() => setTooltip(null)}
                    style={{
                      height: '28px',
                      borderRadius: '3px',
                      backgroundColor: getColor(val),
                      cursor: 'pointer',
                      transition: 'opacity 0.15s',
                    }}
                    title={`${day} ${formatHour(h)}: ${val} mins`}
                  />
                );
              })}
            </>
          ))}
        </div>
      </div>

      {/* Tooltip */}
      {tooltip && (
        <div className="text-sm text-slate-900 dark:text-white text-center">
          <span className="text-muted">{tooltip.day} at {formatHour(tooltip.hour)}</span>
          <span className="mx-2">—</span>
          <span className="font-semibold">{tooltip.value} mins</span>
        </div>
      )}

      {/* Legend */}
      <div className="flex gap-4 items-center justify-center">
        {[
          ['None', '#1E293B'],
          ['Low', '#064e3b'],
          ['Moderate', '#854d0e'],
          ['High', '#ea580c'],
          ['Peak', '#dc2626'],
        ].map(([label, color]) => (
          <div key={label} className="flex items-center gap-1">
            <div style={{ width: '12px', height: '12px', borderRadius: '2px', backgroundColor: color }} />
            <span className="text-muted" style={{ fontSize: '11px' }}>{label}</span>
          </div>
        ))}
      </div>
    </motion.div>
  );
}
