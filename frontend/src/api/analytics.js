import apiClient from './client';

export const analyticsApi = {
  getKB: () => apiClient.get('/analytics/kb'),
  getQueries: () => apiClient.get('/analytics/queries'),
};
