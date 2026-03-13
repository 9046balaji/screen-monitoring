import { NavLink, useLocation } from 'react-router-dom';
import { currentUser } from '../../data/mockData';

export default function TopBar() {
  const location = useLocation();
  const isProfile = location.pathname === '/profile';
  const isReports = location.pathname === '/reports';

  const isWellness = ['/wellness', '/journal', '/therapy'].includes(location.pathname);
  const isAnalyticsGroup = ['/analytics', '/predictions'].includes(location.pathname);

  const getPageTitle = () => {
    switch (location.pathname) {
      case '/dashboard': return 'Dashboard';
      case '/analytics': return 'Analytics';
      case '/predictions': return 'Predictions';
      case '/profile': return 'Profile';
      case '/wellness': return 'Wellness';
      case '/journal': return 'Mood Journal';
      case '/therapy': return 'CBT Therapy';
      case '/detox': return '7-Day Detox';
      case '/coach': return 'AI Coach';
      case '/tracker': return 'App Tracker';
      case '/focus': return 'Focus Mode';
      default: return 'DigiWell';
    }
  };

  const navLinkClass = (isActive) => 
    `px-6 py-3 rounded-lg border text-base font-semibold transition-colors ${
      isActive
        ? 'border-primary bg-primary/20 text-white'
        : 'border-slate-700 bg-surface text-white hover:border-primary hover:text-primary'
    }`;

  const dateStr = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });

  return (
    <header className="h-20 flex items-center justify-between px-8 bg-base/80 backdrop-blur-md sticky top-0 z-10 border-b border-slate-800">
      <div>
        <div className="flex items-center gap-3">
          {(isProfile || isReports) ? (
            <>
              <NavLink to="/profile" className={({ isActive }) => navLinkClass(isActive)}>Profile</NavLink>
              <NavLink to="/reports" className={({ isActive }) => navLinkClass(isActive)}>Reports</NavLink>
            </>
          ) : isWellness ? (
            <>
              <NavLink to="/wellness" className={({ isActive }) => navLinkClass(isActive)}>Wellness Tips</NavLink>
              <NavLink to="/journal" className={({ isActive }) => navLinkClass(isActive)}>Mood Journal</NavLink>
              <NavLink to="/therapy" className={({ isActive }) => navLinkClass(isActive)}>CBT Therapy</NavLink>
            </>
          ) : isAnalyticsGroup ? (
            <>
              <NavLink to="/analytics" className={({ isActive }) => navLinkClass(isActive)}>Analytics</NavLink>
              <NavLink to="/predictions" className={({ isActive }) => navLinkClass(isActive)}>Predictions</NavLink>
            </>
          ) : (
            <h2 className="text-2xl font-bold text-white">{getPageTitle()}</h2>
          )}
        </div>
        <p className="text-muted text-sm">{dateStr}</p>
      </div>
      <div className="flex items-center gap-4">
        <div className="text-right">
          <p className="text-sm font-semibold text-white">{currentUser.name}</p>
          <p className="text-xs text-muted">{currentUser.cluster}</p>
        </div>
        <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center text-white font-bold">
          {currentUser.name.split(' ').map(n => n[0]).join('')}
        </div>
      </div>
    </header>
  );
}
