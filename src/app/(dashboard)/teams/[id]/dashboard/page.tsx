"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from 'next/link';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Users, ArrowLeft, BookMarked, Calendar, Notebook } from "lucide-react";
import apiClient from "@/lib/api";
import { toast } from "sonner";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";
import { InlineMarkdownRenderer } from "@/components/InlineMarkdownRenderer";

export default function TeamDashboardPage() {
  const params = useParams();
  const router = useRouter();
  const teamId = params?.id as string;
  const [team, setTeam] = useState<any>(null);
  const [sharedItems, setSharedItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [editMode, setEditMode] = useState(false);

  useEffect(() => {
    const fetchTeamData = async () => {
      setLoading(true);
      try {
        // Fetch all teams and find the specific one
        const teamsResponse = await apiClient.get(`/api/teams`);
        const foundTeam = teamsResponse.data.find((t: any) => t.id === teamId);
        if (foundTeam) {
          setTeam(foundTeam);
        } else {
          toast.error("Equipo no encontrado.");
          router.push("/teams");
          return;
        }
        
        // Fetch shared items directly associated with this team using the new endpoint
        const sharedItemsResponse = await apiClient.get(`/api/teams/${teamId}/shared-items`);
        
        // Log response data for debugging
        console.log("Using new endpoint to fetch shared items for Team ID " + teamId + ":", sharedItemsResponse.data);
        
        // Combine items, marking them with their type and shared date
        const combinedItems = (sharedItemsResponse.data || []).map((item: any) => {
          if (item.type === 'document') {
            return { ...item, type: 'Documento', shared_at: item.updated_at || item.created_at };
          } else if (item.type === 'event') {
            return { ...item, type: 'Evento', title: item.description, shared_at: item.updated_at || item.created_at };
          } else if (item.type === 'note') {
            return { ...item, type: 'Nota', shared_at: item.updated_at || item.created_at };
          }
          return item;
        });
        
        // Set the shared items for this team
        setSharedItems(combinedItems);
      } catch (error) {
        toast.error("Error al cargar los datos del equipo.");
        console.error(error);
      } finally {
        setLoading(false);
      }
    };
    fetchTeamData();
  }, [teamId, router]);

  const handleEditTeam = () => {
    setEditMode(true);
    // Placeholder for future implementation to manage team members
    toast.info("Función para gestionar miembros del equipo aún no implementada.");
  };

  const handleBack = () => {
    router.push("/teams");
  };

  const [isNoteDialogOpen, setIsNoteDialogOpen] = useState(false);
  const [selectedNote, setSelectedNote] = useState<any>(null);
  const [isDocumentDialogOpen, setIsDocumentDialogOpen] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState<any>(null);
  const [documentContent, setDocumentContent] = useState<string>('');
  const [isLoadingContent, setIsLoadingContent] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [isAnalysisResultDialogOpen, setIsAnalysisResultDialogOpen] = useState(false);
  const [analysisTaskId, setAnalysisTaskId] = useState<string | null>(null);

  useEffect(() => {
    const fetchDocumentContent = async () => {
      if (selectedDocument) {
        setIsLoadingContent(true);
        setDocumentContent('');
        try {
          const response = await apiClient.post('/api/get-document-content', { file_name: selectedDocument.file_name });
          setDocumentContent(response.data.content || 'No se pudo cargar el contenido de este documento.');
        } catch (error) {
          toast.error("Error al cargar el contenido del documento.");
          console.error(error);
          setDocumentContent('No se pudo cargar el contenido de este documento.');
        } finally {
          setIsLoadingContent(false);
        }
      }
    };
    if (isDocumentDialogOpen && selectedDocument) {
      fetchDocumentContent();
    }
  }, [selectedDocument, isDocumentDialogOpen]);

  useEffect(() => {
    const checkAnalysisStatus = async () => {
      if (analysisTaskId) {
        try {
          const response = await apiClient.get(`/api/get-analysis-result/${analysisTaskId}`);
          if (response.data.status === 'completed') {
            setAnalysisResult(response.data.result);
            setIsAnalysisResultDialogOpen(true);
            setAnalysisTaskId(null); // Reset task ID after completion
          } else if (response.data.status === 'failed') {
            toast.error("El análisis del documento falló: " + (response.data.error || 'Error desconocido'));
            setAnalysisTaskId(null); // Reset task ID on failure
          } else {
            // Continue polling if status is pending or processing
            setTimeout(checkAnalysisStatus, 3000); // Check again after 3 seconds
          }
        } catch (error) {
          toast.error("Error al verificar el estado del análisis.");
          console.error(error);
          setAnalysisTaskId(null); // Reset on error
        }
      }
    };
    if (analysisTaskId) {
      checkAnalysisStatus();
    }
  }, [analysisTaskId]);

  const handleAnalyzeDocument = async () => {
    if (!selectedDocument) return;
    setIsAnalyzing(true);
    try {
      const response = await apiClient.post('/api/start-document-analysis', { file_name: selectedDocument.file_name });
      toast.success(`Análisis iniciado. ID de tarea: ${response.data.task_id}`);
      setAnalysisTaskId(response.data.task_id);
    } catch (error) {
      toast.error("Error al iniciar el análisis del documento.");
      console.error(error);
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center">
          <Button variant="outline" size="icon" className="mr-4" onClick={handleBack}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            {team ? (
              <>
                <h1 className="text-3xl font-bold flex items-center">
                  {team.name}
                  <span title="Equipo">
                    <Users className="ml-2 h-5 w-5 text-blue-500" />
                  </span>
                </h1>
                <p className="text-muted-foreground">Dashboard del equipo</p>
              </>
            ) : (
              <h1 className="text-3xl font-bold">Cargando equipo...</h1>
            )}
          </div>
        </div>
        <Button onClick={handleEditTeam}>
          Editar
        </Button>
      </div>

      {loading ? (
        <div className="text-center py-10">
          <p className="text-muted-foreground">Cargando elementos compartidos...</p>
        </div>
      ) : sharedItems.length === 0 ? (
        <div className="rounded-md border-0 mt-6 p-8 text-center">
          <p className="text-muted-foreground">No hay elementos compartidos con este equipo. Es posible que aún no se hayan compartido recursos o que no estén disponibles para tu usuario.</p>
        </div>
      ) : (
        <div className="space-y-8">
          {/* Agenda Section */}
          <div>
            <h2 className="text-2xl font-bold mb-4 flex items-center">
              Agenda
              <Calendar className="ml-2 h-5 w-5 text-green-500" />
            </h2>
            {sharedItems.filter(item => item.type === 'Evento').length === 0 ? (
              <div className="rounded-md border-0 p-6 text-center">
                <p className="text-muted-foreground">No hay rueventos compartidos con este equipo. Es posible que aún no se hayan compartido eventos o que no estén disponibles para tu usuario.</p>
              </div>
            ) : (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {sharedItems.filter(item => item.type === 'Evento').map((item) => (
                  <Link 
                    href={`/agenda`} 
                    passHref
                    key={item.id}
                  >
                    <Card className="flex flex-col hover:border-primary/50 transition-colors cursor-pointer">
                      <CardHeader className="flex flex-row items-start justify-between pb-0">
                        <div>
                          <CardTitle className="flex items-center break-words">
                            {item.description || 'Sin título'}
                          </CardTitle>
                          <CardDescription>{item.type}</CardDescription>
                        </div>
                      </CardHeader>
                      <CardContent className="p-4 pt-2 flex-grow">
                        <p className="text-sm text-muted-foreground line-clamp-4">
                          {item.content || item.summary || 'Sin contenido'}
                        </p>
                      </CardContent>
                      <CardFooter className="flex justify-between items-center">
                        <p className="text-xs text-muted-foreground">
                          Compartido: {new Date(item.shared_at || item.created_at).toLocaleDateString()}
                        </p>
                        <div className="ml-2">
                          <Calendar className="h-4 w-4 text-green-500" />
                        </div>
                      </CardFooter>
                    </Card>
                  </Link>
                ))}
              </div>
            )}
          </div>

          {/* Notas Section */}
          <div>
            <h2 className="text-2xl font-bold mb-4 flex items-center">
              Notas
              <Notebook className="ml-2 h-5 w-5 text-yellow-500" />
            </h2>
            {sharedItems.filter(item => item.type === 'Nota').length === 0 ? (
              <div className="rounded-md border-0 p-6 text-center">
                <p className="text-muted-foreground">No hay notas compartidas con este equipo. Es posible que aún no se hayan compartido notas o que no estén disponibles para tu usuario.</p>
              </div>
            ) : (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {sharedItems.filter(item => item.type === 'Nota').map((item) => (
                  <Card 
                    key={item.id} 
                    className="flex flex-col hover:border-primary/50 transition-colors cursor-pointer"
                    onClick={() => {
                      setSelectedNote(item);
                      setIsNoteDialogOpen(true);
                    }}
                  >
                    <CardHeader className="flex flex-row items-start justify-between pb-0">
                      <div>
                        <CardTitle className="flex items-center break-words">
                          {item.title || 'Sin título'}
                        </CardTitle>
                        <CardDescription>{item.type}</CardDescription>
                      </div>
                    </CardHeader>
                    <CardContent className="p-4 pt-2 flex-grow">
                      <div className="text-sm text-muted-foreground line-clamp-4">
                        {item.content ? (
                          <InlineMarkdownRenderer content={item.content} />
                        ) : (
                          <p>Sin contenido</p>
                        )}
                      </div>
                    </CardContent>
                    <CardFooter className="flex justify-between items-center">
                      <p className="text-xs text-muted-foreground">
                        Compartido por: {item.shared_by || "Usuario desconocido"}
                      </p>
                      <div className="ml-2">
                        <Notebook className="h-4 w-4 text-yellow-500" />
                      </div>
                    </CardFooter>
                  </Card>
                ))}
              </div>
            )}
          </div>

          {/* Documentos Section */}
          <div>
            <h2 className="text-2xl font-bold mb-4 flex items-center">
              Documentos
              <BookMarked className="ml-2 h-5 w-5 text-blue-500" />
            </h2>
            {sharedItems.filter(item => item.type === 'Documento').length === 0 ? (
              <div className="rounded-md border-0 p-6 text-center">
                <p className="text-muted-foreground">No hay documentos compartidos con este equipo. Es posible que aún no se hayan compartido documentos o que no estén disponibles para tu usuario.</p>
              </div>
            ) : (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {sharedItems.filter(item => item.type === 'Documento').map((item) => (
                  <Card 
                    key={item.id} 
                    className="flex flex-col hover:border-primary/50 transition-colors cursor-pointer"
                    onClick={() => {
                      setSelectedDocument(item);
                      setIsDocumentDialogOpen(true);
                    }}
                  >
                    <CardHeader className="flex flex-row items-start justify-between pb-0">
                      <div>
                        <CardTitle className="flex items-center break-words">
                          {item.title || 'Sin título'}
                        </CardTitle>
                        <CardDescription>{item.type}</CardDescription>
                      </div>
                    </CardHeader>
                    <CardContent className="p-4 pt-2 flex-grow">
                      <p className="text-sm text-muted-foreground line-clamp-4">
                        {item.content || item.summary || 'Sin contenido disponible'}
                      </p>
                    </CardContent>
                      <CardFooter className="flex justify-between items-center">
                        <p className="text-xs text-muted-foreground">
                          Compartido por: {item.shared_by || "Usuario desconocido"}
                        </p>
                        <div className="ml-2">
                          <Calendar className="h-4 w-4 text-green-500" />
                        </div>
                      </CardFooter>
                    <CardFooter className="flex justify-between items-center">
                      <p className="text-xs text-muted-foreground">
                        Compartido por: {item.shared_by || "Usuario desconocido"}
                      </p>
                      <div className="ml-2">
                        <BookMarked className="h-4 w-4 text-blue-500" />
                      </div>
                    </CardFooter>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Dialog for viewing note content */}
      <Dialog open={isNoteDialogOpen} onOpenChange={setIsNoteDialogOpen}>
        <DialogContent className="sm:max-w-[600px] max-h-[80vh] overflow-y-auto">
          {selectedNote && (
            <div className="space-y-4">
              <h3 className="text-xl font-bold">{selectedNote.title || 'Sin título'}</h3>
              <div className="prose max-w-none">
                <MarkdownRenderer content={selectedNote.content || 'Sin contenido'} />
              </div>
              <div className="flex justify-end mt-4">
                <Button 
                  variant="outline" 
                  onClick={() => setIsNoteDialogOpen(false)}
                  className="mr-2"
                >
                  Cerrar
                </Button>
                <Link href={`/notes/edit/${selectedNote.id}?fromTeam=${teamId}`} passHref>
                  <Button onClick={() => setIsNoteDialogOpen(false)}>
                    Editar
                  </Button>
                </Link>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Dialog for viewing document content */}
      <Dialog open={isDocumentDialogOpen} onOpenChange={setIsDocumentDialogOpen}>
        <DialogContent className="sm:max-w-[600px] max-h-[80vh] overflow-y-auto">
          {selectedDocument && (
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <h3 className="text-xl font-bold">{selectedDocument.title || 'Sin título'}</h3>
                <Button 
                  onClick={handleAnalyzeDocument} 
                  disabled={isAnalyzing || analysisTaskId !== null}
                >
                  {isAnalyzing ? 'Analizando...' : 'Analizar Documento'}
                </Button>
              </div>
              <div className="prose max-w-none">
                {isLoadingContent ? (
                  <p className="text-muted-foreground">Cargando contenido...</p>
                ) : (
                  <MarkdownRenderer content={documentContent} />
                )}
              </div>
              <div className="flex justify-end mt-4">
                <Button 
                  variant="outline" 
                  onClick={() => setIsDocumentDialogOpen(false)}
                >
                  Cerrar
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Dialog for viewing analysis results */}
      <Dialog open={isAnalysisResultDialogOpen} onOpenChange={setIsAnalysisResultDialogOpen}>
        <DialogContent className="max-w-2xl">
          {analysisResult && (
            <div className="space-y-6">
              <div>
                <h3 className="font-semibold mb-2">Resumen Ejecutivo por IA</h3>
                <p className="text-sm text-muted-foreground p-3 bg-muted rounded-md whitespace-pre-wrap">
                  {analysisResult?.executive_summary || 'No hay resumen disponible'}
                </p>
              </div>
              <div>
                <h3 className="font-semibold mb-2">Temas Clave Avanzados</h3>
                <div className="flex flex-wrap gap-2">
                  {analysisResult?.key_themes?.map((topic: string) => (
                    <Badge key={topic} className="text-black">{topic}</Badge>
                  ))}
                </div>
              </div>
              <div>
                <h3 className="font-semibold mb-2">Preguntas para Explorar</h3>
                <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                  {analysisResult?.knowledge_gaps?.map((question: string, i: number) => (
                    <li key={i}>{question}</li>
                  ))}
                </ul>
              </div>
              <div className="flex justify-end mt-4">
                <Button 
                  variant="outline" 
                  onClick={() => setIsAnalysisResultDialogOpen(false)}
                >
                  Cerrar
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
