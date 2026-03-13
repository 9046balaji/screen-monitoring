// 1. Current user profile
export const currentUser = {
  name: "Arjun Reddy",
  age: 22,
  profession: "Student",
  platform: "Instagram",
  income: 8000,
  gender: "male",
  cluster: "Night Scroller",
  clusterDescription: "Heavy social media use after 10 PM. High mental health risk.",
  dailyGoalMinutes: 120
}

// 2. Today's hourly usage (24 values, realistic pattern)
export const todayHourlyUsage = [
  {hour:"12AM",minutes:5}, {hour:"1AM",minutes:18}, {hour:"2AM",minutes:45},
  {hour:"3AM",minutes:12}, {hour:"4AM",minutes:2}, {hour:"5AM",minutes:0},
  {hour:"6AM",minutes:3}, {hour:"7AM",minutes:22}, {hour:"8AM",minutes:35},
  {hour:"9AM",minutes:28}, {hour:"10AM",minutes:15}, {hour:"11AM",minutes:20},
  {hour:"12PM",minutes:30}, {hour:"1PM",minutes:25}, {hour:"2PM",minutes:18},
  {hour:"3PM",minutes:22}, {hour:"4PM",minutes:35}, {hour:"5PM",minutes:40},
  {hour:"6PM",minutes:55}, {hour:"7PM",minutes:70}, {hour:"8PM",minutes:85},
  {hour:"9PM",minutes:90}, {hour:"10PM",minutes:60}, {hour:"11PM",minutes:40}
]

// 3. 7-day usage trend
export const weeklyTrend = [
  {day:"Mon", minutes:280, goal:120},
  {day:"Tue", minutes:320, goal:120},
  {day:"Wed", minutes:195, goal:120},
  {day:"Thu", minutes:410, goal:120},
  {day:"Fri", minutes:380, goal:120},
  {day:"Sat", minutes:520, goal:120},
  {day:"Sun", minutes:460, goal:120},
]

// 4. App category breakdown
export const appBreakdown = [
  {name:"Instagram",  minutes:180, color:"#E1306C"},
  {name:"YouTube",    minutes:95,  color:"#FF0000"},
  {name:"Facebook",   minutes:45,  color:"#1877F2"},
  {name:"WhatsApp",   minutes:60,  color:"#25D366"},
  {name:"Games",      minutes:40,  color:"#7C3AED"},
  {name:"Other",      minutes:20,  color:"#94A3B8"},
]

// 5. LSTM predictions — next 6 hours
export const usagePredictions = [
  {hour:"Now",   actual:85,  predicted:85},
  {hour:"+1hr",  actual:null, predicted:95},
  {hour:"+2hr",  actual:null, predicted:110},
  {hour:"+3hr",  actual:null, predicted:75},
  {hour:"+4hr",  actual:null, predicted:50},
  {hour:"+5hr",  actual:null, predicted:35},
  {hour:"+6hr",  actual:null, predicted:20},
]

// 6. Mental health scores (from smmh.csv fields)
export const mentalHealthScores = {
  distractionScore: 4,
  restlessnessScore: 3,
  depressionScore: 4,
  sleepIssuesScore: 5,
  concentrationScore: 3,
  overallRisk: "High",  // Low / Medium / High
  riskScore: 78         // 0-100
}

// 7. Student productivity (from StudentPerformanceFactors)
export const productivityData = {
  hoursStudied: 14,
  sleepHours: 5.5,
  motivationLevel: "Low",    // Low/Medium/High
  examScore: 61,
  attendance: 72,
  physicalActivity: 2,
  productivityScore: 0.54
}

// 8. Feature importances (Random Forest output)
export const featureImportances = [
  {feature:"Time Spent",         importance:0.31},
  {feature:"Platform Type",      importance:0.22},
  {feature:"Late Night Usage",   importance:0.18},
  {feature:"Age",                importance:0.12},
  {feature:"Session Count",      importance:0.09},
  {feature:"Income Level",       importance:0.08},
]

// 9. Weekly heatmap (hour x day)
const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
export const usageHeatmap = [];
for (let d = 0; d < days.length; d++) {
  for (let h = 0; h < 24; h++) {
    let base = Math.random() * 30;
    if (h >= 21 || h <= 2) {
      if (days[d] === "Fri" || days[d] === "Sat" || days[d] === "Sun") {
        base += 50 + Math.random() * 20;
      } else {
        base += 30 + Math.random() * 20;
      }
    }
    usageHeatmap.push({
      day: days[d],
      hour: h,
      value: Math.round(base)
    });
  }
}

// 10. User segments / personas
export const userPersonas = [
  {id:1, name:"Night Scroller",      emoji:"🌙", color:"#7C3AED", risk:"High",   description:"Heavy usage after 10 PM. Sleep deprived."},
  {id:2, name:"Balanced Professional",emoji:"⚖️", color:"#10B981", risk:"Low",    description:"Controlled usage. Productivity-first."},
  {id:3, name:"Social Addict",       emoji:"📱", color:"#EF4444", risk:"High",   description:"3+ hours on social platforms daily."},
  {id:4, name:"Productive Learner",  emoji:"📚", color:"#3B82F6", risk:"Low",    description:"Low social media. High study hours."},
  {id:5, name:"Weekend Binger",      emoji:"🎮", color:"#F59E0B", risk:"Medium", description:"Low weekday usage, spikes on weekends."},
]

// 11. ML model performance metrics — REAL values from model_report.json after retraining
export const modelMetrics = {
  classifier:  {name:"RandomForest",        accuracy:0.37, f1:0.37, model:"Usage Category"},
  mentalHealth:{name:"GradientBoosting",     accuracy:0.91, f1:0.91, model:"Mental Health Risk"},
  regressor:   {name:"Ridge Regressor",      r2:0.69, rmse:2.1,     model:"Productivity Score"},
  clustering:  {name:"K-Means (k=5)",        silhouette:0.22,        model:"User Segmentation"},
}
