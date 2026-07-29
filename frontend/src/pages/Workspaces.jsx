import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { workspacesApi } from '../api/workspaces';
import { Briefcase, Plus, Search, Building2, MapPin, Calendar, Clock, ArrowRight, Loader2, Info } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

export function Workspaces() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [workspaces, setWorkspaces] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newWorkspace, setNewWorkspace] = useState({
    name: '',
    building_type: 'Commercial',
    location: '',
    description: ''
  });
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    fetchWorkspaces();
  }, []);

  const fetchWorkspaces = async () => {
    try {
      const { data } = await workspacesApi.list();
      setWorkspaces(data.workspaces || []);
    } catch (err) {
      setError('Failed to load workspaces.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setCreating(true);
    try {
      await workspacesApi.create(newWorkspace);
      setIsModalOpen(false);
      setNewWorkspace({ name: '', building_type: 'Commercial', location: '', description: '' });
      await fetchWorkspaces();
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.detail || 'Failed to create workspace');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto bg-slate-50 relative">
      <div className="max-w-7xl mx-auto p-8">
        
        {/* Header */}
        <div className="flex justify-between items-end mb-8">
          <div>
            <h1 className="text-3xl font-light text-slate-900 tracking-tight mb-2">Workspaces</h1>
            <p className="text-slate-500 font-medium">Manage building engineering projects across {user?.organization}</p>
          </div>
          
          <button 
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl font-medium transition-all shadow-sm hover:shadow active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={user?.is_guest}
            title={user?.is_guest ? "Guest users cannot create workspaces" : ""}
          >
            <Plus size={18} />
            New Workspace
          </button>
        </div>

        {error && (
          <div className="bg-red-50 text-red-600 p-4 rounded-xl mb-6 text-sm flex items-center gap-3 border border-red-100">
            <Info size={18} />
            <span>{error}</span>
          </div>
        )}

        {/* Content */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 size={32} className="animate-spin text-blue-600" />
          </div>
        ) : workspaces.length === 0 ? (
          <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center shadow-sm max-w-2xl mx-auto mt-12">
            <div className="w-16 h-16 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center mx-auto mb-4">
              <Briefcase size={32} />
            </div>
            <h3 className="text-xl font-medium text-slate-900 mb-2">No workspaces yet</h3>
            <p className="text-slate-500 max-w-sm mx-auto mb-6">
              Create your first workspace to start uploading documents, generating reports, and running diagnostics for a specific building project.
            </p>
            <button 
              onClick={() => setIsModalOpen(true)}
              className="bg-slate-900 text-white px-6 py-2.5 rounded-xl font-medium hover:bg-slate-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={user?.is_guest}
            >
              Create Workspace
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {workspaces.map(workspace => (
              <div 
                key={workspace.id}
                onClick={() => navigate(`/workspaces/${workspace.id}`)}
                className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm hover:shadow-md hover:border-blue-200 transition-all cursor-pointer group flex flex-col"
              >
                <div className="flex justify-between items-start mb-4">
                  <div className="w-12 h-12 bg-blue-50 text-blue-600 rounded-xl flex items-center justify-center shrink-0">
                    <Building2 size={24} />
                  </div>
                  <span className={`text-xs font-semibold px-2.5 py-1 rounded-full uppercase tracking-wider ${
                    workspace.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-600'
                  }`}>
                    {workspace.status}
                  </span>
                </div>
                
                <h3 className="text-lg font-bold text-slate-900 mb-1 line-clamp-1 group-hover:text-blue-600 transition-colors">{workspace.name}</h3>
                <p className="text-sm text-slate-500 mb-6 line-clamp-2 min-h-[40px]">
                  {workspace.description || 'No description provided.'}
                </p>
                
                <div className="mt-auto space-y-2 mb-6">
                  <div className="flex items-center gap-2 text-sm text-slate-600">
                    <MapPin size={16} className="text-slate-400" />
                    <span className="truncate">{workspace.location || 'Unknown location'}</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-slate-600">
                    <Building2 size={16} className="text-slate-400" />
                    <span>{workspace.building_type}</span>
                  </div>
                </div>
                
                <div className="pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
                  <div className="flex items-center gap-1.5">
                    <Clock size={14} />
                    Updated {formatDistanceToNow(new Date(workspace.updated_at))} ago
                  </div>
                  <div className="w-6 h-6 rounded-full bg-slate-100 flex items-center justify-center group-hover:bg-blue-600 group-hover:text-white transition-colors">
                    <ArrowRight size={14} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl w-full max-w-lg shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
              <h2 className="text-lg font-bold text-slate-900">Create New Workspace</h2>
              <button 
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-slate-700 text-2xl leading-none px-2"
              >
                &times;
              </button>
            </div>
            
            <form onSubmit={handleCreate} className="p-6">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Project Name <span className="text-red-500">*</span></label>
                  <input
                    type="text"
                    required
                    value={newWorkspace.name}
                    onChange={e => setNewWorkspace({...newWorkspace, name: e.target.value})}
                    className="w-full h-10 px-3 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-sm"
                    placeholder="e.g. Downtown Office Complex Assessment"
                  />
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Building Type</label>
                    <select
                      value={newWorkspace.building_type}
                      onChange={e => setNewWorkspace({...newWorkspace, building_type: e.target.value})}
                      className="w-full h-10 px-3 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-sm bg-white"
                    >
                      <option value="Commercial">Commercial</option>
                      <option value="Residential">Residential</option>
                      <option value="Industrial">Industrial</option>
                      <option value="Institutional">Institutional</option>
                      <option value="Government">Government</option>
                      <option value="Unspecified">Unspecified</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Location</label>
                    <input
                      type="text"
                      value={newWorkspace.location}
                      onChange={e => setNewWorkspace({...newWorkspace, location: e.target.value})}
                      className="w-full h-10 px-3 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-sm"
                      placeholder="City, Country"
                    />
                  </div>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
                  <textarea
                    rows={3}
                    value={newWorkspace.description}
                    onChange={e => setNewWorkspace({...newWorkspace, description: e.target.value})}
                    className="w-full p-3 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-sm resize-none"
                    placeholder="Brief overview of the building condition assessment goals..."
                  />
                </div>
              </div>
              
              <div className="mt-8 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-50 border border-slate-200 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors flex items-center shadow-sm disabled:opacity-70"
                >
                  {creating && <Loader2 size={16} className="animate-spin mr-2" />}
                  Create Workspace
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
