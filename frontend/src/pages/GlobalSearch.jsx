import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Search, Star, Trash2, FileText, BookOpen, BarChart2, File, GitBranch, Loader2 } from 'lucide-react';
import { searchApi } from '../api/search';

const TYPE_CONFIG = {
  document: { label: 'Document', icon: File, color: 'text-blue-600 bg-blue-50' },
  report: { label: 'Report', icon: BarChart2, color: 'text-amber-600 bg-amber-50' },
  standard: { label: 'Standard', icon: BookOpen, color: 'text-emerald-600 bg-emerald-50' },
};

export function GlobalSearch() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [savedSearches, setSavedSearches] = useState(() => {
    try { return JSON.parse(localStorage.getItem('savedSearches') || '[]'); } catch { return []; }
  });
  const inputRef = useRef(null);
  const suggTimeout = useRef(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const fetchSuggestions = useCallback(async (q) => {
    if (q.length < 2) { setSuggestions([]); return; }
    try {
      const { data } = await searchApi.suggestions(q);
      setSuggestions(data.suggestions || []);
    } catch { setSuggestions([]); }
  }, []);

  const handleQueryChange = (e) => {
    const q = e.target.value;
    setQuery(q);
    clearTimeout(suggTimeout.current);
    if (q.length >= 2) {
      setShowSuggestions(true);
      suggTimeout.current = setTimeout(() => fetchSuggestions(q), 300);
    } else {
      setShowSuggestions(false);
      setSuggestions([]);
    }
  };

  const handleSearch = async (q = query) => {
    if (!q.trim()) return;
    setQuery(q);
    setShowSuggestions(false);
    setLoading(true);
    try {
      const { data } = await searchApi.search(q);
      setResults(data.results || []);
    } catch { setResults([]); }
    finally { setLoading(false); }
  };

  const saveSearch = () => {
    if (!query.trim() || savedSearches.includes(query)) return;
    const updated = [query, ...savedSearches].slice(0, 8);
    setSavedSearches(updated);
    localStorage.setItem('savedSearches', JSON.stringify(updated));
  };

  const removeSaved = (s) => {
    const updated = savedSearches.filter(x => x !== s);
    setSavedSearches(updated);
    localStorage.setItem('savedSearches', JSON.stringify(updated));
  };

  return (
    <div className="flex-1 overflow-y-auto bg-slate-50">
      <div className="max-w-3xl mx-auto p-8">
        <div className="mb-8">
          <h1 className="text-3xl font-light text-slate-900 tracking-tight">Global Search</h1>
          <p className="text-slate-500 mt-1">Search across documents, reports, and knowledge entities</p>
        </div>

        {/* Search bar */}
        <div className="relative mb-6">
          <Search size={20} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Search engineering knowledge base..."
            value={query}
            onChange={handleQueryChange}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
            className="w-full h-14 pl-12 pr-32 border border-slate-300 rounded-xl bg-white text-base shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400"
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex gap-2">
            {results.length > 0 && (
              <button onClick={saveSearch} className="p-2 text-slate-400 hover:text-amber-500 transition-colors" title="Save search">
                <Star size={18} />
              </button>
            )}
            <button
              onClick={() => handleSearch()}
              disabled={loading || !query.trim()}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              Search
            </button>
          </div>

          {/* Suggestions dropdown */}
          {showSuggestions && suggestions.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-slate-200 rounded-xl shadow-lg z-10 overflow-hidden">
              {suggestions.map((s, i) => (
                <button
                  key={i}
                  onClick={() => handleSearch(s)}
                  className="w-full text-left px-4 py-2.5 hover:bg-slate-50 text-sm text-slate-700 flex items-center gap-3"
                >
                  <Search size={14} className="text-slate-400" />
                  {s}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Saved Searches */}
        {savedSearches.length > 0 && !results.length && (
          <div className="mb-8">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Saved Searches</p>
            <div className="flex flex-wrap gap-2">
              {savedSearches.map((s, i) => (
                <div key={i} className="flex items-center gap-1 bg-white border border-slate-200 rounded-lg px-3 py-1.5">
                  <Star size={13} className="text-amber-400" />
                  <button onClick={() => handleSearch(s)} className="text-sm text-slate-700 hover:text-blue-600">{s}</button>
                  <button onClick={() => removeSaved(s)} className="text-slate-300 hover:text-red-400 ml-1">
                    <Trash2 size={12} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Results */}
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 size={28} className="animate-spin text-blue-600" />
          </div>
        ) : results.length > 0 ? (
          <div className="space-y-3">
            <p className="text-sm text-slate-500">{results.length} results for &ldquo;{query}&rdquo;</p>
            {results.map((result) => {
              const cfg = TYPE_CONFIG[result.type] || TYPE_CONFIG.document;
              return (
                <div key={result.id} className="bg-white border border-slate-200 rounded-xl p-4 hover:border-blue-200 hover:shadow-sm transition-all">
                  <div className="flex items-start gap-3">
                    <div className={`p-2 rounded-lg shrink-0 ${cfg.color}`}>
                      <cfg.icon size={16} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wide">{cfg.label}</span>
                        {result.category && (
                          <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded">{result.category}</span>
                        )}
                      </div>
                      <h3 className="font-semibold text-slate-900 truncate">{result.name}</h3>
                      <p className="text-sm text-slate-500 mt-0.5">{result.excerpt}</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : query && !loading ? (
          <div className="text-center py-12 text-slate-400">
            <Search size={32} className="mx-auto mb-3 text-slate-300" />
            <p className="font-medium">No results found for &ldquo;{query}&rdquo;</p>
            <p className="text-sm mt-1">Try different keywords or check spelling</p>
          </div>
        ) : null}
      </div>
    </div>
  );
}
