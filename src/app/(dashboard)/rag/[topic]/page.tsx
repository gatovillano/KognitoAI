// En: src/app/(dashboard)/rag/[topic]/page.tsx

'use client';

import { useEffect, useState, useMemo, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { ArrowLeft, Upload, History, Loader2, ScanSearch, FileText, FolderKanban, Text } from 'lucide-react';
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

  // Estado para el historial de análisis
  const [savedAnalyses, setSavedAnalyses] = useState([]);

  const fetchPageData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [docsRes, analysesRes] = await Promise.all([
        apiClient.post('/api/list-documents', { topic: topic }),
        apiClient.post('/api/get-saved-analyses', { topic: topic })
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
        <div className="flex items-center gap-2">
          <Button onClick={handleAnalyzeCollection} variant="outline" disabled={!!docPollingId || !!collectionPollingId}>
            {collectionPollingId ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ScanSearch className="mr-2 h-4 w-4" />}
            Analizar Colección
          </Button>
          <Button onClick={() => setIsUploadOpen(true)}>
            <Upload className="mr-2 h-4 w-4" />
            Subir a esta Colección
          </Button>
          <Button onClick={handleExtractTitles} variant="outline" disabled={!!docPollingId || !!collectionPollingId}>
            <Text className="mr-2 h-4 w-4" />
            Extraer Títulos
          </Button>
          <Button onClick={handleSemanticSummary} variant="outline" disabled={!!docPollingId || !!collectionPollingId}>
            <ScanSearch className="mr-2 h-4 w-4" />
            Resumen Semántico
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
                        {analysis.file_name.startsWith('Colección:') ? <FolderKanban className="h-4 w-4" /> : <FileText className="h-4 w-4" />}
                        <span className="font-medium truncate">{analysis.file_name}</span>
                        <span className="ml-auto text-xs text-muted-foreground pr-4">{new Date(analysis.created_at).toLocaleDateString()}</span>
                      </div>
                    </AccordionTrigger>
                    <AccordionContent>
                      <Button variant="link" className="p-0 h-auto" onClick={() => {
                        if (analysis.file_name.startsWith('Resumen Semántico:')) {
                          setSemanticAnalysisResult(analysis.result_payload);
                          setIsSemanticAnalysisOpen(true);
                        } else if (analysis.file_name.startsWith('Colección:')) {
                          setCollectionAnalysisResult(analysis.result_payload);
                          setIsCollectionAnalysisOpen(true);
                        } else {
                          setDocAnalysisResult(analysis.result_payload);
                          setDocumentToAnalyze({ file_name: analysis.file_name, topic, title: '', author: '' });
                          setIsDocAnalysisOpen(true);
                        }
                      }}>
                        Ver Resultados Detallados
                      </Button>
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
      <ShareDocumentDialog isOpen={isShareOpen} onOpenChange={setIsShareOpen} onShareSuccess={fetchPageData} document={documentToShare} />
    </div>
  );
}
