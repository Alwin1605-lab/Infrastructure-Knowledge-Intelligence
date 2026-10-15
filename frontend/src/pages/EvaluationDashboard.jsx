import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer, LineChart, Line } from 'recharts';
import { Play, TrendingUp } from 'lucide-react';
import { Card, Badge, Loader } from '../components/ui';
import { evalApi } from '../services/api';

export function EvaluationDashboard() {
  const { data: history, isLoading } = useQuery({
    queryKey: ['eval-history-full'],
    queryFn: evalApi.history,
  });

  if (isLoading) {
    return <Loader text="Loading evaluation history..." />;
  }

  // Format history for charts (reverse to get chronological order)
  const chartData = (history || []).slice().reverse().map((run, i) => ({
    name: `Run ${i + 1}`,
    accuracy: run.accuracy_percent || 0,
    latency: run.avg_latency_s || 0,
    date: new Date(run.date).toLocaleDateString()
  }));

  // Mock ablation data for demonstration
  const ablationData = [
    { name: 'LLM Only', accuracy: 65, latency: 0.8 },
    { name: 'RAG Only', accuracy: 78, latency: 1.2 },
    { name: 'RAG + KG', accuracy: 85, latency: 1.4 },
    { name: 'Hybrid RAG', accuracy: 89, latency: 1.6 },
    { name: 'Agentic AI', accuracy: 94, latency: 2.1 },
  ];

  return (
    <div className="flex-1 overflow-y-auto bg-slate-50">
      <div className="p-8 max-w-7xl mx-auto space-y-8">
        <header className="flex justify-between items-end mb-8">
          <div>
            <h1 className="text-3xl font-light text-slate-900 tracking-tight">Evaluation Dashboard</h1>
            <p className="text-slate-500 mt-1">Benchmark history, ablation studies, and pipeline metrics.</p>
          </div>
          <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white transition-colors rounded-lg font-medium shadow-sm">
            <Play className="w-4 h-4" />
            Run Benchmark
          </button>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Historical Accuracy Chart */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-emerald-500" />
                Historical Accuracy
              </h3>
              <Badge variant="success">Latest: {chartData[chartData.length - 1]?.accuracy?.toFixed(1) || 0}%</Badge>
            </div>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                  <XAxis dataKey="name" stroke="#94a3b8" tick={{fill: '#64748b'}} />
                  <YAxis stroke="#94a3b8" tick={{fill: '#64748b'}} domain={[0, 100]} />
                  <RechartsTooltip 
                    contentStyle={{ backgroundColor: '#ffffff', borderColor: '#e2e8f0', color: '#0f172a' }}
                    itemStyle={{ color: '#0f172a' }}
                  />
                  <Line type="monotone" dataKey="accuracy" stroke="#3b82f6" strokeWidth={3} dot={{r: 4, fill: '#3b82f6'}} activeDot={{r: 6}} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Architectural Ablation Study */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                Architectural Ablation (Accuracy)
              </h3>
            </div>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={ablationData} layout="vertical" margin={{ left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
                  <XAxis type="number" domain={[0, 100]} stroke="#94a3b8" tick={{fill: '#64748b'}} />
                  <YAxis dataKey="name" type="category" stroke="#94a3b8" tick={{fill: '#64748b'}} width={80} />
                  <RechartsTooltip 
                    contentStyle={{ backgroundColor: '#ffffff', borderColor: '#e2e8f0', color: '#0f172a' }}
                    cursor={{fill: '#f8fafc'}}
                  />
                  <Bar dataKey="accuracy" fill="#8b5cf6" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
