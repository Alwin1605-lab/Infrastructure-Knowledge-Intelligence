import apiClient from './client';

export const acquisitionApi = {
  getQueue: () => apiClient.get('/acquisition/queue'),
  search: (query, connectorType, author, year, journal) => apiClient.post('/acquisition/search', { 
    query, 
    connector_type: connectorType,
    author,
    year,
    journal
  }),
  importDoi: (doi) => apiClient.post('/acquisition/import/doi', { doi }),
  batchImport: (documents) => apiClient.post('/acquisition/import/batch', { documents }),
  approveDownload: (id) => apiClient.put(`/acquisition/queue/${id}/approve-download`),
  approveIndex: (id) => apiClient.put(`/acquisition/queue/${id}/approve-index`),
  reject: (id) => apiClient.put(`/acquisition/queue/${id}/reject`),
  getGaps: () => apiClient.get('/acquisition/gaps'),
};
