import React, { useEffect, useState } from 'react';
import { getDailyUsage } from '../../api/digiwell';

const UsageTimeline = () => {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await getDailyUsage();
        if (response) {
          setMetrics(response);
        }
      } catch (err) {
        console.error("Error fetching daily usage stats", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) return <div>Loading Usage Timeline...</div>;
  if (!metrics) return null;

  const formatHours = (seconds) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return `${h}h ${m}m`;
  };

  const total = metrics.total_screen_time_seconds || 0;
  const prod = metrics.productivity_time_seconds || 0;
  const dist = metrics.social_media_time_seconds || 0;
  
  const prodRatio = total > 0 ? (prod / total) * 100 : 0;
  const distRatio = total > 0 ? (dist / total) * 100 : 0;

  return (
    <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-100 mt-4">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">Today's Usage Summary</h3>
      
      <div className="flex gap-4 items-center mb-6">
        <div className="flex-1 text-center p-3 bg-indigo-50 rounded-lg">
          <p className="text-xs text-indigo-600 uppercase font-semibold">Total Screen Time</p>
          <p className="text-2xl font-bold text-indigo-900">{formatHours(total)}</p>
        </div>
        <div className="flex-1 text-center p-3 bg-red-50 rounded-lg">
          <p className="text-xs text-red-600 uppercase font-semibold">Distracting Time</p>
          <p className="text-xl font-bold text-red-900">{formatHours(dist)}</p>
        </div>
        <div className="flex-1 text-center p-3 bg-green-50 rounded-lg">
          <p className="text-xs text-green-600 uppercase font-semibold">Productive Time</p>
          <p className="text-xl font-bold text-green-900">{formatHours(prod)}</p>
        </div>
      </div>
      
      <div>
        <div className="flex justify-between text-xs text-gray-500 mb-1">
          <span>Productivity Ratio ({Math.round(prodRatio)}%)</span>
          <span>Distraction Ratio ({Math.round(distRatio)}%)</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3 flex overflow-hidden">
          <div className="bg-green-500 h-3" style={{ width: `${prodRatio}%` }}></div>
          <div className="bg-red-500 h-3" style={{ width: `${distRatio}%` }}></div>
        </div>
      </div>
    </div>
  );
};

export default UsageTimeline;