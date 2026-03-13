import { NavLink } from 'react-router-dom';
import { LayoutDashboard, BarChart2, TrendingUp, User, Heart, Monitor, Target, Bot, BookOpen, Trophy, Brain } from 'lucide-react';

export default function Sidebar() {
  const navItems = [
    { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    { name: 'Analytics', path: '/analytics', icon: BarChart2 },
    { name: '7-Day Detox', path: '/detox', icon: Trophy },
    { name: 'AI Coach', path: '/coach', icon: Bot },
    { name: 'Profile', path: '/profile', icon: User },
    { name: 'Wellness Center', path: '/wellness', icon: Heart },
    { name: 'App Tracker', path: '/tracker', icon: Monitor },
    { name: 'Focus Mode', path: '/focus', icon: Target },
  ];

  return (
    <div className="fixed left-0 top-0 h-full w-60 bg-base border-r border-slate-200 dark:border-slate-800 flex flex-col">
      <div className="p-6">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
          🧠 DigiWell
        </h1>
      </div>
      <nav className="flex-1 px-4 space-y-2">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-xl transition-colors ${
                isActive
                  ? 'bg-primary text-white font-semibold'
                  : 'text-muted hover:bg-slate-200 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-white'
              }`
            }
          >
            <item.icon className="w-5 h-5" />
            {item.name}
          </NavLink>
        ))}
      </nav>
      <div className="p-4">
        <div className="bg-surface border border-slate-300 dark:border-slate-700 rounded-2xl p-4 flex items-center gap-3">
          <div className="w-12 h-12 rounded-full border-4 border-danger flex items-center justify-center text-danger font-bold text-sm">
            42
          </div>
          <div className="text-sm">
            <p className="font-semibold text-slate-900 dark:text-white">Score: 42</p>
            <p className="text-danger text-xs">Needs Attention</p>
          </div>
        </div>
      </div>
    </div>
  );
}
