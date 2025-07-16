// En: src/app/(dashboard)/rag/[topic]/page.tsx

'use client';

import { useEffect, useState, useMemo, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { ArrowLeft, Upload, History, Loader2, ScanSearch, FileText, FolderKanban, Text, Sparkles, ChevronDown, MoreHorizontal, Network } from 'lucide-react';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from '@/components/ui/dropdown-menu';
import { useWebSocket } from '@/hooks/useWebSocket';
import { toast } from 'sonner';

import { DataTable } from '../data-table';
import { getColumns, type Document } from '../columns';
import apiClient from '@/lib/api';
import { UploadDocumentDialog } from '../upload-document-dialog';
import { PreviewDocumentDialog } from '../preview-document-dialog';
import { EditDocumentDialog } from '../edit-document-dialog';
import { DeleteConfirmationDialog } from '../delete-confirmation-dialog';
import { AnalysisResultDialog } from '../analysis-result-dialog';
import { CollectionAnalysisDialog } from '../collection-analysis-dialog';
import { SemanticAnalysisDialog } from '../semantic-analysis-dialog';
import { CustomAnalysisDialog } from '../custom-analysis-dialog';
import { CustomAnalysisResultDialog } from '../custom-analysis-result-dialog';
import { ShareDocumentDialog } from '../share-document-dialog';

export default function CollectionDetailPage() {
  const params = useParams();
  const topic = decodeURIComponent(params.topic as string);

  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
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

  // Estados para análisis semántico
  const [semanticAnalysisResult, setSemanticAnalysisResult] = useState<any>(null);
  const [isSemanticAnalysisOpen, setIsSemanticAnalysisOpen] = useState(false);

  // Estados para análisis personalizado
  const [isCustomAnalysisOpen, setIsCustomAnalysisOpen] = useState(false);
  const [customAnalysisResult, setCustomAnalysisResult] = useState<any>(null);
  const [isCustomAnalysisResultOpen, setIsCustomAnalysisResultOpen] = useState(false);

  // Estado para el historial de análisis
  const [savedAnalyses, setSavedAnalyses] = useState([]);

  // Estados para procesamiento de grafos de conocimiento
  const [isProcessingKnowledgeGraph, setIsProcessingKnowledgeGraph] = useState(false);

  // WebSocket para actualizaciones en tiempo real
  const { isConnected } = useWebSocket({
    onTitleUpdated: (data) => {
      // Actualizar la lista de documentos cuando se actualiza un título
      setDocuments(prevDocs =>
        prevDocs.map(doc =>
          doc.file_name === data.file_name
            ? { ...doc, title: data.new_title }
            : doc
        )
      );
    },
    onTitleExtractionStarted: (data) => {
      console.log('🚀 Extracción de títulos iniciada:', data);
    },
    onTitleExtractionCompleted: (data) => {
      console.log('✅ Extracción de títulos completada:', data);
      // Recargar la página para mostrar todos los cambios
      fetchPageData();
    }
  });

  const fetchPageData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [docsRes, analysesRes] = await Promise.all([
        apiClient.post('/api/list-documents', { topic: topic }),
        apiClient.post('/api/get-saved-analyses', { topic: topic, workspace_id: null })
      ]);
      
      // Ya no necesitamos filtrar en el frontend, el backend lo hace
      setDocuments(docsRes.data);
      setSavedAnalyses(analysesRes.data);
    } catch (error) {
      toast.error('Error al cargar los datos de la colección.');
    } finally {
      setIsLoading(false);
    }
  }, [topic]);

  useEffect(() => {
    fetchPageData();
  }, [fetchPageData]);

  // --- Handlers de Análisis ---

  const handleAnalyzeDocument = async (doc: Document) => {
    if (docPollingId || collectionPollingId) { toast.info("Ya hay un análisis en progreso."); return; }
    setDocumentToAnalyze(doc);
    try {
      const response = await apiClient.post('/api/start-document-analysis', { file_name: doc.file_name });
      setDocPollingId(response.data.task_id);
      toast.info(`Análisis para "${doc.file_name}" iniciado.`);
    } catch (error) { toast.error("No se pudo iniciar el análisis del documento."); }
  };
  
  const handleAnalyzeCollection = async () => {
    if (docPollingId || collectionPollingId) { toast.info("Ya hay un análisis en progreso."); return; }
    try {
      const response = await apiClient.post('/api/start-collection-analysis', { topic });
      setCollectionPollingId(response.data.task_id);
      toast.info(`Análisis de la colección "${topic}" iniciado.`);
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
          // Verificar si es análisis semántico por el nombre del archivo
          if (result?.analysis_metadata?.analysis_type === 'semantic_summary') {
            setSemanticAnalysisResult(result);
            setIsSemanticAnalysisOpen(true);
            toast.success("¡Resumen semántico completado!");
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
      const response = await apiClient.post('/api/extract-title', { topic });
      toast.info(`Extracción de títulos para la colección "${topic}" iniciada.`);
      fetchPageData();
    } catch (error) { toast.error("No se pudo iniciar la extracción de títulos."); }
  };

  // --- Handler para Extraer Título de un Documento Individual ---
  const handleExtractTitleForDocument = async (doc: Document) => {
    if (docPollingId || collectionPollingId) { toast.info("Ya hay un análisis en progreso."); return; }
    try {
      const response = await apiClient.post('/api/extract-title', { file_name: doc.file_name });
      toast.info(`Extracción de título para "${doc.file_name}" iniciada.`);
      fetchPageData();
    } catch (error) { toast.error(`No se pudo iniciar la extracción de título para "${doc.file_name}".`); }
  };

  // --- Handler para Resumen Semántico de la Colección ---
  const handleSemanticSummary = async () => {
    if (docPollingId || collectionPollingId) { toast.info("Ya hay un análisis en progreso."); return; }
    try {
      const response = await apiClient.post('/api/start-semantic-summary', { topic });
      setCollectionPollingId(response.data.task_id);
      toast.info(`Resumen semántico de la colección "${topic}" iniciado.`);
    } catch (error) { toast.error("No se pudo iniciar el resumen semántico de la colección."); }
  };

  // --- Handler para Procesar Grafos de Conocimiento ---
  const handleProcessKnowledgeGraph = async () => {
    if (isProcessingKnowledgeGraph) {
      toast.info("Ya hay un procesamiento de grafo en progreso.");
      return;
    }

    setIsProcessingKnowledgeGraph(true);
    const toastId = toast.loading(`Procesando grafo de conocimiento para "${topic}"...`);

    try {
      const response = await apiClient.post('/api/process-knowledge-graph', { topic });
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
  
  return (
    <div className="h-full flex flex-col p-6">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-2">
        <div>
          <Link href="/rag" className="flex items-center text-sm text-muted-foreground hover:text-foreground mb-2">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Volver a Colecciones
          </Link>
          <h1 className="text-3xl font-bold break-all">Colección: {topic}</h1>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          {/* Botón Principal */}
          <Button onClick={() => setIsUploadOpen(true)} size="lg" className="bg-primary hover:bg-primary/90">
            <Upload className="mr-2 h-4 w-4" />
            Subir Documentos
          </Button>

          {/* Menú de Análisis */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" className="gap-2" disabled={!!docPollingId || !!collectionPollingId}>
                {collectionPollingId ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <ScanSearch className="h-4 w-4" />
                )}
                <span className="hidden sm:inline">Análisis</span>
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
              <DropdownMenuItem onClick={() => setIsCustomAnalysisOpen(true)}>
                <Sparkles className="mr-2 h-4 w-4" />
                <span>Análisis Personalizado</span>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleExtractTitles} disabled={!!docPollingId || !!collectionPollingId}>
                <Text className="mr-2 h-4 w-4" />
                <span>Extraer Títulos</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Botón de Grafos de Conocimiento */}
          <Button
            onClick={handleProcessKnowledgeGraph}
            variant="outline"
            disabled={isProcessingKnowledgeGraph}
            className="gap-2 border-blue-500 text-blue-600 hover:bg-blue-50"
          >
            <Network className="h-4 w-4" />
            <span className="hidden sm:inline">
              {isProcessingKnowledgeGraph ? "Procesando..." : "Crear Grafo"}
            </span>
          </Button>
        </div>
      </div>
      
      {(docPollingId || collectionPollingId) && (
        <div className="bg-muted text-muted-foreground p-3 rounded-md mb-4 flex items-center gap-2 text-sm animate-pulse">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Un análisis está en progreso. La interfaz sigue siendo funcional...</span>
        </div>
      )}

      <Card className="flex-grow mb-6">
        <CardHeader>
          <CardTitle>Documentos en la Colección</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-auto">
            <DataTable columns={columns} data={documents} />
          </div>
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
            <div className="w-full max-h-[300px] overflow-y-auto">
              <Accordion type="single" collapsible className="w-full">
                {savedAnalyses.map((analysis: any) => (
                  <AccordionItem value={`item-${analysis.id}`} key={analysis.id}>
                    <AccordionTrigger>
                      <div className="flex items-center gap-2 text-left flex-1 min-w-0">
                        {analysis.file_name.startsWith('Colección:') ? (
                          <FolderKanban className="h-4 w-4" />
                        ) : analysis.file_name.startsWith('Análisis Personalizado:') ? (
                          <Sparkles className="h-4 w-4 text-pink-500" />
                        ) : analysis.file_name.startsWith('Resumen Semántico:') ? (
                          <Text className="h-4 w-4 text-purple-500" />
                        ) : (
                          <FileText className="h-4 w-4" />
                        )}
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
                            <p className="text-sm text-muted-foreground overflow-hidden" style={{
                              display: '-webkit-box',
                              WebkitLineClamp: 3,
                              WebkitBoxOrient: 'vertical'
                            }}>
                              {analysis.result_payload.collection_summary}
                            </p>
                          </div>
                        )}

                        {analysis.file_name.startsWith('Resumen Semántico:') && analysis.result_payload?.resumen_semantico && (
                          <div className="p-3 bg-muted rounded-lg">
                            <h4 className="font-medium text-sm mb-2">Resumen Semántico:</h4>
                            <p className="text-sm text-muted-foreground overflow-hidden" style={{
                              display: '-webkit-box',
                              WebkitLineClamp: 3,
                              WebkitBoxOrient: 'vertical'
                            }}>
                              {analysis.result_payload.resumen_semantico}
                            </p>
                          </div>
                        )}

                        {analysis.file_name.startsWith('Análisis Personalizado:') && analysis.result_payload?.analysis_result && (
                          <div className="p-3 bg-muted rounded-lg">
                            <h4 className="font-medium text-sm mb-2">Resultado del Análisis:</h4>
                            <p className="text-sm text-muted-foreground overflow-hidden" style={{
                              display: '-webkit-box',
                              WebkitLineClamp: 3,
                              WebkitBoxOrient: 'vertical'
                            }}>
                              {typeof analysis.result_payload.analysis_result === 'string'
                                ? analysis.result_payload.analysis_result
                                : JSON.stringify(analysis.result_payload.analysis_result).substring(0, 200) + '...'}
                            </p>
                          </div>
                        )}

                        {!analysis.file_name.startsWith('Colección:') &&
                         !analysis.file_name.startsWith('Resumen Semántico:') &&
                         !analysis.file_name.startsWith('Análisis Personalizado:') &&
                         analysis.result_payload?.resumen_ejecutivo && (
                          <div className="p-3 bg-muted rounded-lg">
                            <h4 className="font-medium text-sm mb-2">Resumen Ejecutivo:</h4>
                            <p className="text-sm text-muted-foreground overflow-hidden" style={{
                              display: '-webkit-box',
                              WebkitLineClamp: 3,
                              WebkitBoxOrient: 'vertical'
                            }}>
                              {analysis.result_payload.resumen_ejecutivo}
                            </p>
                          </div>
                        )}

                        <Button variant="link" className="p-0 h-auto" onClick={() => {
                          if (analysis.file_name.startsWith('Resumen Semántico:')) {
                            setSemanticAnalysisResult(analysis.result_payload);
                            setIsSemanticAnalysisOpen(true);
                          } else if (analysis.file_name.startsWith('Colección:')) {
                            console.log('📁 Abriendo análisis de colección');
                            setCollectionAnalysisResult(analysis.result_payload);
                            setIsCollectionAnalysisOpen(true);
                          } else if (analysis.file_name.startsWith('Análisis Personalizado:')) {
                            console.log('✨ Abriendo análisis personalizado');
                            setCustomAnalysisResult(analysis.result_payload);
                            setIsCustomAnalysisResultOpen(true);
                          } else {
                            console.log('📄 Abriendo análisis de documento');
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

      {/* Diálogos */}
      <UploadDocumentDialog isOpen={isUploadOpen} onOpenChange={setIsUploadOpen} onUploadSuccess={fetchPageData} defaultTopic={topic} />
      <PreviewDocumentDialog isOpen={!!documentToPreview} onOpenChange={(open) => !open && setDocumentToPreview(null)} document={documentToPreview} />
      <EditDocumentDialog isOpen={!!documentToEdit} onOpenChange={(open) => !open && setDocumentToEdit(null)} onUpdateSuccess={fetchPageData} document={documentToEdit} />
      <DeleteConfirmationDialog isOpen={!!documentToDelete} onOpenChange={(open) => !open && setDocumentToDelete(null)} onDeleteSuccess={fetchPageData} document={documentToDelete} />
      <AnalysisResultDialog isOpen={isDocAnalysisOpen} onOpenChange={setIsDocAnalysisOpen} analysis={docAnalysisResult} document={documentToAnalyze ?? { file_name: '', topic: topic, title: '', author: '' }} />
      <CollectionAnalysisDialog isOpen={isCollectionAnalysisOpen} onOpenChange={setIsCollectionAnalysisOpen} analysis={collectionAnalysisResult} topic={topic} />
      <SemanticAnalysisDialog isOpen={isSemanticAnalysisOpen} onOpenChange={setIsSemanticAnalysisOpen} analysis={semanticAnalysisResult} topic={topic} />
      <CustomAnalysisDialog
        isOpen={isCustomAnalysisOpen}
        onOpenChange={setIsCustomAnalysisOpen}
        document={documentToAnalyze ?? { file_name: '', topic: topic, title: '', author: '' }}
        topic={topic}
        onAnalysisStart={fetchPageData}
      />
      <CustomAnalysisResultDialog
        isOpen={isCustomAnalysisResultOpen}
        onOpenChange={setIsCustomAnalysisResultOpen}
        analysisResult={customAnalysisResult}
      />
      <ShareDocumentDialog isOpen={isShareOpen} onOpenChange={setIsShareOpen} onShareSuccess={fetchPageData} document={documentToShare} />
    </div>
  );
}
