import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Server, Database, Brain, HardDrive, RefreshCw, Layers, Box, CheckCircle, Clock, XCircle } from 'lucide-react';
import { Badge, cn } from '../components/ui';
import { analyticsApi } from '../api/analytics';
import apiClient from '../api/client';

function HealthCard({ title, icon: Icon, status, details }) {
  const isOk = status === 'ok';
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
      <div className="flex justify-between items-start mb-4">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
            isOk ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-500'
          }`}>
            <Icon size={20} />
          </div>
          <div>
            <h3 className="font-semibold text-slate-900 text-sm">{title}</h3>
            <p className="text-xs text-slate-400 mt-0.5">{isOk ? 'Operational' : 'Unavailable'}</p>
          </div>
        </div>
        <div className={`w-2.5 h-2.5 rounded-full mt-1 ${
          isOk ? 'bg-emerald-400' : 'bg-red-400'
        } ${isOk ? 'shadow-[0_0_8px_rgba(52,211,153,0.8)]' : ''}`} />
      </div>
      {details && (
        <div className="space-y-2 border-t border-slate-50 pt-3">
          {Object.entries(details).map(([k, v]) => (
            <div key={k} className="flex justify-between text-xs">
              <span className="text-slate-400 capitalize">{k.replace(/_/g, ' ')}</span>
              <span className="font-mono text-slate-700">{v}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function StatItem({ label, value, icon: Icon }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-slate-50 last:border-0">
      <div className="flex items-center gap-2 text-sm text-slate-600">
        <Icon size={15} className="text-slate-400" />
        {label}
      </div>
      <span className="font-bold text-slate-900">{value?.toLocaleString() ?? '—'}</span>
    </div>
  );
}

export function SystemMonitoring() {
  const { data: health, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ['health-details'],
    queryFn: () => apiClient.get('/health/system').then(r => r.data),
    refetchInterval: 15000,
  });

  const { data: analytics } = useQuery({
    queryKey: ['analytics-kb'],
    queryFn: () => analyticsApi.getKB().then(r => r.data),
    refetchInterval: 30000,
  });

  const services = health?.services || {};
  const versions = health?.versions || {};
  const kbStats = health?.knowledge_base || {};
  const analyticsStats = analytics?.stats || {};
  const queueStats = analytics?.queue || {};

  return (
    <div className="flex-1 overflow-y-auto bg-slate-50">
      <div className="max-w-7xl mx-auto p-8">
        <header className="flex justify-between items-end mb-8">
          <div>
            <h1 className="text-3xl font-light text-slate-900 tracking-tight">System Monitoring</h1>
            <p className="text-slate-500">Real-time infrastructure health and statistics</p>
          </div>
          <button
            onClick={() => refetch()}
            disabled={isRefetching}
            className="flex items-center gap-2 px-4 py-2 border border-slate-200 bg-white rounded-lg text-sm hover:bg-slate-50 disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={cn('w-4 h-4', isRefetching && 'animate-spin')} />
            Refresh
          </button>
        </header>

        {/* Service Health Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
          <HealthCard
            title="FastAPI Backend"
            icon={Server}
            status={health ? 'ok' : 'down'}
            details={{
              backend_version: versions.backend_version || '0.9.0',
              api_version: versions.api_version || 'v1',
              pipeline: versions.pipeline_version || 'Agentic-v2',
            }}
          />
          <HealthCard
            title="MongoDB"
            icon={HardDrive}
            status={services.mongodb || 'down'}
            details={{ documents_indexed: kbStats.documents_indexed || 0 }}
          />
          <HealthCard
            title="ChromaDB"
            icon={Layers}
            status={services.chromadb || 'down'}
            details={{ chunks_indexed: analyticsStats.total_chunks || 0 }}
          />
          <HealthCard
            title="Neo4j Knowledge Graph"
            icon={Database}
            status={services.neo4j || 'down'}
            details={{
              nodes: kbStats.kg_nodes || 0,
              relationships: kbStats.kg_relationships || 0,
            }}
          />
          <HealthCard
            title="Groq LLM"
            icon={Brain}
            status={services.groq_llm || 'down'}
            details={{ model: 'llama-3.1-8b-instant' }}
          />
          <HealthCard
            title="Embedding Service"
            icon={Box}
            status={health ? 'ok' : 'down'}
            details={{ model: 'all-MiniLM-L6-v2', device: 'cpu' }}
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* KB Statistics */}
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h2 className="text-base font-bold text-slate-900 mb-4">Knowledge Base Statistics</h2>
            <StatItem label="Total Documents" value={analyticsStats.total_documents} icon={HardDrive} />
            <StatItem label="Total Chunks" value={analyticsStats.total_chunks} icon={Layers} />
            <StatItem label="Total Embeddings" value={analyticsStats.total_chunks} icon={Box} />
            <StatItem label="KG Entities" value={analyticsStats.total_kg_entities} icon={Database} />
            <StatItem label="KG Relationships" value={analyticsStats.total_kg_relationships} icon={Database} />
            <StatItem label="Failed Documents" value={analyticsStats.failed_documents} icon={XCircle} />
          </div>

          {/* Processing Queue Stats */}
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h2 className="text-base font-bold text-slate-900 mb-4">Processing Queue</h2>
            <StatItem label="Queued" value={queueStats.queued} icon={Clock} />
            <StatItem label="Running" value={queueStats.running} icon={RefreshCw} />
            <StatItem label="Completed" value={queueStats.completed} icon={CheckCircle} />
            <StatItem label="Failed" value={queueStats.failed} icon={XCircle} />
            <StatItem label="Total Jobs" value={queueStats.total} icon={Database} />
          </div>
        </div>
      </div>
    </div>
  );
}
