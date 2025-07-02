// En: src/app/(dashboard)/rag/page.tsx

'use client';

import { useEffect, useState, useCallback, useMemo } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { PlusCircle, FolderKanban, MoreVertical, ScanSearch, Loader2, Library, BookMarked } from 'lucide-react';

import { UploadDocumentDialog } from './upload-document-dialog';
import { CreateCollectionDialog } from './create-collection-dialog';
import { CollectionAnalysisDialog } from './collection-analysis-dialog';
import { GitHubRepoDialog } from './github-repo-dialog';

interface Collection {
  topic: string;
  document_count: number;
}

export default function RagCollectionsPage() {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isGitHubRepoOpen, setIsGitHubRepoOpen] = useState(false);
  
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
          toast.error(`El análisis de "${analyzingTopic}" falló.`, { description: error || "Ocurrió un error." });
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

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold flex items-center">
            <BookMarked className="mr-2 h-8 w-8 text-primary" />
            Gestión de Documentos
          </h1>
          <p className="text-muted-foreground">Organiza tus documentos en bases de conocimiento.</p>
        </div>
        <div className="flex space-x-2">
          <Button onClick={() => setIsGitHubRepoOpen(true)}>
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-2 h-4 w-4"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"/></svg>
            Añadir Repositorio
          </Button>
          <Button onClick={() => setIsUploadOpen(true)}>
              <PlusCircle className="mr-2 h-4 w-4" />
              Subir Documento
          </Button>
        </div>
      </div>

      {isLoading ? <p>Cargando colecciones...</p> : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          <Link href="/rag/all" className="block hover:scale-[1.02] transition-transform">
            <Card className="h-full bg-primary/10 border-primary/20 hover:border-primary">
              <CardHeader>
                <CardTitle className="flex items-start gap-3">
                  <Library className="h-6 w-6 text-primary flex-shrink-0 mt-1" />
                  <span className="break-words">Todos los Documentos</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">Ver y gestionar todos tus archivos en un solo lugar.</p>
              </CardContent>
            </Card>
          </Link>
          
          {collections.map((collection) => (
            <Card key={collection.topic} className="flex flex-col hover:border-primary/50 transition-colors relative group">
                <Link href={`/rag/${encodeURIComponent(collection.topic)}`} className="absolute inset-0 z-10" aria-label={`Ver colección ${collection.topic}`}></Link>
                <div className="flex justify-between items-start p-4 pb-0 z-20">
                    <div className="flex items-start gap-3 flex-1 min-w-0">
                        <FolderKanban className="h-6 w-6 text-primary flex-shrink-0 mt-1" />
                        <div className="flex-1 min-w-0">
                            <CardTitle className="break-words">{collection.topic}</CardTitle>
                            <CardContent className="p-0 pt-2">
                                {collectionPollingId && analyzingTopic === collection.topic ? (
                                    <div className="flex items-center text-sm text-muted-foreground">
                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                        <span>Analizando...</span>
                                    </div>
                                ) : (
                                    <p className="text-sm text-muted-foreground">{collection.document_count} documento(s)</p>
                                )}
                            </CardContent>
                        </div>
                    </div>
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon" className="h-8 w-8 -mt-2 -mr-2 z-30 flex-shrink-0">
                                <MoreVertical className="h-4 w-4" />
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={(e) => { e.stopPropagation(); handleAnalyzeCollection(collection.topic); }}>
                                <ScanSearch className="mr-2 h-4 w-4" />
                                <span>Analizar Colección</span>
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>
            </Card>
          ))}
          
          <Card 
            className="border-dashed hover:border-primary hover:text-primary transition-colors flex flex-col items-center justify-center text-center p-6 cursor-pointer h-full"
            onClick={() => setIsCreateOpen(true)}
          >
            <PlusCircle className="h-8 w-8 mb-2" />
            <p className="font-semibold">Crear Nueva Colección</p>
            <p className="text-sm text-muted-foreground">Define un nuevo tema para tus documentos.</p>
          </Card>
        </div>
      )}

      <UploadDocumentDialog isOpen={isUploadOpen} onOpenChange={setIsUploadOpen} onUploadSuccess={fetchCollections} />
      <CreateCollectionDialog isOpen={isCreateOpen} onOpenChange={setIsCreateOpen} onCreateSuccess={handleCollectionCreated} />
      <GitHubRepoDialog isOpen={isGitHubRepoOpen} onOpenChange={setIsGitHubRepoOpen} onSuccess={fetchCollections} />
      <CollectionAnalysisDialog
        isOpen={isCollectionAnalysisOpen}
        onOpenChange={handleAnalysisDialogClose}
        analysis={collectionAnalysisResult}
        topic={analyzingTopic ?? ''}
      />
    </div>
  );
}
