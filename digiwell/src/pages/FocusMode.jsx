import React, { useState, useEffect } from 'react'
import { startFocus, stopFocus, getFocusStatus, getFocusRecommendation } from '../api/digiwell'
import { Target, Play, Square, CheckSquare, Square as UncheckedSquare, History, Sparkles } from 'lucide-react'

const COMMON_APPS = [
  { id: 'discord.exe', name: 'Discord' },
  { id: 'slack.exe', name: 'Slack' },
  { id: 'WhatsApp.exe', name: 'WhatsApp' },
  { id: 'Telegram.exe', name: 'Telegram' },
  { id: 'steam.exe', name: 'Steam' },
  { id: 'spotify.exe', name: 'Spotify' },
  { id: 'chrome.exe', name: 'Google Chrome' },
  { id: 'firefox.exe', name: 'Firefox' },
  { id: 'Instagram', name: 'Instagram' },
  { id: 'TikTok', name: 'TikTok' },
  { id: 'YouTube', name: 'YouTube' }
]

export default function FocusMode() {
  const [status, setStatus] = useState({ active: false })
  const [sessionName, setSessionName] = useState('Deep Work')
  const [duration, setDuration] = useState(25)
  const [blockedApps, setBlockedApps] = useState(COMMON_APPS.map(a => a.id).slice(0, 5)) // Pre-select first 5
  const [blockedCategories, setBlockedCategories] = useState(['social', 'video', 'entertainment']) // Website blocking categories

  
  const [remainingTime, setRemainingTime] = useState(null)
  const [aiRecommendation, setAiRecommendation] = useState(null)
  const [loadingRec, setLoadingRec] = useState(false)
  const [blockingStatus, setBlockingStatus] = useState(null)

  useEffect(() => {
    fetchStatus()
    loadRecommendation()
    const int = setInterval(fetchStatus, 10000)
    return () => clearInterval(int)
  }, [])

  const loadRecommendation = async () => {
    try {
      setLoadingRec(true)
      const data = await getFocusRecommendation()
      setAiRecommendation(data)
    } catch (e) {
      console.error("Error loading recommendation", e)
    } finally {
      setLoadingRec(false)
    }
  }

  const applyRecommendation = () => {
    if (aiRecommendation) {
      setDuration(aiRecommendation.recommended_duration_minutes)
      const appIds = aiRecommendation.recommended_block_list.map(appName => {
        const found = COMMON_APPS.find(a => a.name.toLowerCase() === appName.toLowerCase())
        return found ? found.id : appName
      })
      setBlockedApps(appIds)
      setSessionName('AI Suggested Focus')
    }
  }

  useEffect(() => {
    let int
    if (status.active && status.ends_at) {
      const updateTime = () => {
        const diff = Math.max(0, new Date(status.ends_at) - new Date())
        setRemainingTime(diff)
      }
      updateTime()
      int = setInterval(updateTime, 1000)
    } else {
      setRemainingTime(null)
    }
    return () => clearInterval(int)
  }, [status])

  const fetchStatus = async () => {
    try {
      const data = await getFocusStatus()
      setStatus(data || { active: false })
      setBlockingStatus(data?.website_blocking || null)
    } catch (e) {
      console.error(e)
    }
  }

  const handleToggleApp = (appId) => {
    setBlockedApps(prev => 
      prev.includes(appId) ? prev.filter(id => id !== appId) : [...prev, appId]
    )
  }

  const handleToggleCategory = (cat) => {
    setBlockedCategories(prev => 
      prev.includes(cat) ? prev.filter(c => c !== cat) : [...prev, cat]
    )
  }

  const handleStart = async () => {
    if (!sessionName) return
    const result = await startFocus({ session_name: sessionName, duration_minutes: duration, block_list: blockedApps, block_categories: blockedCategories })
    setBlockingStatus(result?.website_blocking || null)
    fetchStatus()
  }

  const handleStop = async () => {
    await stopFocus()
    fetchStatus()
  }

  const formatCountdown = (ms) => {
    if (ms === null) return '--:--'
    const totalSecs = Math.floor(ms / 1000)
    const m = Math.floor(totalSecs / 60)
    const s = totalSecs % 60
    return `${m}:${s < 10 ? '0' : ''}${s}`
  }

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center gap-3 mb-2">
        <div className="p-2 bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 rounded-lg">
          <Target size={24} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">Focus Mode</h1>
          <p className="text-slate-600 dark:text-slate-400 text-sm">Block distractions and get deep work done.</p>
        </div>
      </div>

      {status.active && (
        <div className={`rounded-lg border px-4 py-3 text-sm ${blockingStatus?.enforced ? 'border-emerald-300 bg-emerald-50 text-emerald-800' : 'border-amber-300 bg-amber-50 text-amber-900'}`}>
          {blockingStatus?.enforced ? 'Website blocking is actively enforced at system level (hosts file).' : (blockingStatus?.message || 'Website blocking could not be enforced. Run DigiWell as Administrator to block sites across Chrome, Edge, Firefox, and Brave.')}
        </div>
      )}

      {status.active && (
        <div className="bg-gradient-to-r from-emerald-500/10 to-teal-500/10 border border-emerald-500/30 rounded-2xl p-8 flex flex-col md:flex-row items-center justify-between gap-6 shadow-[0_0_30px_rgba(16,185,129,0.15)] relative overflow-hidden backdrop-blur-sm">
          <div className="absolute top-0 left-0 w-1 h-full bg-emerald-500 animate-pulse"></div>
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 rounded-full text-xs font-bold uppercase tracking-wider mb-3">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span> Live
            </div>
            <h2 className="text-slate-900 dark:text-white font-bold text-2xl mb-1 flex items-center gap-2">
              {status.session_name}
            </h2>
              <p className="text-emerald-800/80 dark:text-emerald-100/70 text-sm">Focus Mode is guarding your attention right now.</p>
              <p className="text-rose-700/80 dark:text-rose-300/80 text-xs mt-2">"🚫 This website is blocked during Focus Mode."</p>
            {status.apps_killed && status.apps_killed.length > 0 && (
              <div className="mt-4 flex flex-wrap items-center gap-2">
                <span className="text-xs text-amber-600 dark:text-amber-400/80">Distractions blocked:</span>
                {status.apps_killed.map(app => (
                   <span key={app} className="text-[10px] px-2 py-1 bg-amber-500/10 text-amber-700 dark:text-amber-300 rounded border border-amber-500/20">{app}</span>
                ))}
              </div>
            )}
          </div>
          <div className="flex flex-col items-center gap-4 bg-slate-100 dark:bg-slate-900/40 p-4 rounded-xl border border-slate-300 dark:border-slate-700/50">
            <div className="text-5xl font-mono font-black text-emerald-700 dark:text-emerald-300 tabular-nums tracking-tight tracking-wider" style={{ textShadow: "0 0 20px rgba(16,185,129,0.4)" }}>
              {remainingTime !== null ? (
                <>
                  {Math.floor(remainingTime / 60000)}<span className="text-emerald-500/50 opacity-80 animate-pulse">:</span>
                  {(Math.floor((remainingTime % 60000) / 1000)).toString().padStart(2, '0')}
                </>
              ) : '--:--'}
            </div>
            <button onClick={handleStop} className="w-full flex items-center justify-center gap-2 px-6 py-2.5 bg-surface dark:bg-slate-800/80 hover:bg-red-500/20 text-slate-700 dark:text-slate-300 hover:text-red-600 dark:text-red-400 rounded-lg font-medium transition-all group border border-slate-300 dark:border-slate-700 hover:border-red-500/30">
              <Square size={16} className="group-hover:fill-current" /> Stop Early
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Configuration */}
        <div className={`bg-surface border border-slate-300 dark:border-slate-700 rounded-xl p-6 shadow-sm backdrop-blur-sm transition-opacity ${status.active ? 'opacity-50 pointer-events-none' : ''}`}>
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-200">Start New Session</h2>
            {aiRecommendation && (
              <button 
                onClick={applyRecommendation}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-500/20 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-500/30 rounded-lg text-xs font-semibold transition-colors border border-indigo-500/30"
                title={aiRecommendation.reasoning}
              >
                <Sparkles size={14} />
                AI Suggestion
              </button>
            )}
          </div>
          
          <div className="space-y-5">
            <div>
              <label className="block text-sm text-slate-600 dark:text-slate-400 mb-1">Session Name</label>
              <input 
                type="text" value={sessionName} onChange={e => setSessionName(e.target.value)}
                className="w-full bg-slate-100 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-200 rounded-lg p-2.5 text-sm focus:outline-none focus:border-emerald-500"
                placeholder="e.g., Study for Finals"
              />
            </div>

            <div>
              <label className="block text-sm text-slate-600 dark:text-slate-400 mb-2 flex justify-between">
                <span>Duration</span>
                <span className="text-emerald-600 dark:text-emerald-400 font-semibold">{duration} minutes</span>
              </label>
              <div className="flex gap-2">
                {[5, 15, 25, 45, 60, 90].map(d => (
                  <button
                    key={d} onClick={() => setDuration(d)}
                    className={`flex-1 py-2 text-xs rounded-lg border font-medium ${duration === d ? 'border-emerald-500 bg-emerald-500/20 text-emerald-700 dark:text-emerald-300' : 'border-slate-300 dark:border-slate-700 bg-slate-100 dark:bg-slate-900 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-800'}`}
                  >
                    {d}m
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm text-slate-600 dark:text-slate-400 mb-2">Websites to Block</label>
              <div className="flex flex-col gap-2">
                {[
                  { id: 'social', label: 'Block Social Media (Instagram, Twitter, etc.)' },
                  { id: 'video', label: 'Block Video Platforms (YouTube, TikTok)' },
                  { id: 'entertainment', label: 'Block Entertainment (Netflix, Hulu)' }
                ].map(cat => {
                  const isBlocked = blockedCategories.includes(cat.id);
                  return (
                    <label key={cat.id} className="flex items-center gap-3 p-2 border border-slate-200 dark:border-slate-700 rounded-lg cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800">
                      <input 
                        type="checkbox" 
                        checked={isBlocked} 
                        onChange={() => handleToggleCategory(cat.id)}
                        className="w-4 h-4 text-emerald-600 rounded bg-slate-100 border-slate-300 focus:ring-emerald-500"
                      />
                      <span className="text-sm font-medium text-slate-700 dark:text-slate-300">{cat.label}</span>
                    </label>
                  );
                })}
              </div>
            </div>

            <div>
              <label className="block text-sm text-slate-600 dark:text-slate-400 mb-2">Apps to Block</label>
              <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto pr-2 custom-scrollbar">
                {COMMON_APPS.map(app => {
                  const isBlocked = blockedApps.includes(app.id);
                  return (
                    <div 
                      key={app.id} 
                      onClick={() => handleToggleApp(app.id)}
                      className={`flex items-center justify-between p-3 rounded-xl cursor-pointer border text-sm transition-all transform hover:scale-[1.02] ${isBlocked ? 'bg-emerald-500/10 border-emerald-500/50 text-slate-900 dark:text-slate-200 shadow-md shadow-emerald-500/5' : 'bg-surface border-slate-300 dark:border-slate-700/50 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-600'}`}
                    >
                      <div className="flex items-center gap-3">
                        <div className={`p-1.5 rounded-lg ${isBlocked ? 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400' : 'bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-500'}`}>
                          {app.name.charAt(0)}
                        </div>
                        <span className="font-medium">{app.name}</span>
                      </div>
                      {isBlocked ? <CheckSquare size={18} className="text-emerald-600 dark:text-emerald-400"/> : <UncheckedSquare size={18} />}
                    </div>
                  )
                })}
              </div>
            </div>

            <button onClick={handleStart} className="w-full py-3 mt-4 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-bold flex items-center justify-center gap-2 shadow-lg shadow-emerald-900/20 transition-all active:scale-[0.98]">
              <Play size={18} fill="currentColor"/> Start Focus Session
            </button>
          </div>
        </div>

        {/* Info / History */}
        <div className="bg-surface border border-slate-300 dark:border-slate-700 rounded-xl p-6 shadow-sm backdrop-blur-sm flex flex-col">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-200 mb-4 flex items-center gap-2">
            <History size={18} className="text-indigo-600 dark:text-indigo-400"/> Recent Activity
          </h2>
          
          <div className="flex-1 flex flex-col items-center justify-center text-center p-6 bg-surface rounded-lg border border-slate-200 dark:border-slate-800 border-dashed">
            {status.active ? (
              <>
                <Target size={48} className="text-emerald-500/20 mb-4 animate-pulse"/>
                <p className="text-slate-700 dark:text-slate-300 font-medium">Session in Progress</p>
                <p className="text-slate-600 dark:text-slate-500 text-sm mt-1">Focus Mode is intercepting distractions to keep you on track.</p>
              </>
            ) : (
              <>
                <History size={48} className="text-slate-700 mb-4"/>
                <p className="text-slate-600 dark:text-slate-400">Ready to focus?</p>
                <p className="text-slate-600 dark:text-slate-500 text-sm mt-1 max-w-[250px]">Choose a duration, select distracting apps, and start a session to block them automatically.</p>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}