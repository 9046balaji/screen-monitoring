import React, { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { getHourlyUsage } from '../../api/digiwell'; // adjust path if needed

/**
 * ScreenTimeChart visually represents the hourly usage aggregated
 * from the monitor service.
 */
const ScreenTimeChart = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await getHourlyUsage();
        // Transform for recharts
        // response shape is already array of {hour, total_seconds}
        const formatted = response.map(d => ({
          time: `${d.hour}:00`,
          minutes: Math.round(d.total_seconds / 60)
        }));
        setData(formatted);
      } catch (err) {
        console.error("Error fetching hourly usage", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) return <div>Loading Screen Time Data...</div>;

  return (
    <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-100">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">Daily Screen Time</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="time" />
            <YAxis />
            <Tooltip cursor={{ fill: '#f3f4f6' }} />
            <Legend />
            <Bar dataKey="minutes" name="Minutes Spent" fill="#6366f1" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default ScreenTimeChart;
