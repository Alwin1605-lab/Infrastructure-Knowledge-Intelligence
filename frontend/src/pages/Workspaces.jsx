import React from 'react';
import { useWorkspaceStore } from '../store/useWorkspaceStore';
import { Card, Badge, CollapsibleSection } from '../components/ui';
import { Briefcase, Clock, FileText, ChevronRight, Settings2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export function Workspaces() {
  const { workspaces, currentWorkspaceId, setCurrentWorkspace } = useWorkspaceStore();
  const navigate = useNavigate();

  const handleOpenWorkspace = (id) => {
    setCurrentWorkspace(id);
    navigate('/assistant');
  };

  return (
    <div className="p-8 max-w-7xl mx-auto w-full">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Workspaces</h1>
          <p className="text-slate-500 mt-1 text-lg">Manage your engineering projects and building inspection contexts.</p>
        </div>
        <button className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl font-medium transition-colors shadow-sm flex items-center gap-2">
          <Briefcase className="w-5 h-5" />
          Create Workspace
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {workspaces.map((workspace) => (
          <Card key={workspace.id} hover className="flex flex-col h-full cursor-pointer" onClick={() => handleOpenWorkspace(workspace.id)}>
            <div className="p-6 flex-1">
              <div className="flex justify-between items-start mb-4">
                <div className="w-12 h-12 bg-blue-50 text-blue-600 rounded-xl flex items-center justify-center border border-blue-100 shrink-0">
                  <Briefcase className="w-6 h-6" />
                </div>
                {workspace.id === currentWorkspaceId && (
                  <Badge variant="primary">Active</Badge>
                )}
                {workspace.id !== currentWorkspaceId && (
                  <Badge variant="default">{workspace.status}</Badge>
                )}
              </div>
              <h3 className="text-xl font-bold text-slate-900 mb-2 leading-tight">{workspace.name}</h3>
              <p className="text-slate-600 text-sm line-clamp-2">{workspace.description}</p>
            </div>
            
            <div className="p-4 bg-slate-50 border-t border-slate-100 flex justify-between items-center text-sm text-slate-500">
              <div className="flex items-center gap-4">
                <span className="flex items-center gap-1.5 font-medium"><FileText className="w-4 h-4 text-slate-400" /> {workspace.documentsCount} Docs</span>
                <span className="flex items-center gap-1.5 font-medium"><Clock className="w-4 h-4 text-slate-400" /> {new Date(workspace.lastAccessed).toLocaleDateString()}</span>
              </div>
              <ChevronRight className="w-5 h-5 text-slate-400" />
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
