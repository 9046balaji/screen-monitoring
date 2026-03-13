import React, { useState, useEffect } from 'react'
import { downloadDailyReport, downloadWeeklyReport, getLiveUsage } from '../api/digiwell'
import { FileText, Download, FileBarChart2, ShieldAlert, Activity, CheckCircle2 } from 'lucide-react'
import StatCard from '../components/cards/StatCard'

export default function Reports() {
  const [liveData, setLiveData] = useState({ apps: {}, total_seconds: 0 })

  useEffect(() => {
    getLiveUsage().then(data => setLiveData(data)).catch(console.error)
  }, [])

  const totalHours = liveData.total_seconds / 3600
  const score = Math.max(0, Math.min(100, Math.round(100 - (totalHours / 12 * 100))))
  
  const appsArray = Object.entries(liveData.apps).map(([name, info]) => ({ name, ...info }))
  appsArray.sort((a, b) => b.seconds - a.seconds)
  const topApps = appsArray.slice(0, 3)

  const highRiskSeconds = appsArray.filter(a => a.risk === 'high').reduce((acc, curr) => acc + curr.seconds, 0)
  const highRiskMins = Math.floor(highRiskSeconds / 60)

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2 bg-blue-500/20 text-blue-400 rounded-lg">
          <FileText size={24} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Export Reports</h1>
          <p className="text-slate-600 dark:text-slate-400 text-sm">Download your digital wellness data as PDF</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Daily Card */}
        <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-300 dark:border-slate-700 hover:border-blue-500/50 transition-colors rounded-2xl p-6 group">
          <div className="flex items-start justify-between mb-4">
            <div className="bg-blue-500/20 p-3 rounded-xl text-blue-400">
              <FileBarChart2 size={32} />
            </div>
            <span className="text-xs font-semibold px-2 py-1 bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-700 rounded-full">TODAY</span>
          </div>
          <h2 className="text-xl font-bold text-slate-100 mb-1">Daily Summary</h2>
          <p className="text-slate-600 dark:text-slate-400 text-sm mb-6 h-10">Complete breakdown of today's app usage and high-risk activity.</p>
          <button 
            onClick={downloadDailyReport}
            className="w-full py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-medium flex items-center justify-center gap-2 transition-all group-hover:shadow-[0_0_20px_rgba(59,130,246,0.3)]"
          >
            <Download size={18} /> Download PDF
          </button>
        </div>

        {/* Weekly Card */}
        <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-300 dark:border-slate-700 hover:border-indigo-500/50 transition-colors rounded-2xl p-6 group">
          <div className="flex items-start justify-between mb-4">
            <div className="bg-indigo-500/20 p-3 rounded-xl text-indigo-400">
              <FileBarChart2 size={32} />
            </div>
            <span className="text-xs font-semibold px-2 py-1 bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-700 rounded-full">LAST 7 DAYS</span>
          </div>
          <h2 className="text-xl font-bold text-slate-100 mb-1">Weekly Deep-Dive</h2>
          <p className="text-slate-600 dark:text-slate-400 text-sm mb-6 h-10">7-day trends, wellness score tracking, and automated recommendations.</p>
          <button 
            onClick={downloadWeeklyReport}
            className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-medium flex items-center justify-center gap-2 transition-all group-hover:shadow-[0_0_20px_rgba(99,102,241,0.3)]"
          >
            <Download size={18} /> Download PDF
          </button>
        </div>
      </div>

      {/* Preview Section */}
      <div className="mt-8 bg-surface border border-slate-300 dark:border-slate-700 rounded-xl p-6 shadow-sm backdrop-blur-sm">
        <h3 className="text-lg font-semibold text-slate-200 mb-4">Today's Snapshot Overview</h3>
        
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard 
            title="Screen Time" 
            value={`${Math.floor(liveData.total_seconds / 3600)}h ${Math.floor((liveData.total_seconds % 3600) / 60)}m`} 
            color="indigo" 
            icon={Activity} 
          />
          <StatCard 
            title="Wellness Score" 
            value={isNaN(score) ? '--' : score} 
            color={score > 70 ? 'emerald' : score > 40 ? 'amber' : 'red'} 
            icon={CheckCircle2} 
          />
          <StatCard 
            title="High-Risk Use" 
            value={`${highRiskMins} mins`} 
            color="red" 
            icon={ShieldAlert} 
          />
          
          <div className="bg-surface p-4 rounded-xl border border-slate-300 dark:border-slate-700 flex flex-col justify-center">
            <span className="text-xs text-slate-600 dark:text-slate-400 mb-1 font-medium select-none">Top Apps</span>
            {topApps.length > 0 ? (
              <div className="space-y-1">
                {topApps.map((a, i) => (
                  <div key={i} className="text-sm text-slate-700 dark:text-slate-300 truncate">• {a.name}</div>
                ))}
              </div>
            ) : (
              <span className="text-xl font-bold text-slate-700 dark:text-slate-300">None yet</span>
            )}
          </div>
        </div>
      </div>

    </div>
  )
}
