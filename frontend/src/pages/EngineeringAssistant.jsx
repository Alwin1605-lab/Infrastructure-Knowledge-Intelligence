import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Send, Bot, User, AlignLeft, ShieldAlert, BookOpen, Activity, ChevronRight, FileText, Download } from 'lucide-react';
import { Card, CollapsibleSection, CitationPanel, RecommendationPanel, Loader, Badge, cn } from '../components/ui';
import { agentsApi } from '../services/api';
import toast from 'react-hot-toast';

const SUGGESTED_PROMPTS = [
  "How should carbonation cracks be repaired?",
  "Explain IS 456 crack width limits.",
  "Recommend repair for spalling concrete.",
  "Compare epoxy injection and routing."
];

export function EngineeringAssistant() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');

  const chatMutation = useMutation({
    mutationFn: agentsApi.query,
    onSuccess: (data) => {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: data },
      ]);
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || "Failed to complete engineering analysis.");
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', error: true, content: "An error occurred during analysis. Please try again." },
      ]);
    }
  });

  const handleSubmit = (e) => {
    e?.preventDefault();
    if (!input.trim()) return;

    const userMsg = input.trim();
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: userMsg }]);
    chatMutation.mutate({ question: userMsg, top_k: 5 });
  };

  const handlePromptClick = (prompt) => {
    setInput(prompt);
  };

  return (
    <div className="flex flex-col h-full max-w-5xl mx-auto p-8 w-full">
      <header className="mb-6 flex justify-between items-end shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Engineering Analysis Workspace</h1>
          <p className="text-slate-500 mt-1">Review structural defects, consult engineering codes, and generate recommendations.</p>
        </div>
        <div className="flex gap-2">
          <Badge variant="default" className="flex items-center gap-1.5"><FileText className="w-3.5 h-3.5" /> 4 Active Docs</Badge>
          <Badge variant="default" className="flex items-center gap-1.5"><BookOpen className="w-3.5 h-3.5" /> IS 456, ACI 318</Badge>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto mb-6 space-y-8 pr-4 custom-scrollbar">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center">
            <Bot className="w-16 h-16 text-slate-200 mb-6" />
            <h2 className="text-xl font-bold text-slate-700 mb-2">How can I assist your inspection today?</h2>
            <p className="text-slate-500 mb-8 max-w-md text-center">Ask structural questions, evaluate defect symptoms, or request maintenance reports based on indexed standards.</p>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full max-w-2xl">
              {SUGGESTED_PROMPTS.map((prompt, idx) => (
                <Card 
                  key={idx} 
                  hover 
                  className="p-4 cursor-pointer flex items-center justify-between group"
                  onClick={() => handlePromptClick(prompt)}
                >
                  <span className="text-sm font-medium text-slate-700">{prompt}</span>
                  <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-blue-500 transition-colors" />
                </Card>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={cn("flex gap-4", msg.role === 'user' ? 'justify-end' : 'justify-start')}>
            {msg.role === 'assistant' && (
              <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center shrink-0 border border-blue-100 shadow-sm mt-1">
                <Bot className="w-5 h-5 text-blue-600" />
              </div>
            )}

            <div className={cn(
              "max-w-[90%] rounded-2xl p-6",
              msg.role === 'user' 
                ? "bg-blue-600 text-white shadow-md rounded-tr-none" 
                : "bg-white border border-slate-200 rounded-tl-none shadow-sm"
            )}>
              {msg.role === 'user' ? (
                <p className="whitespace-pre-wrap font-medium">{msg.content}</p>
              ) : msg.error ? (
                <p className="text-red-500 font-medium">{msg.content}</p>
              ) : (
                <div className="space-y-4">
                  {/* Confidence Header */}
                  <div className="flex justify-between items-center pb-4 border-b border-slate-100">
                    <span className="text-sm font-bold text-slate-800 uppercase tracking-wide">Analysis Complete</span>
                    <Badge variant={msg.content.overall_confidence > 0.8 ? "success" : "warning"}>
                      Confidence: {(msg.content.overall_confidence * 100).toFixed(0)}%
                    </Badge>
                  </div>

                  {/* Main Answer Section */}
                  <CollapsibleSection title="Engineering Analysis" defaultOpen={true} icon={AlignLeft}>
                    <div className="prose prose-slate max-w-none text-sm text-slate-700 font-medium">
                      <p className="whitespace-pre-wrap leading-relaxed">
                        {msg.content.report || msg.content.rag_response?.answer || "No text generated."}
                      </p>
                    </div>
                  </CollapsibleSection>

                  {/* Recommendations */}
                  {msg.content.rag_response?.recommendations?.length > 0 && (
                    <CollapsibleSection title="Maintenance Priority" defaultOpen={true} icon={ShieldAlert}>
                      <RecommendationPanel recommendations={msg.content.rag_response.recommendations} />
                    </CollapsibleSection>
                  )}

                  {/* Citations / Sources */}
                  {msg.content.rag_response?.sources?.length > 0 && (
                    <CollapsibleSection title="Supporting Evidence & Documents" icon={BookOpen}>
                      <CitationPanel sources={msg.content.rag_response.sources} />
                    </CollapsibleSection>
                  )}

                  {/* Hidden Execution Trace (Moved to Dev Mode conceptually, but keeping basic status for transparency if needed, though instruction says "Never expose AI implementation terminology". Let's remove it from this view.) */}
                  
                  <div className="pt-4 flex justify-end">
                    <button className="flex items-center gap-2 text-sm font-semibold text-blue-600 hover:text-blue-800 transition-colors bg-blue-50 px-4 py-2 rounded-lg">
                      <Download className="w-4 h-4" />
                      Export Report
                    </button>
                  </div>
                </div>
              )}
            </div>

            {msg.role === 'user' && (
              <div className="w-10 h-10 rounded-xl bg-slate-100 border border-slate-200 flex items-center justify-center shrink-0 mt-1">
                <User className="w-5 h-5 text-slate-500" />
              </div>
            )}
          </div>
        ))}
        
        {chatMutation.isPending && (
          <div className="flex gap-4">
             <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center shrink-0 border border-blue-100 shadow-sm mt-1">
                <Bot className="w-5 h-5 text-blue-600" />
              </div>
             <div className="bg-white border border-slate-200 p-6 rounded-2xl rounded-tl-none shadow-sm max-w-md w-full">
                <Loader text="Analyzing engineering standards and context..." />
             </div>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="relative mt-auto shrink-0">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="E.g., What are the standard repair methods for severe cracks in a load-bearing wall?"
          className="w-full bg-white border border-slate-300 rounded-xl py-4 pl-4 pr-14 text-slate-900 font-medium placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all shadow-sm"
          disabled={chatMutation.isPending}
        />
        <button
          type="submit"
          disabled={chatMutation.isPending || !input.trim()}
          className="absolute right-2 top-1/2 -translate-y-1/2 p-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Send className="w-5 h-5 ml-0.5" />
        </button>
      </form>
    </div>
  );
}
