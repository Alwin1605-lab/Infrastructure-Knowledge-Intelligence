import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { documentsApi } from '../api/documents';
import toast from 'react-hot-toast';

export const useDocuments = (params = {}) => {
  return useQuery({
    queryKey: ['documents', params],
    queryFn: async () => {
      const { data } = await documentsApi.list(params);
      return data;
    },
    keepPreviousData: true,
  });
};

export const useDocument = (id) => {
  return useQuery({
    queryKey: ['documents', id],
    queryFn: async () => {
      const { data } = await documentsApi.get(id);
      return data;
    },
    enabled: !!id,
  });
};

export const useDocumentStats = () => {
  return useQuery({
    queryKey: ['documents', 'stats'],
    queryFn: async () => {
      const { data } = await documentsApi.getStats();
      return data;
    },
    staleTime: 60000,
  });
};

export const useUploadDocument = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (formData) => {
      const { data } = await documentsApi.uploadAsync(formData);
      return data;
    },
    onSuccess: () => {
      toast.success('Document upload started');
      // Invalidate to refresh the queue and document list
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['processing_jobs'] });
    },
    onError: (error) => {
      toast.error(error.response?.data?.message || 'Failed to upload document');
    }
  });
};

export const useProcessingJobs = (params = {}) => {
  return useQuery({
    queryKey: ['processing_jobs', params],
    queryFn: async () => {
      const { data } = await documentsApi.listJobs(params);
      return data;
    },
    // Poll every 5 seconds if there are running jobs
    refetchInterval: (data) => {
      if (!data) return false;
      const hasActiveJobs = data.jobs?.some(job => ['queued', 'running'].includes(job.status));
      return hasActiveJobs ? 5000 : false;
    }
  });
};

export const useDeleteDocument = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (id) => {
      const { data } = await documentsApi.delete(id);
      return data;
    },
    onSuccess: () => {
      toast.success('Document deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
    onError: (error) => {
      toast.error(error.response?.data?.message || 'Failed to delete document');
    }
  });
};
