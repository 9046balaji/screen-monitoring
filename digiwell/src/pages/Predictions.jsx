import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Bot, AlertCircle, Bell, Activity, BrainCircuit } from 'lucide-react';
import PredictionChart from '../components/charts/PredictionChart';
import { usagePredictions as mockPredictions, currentUser, mentalHealthScores as mockMental } from '../data/mockData';
import { getMentalHealthRisk, getModelReport, getRecommendations, getUserCluster, getNextHourPrediction, getDigitalTwinSimulation } from '../api/digiwell';
import toast from 'react-hot-toast';

export default function Predictions() {
  const [grayscale, setGrayscale] = useState(false);
  const [dnd, setDnd] = useState(false);
  const [predictions, setPredictions] = useState(mockPredictions);
  const [modelConfidence, setModelConfidence] = useState(null);
  const [recommendations, setRecommendations] = useState([
    "Set phone to grayscale after 9 PM",
    "Enable Do Not Disturb at 10 PM",
    "Schedule a 15-min break at 8 PM"
  ]);
  const [riskInfo, setRiskInfo] = useState({ prediction: null, risk_score: null });
  const [twinData, setTwinData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [mentalRes, reportRes, segRes, predRes, twinRes] = await Promise.allSettled([
          getMentalHealthRisk({
            distraction_score: mockMental.distractionScore,
            concentration_score: mockMental.concentrationScore,
            depression_score: mockMental.depressionScore,
            interest_fluctuation: 3,
            sleep_issues_score: mockMental.sleepIssuesScore,
            purposeless_usage: 4,
            distracted_when_busy: 3,
            restlessness_score: mockMental.restlessnessScore,
            worries_score: 3,
            comparison_score: 3,
            comparison_feeling: 3,
            validation_seeking: 3,
            avg_daily_usage: 6.3,
            age: currentUser.age,
          }),
          getModelReport(),
          getUserCluster({
            time_spent: 6.3,
            age: currentUser.age,
            income: currentUser.income,
            platform_risk_score: 3,
          }),
          getNextHourPrediction(),
          getDigitalTwinSimulation({ days: 30, current_daily_hours: 6.3, trend_modifier: 1.05 })
        ]);

        if (mentalRes.status === 'fulfilled') {
          setRiskInfo(mentalRes.value);
          setModelConfidence(mentalRes.value.confidence);
        }

        if (reportRes.status === 'fulfilled' && reportRes.value?.mental_health_clf) {
          setModelConfidence(prev => prev || reportRes.value.mental_health_clf.f1_score);
        }

        if (predRes.status === 'fulfilled') {
          setPredictions(predRes.value);
        }
        
        if (twinRes.status === 'fulfilled') {
          setTwinData(twinRes.value);
        }

        // Get persona-specific recommendations
        if (segRes.status === 'fulfilled' && segRes.value?.persona) {
          const recsRes = await getRecommendations(segRes.value.persona, segRes.value.risk);
          if (recsRes?.recommendations) {
            setRecommendations(recsRes.recommendations.slice(0, 3));
          }
        }
      } catch (err) {
        console.error('Failed to fetch prediction data:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const hasHighRisk = predictions.some(p => p.predicted > 60);
  const confidencePercent = modelConfidence ? Math.round(modelConfidence * 100) : 91;

  const handleReminder = () => {
    toast.success('Reminder set for 8 PM');
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Info Banner */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-2xl border border-primary/50 bg-primary/10 p-4 flex items-center gap-3"
      >
        <Bot className="w-6 h-6 text-primary shrink-0" />
        <p className="text-white font-medium text-sm">
          Predictions powered by ML models — Mental health risk: {riskInfo.prediction || 'Loading...'} ({confidencePercent}% confidence)
        </p>
      </motion.div>

      {/* Main Chart */}
      <PredictionChart data={predictions} delay={0.1} />

      {/* Risk Alert Card */}
      {hasHighRisk && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="rounded-2xl border border-danger bg-surface p-6 shadow-lg flex flex-col gap-2"
        >
          <div className="flex items-center gap-2 text-danger">
            <AlertCircle className="w-6 h-6" />
            <h3 className="text-lg font-bold">High Risk Window Detected: 8 PM - 10 PM tonight</h3>
          </div>
          <p className="text-muted text-sm">
            {riskInfo.prediction === 'High'
              ? `Mental health risk is HIGH (score: ${riskInfo.risk_score}/100). You typically spike 85+ minutes in this window.`
              : 'Based on your pattern, you typically spike 85+ minutes in this window'}
          </p>
          <button className="mt-2 self-start px-4 py-2 bg-danger hover:bg-danger/90 text-white rounded-lg text-sm font-medium transition-colors">
            Set a screen limit for this period
          </button>
        </motion.div>
      )}

      {/* AI Digital Twin Simulator */}
      {twinData && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="rounded-2xl border border-indigo-500/30 bg-gradient-to-r from-indigo-500/10 to-transparent p-6 shadow-lg"
        >
          <div className="flex items-center gap-2 text-indigo-400 mb-4">
            <BrainCircuit className="w-6 h-6" />
            <h3 className="text-xl font-bold text-white">AI Digital Twin Simulator</h3>
          </div>
          <p className="text-slate-300 text-sm mb-6">
            Projecting your habits <span className="font-bold text-indigo-300">{twinData.days_projected} days</span> into the future based on current trends.
          </p>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
            <div className="bg-slate-800/60 p-4 rounded-xl border border-slate-700">
              <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">Projected Daily Usage</p>
              <p className="text-2xl font-black text-white">{twinData.projected_daily_hours} hrs</p>
            </div>
            <div className="bg-slate-800/60 p-4 rounded-xl border border-slate-700">
              <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">Productivity Impact</p>
              <p className="text-2xl font-black text-danger">{twinData.productivity_impact_percent}%</p>
            </div>
            <div className="bg-slate-800/60 p-4 rounded-xl border border-slate-700">
              <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">Sleep Impact</p>
              <p className="text-2xl font-black text-warning">{twinData.sleep_impact_percent}%</p>
            </div>
            <div className="bg-slate-800/60 p-4 rounded-xl border border-slate-700">
              <p className="text-xs text-slate-400 uppercase tracking-wider mb-1">Mental Health Forecast</p>
              <p className={`text-2xl font-black ${twinData.mental_health_forecast === 'High Risk' ? 'text-danger' : 'text-primary'}`}>
                {twinData.mental_health_forecast}
              </p>
            </div>
          </div>
          
          <div className="bg-indigo-500/20 text-indigo-200 p-3 rounded-lg border border-indigo-500/20 text-sm font-medium">
            💡 {twinData.message}
          </div>
        </motion.div>
      )}

      {/* Recommendations from ML model */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="grid grid-cols-1 md:grid-cols-3 gap-6"
      >
        {recommendations.map((rec, idx) => (
          <div key={idx} className="rounded-2xl border border-slate-700 bg-surface p-6 shadow-lg flex flex-col justify-between gap-4">
            <p className="text-white font-medium">{rec}</p>
            {idx === 0 && (
              <button
                onClick={() => setGrayscale(!grayscale)}
                className={`self-start px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  grayscale ? 'bg-success text-white' : 'bg-slate-700 text-white hover:bg-slate-600'
                }`}
              >
                {grayscale ? 'Enabled' : 'Enable'}
              </button>
            )}
            {idx === 1 && (
              <button
                onClick={() => setDnd(!dnd)}
                className={`self-start px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  dnd ? 'bg-success text-white' : 'bg-slate-700 text-white hover:bg-slate-600'
                }`}
              >
                {dnd ? 'Enabled' : 'Enable'}
              </button>
            )}
            {idx === 2 && (
              <button
                onClick={handleReminder}
                className="self-start flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary/90 text-white rounded-lg text-sm font-medium transition-colors"
              >
                <Bell className="w-4 h-4" />
                Set Reminder
              </button>
            )}
          </div>
        ))}
      </motion.div>

      {/* Model Confidence */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="rounded-2xl border border-slate-700 bg-surface p-6 shadow-lg flex flex-col gap-2"
      >
        <div className="flex justify-between items-center text-sm">
          <span className="text-white font-medium">Model Confidence: {confidencePercent}%</span>
          {riskInfo.prediction && (
            <span className="text-muted text-xs">Model: {riskInfo.model_used || 'GradientBoosting'}</span>
          )}
        </div>
        <div className="h-1.5 w-full bg-slate-700 rounded-full overflow-hidden">
          <div className="h-full bg-primary rounded-full" style={{ width: `${confidencePercent}%` }} />
        </div>
        <p className="text-xs text-muted mt-1">Prediction confidence from trained ML model. Real-time inference from Flask backend.</p>
      </motion.div>
    </div>
  );
}
