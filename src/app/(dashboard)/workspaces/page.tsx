'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Plus, Bot, Info, Share2, Briefcase } from 'lucide-react';
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
    <div className="p-2 sm:p-4 md:p-8 max-w-7xl mx-auto overflow-x-hidden">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold flex items-center">
            <Bot className="mr-3 h-6 w-6 sm:h-8 sm:w-8 text-primary" />
            Workspaces
            <Button variant="ghost" size="icon" className="ml-2 h-6 w-6 text-muted-foreground" onClick={() => setIsInfoSheetOpen(true)}>
              <Info className="h-4 w-4" />
            </Button>
          </h1>
        </div>
        <Button size="lg" onClick={() => {
          setSelectedWorkspace(null);
          setIsDialogOpen(true);
        }} className="w-full sm:w-auto bg-primary hover:bg-primary/90">
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
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
            {workspaces.map((workspace) => (
              <Card
                key={workspace.id}
                className="group relative cursor-pointer overflow-hidden border-border/40 bg-card/40 backdrop-blur-xl hover:bg-card/60 transition-all duration-500 h-[280px] flex flex-col shadow-sm hover:shadow-2xl hover:shadow-primary/5 hover:-translate-y-1"
                onClick={() => handleCardClick(workspace.id)}
              >
                {/* Efecto de reflejo en el hover */}
                <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" style={{ background: 'linear-gradient(135deg, hsl(var(--primary)/0.08) 0%, transparent 60%)' }} />

                <CardHeader className="pb-3 relative z-10">
                  <CardTitle className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3 min-w-0 flex-1">
                      <div
                        className="p-3 rounded-2xl border border-border/40 shadow-inner group-hover:scale-110 transition-transform duration-500 flex-shrink-0"
                        style={{
                          backgroundColor: workspace.color ? `${workspace.color}20` : 'hsl(var(--background)/0.5)',
                          borderColor: workspace.color ? `${workspace.color}40` : undefined,
                        }}
                      >
                        <Bot className="h-5 w-5" style={{ color: workspace.color || 'hsl(var(--primary))' }} />
                      </div>
                      <span className="font-bold text-lg line-clamp-2 group-hover:text-primary transition-colors leading-tight tracking-tight">{workspace.name}</span>
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

                <CardContent className="pt-0 flex-grow overflow-hidden relative z-10">
                  <div className="text-xs text-muted-foreground/80 line-clamp-4 leading-relaxed font-medium">
                    {workspace.system_prompt ? workspace.system_prompt : (
                      <span className="text-muted-foreground/60 italic">Sin prompt de sistema configurado</span>
                    )}
                  </div>
                </CardContent>

                <CardFooter className="flex justify-between items-center pt-3 mt-auto border-t border-border/20 relative z-10 text-[10px] font-bold text-muted-foreground/60 uppercase tracking-widest">
                  <div className="flex items-center gap-2">
                    <span>{workspace.role}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <div className={`h-1.5 w-1.5 rounded-full ${workspace.system_prompt ? 'bg-green-500' : 'bg-orange-400'}`} />
                    <span>{workspace.system_prompt ? 'Activo' : 'Pendiente'}</span>
                  </div>
                </CardFooter>
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
        <SheetContent side="right" className="w-[400px] sm:w-[540px] overflow-y-auto">
          <SheetHeader className="pb-6 border-b">
            <SheetTitle className="text-2xl font-bold flex items-center gap-2">
              <Briefcase className="h-6 w-6 text-primary" />
              Guía de Workspaces
            </SheetTitle>
            <SheetDescription>
              Espacios de trabajo inteligentes y segmentados.
            </SheetDescription>
          </SheetHeader>
          
          <div className="py-6 space-y-8">
            <section className="space-y-3">
              <h3 className="text-sm font-bold uppercase tracking-wider text-primary">¿Qué es un Workspace?</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Un Workspace es un ecosistema privado. Todo lo que sucede dentro (chats, documentos, tareas) está <strong>aislado</strong> del resto del sistema, permitiendo una organización impecable por proyectos o departamentos.
              </p>
            </section>

            <section className="space-y-3">
              <h3 className="text-sm font-bold uppercase tracking-wider text-primary">Personalidad del Agente</h3>
              <div className="bg-primary/5 rounded-2xl p-4 border border-primary/10 space-y-3">
                <p className="text-xs font-medium text-primary flex items-center gap-2">
                  <Bot className="h-4 w-4" /> Configuración Exclusiva:
                </p>
                <ul className="text-xs space-y-2 text-muted-foreground list-disc pl-4">
                  <li><strong>System Prompt:</strong> Define cómo debe actuar la IA en este espacio (ej: "Actúa como un experto contable").</li>
                  <li><strong>Contexto Especializado:</strong> El agente prioriza los archivos de este workspace para sus respuestas.</li>
                  <li><strong>Identidad Visual:</strong> Asigna colores únicos para identificar rápidamente en qué proyecto estás trabajando.</li>
                </ul>
              </div>
            </section>

            <section className="space-y-3">
              <h3 className="text-sm font-bold uppercase tracking-wider text-primary">Colaboración y Seguridad</h3>
              <div className="grid grid-cols-1 gap-2 text-[11px]">
                <div className="flex items-center gap-2 p-3 rounded-xl bg-green-500/5 text-green-600 border border-green-500/10">
                  <span className="font-bold">ROLES</span> Propietario, Edición o Solo Lectura para un control total.
                </div>
                <div className="flex items-center gap-2 p-3 rounded-xl bg-purple-500/5 text-purple-600 border border-purple-500/10">
                  <span className="font-bold">COMPARTIR</span> Invita a miembros de tu equipo a colaborar en tiempo real.
                </div>
              </div>
            </section>

            <section className="space-y-3">
              <h3 className="text-sm font-bold uppercase tracking-wider text-primary">Recomendación de Uso</h3>
              <p className="text-sm text-muted-foreground leading-relaxed italic">
                "Usa los Workspaces para separar clientes, proyectos de larga duración o incluso áreas personales. La IA será mucho más eficiente si tiene un contexto enfocado."
              </p>
            </section>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
