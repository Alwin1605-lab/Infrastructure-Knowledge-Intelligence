import apiClient from './client';

export const authApi = {
  login: async (email, password) => {
    const formData = new URLSearchParams();
    formData.append('username', email); // OAuth2 requires username field
    formData.append('password', password);
    
    return apiClient.post('/api/v1/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
  },
  
  signup: async (userData) => {
    return apiClient.post('/api/v1/auth/signup', userData);
  },
  
  logout: async () => {
    return apiClient.post('/api/v1/auth/logout');
  },
  
  refreshToken: async () => {
    return apiClient.post('/api/v1/auth/refresh-token');
  },
  
  me: async () => {
    return apiClient.get('/api/v1/auth/me');
  }
};
