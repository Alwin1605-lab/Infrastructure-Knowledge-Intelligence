import apiClient from './client';

export const searchApi = {
  search: (q, params = {}) => apiClient.get('/search', { params: { q, ...params } }),
  suggestions: (q) => apiClient.get('/search/suggestions', { params: { q } }),
};
