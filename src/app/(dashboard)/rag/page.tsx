'use client';

import { useEffect, useState, useCallback } from 'react';
// import Link from 'next/link'; // Removed as CollectionDisplay handles links
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from '@/components/ui/dropdown-menu';
import apiClient from '@/lib/api';
import { toast } from 'sonner';
import { Plus, FolderKanban, MoreVertical, ScanSearch, Loader2, Library, Brain, Trash2, Github, Edit, Share2, Upload, CheckCircle, XCircle, Clock, Network, ChevronDown, Settings, AlertTriangle, BarChart3, Info, Bot } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { useWebSocketContext } from '@/contexts/WebSocketContext';
import { WebSocketMessage } from '@/hooks/useWebSocket';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table as TableIcon, FileSpreadsheet, BarChart, Share, Download, Filter, Search } from 'lucide-react';

import { UploadDocumentDialog } from './upload-document-dialog';
import { CreateCollectionDialog } from './create-collection-dialog';
import { AnalysisDetailDialog } from '@/app/(dashboard)/analysis/analysis-detail-dialog';
import UploadProgressIndicator, { UploadTask } from '@/components/UploadProgressIndicator';
import { Analysis } from '@/lib/models';
import { GitHubRepoDialog } from './github-repo-dialog';
import { EditCollectionDialog } from './edit-collection-dialog';
import { ShareCollectionDialog } from './share-collection-dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { CollectionDisplay, StaticCollectionCard } from '@/components/CollectionDisplay';
import { GenericCard } from '@/components/GenericCard'; // Import CollectionDisplay and StaticCollectionCard
import { DatasetNameDialog } from './dataset-name-dialog';
import { TablesView } from './tables-view';
import { AnalysisResults } from '@/components/AnalysisResults';
import { GraphView } from '@/components/GraphView';
import { ContextualChat } from '@/components/ContextualChat';
import GraphProgressIndicator, { GraphTask } from '@/components/GraphProgressIndicator';

interface Collection {
  topic: string;
  document_count: number;
  description?: string;
  team_shared?: boolean;
  has_knowledge_graph?: boolean;
  workspace_id?: string;
  workspace_name?: string;
  workspace_color?: string; // Nuevo campo
}

export default function RagCollectionsPage() {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isGitHubRepoOpen, setIsGitHubRepoOpen] = useState(false);
  const [deletingTopic, setDeletingTopic] = useState<string | null>(null);
  const [isInfoSheetOpen, setIsInfoSheetOpen] = useState(false); // Estado para controlar la visibilidad del Sheet

  // Estados para el seguimiento de tareas de subida
  const [uploadTasks, setUploadTasks] = useState<UploadTask[]>([]);

  // Estados para procesamiento de grafos de conocimiento
  const [isProcessingKnowledgeGraph, setIsProcessingKnowledgeGraph] = useState(false);
  const [isProcessingMemories, setIsProcessingMemories] = useState(false);

  const [selectedAnalysis, setSelectedAnalysis] = useState<Analysis | null>(null);
  const [collectionPollingId, setCollectionPollingId] = useState<string | null>(null);
  const [analyzingTopic, setAnalyzingTopic] = useState<string | null>(null);

  // Estados para editar y compartir colecciones
  const [isEditCollectionOpen, setIsEditCollectionOpen] = useState(false);
  const [isShareCollectionOpen, setIsShareCollectionOpen] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [selectedCollectionForChat, setSelectedCollectionForChat] = useState<Collection | null>(null);
  const [selectedCollection, setSelectedCollection] = useState<Collection | null>(null);

  // Nuevo estado para el diálogo de análisis global
  const [isGlobalAnalysisOpen, setIsGlobalAnalysisOpen] = useState(false);

  // Estado para el diálogo de configuración de grafo
  const [isDatasetDialogOpen, setIsDatasetDialogOpen] = useState(false);
  const [processingTopic, setProcessingTopic] = useState<string | null>(null);
  const [processingWorkspaceId, setProcessingWorkspaceId] = useState<string | null>(null);
  const [activeTasks, setActiveTasks] = useState<GraphTask[]>([]);

  const { registerMessageHandler } = useWebSocketContext();

  const fetchCollections = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.get('/api/collections');
      console.log('API raw response data:', response.data); // Nuevo log para la data cruda
      setCollections(response.data);
      console.log('Collections state after update:', response.data); // Nuevo log para el estado actualizado
    } catch (error) {
      console.error('Error fetching collections:', error); // Debug log
      toast.error('Error al cargar las colecciones.');
    } finally {
      setIsLoading(false);
      console.log('Finished fetching collections. isLoading set to false.'); // Debug log
    }
  }, []);

  const onUploadStarted = useCallback((message: WebSocketMessage) => {
    if (!message || !message.task_id) return;
    setUploadTasks(prev => {
      // Evitar duplicados si ya se añadió por onUploadStart del diálogo
      const exists = prev.some(t => t.id === message.task_id || t.id === (message.file_names?.[0]));
      if (exists) {
        return prev.map(t => (t.id === message.task_id || t.id === (message.file_names?.[0]))
          ? { ...t, id: message.task_id, status: 'processing', file_names: message.file_names, topic: message.topic }
          : t);
      }
      return [...prev, { id: message.task_id, status: 'processing', file_names: message.file_names, topic: message.topic, created_at: message.created_at || new Date().toISOString() }];
    });
  }, []);

  const onUploadProgress = useCallback((data: any) => {
    if (!data || !data.task_id) return;
    setUploadTasks(prev => prev.map(task => task.id === data.task_id ? { ...task, progress: data.progress } : task));
  }, []);

  const onUploadCompleted = useCallback((data: any) => {
    if (!data || !data.task_id) return;
    toast.success(data.message || 'Subida completada.');
    setUploadTasks(prev => prev.filter(task => task.id !== data.task_id));
    fetchCollections();
  }, [fetchCollections]);

  const onUploadFailed = useCallback((data: any) => {
    if (!data || !data.task_id) return;
    toast.error(data.error_message || 'Falló la subida de archivos.');
    setUploadTasks(prev => prev.filter(task => task.id !== data.task_id));
  }, []);

  useEffect(() => {
    const handleWebSocketMessage = (message: WebSocketMessage) => {
      switch (message.type) {
        case 'upload_started':
          onUploadStarted(message);
          break;
        case 'upload_progress':
          onUploadProgress(message.data || message);
          break;
        case 'upload_completed':
          onUploadCompleted(message.data || message);
          break;
        case 'upload_failed':
          onUploadFailed(message.data || message);
          break;
        case 'knowledge_graph_progress':
        case 'analysis_progress':
          const taskData = message.data as GraphTask;
          if (taskData && taskData.task_id) {
            setActiveTasks(prev => {
              // 1. Verificar si ya existe por ID exacto
              const exists = prev.some(t => t.task_id === taskData.task_id);
              if (exists) {
                return prev.map(t => t.task_id === taskData.task_id ? { ...t, ...taskData } : t);
              }

              // 2. Si no existe, intentar vincular con una tarea temporal del mismo topic y tipo si existe
              // Esto evita que aparezcan dos recuadros cuando se inicia la tarea
              const tempTaskIndex = prev.findIndex(t => 
                (t.task_id.startsWith('temp-')) && 
                (t.topic === taskData.topic)
              );

              if (tempTaskIndex !== -1) {
                const newTasks = [...prev];
                newTasks[tempTaskIndex] = { ...newTasks[tempTaskIndex], ...taskData };
                return newTasks;
              }

              // 3. Si no hay nada con qué vincular, añadir como nueva
              return [...prev, taskData];
            });

            if (taskData.is_complete && message.type === 'knowledge_graph_progress') {
              fetchCollections();
            }
          }
          break;
      }
    };

    const unregister = registerMessageHandler(handleWebSocketMessage);
    return unregister;
  }, [registerMessageHandler, onUploadStarted, onUploadProgress, onUploadCompleted, onUploadFailed]);

  const router = useRouter();

  useEffect(() => {
    console.log('useEffect: Fetching collections...'); // Debug log
    fetchCollections();
  }, [fetchCollections]);

  const handleCollectionCreated = async (newTopic: string) => {
    // Recargar las colecciones para mostrar la nueva
    await fetchCollections();
    // Luego navegar a la nueva colección
    router.push(`/rag/${encodeURIComponent(newTopic)}`);
  };

  const handleAnalyzeCollection = async (topic: string) => {
    console.log(`Attempting to analyze collection: ${topic}`); // Added for debugging
    if (collectionPollingId) {
      toast.info("Ya hay un análisis en progreso. Por favor, espera.");
      return;
    }
    try {
      setSelectedAnalysis(null);
      setAnalyzingTopic(topic);
      
      const tempTaskId = `temp-${Date.now()}`;
      setActiveTasks(prev => [...prev, {
        task_id: tempTaskId,
        phase: 'initializing',
        message: 'Iniciando análisis de colección...',
        progress_percent: 0,
        is_complete: false,
        has_error: false,
        processing_mode: 'conceptual',
        topic: topic
      }]);

      const response = await apiClient.post('/api/start-collection-analysis', { topic });
      setCollectionPollingId(response.data.task_id);
      
      // Vincular ID real con la tarea temporal
      setActiveTasks(prev => prev.map(t => t.task_id === tempTaskId ? { ...t, task_id: response.data.task_id } : t));
      
      toast.info(`Análisis de la colección "${topic}" iniciado.`);
    } catch (error) {
      toast.error("No se pudo iniciar el análisis de la colección.");
      setAnalyzingTopic(null);
      setActiveTasks(prev => prev.filter(t => !t.task_id.startsWith('temp-')));
    }
  };

  // Nueva función para abrir el diálogo de análisis global
  const handleGlobalAnalysis = () => {
    setIsGlobalAnalysisOpen(true);
    setAnalyzingTopic(null); // Resetear para un análisis global
    setSelectedAnalysis(null); // Resetear para un análisis global
  };

  useEffect(() => {
    if (!collectionPollingId) return;

    const poller = setInterval(async () => {
      try {
        const response = await apiClient.get(`/api/get-analysis-result/${collectionPollingId}`);
        const { status, result, error } = response.data;

        if (status === 'completed') {
          clearInterval(poller);

          const analysisType = result?.analysis_metadata?.analysis_type || 'collection';
          let title = `Análisis de Colección: ${analyzingTopic}`;
          if (analysisType === 'semantic_summary') {
            title = `Resumen Semántico: ${analyzingTopic}`;
          } else if (analysisType === 'knowledge_graph_analysis') {
            title = `Análisis de Grafo: ${analyzingTopic}`;
          }

          const newAnalysis: Analysis = {
            id: collectionPollingId,
            type: analysisType,
            title: title,
            created_at: new Date().toISOString(),
            result: result,
            full_data: result,
          };

          setSelectedAnalysis(newAnalysis);
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



  const handleDeleteConfirm = async () => {
    if (!deletingTopic) return;
    const toastId = toast.loading(`Eliminando colección...`);
    try {
      await apiClient.post('/api/documents/collections/delete', { topic: deletingTopic });
      toast.success(`Colección "${deletingTopic}" eliminada.`, { id: toastId });
      // Actualización optimista: eliminar la colección del estado inmediatamente
      setCollections(prevCollections => prevCollections.filter(col => col.topic !== deletingTopic));
      // Luego, recargar para asegurar la consistencia (opcional, pero buena práctica)
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

  const handleProcessKnowledgeGraph = (topic?: string, workspaceId?: string) => {
    console.log('🔍 handleProcessKnowledgeGraph called with:', { topic, workspaceId });
    if (isProcessingKnowledgeGraph) {
      toast.info("Ya hay un procesamiento de grafo en progreso.");
      return;
    }
    setProcessingTopic(topic || null);
    setProcessingWorkspaceId(workspaceId || null);
    setIsDatasetDialogOpen(true);
  };

  const handleConfirmProcessGraph = async (datasetName: string, mode: 'hybrid' | 'conceptual') => {
    setIsProcessingKnowledgeGraph(true);
    const toastId = toast.loading(
      processingTopic
        ? `Procesando grafo de conocimiento para "${processingTopic}" (Modo: ${mode === 'hybrid' ? 'Estándar' : 'Conceptual'})...`
        : `Procesando grafo global (Modo: ${mode === 'hybrid' ? 'Estándar' : 'Conceptual'})...`
    );

    try {
      // Inicializar tarea localmente para feedback inmediato
      const tempTaskId = `temp-${Date.now()}`;
      setActiveTasks(prev => [...prev, {
        task_id: tempTaskId,
        phase: 'initializing',
        message: 'Iniciando procesamiento...',
        progress_percent: 0,
        is_complete: false,
        has_error: false,
        processing_mode: mode,
        topic: processingTopic || undefined
      }]);

      // Determinar qué endpoint usar basado en el modo
      if (mode === 'conceptual') {
        // Modo Conceptual: Usar la herramienta de Procesamiento Conceptual
        const payload = {
          tool_name: "conceptual_processing",
          action: "process_documents",
          dataset_name: datasetName,  // Nombre para organizar el grafo
          topic: processingTopic || undefined,  // Nombre de la colección para filtrar documentos
          documents: [],
          workspace_id: processingWorkspaceId || undefined  // Workspace de la colección específica
        };
        const response = await apiClient.post('/api/tools/run', payload);

        // Actualizar el ID de la tarea temporal con el real si viene en la respuesta
        if (response.data?.task_id) {
          setActiveTasks(prev => prev.map(t => t.task_id === tempTaskId ? { ...t, task_id: response.data.task_id } : t));
        }
      } else {
        // Modo Híbrido (Estándar): Llamar al endpoint optimizado
        const response = await apiClient.post('/api/knowledge-graph/process-knowledge-graph-optimized', {
          workspace_id: processingWorkspaceId || undefined,
          dataset_name: datasetName,
          topic: processingTopic || undefined,  // Filtrar por colección específica
          force_reprocess: true
        });

        // Actualizar el ID de la tarea temporal con el real
        if (response.data?.task_id) {
          setActiveTasks(prev => prev.map(t => t.task_id === tempTaskId ? { ...t, task_id: response.data.task_id } : t));
        }
      }

      toast.success(
        `¡Creación de grafo iniciada!`,
        { id: toastId }
      );
    } catch (error) {
      console.error(error);
      toast.error("Error al iniciar el procesamiento del grafo.", { id: toastId });
      // Limpiar tareas temporales en caso de error
      setActiveTasks(prev => prev.filter(t => !t.task_id.startsWith('temp-')));
    } finally {
      setIsProcessingKnowledgeGraph(false);
      setProcessingTopic(null);
      setProcessingWorkspaceId(null);
    }
  };

  const handleChatCollection = (collection: Collection) => {
    setSelectedCollectionForChat(collection);
    setIsChatOpen(true);
  };

  const renderContent = () => {
    console.log('renderContent called. isLoading:', isLoading, 'collections.length:', collections.length); // Debug log
    if (isLoading) {
      console.log('renderContent: Displaying loading message.'); // Debug log
      return <p className="text-center py-10">Cargando colecciones...</p>;
    }

    if (collections.length === 0) {
      console.log('renderContent: Displaying no collections message.'); // Debug log
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
    console.log('renderContent: Displaying collections.'); // Debug log

    return (
      <motion.div layout className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-8 px-2">
        <AnimatePresence>
          <GenericCard
            key="all-documents-card"
            href="/rag/all"
            icon={Library}
            title="Todos los Documentos"
            description="Ver y gestionar todos tus archivos en un solo lugar."
            className="bg-muted"
          />
          <GenericCard
            key="repositories-card"
            href="/rag/repositories"
            icon={Github}
            title="Repositorios"
            description="Ver y gestionar todos tus repositorios de GitHub."
            className="bg-muted"
          />
          {collections.map((collection) => (
            <motion.div key={collection.topic} className="relative h-full" layout initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.8 }} transition={{ type: "spring", stiffness: 300, damping: 30 }}>
              <CollectionDisplay
                collection={collection}
                onAnalyze={handleAnalyzeCollection}
                onDelete={openDeleteDialog}
                onEdit={handleEditCollection}
                onShare={handleShareCollection}
                onChat={handleChatCollection}
                onProcessKnowledgeGraph={handleProcessKnowledgeGraph}
                isAnalyzing={
                  (collectionPollingId !== null && analyzingTopic === collection.topic) || 
                  activeTasks.some(t => t.topic === collection.topic && !t.is_complete && !t.has_error && !t.task_id.includes('temp'))
                }
                type="list" // Specify type as 'list'
              />
              {/* La etiqueta del workspace ahora se renderiza dentro de CollectionDisplay */}
            </motion.div>
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
              className="border-dashed hover:border-primary hover:bg-primary/5 cursor-pointer h-full flex flex-col items-center justify-center text-center p-6"
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

  const handleClearKnowledgeGraph = async () => {
    if (window.confirm('¿Estás seguro de que quieres borrar TODO el grafo de conocimiento? Esta acción es irreversible y afectará a todos los usuarios.')) {
      const toastId = toast.loading("Limpiando el grafo de conocimiento...");
      try {
        await apiClient.post('/api/clear-neo4j');
        toast.success("El grafo de conocimiento ha sido limpiado.", { id: toastId });
        fetchCollections(); // Recargar para reflejar cambios (e.g., has_knowledge_graph)
      } catch (error) {
        toast.error("Error al limpiar el grafo de conocimiento.", { id: toastId });
      }
    }
  };

  const handleProcessMemories = async () => {
    if (isProcessingMemories) return;

    if (!window.confirm('¿Deseas procesar todas las memorias pendientes de KAI e integrarlas al grafo?')) {
      return;
    }

    setIsProcessingMemories(true);
    const toastId = toast.loading("Iniciando procesamiento de memorias...");

    try {
      await apiClient.post('/api/knowledge-graph/process-memories');
      toast.success("Procesamiento de memorias iniciado en segundo plano.", { id: toastId });
    } catch (error) {
      console.error(error);
      toast.error("Error al iniciar el procesamiento de memorias.", { id: toastId });
    } finally {
      setIsProcessingMemories(false);
    }
  };

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-8 sm:mb-12 gap-4">
        <div className="flex items-center gap-2">
          <h1 className="text-2xl sm:text-3xl font-bold flex items-center truncate">
            <Brain className="mr-2 sm:mr-3 h-6 w-6 sm:h-8 sm:w-8 text-primary flex-shrink-0" />
            <span className="truncate">Conocimientos</span>
          </h1>
          <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground flex-shrink-0" onClick={() => setIsInfoSheetOpen(true)}>
            <Info className="h-4 w-4" />
          </Button>
        </div>
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 sm:gap-3 w-full sm:w-auto">
          {/* Menú de Acciones Avanzadas */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" className="gap-1 sm:gap-2 w-full sm:w-auto">
                <Settings className="h-3 w-3 sm:h-4 sm:w-4" />
                <span className="text-xs sm:text-sm">Acciones</span>
                <ChevronDown className="h-3 w-3 sm:h-4 sm:w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48 sm:w-56">
              <DropdownMenuItem onClick={() => setIsUploadOpen(true)} className="cursor-pointer font-medium text-primary">
                <Upload className="mr-1 sm:mr-2 h-3 w-3 sm:h-4 sm:w-4" />
                <span className="text-xs sm:text-sm">Subir Documento</span>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => setIsGitHubRepoOpen(true)} className="cursor-pointer">
                <Github className="mr-1 sm:mr-2 h-3 w-3 sm:h-4 sm:w-4" />
                <span className="text-xs sm:text-sm">Añadir Repositorio</span>
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => handleProcessKnowledgeGraph()}
                disabled={isProcessingKnowledgeGraph}
                className="cursor-pointer"
              >
                <Network className="mr-1 sm:mr-2 h-3 w-3 sm:h-4 sm:w-4" />
                <span className="text-xs sm:text-sm">{isProcessingKnowledgeGraph ? "Procesando Grafos..." : "Crear Grafos de Conocimiento"}</span>
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={handleClearKnowledgeGraph}
                className="text-red-600 focus:text-red-600 focus:bg-red-50 cursor-pointer"
              >
                <AlertTriangle className="mr-1 sm:mr-2 h-3 w-3 sm:h-4 sm:w-4" />
                <span className="text-xs sm:text-sm">Limpiar Grafo Global</span>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={handleProcessMemories}
                disabled={isProcessingMemories}
                className="cursor-pointer text-purple-600 focus:text-purple-600 focus:bg-purple-50"
              >
                {isProcessingMemories ? (
                  <Loader2 className="mr-1 sm:mr-2 h-3 w-3 sm:h-4 sm:w-4 animate-spin" />
                ) : (
                  <Brain className="mr-1 sm:mr-2 h-3 w-3 sm:h-4 sm:w-4" />
                )}
                <span className="text-xs sm:text-sm">Procesar memorias de KAI</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {(uploadTasks.length > 0 || activeTasks.length > 0) && (
        <div className="fixed bottom-6 right-6 z-50 w-80 space-y-4">
          {uploadTasks.length > 0 && <UploadProgressIndicator tasks={uploadTasks} />}
          {activeTasks.length > 0 && (
            <GraphProgressIndicator
              tasks={activeTasks}
              onDismiss={(taskId) => setActiveTasks(prev => prev.filter(t => t.task_id !== taskId))}
            />
          )}
        </div>
      )}

      <Tabs defaultValue="collections" className="w-full">
        <TabsList className="flex w-full overflow-x-auto no-scrollbar bg-muted/50 p-1 rounded-xl mb-8">
          <TabsTrigger value="collections" className="flex-1 flex items-center justify-center gap-2 py-2.5">
            <Library className="h-4 w-4" />
            <span className="hidden xs:inline text-xs">Colecciones</span>
          </TabsTrigger>
          <TabsTrigger value="tables" className="flex-1 flex items-center justify-center gap-2 py-2.5">
            <TableIcon className="h-4 w-4" />
            <span className="hidden xs:inline text-xs">Tablas</span>
          </TabsTrigger>
          <TabsTrigger value="results" className="flex-1 flex items-center justify-center gap-2 py-2.5">
            <BarChart3 className="h-4 w-4" />
            <span className="hidden xs:inline text-xs">Resultados</span>
          </TabsTrigger>
          <TabsTrigger value="graph" className="flex-1 flex items-center justify-center gap-2 py-2.5">
            <Network className="h-4 w-4" />
            <span className="hidden xs:inline text-xs">Grafos</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="collections" className="space-y-4">
          {renderContent()}
        </TabsContent>

        <TabsContent value="tables" className="space-y-4">
          <TablesView />
        </TabsContent>

        <TabsContent value="results" className="space-y-4">
          <AnalysisResults />
        </TabsContent>

        <TabsContent value="graph" className="space-y-4">
          <GraphView />
        </TabsContent>
      </Tabs>

      <UploadDocumentDialog
        isOpen={isUploadOpen}
        onOpenChange={setIsUploadOpen}
        onUploadSuccess={() => { /* WebSocket handles updates */ }}
        onUploadStart={(fileNames, topic) => {
          const newTasks = fileNames.map(name => ({
            id: name, // Usar el nombre del archivo como ID temporal
            file_names: [name], // Añadir file_names como un array con el nombre del archivo
            topic,
            status: 'pending' as const,
            progress: 0,
            created_at: new Date().toISOString(), // Añadir created_at con la fecha actual
          }));
          setUploadTasks(prev => [...prev, ...newTasks]);
        }}
      />
      <CreateCollectionDialog isOpen={isCreateOpen} onOpenChange={setIsCreateOpen} onCreateSuccess={handleCollectionCreated} />
      <GitHubRepoDialog isOpen={isGitHubRepoOpen} onOpenChange={setIsGitHubRepoOpen} onSuccess={() => { fetchCollections(); /* WebSocket handles upload tasks updates */ }} />
      <AnalysisDetailDialog
        isOpen={!!selectedAnalysis}
        onOpenChange={(open) => !open && setSelectedAnalysis(null)}
        analysis={selectedAnalysis}
      />
      <AlertDialog open={!!deletingTopic} onOpenChange={(open) => !open && setDeletingTopic(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Estás seguro?</AlertDialogTitle>
            <AlertDialogDescription>
              Esta acción es irreversible y eliminará la colección {"\u0022"}{deletingTopic}{"\u0022"} y todos sus documentos permanentemente.
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

      <DatasetNameDialog
        isOpen={isDatasetDialogOpen}
        onOpenChange={setIsDatasetDialogOpen}
        onConfirm={handleConfirmProcessGraph}
        defaultTopic={processingTopic}
        workspaceId={collections.length > 0 ? collections[0].workspace_id : undefined}
      />

      {/* {linkingCollection && (
        <ManageLinkedObjectsDialog
          isOpen={isLinkProfileDialogOpen}
          onOpenChange={setIsLinkProfileDialogOpen}
          profile={{
            id: String(linkingCollection.topic),
            name: linkingCollection.topic,
            email: null, phone: null, tags: null, category: null, custom_fields: null,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString()
          }}
          onLinkedObjectsUpdated={fetchCollections}
        />
      )} */}

      <Sheet open={isInfoSheetOpen} onOpenChange={setIsInfoSheetOpen}>
        <SheetContent side="right" className="w-[400px] sm:w-[540px] overflow-y-auto">
          <SheetHeader className="pb-6 border-b">
            <SheetTitle className="text-2xl font-bold flex items-center gap-2">
              <Brain className="h-6 w-6 text-primary" />
              Guía de Conocimientos (RAG)
            </SheetTitle>
            <SheetDescription>
              Entrena y gestiona la memoria a largo plazo de tu asistente.
            </SheetDescription>
          </SheetHeader>
          
          <div className="py-6 space-y-8">
            <section className="space-y-3">
              <h3 className="text-sm font-bold uppercase tracking-wider text-primary">¿Qué es el RAG en Kognito?</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                RAG (Generación Aumentada por Recuperación) permite que el Agente consulte tus documentos personales o corporativos antes de responderte. Es como darle una <strong>biblioteca privada</strong> que solo él puede leer para darte respuestas exactas y citadas.
              </p>
            </section>

            <section className="space-y-3">
              <h3 className="text-sm font-bold uppercase tracking-wider text-primary">Interacción con el Agente</h3>
              <div className="bg-primary/5 rounded-2xl p-4 border border-primary/10 space-y-3">
                <p className="text-xs font-medium text-primary flex items-center gap-2">
                  <Bot className="h-4 w-4" /> El Agente puede ayudarte a:
                </p>
                <ul className="text-xs space-y-2 text-muted-foreground list-disc pl-4">
                  <li><strong>Responder preguntas complexas</strong> basándose en PDFs, Excels o código de GitHub.</li>
                  <li><strong>Cruzar información</strong> entre diferentes colecciones para hallar conexiones.</li>
                  <li><strong>Generar grafos de conocimiento</strong> para visualizar cómo se relacionan las entidades en tus textos.</li>
                  <li><strong>Entrenar su propia memoria</strong> con nuevos archivos que subas.</li>
                </ul>
              </div>
            </section>

            <section className="space-y-3">
              <h3 className="text-sm font-bold uppercase tracking-wider text-primary">Herramientas Avanzadas</h3>
              <div className="grid grid-cols-1 gap-2 text-[11px]">
                <div className="flex items-center gap-2 p-3 rounded-xl bg-orange-500/5 text-orange-600 border border-orange-500/10">
                  <span className="font-bold">KNOWLEDGE GRAPH</span> Convierte texto en una red de nodos y relaciones lógicas para un análisis profundo.
                </div>
                <div className="flex items-center gap-2 p-3 rounded-xl bg-blue-500/5 text-blue-600 border border-blue-500/10">
                  <span className="font-bold">GITHUB REPOS</span> Analiza repositorios enteros y chatea con el código fuente de forma contextual.
                </div>
              </div>
            </section>

            <section className="space-y-3">
              <h3 className="text-sm font-bold uppercase tracking-wider text-primary">Flujo de Trabajo Sugerido</h3>
              <ol className="text-sm space-y-3 text-muted-foreground list-decimal pl-5">
                <li><strong>Crea una Colección:</strong> Agrupa por tema (ej: "Proyectos 2024").</li>
                <li><strong>Sube Documentos:</strong> Soporta PDFs, TXT, Word y más.</li>
                <li><strong>Procesa Grafos:</strong> Opcionalmente, genera la red de conocimientos.</li>
                <li><strong>Consulta:</strong> Chatea con la colección en el botón interactivo de cada tarjeta.</li>
              </ol>
            </section>
          </div>
        </SheetContent>
      </Sheet>
      {selectedCollectionForChat && (
        <ContextualChat
          isOpen={isChatOpen}
          onClose={() => setIsChatOpen(false)}
          title={selectedCollectionForChat.topic}
          context={{
            type: 'collection',
            id: selectedCollectionForChat.topic,
            snapshot: {
              name: selectedCollectionForChat.topic,
              document_count: selectedCollectionForChat.document_count,
              workspace_id: selectedCollectionForChat.workspace_id
            }
          }}
        />
      )}
    </div>
  );
}
