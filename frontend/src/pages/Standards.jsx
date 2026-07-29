import React from 'react';
import { Card, Badge } from '../components/ui';
import { BookOpen, Search, Filter } from 'lucide-react';

export function Standards() {
  const standards = [
    { id: 'is-456', code: 'IS 456 : 2000', title: 'Plain and Reinforced Concrete - Code of Practice', category: 'Concrete' },
    { id: 'is-800', code: 'IS 800 : 2007', title: 'General Construction in Steel - Code of Practice', category: 'Steel' },
    { id: 'is-1893', code: 'IS 1893 : 2016', title: 'Criteria for Earthquake Resistant Design of Structures', category: 'Earthquake' },
    { id: 'aci-318', code: 'ACI 318-19', title: 'Building Code Requirements for Structural Concrete', category: 'Concrete' },
  ];

  return (
    <div className="p-8 max-w-7xl mx-auto w-full flex flex-col h-full">
      <div className="flex justify-between items-end mb-8 shrink-0">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Standards & Codes Library</h1>
          <p className="text-slate-500 mt-1 text-lg">Searchable repository of building codes and engineering manuals.</p>
        </div>
      </div>

      <div className="flex gap-4 mb-8 shrink-0">
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
          <input 
            type="text" 
            placeholder="Search for IS Codes, ACI, NBC..." 
            className="w-full bg-white border border-slate-200 text-slate-900 py-3.5 pl-12 pr-4 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm font-medium"
          />
        </div>
        <button className="bg-white border border-slate-200 text-slate-700 px-5 py-3 rounded-xl font-medium flex items-center gap-2 hover:bg-slate-50 shadow-sm">
          <Filter className="w-5 h-5" />
          Filters
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6 overflow-y-auto pb-8">
        {standards.map(std => (
          <Card key={std.id} hover className="p-6 cursor-pointer">
            <div className="flex justify-between items-start mb-3">
              <Badge variant="primary">{std.category}</Badge>
              <BookOpen className="w-5 h-5 text-slate-300" />
            </div>
            <h2 className="text-2xl font-bold text-slate-900 mb-2">{std.code}</h2>
            <p className="text-slate-600 font-medium line-clamp-2">{std.title}</p>
          </Card>
        ))}
      </div>
    </div>
  );
}
