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
});

// Request interceptor - logs outgoing requests in development
apiClient.interceptors.request.use(
  (config) => {
    if (import.meta.env.DEV) {
      console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - centralizes error handling and logging
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.message || error.message || 'An unexpected error occurred';
    console.error(`[API Error] ${message}`);
    return Promise.reject(error);
  }
);

export default apiClient;
