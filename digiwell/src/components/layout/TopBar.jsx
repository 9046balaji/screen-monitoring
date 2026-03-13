import { useLocation } from 'react-router-dom';
import { currentUser } from '../../data/mockData';

export default function TopBar() {
  const location = useLocation();
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
        <h2 className="text-2xl font-bold text-white">{getPageTitle()}</h2>
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
