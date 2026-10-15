import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { workspacesApi } from '../api/workspaces';
import toast from 'react-hot-toast';

export const useWorkspaces = () => {
  return useQuery({
    queryKey: ['workspaces'],
    queryFn: async () => {
      const { data } = await workspacesApi.list();
      return data;
    }
  });
};

export const useWorkspace = (id) => {
  return useQuery({
    queryKey: ['workspaces', id],
    queryFn: async () => {
      const { data } = await workspacesApi.get(id);
      return data;
    },
    enabled: !!id,
  });
};

export const useCreateWorkspace = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (workspaceData) => {
      const { data } = await workspacesApi.create(workspaceData);
      return data;
    },
    onSuccess: () => {
      toast.success('Workspace created successfully');
      queryClient.invalidateQueries({ queryKey: ['workspaces'] });
    },
    onError: (error) => {
      toast.error(error.response?.data?.message || 'Failed to create workspace');
    }
  });
};

export const useDeleteWorkspace = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (id) => {
      const { data } = await workspacesApi.delete(id);
      return data;
    },
    onSuccess: () => {
      toast.success('Workspace deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['workspaces'] });
    },
    onError: (error) => {
      toast.error(error.response?.data?.message || 'Failed to delete workspace');
    }
  });
};
