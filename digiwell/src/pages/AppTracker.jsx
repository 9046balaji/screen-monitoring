import React, { useEffect, useState } from 'react'
import { getLiveUsage, getLimits, setLimit, deleteLimit } from '../api/digiwell'
import RiskBadge from '../components/ui/RiskBadge'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'
import { X, Clock, ShieldAlert, MonitorPlay } from 'lucide-react'

const COLORS = ['#6366F1', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#64748B'];

export default function AppTracker() {
  const [usageData, setUsageData] = useState({ apps: {}, total_seconds: 0 })
  const [limits, setLimits] = useState({})
  
  const [selectedApp, setSelectedApp] = useState('')
  const [limitMinutes, setLimitMinutes] = useState(60)
  const [mode, setMode] = useState('warn')

  useEffect(() => {
    fetchLimits()
    const fetchLive = () => {
      getLiveUsage().then(data => setUsageData(data)).catch(err => console.error(err))
    }
    fetchLive()
    const int = setInterval(fetchLive, 5000)
    return () => clearInterval(int)
  }, [])

  const fetchLimits = () => {
    getLimits().then(data => setLimits(data)).catch(err => console.error(err))
  }

  const handleSetLimit = async (e) => {
    e.preventDefault()
    if (!selectedApp) return
    await setLimit({ app_name: selectedApp, limit_seconds: limitMinutes * 60, mode })
    fetchLimits()
    setSelectedApp('')
  }

  const handleDeleteLimit = async (appName) => {
    await deleteLimit(appName)
    fetchLimits()
  }

  const formatTime = (seconds) => {
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    return `${h}h ${m}m`
  }

  const appsArray = Object.entries(usageData.apps).map(([name, info]) => ({ name, ...info }))
  
  // Category data for donut
  const catMap = {}
  appsArray.forEach(a => {
    catMap[a.category] = (catMap[a.category] || 0) + a.seconds
  })
  const catData = Object.entries(catMap).map(([name, value]) => ({ name, value }))

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      
      <div className="flex items-center gap-3 mb-2">
        <div className="p-2 bg-indigo-500/20 text-indigo-600 dark:text-indigo-400 rounded-lg">
          <MonitorPlay size={24} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Live App Tracker</h1>
          <p className="text-slate-600 dark:text-slate-400 text-sm">Monitor Windows usage and enforce limits</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Tracker Table */}
        <div className="lg:col-span-2 bg-surface border border-slate-300 dark:border-slate-700 rounded-xl p-5 shadow-sm backdrop-blur-sm">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-200 mb-4 flex items-center gap-2">
            <Clock size={18} className="text-indigo-600 dark:text-indigo-400"/> Activity Today ({formatTime(usageData.total_seconds || 0)})
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-surface text-slate-600 dark:text-slate-400 text-sm">
                <tr>
                  <th className="p-3 rounded-tl-lg">App Name</th>
                  <th className="p-3">Category</th>
                  <th className="p-3">Time Today</th>
                  <th className="p-3">Risk</th>
                  <th className="p-3 rounded-tr-lg">Limit</th>
                </tr>
              </thead>
              <tbody className="text-sm text-slate-700 dark:text-slate-300 divide-y divide-slate-200 dark:divide-slate-700/50">
                {appsArray.length === 0 && (
                  <tr><td colSpan="5" className="p-4 text-center text-slate-600 dark:text-slate-500">No data tracked yet. Ensure tracker agent is running.</td></tr>
                )}
                {appsArray.map((app) => {
                  const limit = limits[app.name]?.limit_seconds
                  const isOver = limit && app.seconds > limit
                  return (
                    <tr key={app.name} className={`hover:bg-slate-300 dark:hover:bg-slate-700/30 transition-colors ${isOver ? 'bg-red-500/10' : ''}`}>
                      <td className="p-3 font-medium text-slate-900 dark:text-slate-200">{app.name}</td>
                      <td className="p-3">{app.category || 'Other'}</td>
                      <td className="p-3">
                        <div className="flex items-center gap-2">
                          <span className={`${isOver ? 'text-red-600 dark:text-red-400 font-bold' : 'text-slate-700 dark:text-slate-300'}`}>{formatTime(app.seconds)}</span>
                          {limit && (
                            <div className="w-20 h-1.5 bg-slate-300 dark:bg-slate-700 rounded-full overflow-hidden">
                              <div 
                                className={`h-full ${isOver ? 'bg-red-500' : 'bg-emerald-500'}`} 
                                style={{ width: `${Math.min((app.seconds / limit) * 100, 100)}%` }}
                              />
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="p-3"><RiskBadge level={app.risk === 'high' ? 'High' : app.risk === 'medium' ? 'Medium' : 'Low'} /></td>
                      <td className="p-3">
                        {limit ? (
                          <div className="flex items-center gap-2">
                            <span className="text-emerald-600 dark:text-emerald-400 text-xs font-semibold px-2 py-1 bg-emerald-500/10 rounded">{formatTime(limit)}</span>
                            <button onClick={() => handleDeleteLimit(app.name)} className="text-slate-600 dark:text-slate-500 hover:text-red-600 dark:text-red-400 p-1" title="Remove limit">
                              <X size={14} />
                            </button>
                          </div>
                        ) : (
                          <button onClick={() => setSelectedApp(app.name)} className="text-xs px-2 py-1 bg-indigo-500/20 text-indigo-700 dark:text-indigo-300 rounded hover:bg-indigo-500/40 transition-colors">Set Limit</button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Set Limits Panel */}
        <div className="space-y-6">
          <div className="bg-surface border border-slate-300 dark:border-slate-700 rounded-xl p-5 shadow-sm backdrop-blur-sm">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-200 mb-4 flex items-center gap-2">
              <ShieldAlert size={18} className="text-amber-600 dark:text-amber-400"/> Enforce Limit
            </h2>
            <form onSubmit={handleSetLimit} className="space-y-4">
              <div>
                <label className="block text-sm text-slate-600 dark:text-slate-400 mb-1">Select App</label>
                <select 
                  value={selectedApp} onChange={e => setSelectedApp(e.target.value)} required
                  className="w-full bg-slate-100 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-200 rounded-lg p-2 text-sm focus:outline-none focus:border-indigo-500"
                >
                  <option value="">-- Choose an App --</option>
                  {appsArray.map(a => <option key={a.name} value={a.name}>{a.name}</option>)}
                </select>
              </div>

              <div>
                <label className="block text-sm text-slate-600 dark:text-slate-400 mb-1">
                  Time Limit: <span className="text-indigo-600 dark:text-indigo-400 font-semibold">{limitMinutes} mins</span>
                   ({formatTime(limitMinutes * 60)})
                </label>
                <input 
                  type="range" min="1" max="480" step="1" 
                  value={limitMinutes} onChange={e => setLimitMinutes(Number(e.target.value))}
                  className="w-full accent-indigo-500"
                />
              </div>

              <div>
                <label className="block text-sm text-slate-600 dark:text-slate-400 mb-1">Enforcement Mode</label>
                <div className="grid grid-cols-2 gap-2">
                  {['warn', 'close', 'break', 'all'].map(m => (
                    <button 
                      key={m} type="button"
                      onClick={() => setMode(m)}
                      className={`text-xs p-2 rounded-lg border ${mode === m ? 'border-indigo-500 bg-indigo-500/20 text-indigo-700 dark:text-indigo-300' : 'border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-slate-900 text-slate-600 dark:text-slate-400'}`}
                    >
                      {m.toUpperCase()}
                    </button>
                  ))}
                </div>
              </div>

              <button type="submit" className="w-full py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors">
                Save Limit
              </button>
            </form>
          </div>

          <div className="bg-surface border border-slate-300 dark:border-slate-700 rounded-xl p-5 shadow-sm backdrop-blur-sm">
            <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-200 mb-3">Active Limits</h2>
            <div className="space-y-2">
              {Object.keys(limits).length === 0 && <p className="text-slate-600 dark:text-slate-500 text-xs">No active limits</p>}
              {Object.entries(limits).map(([name, info]) => (
                <div key={name} className="flex items-center justify-between bg-slate-100 dark:bg-slate-900 p-2 rounded border border-slate-300 dark:border-slate-700/50">
                  <div>
                    <div className="text-sm text-slate-900 dark:text-slate-200 font-medium">{name}</div>
                    <div className="text-xs text-slate-600 dark:text-slate-400 flex items-center gap-2">
                      <span>{formatTime(info.limit_seconds)}</span>
                      <span className="px-1 py-0.5 bg-slate-200 dark:bg-slate-800 text-[10px] rounded uppercase">{info.mode}</span>
                    </div>
                  </div>
                  <button onClick={() => handleDeleteLimit(name)} className="text-slate-600 dark:text-slate-500 hover:text-red-600 dark:text-red-400 p-1">
                    <X size={16} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Category Chart */}
      <div className="bg-surface border border-slate-300 dark:border-slate-700 rounded-xl p-5 shadow-sm backdrop-blur-sm">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-200 mb-4">Usage By Category</h2>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={catData} cx="50%" cy="50%" innerRadius={60} outerRadius={80} paddingAngle={5} dataKey="value">
                {catData.map((entry, index) => <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />)}
              </Pie>
              <Tooltip 
                contentStyle={{ backgroundColor: '#0F172A', borderColor: '#334155', borderRadius: '8px' }}
                itemStyle={{ color: '#F8FAFC' }}
                formatter={(val) => formatTime(val)}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="flex flex-wrap justify-center gap-4 mt-2 text-xs text-slate-600 dark:text-slate-400">
          {catData.map((entry, idx) => (
            <div key={entry.name} className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[idx % COLORS.length] }}></div>
              {entry.name}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
