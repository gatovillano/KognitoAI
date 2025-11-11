'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Plus, Bot, Info, Share2 } from 'lucide-react';
import apiClient from '@/lib/api';
import { WorkspaceDialog } from './workspace-dialog';
import { ShareWorkspaceDialog } from './ShareWorkspaceDialog'; // Importar el nuevo componente
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet'; // Importar Sheet
import { LoadingSpinner } from '@/components/LoadingSpinner';

interface Workspace {
  id: string;
  name: string;
  system_prompt: string | null;
  color: string | null;
  role: string;
}

interface PaginatedWorkspacesResponse {
  total: number;
  workspaces: Workspace[];
}

export default function WorkspacesPage() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [selectedWorkspace, setSelectedWorkspace] = useState<Workspace | null>(null);
  const [isShareDialogOpen, setIsShareDialogOpen] = useState(false); // Estado para el diálogo de compartir
  const [selectedWorkspaceForShare, setSelectedWorkspaceForShare] = useState<{ id: string; name: string } | null>(null); // Estado para el workspace a compartir
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(9); // Puedes ajustar esto según tus necesidades
  const [totalPages, setTotalPages] = useState(0);
  const [loading, setLoading] = useState(true); // Añadir estado de carga
  const [isInfoSheetOpen, setIsInfoSheetOpen] = useState(false); // Nuevo estado para controlar la visibilidad del Sheet
  const router = useRouter();

  const fetchWorkspaces = useCallback(async () => {
    setLoading(true); // Iniciar carga
    try {
      const skip = (currentPage - 1) * itemsPerPage;
      const response = await apiClient.get<PaginatedWorkspacesResponse>(`/api/workspaces?skip=${skip}&limit=${itemsPerPage}`);
      console.log('Fetched paginated workspaces:', response.data);
      setWorkspaces(response.data.workspaces);
      setTotalPages(Math.ceil(response.data.total / itemsPerPage));
    } catch (error) {
      console.error('Error fetching workspaces:', error);
    } finally {
      setLoading(false); // Finalizar carga
    }
  }, [currentPage, itemsPerPage]);

  useEffect(() => {
    fetchWorkspaces();
  }, [currentPage, fetchWorkspaces]);

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

  if (loading) { // Mostrar spinner mientras carga
    return <LoadingSpinner />;
  }

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold flex items-center">
            <Bot className="mr-3 h-8 w-8 text-primary" />
            Workspaces
            <Button variant="ghost" size="icon" className="ml-2 h-6 w-6 text-muted-foreground" onClick={() => setIsInfoSheetOpen(true)}>
              <Info className="h-4 w-4" />
            </Button>
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

      {workspaces.length === 0 ? ( // Si no hay workspaces después de cargar
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
        <>
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
                      {(workspace.role === 'owner' || workspace.role === 'editor') && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 w-8 p-0 hover:bg-muted"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedWorkspaceForShare({ id: workspace.id, name: workspace.name });
                            setIsShareDialogOpen(true);
                          }}
                          title="Compartir workspace"
                        >
                          <Share2 className="h-4 w-4" />
                        </Button>
                      )}
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
          {totalPages > 1 && (
            <div className="flex justify-center items-center space-x-2 mt-8">
              <Button
                variant="outline"
                onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
                disabled={currentPage === 1}
              >
                Anterior
              </Button>
              {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                <Button
                  key={page}
                  variant={currentPage === page ? "default" : "outline"}
                  onClick={() => setCurrentPage(page)}
                >
                  {page}
                </Button>
              ))}
              <Button
                variant="outline"
                onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
                disabled={currentPage === totalPages}
              >
                Siguiente
              </Button>
            </div>
          )}
        </>
      )}

      <WorkspaceDialog
        isOpen={isDialogOpen}
        onClose={() => setIsDialogOpen(false)}
        onSuccess={fetchWorkspaces}
        workspace={selectedWorkspace}
      />

      {selectedWorkspaceForShare && (
        <ShareWorkspaceDialog
          isOpen={isShareDialogOpen}
          onClose={() => setIsShareDialogOpen(false)}
          workspaceId={selectedWorkspaceForShare.id}
          workspaceName={selectedWorkspaceForShare.name}
          onPermissionsUpdated={fetchWorkspaces} // Recargar la lista de workspaces después de actualizar permisos
        />
      )}

      <Sheet open={isInfoSheetOpen} onOpenChange={setIsInfoSheetOpen}>
        <SheetContent side="right" className="w-full sm:max-w-md overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="text-xl font-bold text-primary">Módulo de Workspaces</SheetTitle>
            <SheetDescription className="text-sm text-muted-foreground">
              Organiza y gestiona tus espacios de trabajo personalizados con asistentes de IA.
            </SheetDescription>
          </SheetHeader>
          <div className="py-4 text-sm text-gray-700 dark:text-gray-300 space-y-4">
            <p><strong>¿Qué son los Workspaces?</strong></p>
            <p>Los workspaces son entornos aislados donde puedes configurar asistentes de IA con indicaciones de sistema específicas y gestionar colecciones de conocimientos exclusivas. Esto permite tener diferentes "personalidades" de IA y bases de conocimiento para distintas tareas o proyectos.</p>
            
            <p><strong>Características Principales:</strong></p>
            <ul className="list-disc pl-5 space-y-2">
              <li><strong>Asistentes Personalizados:</strong> Configura asistentes de IA con prompts de sistema únicos para cada workspace.</li>
              <li><strong>Conocimiento Aislado:</strong> Gestiona colecciones de conocimientos (documentos, notas, etc.) que son accesibles solo dentro de ese workspace.</li>
              <li><strong>Colaboración Segura:</strong> Comparte workspaces con equipos específicos, controlando el acceso a la información y las configuraciones.</li>
              <li><strong>Roles de Usuario:</strong> Asigna diferentes roles (propietario, editor, lector) a los miembros del equipo dentro de cada workspace.</li>
            </ul>

            <p><strong>Interacción con IA:</strong></p>
            <p>Los workspaces potencian la interacción con la IA al permitirte tener asistentes altamente especializados. Puedes:</p>
            <ul className="list-disc pl-5 space-y-2">
              <li>Interactuar con un asistente de IA que tiene un contexto y un propósito definidos por el workspace.</li>
              <li>Realizar búsquedas y análisis que solo utilizan la base de conocimiento de ese workspace.</li>
              <li>Generar contenido o resolver problemas con la IA, basándose en la información y la configuración específica del entorno.</li>
            </ul>

            <p><strong>Beneficios Clave:</strong></p>
            <ul className="list-disc pl-5 space-y-2">
              <li><strong>Contexto Controlado:</strong> Asegura que la IA opere con la información y el propósito correctos para cada tarea.</li>
              <li><strong>Flexibilidad:</strong> Adapta tus asistentes de IA a una amplia gama de necesidades y proyectos.</li>
              <li><strong>Privacidad y Seguridad:</strong> Mantén la información de diferentes proyectos o equipos separada y segura.</li>
              <li><strong>Productividad Aumentada:</strong> Mejora la eficiencia al tener asistentes de IA especializados a tu disposición.</li>
            </ul>

            <p>¡Crea workspaces para cada aspecto de tu vida profesional o personal y potencia tu experiencia con Kognito AI!</p>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
