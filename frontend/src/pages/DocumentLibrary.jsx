import React from 'react';
import { useDropzone } from 'react-dropzone';
import { UploadCloud, File, Calendar, Database, AlignLeft } from 'lucide-react';
import { Card, Badge } from '../components/ui';

export function DocumentLibrary() {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: { 'application/pdf': ['.pdf'] }
  });

  const documents = [
    { id: 1, name: 'Structural_Audit_ABC.pdf', status: 'indexed', pages: 45, date: '2026-07-28', entities: 320 },
    { id: 2, name: 'CPWD_Maintenance_Manual.pdf', status: 'indexed', pages: 112, date: '2026-07-25', entities: 512 },
    { id: 3, name: 'Seismic_Retrofitting_Guide.pdf', status: 'processing', pages: 80, date: '2026-07-28', entities: 0 },
  ];

  return (
    <div className="p-8 max-w-7xl mx-auto w-full flex flex-col h-full space-y-8">
      <header className="shrink-0 flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Project Documents</h1>
          <p className="text-slate-500 mt-1 text-lg">Manage engineering guidelines, structural audits, and blueprints.</p>
        </div>
      </header>

      {/* Upload Zone */}
      <Card className="p-12 border-dashed border-2 border-blue-200 bg-blue-50/50 text-center cursor-pointer hover:bg-blue-50 hover:border-blue-300 transition-all shrink-0">
        <div {...getRootProps()} className="flex flex-col items-center justify-center outline-none">
          <input {...getInputProps()} />
          <UploadCloud className="w-16 h-16 text-blue-500 mb-4" />
          {isDragActive ? (
            <p className="text-xl font-bold text-blue-700">Drop the PDF here ...</p>
          ) : (
            <>
              <p className="text-xl font-bold text-slate-700 mb-2">Drag & drop engineering documents here</p>
              <p className="text-slate-500 font-medium">Only PDF files are supported. Max 50MB.</p>
            </>
          )}
        </div>
      </Card>

      {/* Document List */}
      <div className="flex-1 overflow-y-auto">
        <h3 className="text-xl font-bold text-slate-900 mb-6">Indexed Documents</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pb-8">
          {documents.map(doc => (
            <Card key={doc.id} hover className="flex flex-col h-full cursor-pointer">
              <div className="p-6 flex-1">
                <div className="flex items-start gap-4 mb-4">
                  <div className="p-3 bg-slate-100 rounded-xl text-slate-400 shrink-0 border border-slate-200">
                    <File className="w-8 h-8" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="font-bold text-slate-900 truncate mb-2" title={doc.name}>{doc.name}</h4>
                    <Badge variant={doc.status === 'indexed' ? 'success' : 'warning'}>
                      {doc.status.toUpperCase()}
                    </Badge>
                  </div>
                </div>
              </div>
              
              <div className="p-4 bg-slate-50 border-t border-slate-100 grid grid-cols-2 gap-4 text-sm text-slate-500">
                <div className="flex items-center gap-2">
                  <AlignLeft className="w-4 h-4 text-slate-400" />
                  <span className="font-semibold">{doc.pages} Pages</span>
                </div>
                <div className="flex items-center gap-2">
                  <Database className="w-4 h-4 text-slate-400" />
                  <span className="font-semibold">{doc.entities} Entities</span>
                </div>
                <div className="col-span-2 flex items-center gap-2 pt-2 border-t border-slate-200/60 mt-1">
                  <Calendar className="w-4 h-4 text-slate-400" />
                  <span className="font-medium">Uploaded {new Date(doc.date).toLocaleDateString()}</span>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
