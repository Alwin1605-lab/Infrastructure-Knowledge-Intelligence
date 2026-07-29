import React from 'react';
import { Network, Database, BrainCircuit, Activity, FileCheck, Target, ArrowRight } from 'lucide-react';
import { Card, Badge, cn } from '../components/ui';

function WorkflowNode({ title, icon: Icon, status, latency, active }) {
  return (
    <div className={cn(
      "flex flex-col items-center justify-center p-4 rounded-xl border-2 transition-all duration-300 w-48 text-center",
      active ? "border-[var(--color-primary)] bg-[var(--color-primary)]/10 shadow-[0_0_20px_rgba(79,70,229,0.3)]" : 
      status === 'success' ? "border-emerald-500/30 bg-emerald-500/5" :
      "border-slate-200 bg-white/5"
    )}>
      <div className={cn(
        "p-3 rounded-full mb-3",
        active ? "bg-[var(--color-primary)] text-slate-900" : "bg-white/10 text-slate-600"
      )}>
        <Icon className="w-6 h-6" />
      </div>
      <h4 className="font-semibold text-sm mb-1">{title}</h4>
      {latency && (
        <span className="text-xs text-slate-400 font-mono">{latency} ms</span>
      )}
    </div>
  );
}

export function Explainability() {
  // Static mockup of execution flow for presentation
  const agents = [
    { title: "Query Analysis", icon: Target, status: "success", latency: 45, active: false },
    { title: "Retrieval", icon: Database, status: "success", latency: 120, active: false },
    { title: "KG Reasoning", icon: Network, status: "success", latency: 85, active: false },
    { title: "Recommendation", icon: Activity, status: "success", latency: 310, active: false },
    { title: "Report Generation", icon: FileCheck, status: "success", latency: 450, active: true },
  ];

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold">Pipeline Explainability</h1>
        <p className="text-slate-500">Visualize the internal execution trace and reasoning of the Agentic AI.</p>
      </header>

      {/* Workflow Viewer */}
      <Card className="p-8 bg-gradient-to-br from-[#1a1728] to-[var(--color-surface)] border border-slate-100">
        <h3 className="text-lg font-semibold mb-8 flex items-center gap-2">
          <BrainCircuit className="w-5 h-5 text-[var(--color-primary-light)]" />
          Live Workflow Viewer
        </h3>
        
        <div className="flex items-center justify-center space-x-2 overflow-x-auto pb-4 custom-scrollbar">
          {agents.map((agent, i) => (
            <React.Fragment key={i}>
              <WorkflowNode {...agent} />
              {i < agents.length - 1 && (
                <div className="flex-shrink-0">
                  <ArrowRight className={cn(
                    "w-6 h-6 mx-2",
                    agent.active || agents[i+1].active ? "text-[var(--color-primary)]" : "text-slate-900/20"
                  )} />
                </div>
              )}
            </React.Fragment>
          ))}
        </div>
      </Card>

      {/* Detail Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-6">
          <h3 className="font-semibold mb-4 border-b border-slate-200 pb-2">Active Agent: Report Generation</h3>
          <div className="space-y-4 text-sm text-slate-900/80">
            <div>
              <p className="text-slate-400 mb-1">Status</p>
              <Badge variant="primary">Processing</Badge>
            </div>
            <div>
              <p className="text-slate-400 mb-1">Reasoning Trace</p>
              <div className="p-3 bg-black/30 rounded border border-slate-100 font-mono text-xs">
                {`> Synthesizing retrieved chunks (n=4)\n> Injecting KG relationships for 'Carbonation'\n> Formatting engineering recommendations\n> Assessing overall structural condition...`}
              </div>
            </div>
            <div>
              <p className="text-slate-400 mb-1">Confidence Propagation</p>
              <div className="w-full bg-white/10 rounded-full h-2 mb-1">
                <div className="bg-emerald-500 h-2 rounded-full" style={{ width: '92%' }}></div>
              </div>
              <p className="text-xs text-emerald-400">0.92 (High Grounding)</p>
            </div>
          </div>
        </Card>

        <Card className="p-6">
           <h3 className="font-semibold mb-4 border-b border-slate-200 pb-2">Retrieval Evidence</h3>
           <p className="text-sm text-slate-400 mb-4">Chunks supporting the current reasoning.</p>
           
           <div className="space-y-3">
             <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded-lg text-xs">
               <p className="font-medium text-blue-400 mb-1">Source: IS_456_2000.pdf</p>
               <p className="text-slate-900/80">"Carbonation of concrete in the presence of moisture and oxygen results in corrosion of reinforcement..."</p>
             </div>
             <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-xs">
               <p className="font-medium text-emerald-400 mb-1">Graph Entity: Carbonation</p>
               <p className="text-slate-900/80">CAUSES {'->'} Corrosion (Weight: 0.95)</p>
             </div>
           </div>
        </Card>
      </div>
    </div>
  );
}
