import React from 'react';
import { NavLink, Link } from 'react-router-dom';
import { 
  Home, 
  Briefcase, 
  Files, 
  Bot, 
  FileBarChart, 
  BookOpen, 
  Settings,
  TerminalSquare
} from 'lucide-react';
import { cn } from '../ui';

const MAIN_NAV = [
  { name: 'Home', path: '/', icon: Home },
  { name: 'Workspaces', path: '/workspaces', icon: Briefcase },
  { name: 'Documents', path: '/docs', icon: Files },
  { name: 'Engineering Assistant', path: '/assistant', icon: Bot },
  { name: 'Reports', path: '/reports', icon: FileBarChart },
  { name: 'Standards & Codes', path: '/standards', icon: BookOpen },
  { name: 'Settings', path: '/settings', icon: Settings },
];

export function Sidebar() {
  return (
    <div className="w-64 h-screen bg-white border-r border-slate-200 flex flex-col shrink-0 shadow-sm z-10">
      <div className="p-6 border-b border-slate-100 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold text-lg">
          B
        </div>
        <div>
          <h1 className="text-sm font-bold text-slate-900 leading-tight">
            Building Knowledge
          </h1>
          <p className="text-xs text-slate-500 font-medium tracking-wide">INTELLIGENCE SYSTEM</p>
        </div>
      </div>
      
      <nav className="flex-1 overflow-y-auto py-6 px-4 space-y-1">
        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3 px-2">
          Engineering Platform
        </div>
        {MAIN_NAV.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 text-sm font-medium group",
                isActive
                  ? "bg-blue-50 text-blue-700 shadow-sm ring-1 ring-blue-600/10"
                  : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
              )
            }
          >
            {({ isActive }) => (
              <>
                <item.icon 
                  className={cn(
                    "w-5 h-5 transition-colors", 
                    isActive ? "text-blue-600" : "text-slate-400 group-hover:text-slate-600"
                  )} 
                />
                {item.name}
              </>
            )}
          </NavLink>
        ))}
      </nav>
      
      <div className="p-4 border-t border-slate-100">
        <NavLink
          to="/dev"
          className={({ isActive }) =>
            cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-xl transition-colors text-sm font-medium text-slate-500 hover:bg-slate-50 hover:text-slate-700",
              isActive && "bg-slate-100 text-slate-800"
            )
          }
        >
          <TerminalSquare className="w-5 h-5 text-slate-400" />
          Developer Mode
        </NavLink>
      </div>
    </div>
  );
}
