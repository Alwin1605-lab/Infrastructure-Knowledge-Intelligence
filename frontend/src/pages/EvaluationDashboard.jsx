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
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <header className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold">Evaluation Dashboard</h1>
          <p className="text-slate-500">Benchmark history, ablation studies, and pipeline metrics.</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-[var(--color-primary)] hover:bg-[var(--color-primary-dark)] transition-colors rounded-lg font-medium shadow-lg shadow-[var(--color-primary)]/20">
          <Play className="w-4 h-4" />
          Run Benchmark
        </button>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Historical Accuracy Chart */}
        <Card className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-emerald-400" />
              Historical Accuracy
            </h3>
            <Badge variant="success">Latest: {chartData[chartData.length - 1]?.accuracy?.toFixed(1) || 0}%</Badge>
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" vertical={false} />
                <XAxis dataKey="name" stroke="rgba(255,255,255,0.5)" tick={{fill: 'rgba(255,255,255,0.5)'}} />
                <YAxis stroke="rgba(255,255,255,0.5)" tick={{fill: 'rgba(255,255,255,0.5)'}} domain={[0, 100]} />
                <RechartsTooltip 
                  contentStyle={{ backgroundColor: 'var(--color-surface-light)', borderColor: 'rgba(255,255,255,0.1)', color: '#fff' }}
                  itemStyle={{ color: '#fff' }}
                />
                <Line type="monotone" dataKey="accuracy" stroke="var(--color-primary)" strokeWidth={3} dot={{r: 4, fill: 'var(--color-primary)'}} activeDot={{r: 6}} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Architectural Ablation Study */}
        <Card className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              Architectural Ablation (Accuracy)
            </h3>
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={ablationData} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" horizontal={false} />
                <XAxis type="number" domain={[0, 100]} stroke="rgba(255,255,255,0.5)" />
                <YAxis dataKey="name" type="category" stroke="rgba(255,255,255,0.5)" width={80} />
                <RechartsTooltip 
                  contentStyle={{ backgroundColor: 'var(--color-surface-light)', borderColor: 'rgba(255,255,255,0.1)', color: '#fff' }}
                  cursor={{fill: 'rgba(255,255,255,0.05)'}}
                />
                <Bar dataKey="accuracy" fill="var(--color-secondary)" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
    </div>
  );
}
