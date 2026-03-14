import { useState, useEffect } from 'react';
import { Clock, Activity, Brain, Target, ShieldAlert, Sparkles } from 'lucide-react';
import StatCard from '../components/cards/StatCard';
import WellnessScoreCard from '../components/cards/WellnessScoreCard';
import AddictionRiskCard from '../components/cards/AddictionRiskCard';
import AlertBanner from '../components/cards/AlertBanner';
import HourlyBarChart from '../components/charts/HourlyBarChart';
import AppDonutChart from '../components/charts/AppDonutChart';
import WeeklyLineChart from '../components/charts/WeeklyLineChart';
import RiskBadge from '../components/ui/RiskBadge';
import { weeklyTrend as mockWeeklyTrend, currentUser, mentalHealthScores as mockMentalHealth, productivityData as mockProductivity } from '../data/mockData';
import { predictUsageCategory, getMentalHealthRisk, predictProductivity, getUserCluster, checkAnomaly, getWellnessScore, getInterventions, resolveIntervention, predictRealtimeDoomscroll, getProductivityScore, predictBurnoutRisk, getDailyReflection, getDailyUsage, getAnalyticsWeekly } from '../api/digiwell';

export default function Dashboard() {
  const [usageCategory, setUsageCategory] = useState(null);
  const [mentalHealth, setMentalHealth] = useState(null);
  const [productivity, setProductivity] = useState(null);
  const [focusProdData, setFocusProdData] = useState(null);
  const [burnoutData, setBurnoutData] = useState(null);
  const [persona, setPersona] = useState(null);
  const [anomaly, setAnomaly] = useState(null);
  const [wellnessData, setWellnessData] = useState(null);
  const [interventions, setInterventions] = useState([]);
  const [doomWarning, setDoomWarning] = useState(null);
  const [dailyReflection, setDailyReflection] = useState(null);
  const [todayUsage, setTodayUsage] = useState(null);
  const [weeklyTrendData, setWeeklyTrendData] = useState([]);
  const [loading, setLoading] = useState(true);

  const formatDurationSeconds = (seconds = 0) => {
    const totalMinutes = Math.max(0, Math.round(seconds / 60));
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    return `${hours}h ${minutes}m`;
  };

  const mapWeeklyTimeline = (weeklyRes) => {
    if (!weeklyRes?.timeline || !Array.isArray(weeklyRes.timeline)) return [];
    return weeklyRes.timeline.map((entry) => ({
      day: entry.day,
      minutes: Math.round(entry.minutes || 0),
      goal: 180,
    }));
  };

  useEffect(() => {
    async function fetchData() {
      try {
        const dailyUsageRes = await getDailyUsage().catch(() => null);
        if (dailyUsageRes) {
          setTodayUsage(dailyUsageRes);
        }

        const todayScreenHours = dailyUsageRes?.total_screen_time_seconds
          ? Number((dailyUsageRes.total_screen_time_seconds / 3600).toFixed(2))
          : 0;

        const [usageRes, mentalRes, prodRes, segRes, anomalyRes, wellnessRes, interventionRes, focusProdRes, burnoutRes, reflectionRes, weeklyRes] = await Promise.allSettled([
          predictUsageCategory({
            age_scaled: currentUser.age / 50,
            income_scaled: currentUser.income / 100000,
            gender_encoded: currentUser.gender === 'male' ? 1 : 0,
            platform_encoded: currentUser.platform === 'Instagram' ? 0 : currentUser.platform === 'Facebook' ? 1 : 2,
            interests_encoded: 0,
            location_encoded: 0,
            demographics_encoded: 0,
            profession_encoded: currentUser.profession === 'Student' ? 0 : 1,
            indebt: 0,
            isHomeOwner: 0,
            Owns_Car: 0,
            platform_risk_score: currentUser.platform === 'Instagram' ? 3 : 2,
          }),
          getMentalHealthRisk({
            distraction_score: mockMentalHealth.distractionScore,
            concentration_score: mockMentalHealth.concentrationScore,
            depression_score: mockMentalHealth.depressionScore,
            interest_fluctuation: 3,
            sleep_issues_score: mockMentalHealth.sleepIssuesScore,
            purposeless_usage: 4,
            distracted_when_busy: 3,
            restlessness_score: mockMentalHealth.restlessnessScore,
            worries_score: 3,
            comparison_score: 3,
            comparison_feeling: 3,
            validation_seeking: 3,
            avg_daily_usage: todayScreenHours,
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
          getUserCluster({
            time_spent: todayScreenHours,
            age: currentUser.age,
            income: currentUser.income,
            platform_risk_score: 3,
          }),
          checkAnomaly(todayScreenHours),
          getWellnessScore(),
          getInterventions(),
          getProductivityScore(),
          predictBurnoutRisk({
            screen_time_hours: todayScreenHours,
            mood_score: 5, // mock mood score
            sleep_hours: 6 // mock sleep
          }),
          getDailyReflection(),
          getAnalyticsWeekly()
        ]);

        if (usageRes.status === 'fulfilled') setUsageCategory(usageRes.value);
        if (mentalRes.status === 'fulfilled') setMentalHealth(mentalRes.value);
        if (prodRes.status === 'fulfilled') setProductivity(prodRes.value);
        if (segRes.status === 'fulfilled') setPersona(segRes.value);
        if (anomalyRes.status === 'fulfilled') setAnomaly(anomalyRes.value);
        if (wellnessRes.status === 'fulfilled') setWellnessData(wellnessRes.value);
        if (interventionRes.status === 'fulfilled') setInterventions(interventionRes.value.filter(i => i.status === 'pending'));
        if (focusProdRes.status === 'fulfilled') setFocusProdData(focusProdRes.value);
        if (burnoutRes.status === 'fulfilled') setBurnoutData(burnoutRes.value);
        if (reflectionRes.status === 'fulfilled') setDailyReflection(reflectionRes.value);
        if (weeklyRes.status === 'fulfilled') {
          const mapped = mapWeeklyTimeline(weeklyRes.value);
          setWeeklyTrendData(mapped);
        }

        checkDoomScroll();
      } catch (err) {
        console.error('Failed to fetch data:', err);
      } finally {
        setLoading(false);
      }
    }

    async function checkDoomScroll() {
      try {
        const res = await predictRealtimeDoomscroll({
          user_id: "demo",
          last_events: [
            { app: "Instagram", duration: 1200 },
            { app: "TikTok", duration: 800 }
          ],
          hour_of_day: new Date().getHours()
        });
        if (res?.risk && res.risk > 0.7) {
          setDoomWarning(res);
        }
      } catch(e) {}
    }

    fetchData();
    // Poll for interventions every 10s
    const int = setInterval(async () => {
      try {
        const invs = await getInterventions();
        setInterventions(invs.filter(i => i.status === 'pending'));
        checkDoomScroll();
      } catch (e) {}
    }, 10000);
    return () => clearInterval(int);
  }, []);

  // Derive display values from model responses or fallback to mock
  const mentalRisk = mentalHealth?.prediction || mockMentalHealth.overallRisk;
  const mentalRiskScore = mentalHealth?.risk_score || mockMentalHealth.riskScore;
  const prodScore = productivity?.productivity_score ?? mockProductivity.productivityScore;
  const prodMotivation = prodScore >= 0.7 ? 'High' : prodScore >= 0.4 ? 'Medium' : 'Low';
  const usageLabel = usageCategory?.prediction || 'Excessive';
  const usageConfidence = usageCategory?.confidence;

  // Wellness score: composite of mental health risk + productivity + usage
  const mentalComponent = mentalRisk === 'Low' ? 80 : mentalRisk === 'Medium' ? 50 : 20;
  const prodComponent = Math.round(prodScore * 100);
  const usageComponent = usageLabel === 'Light' ? 90 : usageLabel === 'Moderate' ? 60 : 20;
  const wellnessScore = Math.round((mentalComponent + prodComponent + usageComponent) / 3);

  return (
    <div className="flex flex-col gap-6">
      {interventions.map((inv, idx) => (
        <div key={inv.id} className="animate-in slide-in-from-top-4">
          <div className="bg-danger/20 border border-danger/50 p-4 rounded-xl flex items-center justify-between">
            <div className="flex items-center gap-3">
              <ShieldAlert className="text-danger" size={24} />
              <div>
                <h4 className="text-slate-900 dark:text-white font-semibold flex items-center gap-2">
                  AI Intervention <span className="bg-danger text-white text-xs px-2 py-0.5 rounded-full">New</span>
                </h4>
                <p className="text-sm text-slate-700 dark:text-slate-300">
                  {inv.reason} ({inv.app_name})
                </p>
              </div>
            </div>
            <button
              onClick={() => resolveIntervention(inv.id).then(() => setInterventions(prev => prev.filter(i => i.id !== inv.id)))}
              className="px-4 py-2 bg-danger/20 hover:bg-danger/30 text-danger rounded-lg transition-colors text-sm font-medium"
            >
              Acknowledge
            </button>
          </div>
        </div>
      ))}
      
      {/* Top Row: Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Today's Screen Time"
          value={loading ? '...' : formatDurationSeconds(todayUsage?.total_screen_time_seconds || 0)}
          subtitle={
            <span className="text-danger flex items-center gap-1">
              {usageLabel}{usageConfidence ? ` (${Math.round(usageConfidence * 100)}% conf.)` : ''}
            </span>
          }
          icon={Clock}
          delay={0.1}
        />
        <StatCard
          title="Wellness Score"
          value={
            <span className={wellnessScore < 50 ? 'text-danger' : wellnessScore <= 75 ? 'text-warning' : 'text-success'}>
              {loading ? '...' : `${wellnessScore}/100`}
            </span>
          }
          subtitle={wellnessScore < 50 ? 'Needs Attention' : wellnessScore <= 75 ? 'Moderate' : 'Good'}
          icon={Activity}
          delay={0.2}
        />
        <StatCard
          title="Mental Health Risk"
          value={<RiskBadge risk={mentalRisk} />}
          subtitle={`Score: ${mentalRiskScore}/100`}
          icon={Brain}
          delay={0.3}
        />
        <StatCard
          title="Productivity Score"
          value={loading ? '...' : `${Math.round(prodScore * 100)}%`}
          subtitle={<RiskBadge risk={prodMotivation} />}
          icon={Target}
          delay={0.4}
        />
      </div>

      {/* AI Daily Reflection */}
      {dailyReflection && (
        <div className="border border-indigo-500/20 bg-indigo-500/10 rounded-xl p-5 flex items-start gap-4 animate-in slide-in-from-bottom-4 shadow-sm backdrop-blur-sm">
          <div className="p-2 bg-indigo-500/20 text-indigo-400 rounded-lg shrink-0 mt-1">
            <Sparkles size={24} />
          </div>
          <div className="flex-1">
            <h3 className="text-slate-900 dark:text-white font-bold text-lg mb-1">AI Daily Reflection</h3>
            <p className="text-slate-700 dark:text-slate-300 text-sm mb-3">{dailyReflection.summary}</p>
            <div className="flex items-center gap-4 text-xs font-medium">
              <span className="bg-surface dark:bg-slate-800/80 px-2 py-1 rounded text-slate-700 dark:text-slate-300">Today: {dailyReflection.today_hours}h</span>
              <span className="bg-surface dark:bg-slate-800/80 px-2 py-1 rounded text-slate-700 dark:text-slate-300">Yesterday: {dailyReflection.yesterday_hours}h</span>
              <span className={`px-2 py-1 rounded ${dailyReflection.trend === 'down' ? 'bg-success/20 text-success' : 'bg-danger/20 text-danger'}`}>
                {dailyReflection.trend === 'down' ? '▼' : '▲'} {dailyReflection.difference_hours}h
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Focus Productivity Insights */}
      {focusProdData && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-in slide-in-from-bottom-4" style={{ animationDelay: '0.45s' }}>
          <div className="card lg:col-span-3 bg-gradient-to-r from-success/10 to-transparent border border-success/20">
            <h3 className="text-xl font-bold flex items-center gap-2 text-slate-900 dark:text-white mb-4">
              <Target className="text-success" /> Focus Productivity AI
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <p className="text-sm text-slate-600 dark:text-slate-400">Focus Score</p>
                <p className="text-2xl font-bold text-success">{focusProdData.productivity_score}%</p>
              </div>
              <div>
                <p className="text-sm text-slate-600 dark:text-slate-400">Deep Work</p>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">{focusProdData.deep_work_minutes} min</p>
              </div>
              <div>
                <p className="text-sm text-slate-600 dark:text-slate-400">Distracted</p>
                <p className="text-2xl font-bold text-danger">{focusProdData.distracted_minutes} min</p>
              </div>
              <div>
                <p className="text-sm text-slate-600 dark:text-slate-400">Best Focus Window</p>
                <p className="text-2xl font-bold text-primary">{focusProdData.best_focus_window}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Middle Row: Wellness Score & Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          {wellnessData ? (
            <AddictionRiskCard
              score={wellnessData.score}
              riskLevel={wellnessData.risk_level}
              socialHours={wellnessData.social_hours}
              totalHours={wellnessData.total_hours}
              projectedScore={wellnessData.projected_score_30_days}
              delay={0.5}
            />
          ) : (
            <WellnessScoreCard
              score={wellnessScore}
              label="Your Digital Health Score"
              subtext="Based on ML predictions: usage + mental health + productivity"
              delay={0.5}
            />
          )}
        </div>
        <div className="lg:col-span-2 flex flex-col justify-center gap-4">
          {burnoutData?.is_high_risk && (
            <AlertBanner
              message={`🚨 ${burnoutData.warning} (${burnoutData.burnout_risk_percentage}%). High screen time, low mood, or poor sleep detected.`}
              buttonText="Take Action"
              route="/wellness"
              delay={0.5}
              variant="danger"
            />
          )}
          {doomWarning && (
            <AlertBanner
              message={`⚠️ High Doomscroll Risk Detected (${Math.round(doomWarning.risk * 100)}%). AI suggests you ${doomWarning.action.replace('_', ' ')}.`}
              buttonText="Focus Mode"
              route="/focus"
              delay={0.5}
              variant="danger"
            />
          )}
          {wellnessScore < 50 && !doomWarning && (
            <AlertBanner
              message={`You're in the ${usageLabel} usage category. ${persona?.persona ? `Persona: ${persona.persona}.` : ''} Your predicted risk window is 9-11 PM tonight.`}
              buttonText="See Predictions"
              route="/predictions"
              delay={0.6}
            />
          )}
          {interventions.map((inv) => (
            <AlertBanner
              key={inv.id}
              message={`🚨 ${inv.app_name} limit reached! ${inv.reason}`}
              buttonText="Acknowledge"
              route="/tracker"
              delay={0.5}
            />
          ))}
          {anomaly?.is_anomaly && (
            <div className="mt-4">
              <AlertBanner
                message={`Unusual Device Usage Detected: ${anomaly.current_usage_hours} hours. This is outside your normal pattern. Consider taking a deep breath and a short break.`}
                buttonText="Talk to Coach"
                route="/coach"
                delay={0.7}
                variant="warning"
              />
            </div>
          )}
        </div>
      </div>

      {/* Hourly Usage Chart */}
      <HourlyBarChart data={[]} delay={0.7} />

      {/* Bottom Row: App Breakdown & Weekly Trend */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <AppDonutChart data={[]} delay={0.8} />
        <WeeklyLineChart data={weeklyTrendData.length ? weeklyTrendData : mockWeeklyTrend} delay={0.9} />
      </div>
    </div>
  );
}
