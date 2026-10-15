import React, { useEffect, useState } from 'react';
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import { Loader2, BarChart3, Clock, Zap, FileText } from 'lucide-react';
import { analyticsApi } from '../api/analytics';

const CATEGORY_COLORS = [
  '#3b82f6', '#6366f1', '#8b5cf6', '#06b6d4', '#10b981',
  '#f59e0b', '#ef4444', '#ec4899', '#84cc16', '#f97316',
];

function StatCard({ label, value, unit, icon: Icon, color }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 px-5 py-4">
      <div className="flex items-center gap-3 mb-2">
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${color}`}>
          <Icon size={18} />
        </div>
        <span className="text-sm text-slate-500">{label}</span>
      </div>
      <p className="text-2xl font-bold text-slate-900">
        {value ?? '—'}{unit && <span className="text-base font-normal text-slate-400 ml-1">{unit}</span>}
      </p>
    </div>
  );
}

export function Analytics() {
  const [kbData, setKbData] = useState(null);
  const [queryData, setQueryData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [kb, q] = await Promise.all([
          analyticsApi.getKB().catch(() => ({ data: {} })),
          analyticsApi.getQueries().catch(() => ({ data: {} })),
        ]);
        setKbData(kb.data);
        setQueryData(q.data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const categoryData = Object.entries(kbData?.stats?.category_distribution || {}).map(
    ([name, value]) => ({ name: name.replace('_', ' '), value })
  );

  const growthData = (kbData?.growth || []).slice(-14).map(g => ({
    date: g.date.slice(5), // MM-DD
    Documents: g.documents,
    Chunks: g.chunks,
  }));

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 size={32} className="animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto bg-slate-50">
      <div className="max-w-7xl mx-auto p-8">
        <div className="mb-8">
          <h1 className="text-3xl font-light text-slate-900 tracking-tight">Analytics</h1>
          <p className="text-slate-500 mt-1">Knowledge base and query performance insights</p>
        </div>

        {/* Knowledge Quality Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <StatCard label="Total Entities" value={kbData?.stats?.total_kg_entities || 0} icon={FileText} color="bg-indigo-50 text-indigo-600" />
          <StatCard label="Total Relationships" value={kbData?.stats?.total_kg_relationships || 0} icon={FileText} color="bg-pink-50 text-pink-600" />
          <StatCard 
            label="Entity Density" 
            value={kbData?.stats?.total_chunks ? (kbData.stats.total_kg_entities / kbData.stats.total_chunks).toFixed(2) : 0} 
            unit="per chunk"
            icon={BarChart3} color="bg-blue-50 text-blue-600" 
          />
          <StatCard 
            label="Graph Connectivity" 
            value={kbData?.stats?.total_kg_entities ? (kbData.stats.total_kg_relationships / kbData.stats.total_kg_entities).toFixed(2) : 0} 
            unit="rel/node"
            icon={BarChart3} color="bg-emerald-50 text-emerald-600" 
          />
        </div>

        {/* Query Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <StatCard label="Total Queries" value={queryData?.total_queries} icon={BarChart3} color="bg-blue-50 text-blue-600" />
          <StatCard label="Avg Response" value={queryData?.avg_total_ms} unit="ms" icon={Clock} color="bg-violet-50 text-violet-600" />
          <StatCard label="Avg Retrieval" value={queryData?.avg_retrieval_ms} unit="ms" icon={Zap} color="bg-emerald-50 text-emerald-600" />
          <StatCard label="Avg Chunks" value={queryData?.avg_chunks_retrieved} icon={FileText} color="bg-amber-50 text-amber-600" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          {/* KB Growth Chart */}
          <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-6">
            <h2 className="text-base font-bold text-slate-900 mb-4">Knowledge Base Growth (Last 14 Days)</h2>
            {growthData.length === 0 ? (
              <div className="flex items-center justify-center h-48 text-slate-400 text-sm">No data yet</div>
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={growthData}>
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Line type="monotone" dataKey="Documents" stroke="#3b82f6" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Category Distribution */}
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h2 className="text-base font-bold text-slate-900 mb-4">By Category</h2>
            {categoryData.length === 0 ? (
              <div className="flex items-center justify-center h-48 text-slate-400 text-sm">No documents</div>
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={categoryData} dataKey="value" nameKey="name" outerRadius={80} label={({name, value}) => `${name}:${value}`}>
                    {categoryData.map((_, i) => (
                      <Cell key={i} fill={CATEGORY_COLORS[i % CATEGORY_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Slowest Queries */}
        {queryData?.slowest_queries?.length > 0 && (
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <h2 className="text-base font-bold text-slate-900 mb-4">Slowest Queries</h2>
            <div className="space-y-3">
              {queryData.slowest_queries.map((q, i) => (
                <div key={i} className="flex items-center justify-between py-2 border-b border-slate-50 last:border-0">
                  <p className="text-sm text-slate-700 truncate flex-1 mr-4">{q.question}</p>
                  <span className="text-sm font-mono font-semibold text-slate-900 shrink-0">{q.total_ms}ms</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
