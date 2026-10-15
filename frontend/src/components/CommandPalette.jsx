import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, FileText, Briefcase, Bot, Settings, LayoutDashboard } from 'lucide-react';
import { useDocuments } from '../hooks/useDocumentsQuery';

export function CommandPalette() {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const navigate = useNavigate();
  const { data: documents } = useDocuments({ limit: 10 });

  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      }
      if (e.key === 'Escape') {
        setIsOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  if (!isOpen) return null;

  const quickLinks = [
    { name: 'Dashboard', icon: LayoutDashboard, path: '/' },
    { name: 'Workspaces', icon: Briefcase, path: '/workspaces' },
    { name: 'Document Library', icon: FileText, path: '/library' },
    { name: 'AI Assistant', icon: Bot, path: '/assistant' },
    { name: 'Settings', icon: Settings, path: '/settings' },
  ];

  const filteredLinks = quickLinks.filter(link => 
    link.name.toLowerCase().includes(query.toLowerCase())
  );
  
  const filteredDocs = (documents?.documents || []).filter(doc =>
    doc.filename.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm flex items-start justify-center pt-[15vh]">
      <div className="bg-white w-full max-w-2xl rounded-2xl shadow-2xl border border-slate-200 overflow-hidden"
           onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center px-4 py-3 border-b border-slate-100">
          <Search className="w-5 h-5 text-slate-400 mr-3" />
          <input
            type="text"
            className="flex-1 bg-transparent border-none outline-none text-slate-800 placeholder-slate-400 text-lg"
            placeholder="Type a command or search..."
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <kbd className="hidden sm:inline-block bg-slate-100 text-slate-500 px-2 py-1 rounded text-xs font-mono font-semibold">
            ESC
          </kbd>
        </div>
        
        <div className="max-h-[60vh] overflow-y-auto p-2">
          {query.length === 0 && (
            <div className="p-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Quick Links
            </div>
          )}
          
          <div className="space-y-1">
            {filteredLinks.map((link, i) => (
              <button
                key={i}
                className="w-full flex items-center px-4 py-3 text-left text-slate-700 hover:bg-slate-100 rounded-xl transition-colors"
                onClick={() => { navigate(link.path); setIsOpen(false); }}
              >
                <link.icon className="w-5 h-5 mr-3 text-slate-400" />
                <span className="font-medium">{link.name}</span>
              </button>
            ))}
          </div>

          {filteredDocs.length > 0 && (
            <>
              <div className="p-3 mt-4 text-xs font-semibold text-slate-500 uppercase tracking-wider border-t border-slate-100">
                Documents
              </div>
              <div className="space-y-1">
                {filteredDocs.map((doc, i) => (
                  <button
                    key={doc.id || i}
                    className="w-full flex items-center px-4 py-3 text-left text-slate-700 hover:bg-slate-100 rounded-xl transition-colors"
                    onClick={() => { navigate('/docs'); setIsOpen(false); }}
                  >
                    <FileText className="w-5 h-5 mr-3 text-emerald-500" />
                    <span className="font-medium truncate">{doc.filename}</span>
                  </button>
                ))}
              </div>
            </>
          )}

          {query.length > 0 && filteredLinks.length === 0 && filteredDocs.length === 0 && (
            <div className="px-4 py-12 text-center">
              <p className="text-slate-500">No results found for "{query}"</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
