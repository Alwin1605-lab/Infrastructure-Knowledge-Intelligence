/**
 * Axios HTTP client instance for the Infrastructure Knowledge Intelligence API.
 *
 * Pre-configured with:
 * - Base URL from environment variable (VITE_API_BASE_URL)
 * - 30-second request timeout
 * - JSON content type headers
 * - Request logging in development mode
 * - Centralized error response handling
 *
 * @module api/client
 */

import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// Request interceptor - logs outgoing requests in development
apiClient.interceptors.request.use(
  (config) => {
    if (import.meta.env.DEV) {
      console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    }
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - centralizes error handling and logging
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    // Attempt refresh if 401 Unauthorized
    if (error.response?.status === 401 && !originalRequest._retry && originalRequest.url !== '/api/v1/auth/login' && originalRequest.url !== '/api/v1/auth/refresh-token') {
      originalRequest._retry = true;
      try {
        const { data } = await axios.post(`${apiClient.defaults.baseURL}/api/v1/auth/refresh-token`, {}, { withCredentials: true });
        localStorage.setItem('access_token', data.access_token);
        apiClient.defaults.headers.common['Authorization'] = `Bearer ${data.access_token}`;
        originalRequest.headers['Authorization'] = `Bearer ${data.access_token}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        // Refresh failed, clear session
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    const message =
      error.response?.data?.message || error.response?.data?.detail || error.message || 'An unexpected error occurred';
    console.error(`[API Error] ${message}`);
    return Promise.reject(error);
  }
);

export default apiClient;
