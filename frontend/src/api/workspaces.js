import apiClient from './client';

export const workspacesApi = {
  list: async () => {
    return apiClient.get('/workspaces');
  },
  
  get: async (id) => {
    return apiClient.get(`/workspaces/${id}`);
  },
  
  create: async (workspaceData) => {
    return apiClient.post('/workspaces', workspaceData);
  },
  
  delete: async (id) => {
    return apiClient.delete(`/workspaces/${id}`);
  },
  
  uploadDocument: async (workspaceId, file, documentType = 'General') => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);
    
    return apiClient.post(`/workspaces/${workspaceId}/documents/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  }
};
