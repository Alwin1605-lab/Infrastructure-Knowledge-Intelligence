import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp, ExternalLink, Loader2, Info } from 'lucide-react';
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
// CitationPanel
// ---------------------------------------------------------------------------
export function CitationPanel({ sources }) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="space-y-3">
      {sources.map((src, i) => (
        <Card key={i} className="p-4 bg-slate-50 border-slate-200 text-sm">
          <div className="flex justify-between items-start mb-3">
            <h5 className="font-semibold flex items-center gap-2 text-slate-800">
              <ExternalLink className="w-4 h-4 text-blue-600" />
              {src.document_name}
            </h5>
            <Badge variant="primary">Page {src.page}</Badge>
          </div>
          <p className="text-slate-600 text-sm italic border-l-2 border-slate-300 pl-3 py-1">
            "{src.chunk_preview}..."
          </p>
        </Card>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// RecommendationPanel
// ---------------------------------------------------------------------------
export function RecommendationPanel({ recommendations }) {
  if (!recommendations || recommendations.length === 0) return null;

  return (
    <div className="space-y-3">
      {recommendations.map((rec, i) => (
        <div key={i} className="flex gap-4 p-4 rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="mt-0.5 shrink-0">
            <Info className={cn("w-5 h-5", 
              rec.priority === "high" ? "text-red-500" : 
              rec.priority === "medium" ? "text-amber-500" : "text-emerald-500"
            )} />
          </div>
          <div className="flex-1">
            <div className="flex items-center justify-between gap-2 mb-1.5">
              <h5 className="font-semibold text-slate-900">{rec.action}</h5>
              <Badge variant={rec.priority === "high" ? "danger" : rec.priority === "medium" ? "warning" : "success"}>
                {rec.priority.toUpperCase()}
              </Badge>
            </div>
            <p className="text-sm text-slate-600 leading-relaxed mb-2">{rec.reason}</p>
            {rec.standards_reference && (
              <p className="text-xs font-medium text-blue-700 bg-blue-50 inline-block px-2 py-1 rounded-md">
                Ref: {rec.standards_reference}
              </p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
