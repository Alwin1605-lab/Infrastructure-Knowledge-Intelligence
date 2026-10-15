import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Loader2 } from 'lucide-react';
import { Sidebar } from './layout/Sidebar';
import { TopNav } from './layout/TopNav';
import { CommandPalette } from './CommandPalette';

export const ProtectedRoute = () => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <Loader2 size={48} className="animate-spin text-blue-600" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden text-slate-900 font-sans selection:bg-blue-100 selection:text-blue-900">
      <Sidebar />
      <main className="flex-1 overflow-y-auto relative flex flex-col">
        <TopNav />
        <CommandPalette />
        <Outlet />
      </main>
    </div>
  );
};
