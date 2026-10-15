import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import toast from 'react-hot-toast';
import {
  UploadCloud, File, Search, Filter, RefreshCw, Trash2, Eye, 
  Database, BarChart3, GitBranch, Layers, CheckCircle2, XCircle,
  Clock, AlertCircle, Loader2, ChevronDown, X
} from 'lucide-react';
import { formatDistanceToNow, format } from 'date-fns';
import { useAuth } from '../context/AuthContext';
import { documentsApi } from '../api/documents';
import { useDocuments, useDocumentStats, useUploadDocument, useDeleteDocument } from '../hooks/useDocumentsQuery';

const CATEGORIES = [
  'GENERAL', 'IS_CODE', 'NBC', 'CPWD', 'ACI', 'ASTM', 'FEMA',
  'NIST', 'RESEARCH', 'CASE_STUDY', 'INSPECTION', 'REPAIR', 'MAINTENANCE', 'DRAWING', 'OTHER'
];

const STATUS_CONFIG = {
  completed: { label: 'Indexed', color: 'bg-emerald-100 text-emerald-700', Icon: CheckCircle2 },
  failed: { label: 'Failed', color: 'bg-red-100 text-red-700', Icon: XCircle },
  uploading: { label: 'Uploading', color: 'bg-blue-100 text-blue-700', Icon: Loader2 },
  extracting: { label: 'Extracting', color: 'bg-blue-100 text-blue-700', Icon: Loader2 },
  chunking: { label: 'Chunking', color: 'bg-violet-100 text-violet-700', Icon: Loader2 },
  embedding: { label: 'Embedding', color: 'bg-indigo-100 text-indigo-700', Icon: Loader2 },
  indexing_kg: { label: 'KG Indexing', color: 'bg-purple-100 text-purple-700', Icon: Loader2 },
  uploaded: { label: 'Uploaded', color: 'bg-slate-100 text-slate-600', Icon: Clock },
};

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.uploaded;
  const isProcessing = !['completed', 'failed'].includes(status);
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-semibold ${cfg.color}`}>
      <cfg.Icon size={12} className={isProcessing ? 'animate-spin' : ''} />
      {cfg.label}
    </span>
  );
}

function StatCard({ label, value, icon: Icon, color }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 px-5 py-4 flex items-center gap-4">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${color}`}>
        <Icon size={20} />
      </div>
      <div>
        <p className="text-2xl font-bold text-slate-900">{value?.toLocaleString() ?? '—'}</p>
        <p className="text-xs text-slate-500 mt-0.5">{label}</p>
      </div>
    </div>
  );
}

const STEPS = [
  { key: 'upload', label: 'Uploading' },
  { key: 'extract', label: 'Extracting Text' },
  { key: 'chunk', label: 'Chunking' },
  { key: 'embed', label: 'Generating Embeddings' },
  { key: 'kg_index', label: 'Knowledge Graph' },
  { key: 'complete', label: 'Complete' },
];

function ProcessingModal({ jobId, filename, onClose }) {
  const [job, setJob] = useState(null);
  const intervalRef = useRef(null);

  const fetchJob = useCallback(async () => {
    if (!jobId) return;
    try {
      const { data } = await documentsApi.getJob(jobId);
      setJob(data);
      if (['completed', 'failed'].includes(data.status)) {
        clearInterval(intervalRef.current);
        if (data.status === 'completed') {
          toast.success(`'${filename}' indexed successfully!`);
        } else {
          toast.error(`Processing failed: ${data.error_message}`);
        }
      }
    } catch (err) {
      console.error(err);
    }
  }, [jobId, filename]);

  useEffect(() => {
    fetchJob();
    intervalRef.current = setInterval(fetchJob, 2000);
    return () => clearInterval(intervalRef.current);
  }, [fetchJob]);

  const getCurrentStepIndex = () => {
    if (!job) return 0;
    const step = job.current_step?.replace('JobStep.', '');
    const idx = STEPS.findIndex(s => s.key === step);
    return idx >= 0 ? idx : 0;
  };

  const stepIdx = getCurrentStepIndex();
  const progress = job?.status === 'completed' ? 100 : Math.round((stepIdx / (STEPS.length - 1)) * 100);

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl w-full max-w-md shadow-2xl">
        <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center">
          <div>
            <h3 className="font-bold text-slate-900">Processing Document</h3>
            <p className="text-xs text-slate-500 mt-0.5 truncate max-w-xs">{filename}</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition-colors">
            <X size={20} />
          </button>
        </div>

        <div className="p-6">
          {/* Progress bar */}
          <div className="mb-6">
            <div className="flex justify-between text-xs text-slate-500 mb-2">
              <span>{job?.status === 'failed' ? 'Failed' : job?.status === 'completed' ? 'Complete' : 'Processing...'}</span>
              <span>{progress}%</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2">
              <div
                className={`h-2 rounded-full transition-all duration-500 ${
                  job?.status === 'failed' ? 'bg-red-500' : 
                  job?.status === 'completed' ? 'bg-emerald-500' : 'bg-blue-500'
                }`}
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          {/* Steps */}
          <div className="space-y-2 mb-6">
            {STEPS.filter(s => s.key !== 'complete').map((step, i) => {
              const isCompleted = job?.completed_steps?.some(s => s.includes(step.key));
              const isCurrent = i === stepIdx && !['completed', 'failed'].includes(job?.status);
              const isFailed = job?.status === 'failed' && job?.failed_step?.includes(step.key);
              return (
                <div key={step.key} className={`flex items-center gap-3 text-sm py-1 ${
                  isCompleted ? 'text-emerald-600' : isFailed ? 'text-red-500' : isCurrent ? 'text-blue-600 font-medium' : 'text-slate-400'
                }`}>
                  {isCompleted ? <CheckCircle2 size={16} className="text-emerald-500" /> :
                   isFailed ? <XCircle size={16} className="text-red-500" /> :
                   isCurrent ? <Loader2 size={16} className="animate-spin text-blue-500" /> :
                   <div className="w-4 h-4 rounded-full border-2 border-slate-200" />}
                  {step.label}
                </div>
              );
            })}
          </div>

          {/* Metrics */}
          {job && (
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="bg-slate-50 rounded-lg p-3">
                <p className="text-lg font-bold text-slate-900">{job.pages_extracted || 0}</p>
                <p className="text-xs text-slate-500">Pages</p>
              </div>
              <div className="bg-slate-50 rounded-lg p-3">
                <p className="text-lg font-bold text-slate-900">{job.chunks_created || 0}</p>
                <p className="text-xs text-slate-500">Chunks</p>
              </div>
              <div className="bg-slate-50 rounded-lg p-3">
                <p className="text-lg font-bold text-slate-900">{job.kg_nodes_created || 0}</p>
                <p className="text-xs text-slate-500">KG Nodes</p>
              </div>
            </div>
          )}

          {job?.elapsed_seconds > 0 && (
            <p className="text-xs text-slate-400 text-center mt-3">
              Elapsed: {Math.round(job.elapsed_seconds)}s
            </p>
          )}

          {['completed', 'failed'].includes(job?.status) && (
            <button
              onClick={onClose}
              className="mt-4 w-full py-2 bg-slate-900 text-white rounded-lg font-medium hover:bg-slate-800 transition-colors"
            >
              Close
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export function DocumentLibrary() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'Administrator';
  
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [category, setCategory] = useState('GENERAL');
  const [activeJob, setActiveJob] = useState(null); // { jobId, filename }

  const { data: documentsData, isLoading: docsLoading, refetch: refetchDocs } = useDocuments({ limit: 100 });
  const { data: statsData, refetch: refetchStats } = useDocumentStats();
  
  const documents = documentsData?.documents || [];
  const stats = statsData || null;
  const loading = docsLoading;

  const uploadMutation = useUploadDocument();
  const deleteMutation = useDeleteDocument();

  const fetchData = useCallback(() => {
    refetchDocs();
    refetchStats();
  }, [refetchDocs, refetchStats]);

  const onDrop = useCallback(async (acceptedFiles) => {
    if (!isAdmin) {
      toast.error('Only Administrators can upload to the Global Knowledge Base');
      return;
    }
    const file = acceptedFiles[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('category', category);
    formData.append('document_type', 'general');

    uploadMutation.mutate(formData, {
      onSuccess: (data) => {
        setActiveJob({ jobId: data.job_id, filename: file.name });
        toast.success('Upload queued! Processing in background...');
      }
    });
  }, [isAdmin, category, uploadMutation]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    disabled: !isAdmin || uploadMutation.isPending,
  });

  const handleDelete = async (id, name) => {
    if (!window.confirm(`Delete '${name}'? This removes it from the knowledge base permanently.`)) return;
    deleteMutation.mutate(id);
  };

  const filtered = documents.filter(d => {
    const matchesSearch = d.filename.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = !statusFilter || d.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="flex flex-col h-full bg-slate-50">
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-7xl mx-auto p-8">
          {/* Header */}
          <div className="flex justify-between items-end mb-6">
            <div>
              <h1 className="text-3xl font-light text-slate-900 tracking-tight">Knowledge Base</h1>
              <p className="text-slate-500 mt-1">Global engineering document repository</p>
            </div>
            <button
              onClick={fetchData}
              className="flex items-center gap-2 px-4 py-2 text-sm border border-slate-200 bg-white rounded-lg hover:bg-slate-50 transition-colors"
            >
              <RefreshCw size={14} /> Refresh
            </button>
          </div>

          {/* Stats bar */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <StatCard label="Documents" value={stats?.total_documents} icon={File} color="bg-blue-50 text-blue-600" />
            <StatCard label="Chunks Indexed" value={stats?.total_chunks} icon={Layers} color="bg-violet-50 text-violet-600" />
            <StatCard label="KG Entities" value={stats?.total_kg_entities} icon={GitBranch} color="bg-emerald-50 text-emerald-600" />
            <StatCard label="KG Relations" value={stats?.total_kg_relationships} icon={Database} color="bg-amber-50 text-amber-600" />
          </div>

          {/* Upload Zone - Admin only */}
          {isAdmin && (
            <div className="mb-6">
              <div className="flex items-center gap-3 mb-3">
                <label className="text-sm font-medium text-slate-700">Document Category:</label>
                <select
                  value={category}
                  onChange={e => setCategory(e.target.value)}
                  className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                >
                  {CATEGORIES.map(c => <option key={c} value={c}>{c.replace('_', ' ')}</option>)}
                </select>
              </div>
              <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all ${
                  isDragActive ? 'border-blue-400 bg-blue-50' : 'border-slate-300 bg-white hover:border-blue-300 hover:bg-blue-50/30'
                } ${uploadMutation.isPending ? 'opacity-60 cursor-not-allowed' : ''}`}
              >
                <input {...getInputProps()} />
                {uploadMutation.isPending ? (
                  <div className="flex flex-col items-center gap-3">
                    <Loader2 size={36} className="text-blue-500 animate-spin" />
                    <p className="text-blue-600 font-medium">Uploading...</p>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-3">
                    <UploadCloud size={40} className={isDragActive ? 'text-blue-500' : 'text-slate-400'} />
                    <div>
                      <p className="font-semibold text-slate-700">
                        {isDragActive ? 'Drop PDF here' : 'Drag & drop a PDF, or click to browse'}
                      </p>
                      <p className="text-sm text-slate-500 mt-1">PDF only · Max 50MB · Automatically indexed</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Search & Filter */}
          <div className="flex gap-3 mb-4">
            <div className="flex-1 relative">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search documents..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full h-10 pl-9 pr-4 border border-slate-200 rounded-lg bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400"
              />
            </div>
            <select
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value)}
              className="h-10 px-3 border border-slate-200 rounded-lg bg-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            >
              <option value="">All Status</option>
              <option value="completed">Indexed</option>
              <option value="failed">Failed</option>
              <option value="embedding">Processing</option>
            </select>
          </div>

          {/* Documents Table */}
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
            {loading ? (
              <div className="flex items-center justify-center py-16">
                <Loader2 size={28} className="animate-spin text-blue-600" />
              </div>
            ) : filtered.length === 0 ? (
              <div className="text-center py-20 px-6 max-w-lg mx-auto">
                <div className="w-20 h-20 bg-blue-50 text-blue-500 rounded-full flex items-center justify-center mx-auto mb-6 shadow-sm border border-blue-100">
                  <Database size={36} />
                </div>
                <h3 className="font-semibold text-slate-900 text-xl mb-3">
                  {searchQuery ? 'No matching documents found' : 'Knowledge base is empty'}
                </h3>
                <p className="text-slate-500 mb-8 leading-relaxed">
                  {searchQuery 
                    ? `We couldn't find any documents matching "${searchQuery}". Try adjusting your filters or search terms.`
                    : 'The global knowledge base is currently empty. Upload engineering standards, reports, and code PDFs to begin analyzing them.'}
                </p>
                {isAdmin && !searchQuery && (
                  <button 
                    onClick={() => {
                      const fileInput = document.querySelector('input[type="file"]');
                      if (fileInput) fileInput.click();
                    }} 
                    className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded-xl font-medium transition-colors shadow-sm"
                  >
                    Upload First Document
                  </button>
                )}
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50">
                    <th className="text-left px-4 py-3 font-semibold text-slate-600">Document</th>
                    <th className="text-left px-4 py-3 font-semibold text-slate-600">Category</th>
                    <th className="text-left px-4 py-3 font-semibold text-slate-600">Status</th>
                    <th className="text-right px-4 py-3 font-semibold text-slate-600">Pages</th>
                    <th className="text-right px-4 py-3 font-semibold text-slate-600">Chunks</th>
                    <th className="text-right px-4 py-3 font-semibold text-slate-600">KG Entities</th>
                    <th className="text-left px-4 py-3 font-semibold text-slate-600">Uploaded</th>
                    {isAdmin && <th className="text-right px-4 py-3 font-semibold text-slate-600">Actions</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {filtered.map((doc) => (
                    <tr key={doc.id} className="hover:bg-slate-50/50 transition-colors">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <File size={16} className="text-slate-400 shrink-0" />
                          <span className="font-medium text-slate-800 truncate max-w-[200px]" title={doc.filename}>
                            {doc.filename}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-xs font-medium text-slate-600 bg-slate-100 px-2 py-0.5 rounded">
                          {doc.category || 'GENERAL'}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={doc.status} />
                      </td>
                      <td className="px-4 py-3 text-right text-slate-600">{doc.total_pages || '—'}</td>
                      <td className="px-4 py-3 text-right text-slate-600">{doc.total_chunks || '—'}</td>
                      <td className="px-4 py-3 text-right text-slate-600">{doc.total_kg_entities || '—'}</td>
                      <td className="px-4 py-3 text-slate-500">
                        {doc.created_at ? formatDistanceToNow(new Date(doc.created_at)) + ' ago' : '—'}
                      </td>
                      {isAdmin && (
                        <td className="px-4 py-3">
                          <div className="flex justify-end">
                            <button
                              onClick={() => handleDelete(doc.id, doc.filename)}
                              className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                              title="Delete"
                            >
                              <Trash2 size={15} />
                            </button>
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>

      {/* Processing Modal */}
      {activeJob && (
        <ProcessingModal
          jobId={activeJob.jobId}
          filename={activeJob.filename}
          onClose={() => { setActiveJob(null); fetchData(); }}
        />
      )}
    </div>
  );
}
