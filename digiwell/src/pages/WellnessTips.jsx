import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Moon, Target, Brain, CheckCircle2 } from 'lucide-react';
import Timer2020 from '../components/ui/Timer2020';
import toast from 'react-hot-toast';
import { currentUser, mentalHealthScores as mockMental, productivityData as mockProductivity } from '../data/mockData';
import { getUserCluster, getRecommendations, getMentalHealthRisk, predictProductivity } from '../api/digiwell';

export default function WellnessTips() {
  const [streak, setStreak] = useState(() => {
    return parseInt(localStorage.getItem('digiwell_streak') || '0', 10);
  });
  const [challengeAccepted, setChallengeAccepted] = useState(() => {
    const today = new Date().toDateString();
    return localStorage.getItem('digiwell_challenge_date') === today;
  });

  const [sleepTips, setSleepTips] = useState([
    "No screens 1hr before bed",
    "Enable Night mode after 8 PM",
    "Keep phone outside bedroom",
  ]);
  const [productivityTips, setProductivityTips] = useState([
    "Use the Pomodoro technique (25m work, 5m break)",
    "Enable app blockers during study sessions",
    "Set specific goals for each session",
  ]);
  const [mentalTips, setMentalTips] = useState([
    "Schedule 1 social-media-free day/week",
    "Try mindfulness or meditation apps",
    "Unfollow accounts that cause stress",
  ]);
  const [personaInsight, setPersonaInsight] = useState(null);
  const [mentalRisk, setMentalRisk] = useState(null);
  const [prodScore, setProdScore] = useState(null);

  useEffect(() => {
    async function fetchPersonalizedTips() {
      try {
        const [segRes, mentalRes, prodRes] = await Promise.allSettled([
          getUserCluster({
            time_spent: 6.3,
            age: currentUser.age,
            income: currentUser.income,
            platform_risk_score: 3,
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
            motivation_encoded: 0,
            internet_access_encoded: 1,
            family_income_encoded: 1,
            teacher_quality_encoded: 1,
            school_type_encoded: 0,
            peer_influence_encoded: 1,
            learning_disabilities_encoded: 0,
            parental_education_encoded: 1,
            distance_encoded: 1,
            gender_encoded: 0,
          }),
        ]);

        if (mentalRes.status === 'fulfilled') {
          setMentalRisk(mentalRes.value);
        }

        if (prodRes.status === 'fulfilled') {
          setProdScore(prodRes.value);
        }

        if (segRes.status === 'fulfilled' && segRes.value?.persona) {
          setPersonaInsight(segRes.value);
          const recsRes = await getRecommendations(segRes.value.persona, segRes.value.risk);
          if (recsRes?.recommendations) {
            const recs = recsRes.recommendations;
            // Distribute tips into categories based on keywords
            const sleep = recs.filter(r => /sleep|night|bed|grayscale|blue light|charge|DND|Do Not Disturb/i.test(r));
            const mental = recs.filter(r => /social|detox|unfollow|notification|delete|free day/i.test(r));
            const prod = recs.filter(r => /limit|screen|pomodoro|block|study|focus|goal|weekend|activity|cap/i.test(r));

            if (sleep.length > 0) setSleepTips(sleep);
            if (mental.length > 0) setMentalTips(mental);
            if (prod.length > 0) setProductivityTips(prod);

            // If categorization didn't distribute well, spread evenly
            if (sleep.length === 0 && mental.length === 0 && prod.length === 0 && recs.length >= 3) {
              setSleepTips([recs[0]]);
              setProductivityTips([recs[1]]);
              setMentalTips(recs.slice(2));
            }
          }
        }
      } catch (err) {
        console.error('Failed to fetch personalized tips:', err);
      }
    }
    fetchPersonalizedTips();
  }, []);

  const handleAccept = () => {
    const newStreak = streak + 1;
    setChallengeAccepted(true);
    setStreak(newStreak);
    localStorage.setItem('digiwell_streak', newStreak.toString());
    localStorage.setItem('digiwell_challenge_date', new Date().toDateString());
    toast.success(`Day ${newStreak} streak! Keep it up!`);
  };

  const handleSkip = () => {
    setStreak(0);
    localStorage.setItem('digiwell_streak', '0');
    localStorage.removeItem('digiwell_challenge_date');
    toast('Streak reset. Try again tomorrow!', { icon: '\uD83D\uDC4B' });
  };

  const mentalRiskLabel = mentalRisk?.prediction || mockMental.overallRisk;
  const mentalRiskScore = mentalRisk?.risk_score || mockMental.riskScore;
  const predictedExam = prodScore?.predicted_exam_score || mockProductivity.examScore;

  return (
    <div className="flex flex-col gap-8">
      {/* Persona insight banner */}
      {personaInsight && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-2xl border border-primary/50 bg-primary/10 p-4 flex items-center gap-3"
        >
          <Brain className="w-6 h-6 text-primary shrink-0" />
          <p className="text-white font-medium text-sm">
            Your persona: <strong>{personaInsight.persona}</strong> — {personaInsight.description} Tips personalized by ML model.
          </p>
        </motion.div>
      )}

      {/* Timer Section */}
      <Timer2020 />

      {/* Tips Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Sleep Hygiene */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="rounded-2xl border border-slate-700 bg-surface p-6 shadow-lg flex flex-col gap-4"
        >
          <div className="flex items-center gap-3 text-primary">
            <Moon className="w-6 h-6" />
            <h3 className="text-lg font-semibold text-white">Sleep Hygiene</h3>
          </div>
          <div className="p-3 bg-base rounded-lg border border-slate-700">
            <p className="text-sm text-muted italic">"Your data shows usage until 2 AM on 5 of last 7 days"</p>
          </div>
          <ul className="space-y-2 text-sm text-white">
            {sleepTips.map((tip, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="text-primary mt-0.5">-</span>
                {tip}
              </li>
            ))}
          </ul>
        </motion.div>

        {/* Productivity Boost */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="rounded-2xl border border-slate-700 bg-surface p-6 shadow-lg flex flex-col gap-4"
        >
          <div className="flex items-center gap-3 text-warning">
            <Target className="w-6 h-6" />
            <h3 className="text-lg font-semibold text-white">Productivity Boost</h3>
          </div>
          <div className="p-3 bg-base rounded-lg border border-slate-700">
            <p className="text-sm text-muted italic">
              "Predicted exam score: {predictedExam}% — {predictedExam < 65 ? 'needs improvement' : 'on track'}"
            </p>
          </div>
          <ul className="space-y-2 text-sm text-white">
            {productivityTips.map((tip, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="text-warning mt-0.5">-</span>
                {tip}
              </li>
            ))}
          </ul>
        </motion.div>

        {/* Mental Wellness */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="rounded-2xl border border-slate-700 bg-surface p-6 shadow-lg flex flex-col gap-4"
        >
          <div className="flex items-center gap-3 text-danger">
            <Brain className="w-6 h-6" />
            <h3 className="text-lg font-semibold text-white">Mental Wellness</h3>
          </div>
          <div className="p-3 bg-base rounded-lg border border-slate-700">
            <p className="text-sm text-muted italic">
              "Mental health risk: {mentalRiskLabel} (score: {mentalRiskScore}/100)"
            </p>
          </div>
          <ul className="space-y-2 text-sm text-white">
            {mentalTips.map((tip, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="text-danger mt-0.5">-</span>
                {tip}
              </li>
            ))}
          </ul>
        </motion.div>
      </div>

      {/* Daily Challenge */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="rounded-2xl border border-primary/30 bg-primary/5 p-6 shadow-lg flex flex-col md:flex-row items-center justify-between gap-6"
      >
        <div className="flex flex-col gap-2">
          <h3 className="text-xl font-bold text-white">Today's Challenge: No Instagram before noon</h3>
          <p className="text-muted text-sm flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-success" />
            Current streak: {streak} days
          </p>
        </div>

        {!challengeAccepted ? (
          <div className="flex gap-3 w-full md:w-auto">
            <button
              onClick={handleSkip}
              className="flex-1 md:flex-none px-6 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-xl font-medium transition-colors"
            >
              Skip
            </button>
            <button
              onClick={handleAccept}
              className="flex-1 md:flex-none px-6 py-2 bg-primary hover:bg-primary/90 text-white rounded-xl font-medium transition-colors"
            >
              Accept
            </button>
          </div>
        ) : (
          <div className="px-6 py-2 bg-success/20 text-success border border-success/30 rounded-xl font-medium">
            Challenge Accepted!
          </div>
        )}
      </motion.div>
    </div>
  );
}
