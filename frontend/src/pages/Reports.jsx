import React from 'react';
import { Card, Badge } from '../components/ui';
import { FileBarChart, Download, ExternalLink, Calendar } from 'lucide-react';

export function Reports() {
  const reports = [
    { id: 1, title: 'Structural Integrity Assessment - ABC Apartment', date: '2026-07-28', risk: 'high', type: 'Inspection' },
    { id: 2, title: 'Seismic Retrofitting Recommendations - City Hospital', date: '2026-07-25', risk: 'medium', type: 'Consulting' },
    { id: 3, title: 'Maintenance Schedule Q3 - University Main Block', date: '2026-07-10', risk: 'low', type: 'Maintenance' },
  ];

  return (
    <div className="p-8 max-w-7xl mx-auto w-full">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Engineering Reports</h1>
          <p className="text-slate-500 mt-1 text-lg">Generated inspection summaries and maintenance recommendations.</p>
        </div>
        <button className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl font-medium transition-colors shadow-sm flex items-center gap-2">
          <FileBarChart className="w-5 h-5" />
          Generate Report
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {reports.map(report => (
          <Card key={report.id} hover className="p-6">
            <div className="flex justify-between items-start mb-4">
              <Badge variant={report.risk === 'high' ? 'danger' : report.risk === 'medium' ? 'warning' : 'success'}>
                {report.risk.toUpperCase()} RISK
              </Badge>
              <Badge variant="default">{report.type}</Badge>
            </div>
            <h3 className="text-xl font-bold text-slate-900 mb-3">{report.title}</h3>
            
            <div className="flex items-center gap-2 text-slate-500 text-sm mb-6 font-medium">
              <Calendar className="w-4 h-4" />
              Generated on {new Date(report.date).toLocaleDateString()}
            </div>
            
            <div className="flex gap-3 border-t border-slate-100 pt-4">
              <button className="flex-1 flex items-center justify-center gap-2 bg-slate-50 hover:bg-slate-100 text-slate-700 py-2 rounded-lg font-semibold transition-colors">
                <ExternalLink className="w-4 h-4" /> View
              </button>
              <button className="flex-1 flex items-center justify-center gap-2 bg-blue-50 hover:bg-blue-100 text-blue-700 py-2 rounded-lg font-semibold transition-colors">
                <Download className="w-4 h-4" /> Export PDF
              </button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
