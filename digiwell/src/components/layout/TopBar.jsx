import { NavLink, useLocation } from 'react-router-dom';
import { currentUser } from '../../data/mockData';

export default function TopBar() {
  const location = useLocation();
  const isProfile = location.pathname === '/profile';
  const isReports = location.pathname === '/reports';
  const getPageTitle = () => {
    switch (location.pathname) {
      case '/dashboard': return 'Dashboard';
      case '/analytics': return 'Analytics';
      case '/predictions': return 'Predictions';
      case '/profile': return 'Profile';
      case '/wellness': return 'Wellness Tips';
      default: return 'DigiWell';
    }
  };

  const dateStr = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });

  return (
    <header className="h-20 flex items-center justify-between px-8 bg-base/80 backdrop-blur-md sticky top-0 z-10 border-b border-slate-800">
      <div>
        <div className="flex items-center gap-3">
          {(isProfile || isReports) ? (
            <>
              <NavLink
                to="/profile"
                className={`px-4 py-2 rounded-lg border text-sm font-semibold transition-colors ${
                  isProfile
                    ? 'border-primary bg-primary/20 text-white'
                    : 'border-slate-700 bg-surface text-white hover:border-primary hover:text-primary'
                }`}
              >
                Profile
              </NavLink>
              <NavLink
                to="/reports"
                className={`px-4 py-2 rounded-lg border text-sm font-semibold transition-colors ${
                  isReports
                    ? 'border-primary bg-primary/20 text-white'
                    : 'border-slate-700 bg-surface text-white hover:border-primary hover:text-primary'
                }`}
              >
                Reports
              </NavLink>
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
