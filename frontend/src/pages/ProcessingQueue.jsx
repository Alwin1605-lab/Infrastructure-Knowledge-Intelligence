import React, { useState, useEffect, useCallback } from 'react';
import { Loader2, CheckCircle2, XCircle, Clock, RefreshCw, AlertTriangle } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { documentsApi } from '../api/documents';

const STATUS_STYLES = {
  queued: { color: 'bg-slate-100 text-slate-600', label: 'Queued', Icon: Clock },
  running: { color: 'bg-blue-100 text-blue-700', label: 'Running', Icon: Loader2, spin: true },
  completed: { color: 'bg-emerald-100 text-emerald-700', label: 'Completed', Icon: CheckCircle2 },
  failed: { color: 'bg-red-100 text-red-700', label: 'Failed', Icon: XCircle },
  retrying: { color: 'bg-yellow-100 text-yellow-700', label: 'Retrying', Icon: RefreshCw, spin: true },
};

function normalizeJobStatus(status) {
  if (!status) return 'queued';
  const s = String(status).replace('JobStatus.', '').toLowerCase();
  if (s.includes('complete')) return 'completed';
  if (s.includes('fail')) return 'failed';
  if (s.includes('run') || s.includes('extract') || s.includes('chunk') || s.includes('embed') || s.includes('kg')) return 'running';
  return s;
}

function JobRow({ job }) {
  const normStatus = normalizeJobStatus(job.status);
  const style = STATUS_STYLES[normStatus] || STATUS_STYLES.queued;
  const progress = normStatus === 'completed' ? 100 :
    normStatus === 'failed' ? 0 :
    Math.round(((job.completed_steps?.length || 0) / 5) * 100);
  
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 mb-3 hover:border-slate-300 transition-colors">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-slate-900 truncate">{job.filename}</p>
          <p className="text-xs text-slate-400 mt-0.5">
            Started {formatDistanceToNow(new Date(job.created_at))} ago
            {job.elapsed_seconds > 0 && ` · ${Math.round(job.elapsed_seconds)}s elapsed`}
          </p>
        </div>
        <span className={`ml-4 inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold shrink-0 ${style.color}`}>
          <style.Icon size={12} className={style.spin ? 'animate-spin' : ''} />
          {style.label}
        </span>
      </div>

      {normStatus !== 'queued' && (
        <>
          <div className="w-full bg-slate-100 rounded-full h-1.5 mb-3">
            <div
              className={`h-1.5 rounded-full transition-all ${
                normStatus === 'failed' ? 'bg-red-400' :
                normStatus === 'completed' ? 'bg-emerald-500' : 'bg-blue-500'
              }`}
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="flex gap-6 text-xs text-slate-500">
            <span>{job.pages_extracted || 0} pages</span>
            <span>{job.chunks_created || 0} chunks</span>
            <span>{job.embeddings_created || 0} embeddings</span>
            <span>{job.kg_nodes_created || 0} KG nodes</span>
          </div>
        </>
      )}

      {normStatus === 'failed' && job.error_message && (
        <div className="mt-3 flex items-start gap-2 text-xs text-red-600 bg-red-50 p-3 rounded-lg">
          <AlertTriangle size={14} className="mt-0.5 shrink-0" />
          <span className="line-clamp-2">{job.error_message}</span>
        </div>
      )}
    </div>
  );
}

export function ProcessingQueue() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchJobs = useCallback(async () => {
    try {
      const { data } = await documentsApi.listJobs({ limit: 50 });
      setJobs(data.jobs || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchJobs();
    if (autoRefresh) {
      const interval = setInterval(fetchJobs, 3000);
      return () => clearInterval(interval);
    }
  }, [fetchJobs, autoRefresh]);

  const filtered = jobs.filter(j => filter === 'all' || normalizeJobStatus(j.status) === filter);
  const counts = {
    queued: jobs.filter(j => normalizeJobStatus(j.status) === 'queued').length,
    running: jobs.filter(j => normalizeJobStatus(j.status) === 'running').length,
    completed: jobs.filter(j => normalizeJobStatus(j.status) === 'completed').length,
    failed: jobs.filter(j => normalizeJobStatus(j.status) === 'failed').length,
  };

  return (
    <div className="flex-1 overflow-y-auto bg-slate-50">
      <div className="max-w-4xl mx-auto p-8">
        <div className="flex justify-between items-end mb-6">
          <div>
            <h1 className="text-3xl font-light text-slate-900 tracking-tight">Processing Queue</h1>
            <p className="text-slate-500 mt-1">Background document indexing jobs</p>
          </div>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
              <input type="checkbox" checked={autoRefresh} onChange={e => setAutoRefresh(e.target.checked)} className="rounded" />
              Auto-refresh
            </label>
            <button onClick={fetchJobs} className="flex items-center gap-2 px-4 py-2 border border-slate-200 bg-white rounded-lg text-sm hover:bg-slate-50 transition-colors">
              <RefreshCw size={14} /> Refresh
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 bg-white border border-slate-200 rounded-xl p-1 w-fit">
          {['all', 'running', 'queued', 'completed', 'failed'].map(status => (
            <button
              key={status}
              onClick={() => setFilter(status)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold capitalize transition-colors ${
                filter === status
                  ? 'bg-slate-900 text-white'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {status} {status !== 'all' && `(${counts[status] || 0})`}
            </button>
          ))}
        </div>

        {/* List */}
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 size={24} className="animate-spin text-blue-600" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-400">
            No {filter !== 'all' ? filter : ''} jobs found
          </div>
        ) : (
          filtered.map(job => <JobRow key={job.id} job={job} />)
        )}
      </div>
    </div>
  );
}
