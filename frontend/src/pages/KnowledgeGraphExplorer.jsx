import React from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { Card } from '../components/ui';

export function KnowledgeGraphExplorer() {
  // Placeholder graph data
  const graphData = {
    nodes: [
      { id: 'Spalling', group: 1 },
      { id: 'Corrosion', group: 2 },
      { id: 'IS 456', group: 3 },
    ],
    links: [
      { source: 'Spalling', target: 'Corrosion', name: 'CAUSED_BY' },
      { source: 'Corrosion', target: 'IS 456', name: 'REFERENCED_IN' },
    ]
  };

  return (
    <div className="p-8 max-w-7xl mx-auto h-full flex flex-col">
      <header className="mb-6">
        <h1 className="text-3xl font-bold">Knowledge Graph Explorer</h1>
        <p className="text-slate-500">Interactive visualization of building entities and relationships.</p>
      </header>
      
      <Card className="flex-1 min-h-[600px] bg-black/20 overflow-hidden relative border-slate-200">
        <ForceGraph2D
          graphData={graphData}
          nodeLabel="id"
          nodeColor={(node) => (node.group === 1 ? '#ef4444' : node.group === 2 ? '#f59e0b' : '#3b82f6')}
          linkColor={() => 'rgba(255,255,255,0.2)'}
          width={1000}
          height={600}
        />
        <div className="absolute top-4 right-4 bg-black/50 p-4 rounded-lg backdrop-blur text-sm border border-slate-200">
          <p className="font-semibold mb-2">Legend</p>
          <div className="flex items-center gap-2 mb-1"><div className="w-3 h-3 rounded-full bg-red-500"></div> Defect</div>
          <div className="flex items-center gap-2 mb-1"><div className="w-3 h-3 rounded-full bg-amber-500"></div> Mechanism</div>
          <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-blue-500"></div> Standard</div>
        </div>
      </Card>
    </div>
  );
}
