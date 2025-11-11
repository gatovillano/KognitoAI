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
import { AnalysisResultDialog } from '@/app/(dashboard)/rag/analysis-result-dialog';
import UploadProgressIndicator, { UploadTask } from '@/components/UploadProgressIndicator';
import { CollectionAnalysisDialog } from '@/app/(dashboard)/rag/collection-analysis-dialog';
import { SemanticAnalysisDialog } from '@/app/(dashboard)/rag/semantic-analysis-dialog';
import { ShareDocumentDialog } from '@/app/(dashboard)/rag/share-document-dialog';
import { CustomAnalysisDialog } from '@/app/(dashboard)/rag/custom-analysis-dialog';
import { KnowledgeGraphAnalysisDialog } from '@/app/(dashboard)/rag/knowledge-graph-analysis-dialog';

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
  const [isShareOpen, setIsShareOpen] = useState(false);
  
  // Estados para análisis de documento individual
  const [documentToAnalyze, setDocumentToAnalyze] = useState<Document | null>(null);
  const [docAnalysisResult, setDocAnalysisResult] = useState<any>(null);
  const [isDocAnalysisOpen, setIsDocAnalysisOpen] = useState(false);
  const [docPollingId, setDocPollingId] = useState<string | null>(null);

  // Estados para análisis de colección completa
  const [collectionAnalysisResult, setCollectionAnalysisResult] = useState<any>(null);
  const [isCollectionAnalysisOpen, setIsCollectionAnalysisOpen] = useState(false);
  const [collectionPollingId, setCollectionPollingId] = useState<string | null>(null);

  // Estado para análisis personalizado
  const [isCustomAnalysisOpen, setIsCustomAnalysisOpen] = useState(false);

  // Estados para análisis semántico
  const [semanticAnalysisResult, setSemanticAnalysisResult] = useState<any>(null);
  const [isSemanticAnalysisOpen, setIsSemanticAnalysisOpen] = useState(false);

  // Estado para el historial de análisis
  const [savedAnalyses, setSavedAnalyses] = useState([]);

  // Estados para procesamiento de grafos de conocimiento
  const [isProcessingKnowledgeGraph, setIsProcessingKnowledgeGraph] = useState(false);
  // Nuevo estado para el análisis de grafo de conocimiento
  const [knowledgeGraphAnalysisResult, setKnowledgeGraphAnalysisResult] = useState<any>(null);
  const [isKnowledgeGraphAnalysisOpen, setIsKnowledgeGraphAnalysisOpen] = useState(false);

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
  const onTitleUpdated = (data: { file_name: string; new_title: string; progress: number; total: number }) => {
    setDocuments(prevDocs =>
      prevDocs.map(doc =>
        doc.file_name === data.file_name ? { ...doc, title: data.new_title } : doc
      )
    );
  };

  const onTitleUpdatedRef = useRef(onTitleUpdated);
  useEffect(() => {
    onTitleUpdatedRef.current = onTitleUpdated;
  });

  const onTitleExtractionCompleted = useCallback((data: { updated_count: number; total_processed: number; message: string }) => {
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
    setUploadTasks(prev => prev.map(task => task.id === data.task_id ? { ...task, progress: data.progress } : task));
  }, []);

  const onUploadCompleted = useCallback((data: { task_id: string; message: string; }) => {
    toast.success(data.message || 'Subida completada.');
    setUploadTasks(prev => prev.filter(task => task.id !== data.task_id));
    fetchPageData();
  }, [fetchPageData]);

  const onUploadFailed = useCallback((data: { task_id: string; error_message: string; }) => {
    toast.error(data.error_message || 'Falló la subida de archivos.');
    setUploadTasks(prev => prev.filter(task => task.id !== data.task_id));
    fetchPageData(); // Recargar para limpiar
  }, [fetchPageData]);

  const onDocumentProcessingStarted = useCallback((message: WebSocketMessage) => {
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
    toast.success(`"${message.file_name}" procesado con éxito.`);
    // Simplemente recargamos los datos. La nueva lógica en fetchPageData se encargará
    // de reemplazar el placeholder con el documento real sin afectar a los demás.
    fetchPageData();
  }, [fetchPageData]);

  const onDocumentProcessingFailed = useCallback((message: WebSocketMessage) => {
    toast.error(`Error procesando "${message.file_name}"`, { description: message.error });
    // Actualizamos el placeholder a un estado de error
    setDocuments(prevDocs => prevDocs.map(doc => 
      doc.file_name === message.file_name ? { ...doc, status: 'failed', title: 'Error de procesamiento' } : doc
    ));
  }, []);





  useEffect(() => {
    const handleWebSocketMessage = (message: WebSocketMessage) => {
      console.log("WebSocket message received:", message); // Log para depuración
      if (!message) return;

      switch (message.type) {
        case 'title_updated':
          onTitleUpdatedRef.current(message.data);
          break;
        case 'title_extraction_completed':
          onTitleExtractionCompleted(message.data);
          break;
        case 'upload_started':
          onUploadStarted(message);
          break;
        case 'upload_progress':
          onUploadProgress(message.data);
          break;
        case 'upload_completed':
          onUploadCompleted(message.data);
          break;
        case 'upload_failed':
          onUploadFailed(message.data);
          break;
        case 'document_processing_started':
          onDocumentProcessingStarted(message);
          break;
        case 'document_processing_completed':
          onDocumentProcessingCompleted(message);
          break;
        case 'document_processing_failed':
          onDocumentProcessingFailed(message);
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
  ]);

  useEffect(() => {
    fetchPageData();
  }, [fetchPageData]);

  // --- Handlers de Análisis ---

  const handleAnalyzeDocument = useCallback(async (doc: Document) => {
    if (docPollingId || collectionPollingId) { toast.info("Ya hay un análisis en progreso."); return; }
    setDocumentToAnalyze(doc);
    try {
      const response = await apiClient.post('/api/start-document-analysis', { file_name: doc.file_name, ...(workspaceId && { workspace_id: workspaceId }) });
      setDocPollingId(response.data.task_id);
      toast.info(`Análisis para "${doc.file_name}" iniciado.`);
    } catch (error) { toast.error("No se pudo iniciar el análisis del documento."); }
  }, [docPollingId, collectionPollingId, workspaceId]);
  
  const handleAnalyzeCollection = async () => {
    if (docPollingId || collectionPollingId) { toast.info("Ya hay un análisis en progreso."); return; }
    try {
      const response = await apiClient.post('/api/start-collection-analysis', { topic, ...(workspaceId && { workspace_id: workspaceId }) });
      setCollectionPollingId(response.data.task_id);
      toast.info(`Análisis de la colección "${collectionName || topic}" iniciado.`);
    } catch (error) { toast.error("No se pudo iniciar el análisis de la colección."); }
  };

  // --- Polling para Análisis de Documento ---
  useEffect(() => {
    if (!docPollingId) return;
    const poller = setInterval(async () => {
      try {
        const response = await apiClient.get(`/api/get-analysis-result/${docPollingId}`);
        const { status, result, error } = response.data;
        if (status === 'completed') {
          clearInterval(poller); setDocPollingId(null); setDocAnalysisResult(result);
          setIsDocAnalysisOpen(true); toast.success("¡Análisis de documento completado!"); fetchPageData();
        } else if (status === 'failed') {
          clearInterval(poller); setDocPollingId(null); toast.error("El análisis del documento falló: " + error);
        }
      } catch (err) { clearInterval(poller); setDocPollingId(null); toast.error("Error al consultar el análisis."); }
    }, 5000);
    return () => clearInterval(poller);
  }, [docPollingId, fetchPageData]);

  // --- Polling para Análisis de Colección ---
  useEffect(() => {
    if (!collectionPollingId) return;
    const poller = setInterval(async () => {
      try {
        const response = await apiClient.get(`/api/get-analysis-result/${collectionPollingId}`);
        const { status, result, error } = response.data;
        if (status === 'completed') {
          clearInterval(poller); setCollectionPollingId(null);
          // Verificar si es análisis semántico o de grafo de conocimiento
          if (result?.analysis_metadata?.analysis_type === 'semantic_summary') {
            setSemanticAnalysisResult(result);
            setIsSemanticAnalysisOpen(true);
            toast.success("¡Resumen semántico completado!");
          } else if (result?.analysis_metadata?.analysis_type === 'knowledge_graph_analysis') {
            setKnowledgeGraphAnalysisResult(result);
            setIsKnowledgeGraphAnalysisOpen(true);
            toast.success("¡Análisis de grafo de conocimiento completado!");
          } else {
            setCollectionAnalysisResult(result);
            setIsCollectionAnalysisOpen(true);
            toast.success("¡Análisis de colección completado!");
          }
          fetchPageData();
        } else if (status === 'failed') {
          clearInterval(poller); setCollectionPollingId(null); toast.error("El análisis de la colección falló: " + error);
        }
      } catch (err) { clearInterval(poller); setCollectionPollingId(null); toast.error("Error al consultar el análisis."); }
    }, 5000);
    return () => clearInterval(poller);
  }, [collectionPollingId, fetchPageData]);

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
    try {
      const response = await apiClient.post('/api/start-semantic-summary', { topic, ...(workspaceId && { workspace_id: workspaceId }) });
      setCollectionPollingId(response.data.task_id);
      toast.info(`Resumen semántico de la colección "${collectionName || topic}" iniciado.`);
    } catch (error) { toast.error("No se pudo iniciar el resumen semántico de la colección."); }
  };

  // --- Handler para Procesar Grafos de Conocimiento ---
  const handleProcessKnowledgeGraph = async () => {
    if (isProcessingKnowledgeGraph) {
      toast.info("Ya hay un procesamiento de grafo en progreso.");
      return;
    }

    setIsProcessingKnowledgeGraph(true);
    const toastId = toast.loading(`Procesando grafo de conocimiento para "${collectionName || topic}"...`);

    try {
      const payload = {
        tool_name: "cognee_knowledge_graph",
        action: "process_documents",
        dataset_name: topic,
        documents: [], // Se podría añadir lógica para obtener documentos si es necesario
        ...(workspaceId && { workspace_id: workspaceId })
      };

      const response = await apiClient.post('/api/tools/run', payload);

      toast.success(
        `¡Creación de grafo iniciada!`,
        { id: toastId }
      );
    } catch (error) {
      toast.error("Error al iniciar el procesamiento del grafo de conocimiento.", { id: toastId });
    } finally {
      setIsProcessingKnowledgeGraph(false);
    }
  };

  // --- Handler para Análisis de Grafo de Conocimiento ---
  const handleKnowledgeGraphAnalysis = async () => {
    if (docPollingId || collectionPollingId) { toast.info("Ya hay un análisis en progreso."); return; }
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
      handleExtractTitleForDocument
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
      
      {(docPollingId || collectionPollingId) && (
        <div className="bg-muted text-muted-foreground p-3 rounded-md mb-4 flex items-center gap-2 text-sm animate-pulse">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Un análisis está en progreso. La interfaz sigue siendo funcional...</span>
        </div>
      )}

      {uploadTasks.length > 0 && (
        <div className="fixed bottom-6 right-6 z-50 w-80"><UploadProgressIndicator tasks={uploadTasks} /></div>
      )}

      <div className="space-y-6">
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
                          if (analysis.file_name.startsWith('Resumen Semántico:')) {
                            setSemanticAnalysisResult(analysis.result_payload);
                            setIsSemanticAnalysisOpen(true);
                          } else if (analysis.file_name.startsWith('Colección:')) {
                            setCollectionAnalysisResult(analysis.result_payload);
                            setIsCollectionAnalysisOpen(true);
                          } else if (analysis.file_name.startsWith('Análisis Personalizado:')) {
                            setDocAnalysisResult(analysis.result_payload);
                            setIsDocAnalysisOpen(true);
                          } else if (analysis.file_name.startsWith('Análisis de Grafo de Conocimiento:')) {
                            setKnowledgeGraphAnalysisResult(analysis.result_payload);
                            setIsKnowledgeGraphAnalysisOpen(true);
                          } else {
                            setDocAnalysisResult(analysis.result_payload);
                            setDocumentToAnalyze({ file_name: analysis.file_name, topic, title: '', author: '' });
                            setIsDocAnalysisOpen(true);
                          }
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
      <PreviewDocumentDialog isOpen={!!documentToPreview} onOpenChange={(open) => !open && setDocumentToPreview(null)} document={documentToPreview} />
      <EditDocumentDialog isOpen={!!documentToEdit} onOpenChange={(open) => !open && setDocumentToEdit(null)} onUpdateSuccess={fetchPageData} document={documentToEdit} />
      <DeleteConfirmationDialog isOpen={!!documentToDelete} onOpenChange={(open) => !open && setDocumentToDelete(null)} onDeleteSuccess={fetchPageData} document={documentToDelete} />
      <AnalysisResultDialog isOpen={isDocAnalysisOpen} onOpenChange={setIsDocAnalysisOpen} analysis={docAnalysisResult} document={documentToAnalyze ?? { file_name: '', topic: topic, title: '', author: '' }} />
      <CollectionAnalysisDialog isOpen={isCollectionAnalysisOpen} onOpenChange={setIsCollectionAnalysisOpen} analysis={collectionAnalysisResult} topic={topic} />
      <SemanticAnalysisDialog isOpen={isSemanticAnalysisOpen} onOpenChange={setIsSemanticAnalysisOpen} analysis={semanticAnalysisResult} topic={topic} />
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

      <KnowledgeGraphAnalysisDialog
        isOpen={isKnowledgeGraphAnalysisOpen}
        onOpenChange={setIsKnowledgeGraphAnalysisOpen}
        analysis={knowledgeGraphAnalysisResult}
      />
    </>
  );
}
