import axios from 'axios';

// Base Axios instance
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Generic error handler
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// Engineering Assistant API (Phase 6)
export const agentsApi = {
  query: async ({ question, top_k = 5 }) => {
    return api.post('/agents/query', { question, top_k });
  },
};

// Hybrid RAG API (Phase 5 - fallback if needed)
export const chatApi = {
  query: async ({ question, top_k = 5, include_kg = true }) => {
    return api.post('/chat/query', { question, top_k, include_kg });
  },
};

// Evaluation API (Phase 7)
export const evalApi = {
  benchmark: async ({ category, top_k = 5 }) => {
    return api.post('/eval/benchmark', { category, top_k });
  },
  history: async () => {
    return api.get('/eval/history');
  },
  ablation: async ({ question, top_k = 5 }) => {
    return api.post('/eval/ablation', { question, top_k });
  },
};

// System Health / Monitoring API (Built-in FastAPI & custom)
export const systemApi = {
  health: async () => {
    try {
        const response = await api.get('/health/system');
        return response;
    } catch {
        return { status: "error" };
    }
  },
};
