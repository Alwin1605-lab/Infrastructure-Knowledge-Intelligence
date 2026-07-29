import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { workspacesApi } from '../api/workspaces';
import { Building2, MapPin, Calendar, Upload, FileText, ArrowLeft, Loader2, Trash2 } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

export function WorkspaceDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [workspace, setWorkspace] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [file, setFile] = useState(null);

  useEffect(() => {
    fetchWorkspace();
  }, [id]);

  const fetchWorkspace = async () => {
    try {
      const { data } = await workspacesApi.get(id);
      setWorkspace(data);
    } catch (err) {
      console.error(err);
      navigate('/workspaces');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm("Are you sure you want to delete this workspace? All data will be lost.")) return;
    try {
      await workspacesApi.delete(id);
      navigate('/workspaces');
    } catch (err) {
      alert("Failed to delete workspace.");
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    try {
      await workspacesApi.uploadDocument(id, file);
      alert("Document uploaded successfully");
      setFile(null);
      // Ideally we would fetch documents here
    } catch (err) {
      alert("Failed to upload document");
    } finally {
      setUploading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center bg-slate-50">
        <Loader2 size={32} className="animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto bg-slate-50">
      <div className="max-w-6xl mx-auto p-8">
        
        {/* Header */}
        <div className="mb-8">
          <button 
            onClick={() => navigate('/workspaces')}
            className="flex items-center text-sm text-slate-500 hover:text-slate-900 mb-6 transition-colors"
          >
            <ArrowLeft size={16} className="mr-1" /> Back to Workspaces
          </button>
          
          <div className="flex justify-between items-start">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center shrink-0">
                <Building2 size={32} />
              </div>
              <div>
                <h1 className="text-3xl font-light text-slate-900 tracking-tight mb-1">{workspace?.name}</h1>
                <div className="flex items-center gap-4 text-sm text-slate-500">
                  <span className="flex items-center gap-1.5"><MapPin size={14}/> {workspace?.location || 'No location'}</span>
                  <span className="flex items-center gap-1.5"><Building2 size={14}/> {workspace?.building_type}</span>
                  <span className="flex items-center gap-1.5"><Calendar size={14}/> Updated {workspace ? formatDistanceToNow(new Date(workspace.updated_at)) : ''} ago</span>
                </div>
              </div>
            </div>
            
            <button 
              onClick={handleDelete}
              className="p-2 text-red-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
              title="Delete Workspace"
            >
              <Trash2 size={20} />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="grid grid-cols-3 gap-6">
          <div className="col-span-2 space-y-6">
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
              <h2 className="text-lg font-bold text-slate-900 mb-4">Workspace Details</h2>
              <p className="text-slate-600 text-sm leading-relaxed whitespace-pre-wrap">
                {workspace?.description || 'No description provided.'}
              </p>
            </div>
            
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-lg font-bold text-slate-900">Workspace Documents</h2>
              </div>
              
              <div className="bg-slate-50 border border-dashed border-slate-300 rounded-xl p-8 text-center">
                <FileText size={32} className="mx-auto text-slate-400 mb-4" />
                <h3 className="text-sm font-medium text-slate-900 mb-1">No documents yet</h3>
                <p className="text-xs text-slate-500 mb-6">Upload PDFs to start analyzing them.</p>
                
                <form onSubmit={handleUpload} className="max-w-xs mx-auto space-y-4">
                  <input 
                    type="file" 
                    accept=".pdf"
                    onChange={(e) => setFile(e.target.files[0])}
                    className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 cursor-pointer"
                  />
                  <button 
                    type="submit"
                    disabled={!file || uploading}
                    className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-xl font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    {uploading ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
                    Upload Document
                  </button>
                </form>
              </div>
            </div>
          </div>
          
          <div className="col-span-1 space-y-6">
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
              <h2 className="text-lg font-bold text-slate-900 mb-4">Activity Feed</h2>
              <div className="text-sm text-slate-500 italic text-center py-8">
                Activity log will appear here
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
