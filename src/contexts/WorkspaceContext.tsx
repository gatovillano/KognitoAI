// En: src/contexts/WorkspaceContext.tsx
'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import apiClient from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';

interface Workspace {
  id: string;
  name: string;
  owner_id: string;
}

interface WorkspaceContextType {
  workspaces: Workspace[];
  currentWorkspace: Workspace | null;
  setCurrentWorkspace: (workspace: Workspace | null) => void;
  isLoading: boolean;
  refreshWorkspaces: () => Promise<void>;
}

const WorkspaceContext = createContext<WorkspaceContextType | undefined>(undefined);

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const { user, token } = useAuth();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [currentWorkspace, setCurrentWorkspaceState] = useState<Workspace | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshWorkspaces = useCallback(async () => {
    if (user && token) {
      try {
        setIsLoading(true);
        const response = await apiClient.get('/api/workspaces', {
          headers: { Authorization: `Bearer ${token}` },
        });
        setWorkspaces(response.data);

        const storedWorkspaceId = localStorage.getItem('currentWorkspaceId');
        const workspacesData = Array.isArray(response.data) ? response.data : [];
        const workspaceToSet = workspacesData.find((ws: Workspace) => ws.id === storedWorkspaceId) || workspacesData[0] || null;
        
        setCurrentWorkspaceState(workspaceToSet);
        if (workspaceToSet) {
          localStorage.setItem('currentWorkspaceId', workspaceToSet.id);
        }

      } catch (error) {
        console.error('Failed to fetch workspaces', error);
        setWorkspaces([]);
        setCurrentWorkspaceState(null);
      } finally {
        setIsLoading(false);
      }
    } else {
      setWorkspaces([]);
      setCurrentWorkspaceState(null);
      setIsLoading(false);
    }
  }, [user, token]);

  useEffect(() => {
    refreshWorkspaces();
  }, [refreshWorkspaces]);

  const setCurrentWorkspace = (workspace: Workspace | null) => {
    setCurrentWorkspaceState(workspace);
    if (workspace) {
      localStorage.setItem('currentWorkspaceId', workspace.id);
    } else {
      localStorage.removeItem('currentWorkspaceId');
    }
  };

  const value = { workspaces, currentWorkspace, setCurrentWorkspace, isLoading, refreshWorkspaces };

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace() {
  const context = useContext(WorkspaceContext);
  if (context === undefined) {
    throw new Error('useWorkspace must be used within a WorkspaceProvider');
  }
  return context;
}
