import React, { useState } from 'react';
import { Search, ChevronDown, ChevronRight, Loader2, FileText, Zap, Brain, Database } from 'lucide-react';
import apiClient from '../api/client';
import toast from 'react-hot-toast';

export function RetrievalInspector() {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [expandedSource, setExpandedSource] = useState(null);
  const [workspaceId, setWorkspaceId] = useState('');
  const [topK, setTopK] = useState(5);

  const handleInspect = async () => {
    if (!question.trim()) return;
    setLoading(true);
    setResult(null);
    try {
      const { data } = await apiClient.post('/chat/query', {
        question,
        top_k: topK,
        workspace_id: workspaceId || null,
      });
      setResult(data);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Query failed');
    } finally {
      setLoading(false);
    }
  };

  const getConfidenceColor = (score) => {
    if (score >= 0.8) return 'text-emerald-600 bg-emerald-50';
    if (score >= 0.6) return 'text-amber-600 bg-amber-50';
    return 'text-red-600 bg-red-50';
  };

  return (
    <div className="flex-1 overflow-y-auto bg-slate-50">
      <div className="max-w-5xl mx-auto p-8">
        <div className="mb-6">
          <h1 className="text-3xl font-light text-slate-900 tracking-tight">Retrieval Inspector</h1>
          <p className="text-slate-500 mt-1">Developer tool: inspect retrieved chunks, similarity scores, and context</p>
        </div>

        {/* Query Form */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
          <div className="flex gap-3 mb-4">
            <div className="flex-1">
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Question</label>
              <input
                type="text"
                value={question}
                onChange={e => setQuestion(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleInspect()}
                placeholder="Enter engineering question..."
                className="w-full h-10 px-4 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              />
            </div>
            <div className="w-32">
              <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Top-K</label>
              <input
                type="number"
                value={topK}
                onChange={e => setTopK(Number(e.target.value))}
                min={1} max={20}
                className="w-full h-10 px-3 border border-slate-300 rounded-lg text-sm focus:outline-none"
              />
            </div>
          </div>
          <button
            onClick={handleInspect}
            disabled={loading || !question.trim()}
            className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
            Inspect Retrieval
          </button>
        </div>

        {result && (
          <div className="space-y-5">
            {/* Confidence Overview */}
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <h2 className="font-bold text-slate-900 mb-3 flex items-center gap-2"><Brain size={18} /> Response Overview</h2>
              <div className="grid grid-cols-3 gap-4 mb-4">
                <div className="text-center p-3 bg-slate-50 rounded-lg">
                  <p className="text-xl font-bold text-slate-900">{result.sources?.length || 0}</p>
                  <p className="text-xs text-slate-500">Sources Retrieved</p>
                </div>
                <div className="text-center p-3 bg-slate-50 rounded-lg">
                  <p className="text-xl font-bold text-slate-900">
                    {result.confidence?.score ? (result.confidence.score * 100).toFixed(0) + '%' : '—'}
                  </p>
                  <p className="text-xs text-slate-500">Confidence</p>
                </div>
                <div className="text-center p-3 bg-slate-50 rounded-lg">
                  <p className="text-xl font-bold text-slate-900">{result.confidence?.grounding || '—'}</p>
                  <p className="text-xs text-slate-500">Grounding</p>
                </div>
              </div>
              <div className="text-sm text-slate-700 leading-relaxed bg-slate-50 p-4 rounded-lg">
                {result.answer || 'No answer generated'}
              </div>
            </div>

            {/* Retrieved Sources */}
            {result.sources?.length > 0 && (
              <div className="bg-white rounded-xl border border-slate-200 p-5">
                <h2 className="font-bold text-slate-900 mb-4 flex items-center gap-2"><Database size={18} /> Retrieved Chunks</h2>
                <div className="space-y-3">
                  {result.sources.map((src, i) => (
                    <div key={i} className="border border-slate-100 rounded-xl overflow-hidden">
                      <button
                        onClick={() => setExpandedSource(expandedSource === i ? null : i)}
                        className="w-full flex items-center justify-between px-4 py-3 bg-slate-50 hover:bg-slate-100 transition-colors text-left"
                      >
                        <div className="flex items-center gap-3">
                          <FileText size={15} className="text-slate-400 shrink-0" />
                          <div>
                            <p className="font-medium text-slate-800 text-sm">{src.document_name || src.source || 'Unknown'}</p>
                            <p className="text-xs text-slate-500">
                              Page {src.page_number || '?'} · {src.section || 'No section'}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className={`text-xs font-bold px-2 py-1 rounded ${getConfidenceColor(src.relevance_score || 0)}`}>
                            {((src.relevance_score || 0) * 100).toFixed(1)}%
                          </span>
                          {expandedSource === i ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                        </div>
                      </button>
                      {expandedSource === i && (
                        <div className="px-4 py-3 text-sm text-slate-600 leading-relaxed font-mono bg-white border-t border-slate-100">
                          {src.text || src.content || 'No content'}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* KG Context */}
            {result.kg_context && result.kg_context.length > 0 && (
              <div className="bg-white rounded-xl border border-slate-200 p-5">
                <h2 className="font-bold text-slate-900 mb-3 flex items-center gap-2"><Zap size={18} /> Knowledge Graph Context</h2>
                <div className="font-mono text-xs text-slate-600 bg-slate-50 p-4 rounded-lg max-h-48 overflow-y-auto">
                  <pre>{JSON.stringify(result.kg_context, null, 2)}</pre>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
