import React, { useState } from 'react';
import { Upload, FileText, CheckCircle, AlertCircle } from 'lucide-react';
import { useMutation } from '@tanstack/react-query';
import apiClient from '../api/client';

export function AdminUpload() {
  const [file, setFile] = useState(null);
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('IS/BIS Codes');
  const [uploadStatus, setUploadStatus] = useState(null); // 'success' | 'error' | null

  const uploadMutation = useMutation({
    mutationFn: async (formData) => {
      const res = await apiClient.post('/acquisition/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return res.data;
    },
    onSuccess: () => {
      setUploadStatus('success');
      setFile(null);
      setTitle('');
    },
    onError: () => {
      setUploadStatus('error');
    }
  });

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = (e) => {
    e.preventDefault();
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    if (title) formData.append('title', title);
    formData.append('category', category);
    formData.append('source', 'admin_upload');

    uploadMutation.mutate(formData);
  };

  return (
    <div className="flex-1 overflow-y-auto bg-slate-50 p-8">
      <div className="max-w-3xl mx-auto space-y-8">
        <div>
          <h1 className="text-3xl font-light text-slate-900 tracking-tight">Administrator Document Upload</h1>
          <p className="text-slate-500 mt-1">Legally upload proprietary codes, manuals, and technical data sheets into the review queue.</p>
        </div>

        <form onSubmit={handleUpload} className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-6">
          
          {uploadStatus === 'success' && (
            <div className="p-4 bg-green-50 border border-green-200 rounded-lg flex items-center gap-3 text-green-700">
              <CheckCircle className="w-5 h-5" />
              <p className="font-medium">Document uploaded successfully to the Review Queue!</p>
            </div>
          )}

          {uploadStatus === 'error' && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3 text-red-700">
              <AlertCircle className="w-5 h-5" />
              <p className="font-medium">Failed to upload document. Please try again.</p>
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Document Title (Optional)</label>
              <input 
                type="text" 
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Leave blank to use filename"
                className="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Document Category</label>
              <select 
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
              >
                <option value="IS/BIS Codes">IS/BIS Codes</option>
                <option value="NBC Documents">NBC Documents</option>
                <option value="CPWD Manuals">CPWD Manuals</option>
                <option value="FEMA/NIST Reports">FEMA/NIST Reports</option>
                <option value="Manufacturer TDS">Manufacturer Technical Data Sheets</option>
                <option value="Case Studies">Case Studies</option>
                <option value="Inspection Reports">Inspection Reports</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Select PDF File</label>
              <label className="flex flex-col items-center justify-center w-full h-32 px-4 transition bg-slate-50 border-2 border-slate-300 border-dashed rounded-xl hover:bg-slate-100 hover:border-slate-400 cursor-pointer">
                <span className="flex items-center space-x-2">
                  <Upload className="w-6 h-6 text-slate-400" />
                  <span className="font-medium text-slate-600">
                    {file ? file.name : 'Drop PDF here or click to browse'}
                  </span>
                </span>
                <input type="file" name="file" className="hidden" accept=".pdf" onChange={handleFileChange} />
              </label>
            </div>
          </div>

          <div className="flex justify-end pt-4 border-t border-slate-100">
            <button 
              type="submit" 
              disabled={!file || uploadMutation.isPending}
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {uploadMutation.isPending ? 'Uploading...' : 'Upload to Queue'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
