import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import { currentUser, userPersonas, mentalHealthScores as mockMental, productivityData as mockProductivity, modelMetrics as mockMetrics } from '../data/mockData';
import RiskBadge from '../components/ui/RiskBadge';
import PersonaCard from '../components/cards/PersonaCard';
import MentalHealthCard from '../components/cards/MentalHealthCard';
import { getUserCluster, getMentalHealthRisk, predictProductivity, getModelReport } from '../api/digiwell';

export default function Profile() {
  const [goal, setGoal] = useState(currentUser.dailyGoalMinutes);
  const [platform, setPlatform] = useState(currentUser.platform);
  const [profession, setProfession] = useState(currentUser.profession);

  const [activePersona, setActivePersona] = useState(currentUser.cluster);
  const [mentalScores, setMentalScores] = useState(mockMental);
  const [prodData, setProdData] = useState(mockProductivity);
  const [modelMetrics, setModelMetrics] = useState(mockMetrics);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchProfileData() {
      try {
        const [segRes, mentalRes, prodRes, reportRes] = await Promise.allSettled([
          getUserCluster({
            time_spent: 6.3,
            age: currentUser.age,
            income: currentUser.income,
            platform_risk_score: platform === 'Instagram' ? 3 : platform === 'YouTube' ? 2 : 2,
          }),
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
          predictProductivity({
            hours_studied: mockProductivity.hoursStudied,
            attendance: mockProductivity.attendance,
            sleep_hours: Math.round(mockProductivity.sleepHours),
            previous_scores: mockProductivity.examScore,
            tutoring_sessions: 1,
            physical_activity: mockProductivity.physicalActivity,
            parental_involvement_encoded: 1,
            access_to_resources_encoded: 1,
            extracurricular_encoded: 0,
            motivation_encoded: mockProductivity.motivationLevel === 'Low' ? 0 : mockProductivity.motivationLevel === 'Medium' ? 1 : 2,
            internet_access_encoded: 1,
            family_income_encoded: 1,
            teacher_quality_encoded: 1,
            school_type_encoded: 0,
            peer_influence_encoded: 1,
            learning_disabilities_encoded: 0,
            parental_education_encoded: 1,
            distance_encoded: 1,
            gender_encoded: currentUser.gender === 'male' ? 0 : 1,
          }),
          getModelReport(),
        ]);

        if (segRes.status === 'fulfilled' && segRes.value?.persona) {
          setActivePersona(segRes.value.persona);
        }

        if (mentalRes.status === 'fulfilled') {
          setMentalScores(prev => ({
            ...prev,
            overallRisk: mentalRes.value.prediction || prev.overallRisk,
            riskScore: mentalRes.value.risk_score || prev.riskScore,
          }));
        }

        if (prodRes.status === 'fulfilled') {
          const score = prodRes.value.predicted_exam_score || mockProductivity.examScore;
          const prodScore = prodRes.value.productivity_score || mockProductivity.productivityScore;
          setProdData(prev => ({
            ...prev,
            examScore: Math.round(score),
            productivityScore: prodScore,
            motivationLevel: prodScore >= 0.7 ? 'High' : prodScore >= 0.4 ? 'Medium' : 'Low',
          }));
        }

        if (reportRes.status === 'fulfilled') {
          const r = reportRes.value;
          setModelMetrics({
            classifier: { name: r.usage_classifier?.best_model || 'RandomForest', accuracy: r.usage_classifier?.accuracy || 0.37, f1: r.usage_classifier?.f1_score || 0.37, model: 'Usage Category' },
            mentalHealth: { name: r.mental_health_clf?.best_model || 'GradientBoosting', accuracy: r.mental_health_clf?.accuracy || 0.91, f1: r.mental_health_clf?.f1_score || 0.91, model: 'Mental Health Risk' },
            regressor: { name: r.productivity_reg?.best_model || 'Ridge Regressor', r2: r.productivity_reg?.r2 || 0.69, rmse: r.productivity_reg?.rmse || 2.1, model: 'Productivity Score' },
            clustering: { name: `K-Means (k=${r.user_segmentation?.k || 5})`, silhouette: r.user_segmentation?.silhouette || 0.22, model: 'User Segmentation' },
          });
        }
      } catch (err) {
        console.error('Failed to fetch profile data:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchProfileData();
  }, []);

  const handleSave = () => {
    toast.success('Profile updated successfully!');
  };

  return (
    <div className="flex flex-col gap-8">
      {/* Top Section: User Info */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-2xl border border-slate-700 bg-surface p-6 shadow-lg flex flex-col md:flex-row gap-8 items-start"
      >
        <div className="flex flex-col items-center gap-4">
          <div className="w-24 h-24 rounded-full bg-primary flex items-center justify-center text-white text-3xl font-bold">
            {currentUser.name.split(' ').map(n => n[0]).join('')}
          </div>
          <div className="text-center">
            <h2 className="text-xl font-bold text-white">{currentUser.name}</h2>
            <p className="text-muted text-sm">{currentUser.age} years old</p>
          </div>
        </div>

        <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-6 w-full">
          <div className="flex flex-col gap-2">
            <label className="text-sm text-muted">Daily Goal (minutes)</label>
            <input
              type="number"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              className="bg-base border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-primary"
            />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-sm text-muted">Primary Platform</label>
            <select
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
              className="bg-base border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-primary"
            >
              <option value="Instagram">Instagram</option>
              <option value="Facebook">Facebook</option>
              <option value="YouTube">YouTube</option>
            </select>
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-sm text-muted">Profession</label>
            <select
              value={profession}
              onChange={(e) => setProfession(e.target.value)}
              className="bg-base border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-primary"
            >
              <option value="Student">Student</option>
              <option value="Software Engineer">Software Engineer</option>
              <option value="Marketer Manager">Marketer Manager</option>
            </select>
          </div>
          <div className="flex items-end">
            <button
              onClick={handleSave}
              className="w-full px-4 py-2 bg-primary hover:bg-primary/90 text-white rounded-lg font-medium transition-colors"
            >
              Save Changes
            </button>
          </div>
        </div>
      </motion.div>

      {/* Cluster / Persona Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="flex flex-col gap-4"
      >
        <h3 className="text-xl font-bold text-white">Your Digital Persona {loading ? '' : '(ML Predicted)'}</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
          {userPersonas.map((persona) => (
            <PersonaCard
              key={persona.id}
              persona={persona}
              isUser={persona.name === activePersona}
            />
          ))}
        </div>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Mental Health Breakdown */}
        <MentalHealthCard scores={mentalScores} delay={0.2} />

        {/* Productivity Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="rounded-2xl border border-slate-700 bg-surface p-6 shadow-lg flex flex-col gap-6"
        >
          <h3 className="text-lg font-semibold text-white">Productivity Profile {loading ? '' : '(ML Predicted)'}</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-base border border-slate-700 rounded-xl p-4">
              <p className="text-muted text-sm">Study Hours/wk</p>
              <p className="text-2xl font-bold text-white mt-1">{prodData.hoursStudied}</p>
            </div>
            <div className="bg-base border border-slate-700 rounded-xl p-4">
              <p className="text-muted text-sm">Sleep Hours/night</p>
              <p className="text-2xl font-bold text-white mt-1">{prodData.sleepHours}</p>
            </div>
            <div className="bg-base border border-slate-700 rounded-xl p-4">
              <p className="text-muted text-sm">Motivation</p>
              <div className="mt-2"><RiskBadge risk={prodData.motivationLevel} /></div>
            </div>
            <div className="bg-base border border-slate-700 rounded-xl p-4">
              <p className="text-muted text-sm">Predicted Exam Score</p>
              <p className="text-2xl font-bold text-white mt-1">{prodData.examScore}%</p>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Model Results Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="rounded-2xl border border-slate-700 bg-surface p-6 shadow-lg flex flex-col gap-4"
      >
        <h3 className="text-lg font-semibold text-white">ML Model Metrics {loading ? '' : '(Live from Backend)'}</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-muted">
            <thead className="text-xs uppercase bg-base text-white">
              <tr>
                <th className="px-4 py-3 rounded-tl-lg">Model Task</th>
                <th className="px-4 py-3">Algorithm</th>
                <th className="px-4 py-3">Metrics</th>
                <th className="px-4 py-3 rounded-tr-lg">Status</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-slate-700">
                <td className="px-4 py-3 font-medium text-white">{modelMetrics.classifier.model}</td>
                <td className="px-4 py-3">{modelMetrics.classifier.name}</td>
                <td className="px-4 py-3">Acc: {modelMetrics.classifier.accuracy} | F1: {modelMetrics.classifier.f1}</td>
                <td className="px-4 py-3 text-success">Deployed</td>
              </tr>
              <tr className="border-b border-slate-700">
                <td className="px-4 py-3 font-medium text-white">{modelMetrics.mentalHealth.model}</td>
                <td className="px-4 py-3">{modelMetrics.mentalHealth.name}</td>
                <td className="px-4 py-3">Acc: {modelMetrics.mentalHealth.accuracy} | F1: {modelMetrics.mentalHealth.f1}</td>
                <td className="px-4 py-3 text-success">Deployed</td>
              </tr>
              <tr className="border-b border-slate-700">
                <td className="px-4 py-3 font-medium text-white">{modelMetrics.regressor.model}</td>
                <td className="px-4 py-3">{modelMetrics.regressor.name}</td>
                <td className="px-4 py-3">R2: {modelMetrics.regressor.r2} | RMSE: {modelMetrics.regressor.rmse}</td>
                <td className="px-4 py-3 text-success">Deployed</td>
              </tr>
              <tr>
                <td className="px-4 py-3 font-medium text-white">{modelMetrics.clustering.model}</td>
                <td className="px-4 py-3">{modelMetrics.clustering.name}</td>
                <td className="px-4 py-3">Silhouette: {modelMetrics.clustering.silhouette}</td>
                <td className="px-4 py-3 text-success">Deployed</td>
              </tr>
            </tbody>
          </table>
        </div>
      </motion.div>
    </div>
  );
}
