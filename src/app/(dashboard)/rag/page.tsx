// En: src/app/(dashboard)/rag/page.tsx

'use client';

import { useEffect, useState, useCallback, useMemo } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Badge } from '@/components/ui/badge';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { PlusCircle, FolderKanban, MoreVertical, ScanSearch, Loader2, Library, BookMarked, Github, Plus } from 'lucide-react';

import { UploadDocumentDialog } from './upload-document-dialog';
import { CreateCollectionDialog } from './create-collection-dialog';
import { CollectionAnalysisDialog } from './collection-analysis-dialog';
import { GitHubRepoDialog } from './github-repo-dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';

interface Collection {
  topic: string;
  document_count: number;
  description?: string;
}

export default function RagCollectionsPage() {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isGitHubRepoOpen, setIsGitHubRepoOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [deletingTopic, setDeletingTopic] = useState<string | null>(null);
  
  const [collectionAnalysisResult, setCollectionAnalysisResult] = useState<any>(null);
  const [isCollectionAnalysisOpen, setIsCollectionAnalysisOpen] = useState(false);
  const [collectionPollingId, setCollectionPollingId] = useState<string | null>(null);
  const [analyzingTopic, setAnalyzingTopic] = useState<string | null>(null);
  
  const router = useRouter();

  const fetchCollections = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.post('/api/list-collections');
      setCollections(response.data);
    } catch (error) {
      toast.error('Error al cargar las colecciones.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { fetchCollections(); }, [fetchCollections]);

  const handleCollectionCreated = (newTopic: string) => {
    router.push(`/rag/${encodeURIComponent(newTopic)}`);
  };

  const handleAnalyzeCollection = async (topic: string) => {
    if (collectionPollingId) {
      toast.info("Ya hay un análisis en progreso. Por favor, espera.");
      return;
    }
    try {
      setCollectionAnalysisResult(null); 
      setAnalyzingTopic(topic);
      const response = await apiClient.post('/api/start-collection-analysis', { topic });
      setCollectionPollingId(response.data.task_id);
      toast.info(`Análisis de la colección "${topic}" iniciado.`);
    } catch (error) {
      toast.error("No se pudo iniciar el análisis de la colección.");
      setAnalyzingTopic(null);
    }
  };

  useEffect(() => {
    if (!collectionPollingId) return;

    const poller = setInterval(async () => {
      try {
        const response = await apiClient.get(`/api/get-analysis-result/${collectionPollingId}`);
        const { status, result, error } = response.data;

        if (status === 'completed') {
          clearInterval(poller);
          setCollectionAnalysisResult(result);
          setIsCollectionAnalysisOpen(true);
          toast.success(`¡Análisis de "${analyzingTopic}" completado!`);
          setCollectionPollingId(null);
          setAnalyzingTopic(null);
        } else if (status === 'failed') {
          clearInterval(poller);
          toast.error(`El análisis de "${analyzingTopic}" falló: ${error || "Ocurrió un error."}`);
          setCollectionPollingId(null);
          setAnalyzingTopic(null);
        }
      } catch (err) {
        clearInterval(poller);
        toast.error("Error al obtener el resultado del análisis.");
        setCollectionPollingId(null);
        setAnalyzingTopic(null);
      }
    }, 5000);

    return () => clearInterval(poller);
  }, [collectionPollingId, analyzingTopic]);

  const handleAnalysisDialogClose = (isOpen: boolean) => {
    setIsCollectionAnalysisOpen(isOpen);
    if (!isOpen) {
      setCollectionAnalysisResult(null);
    }
  };

  const handleDeleteCollection = async () => {
    if (!deletingTopic) return;
    try {
      await apiClient.post('/api/delete-collection', { topic: deletingTopic });
      toast.success(`Colección "${deletingTopic}" eliminada.`);
      fetchCollections();
    } catch (error) {
      toast.error(`Error al eliminar la colección "${deletingTopic}".`);
    } finally {
      setIsDeleteDialogOpen(false);
      setDeletingTopic(null);
    }
  };

  const openDeleteDialog = (topic: string) => {
    setDeletingTopic(topic);
    setIsDeleteDialogOpen(true);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-muted/20">
      <div className="container mx-auto px-6 py-8 max-w-7xl">
        {/* Header */}
        <div className="mb-12">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-6">
            <div className="space-y-2">
              <div className="flex items-center gap-3">
                <div className="h-12 w-12 rounded-2xl bg-primary/10 flex items-center justify-center">
                  <BookMarked className="h-6 w-6 text-primary" />
                </div>
                <div>
                  <h1 className="text-3xl font-bold tracking-tight">Gestión de Documentos</h1>
                  <p className="text-muted-foreground">Organiza tu conocimiento en colecciones inteligentes</p>
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-3">
              <Button 
                variant="outline" 
                onClick={() => setIsGitHubRepoOpen(true)}
                className="h-11 px-6 shadow-sm hover:shadow-md transition-all duration-200"
              >
                <Github className="mr-2 h-4 w-4" />
                Repositorio
              </Button>
              <Button 
                onClick={() => setIsUploadOpen(true)}
                className="h-11 px-6 shadow-sm hover:shadow-md transition-all duration-200"
              >
                <Plus className="mr-2 h-4 w-4" />
                Subir Documento
              </Button>
            </div>
          </div>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="flex flex-col items-center gap-4">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <p className="text-muted-foreground">Cargando colecciones...</p>
            </div>
          </div>
        ) : (
          <div className="space-y-8">
            {/* Quick Access Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Link href="/rag/all" className="group">
                <Card className="h-full border-0 shadow-sm hover:shadow-lg transition-all duration-300 bg-gradient-to-br from-primary/5 to-primary/10 hover:from-primary/10 hover:to-primary/15">
                  <CardContent className="p-8">
                    <div className="flex items-start gap-4">
                      <div className="h-14 w-14 rounded-2xl bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                        <Library className="h-7 w-7 text-primary" />
                      </div>
                      <div className="flex-1 space-y-2">
                        <h3 className="text-xl font-semibold">Todos los Documentos</h3>
                        <p className="text-muted-foreground text-sm leading-relaxed">
                          Explora y gestiona toda tu biblioteca de conocimiento en un solo lugar
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </Link>
              
              <Link href="/rag/repositories" className="group">
                <Card className="h-full border-0 shadow-sm hover:shadow-lg transition-all duration-300 bg-gradient-to-br from-primary/5 to-primary/10 hover:from-primary/10 hover:to-primary/15">
                  <CardContent className="p-8">
                    <div className="flex items-start gap-4">
                      <div className="h-14 w-14 rounded-2xl bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                        <Github className="h-7 w-7 text-primary" />
                      </div>
                      <div className="flex-1 space-y-2">
                        <h3 className="text-xl font-semibold">Repositorios</h3>
                        <p className="text-muted-foreground text-sm leading-relaxed">
                          Conecta y sincroniza tus repositorios de GitHub para análisis de código
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            </div>

            {/* Collections Section */}
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-2xl font-semibold tracking-tight">Colecciones</h2>
                <Badge variant="secondary" className="text-sm">
                  {collections.length} colección{collections.length !== 1 ? 'es' : ''}
                </Badge>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {collections.map((collection) => (
                  <Card key={collection.topic} className="group relative overflow-hidden border-0 shadow-sm hover:shadow-lg transition-all duration-300 bg-card/50 backdrop-blur-sm">
                    <Link 
                      href={`/rag/${encodeURIComponent(collection.topic)}`} 
                      className="absolute inset-0 z-10" 
                      aria-label={`Ver colección ${collection.topic}`}
                    />
                    
                    <CardContent className="p-6 space-y-4">
                      <div className="flex items-start justify-between">
                        <div className="flex items-start gap-3 flex-1 min-w-0">
                          <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center flex-shrink-0 group-hover:bg-primary/20 transition-colors">
                            <FolderKanban className="h-5 w-5 text-primary" />
                          </div>
                          <div className="flex-1 min-w-0 space-y-1">
                            <h3 className="font-semibold truncate text-base leading-tight">
                              {collection.topic}
                            </h3>
                            <Badge variant="outline" className="text-xs">
                              {collection.document_count} doc{collection.document_count !== 1 ? 's' : ''}
                            </Badge>
                          </div>
                        </div>
                        
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button 
                              variant="ghost" 
                              size="icon" 
                              className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity z-20 flex-shrink-0"
                            >
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end" className="w-48">
                            <DropdownMenuItem 
                              onClick={(e) => { 
                                e.stopPropagation(); 
                                handleAnalyzeCollection(collection.topic); 
                              }}
                            >
                              <ScanSearch className="mr-2 h-4 w-4" />
                              Analizar Colección
                            </DropdownMenuItem>
                            <DropdownMenuItem 
                              onClick={(e) => { 
                                e.stopPropagation(); 
                                openDeleteDialog(collection.topic); 
                              }}
                              className="text-destructive focus:text-destructive"
                            >
                              Eliminar Colección
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                      
                      {collectionPollingId && analyzingTopic === collection.topic ? (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground bg-muted/50 rounded-lg p-3">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          <span>Analizando colección...</span>
                        </div>
                      ) : collection.description && (
                        <p className="text-sm text-muted-foreground leading-relaxed line-clamp-2">
                          {collection.description}
                        </p>
                      )}
                    </CardContent>
                  </Card>
                ))}
                
                {/* Create New Collection Card */}
                <Card 
                  className="group cursor-pointer border-2 border-dashed border-muted-foreground/25 hover:border-primary/50 bg-transparent hover:bg-primary/5 transition-all duration-300"
                  onClick={() => setIsCreateOpen(true)}
                >
                  <CardContent className="p-6 flex flex-col items-center justify-center text-center space-y-4 min-h-[200px]">
                    <div className="h-12 w-12 rounded-2xl border-2 border-dashed border-muted-foreground/25 group-hover:border-primary/50 flex items-center justify-center group-hover:bg-primary/10 transition-all">
                      <Plus className="h-6 w-6 text-muted-foreground group-hover:text-primary transition-colors" />
                    </div>
                    <div className="space-y-2">
                      <h3 className="font-semibold group-hover:text-primary transition-colors">
                        Nueva Colección
                      </h3>
                      <p className="text-sm text-muted-foreground">
                        Crea un nuevo espacio para organizar tus documentos
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Dialogs */}
      <UploadDocumentDialog 
        isOpen={isUploadOpen} 
        onOpenChange={setIsUploadOpen} 
        onUploadSuccess={fetchCollections} 
      />
      <CreateCollectionDialog 
        isOpen={isCreateOpen} 
        onOpenChange={setIsCreateOpen} 
        onCreateSuccess={handleCollectionCreated} 
      />
      <GitHubRepoDialog 
        isOpen={isGitHubRepoOpen} 
        onOpenChange={setIsGitHubRepoOpen} 
        onSuccess={fetchCollections} 
      />
      <CollectionAnalysisDialog
        isOpen={isCollectionAnalysisOpen}
        onOpenChange={handleAnalysisDialogClose}
        analysis={collectionAnalysisResult}
        topic={analyzingTopic ?? ''}
      />
      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Eliminar colección?</AlertDialogTitle>
            <AlertDialogDescription>
              Esta acción eliminará permanentemente la colección "{deletingTopic}" y todos sus documentos. 
              Esta acción no se puede deshacer.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleDeleteCollection} 
              className="bg-destructive hover:bg-destructive/90"
            >
              Eliminar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
