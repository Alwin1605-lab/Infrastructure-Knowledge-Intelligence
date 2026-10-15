import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp, ExternalLink, Loader2, Info, X, FileText } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

// ---------------------------------------------------------------------------
// Card
// ---------------------------------------------------------------------------
export function Card({ children, className, hover = false, ...props }) {
  return (
    <div
      className={cn(
        "bg-white border border-slate-200 rounded-xl shadow-sm",
        hover && "transition-all duration-200 hover:-translate-y-1 hover:shadow-md hover:border-slate-300",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Badge
// ---------------------------------------------------------------------------
export function Badge({ children, variant = "default", className }) {
  const variants = {
    default: "bg-slate-100 text-slate-700 ring-1 ring-slate-200",
    primary: "bg-blue-50 text-blue-700 ring-1 ring-blue-600/20",
    success: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-600/20",
    warning: "bg-amber-50 text-amber-700 ring-1 ring-amber-600/20",
    danger: "bg-red-50 text-red-700 ring-1 ring-red-600/20",
  };
  return (
    <span className={cn("px-2.5 py-0.5 text-xs font-semibold rounded-md", variants[variant], className)}>
      {children}
    </span>
  );
}

// ---------------------------------------------------------------------------
// CollapsibleSection
// ---------------------------------------------------------------------------
export function CollapsibleSection({ title, defaultOpen = false, children, icon: Icon, className }) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className={cn("border border-slate-200 rounded-lg overflow-hidden my-3 bg-slate-50/50", className)}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-3 flex items-center justify-between bg-white hover:bg-slate-50 transition-colors border-b border-transparent data-[open=true]:border-slate-200"
        data-open={isOpen}
      >
        <div className="flex items-center gap-2.5 font-semibold text-slate-800 text-sm">
          {Icon && <Icon className="w-4 h-4 text-blue-600" />}
          {title}
        </div>
        {isOpen ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
      </button>
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden bg-white"
          >
            <div className="p-4 border-t border-slate-100">
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Loader
// ---------------------------------------------------------------------------
export function Loader({ text = "Processing..." }) {
  return (
    <div className="flex flex-col items-center justify-center p-12 space-y-4">
      <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      {text && <p className="text-slate-500 font-medium text-sm animate-pulse">{text}</p>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// CitationPanel — Rich citation display
// ---------------------------------------------------------------------------
export function PDFViewerModal({ url, isOpen, onClose, title = "Document Viewer" }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-5xl h-[85vh] flex flex-col overflow-hidden">
        <div className="flex justify-between items-center px-4 py-3 border-b border-slate-200 shrink-0">
          <h3 className="font-semibold text-slate-900 truncate">{title}</h3>
          <button onClick={onClose} className="p-1 hover:bg-slate-100 rounded-lg text-slate-500 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="flex-1 w-full bg-slate-100 relative">
          <iframe 
            src={url} 
            className="w-full h-full border-none"
            title="PDF Viewer"
          />
        </div>
      </div>
    </div>
  );
}

export function CitationPanel({ sources }) {
  const [expanded, setExpanded] = useState(null);
  const [pdfViewerOpen, setPdfViewerOpen] = useState(false);
  const [activePdfUrl, setActivePdfUrl] = useState('');
  const [activePdfTitle, setActivePdfTitle] = useState('');

  if (!sources || sources.length === 0) return null;

  const getConfidenceBadge = (score) => {
    const pct = score != null ? Math.round(score * 100) : null;
    if (pct == null) return null;
    const variant = pct >= 80 ? 'success' : pct >= 60 ? 'warning' : 'danger';
    return <Badge variant={variant}>{pct}% match</Badge>;
  };

  const sorted = [...sources].sort((a, b) => (b.relevance_score ?? 0) - (a.relevance_score ?? 0));

  const handleViewPdf = (src) => {
    const docId = src.document_id;
    const page = src.page_number ?? src.page ?? 1;
    if (docId) {
      // In a real app, you would point to the document download endpoint or a custom viewer endpoint.
      // Append #page=page to jump to the page if the browser PDF viewer supports it.
      const url = `/api/v1/documents/${docId}/download#page=${page}`;
      setActivePdfUrl(url);
      setActivePdfTitle(`${src.document_name || 'Document'} - Page ${page}`);
      setPdfViewerOpen(true);
    }
  };

  return (
    <>
      <div className="space-y-2">
        {sorted.map((src, i) => {
          const isOpen = expanded === i;
          const docName = src.document_name || src.source || 'Unknown document';
          const page = src.page_number ?? src.page ?? null;
          const section = src.section ?? null;
          return (
            <div
              key={i}
              className="border border-slate-200 rounded-xl overflow-hidden bg-white shadow-sm"
            >
              <button
                onClick={() => setExpanded(isOpen ? null : i)}
                className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-50 transition-colors text-left gap-3"
              >
                {/* Rank */}
                <span className="w-6 h-6 rounded-full bg-blue-50 text-blue-600 text-xs font-bold flex items-center justify-center shrink-0">
                  {i + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-slate-800 text-sm truncate">{docName}</p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {page != null && `Page ${page}`}
                    {page != null && section && ' · '}
                    {section && section}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {getConfidenceBadge(src.relevance_score)}
                  {isOpen
                    ? <ChevronUp className="w-4 h-4 text-slate-400" />
                    : <ChevronDown className="w-4 h-4 text-slate-400" />}
                </div>
              </button>
              {isOpen && (
                <div className="px-4 pb-4 border-t border-slate-100 pt-3">
                  <p className="text-slate-600 text-sm leading-relaxed italic border-l-2 border-blue-300 pl-3">
                    &ldquo;{src.text || src.chunk_preview || 'No preview available.'}&rdquo;
                  </p>
                  <div className="flex gap-3 mt-4 flex-wrap items-center">
                    {src.document_type && (
                      <span className="text-xs bg-slate-100 text-slate-600 px-2 py-1 rounded-md font-medium">
                        {String(src.document_type).replace('_', ' ')}
                      </span>
                    )}
                    {page != null && (
                      <span className="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded-md font-medium">
                        Page {page}
                      </span>
                    )}
                    {src.relevance_score != null && (
                      <span className="text-xs bg-emerald-50 text-emerald-700 px-2 py-1 rounded-md font-medium">
                        Score: {(src.relevance_score * 100).toFixed(1)}%
                      </span>
                    )}
                    {src.document_id && (
                      <button 
                        onClick={() => handleViewPdf(src)}
                        className="ml-auto text-xs font-medium text-blue-600 hover:text-blue-700 bg-blue-50 hover:bg-blue-100 px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5"
                      >
                        <FileText className="w-3.5 h-3.5" />
                        View PDF
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
      
      <PDFViewerModal 
        isOpen={pdfViewerOpen} 
        onClose={() => setPdfViewerOpen(false)} 
        url={activePdfUrl} 
        title={activePdfTitle} 
      />
    </>
  );
}

// ---------------------------------------------------------------------------
// RecommendationPanel
// ---------------------------------------------------------------------------
export function RecommendationPanel({ recommendations }) {
  if (!recommendations || recommendations.length === 0) return null;

  const cleanActionText = (rawText) => {
    if (!rawText) return "Recommended Maintenance Action";
    // If text is a markdown table row or header, clean up pipes and formatting
    if (rawText.includes('|')) {
      const parts = rawText.split('|').map(s => s.trim()).filter(Boolean);
      // Remove table header labels like '#', 'Action', 'Priority'
      const cleanParts = parts.filter(p => !['#', 'action', 'priority', 'category', 'source reference', 'rationale', '---', ':---'].includes(p.toLowerCase()));
      if (cleanParts.length > 0) {
        return cleanParts.join(' — ').replace(/\*\*/g, '');
      }
    }
    return rawText.replace(/\*\*/g, '').trim();
  };

  return (
    <div className="space-y-3">
      {recommendations.map((rec, i) => {
        const priority = (rec.priority || 'medium').toLowerCase();
        const actionText = cleanActionText(rec.action || rec.title);
        const reasonText = rec.reason || rec.rationale || '';
        const standardsRef = rec.standards_reference || rec.source_reference || null;

        return (
          <div key={i} className="flex gap-4 p-4 rounded-xl border border-slate-200 bg-white shadow-sm hover:border-slate-300 transition-colors">
            <div className="mt-0.5 shrink-0">
              <Info className={cn("w-5 h-5", 
                priority === "high" ? "text-red-500" : 
                priority === "medium" ? "text-amber-500" : "text-emerald-500"
              )} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2 mb-1.5 flex-wrap">
                <h5 className="font-semibold text-slate-900 text-sm leading-snug break-words">{actionText}</h5>
                <Badge variant={priority === "high" ? "danger" : priority === "medium" ? "warning" : "success"}>
                  {priority.toUpperCase()}
                </Badge>
              </div>
              {reasonText && (
                <p className="text-sm text-slate-600 leading-relaxed mb-2 whitespace-pre-wrap">{reasonText}</p>
              )}
              {standardsRef && (
                <p className="text-xs font-medium text-blue-700 bg-blue-50 inline-block px-2.5 py-1 rounded-md mt-1">
                  Ref: {standardsRef}
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
