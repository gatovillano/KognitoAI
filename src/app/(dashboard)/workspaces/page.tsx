'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Plus, FolderKanban } from 'lucide-react';
import apiClient from '@/lib/api';
import { WorkspaceDialog } from './workspace-dialog';

interface Workspace {
  id: string;
  name: string;
  system_prompt: string | null;
}

export default function WorkspacesPage() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [selectedWorkspace, setSelectedWorkspace] = useState<Workspace | null>(null);
  const router = useRouter();

  useEffect(() => {
    fetchWorkspaces();
  }, []);

  const fetchWorkspaces = async () => {
    try {
      const response = await apiClient.get<Workspace[]>('/api/workspaces');
      setWorkspaces(response.data);
    } catch (error) {
      console.error('Error fetching workspaces:', error);
    }
  };

  const handleCardClick = (workspaceId: string) => {
    router.push(`/workspaces/${workspaceId}`);
  };

  const handleEdit = (workspace: Workspace) => {
    setSelectedWorkspace(workspace);
    setIsDialogOpen(true);
  };

  const handleDelete = async (workspaceId: string) => {
    try {
      await apiClient.delete(`/api/workspaces/${workspaceId}`);
      fetchWorkspaces();
    } catch (error) {
      console.error('Error deleting workspace:', error);
    }
  };

  return (
    <div className="p-4 md:p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold flex items-center">
            <FolderKanban className="mr-2 h-8 w-8 text-primary" />
            Workspaces
        </h1>
        <Button onClick={() => {
          setSelectedWorkspace(null);
          setIsDialogOpen(true);
        }}>
          <Plus className="mr-2 h-4 w-4" />
          Nuevo Workspace
        </Button>
      </div>
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {workspaces.map((workspace) => (
          <Card key={workspace.id} className="cursor-pointer hover:shadow-lg transition-shadow" onClick={() => handleCardClick(workspace.id)}>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                {workspace.name}
                <div className="flex items-center gap-2">
                  <Button variant="ghost" size="icon" onClick={(e) => { e.stopPropagation(); handleEdit(workspace); }}>
                    ...
                  </Button>
                  <Button variant="ghost" size="icon" onClick={(e) => { e.stopPropagation(); handleDelete(workspace.id); }}>
                    X
                  </Button>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                {workspace.system_prompt ? `${workspace.system_prompt.substring(0, 100)}...` : 'Sin prompt de sistema'}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>
      <WorkspaceDialog
        isOpen={isDialogOpen}
        onClose={() => setIsDialogOpen(false)}
        onSuccess={fetchWorkspaces}
        workspace={selectedWorkspace}
      />
    </div>
  );
}
