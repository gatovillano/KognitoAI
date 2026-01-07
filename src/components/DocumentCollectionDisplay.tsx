'use client';

import { useEffect, useState, useMemo, useCallback, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Upload, History, Loader2, ScanSearch, FileText, FolderKanban, Text, Sparkles, ChevronDown, MoreHorizontal, Network, Brain, ArrowLeft, Info } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from '@/components/ui/dropdown-menu';
import { useWebSocketContext } from '@/contexts/WebSocketContext';
import { WebSocketMessage } from '@/hooks/useWebSocket';
import { toast } from 'sonner';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { useMediaQuery } from '@/hooks/useMediaQuery';
import { DocumentCard } from '@/app/(dashboard)/rag/document-card';
import { useAuth } from '@/contexts/AuthContext'; // Importar useAuth

import { DataTable } from '@/app/(dashboard)/rag/data-table';
import { getColumns, type Document } from '@/app/(dashboard)/rag/columns';
import apiClient from '@/lib/api';
import { UploadDocumentDialog } from '@/app/(dashboard)/rag/upload-document-dialog';
import { PreviewDocumentDialog } from '@/app/(dashboard)/rag/preview-document-dialog';
import { EditDocumentDialog } from '@/app/(dashboard)/rag/edit-document-dialog';
import { DeleteConfirmationDialog } from '@/app/(dashboard)/rag/delete-confirmation-dialog';
import { AnalysisDetailDialog } from '@/app/(dashboard)/analysis/analysis-detail-dialog';
import UploadProgressIndicator, { UploadTask } from '@/components/UploadProgressIndicator';
import AnalysisProgressIndicator from '@/components/AnalysisProgressIndicator';
import { ShareDocumentDialog } from '@/app/(dashboard)/rag/share-document-dialog';
import { CustomAnalysisDialog } from '@/app/(dashboard)/rag/custom-analysis-dialog';
import { DatasetNameDialog } from '@/app/(dashboard)/rag/dataset-name-dialog';
import { MoveToCollectionDialog } from '@/app/(dashboard)/rag/move-to-collection-dialog';
import { CollectionSearch } from '@/components/CollectionSearch';
import { ContextualChat } from '@/components/ContextualChat';

import { Analysis, AnalysisType } from '@/lib/models';

interface DocumentCollectionDisplayProps {
  topic: string;
  workspaceId?: string;
  collectionName?: string; // Optional, for display purposes in workspace context
  backButtonText?: string; // Nuevo: Texto para el botón de volver
  backButtonHref?: string; // Nuevo: Ruta para el botón de volver
}

export function DocumentCollectionDisplay({ topic, workspaceId, collectionName, backButtonText = "Volver a Colecciones", backButtonHref = "/rag/all" }: DocumentCollectionDisplayProps) {

  const { user } = useAuth(); // Obtener el usuario del contexto de autenticación
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [uploadTasks, setUploadTasks] = useState<UploadTask[]>([]);
  const [collectionDescription, setCollectionDescription] = useState<string | null>(null);
  const isMobile = useMediaQuery('(max-width: 768px)'); // md breakpoint
  const { registerMessageHandler } = useWebSocketContext();

  useEffect(() => {
    if (user?.id) {

    }
  }, [user?.id]);

  const handleUploadStart = (fileNames: string[], topic: string) => {
    const newPlaceholders = fileNames.map(fileName => ({
      id: `placeholder-${fileName}-${Date.now()}`,
      file_name: fileName,
      topic: topic,
      status: 'pending' as const,
      title: 'Pendiente de procesamiento...',
      author: '-',
      created_at: new Date().toISOString(),
      document_type: 'placeholder' as const,
    }));
    setDocuments(prevDocs => [...newPlaceholders, ...prevDocs]);
  };

  // Estados para diálogos
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [documentToPreview, setDocumentToPreview] = useState<Document | null>(null);
  const [documentToEdit, setDocumentToEdit] = useState<Document | null>(null);
  const [documentToDelete, setDocumentToDelete] = useState<Document | null>(null);
  const [documentToShare, setDocumentToShare] = useState<Document | null>(null);
  const [documentToMove, setDocumentToMove] = useState<Document | null>(null);
  const [isShareOpen, setIsShareOpen] = useState(false);
  const [isMoveOpen, setIsMoveOpen] = useState(false);
  const [highlightText, setHighlightText] = useState<string | undefined>(undefined);

  // Estados para análisis
  const [documentToAnalyze, setDocumentToAnalyze] = useState<Document | null>(null);
  const [selectedAnalysis, setSelectedAnalysis] = useState<Analysis | null>(null);
  const [docPollingId, setDocPollingId] = useState<string | null>(null);
  const [collectionPollingId, setCollectionPollingId] = useState<string | null>(null);
  const [currentAnalysisType, setCurrentAnalysisType] = useState<AnalysisType | null>(null);

  // Estado para análisis personalizado
  const [isCustomAnalysisOpen, setIsCustomAnalysisOpen] = useState(false);

  // Estado para el historial de análisis
  const [savedAnalyses, setSavedAnalyses] = useState([]);

  // Estados para el progreso del análisis
  const [analysisProgress, setAnalysisProgress] = useState<number | null>(null);
  const [analysisText, setAnalysisText] = useState<string>("");

  // Estados para procesamiento de grafos de conocimiento
  const [isProcessingKnowledgeGraph, setIsProcessingKnowledgeGraph] = useState(false);

  // Estado para el diálogo de configuración de grafo
  const [isDatasetDialogOpen, setIsDatasetDialogOpen] = useState(false);
  const [processingTopic, setProcessingTopic] = useState<string | null>(null);
  const [processingWorkspaceId, setProcessingWorkspaceId] = useState<string | null>(null);
  const [isChatOpen, setIsChatOpen] = useState(false);

  const fetchPageData = useCallback(async () => {
    setIsLoading(true);
    try {
      const commonParams = { topic: topic, ...(workspaceId && { workspace_id: workspaceId }) };
      const [docsRes, analysesRes, collectionRes] = await Promise.all([
        apiClient.get('/api/documents/list-documents', { params: commonParams }),
        apiClient.post('/api/get-saved-analyses', commonParams),
        apiClient.get(`/api/collections/${topic}/details`, { params: workspaceId ? { workspace_id: workspaceId } : {} })
      ]);

      const serverDocuments = docsRes.data;

      const savedAnalysesData = analysesRes.data;
      const collectionData = collectionRes.data;

      setDocuments(prevDocs => {
        // Filtramos los placeholders que aún están pendientes o procesando
        const pendingPlaceholders = prevDocs.filter(
          p => p.document_type === 'placeholder' && !serverDocuments.some((d: Document) => d.file_name === p.file_name)
        );
        // Combinamos los documentos del servidor con los placeholders que aún no han terminado
        return [...pendingPlaceholders, ...serverDocuments];
      });

      setSavedAnalyses(savedAnalysesData);
      setCollectionDescription(collectionData.description || null);

    } catch (error) {
      toast.error('Error al cargar los datos de la colección.');
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  }, [topic, workspaceId]);

  // WebSocket para actualizaciones en tiempo real
  const onTitleUpdated = (message: WebSocketMessage) => {
    if (!message || !message.file_name) {
      console.error("Received undefined message or file_name in onTitleUpdated", message);
      return;
    }
    setDocuments(prevDocs =>
      prevDocs.map(doc =>
        doc.file_name === message.file_name ? { ...doc, title: message.new_title } : doc
      )
    );
  };

  const onTitleUpdatedRef = useRef(onTitleUpdated);
  useEffect(() => {
    onTitleUpdatedRef.current = onTitleUpdated;
  });

  const onTitleExtractionCompleted = useCallback((data: { updated_count: number; total_processed: number; message: string }) => {
    if (!data) {
      console.error("Received undefined data in onTitleExtractionCompleted", data);
      return;
    }
    toast.success(data.message || `Extracción de títulos completada.`);
  }, []);

  const onUploadStarted = useCallback((message: WebSocketMessage) => {
    console.log("onUploadStarted received message:", message); // Log para depuración
    if (!message || !message.task_id) {
      console.error("Received undefined message or task_id in onUploadStarted", message);
      return;
    }
    setUploadTasks(prev => [...prev, { id: message.task_id, status: 'processing', file_names: message.file_names, topic: message.topic, created_at: message.created_at }]);
  }, []);

  const onUploadProgress = useCallback((data: { task_id: string; progress: number; message: string; }) => {
    if (!data || !data.task_id) {
      console.error("Received undefined data or task_id in onUploadProgress", data);
      return;
    }
    setUploadTasks(prev => prev.map(task => task.id === data.task_id ? { ...task, progress: data.progress } : task));
  }, []);

  const onUploadCompleted = useCallback((data: { task_id: string; message: string; }) => {
    if (!data || !data.task_id) {
      console.error("Received undefined data or task_id in onUploadCompleted", data);
      return;
    }
    toast.success(data.message || 'Subida completada.');
    setUploadTasks(prev => prev.filter(task => task.id !== data.task_id));
    fetchPageData();
  }, [fetchPageData]);

  const onUploadFailed = useCallback((data: { task_id: string; error_message: string; }) => {
    if (!data || !data.task_id) {
      console.error("Received undefined data or task_id in onUploadFailed", data);
      return;
    }
    toast.error(data.error_message || 'Falló la subida de archivos.');
    setUploadTasks(prev => prev.filter(task => task.id !== data.task_id));
    fetchPageData(); // Recargar para limpiar
  }, [fetchPageData]);

  const onDocumentProcessingStarted = useCallback((message: WebSocketMessage) => {
    if (!message || !message.file_name) {
      console.error("Received undefined message or file_name in onDocumentProcessingStarted", message);
      return;
    }
    setDocuments(prevDocs => {
      const docIndex = prevDocs.findIndex(d => d.file_name === message.file_name && d.document_type === 'placeholder');

      if (docIndex !== -1) {
        // Si ya existe un placeholder, actualízalo a "Procesando"
        const newDocs = [...prevDocs];
        newDocs[docIndex] = { ...prevDocs[docIndex], status: 'processing' as const, title: 'Procesando...' };
        return newDocs;
      } else {
        // Si no existe (por una condición de carrera), créalo ahora
        const newPlaceholder: Document = {
          id: `placeholder-${message.file_name}-${Date.now()}`,
          file_name: message.file_name,
          topic: topic,
          status: 'processing' as const,
          title: 'Procesando...',
          author: '-',
          created_at: new Date().toISOString(),
          document_type: 'placeholder' as const,
        };
        return [newPlaceholder, ...prevDocs];
      }
    });
  }, [topic]);

  const onDocumentProcessingCompleted = useCallback((message: WebSocketMessage) => {
    if (!message || !message.file_name) {
      console.error("Received undefined message or file_name in onDocumentProcessingCompleted", message);
      return;
    }
    toast.success(`"${message.file_name}" procesado con éxito.`);
    // Simplemente recargamos los datos. La nueva lógica en fetchPageData se encargará
    // de reemplazar el placeholder con el documento real sin afectar a los demás.
    fetchPageData();
  }, [fetchPageData]);

  const onDocumentProcessingFailed = useCallback((message: WebSocketMessage) => {
    if (!message || !message.file_name) {
      console.error("Received undefined message or file_name in onDocumentProcessingFailed", message);
      return;
    }
    toast.error(`Error procesando "${message.file_name}"`, { description: message.error });
    // Actualizamos el placeholder a un estado de error
    setDocuments(prevDocs => prevDocs.map(doc =>
      doc.file_name === message.file_name ? { ...doc, status: 'failed', title: 'Error de procesamiento' } : doc
    ));
  }, []);

  const onKnowledgeGraphProgress = useCallback((data: any) => {
    if (!data) return;

    setAnalysisProgress(data.progress_percent);
    setAnalysisText(data.message);

    if (data.is_complete || data.has_error) {
      setIsProcessingKnowledgeGraph(false);
      // Limpiar el progreso después de un momento
      setTimeout(() => {
        setAnalysisProgress(null);
        setAnalysisText("");
      }, 3000);

      if (data.is_complete) {
        toast.success("Procesamiento de grafo completado");
        fetchPageData();
      } else {
        toast.error(`Error en procesamiento de grafo: ${data.error}`);
      }
    } else {
      setIsProcessingKnowledgeGraph(true);
    }
  }, [fetchPageData]);





  useEffect(() => {
    const handleWebSocketMessage = (message: WebSocketMessage) => {
      console.log("WebSocket message received:", message); // Log para depuración
      if (!message) return;

      switch (message.type) {
        case 'title_updated':
          onTitleUpdatedRef.current(message);
          break;
        case 'title_extraction_completed':
          onTitleExtractionCompleted(message.data || message);
          break;
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
        case 'document_processing_started':
          onDocumentProcessingStarted(message.data || message);
          break;
        case 'document_processing_completed':
          onDocumentProcessingCompleted(message.data || message);
          break;
        case 'document_processing_failed':
          onDocumentProcessingFailed(message.data || message);
          break;
        case 'knowledge_graph_progress':
          onKnowledgeGraphProgress(message.data || message);
          break;
      }
    };

    const unregister = registerMessageHandler(handleWebSocketMessage);
    return unregister;
  }, [
    registerMessageHandler,
    onDocumentProcessingCompleted,
    onDocumentProcessingFailed,
    onDocumentProcessingStarted,
    onTitleExtractionCompleted,
    onUploadCompleted,
    onUploadFailed,
    onUploadProgress,
    onUploadStarted,
    onKnowledgeGraphProgress,
  ]);

  useEffect(() => {
    fetchPageData();
  }, [fetchPageData]);

  // --- Handlers de Análisis ---

  const handleAnalyzeDocument = useCallback(async (doc: Document) => {
    if (docPollingId || collectionPollingId) { toast.info("Ya hay un análisis en progreso."); return; }
    setDocumentToAnalyze(doc);
    setCurrentAnalysisType('document');
    try {
      const response = await apiClient.post('/api/start-document-analysis', { file_name: doc.file_name, ...(workspaceId && { workspace_id: workspaceId }) });
      setDocPollingId(response.data.task_id);
      toast.info(`Análisis para "${doc.file_name}" iniciado.`);
    } catch (error) { toast.error("No se pudo iniciar el análisis del documento."); }
  }, [docPollingId, collectionPollingId, workspaceId]);

  const handleAnalyzeCollection = async () => {
    if (docPollingId || collectionPollingId) { toast.info("Ya hay un análisis en progreso."); return; }
    setCurrentAnalysisType('collection');
    try {
      const response = await apiClient.post('/api/start-collection-analysis', { topic, ...(workspaceId && { workspace_id: workspaceId }) });
      setCollectionPollingId(response.data.task_id);
      toast.info(`Análisis de la colección "${collectionName || topic}" iniciado.`);
    } catch (error) { toast.error("No se pudo iniciar el análisis de la colección."); }
  };

  // --- Polling para Análisis de Documento ---
  useEffect(() => {
    if (!docPollingId) return;

    const docName = documentToAnalyze?.file_name || 'el documento';
    setAnalysisText(`Analizando ${docName}...`);
    setAnalysisProgress(null);

    const poller = setInterval(async () => {
      try {
        const response = await apiClient.get(`/api/get-analysis-result/${docPollingId}`);
        const { status, result, error, progress } = response.data;

        if (progress !== undefined) {
          setAnalysisProgress(progress);
        }

        if (status === 'completed') {
          clearInterval(poller);
          setDocPollingId(null);

          const newAnalysis: Analysis = {
            id: docPollingId,
            type: 'document',
            title: `Análisis: ${documentToAnalyze?.file_name || "Documento"}`,
            created_at: new Date().toISOString(),
            result: result,
            full_data: result,
            file_name: documentToAnalyze?.file_name,
          };

          setSelectedAnalysis(newAnalysis);
          toast.success("¡Análisis de documento completado!");
          fetchPageData();
          setAnalysisProgress(null);
        } else if (status === 'failed') {
          clearInterval(poller); setDocPollingId(null); toast.error("El análisis del documento falló: " + error);
          setAnalysisProgress(null);
        }
      } catch (err) { clearInterval(poller); setDocPollingId(null); toast.error("Error al consultar el análisis."); setAnalysisProgress(null); }
    }, 5000);
    return () => clearInterval(poller);
  }, [docPollingId, fetchPageData, documentToAnalyze]);

  // --- Polling para Análisis de Colección ---
  useEffect(() => {
    if (!collectionPollingId) return;

    let currentAnalysisText = `Analizando la colección "${collectionName || topic}"...`;
    setAnalysisText(currentAnalysisText);
    setAnalysisProgress(null);

    const poller = setInterval(async () => {
      try {
        const response = await apiClient.get(`/api/get-analysis-result/${collectionPollingId}`);
        const { status, result, error, progress } = response.data;

        if (progress !== undefined) {
          setAnalysisProgress(progress);
        }

        if (status === 'completed') {
          clearInterval(poller);
          setCollectionPollingId(null);

          const analysisType = result?.analysis_metadata?.analysis_type || currentAnalysisType || 'collection';
          let title = `Análisis de Colección: ${collectionName || topic}`;
          if (analysisType === 'semantic_summary') {
            title = `Resumen Semántico: ${collectionName || topic}`;
            toast.success("¡Resumen semántico completado!");
          } else if (analysisType === 'knowledge_graph_analysis') {
            title = `Análisis de Grafo: ${collectionName || topic}`;
            toast.success("¡Análisis de grafo de conocimiento completado!");
          } else {
            toast.success("¡Análisis de colección completado!");
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

          fetchPageData();
          setAnalysisProgress(null);
        } else if (status === 'failed') {
          clearInterval(poller); setCollectionPollingId(null); toast.error("El análisis de la colección falló: " + error);
          setAnalysisProgress(null);
        }
      } catch (err) { clearInterval(poller); setCollectionPollingId(null); toast.error("Error al consultar el análisis."); setAnalysisProgress(null); }
    }, 5000);
    return () => clearInterval(poller);
  }, [collectionPollingId, fetchPageData, collectionName, topic, currentAnalysisType]);

  // --- Handler para Extraer Títulos de la Colección ---
  const handleExtractTitles = async () => {
    if (docPollingId || collectionPollingId) { toast.info("Ya hay un análisis en progreso."); return; }
    try {
      const response = await apiClient.post('/api/documents/extract-title', { topic, ...(workspaceId && { workspace_id: workspaceId }) });
      toast.info(`Extracción de títulos para la colección "${collectionName || topic}" iniciada.`);
    } catch (error) { toast.error("No se pudo iniciar la extracción de títulos."); }
  };

  // --- Handler para Extraer Título de un Documento Individual ---
  const handleExtractTitleForDocument = useCallback(async (doc: Document) => {
    if (docPollingId || collectionPollingId) { toast.info("Ya hay un análisis en progreso."); return; }
    try {
      const response = await apiClient.post('/api/documents/extract-title', { file_name: doc.file_name, ...(workspaceId && { workspace_id: workspaceId }) });
      toast.info(`Extracción de título para "${doc.file_name}" iniciada.`);
    } catch (error) { toast.error(`No se pudo iniciar la extracción de título para "${doc.file_name}".`); }
  }, [docPollingId, collectionPollingId, workspaceId]);

  // --- Handler para Resumen Semántico de la Colección ---
  const handleSemanticSummary = async () => {
    if (docPollingId || collectionPollingId) { toast.info("Ya hay un análisis en progreso."); return; }
    setCurrentAnalysisType('semantic_summary');
    try {
      const response = await apiClient.post('/api/start-semantic-summary', { topic, ...(workspaceId && { workspace_id: workspaceId }) });
      setCollectionPollingId(response.data.task_id);
      toast.info(`Resumen semántico de la colección "${collectionName || topic}" iniciado.`);
    } catch (error) { toast.error("No se pudo iniciar el resumen semántico de la colección."); }
  };

  // --- Handler para Procesar Grafos de Conocimiento ---
  const handleProcessKnowledgeGraph = () => {
    console.log('🔍 handleProcessKnowledgeGraph called with:', { topic, workspaceId });
    if (isProcessingKnowledgeGraph) {
      toast.info("Ya hay un procesamiento de grafo en progreso.");
      return;
    }
    setProcessingTopic(topic);
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
      // Determinar qué endpoint usar basado en el modo
      if (mode === 'conceptual') {
        // Modo Conceptual: Usar la herramienta de Cognee
        await apiClient.post('/api/tools/run', {
          tool_name: "cognee_knowledge_graph",
          action: "process_documents",
          dataset_name: datasetName,  // Nombre para organizar el grafo
          topic: processingTopic || undefined,  // Nombre de la colección para filtrar documentos
          document_titles: documents.map(doc => doc.file_name), // Pasa los títulos de los documentos
          workspace_id: processingWorkspaceId || undefined  // Workspace de la colección específica
        });
      } else {
        // Modo Híbrido (Estándar): Llamar al endpoint optimizado
        await apiClient.post('/api/knowledge-graph/process-knowledge-graph-optimized', {
          workspace_id: processingWorkspaceId || undefined,
          dataset_name: datasetName,
          topic: processingTopic || undefined,  // Filtrar por colección específica
          force_reprocess: true
        });
      }

      toast.success(
        `¡Creación de grafo iniciada!`,
        { id: toastId }
      );
    } catch (error) {
      console.error(error);
      toast.error("Error al iniciar el procesamiento del grafo.", { id: toastId });
    } finally {
      setProcessingTopic(null);
      setProcessingWorkspaceId(null);
    }
  };

  // --- Handler para Análisis de Grafo de Conocimiento ---
  const handleKnowledgeGraphAnalysis = async () => {
    if (docPollingId || collectionPollingId) { toast.info("Ya hay un análisis en progreso."); return; }
    setCurrentAnalysisType('knowledge_graph_analysis');
    try {
      const response = await apiClient.post('/api/documents/start-knowledge-graph-analysis', { topic, ...(workspaceId && { workspace_id: workspaceId }) });
      setCollectionPollingId(response.data.task_id);
      toast.info(`Análisis de Grafo de Conocimiento para la colección "${collectionName || topic}" iniciado.`);
    } catch (error) { toast.error("No se pudo iniciar el análisis de grafo de conocimiento."); }
  };

  const columns = useMemo(() => getColumns(
    (doc) => setDocumentToPreview(doc),
    (doc) => setDocumentToEdit(doc),
    (doc) => setDocumentToDelete(doc),
    handleAnalyzeDocument,
    (doc) => {
      setDocumentToShare(doc);
      setIsShareOpen(true);
    },
    handleExtractTitleForDocument,
    (doc) => {
      setDocumentToMove(doc);
      setIsMoveOpen(true);
    }
  ), [handleAnalyzeDocument, handleExtractTitleForDocument]);

  const router = useRouter();

  if (isLoading) {
    return (
      <div className="flex h-[calc(100vh-200px)] w-full items-center justify-center">
        <div className="flex flex-col items-center gap-2">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-muted-foreground">Cargando datos de la colección...</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="mb-4">
        <Button
          variant="ghost"
          onClick={() => router.push(backButtonHref)}
          className="px-2 py-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="mr-1 h-4 w-4" />
          {backButtonText}
        </Button>
      </div>
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center mb-6 gap-4">
        <div className="flex items-center gap-2"> {/* New div for title and tooltip */}
          {collectionName && <h1 className="text-2xl font-bold">{collectionName}</h1>}
          {collectionDescription && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon" className="ml-1 h-6 w-6 text-muted-foreground">
                    <Info className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent className="max-w-xs">
                  <p>{collectionDescription}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" className="gap-2" disabled={!!docPollingId || !!collectionPollingId || isProcessingKnowledgeGraph}>
                <MoreHorizontal className="h-4 w-4" />
                <span className="hidden sm:inline">Acciones</span>
                <ChevronDown className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuItem onClick={() => setIsChatOpen(true)}>
                <Brain className="mr-2 h-4 w-4 text-primary" />
                <span className="font-medium text-primary">Chatear con Colección</span>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => setIsUploadOpen(true)}>
                <Upload className="mr-2 h-4 w-4" />
                <span>Subir Documentos</span>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleAnalyzeCollection} disabled={!!docPollingId || !!collectionPollingId}>
                <ScanSearch className="mr-2 h-4 w-4" />
                <span>Analizar Colección</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={handleSemanticSummary} disabled={!!docPollingId || !!collectionPollingId}>
                <ScanSearch className="mr-2 h-4 w-4" />
                <span>Resumen Semántico</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setIsCustomAnalysisOpen(true)} disabled={!!docPollingId || !!collectionPollingId}>
                <Sparkles className="mr-2 h-4 w-4" />
                <span>Análisis Personalizado</span>
              </DropdownMenuItem>

              <DropdownMenuItem onClick={handleExtractTitles} disabled={!!docPollingId || !!collectionPollingId}>
                <Text className="mr-2 h-4 w-4" />
                <span>Extraer Títulos</span>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleProcessKnowledgeGraph} disabled={isProcessingKnowledgeGraph}>
                <Network className="mr-2 h-4 w-4" />
                <span>Crear Grafo</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={handleKnowledgeGraphAnalysis} disabled={!!docPollingId || !!collectionPollingId}>
                <Brain className="mr-2 h-4 w-4" />
                <span>Análisis de Grafo de Conocimiento</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {(docPollingId || collectionPollingId || isProcessingKnowledgeGraph) && (
        <AnalysisProgressIndicator progress={analysisProgress} text={analysisText} />
      )}

      {uploadTasks.length > 0 && (
        <div className="fixed bottom-6 right-6 z-50 w-80"><UploadProgressIndicator tasks={uploadTasks} /></div>
      )}

      <div className="space-y-6">
        {/* Componente de búsqueda */}
        <CollectionSearch
          topic={topic}
          accountId={user?.id || ''}
          workspaceId={workspaceId}
          onResultClick={(result) => {
            // Buscar el documento completo en la lista de documentos
            const doc = documents.find(d => d.file_name === result.file_name);
            if (doc) {
              setDocumentToPreview(doc);
              setHighlightText(result.content); // Establecer el texto a resaltar
            } else {
              toast.info(`Documento: ${result.file_name}`, {
                description: result.content.substring(0, 200) + '...'
              });
            }
          }}
        />

        <Card>
          <CardHeader>
            <CardTitle>Documentos en la Colección</CardTitle>
          </CardHeader>
          <CardContent>
            {isMobile ? (
              <div className="grid grid-cols-1 gap-4">
                {documents.map((document) => (
                  <DocumentCard
                    key={document.id}
                    document={document}
                    onPreview={(doc) => setDocumentToPreview(doc)}
                    onEdit={(doc) => setDocumentToEdit(doc)}
                    onDelete={(doc) => setDocumentToDelete(doc)}
                    onAnalyze={handleAnalyzeDocument}
                    onShare={(doc) => {
                      setDocumentToShare(doc);
                      setIsShareOpen(true);
                    }}
                    onExtractTitle={handleExtractTitleForDocument}
                    onMoveToCollection={(doc) => {
                      setDocumentToMove(doc);
                      setIsMoveOpen(true);
                    }}
                  />
                ))}
              </div>
            ) : (
              <div className="overflow-x-auto w-full">
                <DataTable columns={columns} data={documents} />
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <History className="h-6 w-6" />
              Historial de Análisis
            </CardTitle>
          </CardHeader>
          <CardContent>
            {savedAnalyses.length > 0 ? (
              <div className="w-full overflow-y-auto">
                <Accordion type="single" collapsible className="w-full">
                  {savedAnalyses.map((analysis: any) => (
                    <AccordionItem value={`item-${analysis.id}`} key={analysis.id}>
                      <AccordionTrigger>
                        <div className="flex items-center gap-2 text-left flex-1 min-w-0">
                          {analysis.file_name.startsWith('Resumen Semántico:') ? <Brain className="h-4 w-4" /> :
                            analysis.file_name.startsWith('Colección:') ? <FolderKanban className="h-4 w-4" /> : <FileText className="h-4 w-4" />}
                          <span className="font-medium truncate">{analysis.file_name}</span>
                          <span className="ml-auto text-xs text-muted-foreground pr-4">{new Date(analysis.created_at).toLocaleDateString()}</span>
                        </div>
                      </AccordionTrigger>
                      <AccordionContent>
                        <div className="space-y-3">
                          {/* Mostrar resumen según el tipo de análisis */}
                          {analysis.file_name.startsWith('Colección:') && analysis.result_payload?.collection_summary && (
                            <div className="p-3 bg-muted rounded-lg">
                              <h4 className="font-medium text-sm mb-2">Resumen de la Colección:</h4>
                              <p className="text-sm text-muted-foreground">
                                {analysis.result_payload.collection_summary}
                              </p>
                            </div>
                          )}

                          {analysis.file_name.startsWith('Resumen Semántico:') && analysis.result_payload?.resumen_semantico && (
                            <div className="p-3 bg-muted rounded-lg">
                              <h4 className="font-medium text-sm mb-2">Resumen Semántico:</h4>
                              <p className="text-sm text-muted-foreground">
                                {analysis.result_payload.resumen_semantico}
                              </p>
                            </div>
                          )}

                          {analysis.file_name.startsWith('Análisis Personalizado:') && analysis.result_payload?.analysis_result && (
                            <div className="p-3 bg-muted rounded-lg">
                              <h4 className="font-medium text-sm mb-2">Resultado del Análisis:</h4>
                              <p className="text-sm text-muted-foreground">
                                {typeof analysis.result_payload.analysis_result === 'string'
                                  ? analysis.result_payload.analysis_result
                                  : JSON.stringify(analysis.result_payload.analysis_result).substring(0, 200) + '...'}
                              </p>
                            </div>
                          )}

                          {analysis.file_name.startsWith('Análisis de Grafo de Conocimiento:') && analysis.result_payload?.graph_summary && (
                            <div className="p-3 bg-muted rounded-lg">
                              <h4 className="font-medium text-sm mb-2">Resumen del Grafo de Conocimiento:</h4>
                              <p className="text-sm text-muted-foreground">
                                {analysis.result_payload.graph_summary}
                              </p>
                            </div>
                          )}

                          {!analysis.file_name.startsWith('Colección:') &&
                            !analysis.file_name.startsWith('Resumen Semántico:') &&
                            !analysis.file_name.startsWith('Análisis Personalizado:') &&
                            !analysis.file_name.startsWith('Análisis de Grafo de Conocimiento:') &&
                            analysis.result_payload?.resumen_ejecutivo && (
                              <div className="p-3 bg-muted rounded-lg">
                                <h4 className="font-medium text-sm mb-2">Resumen Ejecutivo:</h4>
                                <p className="text-sm text-muted-foreground">
                                  {analysis.result_payload.resumen_ejecutivo}
                                </p>
                              </div>
                            )}

                          <Button variant="link" className="p-0 h-auto" onClick={() => {
                            let analysisType: AnalysisType = 'document';
                            const fileName = analysis.file_name || '';

                            if (fileName.startsWith('Resumen Semántico:')) {
                              analysisType = 'semantic_summary';
                            } else if (fileName.startsWith('Colección:')) {
                              analysisType = 'collection';
                            } else if (fileName.startsWith('Análisis Personalizado:')) {
                              analysisType = 'custom_analysis';
                            } else if (fileName.startsWith('Análisis de Grafo de Conocimiento:')) {
                              analysisType = 'knowledge_graph_analysis';
                            }

                            const newAnalysis: Analysis = {
                              id: analysis.id,
                              type: analysisType,
                              title: fileName,
                              created_at: analysis.created_at,
                              result: analysis.result_payload,
                              full_data: analysis.result_payload,
                              file_name: fileName,
                            };

                            setSelectedAnalysis(newAnalysis);
                          }}>
                            Ver Resultados Detallados →
                          </Button>
                        </div>
                      </AccordionContent>
                    </AccordionItem>
                  ))}
                </Accordion>
              </div>
            ) : (
              !isLoading && <p className="text-sm text-muted-foreground text-center py-4">No hay análisis guardados para esta vista.</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Diálogos */}
      <UploadDocumentDialog
        isOpen={isUploadOpen}
        onOpenChange={setIsUploadOpen}
        onUploadSuccess={() => { /* WebSocket handles updates */ }}
        onUploadStart={handleUploadStart} // Conectamos la función para crear placeholders
        defaultTopic={topic}
        workspaceId={workspaceId}
      />
      <PreviewDocumentDialog
        isOpen={!!documentToPreview}
        onOpenChange={(open) => {
          if (!open) {
            setDocumentToPreview(null);
            setHighlightText(undefined);
          }
        }}
        document={documentToPreview}
        highlightText={highlightText}
      />
      <EditDocumentDialog isOpen={!!documentToEdit} onOpenChange={(open) => !open && setDocumentToEdit(null)} onUpdateSuccess={fetchPageData} document={documentToEdit} />
      <DeleteConfirmationDialog isOpen={!!documentToDelete} onOpenChange={(open) => !open && setDocumentToDelete(null)} onDeleteSuccess={fetchPageData} document={documentToDelete} />
      <AnalysisDetailDialog
        analysis={selectedAnalysis}
        isOpen={!!selectedAnalysis}
        onOpenChange={(open) => {
          if (!open) {
            setSelectedAnalysis(null);
          }
        }}
      />
      <ShareDocumentDialog isOpen={isShareOpen} onOpenChange={setIsShareOpen} onShareSuccess={fetchPageData} document={documentToShare} />
      <CustomAnalysisDialog
        isOpen={isCustomAnalysisOpen}
        onOpenChange={setIsCustomAnalysisOpen}
        topic={topic}
        onAnalysisStart={(taskId) => {
          setCollectionPollingId(taskId); // Usar el mismo polling para análisis de colección
          toast.info("Análisis personalizado iniciado. Esperando resultados...");
        }}
      />

      <DatasetNameDialog
        isOpen={isDatasetDialogOpen}
        onOpenChange={setIsDatasetDialogOpen}
        onConfirm={handleConfirmProcessGraph}
        defaultTopic={processingTopic}
        workspaceId={processingWorkspaceId || undefined}
      />

      <MoveToCollectionDialog
        isOpen={isMoveOpen}
        onOpenChange={setIsMoveOpen}
        document={documentToMove}
        onSuccess={fetchPageData}
        workspaceId={workspaceId}
      />

      <ContextualChat
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
        title={collectionName || topic}
        context={{
          type: 'collection',
          id: topic,
          snapshot: {
            name: collectionName || topic,
            document_count: documents.length,
            workspace_id: workspaceId
          }
        }}
      />
    </>
  );
}
