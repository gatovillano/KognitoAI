// En: src/app/(dashboard)/rag/all/page.tsx

'use client';

import { useEffect, useState, useMemo, useCallback } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { ArrowLeft, Upload, History, FileText, FolderKanban, Brain, MoreHorizontal, ChevronDown, ScanSearch, Sparkles, Text, Network, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from '@/components/ui/dropdown-menu';

// Importaciones de componentes del directorio padre 'rag'
import { DataTable } from '../data-table';
import { getColumns, type Document } from '../columns';
import apiClient from '@/lib/api';
import { UploadDocumentDialog } from '../upload-document-dialog';
import { PreviewDocumentDialog } from '../preview-document-dialog';
import { EditDocumentDialog } from '../edit-document-dialog';
import { DeleteConfirmationDialog } from '../delete-confirmation-dialog';
import { AnalysisResultDialog } from '../analysis-result-dialog';
import { CollectionAnalysisDialog } from '../collection-analysis-dialog'; // Aunque no lo iniciamos aquí, lo necesitamos por si el usuario abre un análisis guardado de colección
import { SemanticAnalysisDialog } from '../semantic-analysis-dialog';
import { CustomAnalysisDialog } from '../custom-analysis-dialog'; // Nueva importación

export default function AllDocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  // Estados para los diálogos
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [documentToPreview, setDocumentToPreview] = useState<Document | null>(null);
  const [documentToEdit, setDocumentToEdit] = useState<Document | null>(null);
  const [documentToDelete, setDocumentToDelete] = useState<Document | null>(null);
  const [uploadingFiles, setUploadingFiles] = useState<string[]>([]);
  const [uploadTopic, setUploadTopic] = useState<string>('');
  
  // Estados para el análisis
  const [documentToAnalyze, setDocumentToAnalyze] = useState<Document | null>(null);
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [isAnalysisDialogOpen, setIsAnalysisDialogOpen] = useState(false);
  const [isCollectionAnalysisOpen, setIsCollectionAnalysisOpen] = useState(false); // Necesario para el diálogo
  const [isSemanticAnalysisOpen, setIsSemanticAnalysisOpen] = useState(false); // Para análisis semánticos
  const [docPollingId, setDocPollingId] = useState<string | null>(null);
  const [collectionPollingId, setCollectionPollingId] = useState<string | null>(null); // Nuevo estado para polling de colección
  const [isProcessingKnowledgeGraph, setIsProcessingKnowledgeGraph] = useState(false); // Nuevo estado para grafo de conocimiento
  const [isCustomAnalysisOpen, setIsCustomAnalysisOpen] = useState(false); // Nuevo estado para análisis personalizado

  // Estado para el historial
  const [savedAnalyses, setSavedAnalyses] = useState([]);

  const fetchPageData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [docsRes, analysesRes] = await Promise.all([
        apiClient.get('/api/list-documents'),
        // --- CAMBIO CLAVE: Pedimos TODOS los análisis guardados ---
        apiClient.post('/api/get-saved-analyses', { all: true })
      ]);
      setDocuments(docsRes.data);
      setSavedAnalyses(analysesRes.data);
    } catch (error) {
      toast.error('Error al cargar los datos.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPageData();
  }, [fetchPageData]);

  // Polling para el análisis de documento
  useEffect(() => {
    const pollDocumentAnalysis = async () => {
      if (docPollingId) {
        try {
          const response = await apiClient.get(`/api/get-analysis-result/${docPollingId}`);
          if (response.data.status === 'completed') {
            setAnalysisResult(response.data.result);
            setIsAnalysisDialogOpen(true);
            setDocPollingId(null);
            toast.success("¡Análisis completado!");
            fetchPageData(); // Refresca la lista de análisis guardados
          } else if (response.data.status === 'failed') {
            toast.error(`Error en el análisis: ${response.data.error || 'Error desconocido'}`);
            setDocPollingId(null);
          }
        } catch (error) {
          toast.error("Error al verificar el estado del análisis.");
          console.error(error);
          setDocPollingId(null);
        }
      }
    };

    if (docPollingId) {
      const interval = setInterval(pollDocumentAnalysis, 3000);
      return () => clearInterval(interval);
    }
  }, [docPollingId, fetchPageData]);

  // Polling para análisis de colección/semántico/personalizado
  useEffect(() => {
    if (!collectionPollingId) return;
    const poller = setInterval(async () => {
      try {
        const response = await apiClient.get(`/api/get-analysis-result/${collectionPollingId}`);
        const { status, result, error } = response.data;
        if (status === 'completed') {
          clearInterval(poller); setCollectionPollingId(null);
          if (result?.analysis_metadata?.analysis_type === 'semantic_summary') {
            setAnalysisResult(result); // Reutilizamos analysisResult para el diálogo semántico
            setIsSemanticAnalysisOpen(true);
            toast.success("¡Resumen semántico completado!");
          } else if (result?.analysis_metadata?.analysis_type === 'custom_analysis') {
            setAnalysisResult(result); // Reutilizamos analysisResult para el diálogo de análisis personalizado
            setIsAnalysisDialogOpen(true); // Usamos el diálogo de análisis de documento para mostrar el resultado
            toast.success("¡Análisis personalizado completado!");
          } else {
            setAnalysisResult(result); // Reutilizamos analysisResult para el diálogo de colección
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

  const handleAnalyzeDocument = useCallback(async (doc: Document) => {
    if (docPollingId || collectionPollingId) {
      toast.info('Ya hay un análisis en progreso');
      return;
    }
    setDocumentToAnalyze(doc);
    try {
      const response = await apiClient.post('/api/start-document-analysis', { file_name: doc.file_name });
      setDocPollingId(response.data.task_id);
      toast.info(`Análisis para "${doc.file_name}" iniciado`);
    } catch (error) {
      toast.error('No se pudo iniciar el análisis del documento');
    }
  }, [docPollingId, collectionPollingId]);

  const handleAnalyzeCollection = async () => {
    if (docPollingId || collectionPollingId) { toast.info("Ya hay un análisis en progreso."); return; }
    try {
      const response = await apiClient.post('/api/start-collection-analysis', { topic: 'all_documents' }); // Usamos 'all_documents' como topic
      setCollectionPollingId(response.data.task_id);
      toast.info(`Análisis de la colección "Todos los Documentos" iniciado.`);
    } catch (error) { toast.error("No se pudo iniciar el análisis de la colección."); }
  };

  const handleSemanticSummary = async () => {
    if (docPollingId || collectionPollingId) { toast.info("Ya hay un análisis en progreso."); return; }
    try {
      const response = await apiClient.post('/api/start-semantic-summary', { topic: 'all_documents' }); // Usamos 'all_documents' como topic
      setCollectionPollingId(response.data.task_id);
      toast.info(`Resumen semántico de la colección "Todos los Documentos" iniciado.`);
    } catch (error) { toast.error("No se pudo iniciar el resumen semántico de la colección."); }
  };

  const handleExtractTitles = async () => {
    if (docPollingId || collectionPollingId) { toast.info("Ya hay un análisis en progreso."); return; }
    try {
      const response = await apiClient.post('/api/extract-title', { topic: 'all_documents' }); // Usamos 'all_documents' como topic
      toast.info(`Extracción de títulos para la colección "Todos los Documentos" iniciada.`);
      fetchPageData();
    } catch (error) { toast.error("No se pudo iniciar la extracción de títulos."); }
  };

  const handleProcessKnowledgeGraph = async () => {
    if (isProcessingKnowledgeGraph) {
      toast.info("Ya hay un procesamiento de grafo en progreso.");
      return;
    }

    setIsProcessingKnowledgeGraph(true);
    const toastId = toast.loading(`Procesando grafo de conocimiento para "Todos los Documentos"...`);

    try {
      const response = await apiClient.post('/api/process-knowledge-graph', { topic: 'all_documents' }); // Usamos 'all_documents' como topic
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

  const handleUploadStart = useCallback((fileNames: string[], topic: string) => {
    setUploadingFiles(fileNames);
    setUploadTopic(topic);
  }, []);
  
  const columns = useMemo(() => getColumns(
      (doc) => setDocumentToPreview(doc),
      (doc) => setDocumentToEdit(doc),
      (doc) => setDocumentToDelete(doc),
      handleAnalyzeDocument
  ), [handleAnalyzeDocument]); // useCallback envuelve el handler para que no cambie

  return (
    <div className="p-4 sm:p-8 max-w-7xl mx-auto overflow-x-hidden">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-4 gap-2">
        <div>
          <Link href="/rag" className="flex items-center text-sm text-muted-foreground hover:text-foreground mb-1 sm:mb-2">
            <ArrowLeft className="h-3 w-3 sm:h-4 sm:w-4 mr-1 sm:mr-2" />
            Volver a Colecciones
          </Link>
          <h1 className="text-2xl sm:text-3xl font-bold">Todos los Documentos</h1>
        </div>
        <div className="flex items-center gap-3 flex-wrap"> {/* Contenedor para los botones */}
          <Button onClick={() => setIsUploadOpen(true)} className="w-full sm:w-auto">
              <Upload className="mr-2 h-4 w-4" />
              Subir Nuevo Documento
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" className="gap-2" disabled={!!docPollingId || !!collectionPollingId || isProcessingKnowledgeGraph}>
                <MoreHorizontal className="h-4 w-4" />
                <span className="hidden sm:inline">Acciones</span>
                <ChevronDown className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
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
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleExtractTitles} disabled={!!docPollingId || !!collectionPollingId}>
                <Text className="mr-2 h-4 w-4" />
                <span>Extraer Títulos</span>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleProcessKnowledgeGraph} disabled={isProcessingKnowledgeGraph}>
                <Network className="mr-2 h-4 w-4" />
                <span>Crear Grafo</span>
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

      <div className="flex-grow overflow-x-auto">
        {isLoading ? <p className="text-center py-4">Cargando documentos...</p> : <DataTable columns={columns} data={documents} />}
      </div>
      
      {/* --- NUEVA SECCIÓN DE HISTORIAL --- */}
      <div className="mt-6 sm:mt-8 pt-4 sm:pt-6 border-t">
        <h2 className="text-xl sm:text-2xl font-bold flex items-center gap-2 mb-3 sm:mb-4">
          <History className="h-5 w-5 sm:h-6 sm:w-6" />
          Historial de Análisis Recientes
        </h2>
        {savedAnalyses.length > 0 ? (
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
                  <Button variant="link" className="p-0 h-auto text-xs sm:text-sm" onClick={() => {
                    setAnalysisResult(analysis.result_payload);
                    if (analysis.file_name.startsWith('Resumen Semántico:')) {
                      setIsSemanticAnalysisOpen(true);
                    } else if (analysis.file_name.startsWith('Colección:')) {
                      setIsCollectionAnalysisOpen(true);
                    } else {
                      setDocumentToAnalyze({ file_name: analysis.file_name, topic: '', title: '', author: '' });
                      setIsAnalysisDialogOpen(true);
                    }
                  }}>
                    Ver Resultados Detallados
                  </Button>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        ) : (
          !isLoading && <p className="text-sm text-muted-foreground text-center py-4">No hay análisis guardados.</p>
        )}
      </div>

      {/* Diálogos */}
      <UploadDocumentDialog
        isOpen={isUploadOpen}
        onOpenChange={setIsUploadOpen}
        onUploadSuccess={fetchPageData}
        onUploadStart={handleUploadStart}
      />
      <PreviewDocumentDialog isOpen={!!documentToPreview} onOpenChange={(open) => !open && setDocumentToPreview(null)} document={documentToPreview} />
      <EditDocumentDialog isOpen={!!documentToEdit} onOpenChange={(open) => !open && setDocumentToEdit(null)} onUpdateSuccess={fetchPageData} document={documentToEdit} />
      <DeleteConfirmationDialog isOpen={!!documentToDelete} onOpenChange={(open) => !open && setDocumentToDelete(null)} onDeleteSuccess={fetchPageData} document={documentToDelete} />
      <AnalysisResultDialog isOpen={isAnalysisDialogOpen} onOpenChange={setIsAnalysisDialogOpen} analysis={analysisResult} document={documentToAnalyze} />
      <CollectionAnalysisDialog isOpen={isCollectionAnalysisOpen} onOpenChange={setIsCollectionAnalysisOpen} analysis={analysisResult} topic={documentToAnalyze?.file_name?.replace('Colección: ', '') ?? ''} />
      <SemanticAnalysisDialog isOpen={isSemanticAnalysisOpen} onOpenChange={setIsSemanticAnalysisOpen} analysis={analysisResult} topic={documentToAnalyze?.file_name?.replace('Resumen Semántico: ', '') ?? ''} />
      <CustomAnalysisDialog
        isOpen={isCustomAnalysisOpen}
        onOpenChange={setIsCustomAnalysisOpen}
        topic="all_documents" // Pasamos el topic por defecto
        onAnalysisStart={(taskId) => {
          setCollectionPollingId(taskId); // Usar el mismo polling para análisis de colección
          toast.info("Análisis personalizado iniciado. Esperando resultados...");
        }}
      />
    </div>
  );
}
