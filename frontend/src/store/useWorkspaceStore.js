import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export const useWorkspaceStore = create(
  persist(
    (set, get) => ({
      workspaces: [
        {
          id: 'ws-1',
          name: 'ABC Apartment Complex',
          description: 'Structural inspection and maintenance planning for 12-story residential building.',
          createdAt: new Date().toISOString(),
          lastAccessed: new Date().toISOString(),
          status: 'Active',
          type: 'Residential',
          documentsCount: 4,
          reportsCount: 1,
        },
        {
          id: 'ws-2',
          name: 'City General Hospital',
          description: 'Seismic retrofitting assessment and ASCE 41-17 compliance.',
          createdAt: new Date(Date.now() - 86400000).toISOString(),
          lastAccessed: new Date(Date.now() - 3600000).toISOString(),
          status: 'Under Review',
          type: 'Healthcare',
          documentsCount: 12,
          reportsCount: 3,
        },
      ],
      currentWorkspaceId: 'ws-1',
      
      setCurrentWorkspace: (id) => set({ currentWorkspaceId: id }),
      
      addWorkspace: (workspace) => set((state) => ({
        workspaces: [
          {
            id: `ws-${Date.now()}`,
            createdAt: new Date().toISOString(),
            lastAccessed: new Date().toISOString(),
            documentsCount: 0,
            reportsCount: 0,
            ...workspace
          },
          ...state.workspaces,
        ]
      })),
      
      updateWorkspace: (id, updates) => set((state) => ({
        workspaces: state.workspaces.map(ws => 
          ws.id === id ? { ...ws, ...updates } : ws
        )
      })),
      
      deleteWorkspace: (id) => set((state) => ({
        workspaces: state.workspaces.filter(ws => ws.id !== id),
        currentWorkspaceId: state.currentWorkspaceId === id ? null : state.currentWorkspaceId
      })),
      
      getCurrentWorkspace: () => {
        const state = get();
        return state.workspaces.find(ws => ws.id === state.currentWorkspaceId) || null;
      }
    }),
    {
      name: 'engineering-workspaces-storage',
    }
  )
);
