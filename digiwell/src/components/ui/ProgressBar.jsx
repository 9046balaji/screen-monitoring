export default function ProgressBar({ label, value, max = 5, colorClass = "bg-primary" }) {
  const percentage = (value / max) * 100;
  
  return (
    <div className="flex flex-col gap-1 w-full">
      <div className="flex justify-between text-sm">
        <span className="text-muted">{label}</span>
        <span className="text-white font-medium">{value}/{max}</span>
      </div>
      <div className="h-2 w-full bg-slate-700 rounded-full overflow-hidden">
        <div 
          className={`h-full rounded-full ${colorClass}`} 
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
