import axios from 'axios'
import * as mock from '../data/mockData'

const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false'
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api'

export const predictUsageCategory = async (userData) => {
  if (USE_MOCK) return { prediction: "Excessive", confidence: 0.89, model_used: "RandomForest" }
  const res = await axios.post(`${BASE_URL}/predict/usage`, userData)
  return res.data
}

export const getNextHourPrediction = async () => {
  if (USE_MOCK) return mock.usagePredictions
  // No LSTM endpoint exists yet — return mock data as fallback
  return mock.usagePredictions
}

export const getUserCluster = async (userData) => {
  if (USE_MOCK) return mock.userPersonas.find(p => p.name === mock.currentUser.cluster)
  const res = await axios.post(`${BASE_URL}/user/segment`, userData)
  return res.data
}

export const getMentalHealthRisk = async (userData) => {
  if (USE_MOCK) return mock.mentalHealthScores
  const res = await axios.post(`${BASE_URL}/predict/mental_health`, userData)
  return res.data
}

export const getRecommendations = async (persona, risk) => {
  if (USE_MOCK) return { recommendations: ["Set phone to grayscale after 9 PM", "Enable DND at 10 PM", "Schedule a 15-min break at 8 PM"] }
  const res = await axios.post(`${BASE_URL}/recommendations`, { persona, risk })
  return res.data
}

export const getWeeklyAnalytics = async () => {
  if (USE_MOCK) return mock.weeklyTrend
  const res = await axios.get(`${BASE_URL}/analytics/weekly`)
  return res.data
}

export const predictProductivity = async (userData) => {
  if (USE_MOCK) return { predicted_exam_score: 61, productivity_score: 0.54, model_used: "Ridge" }
  const res = await axios.post(`${BASE_URL}/predict/productivity`, userData)
  return res.data
}

export const getRelapseRisk = async () => {
  if (USE_MOCK) return { risk: 0.85, top_features: ["Late night (pm)", "Recent negative mood"] };
  try {
    const res = await axios.get(`${BASE_URL}/predictions/relapse-risk`);
    return res.data;
  } catch (err) {
    return { risk: 0.0, top_features: [] };
  }
}

export const getModelReport = async () => {
  if (USE_MOCK) return mock.modelMetrics
  const res = await axios.get(`${BASE_URL}/model/report`)
  return res.data
}

// ── App Tracker ──
export const getLiveUsage    = () => axios.get(`${BASE_URL}/tracker/live`).then(r => r.data)
export const getLimits       = () => axios.get(`${BASE_URL}/limits`).then(r => r.data)
export const setLimit        = (data) => axios.post(`${BASE_URL}/limits`, data).then(r => r.data)
export const deleteLimit     = (appName) => axios.delete(`${BASE_URL}/limits/${encodeURIComponent(appName)}`).then(r => r.data)

export const getInterventions = () => axios.get(`${BASE_URL}/interventions`).then(r => r.data)
export const resolveIntervention = (id) => axios.post(`${BASE_URL}/interventions/${id}`).then(r => r.data)

export const getWellnessScore = async () => {
  if (USE_MOCK) return { score: 85, risk_level: "Low", social_hours: 1.5, total_hours: 4.2 };
  try {
    const res = await axios.get(`${BASE_URL}/wellness-score`);
    return res.data;
  } catch (err) {
    return { score: 85, risk_level: "Low", social_hours: 1.5, total_hours: 4.2 };
  }
}

// ── Focus Mode ──
export const startFocus      = (data) => axios.post(`${BASE_URL}/focus/start`, data).then(r => r.data)
export const stopFocus       = ()     => axios.post(`${BASE_URL}/focus/stop`).then(r => r.data)
export const getFocusStatus  = ()     => axios.get(`${BASE_URL}/focus/status`).then(r => r.data)

// ── Pomodoro ──
export const startPomodoro   = (cfg)  => axios.post(`${BASE_URL}/pomodoro/start`, cfg).then(r => r.data)
export const stopPomodoro    = ()     => axios.post(`${BASE_URL}/pomodoro/stop`).then(r => r.data)
export const getPomodoroState= ()     => axios.get(`${BASE_URL}/pomodoro/state`).then(r => r.data)

// ── Dopamine Loop Detector ──
export const checkDopamineLoop = async () => {
  const res = await axios.get(`${BASE_URL}/dopamine-loop`)
  return res.data
}

// ── AI Life Coach ──
export const chatWithLifeCoach = async (message) => {
  if (USE_MOCK) {
    // using actual fallback if mock is true but we still want a response
    try {
      const res = await axios.post(`${BASE_URL}/coach/chat`, { message })
      return res.data;
    } catch(err) {
      return { response: "You are doing fine. Relax." }
    }
  }
  const res = await axios.post(`${BASE_URL}/coach/chat`, { message })
  return res.data
}

// ── AI Screen Addiction Therapy (CBT) ──
export const startTherapySession = async () => {
  if (USE_MOCK) return { session_id: "mock-123", messages: [{role: "assistant", content: "Hi! How can I help you today?"}] };
  const res = await axios.post(`${BASE_URL}/therapy/session`);
  return res.data;
}

export const respondTherapySession = async (sessionId, message) => {
  if (USE_MOCK) return { 
    messages: [], 
    agent_reply: "Let's take a quick break.", 
    suggested_commitment: { title: "Short Break", duration_minutes: 15 } 
  };
  const res = await axios.post(`${BASE_URL}/therapy/session/${sessionId}/respond`, { message });
  return res.data;
}

export const getTherapyPlan = async () => {
  const res = await axios.get(`${BASE_URL}/therapy/plan`)
  return res.data
}

// ── Reports ──
export const downloadDailyReport  = () => window.open(`${BASE_URL}/reports/daily`, '_blank')
export const downloadWeeklyReport = () => window.open(`${BASE_URL}/reports/weekly`, '_blank')

// ── AI Coach (Ollama) ──
export const chatWithDigiWell = async (message) => {
  if (USE_MOCK) {
    return new Promise(resolve => setTimeout(() => {
      resolve({ response: "This is a mock response from DigiWell Coach. Your actual usage data would be analyzed here if connected to the backend." });
    }, 1000));
  }
  const res = await axios.post(`${BASE_URL}/chat`, { message })
  return res.data
}

// ── Habits / Detox Challenge ──
export const getDetoxChallenge = async () => {
  if (USE_MOCK) {
    return [
      { day: 1, task: "Reduce Instagram usage by 15 mins", completed: true, date_completed: "2026-03-12" },
      { day: 2, task: "No screens 1 hour before bed", completed: false, date_completed: null },
      { day: 3, task: "Keep phone outside bedroom", completed: false, date_completed: null },
      { day: 4, task: "Grayscale mode for 4 hours", completed: false, date_completed: null },
      { day: 5, task: "Delete 1 distracting app", completed: false, date_completed: null },
      { day: 6, task: "Take 10-minute walk without phone", completed: false, date_completed: null },
      { day: 7, task: "Full day: Social media fasting!", completed: false, date_completed: null }
    ]
  }
  const res = await axios.get(`${BASE_URL}/habits/challenge`);
  return res.data;
}

export const completeDetoxTask = async (day, completed) => {
  if (USE_MOCK) return { status: "success", day, completed };
  const res = await axios.post(`${BASE_URL}/habits/challenge`, { day, completed });
  return res.data;
}

// ── AI Daily Reflection ──
export const getDailyReflection = async () => {
  if (USE_MOCK) {
    return {
      today_hours: 5.2,
      yesterday_hours: 6.4,
      difference_hours: 1.2,
      trend: "down",
      summary: "Great job! You've reduced your screen time today compared to yesterday."
    };
  }
  const res = await axios.get(`${BASE_URL}/daily-reflection`);
  return res.data;
}

// ── AI Personalized Focus Mode ──
export const getFocusRecommendation = async () => {
  if (USE_MOCK) {
    return {
      recommended_duration_minutes: 45,
      recommended_block_list: ["Instagram", "TikTok", "YouTube"],
      reasoning: "Based on your recent high usage of these apps, we recommend blocking them to minimize distractions."
    };
  }
  const res = await axios.get(`${BASE_URL}/focus/recommend`);
  return res.data;
}

// ── AI Digital Twin Simulator ──
export const getDigitalTwinSimulation = async (data) => {
  if (USE_MOCK) {
    return {
      days_projected: data.days || 30,
      projected_daily_hours: 7.2,
      productivity_impact_percent: -18.5,
      sleep_impact_percent: -12.0,
      mental_health_forecast: "High Risk",
      message: "If current trends continue, your daily screen time will reach 7.2 hrs. Productivity could drop by 18.5%."
    };
  }
  const res = await axios.post(`${BASE_URL}/predict/simulation`, data || {});
  return res.data;
}

// ── Anomaly Detection & Mood Journal ──
export const checkAnomaly = async (timeSpent) => {
  if (USE_MOCK) return { is_anomaly: timeSpent > 300, risk_score: 0.8 }
  const res = await axios.post(`${BASE_URL}/anomaly`, { time_spent: timeSpent })
  return res.data
}

// ── Realtime Pre-emptive AI ──
export const predictRealtimeDoomscroll = async (payload) => {
  if (USE_MOCK) return { risk: Math.random(), action: "suggest_break", confidence: 0.85 };
  try {
    const res = await axios.post(`${BASE_URL}/predict/realtime`, payload);
    return res.data;
  } catch (err) {
    return { risk: 0, action: "none", confidence: 0.0 };
  }
}

export const getMoodJournals = async () => {
  if (USE_MOCK) return [{ date: new Date().toISOString(), entry: "Feeling great after limiting my screen time!", mood_score: 5, polarity: 0.8 }];
  const res = await axios.get(`${BASE_URL}/mood`)
  return res.data
}

export const analyzeAndSaveMoodJournal = async (entry, moodScore) => {
  if (USE_MOCK) return {
    status: "saved", entry: { date: new Date().toISOString(), entry, mood_score: moodScore, polarity: 0.5 },
    ai_primary_emotion: "Anxious",
    ai_distortion: ["Catastrophizing"],
    ai_reframe: "This is a mock reframe.",
    ai_microtask: { type: "breathing", duration_minutes: 1, instruction: "Breathe in, breathe out." }
  };
  const res = await axios.post(`${BASE_URL}/mood/analyze-and-save`, { entry, mood_score: moodScore });
  return res.data;
}

export const addMoodJournal = async (entry, moodScore) => {
  if (USE_MOCK) return { status: "saved", entry: { date: new Date().toISOString(), entry, mood_score: moodScore, polarity: 0.5 } };
  const res = await axios.post(`${BASE_URL}/mood`, { entry, mood_score: moodScore })
  return res.data
}

// ── Focus Productivity & Burnout Risk ──
export const getProductivityScore = async () => {
  if (USE_MOCK) return { productivity_score: 75, deep_work_minutes: 120, distracted_minutes: 40, best_focus_window: "10:00" };
  try {
    const res = await axios.get(`${BASE_URL}/productivity-score`);
    return res.data;
  } catch (err) {
    return { productivity_score: 75, deep_work_minutes: 120, distracted_minutes: 40, best_focus_window: "10:00" };
  }
}

export const predictBurnoutRisk = async (payload) => {
  if (USE_MOCK) return { burnout_risk_percentage: payload.screen_time_hours > 8 ? 85 : 45, is_high_risk: payload.screen_time_hours > 8, warning: payload.screen_time_hours > 8 ? "Burnout Risk Detected" : "Burnout risk is manageable." };
  try {
    const res = await axios.post(`${BASE_URL}/predict/burnout`, payload);
    return res.data;
  } catch (err) {
    return { burnout_risk_percentage: 45, is_high_risk: false, warning: "Burnout risk is manageable." };
  }
}




export const getAddictionHeatmap = async () => {
  if (USE_MOCK) {
    const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    const dummy = [];
    for(let d=0; d<days.length; d++){
      for(let h=0; h<24; h++){
        let val = Math.random() * 60;
        let risk = val < 15 ? "Low" : val < 30 ? "Medium" : val < 60 ? "High" : "Very High";
        dummy.push({day: days[d], hour: h, value: Math.floor(val), riskLevel: risk});
      }
    }
    return dummy;
  }
  const res = await axios.get(`${BASE_URL}/addiction-heatmap`);
  return res.data;
}

// ── Commitments API ───────────────────────────────────────

export const startCommitment = async (payload) => {
  if (USE_MOCK) {
    return {
      commitment_id: "mock-123",
      status: "active",
      start_ts: new Date().toISOString(),
      expected_end_ts: new Date(Date.now() + payload.expected_duration_minutes * 60000).toISOString(),
      focus_session_created: payload.auto_start_focus
    }
  }
  const res = await fetch(`${BASE_URL}/commitments/start`, {
    method: 'POST',
    body: JSON.stringify(payload),
    headers: { 'Content-Type': 'application/json' }
  });
  if (!res.ok) throw new Error('Failed to start commitment');
  return res.json();
}

export const getCommitments = async () => {
  if (USE_MOCK) return [];
  const res = await fetch(`${BASE_URL}/commitments`);
  if (!res.ok) throw new Error('Failed to get commitments');
  return res.json();
}

export const completeCommitment = async (id) => {
  if (USE_MOCK) return { status: 'completed' };
  const res = await fetch(`${BASE_URL}/commitments/${id}/complete`, {
    method: 'POST'
  });
  if (!res.ok) throw new Error('Failed to complete commitment');
  return res.json();
}
