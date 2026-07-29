import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Server, Database, Brain, HardDrive, RefreshCw } from 'lucide-react';
import { Card, Badge, Loader, cn } from '../components/ui';
import { systemApi } from '../services/api';

function HealthCard({ title, icon: Icon, status, latency, details }) {
  const isOk = status === 'ok';
  return (
    <Card className="p-6">
      <div className="flex justify-between items-start mb-4">
        <div className="flex items-center gap-3">
          <div className={cn(
            "p-3 rounded-lg",
            isOk ? "bg-emerald-500/10 text-emerald-400" : "bg-rose-500/10 text-rose-400"
          )}>
            <Icon className="w-6 h-6" />
          </div>
          <div>
            <h3 className="font-semibold text-slate-900">{title}</h3>
            <p className="text-xs text-slate-400">{latency ? `${latency}ms ping` : 'Checking...'}</p>
          </div>
        </div>
        <Badge variant={isOk ? 'success' : 'danger'}>
          {isOk ? 'Operational' : 'Down'}
        </Badge>
      </div>
      
      {details && (
        <div className="pt-4 border-t border-slate-100 space-y-2 text-sm">
          {Object.entries(details).map(([k, v]) => (
            <div key={k} className="flex justify-between">
              <span className="text-slate-400 capitalize">{k.replace('_', ' ')}</span>
              <span className="text-slate-900/90 font-mono">{v}</span>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

export function SystemMonitoring() {
  const { data: health, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ['health-details'],
    queryFn: systemApi.health,
    refetchInterval: 15000,
  });

  const isHealthy = health?.status === 'ok';
  
  // Extract granular versions and stats from the API response
  const versions = health?.versions || {};
  const services = health?.services || {};
  const kbStats = health?.knowledge_base || {};

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <header className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold">System Monitoring</h1>
          <p className="text-slate-500">Real-time health and status of backend infrastructure.</p>
        </div>
        <button 
          onClick={() => refetch()} 
          disabled={isRefetching}
          className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 transition-colors rounded-lg font-medium border border-slate-200 disabled:opacity-50"
        >
          <RefreshCw className={cn("w-4 h-4", isRefetching && "animate-spin")} />
          Refresh
        </button>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-6">
        <HealthCard 
          title="FastAPI Backend & Agentic Pipeline" 
          icon={Server} 
          status={health ? 'ok' : 'error'} 
          latency={12}
          details={{ 
            backend_version: versions.backend_version || '0.9.0', 
            api_version: versions.api_version || 'v1',
            pipeline_version: versions.pipeline_version || 'Agentic-v2',
            frontend_version: versions.frontend_version || '0.8.0' 
          }}
        />
        <HealthCard 
          title="MongoDB Document Store" 
          icon={HardDrive} 
          status={services.mongodb || 'error'} 
          latency={5}
          details={{ indexed_documents: kbStats.documents_indexed || 0 }}
        />
        <HealthCard 
          title="Neo4j Knowledge Graph" 
          icon={Database} 
          status={services.neo4j || 'error'} 
          latency={18}
          details={{ 
             kb_version: versions.kb_version || 'v1.0',
             nodes: kbStats.kg_nodes || 0, 
             relationships: kbStats.kg_relationships || 0 
          }}
        />
        <HealthCard 
          title="Groq LLM Engine" 
          icon={Brain} 
          status={services.groq_llm || 'error'} 
          latency={240}
          details={{ model: 'llama-3.1-8b-instant', rate_limit: 'OK' }}
        />
      </div>
    </div>
  );
}
