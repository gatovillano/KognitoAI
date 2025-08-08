'use client';

import { useEffect, useState, useCallback } from 'react';
// import Link from 'next/link'; // Removed as CollectionDisplay handles links
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { Plus, FolderKanban, MoreVertical, ScanSearch, Loader2, Library, BookMarked, Trash2, Github, Edit, Share2, Upload, CheckCircle, XCircle, Clock, Network, ChevronDown, Settings } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

import { UploadDocumentDialog } from './upload-document-dialog';
import { CreateCollectionDialog } from './create-collection-dialog';
import { CollectionAnalysisDialog } from './collection-analysis-dialog';
import UploadProgressIndicator, { UploadTask } from '@/components/UploadProgressIndicator';
import { GitHubRepoDialog } from './github-repo-dialog';
import { EditCollectionDialog } from './edit-collection-dialog';
import { ShareCollectionDialog } from './share-collection-dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { CollectionDisplay, StaticCollectionCard } from '@/components/CollectionDisplay'; // Import CollectionDisplay and StaticCollectionCard

interface Collection {
  topic: string;
  document_count: number;
  description?: string;
  team_shared?: boolean;
  has_knowledge_graph?: boolean;
}

export default function RagCollectionsPage() {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isGitHubRepoOpen, setIsGitHubRepoOpen] = useState(false);
  const [deletingTopic, setDeletingTopic] = useState<string | null>(null);

  // Estados para el seguimiento de tareas de subida
  const [uploadTasks, setUploadTasks] = useState<UploadTask[]>([]);

  // Estados para procesamiento de grafos de conocimiento
  const [isProcessingKnowledgeGraph, setIsProcessingKnowledgeGraph] = useState(false);
  
  const [collectionAnalysisResult, setCollectionAnalysisResult] = useState<any>(null);
  const [isCollectionAnalysisOpen, setIsCollectionAnalysisOpen] = useState(false);
  const [collectionPollingId, setCollectionPollingId] = useState<string | null>(null);
  const [analyzingTopic, setAnalyzingTopic] = useState<string | null>(null);

  // Estados para editar y compartir colecciones
  const [isEditCollectionOpen, setIsEditCollectionOpen] = useState(false);
  const [isShareCollectionOpen, setIsShareCollectionOpen] = useState(false);
  const [selectedCollection, setSelectedCollection] = useState<Collection | null>(null);
  
  const router = useRouter();

  const fetchCollections = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.get('/api/list-collections');
      setCollections(response.data);
    } catch (error) {
      toast.error('Error al cargar las colecciones.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCollections();
  }, [fetchCollections]);

  const handleCollectionCreated = async (newTopic: string) => {
    // Recargar las colecciones para mostrar la nueva
    await fetchCollections();
    // Luego navegar a la nueva colección
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
      toast.info(`Análisis de la colección &quot;${topic}&quot; iniciado.`);
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

  const handleDeleteConfirm = async () => {
    if (!deletingTopic) return;
    const toastId = toast.loading(`Eliminando colección...`);
    try {
      await apiClient.post('/api/delete-collection', { topic: deletingTopic });
      toast.success(`Colección "${deletingTopic}" eliminada.`, { id: toastId });
      fetchCollections();
    } catch (error) {
      toast.error(`Error al eliminar la colección "${deletingTopic}".`, { id: toastId });
    } finally {
      setDeletingTopic(null);
    }
  };

  const openDeleteDialog = (topic: string) => {
    setDeletingTopic(topic);
  };

  const handleEditCollection = (collection: Collection) => {
    setSelectedCollection(collection);
    setIsEditCollectionOpen(true);
  };

  const handleShareCollection = (collection: Collection) => {
    setSelectedCollection(collection);
    setIsShareCollectionOpen(true);
  };

  const handleEditSuccess = () => {
    fetchCollections();
    setSelectedCollection(null);
  };

  const handleShareSuccess = () => {
    fetchCollections();
    setSelectedCollection(null);
  };

  const handleProcessKnowledgeGraph = async (topic?: string) => {
    if (isProcessingKnowledgeGraph) {
      toast.info("Ya hay un procesamiento de grafo en progreso.");
      return;
    }

    setIsProcessingKnowledgeGraph(true);
    const toastId = toast.loading(
      topic
        ? `Procesando grafo de conocimiento para "${topic}"...`
        : "Procesando grafo de conocimiento para todos los documentos..."
    );

    try {
      const response = await apiClient.post('/api/process-knowledge-graph',
        topic ? { topic } : {}
      );

      toast.success(
        `¡Procesamiento iniciado! ${response.data.documents_count} documentos serán procesados.`,
        { id: toastId }
      );
    } catch (error) {
      toast.error("Error al iniciar el procesamiento del grafo de conocimiento.", { id: toastId });
    } finally {
      setIsProcessingKnowledgeGraph(false);
    }
  };

  const renderContent = () => {
    if (isLoading) {
      return <p className="text-center py-10">Cargando colecciones...</p>;
    }

    if (collections.length === 0) {
      return (
        <div className="text-center py-20 px-8">
          <FolderKanban className="mx-auto h-16 w-16 text-muted-foreground/50 mb-6" />
          <h3 className="text-xl font-semibold mb-4">No tienes colecciones aún</h3>
          <p className="text-muted-foreground mb-8 max-w-md mx-auto">
            Las colecciones te ayudan a organizar tus documentos por temas. ¡Crea tu primera colección para empezar!
          </p>
          <Button onClick={() => setIsCreateOpen(true)} size="lg">
            <Plus className="mr-2 h-5 w-5" />
            Crear tu primera Colección
          </Button>
        </div>
      );
    }

    return (
      <motion.div layout className="grid gap-8 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 px-2">
        <AnimatePresence>
          <StaticCollectionCard
            key="all-documents-card"
            href="/rag/all"
            icon={Library}
            title="Todos los Documentos"
            description="Ver y gestionar todos tus archivos en un solo lugar."
            className="bg-muted"
          />
          <StaticCollectionCard
            key="repositories-card"
            href="/rag/repositories"
            icon={Github}
            title="Repositorios"
            description="Ver y gestionar todos tus repositorios de GitHub."
            className="bg-muted"
          />
          {collections.map((collection) => (
            <CollectionDisplay
              key={collection.topic}
              collection={collection}
              onAnalyze={handleAnalyzeCollection}
              onDelete={openDeleteDialog}
              onEdit={handleEditCollection}
              onShare={handleShareCollection}
              onProcessKnowledgeGraph={handleProcessKnowledgeGraph}
              isAnalyzing={collectionPollingId !== null && analyzingTopic === collection.topic}
              type="list" // Specify type as 'list'
            /> 
          ))}
          {/* Tarjeta para crear nueva colección */}
          <motion.div
            key="create-collection-card"
            layout
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="h-full"
          >
            <Card
              className="group border-2 border-dashed border-border hover:border-primary hover:bg-primary/5 transition-all duration-200 flex flex-col items-center justify-center text-center p-6 cursor-pointer h-full"
              onClick={() => setIsCreateOpen(true)}
            >
              <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center mb-3 group-hover:bg-primary/20 transition-colors">
                <Plus className="h-6 w-6 text-primary" />
              </div>
              <h3 className="font-semibold mb-1">Crear Colección</h3>
              <p className="text-xs text-muted-foreground">Nuevo tema de documentos</p>
            </Card>
          </motion.div>
        </AnimatePresence>
      </motion.div>
    );
  };

  return (
    <div className="p-8 mx-4 overflow-x-hidden">
      <div className="flex items-center justify-between mb-12">
        <div>
          <h1 className="text-3xl font-bold flex items-center">
            <BookMarked className="mr-3 h-8 w-8 text-primary" />
            Colecciones de Conocimientos
          </h1>
          <p className="text-muted-foreground mt-2">Organiza tus documentos en bases de conocimiento.</p>
        </div>
        <div className="flex items-center gap-3">
          {/* Menú de Acciones Avanzadas */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" className="gap-2">
                <Settings className="h-4 w-4" />
                <span className="hidden sm:inline">Acciones</span>
                <ChevronDown className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuItem onClick={() => setIsGitHubRepoOpen(true)}>
                <Github className="mr-2 h-4 w-4" />
                <span>Añadir Repositorio</span>
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => handleProcessKnowledgeGraph()}
                disabled={isProcessingKnowledgeGraph}
              >
                <Network className="mr-2 h-4 w-4" />
                <span>{isProcessingKnowledgeGraph ? "Procesando Grafos..." : "Crear Grafos de Conocimiento"}</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Botón Principal */}
          <Button size="lg" onClick={() => setIsUploadOpen(true)} className="bg-primary hover:bg-primary/90 gap-2">
            <Plus className="h-5 w-5" />
            <span>Subir Documento</span>
          </Button>
        </div>
      </div>

      {uploadTasks.length > 0 && <UploadProgressIndicator tasks={uploadTasks} />}
 
       {renderContent()}
 
       <UploadDocumentDialog isOpen={isUploadOpen} onOpenChange={setIsUploadOpen} onUploadSuccess={() => { /* WebSocket handles updates */ }} onUploadStart={() => { /* WebSocket handles updates */ }} />
       <CreateCollectionDialog isOpen={isCreateOpen} onOpenChange={setIsCreateOpen} onCreateSuccess={handleCollectionCreated} />
       <GitHubRepoDialog isOpen={isGitHubRepoOpen} onOpenChange={setIsGitHubRepoOpen} onSuccess={() => { fetchCollections(); /* WebSocket handles upload tasks updates */ }} />
       <CollectionAnalysisDialog
         isOpen={isCollectionAnalysisOpen}
         onOpenChange={handleAnalysisDialogClose}
         analysis={collectionAnalysisResult}
         topic={analyzingTopic ?? ''}
      />
      <AlertDialog open={!!deletingTopic} onOpenChange={(open) => !open && setDeletingTopic(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Estás seguro?</AlertDialogTitle>
            <AlertDialogDescription>
              Esta acción es irreversible y eliminará la colección &quot;{deletingTopic}&quot; y todos sus documentos permanentemente.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteConfirm} className="bg-destructive hover:bg-destructive/90">Sí, eliminar</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <EditCollectionDialog
        isOpen={isEditCollectionOpen}
        onOpenChange={setIsEditCollectionOpen}
        onEditSuccess={handleEditSuccess}
        collection={selectedCollection}
      />

      <ShareCollectionDialog
        isOpen={isShareCollectionOpen}
        onOpenChange={setIsShareCollectionOpen}
        onShareSuccess={handleShareSuccess}
        collection={selectedCollection}
      />
    </div>
  );
}
