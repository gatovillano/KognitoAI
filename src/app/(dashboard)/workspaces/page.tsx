'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Plus, Bot, Info } from 'lucide-react';
import apiClient from '@/lib/api';
import { WorkspaceDialog } from './workspace-dialog';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

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
      console.log('Fetched workspaces:', response.data);
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
      console.log(`Workspace with ID ${workspaceId} deleted.`);
      fetchWorkspaces();
    } catch (error) {
      console.error('Error deleting workspace:', error);
    }
  };

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold flex items-center">
            <Bot className="mr-3 h-8 w-8 text-primary" />
            Workspaces
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon" className="ml-2 h-6 w-6 text-muted-foreground">
                    <Info className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent className="max-w-xs">
                  <p>Organiza y gestiona tus espacios de trabajo especializados. Crea un espacio con un asistente con sus propias indicaciones de sistema. Dentro podrás gestionar colecciones de conocimiento a las que tendrá acceso tu asistente de forma aislada del resto del contexto personal.</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </h1>
        </div>
        <Button size="lg" onClick={() => {
          setSelectedWorkspace(null);
          setIsDialogOpen(true);
        }} className="bg-primary hover:bg-primary/90">
          <Plus className="mr-2 h-5 w-5" />
          Nuevo Workspace
        </Button>
      </div>

      {workspaces.length === 0 ? (
        <div className="text-center py-16">
          <Bot className="mx-auto h-16 w-16 text-muted-foreground/50 mb-4" />
          <h3 className="text-xl font-semibold mb-2">No tienes workspaces aún</h3>
          <p className="text-muted-foreground mb-6 max-w-md mx-auto">
            Los workspaces te permiten crear espacios especializados con configuraciones específicas para diferentes tareas.
          </p>
          <Button onClick={() => {
            setSelectedWorkspace(null);
            setIsDialogOpen(true);
          }} size="lg">
            <Plus className="mr-2 h-5 w-5" />
            Crear tu primer Workspace
          </Button>
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {workspaces.map((workspace) => (
            <Card key={workspace.id} className="group cursor-pointer hover:shadow-xl hover:scale-[1.02] transition-all duration-200 border-2 hover:border-primary/20" onClick={() => handleCardClick(workspace.id)}>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                      <Bot className="h-5 w-5 text-primary" />
                    </div>
                    <span className="font-semibold text-lg truncate">{workspace.name}</span>
                  </div>
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="h-8 w-8 p-0 hover:bg-muted" 
                      onClick={(e) => { e.stopPropagation(); handleEdit(workspace); }}
                      title="Editar workspace"
                    >
                      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                      </svg>
                    </Button>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="h-8 w-8 p-0 hover:bg-destructive hover:text-destructive-foreground" 
                      onClick={(e) => { e.stopPropagation(); handleDelete(workspace.id); }}
                      title="Eliminar workspace"
                    >
                      <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </Button>
                  </div>
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="space-y-3">
                  <p className="text-sm text-muted-foreground line-clamp-3 leading-relaxed">
                    {workspace.system_prompt ? workspace.system_prompt : 'Sin prompt de sistema configurado'}
                  </p>
                  <div className="flex items-center justify-between pt-2 border-t border-border/50">
                    <span className="text-xs text-muted-foreground font-medium">
                      {workspace.system_prompt ? 'Configurado' : 'Sin configurar'}
                    </span>
                    <div className="flex items-center gap-1">
                      <div className={`h-2 w-2 rounded-full ${workspace.system_prompt ? 'bg-green-500' : 'bg-orange-400'}`}></div>
                      <span className="text-xs text-muted-foreground">
                        {workspace.system_prompt ? 'Activo' : 'Pendiente'}
                      </span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <WorkspaceDialog
        isOpen={isDialogOpen}
        onClose={() => setIsDialogOpen(false)}
        onSuccess={fetchWorkspaces}
        workspace={selectedWorkspace}
      />
    </div>
  );
}
