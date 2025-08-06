
'use client';

import { useState, useEffect, useCallback } from 'react';
import apiClient from '@/lib/api';

interface Workspace {
  id: string;
  name: string;
  document_count: number;
}

export const useWorkspaces = () => {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [currentWorkspace, setCurrentWorkspace] = useState<Workspace | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchWorkspaces = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.get('/api/workspaces');
      setWorkspaces(response.data);
      if (response.data.length > 0) {
        setCurrentWorkspace(response.data[0]);
      }
    } catch (error) {
      console.error('Error fetching workspaces:', error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchWorkspaces();
  }, [fetchWorkspaces]);

  return { workspaces, currentWorkspace, isLoading, fetchWorkspaces };
};
