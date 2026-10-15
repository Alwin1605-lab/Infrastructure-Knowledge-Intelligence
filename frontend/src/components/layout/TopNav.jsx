import React from 'react';
import { Search, Bell, User } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export function TopNav() {
  const { user } = useAuth();

  return (
    <div className="h-16 border-b border-slate-200 bg-white flex items-center justify-between px-6 sticky top-0 z-10 shrink-0">
      <div className="flex-1 max-w-xl flex items-center relative">
        <Search className="w-4 h-4 text-slate-400 absolute left-3" />
        <input 
          type="text" 
          placeholder="Search across your workspaces (Ctrl+K)..." 
          className="w-full bg-slate-50 border border-slate-200 text-slate-700 text-sm rounded-lg pl-10 pr-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
          onClick={() => {
            const event = new KeyboardEvent('keydown', { key: 'k', ctrlKey: true });
            window.dispatchEvent(event);
          }}
          readOnly
        />
      </div>

      <div className="flex items-center gap-4">
        <button className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-full transition-colors relative">
          <Bell size={20} />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-blue-500 rounded-full border-2 border-white"></span>
        </button>
        <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-sm">
          {user?.full_name?.charAt(0).toUpperCase() || <User size={16} />}
        </div>
      </div>
    </div>
  );
}
