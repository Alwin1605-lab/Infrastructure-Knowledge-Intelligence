import apiClient from '../api/client';

// Engineering Assistant API (Phase 6)
export const agentsApi = {
  query: async ({ question, top_k = 5 }) => {
    const response = await apiClient.post('/agents/query', { question, top_k });
    return response.data;
  },
};

// Hybrid RAG API (Phase 5 - fallback if needed)
export const chatApi = {
  query: async ({ question, top_k = 5, include_kg = true }) => {
    const response = await apiClient.post('/chat/query', { question, top_k, include_kg });
    return response.data;
  },
};

// Evaluation API (Phase 7)
export const evalApi = {
  benchmark: async ({ category, top_k = 5 }) => {
    const response = await apiClient.post('/eval/benchmark', { category, top_k });
    return response.data;
  },
  history: async () => {
    const response = await apiClient.get('/eval/history');
    return response.data;
  },
  ablation: async ({ question, top_k = 5 }) => {
    const response = await apiClient.post('/eval/ablation', { question, top_k });
    return response.data;
  },
};

// System Health / Monitoring API (Built-in FastAPI & custom)
export const systemApi = {
  health: async () => {
    try {
        const response = await apiClient.get('/health/system');
        return response.data;
    } catch {
        return { status: "error" };
    }
  },
};
