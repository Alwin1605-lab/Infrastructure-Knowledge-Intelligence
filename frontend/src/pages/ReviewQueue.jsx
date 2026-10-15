import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { acquisitionApi } from '../api/acquisition';
import { Check, X, Clock, FileText } from 'lucide-react';
import toast from 'react-hot-toast';

export function ReviewQueue() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('METADATA_REVIEW'); // 'METADATA_REVIEW' or 'FULL_REVIEW'

  const { data: queueItems = [], isLoading } = useQuery({
    queryKey: ['acquisitionQueue'],
    queryFn: async () => {
      const res = await acquisitionApi.getQueue();
      return res.data;
    }
  });

  const approveDownload = useMutation({
    mutationFn: (id) => acquisitionApi.approveDownload(id),
    onSuccess: () => {
      toast.success('Document approved for download');
      queryClient.invalidateQueries(['acquisitionQueue']);
    },
    onError: () => toast.error('Failed to approve download')
  });

  const approveIndex = useMutation({
    mutationFn: (id) => acquisitionApi.approveIndex(id),
    onSuccess: () => {
      toast.success('Document approved for indexing');
      queryClient.invalidateQueries(['acquisitionQueue']);
    },
    onError: () => toast.error('Failed to approve indexing')
  });

  const reject = useMutation({
    mutationFn: (id) => acquisitionApi.reject(id),
    onSuccess: () => {
      toast.success('Document rejected');
      queryClient.invalidateQueries(['acquisitionQueue']);
    },
    onError: () => toast.error('Failed to reject document')
  });

  const filteredQueue = queueItems.filter(item => item.status === activeTab);

  if (isLoading) {
    return <div className="p-8">Loading queue...</div>;
  }

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Review Queue</h1>
          <p className="text-slate-500 mt-1">Review and approve documents for acquisition</p>
        </div>
      </div>

      <div className="flex space-x-4 mb-6">
        <button
          onClick={() => setActiveTab('METADATA_REVIEW')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === 'METADATA_REVIEW' ? 'bg-blue-600 text-white' : 'bg-white text-slate-600 hover:bg-slate-50'
          }`}
        >
          Needs Download ({queueItems.filter(i => i.status === 'METADATA_REVIEW').length})
        </button>
        <button
          onClick={() => setActiveTab('FULL_REVIEW')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === 'FULL_REVIEW' ? 'bg-blue-600 text-white' : 'bg-white text-slate-600 hover:bg-slate-50'
          }`}
        >
          Needs Indexing ({queueItems.filter(i => i.status === 'FULL_REVIEW').length})
        </button>
      </div>

      <div className="space-y-4">
        {filteredQueue.length === 0 ? (
          <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-slate-500">
            No items in this queue.
          </div>
        ) : (
          filteredQueue.map(item => (
            <div key={item.id} className="bg-white rounded-xl border border-slate-200 p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="flex-1">
                <h3 className="font-semibold text-slate-900 text-lg">{item.title}</h3>
                <div className="mt-2 space-y-1 text-sm text-slate-600">
                  <p><span className="font-medium text-slate-700">Source:</span> {item.source}</p>
                  {item.doi && <p><span className="font-medium text-slate-700">DOI:</span> {item.doi}</p>}
                  {item.abstract && <p className="line-clamp-2 mt-2">{item.abstract}</p>}
                </div>
                <div className="mt-3 flex items-center gap-2 text-xs text-slate-500">
                  <Clock className="w-4 h-4" />
                  <span>Added {new Date(item.created_at).toLocaleDateString()}</span>
                  <span className="px-2 py-0.5 rounded-full bg-slate-100 border border-slate-200">Score: {item.relevance_score || 'N/A'}</span>
                </div>
              </div>
              <div className="flex items-center gap-3 shrink-0">
                <button
                  onClick={() => reject.mutate(item.id)}
                  disabled={reject.isPending}
                  className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors flex items-center gap-2 font-medium"
                >
                  <X className="w-5 h-5" />
                  Reject
                </button>
                {activeTab === 'METADATA_REVIEW' ? (
                  <button
                    onClick={() => approveDownload.mutate(item.id)}
                    disabled={approveDownload.isPending}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors flex items-center gap-2 font-medium shadow-sm"
                  >
                    <Check className="w-5 h-5" />
                    Approve Download
                  </button>
                ) : (
                  <button
                    onClick={() => approveIndex.mutate(item.id)}
                    disabled={approveIndex.isPending}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition-colors flex items-center gap-2 font-medium shadow-sm"
                  >
                    <Check className="w-5 h-5" />
                    Approve Indexing
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
