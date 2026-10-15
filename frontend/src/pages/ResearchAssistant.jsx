import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { acquisitionApi } from '../api/acquisition';
import { Search, Link as LinkIcon, BookOpen, AlertCircle, CheckSquare, Square } from 'lucide-react';
import toast from 'react-hot-toast';

export function ResearchAssistant() {
  const [doi, setDoi] = useState('');
  const [query, setQuery] = useState('');
  const [author, setAuthor] = useState('');
  const [year, setYear] = useState('');
  const [journal, setJournal] = useState('');
  const [connectorType, setConnectorType] = useState('openalex');
  
  const [searchResults, setSearchResults] = useState([]);
  const [selectedDocs, setSelectedDocs] = useState(new Set());

  const importDoiMutation = useMutation({
    mutationFn: (doiStr) => acquisitionApi.importDoi(doiStr),
    onSuccess: () => {
      toast.success('DOI imported successfully! Check Review Queue.');
      setDoi('');
    },
    onError: () => toast.error('Failed to import DOI')
  });

  const searchMutation = useMutation({
    mutationFn: () => acquisitionApi.search(query, connectorType, author, year, journal),
    onSuccess: (data) => {
      setSearchResults(data.data?.documents || []);
      setSelectedDocs(new Set());
      if (data.data?.documents?.length === 0) {
        toast.error('No Open Access documents found for this query.');
      } else {
        toast.success(`Search completed. Found ${data.data?.documents?.length || 0} Open Access items.`);
      }
    },
    onError: () => toast.error('Search failed')
  });

  const batchImportMutation = useMutation({
    mutationFn: (docs) => acquisitionApi.batchImport(docs),
    onSuccess: () => {
      toast.success('Selected documents imported to Review Queue!');
      setSelectedDocs(new Set());
      setSearchResults([]);
    },
    onError: () => toast.error('Failed to import batch')
  });

  const toggleSelection = (index) => {
    const newSet = new Set(selectedDocs);
    if (newSet.has(index)) {
      newSet.delete(index);
    } else {
      newSet.add(index);
    }
    setSelectedDocs(newSet);
  };

  const selectAll = () => {
    if (selectedDocs.size === searchResults.length) {
      setSelectedDocs(new Set());
    } else {
      setSelectedDocs(new Set(searchResults.map((_, i) => i)));
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8 h-full flex flex-col">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Research Assistant</h1>
        <p className="text-slate-500 mt-1">Discover and batch import Open Access research material</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {/* Left Column: Search Controls */}
        <div className="md:col-span-1 space-y-6">
          {/* DOI Import */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-4 text-blue-600">
              <div className="p-2 bg-blue-50 rounded-lg">
                <LinkIcon className="w-5 h-5" />
              </div>
              <h2 className="text-lg font-semibold text-slate-900">Direct Import</h2>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">DOI</label>
                <input 
                  type="text" 
                  value={doi}
                  onChange={(e) => setDoi(e.target.value)}
                  placeholder="e.g. 10.1038/..." 
                  className="w-full px-4 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-600/20 focus:border-blue-600 outline-none"
                />
              </div>
              <button
                onClick={() => doi && importDoiMutation.mutate(doi)}
                disabled={!doi || importDoiMutation.isPending}
                className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg font-medium transition-colors shadow-sm"
              >
                {importDoiMutation.isPending ? 'Importing...' : 'Import via DOI'}
              </button>
            </div>
          </div>

          {/* Advanced Search */}
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
            <div className="flex items-center gap-3 mb-4 text-purple-600">
              <div className="p-2 bg-purple-50 rounded-lg">
                <Search className="w-5 h-5" />
              </div>
              <h2 className="text-lg font-semibold text-slate-900">Advanced Search</h2>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Connector</label>
                <select
                  value={connectorType}
                  onChange={(e) => setConnectorType(e.target.value)}
                  className="w-full px-4 py-2 border border-slate-200 rounded-lg outline-none bg-white"
                >
                  <option value="openalex">OpenAlex (Open Access Only)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Keywords</label>
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="concrete, corrosion, etc." 
                  className="w-full px-4 py-2 border border-slate-200 rounded-lg outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Author (ORCID)</label>
                <input
                  value={author}
                  onChange={(e) => setAuthor(e.target.value)}
                  placeholder="Optional" 
                  className="w-full px-4 py-2 border border-slate-200 rounded-lg outline-none"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Year</label>
                  <input
                    value={year}
                    onChange={(e) => setYear(e.target.value)}
                    placeholder="e.g. 2024" 
                    className="w-full px-4 py-2 border border-slate-200 rounded-lg outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Journal ID</label>
                  <input
                    value={journal}
                    onChange={(e) => setJournal(e.target.value)}
                    placeholder="Optional" 
                    className="w-full px-4 py-2 border border-slate-200 rounded-lg outline-none"
                  />
                </div>
              </div>

              <button
                onClick={() => (query || author || year || journal) && searchMutation.mutate()}
                disabled={(!query && !author && !year && !journal) || searchMutation.isPending}
                className="w-full px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-lg font-medium transition-colors shadow-sm flex items-center justify-center gap-2 mt-2"
              >
                <Search className="w-4 h-4" />
                {searchMutation.isPending ? 'Searching...' : 'Search Metadata'}
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Search Results & Batch Import */}
        <div className="md:col-span-2 bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col overflow-hidden h-[600px]">
          <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
            <h3 className="font-semibold text-slate-900">Preview Results ({searchResults.length})</h3>
            {searchResults.length > 0 && (
              <button 
                onClick={() => batchImportMutation.mutate(Array.from(selectedDocs).map(i => searchResults[i]))}
                disabled={selectedDocs.size === 0 || batchImportMutation.isPending}
                className="px-4 py-1.5 bg-blue-600 text-white rounded-lg text-sm font-medium disabled:opacity-50"
              >
                {batchImportMutation.isPending ? 'Importing...' : `Acquire Selected (${selectedDocs.size})`}
              </button>
            )}
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {searchResults.length === 0 ? (
              <div className="flex items-center justify-center h-full text-slate-400">
                Run a search to see Open Access papers here
              </div>
            ) : (
              <>
                <div className="flex items-center gap-2 mb-2 px-2 cursor-pointer" onClick={selectAll}>
                  {selectedDocs.size === searchResults.length ? (
                    <CheckSquare className="w-5 h-5 text-blue-600" />
                  ) : (
                    <Square className="w-5 h-5 text-slate-400" />
                  )}
                  <span className="text-sm text-slate-600">Select All</span>
                </div>
                {searchResults.map((doc, i) => (
                  <div key={i} className="flex gap-3 p-4 border border-slate-200 rounded-lg hover:border-blue-300 hover:bg-blue-50/50 transition-colors cursor-pointer" onClick={() => toggleSelection(i)}>
                    <div className="shrink-0 mt-1">
                      {selectedDocs.has(i) ? (
                        <CheckSquare className="w-5 h-5 text-blue-600" />
                      ) : (
                        <Square className="w-5 h-5 text-slate-400" />
                      )}
                    </div>
                    <div>
                      <h4 className="font-medium text-slate-900 line-clamp-2">{doc.title}</h4>
                      <p className="text-sm text-slate-500 mt-1 truncate">
                        {doc.authors?.join(', ')} • {doc.year}
                      </p>
                    </div>
                  </div>
                ))}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
