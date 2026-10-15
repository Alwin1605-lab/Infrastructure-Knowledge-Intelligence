import React from 'react';
import { useWorkspaces } from '../hooks/useWorkspacesQuery';
import { useDocumentStats } from '../hooks/useDocumentsQuery';
import { useAuth } from '../context/AuthContext';
import { Card, Badge } from '../components/ui';
import { 
  Briefcase, 
  Upload, 
  Bot, 
  BookOpen, 
  FileBarChart,
  Activity,
  CheckCircle2,
  FileText,
  Database
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useRole } from '../hooks/useRole';

export function Dashboard() {
  const { user } = useAuth();
  const { isDeveloper } = useRole();
  const { data: workspaces } = useWorkspaces();
  const { data: docStats } = useDocumentStats();
  const navigate = useNavigate();

  // For Demo purposes we can fall back to mock activities if backend doesn't provide them yet,
  // but we should fetch from an activity API if it exists.
  const activities = [
    { type: 'report', text: 'Inspection Report generated for ABC Apartment', time: '10 mins ago' },
    { type: 'doc', text: 'IS 456 Structural Code indexed', time: '2 hours ago' },
    { type: 'project', text: 'City Hospital Retrofit workspace created', time: '1 day ago' },
  ];
  
  const activeWorkspaces = workspaces?.length || 0;
  const totalDocs = docStats?.total_documents || 0;
  const processedDocs = docStats?.processed_documents || 0;
  const kgNodes = docStats?.total_entities || 0;
  const kgRelationships = docStats?.total_relationships || 0;

  const quickActions = [
    { name: 'Create Workspace', icon: Briefcase, color: 'text-blue-600', bg: 'bg-blue-50', path: '/workspaces' },
    { name: 'Upload Documents', icon: Upload, color: 'text-emerald-600', bg: 'bg-emerald-50', path: '/library' },
    { name: 'Start Analysis', icon: Bot, color: 'text-indigo-600', bg: 'bg-indigo-50', path: '/assistant' },
    { name: 'Generate Report', icon: FileBarChart, color: 'text-amber-600', bg: 'bg-amber-50', path: '/reports' },
    { name: 'Browse Standards', icon: BookOpen, color: 'text-slate-600', bg: 'bg-slate-100', path: '/standards' },
  ];

  const recentActivity = [
    { type: 'report', text: 'Inspection Report generated for ABC Apartment', time: '10 mins ago', icon: FileBarChart, color: 'text-amber-600' },
    { type: 'doc', text: 'IS 456 Structural Code indexed', time: '2 hours ago', icon: CheckCircle2, color: 'text-emerald-600' },
    { type: 'analysis', text: 'Maintenance recommendation completed for HVAC', time: '4 hours ago', icon: Bot, color: 'text-blue-600' },
    { type: 'project', text: 'City Hospital Retrofit workspace created', time: '1 day ago', icon: Briefcase, color: 'text-slate-600' },
  ];

  return (
    <div className="p-8 max-w-7xl mx-auto w-full space-y-8">
      {/* Header */}
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Welcome back, {user?.full_name?.split(' ')[0] || 'Engineer'}</h1>
          <p className="text-slate-500 mt-1 text-lg">Here is what's happening across your active projects today.</p>
        </div>
        <div className="flex gap-4">
          <Card className="px-5 py-3 border-slate-200 flex flex-col items-center justify-center">
            <span className="text-2xl font-bold text-blue-600 leading-none">{activeWorkspaces}</span>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide mt-1">Active Projects</span>
          </Card>
          <Card className="px-5 py-3 border-slate-200 flex flex-col items-center justify-center">
            <span className="text-2xl font-bold text-emerald-600 leading-none">12</span>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide mt-1">Reports Ready</span>
          </Card>
        </div>
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2">
          Quick Actions
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {quickActions.map((action, i) => (
            <button 
              key={i} 
              onClick={() => navigate(action.path)}
              className="flex flex-col items-center justify-center gap-3 p-6 bg-white border border-slate-200 rounded-2xl shadow-sm hover:shadow-md hover:-translate-y-0.5 hover:border-slate-300 transition-all duration-200"
            >
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${action.bg} ${action.color}`}>
                <action.icon className="w-6 h-6" />
              </div>
              <span className="font-semibold text-slate-700 text-sm text-center leading-tight">
                {action.name}
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Recent Activity Timeline */}
        <div className="lg:col-span-2 space-y-8">
          
          {/* Live System Stats */}
          <div>
            <h2 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2">
              <Database className="w-5 h-5 text-slate-400" />
              Knowledge Base Stats
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card className="p-4 border-slate-200">
                <p className="text-slate-500 text-xs font-semibold uppercase tracking-wider mb-1">Total Docs</p>
                <p className="text-2xl font-bold text-slate-900">{totalDocs}</p>
              </Card>
              <Card className="p-4 border-slate-200">
                <p className="text-slate-500 text-xs font-semibold uppercase tracking-wider mb-1">Processed</p>
                <p className="text-2xl font-bold text-emerald-600">{processedDocs}</p>
              </Card>
              <Card className="p-4 border-slate-200">
                <p className="text-slate-500 text-xs font-semibold uppercase tracking-wider mb-1">KG Entities</p>
                <p className="text-2xl font-bold text-indigo-600">{kgNodes}</p>
              </Card>
              <Card className="p-4 border-slate-200">
                <p className="text-slate-500 text-xs font-semibold uppercase tracking-wider mb-1">KG Edges</p>
                <p className="text-2xl font-bold text-purple-600">{kgRelationships}</p>
              </Card>
            </div>
          </div>

          <div>
            <h2 className="text-lg font-bold text-slate-900 mb-4 flex items-center gap-2">
              <Activity className="w-5 h-5 text-slate-400" />
              Recent Activity
            </h2>
            <Card className="p-6">
              {activities.length === 0 ? (
                <div className="text-center text-slate-500 py-4">No recent activity found.</div>
              ) : (
                <div className="space-y-6">
                  {activities.map((activity, i) => {
                    let Icon = CheckCircle2;
                    let color = "text-slate-400";
                    if (activity.type === 'report') { Icon = FileBarChart; color = "text-amber-600"; }
                    else if (activity.type === 'project') { Icon = Briefcase; color = "text-blue-600"; }
                    else if (activity.type === 'doc') { Icon = FileText; color = "text-emerald-600"; }
                    
                    return (
                      <div key={i} className="flex gap-4">
                        <div className="mt-1 relative flex flex-col items-center">
                          <div className="w-2 h-2 rounded-full bg-slate-300 z-10"></div>
                          {i !== activities.length - 1 && (
                            <div className="absolute top-2 bottom-[-24px] w-0.5 bg-slate-100"></div>
                          )}
                        </div>
                        <div className="flex-1 pb-1">
                          <p className="text-slate-800 font-medium text-sm leading-snug flex items-center gap-2">
                            <Icon className={`w-4 h-4 ${color}`} />
                            {activity.text}
                          </p>
                          <p className="text-slate-500 text-xs mt-1">
                            {activity.time}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </Card>
          </div>
        </div>

        {/* System Notifications */}
        <div>
          <h2 className="text-lg font-bold text-slate-900 mb-4">System Notifications</h2>
          <div className="space-y-3">
            <Card hover className="p-4 border-l-4 border-l-blue-500">
              <h4 className="font-semibold text-sm text-slate-900 mb-1">Knowledge Base Updated</h4>
              <p className="text-xs text-slate-600">The latest structural codes have been indexed and are ready for analysis.</p>
            </Card>
            <Card hover className="p-4 border-l-4 border-l-emerald-500">
              <h4 className="font-semibold text-sm text-slate-900 mb-1">Processing Completed</h4>
              <p className="text-xs text-slate-600">3 new architectural blueprints were successfully processed.</p>
            </Card>
            <Card hover className="p-4 border-l-4 border-l-amber-500">
              <h4 className="font-semibold text-sm text-slate-900 mb-1">Report Ready</h4>
              <p className="text-xs text-slate-600">Maintenance schedule Q3 for ABC Apartment is ready for download.</p>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
