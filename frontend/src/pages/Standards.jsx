import React, { useState } from 'react';
import { Card, Badge, Loader, PDFViewerModal } from '../components/ui';
import { BookOpen, Search, Filter, FileText, Download, CheckCircle2, Layers } from 'lucide-react';
import { useDocuments } from '../hooks/useDocumentsQuery';
import { useNavigate } from 'react-router-dom';

const DEFAULT_STANDARDS = [
  { id: 'is-456', filename: 'IS 456 : 2000', title: 'Plain and Reinforced Concrete - Code of Practice', category: 'IS_CODE', total_pages: 114, is_standard: true },
  { id: 'is-800', filename: 'IS 800 : 2007', title: 'General Construction in Steel - Code of Practice', category: 'IS_CODE', total_pages: 152, is_standard: true },
  { id: 'is-1893', filename: 'IS 1893 : 2016', title: 'Criteria for Earthquake Resistant Design of Structures', category: 'IS_CODE', total_pages: 44, is_standard: true },
  { id: 'aci-318', filename: 'ACI 318-19', title: 'Building Code Requirements for Structural Concrete', category: 'ACI', total_pages: 624, is_standard: true },
  { id: 'nbc-2016', filename: 'NBC 2016 Part 4 & 6', title: 'National Building Code of India - Structural & Fire Safety', category: 'NBC', total_pages: 350, is_standard: true },
  { id: 'cpwd-maint', filename: 'CPWD Maintenance Manual', title: 'Handbook on Repair and Rehabilitation of RCC Buildings', category: 'CPWD', total_pages: 180, is_standard: true },
];

export function Standards() {
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('ALL');
  const [pdfModal, setPdfModal] = useState({ open: false, url: '', title: '' });
  const navigate = useNavigate();

  const { data: documentsData, isLoading } = useDocuments({ limit: 100 });
  const liveDocs = documentsData?.documents || [];

  // Combine live indexed documents with standard references
  const allStandards = [
    ...liveDocs.map(doc => ({
      id: doc.id,
      filename: doc.filename,
      title: doc.title || doc.filename.replace(/\.pdf$/i, '').replace(/[-_]/g, ' '),
      category: doc.category || 'RESEARCH',
      total_pages: doc.total_pages || 1,
      total_chunks: doc.total_chunks || 0,
      is_indexed: doc.status === 'completed',
      doc_id: doc.id
    })),
    ...DEFAULT_STANDARDS.filter(std => !liveDocs.some(d => d.filename?.toLowerCase().includes(std.id)))
  ];

  const filteredStandards = allStandards.filter(std => {
    const matchesSearch = 
      (std.filename || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (std.title || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      (std.category || '').toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCat = categoryFilter === 'ALL' || std.category === categoryFilter;
    return matchesSearch && matchesCat;
  });

  const categories = ['ALL', ...new Set(allStandards.map(s => s.category).filter(Boolean))];

  const handleOpenDoc = (std) => {
    if (std.doc_id) {
      setPdfModal({
        open: true,
        url: `/api/v1/documents/${std.doc_id}/download`,
        title: std.title || std.filename
      });
    } else {
      navigate('/assistant');
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto w-full flex flex-col h-full space-y-6">
      <div className="flex justify-between items-end shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Standards & Engineering Codes Library</h1>
          <p className="text-slate-500 mt-1 text-lg">Searchable knowledge repository of building standards, NBC guidelines, and indexed research literature.</p>
        </div>
        <Badge variant="primary" className="text-xs px-3 py-1">
          {allStandards.length} Standards & Guidelines
        </Badge>
      </div>

      <div className="flex flex-col sm:flex-row gap-4 shrink-0">
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
          <input 
            type="text" 
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search IS Codes (IS 456, IS 1893), ACI 318, NBC, CPWD manuals..." 
            className="w-full bg-white border border-slate-200 text-slate-900 py-3.5 pl-12 pr-4 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm font-medium"
          />
        </div>
        
        {/* Category Pills */}
        <div className="flex gap-2 overflow-x-auto pb-1 items-center">
          {categories.slice(0, 6).map((cat) => (
            <button
              key={cat}
              onClick={() => setCategoryFilter(cat)}
              className={`px-3 py-2 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                categoryFilter === cat 
                  ? 'bg-blue-600 text-white shadow-sm' 
                  : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <Loader text="Loading engineering standards and documents..." />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6 overflow-y-auto pb-8">
          {filteredStandards.map((std, idx) => (
            <Card 
              key={std.id || idx} 
              hover 
              className="p-6 cursor-pointer flex flex-col justify-between"
              onClick={() => handleOpenDoc(std)}
            >
              <div>
                <div className="flex justify-between items-start mb-3">
                  <Badge variant={std.is_indexed ? "success" : "primary"}>
                    {std.category}
                  </Badge>
                  {std.is_indexed && (
                    <span className="flex items-center gap-1 text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-md">
                      <CheckCircle2 className="w-3.5 h-3.5" /> Indexed in RAG
                    </span>
                  )}
                </div>
                <h3 className="text-xl font-bold text-slate-900 mb-2 leading-snug">{std.filename}</h3>
                <p className="text-slate-600 text-sm font-medium line-clamp-3 mb-4">{std.title}</p>
              </div>

              <div className="pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500 font-medium">
                <span className="flex items-center gap-1">
                  <BookOpen className="w-4 h-4 text-slate-400" />
                  {std.total_pages} {std.total_pages === 1 ? 'page' : 'pages'}
                </span>
                {std.total_chunks > 0 && (
                  <span className="flex items-center gap-1 text-blue-600">
                    <Layers className="w-3.5 h-3.5" /> {std.total_chunks} chunks
                  </span>
                )}
                <span className="text-blue-600 hover:text-blue-800 font-semibold flex items-center gap-1">
                  View Reference →
                </span>
              </div>
            </Card>
          ))}
        </div>
      )}

      <PDFViewerModal 
        isOpen={pdfModal.open}
        onClose={() => setPdfModal({ open: false, url: '', title: '' })}
        url={pdfModal.url}
        title={pdfModal.title}
      />
    </div>
  );
}
