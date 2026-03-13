export default function RiskBadge({ risk }) {
  const colors = {
    Low: 'bg-success/20 text-success border-success/30',
    Medium: 'bg-warning/20 text-warning border-warning/30',
    High: 'bg-danger/20 text-danger border-danger/30',
  };

  const colorClass = colors[risk] || colors.Medium;

  return (
    <span className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${colorClass}`}>
      {risk}
    </span>
  );
}
