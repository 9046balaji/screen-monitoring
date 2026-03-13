import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import Sidebar from './components/layout/Sidebar';
import TopBar from './components/layout/TopBar';
import Dashboard from './pages/Dashboard';
import Analytics from './pages/Analytics';
import Predictions from './pages/Predictions';
import Profile from './pages/Profile';
import WellnessTips from './pages/WellnessTips';
import AppTracker from './pages/AppTracker';
import FocusMode from './pages/FocusMode';
import Reports from './pages/Reports';
import Coach from './pages/Coach';
import MoodJournal from './pages/MoodJournal';
import DetoxChallenge from './pages/DetoxChallenge.jsx';
import Therapy from './pages/Therapy.jsx';
import InterventionPopup from './components/ui/InterventionPopup.jsx';
import use2020Timer from './hooks/use2020Timer.js'; // Feature 4 hook
import useDopamineDetector from './hooks/useDopamineDetector'; // Feature 1 hook

function AppContent() {
  // Activate global 20-20-20 rule timer
  use2020Timer();
  useDopamineDetector();

  return (
    <div className="flex min-h-screen bg-base text-slate-900 dark:text-white">
      <Sidebar />
      <div className="flex-1 ml-60 flex flex-col">
        <TopBar />
        <main className="flex-1 p-8 overflow-y-auto">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/predictions" element={<Predictions />} />
            <Route path="/profile" element={<Profile />} />
            <Route path="/wellness" element={<WellnessTips />} />
            <Route path="/tracker" element={<AppTracker />} />
            <Route path="/focus" element={<FocusMode />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/coach" element={<Coach />} />
            <Route path="/journal" element={<MoodJournal />} />
            <Route path="/detox" element={<DetoxChallenge />} />
            <Route path="/therapy" element={<Therapy />} />
          </Routes>
        </main>
      </div>
      <InterventionPopup />
    </div>
  );
}

export default function App() {
  return (
    <Router>
      <AppContent />
      <Toaster position="top-right" toastOptions={{
        className: 'bg-surface text-slate-900 dark:bg-slate-800 dark:text-white border border-slate-200 dark:border-slate-700'
      }} />
    </Router>
  );
}

