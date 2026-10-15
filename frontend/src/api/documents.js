import apiClient from './client';

export const documentsApi = {
  list: (params = {}) => apiClient.get('/documents', { params }),
  get: (id) => apiClient.get(`/documents/${id}`),
  delete: (id) => apiClient.delete(`/documents/${id}`),
  getStats: () => apiClient.get('/documents/stats'),
  listJobs: (params = {}) => apiClient.get('/documents/jobs', { params }),
  getJob: (jobId) => apiClient.get(`/documents/jobs/${jobId}`),
  uploadAsync: (formData) => apiClient.post('/documents/upload-async', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  // Legacy sync upload
  upload: (formData) => apiClient.post('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
};
